import os
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import github_api


class RequireEnvTest(unittest.TestCase):
    def test_present_returns_value(self):
        with mock.patch.dict(os.environ, {"FOO": "bar"}):
            self.assertEqual(github_api.require_env("FOO"), "bar")

    def test_missing_exits_2(self):
        env = dict(os.environ)
        env.pop("FOO", None)
        with mock.patch.dict(os.environ, env, clear=True):
            with self.assertRaises(SystemExit) as cm:
                github_api.require_env("FOO")
        self.assertEqual(cm.exception.code, 2)


class WriteOutputTest(unittest.TestCase):
    def test_writes_to_github_output_file(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "out")
            with mock.patch.dict(os.environ, {"GITHUB_OUTPUT": path}):
                github_api.write_output("k", "v")
            with open(path, encoding="utf-8") as f:
                self.assertEqual(f.read(), "k=v\n")

    def test_falls_back_to_stdout_without_env(self):
        env = dict(os.environ)
        env.pop("GITHUB_OUTPUT", None)
        with mock.patch.dict(os.environ, env, clear=True):
            import io
            from contextlib import redirect_stdout
            buf = io.StringIO()
            with redirect_stdout(buf):
                github_api.write_output("k", "v")
        self.assertEqual(buf.getvalue(), "k=v\n")


if __name__ == "__main__":
    unittest.main()
