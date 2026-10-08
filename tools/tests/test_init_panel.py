import os
import pathlib
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import init_panel


class SeqApi:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, method, path, token, payload=None):
        self.calls.append((method, path, payload))
        return self.responses.pop(0)


ENV = {"GITHUB_TOKEN": "tk", "GITHUB_REPOSITORY": "o/r"}
ISSUES_PATH = "/repos/o/r/issues?state=open&per_page=100"


class InitPanelTest(unittest.TestCase):
    def _run(self, api, env=None):
        with mock.patch.dict(os.environ, env or ENV, clear=False):
            return init_panel.main(api_func=api, argv=[])

    def test_existing_panel_skips_create(self):
        api = SeqApi([(200, [{"number": 1, "title": "命令面板"}])])
        self.assertEqual(self._run(api), 0)
        self.assertEqual(len(api.calls), 1)
        self.assertEqual(api.calls[0][0], "GET")

    def test_missing_panel_creates_issue(self):
        api = SeqApi([(200, []), (201, {"number": 9})])
        self.assertEqual(self._run(api), 0)
        method, path, payload = api.calls[1]
        self.assertEqual((method, path), ("POST", "/repos/o/r/issues"))
        self.assertEqual(payload["title"], "命令面板")
        self.assertEqual(payload["labels"], ["command-panel"])
        self.assertIn("/list", payload["body"])

    def test_pull_request_with_same_title_is_ignored(self):
        api = SeqApi([(200, [{"number": 3, "title": "命令面板", "pull_request": {}}]),
                      (201, {"number": 9})])
        self.assertEqual(self._run(api), 0)
        self.assertEqual(len(api.calls), 2)

    def test_title_contains_match(self):
        api = SeqApi([(200, [{"number": 5, "title": "🛠️ 命令面板（勿删）"}])])
        self.assertEqual(self._run(api), 0)
        self.assertEqual(len(api.calls), 1)
        self.assertEqual(api.calls[0][0], "GET")

    def test_list_failure_returns_1(self):
        api = SeqApi([(500, None)])
        self.assertEqual(self._run(api), 1)
        self.assertEqual(len(api.calls), 1)
        self.assertEqual(api.calls[0][0], "GET")

    def test_missing_token_exits_2(self):
        env = dict(ENV)
        env.pop("GITHUB_TOKEN")
        with mock.patch.dict(os.environ, env, clear=True):
            with self.assertRaises(SystemExit) as cm:
                init_panel.main(api_func=SeqApi([]), argv=[])
        self.assertEqual(cm.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
