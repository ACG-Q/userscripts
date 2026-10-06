import os
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import gate


class FakeApi:
    def __init__(self, status=204):
        self.status = status
        self.calls = []

    def __call__(self, method, path, token, payload=None):
        self.calls.append((method, path, token))
        return self.status, None


def base_env(**extra):
    env = {
        "COMMENT_USER": "alice",
        "REPO_OWNER": "alice",
        "GITHUB_TOKEN": "tk",
        "GITHUB_REPOSITORY": "o/r",
        "COMMENT_ID": "42",
    }
    env.update(extra)
    return env


class GateTest(unittest.TestCase):
    def _run(self, api, extra=None):
        env = base_env(**(extra or {}))
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "out")
            env["GITHUB_OUTPUT"] = out
            with mock.patch.dict(os.environ, env, clear=False):
                code = gate.main(api_func=api)
            with open(out, encoding="utf-8") as f:
                content = f.read()
        return code, content

    def test_authorized_writes_true_and_calls_nothing(self):
        api = FakeApi()
        code, content = self._run(api)
        self.assertEqual(code, 0)
        self.assertEqual(content, "authorized=true\n")
        self.assertEqual(api.calls, [])

    def test_unauthorized_writes_false_and_deletes_comment(self):
        api = FakeApi()
        code, content = self._run(api, {"COMMENT_USER": "mallory"})
        self.assertEqual(code, 0)
        self.assertEqual(content, "authorized=false\n")
        self.assertEqual(api.calls, [("DELETE", "/repos/o/r/issues/comments/42", "tk")])

    def test_delete_failure_returns_1(self):
        api = FakeApi(status=500)
        code, _ = self._run(api, {"COMMENT_USER": "mallory"})
        self.assertEqual(code, 1)

    def test_missing_comment_id_exits_2(self):
        env = base_env(COMMENT_ID="")
        with tempfile.TemporaryDirectory() as td:
            env["GITHUB_OUTPUT"] = os.path.join(td, "out")
            with mock.patch.dict(os.environ, env, clear=False):
                with self.assertRaises(SystemExit) as cm:
                    gate.main(api_func=FakeApi())
        self.assertEqual(cm.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
