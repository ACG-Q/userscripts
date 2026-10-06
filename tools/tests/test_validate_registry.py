import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import validate_registry

OK = {"schema": 1, "scripts": [{"id": "a", "type": "self"}]}


class ValidateTest(unittest.TestCase):
    def test_valid_returns_no_errors(self):
        self.assertEqual(validate_registry.validate(OK), [])

    def test_empty_registry_is_valid(self):
        self.assertEqual(validate_registry.validate({"schema": 1, "scripts": []}), [])

    def test_top_level_must_be_object(self):
        self.assertTrue(validate_registry.validate([]))

    def test_scripts_must_be_list(self):
        self.assertTrue(validate_registry.validate({"scripts": {"a": 1}}))

    def test_missing_id_reported(self):
        errors = validate_registry.validate({"scripts": [{"type": "self"}]})
        self.assertTrue(any("缺 id" in e for e in errors))

    def test_invalid_type_reported(self):
        errors = validate_registry.validate({"scripts": [{"id": "a", "type": "evil"}]})
        self.assertTrue(any("type 非法" in e for e in errors))


class MainTest(unittest.TestCase):
    def _run(self, data):
        with tempfile.TemporaryDirectory() as td:
            path = pathlib.Path(td) / "registry.json"
            if data is not None:
                path.write_text(json.dumps(data), encoding="utf-8")
            return validate_registry.main(["--registry", str(path)])

    def test_valid_file_returns_0(self):
        self.assertEqual(self._run(OK), 0)

    def test_invalid_entry_returns_1(self):
        self.assertEqual(self._run({"scripts": [{"type": "synced"}]}), 1)

    def test_unparsable_file_returns_1(self):
        with tempfile.TemporaryDirectory() as td:
            path = pathlib.Path(td) / "registry.json"
            path.write_text("{ not json", encoding="utf-8")
            self.assertEqual(validate_registry.main(["--registry", str(path)]), 1)


if __name__ == "__main__":
    unittest.main()
