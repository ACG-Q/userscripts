import os
import pathlib
import sys
import tempfile
import types
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import commit

ARGV = ["--allowlist", "registry.json", "scripts", "--message", "test msg"]


class CommitTest(unittest.TestCase):
    def _run(self, rcs, argv=None):
        calls = []

        def fake_git(*args):
            calls.append(args)
            rc = rcs.pop(0) if rcs else 0
            return types.SimpleNamespace(returncode=rc, stdout="", stderr="")

        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "out")
            with mock.patch.dict(os.environ, {"GITHUB_OUTPUT": out}):
                code = commit.main(argv or ARGV, git=fake_git)
            if os.path.exists(out):
                with open(out, encoding="utf-8") as f:
                    content = f.read()
            else:
                content = ""
        return code, content, calls

    def test_no_changes_writes_committed_false_and_skips(self):
        code, content, calls = self._run([0, 0, 0, 0])
        self.assertEqual(code, 0)
        self.assertEqual(content, "committed=false\n")
        self.assertFalse(any(c[0] == "commit" for c in calls))

    def test_changes_commit_and_push(self):
        code, content, calls = self._run([0, 0, 0, 1, 0, 0])
        self.assertEqual(code, 0)
        self.assertEqual(content, "committed=true\n")
        self.assertTrue(any(c[0] == "commit" and c[1] == "-m" for c in calls))
        self.assertTrue(any(c == ("push",) for c in calls))

    def test_add_failure_returns_1(self):
        code, _, calls = self._run([0, 0, 1])
        self.assertEqual(code, 1)
        self.assertFalse(any(c[0] == "commit" for c in calls))

    def test_diff_error_returns_1(self):
        code, _, _ = self._run([0, 0, 0, 2])
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
