import os
import tempfile
import unittest
from aider.commands import Commands
from aider.io import InputOutput as IO
from aider.coder import Coder
from unittest.mock import MagicMock  # noqa: F401


class TestCommands(unittest.TestCase):
    def test_cmd_add(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)

            io = IO(pretty=False, yes=True)
            coder = Coder(io)
            commands = Commands(io, coder)

            with unittest.mock.patch("rich.prompt.Confirm.ask", return_value=True):
                commands.cmd_add("foo.txt bar.txt")

            foo_path = os.path.join(tmpdir, "foo.txt")
            bar_path = os.path.join(tmpdir, "bar.txt")

            self.assertTrue(os.path.exists(foo_path), "foo.txt should be created")
            self.assertTrue(os.path.exists(bar_path), "bar.txt should be created")


if __name__ == "__main__":
    unittest.main()