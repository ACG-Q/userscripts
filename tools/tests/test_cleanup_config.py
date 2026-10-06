import os
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import cleanup_config


class NormalizeTest(unittest.TestCase):
    def test_schedule_is_always_real_cleanup(self):
        self.assertEqual(cleanup_config.normalize("schedule", "", ""), ("true", "10"))

    def test_dispatch_defaults_to_dry_run(self):
        self.assertEqual(
            cleanup_config.normalize("workflow_dispatch", "", "5"), ("false", "5")
        )

    def test_dispatch_explicit_true(self):
        self.assertEqual(
            cleanup_config.normalize("workflow_dispatch", "true", "20"), ("true", "20")
        )

    def test_dispatch_explicit_false(self):
        self.assertEqual(
            cleanup_config.normalize("workflow_dispatch", "false", "10"), ("false", "10")
        )

    def test_dispatch_empty_keep_falls_back_to_10(self):
        self.assertEqual(
            cleanup_config.normalize("workflow_dispatch", "false", ""), ("false", "10")
        )


class MainTest(unittest.TestCase):
    def test_main_writes_both_outputs(self):
        env = {"EVENT": "schedule", "DISPATCH_APPLY": "", "KEEP": ""}
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "out")
            env["GITHUB_OUTPUT"] = out
            with mock.patch.dict(os.environ, env, clear=False):
                code = cleanup_config.main()
            with open(out, encoding="utf-8") as f:
                content = f.read()
        self.assertEqual(code, 0)
        self.assertEqual(content, "apply=true\nkeep=10\n")


if __name__ == "__main__":
    unittest.main()
