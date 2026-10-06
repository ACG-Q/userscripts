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
    def _run(self, rcs, argv=None, changed=("registry.json", "scripts"), status_rc=0):
        calls = []

        def fake_git(*args):
            calls.append(args)
            if args[:2] == ("status", "--porcelain"):
                path = args[-1]
                out = f" M {path}\n" if path in changed else ""
                return types.SimpleNamespace(returncode=status_rc, stdout=out, stderr="")
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
        code, content, calls = self._run([], changed=())
        self.assertEqual(code, 0)
        self.assertEqual(content, "committed=false\n")
        self.assertFalse(any(c[0] == "add" for c in calls))
        self.assertFalse(any(c[0] == "commit" for c in calls))

    def test_changes_commit_and_push(self):
        code, content, calls = self._run([0, 0, 0, 1, 0, 0])
        self.assertEqual(code, 0)
        self.assertEqual(content, "committed=true\n")
        self.assertTrue(any(c == ("add", "registry.json", "scripts") for c in calls))
        self.assertTrue(any(c[0] == "commit" and c[1] == "-m" for c in calls))
        self.assertTrue(any(c == ("push", "origin", "HEAD") for c in calls))

    def test_add_failure_returns_1(self):
        code, _, calls = self._run([0, 0, 1])
        self.assertEqual(code, 1)
        self.assertFalse(any(c[0] == "commit" for c in calls))

    def test_diff_error_returns_1(self):
        code, _, _ = self._run([0, 0, 0, 2])
        self.assertEqual(code, 1)

    def test_不存在路径被过滤不再传给_git_add(self):
        argv = ["--allowlist", "registry.json", "dist", "archive", "--message", "m"]
        code, content, calls = self._run(
            [0, 0, 0, 1, 0, 0], argv=argv, changed=("registry.json",)
        )
        self.assertEqual(code, 0)
        self.assertEqual(content, "committed=true\n")
        add_calls = [c for c in calls if c[0] == "add"]
        self.assertEqual(add_calls, [("add", "registry.json")])

    def test_status异常返回1且不提交(self):
        code, content, calls = self._run([], status_rc=2)
        self.assertEqual(code, 1)
        self.assertEqual(content, "")
        self.assertFalse(any(c[0] == "add" for c in calls))

    def test_all_paths_missing_short_circuits(self):
        code, content, calls = self._run(
            [], argv=["--allowlist", "dist", "--message", "m"], changed=()
        )
        self.assertEqual(code, 0)
        self.assertEqual(content, "committed=false\n")
        self.assertFalse(any(c[0] in ("add", "commit", "config") for c in calls))


if __name__ == "__main__":
    unittest.main()
