import os
import pathlib
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import reply


class FakeApi:
    def __init__(self, status=201):
        self.status = status
        self.calls = []

    def __call__(self, method, path, token, payload=None):
        self.calls.append((method, path, payload))
        return self.status, None


ENV = {"GITHUB_TOKEN": "tk", "GITHUB_REPOSITORY": "o/r", "ISSUE_NUMBER": "7"}


class ComposeTest(unittest.TestCase):
    def test_success_empty_result(self):
        self.assertEqual(reply.compose_body("", "", "success"), "**执行结果：**\n操作完成")

    def test_failure_prefix(self):
        body = reply.compose_body("部分结果", "", "failure")
        self.assertTrue(body.startswith("**执行结果：**\n⚠️ 命令执行失败（Run command: failure）"))
        self.assertIn("部分结果", body)

    def test_proj_appended(self):
        body = reply.compose_body("结果X", "投影Y", "success")
        self.assertEqual(body, "**执行结果：**\n结果X\n\n投影Y")

    def test_skipped_counts_as_success(self):
        self.assertEqual(reply.compose_body("R", "", "skipped"), "**执行结果：**\nR")


class ComposeBodyStatusTest(unittest.TestCase):
    def test_commit_failure_reported(self):
        out = reply.compose_body("结果", "", "success", commit_ok="failure")
        self.assertIn("提交失败", out)
        self.assertIn("Commit changes: failure", out)

    def test_dispatch_failure_reported(self):
        out = reply.compose_body(
            "结果", "", "success", commit_ok="success", dispatch_ok="failure")
        self.assertIn("派发失败", out)
        self.assertIn("Trigger site deploy: failure", out)

    def test_skipped_and_success_silent(self):
        out = reply.compose_body(
            "结果", "", "success", commit_ok="skipped", dispatch_ok="success")
        self.assertNotIn("提交失败", out)
        self.assertNotIn("派发失败", out)

    def test_cmd_failure_still_first(self):
        out = reply.compose_body("结果", "", "failure", commit_ok="failure")
        self.assertLess(out.index("命令执行失败"), out.index("提交失败"))


class MainTest(unittest.TestCase):
    def _run(self, extra, api):
        env = dict(ENV)
        env.update(extra)
        with mock.patch.dict(os.environ, env, clear=False):
            return reply.main(api_func=api)

    def test_posts_composed_body(self):
        api = FakeApi()
        code = self._run({"RESULT": "hello", "PROJ": "", "CMD_OK": "success"}, api)
        self.assertEqual(code, 0)
        method, path, payload = api.calls[0]
        self.assertEqual((method, path), ("POST", "/repos/o/r/issues/7/comments"))
        self.assertEqual(payload, {"body": "**执行结果：**\nhello"})

    def test_api_failure_returns_1(self):
        code = self._run({"RESULT": "", "PROJ": "", "CMD_OK": "success"}, FakeApi(500))
        self.assertEqual(code, 1)

    def test_commit_failure_env_posted(self):
        api = FakeApi()
        code = self._run(
            {"RESULT": "r", "PROJ": "", "CMD_OK": "success", "COMMIT_OK": "failure"}, api)
        self.assertEqual(code, 0)
        self.assertIn("提交失败", api.calls[0][2]["body"])

    def test_missing_issue_number_exits_2(self):
        env = dict(ENV)
        env.pop("ISSUE_NUMBER")
        with mock.patch.dict(os.environ, env, clear=True):
            with self.assertRaises(SystemExit) as cm:
                reply.main(api_func=FakeApi())
        self.assertEqual(cm.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
