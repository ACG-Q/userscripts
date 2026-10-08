import pathlib
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import validate_graphql as vg

MINI_SCHEMA = """
type Query { repository(owner: String!, name: String): Repo }
type Repo { id: ID!, name: String }
schema { query: Query }
"""


def _schema_obj():
    from graphql import build_schema
    return build_schema(MINI_SCHEMA, assume_valid=True)


class CollectGoQueriesTest(unittest.TestCase):
    def test_collects_query_literals_and_skips_noise(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "queries.go"
            p.write_text(
                "package github\n"
                "const Q = `query { repository(owner: \\\"a\\\", name: \\\"b\\\") { id } }`\n"
                "const NotQ = `plain text without graphql`\n",
                encoding="utf-8")
            got = vg.collect_go_queries(Path(d))
        self.assertEqual(len(got), 1)
        self.assertIn("query", next(iter(got.values())))

    def test_missing_go_dir_returns_error(self):
        self.assertEqual(vg.main(["--go-dir", r"C:\no\such\dir", "--offline"]), 1)


class ValidateTextTest(unittest.TestCase):
    def test_valid_query_passes(self):
        errs = vg.validate_text(_schema_obj(), "q", "query { repository(owner: \"a\") { id } }")
        self.assertEqual(errs, [])

    def test_unknown_field_reported(self):
        errs = vg.validate_text(_schema_obj(), "q", "query { repository { nope } }")
        self.assertTrue(errs)

    def test_syntax_error_reported(self):
        errs = vg.validate_text(_schema_obj(), "q", "query {")
        self.assertTrue(errs)


if __name__ == "__main__":
    unittest.main()
