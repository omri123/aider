import os
from pathlib import Path, PurePosixPath
import difflib
import io
import difflib
from typing import List

import git
import pathspec

from aider import models, prompts, utils
from aider.sendchat import simple_send_with_retries


class AiderDiff:
    def __init__(self, change_type, path_a, path_b, content_a, content_b, start_a):
        self.change_type = change_type
        self.path_a = path_a
        self.path_b = path_b
        self.content_a = content_a
        self.content_b = content_b
        self.start_a = start_a
    
    def __repr__(self) -> str:
        return f"AiderDiff:\ntyps: {self.change_type}\npath_a: {self.path_a}\npath_b: {self.path_b}\ncontent_a:\n{self.content_a}\ncontent_b:\n{self.content_b}\nstart_a: {self.start_a}"

def get_content(commit, path):
    try:
        blob = commit.tree / path
    except KeyError:
        return ""
    with io.BytesIO(blob.data_stream.read()) as f:
        return f.read().decode('utf-8')


def merge_unmatching_blocks(unmatching_blocks):
    maximal_distance = 3
    merged_blocks = []
    for i, block in enumerate(unmatching_blocks):
        if i == 0:
            merged_blocks.append(block)
        else:
            prev = merged_blocks[-1]
            distance_a = block[0] - prev[0] - prev[1]
            distance_b = block[2] - prev[2] - prev[3]
            if distance_a < maximal_distance or distance_b < maximal_distance:
                merged_blocks[-1] = (prev[0], block[0] + block[1] - prev[0], prev[2], block[2] + block[3] - prev[2])
            else:
                merged_blocks.append(block)
    return merged_blocks

def create_diff_blocks(blocks_indecies, content_a, content_b, change)-> List[AiderDiff]: 
    # extract diff blocks from content using indecies.
    # blocks_indecies is a list of tuples (start_a, len_a, start_b, len_b)
    diff_blocks = []
    for (start_a, len_a, start_b, len_b) in blocks_indecies:
        end_a = start_a + len_a
        end_b = start_b + len_b
        if start_a == end_a and start_b == end_b:
            continue
        content_a_lines = content_a.splitlines(keepends=False)[start_a:end_a]
        content_b_lines = content_b.splitlines(keepends=False)[start_b:end_b]
        diff_blocks.append(AiderDiff(change.change_type, change.a_path, change.b_path, "\n".join(content_a_lines), "\n".join(content_b_lines), start_a))
    return diff_blocks

def add_line_numbers(content, start_line):
    lines = content.splitlines()
    lines_view = []
    digits = 4  # number of digits in line number. TODO: make this configurable
    for i, line in enumerate(lines):
        lines_view.append(f"{i+start_line:{digits}}|{lines[i]}")
    
    code_view = "\n".join(lines_view)
    return code_view

