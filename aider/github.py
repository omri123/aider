from github import Github

class GithubRepo:
    """ A class for interacting with a github repository. """

    def __init__(self, token, repo_name) -> None:
        self.github = Github(token)
        self.repo = self.github.get_repo(repo_name)
        self.issue_numbers = []

    def get_issue_numbers(self) -> list:
        if not self.issue_numbers:
            self.issue_numbers = [issue.number for issue in self.repo.get_issues()]
        return self.issue_numbers

    def get_issue_content(self, issue_number: int) -> str:
        "Get the content of an issue"

        try:
            issue = self.repo.get_issue(number=issue_number)
        except:
            return ""
        
        issue_content = f"Title: {issue.title}\n\nBody:\n{issue.body}\n\nComments:\n"

        for comment in issue.get_comments():
            issue_content += f"{comment.user.login}: {comment.body}\n"

        return issue_content
