import re
import unittest
from pathlib import Path

YML = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "issue-commands.yml"


class IssueCommandsIfConditionsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = YML.read_text(encoding="utf-8")

    def _step_if(self, step_id):
        m = re.search(
            rf"- name: [^\n]+\n\s+id: {step_id}\n\s+if: \${{{{([^}}]+)}}}}",
            self.text)
        self.assertIsNotNone(m, f"步骤 {step_id} 缺 id 或 if 条件")
        return m.group(1)

    def test_commit_if_survives_upstream_failure(self):
        cond = self._step_if("commit")
        self.assertIn("!cancelled()", cond)
        self.assertIn("steps.cmd.outcome == 'success'", cond)
        self.assertIn("steps.cmd.outputs.changed == 'true'", cond)

    def test_dispatch_if_requires_commit_only(self):
        cond = self._step_if("deploy")
        self.assertIn("!cancelled()", cond)
        self.assertIn("steps.commit.outputs.committed == 'true'", cond)

    def test_dispatch_has_id(self):
        self.assertRegex(self.text, r"id: deploy")


if __name__ == "__main__":
    unittest.main()