class GitRepo:
    repo = None
    aider_ignore_file = None
    aider_ignore_spec = None
    aider_ignore_ts = 0

    def __init__(self, io, fnames, git_dname, aider_ignore_file=None):
        self.io = io

        if git_dname:
            check_fnames = [git_dname]
        elif fnames:
            check_fnames = fnames
        else:
            check_fnames = ["."]

        repo_paths = []
        for fname in check_fnames:
            fname = Path(fname)
            fname = fname.resolve()

            if not fname.exists() and fname.parent.exists():
                fname = fname.parent

            try:
                repo_path = git.Repo(fname, search_parent_directories=True).working_dir
                repo_path = utils.safe_abs_path(repo_path)
                repo_paths.append(repo_path)
            except git.exc.InvalidGitRepositoryError:
                pass

        num_repos = len(set(repo_paths))

        if num_repos == 0:
            raise FileNotFoundError
        if num_repos > 1:
            self.io.tool_error("Files are in different git repos.")
            raise FileNotFoundError

        # https://github.com/gitpython-developers/GitPython/issues/427
        self.repo = git.Repo(repo_paths.pop(), odbt=git.GitDB)
        self.root = utils.safe_abs_path(self.repo.working_tree_dir)

        if aider_ignore_file:
            self.aider_ignore_file = Path(aider_ignore_file)

    def commit(self, fnames=None, context=None, prefix=None, message=None):
        if not fnames and not self.repo.is_dirty():
            return

        diffs = self.get_diffs(fnames)
        if not diffs:
            return

        if message:
            commit_message = message
        else:
            commit_message = self.get_commit_message(diffs, context)

        if not commit_message:
            commit_message = "(no commit message provided)"

        if prefix:
            commit_message = prefix + commit_message

        full_commit_message = commit_message
        if context:
            full_commit_message += "\n\n# Aider chat conversation:\n\n" + context

        cmd = ["-m", full_commit_message, "--no-verify"]
        if fnames:
            fnames = [str(self.abs_root_path(fn)) for fn in fnames]
            for fname in fnames:
                self.repo.git.add(fname)
            cmd += ["--"] + fnames
        else:
            cmd += ["-a"]

        self.repo.git.commit(cmd)
        commit_hash = self.repo.head.commit.hexsha[:7]
        self.io.tool_output(f"Commit {commit_hash} {commit_message}")

        return commit_hash, commit_message

    def get_rel_repo_dir(self):
        try:
            return os.path.relpath(self.repo.git_dir, os.getcwd())
        except ValueError:
            return self.repo.git_dir

    def get_commit_message(self, diffs, context):
        if len(diffs) >= 4 * 1024 * 4:
            self.io.tool_error(
                f"Diff is too large for {models.GPT35.name} to generate a commit message."
            )
            return

        diffs = "# Diffs:\n" + diffs

        content = ""
        if context:
            content += context + "\n"
        content += diffs

        messages = [
            dict(role="system", content=prompts.commit_system),
            dict(role="user", content=content),
        ]

        for model in models.Model.commit_message_models():
            commit_message = simple_send_with_retries(model.name, messages)
            if commit_message:
                break

        if not commit_message:
            self.io.tool_error("Failed to generate commit message!")
            return

        commit_message = commit_message.strip()
        if commit_message and commit_message[0] == '"' and commit_message[-1] == '"':
            commit_message = commit_message[1:-1].strip()

        return commit_message

    def get_diffs(self, fnames=None):
        # We always want diffs of index and working dir
        try:
            commits = self.repo.iter_commits(self.repo.active_branch)
            current_branch_has_commits = any(commits)
        except git.exc.GitCommandError:
            current_branch_has_commits = False

        if not fnames:
            fnames = []

        diffs = ""
        for fname in fnames:
            if not self.path_in_repo(fname):
                diffs += f"Added {fname}\n"

        if current_branch_has_commits:
            args = ["HEAD", "--"] + list(fnames)
            diffs += self.repo.git.diff(*args)
            return diffs

        wd_args = ["--"] + list(fnames)
        index_args = ["--cached"] + wd_args

        diffs += self.repo.git.diff(*index_args)
        diffs += self.repo.git.diff(*wd_args)

        return diffs

    def diff_commits(self, pretty, from_commit, to_commit):
        args = []
        if pretty:
            args += ["--color"]

        args += [from_commit, to_commit]
        diffs = self.repo.git.diff(*args)

        return diffs

    def get_tracked_files(self):
        if not self.repo:
            return []

        try:
            commit = self.repo.head.commit
        except ValueError:
            commit = None

        files = []
        if commit:
            for blob in commit.tree.traverse():
                if blob.type == "blob":  # blob is a file
                    files.append(blob.path)

        # Add staged files
        index = self.repo.index
        staged_files = [path for path, _ in index.entries.keys()]

        files.extend(staged_files)

        # convert to appropriate os.sep, since git always normalizes to /
        res = set(
            str(Path(PurePosixPath((Path(self.root) / path).relative_to(self.root))))
            for path in files
        )

        return self.filter_ignored_files(res)

    def filter_ignored_files(self, fnames):
        if not self.aider_ignore_file or not self.aider_ignore_file.is_file():
            return fnames

        mtime = self.aider_ignore_file.stat().st_mtime
        if mtime != self.aider_ignore_ts:
            self.aider_ignore_ts = mtime
            lines = self.aider_ignore_file.read_text().splitlines()
            self.aider_ignore_spec = pathspec.PathSpec.from_lines(
                pathspec.patterns.GitWildMatchPattern,
                lines,
            )

        return [fname for fname in fnames if not self.aider_ignore_spec.match_file(fname)]

    def path_in_repo(self, path):
        if not self.repo:
            return

        tracked_files = set(self.get_tracked_files())
        return path in tracked_files

    def abs_root_path(self, path):
        res = Path(self.root) / path
        return utils.safe_abs_path(res)

    def is_dirty(self, path=None):
        if path and not self.path_in_repo(path):
            return True

        return self.repo.is_dirty(path=path)

    def get_commits_hashes(self):
        for commit in self.repo.iter_commits():
            yield commit.hexsha

    def get_commit_content(self, hash):
        """Get diff for a commit, presented as search/replace blocks."""
        commit_a = self.repo.commit(hash + "^")
        commit_b = self.repo.commit(hash)
        diff = commit_a.diff(commit_b, create_patch=False)        
        all_diff_blocks = [] # list of AiderDiff objects
        for change in diff:
            content_a = get_content(commit_a, change.a_path)
            content_b = get_content(commit_b, change.b_path)
            matcher = difflib.SequenceMatcher(None, content_a.splitlines(keepends=True), content_b.splitlines(keepends=True))
            matching_blocks = list(matcher.get_matching_blocks()) # block is (i, j, n) such that a[i:i+n] == b[j:j+n]
            unmatching_blocks = [] # this is the list of changes! (i, ni, j, nj) such that block is i:i+ni in a and j:j+nj in b
            for i, mblock in enumerate(matching_blocks):
                if i == 0:
                    prev = (0, 0, 0)
                else:
                    prev = matching_blocks[i-1]
                prev_end_a = prev[0]+prev[2]
                prev_end_b = prev[1]+prev[2]
                unmatching_blocks.append((prev_end_a, mblock[0]-prev_end_a, prev_end_b, mblock[1]-prev_end_b))
            merged_blocks = merge_unmatching_blocks(unmatching_blocks)
            all_diff_blocks.extend(create_diff_blocks(merged_blocks, content_a, content_b, change))
        
        content = ""
        content += f"Commit {hash}\n"
        content += f"From: {commit_b.author.name} <{commit_b.author.email}>\n"
        content += f"Commit message: {commit_b.message}\n"
        for block in all_diff_blocks:
            if not (block.change_type == "A" or block.change_type == "D" or block.change_type == "M"):
                self.io.tool_error(f"Unsupported change type: {block.change_type}")
                return ""
            if block.path_a != block.path_b:
                self.io.tool_error(f"Unsupported change, path_a != path_b: {block.path_a} != {block.path_b}")
                return ""
            content += format_search_replace_block(block.path_a, block.content_a, block.content_b, block.start_a)
        return content

def format_search_replace_block(path, search, replace, search_start_line):
    content = ""
    content += "\n"
    content += "{fence[0]}\n"
    content += f"{path}\n"
    content += f"<<<<<<< SEARCH\n"
    content += f"{add_line_numbers(search, search_start_line)}\n"
    content += f"=======\n"
    content += f"{add_line_numbers(replace, search_start_line)}\n"
    content += f">>>>>>> REPLACE\n"
    content += "{fence[1]}\n"
    return content
        
