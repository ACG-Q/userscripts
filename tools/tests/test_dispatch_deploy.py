import os
import pathlib
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import dispatch_deploy


class FakeApi:
    def __init__(self, status):
        self.status = status
        self.calls = []

    def __call__(self, method, path, token, payload=None):
        self.calls.append((method, path, payload))
        return self.status, None


ENV = {"GITHUB_TOKEN": "tk", "GITHUB_REPOSITORY": "o/r", "GITHUB_REF_NAME": "master"}


class DispatchTest(unittest.TestCase):
    def _run(self, status, argv=None):
        api = FakeApi(status)
        with mock.patch.dict(os.environ, ENV, clear=False):
            code = dispatch_deploy.main(
                api_func=api, argv=argv or ["--workflow", "deploy-pages.yml"]
            )
        return code, api

    def test_success_posts_dispatches(self):
        code, api = self._run(204)
        self.assertEqual(code, 0)
        self.assertEqual(
            api.calls, [("POST", "/repos/o/r/workflows/deploy-pages.yml/dispatches",
                         {"ref": "master"})]
        )

    def test_failure_still_returns_0(self):
        code, api = self._run(404)
        self.assertEqual(code, 0)
        self.assertEqual(len(api.calls), 1)

    def test_explicit_ref_overrides_env(self):
        code, api = self._run(204, ["--workflow", "deploy-pages.yml", "--ref", "dev"])
        self.assertEqual(code, 0)
        self.assertEqual(api.calls[0][2], {"ref": "dev"})

    def test_missing_token_exits_2(self):
        env = dict(os.environ)
        env.pop("GITHUB_TOKEN", None)
        with mock.patch.dict(os.environ, env, clear=True):
            with self.assertRaises(SystemExit) as cm:
                dispatch_deploy.main(api_func=FakeApi(204), argv=["--workflow", "w.yml"])
        self.assertEqual(cm.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
