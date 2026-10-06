import os
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import assemble_site


class AssembleTest(unittest.TestCase):
    def _make_repo(self, td, entries):
        dist = os.path.join(td, "dist")
        os.makedirs(dist, exist_ok=True)
        for name in entries:
            path = os.path.join(dist, name)
            if name.endswith("/"):
                os.makedirs(path, exist_ok=True)
            else:
                with open(path, "w", encoding="utf-8") as f:
                    f.write("x")
        return dist

    def test_user_js_to_site_dist_rest_to_site(self):
        with tempfile.TemporaryDirectory() as td:
            self._make_repo(td, ["a.user.js", "b.user.js", "index.html", "scripts/"])
            placed = assemble_site.assemble(td)
            self.assertTrue(os.path.isfile(os.path.join(td, "_site", "dist", "a.user.js")))
            self.assertTrue(os.path.isfile(os.path.join(td, "_site", "dist", "b.user.js")))
            self.assertTrue(os.path.isfile(os.path.join(td, "_site", "index.html")))
            self.assertTrue(os.path.isdir(os.path.join(td, "_site", "scripts")))
            self.assertEqual(len(placed), 4)

    def test_missing_dist_raises(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(FileNotFoundError):
                assemble_site.assemble(td)

    def test_empty_dist_raises(self):
        with tempfile.TemporaryDirectory() as td:
            self._make_repo(td, [])
            with self.assertRaises(FileNotFoundError):
                assemble_site.assemble(td)

    def test_main_returns_1_on_missing_dist(self):
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(assemble_site.main(["--root", td]), 1)


if __name__ == "__main__":
    unittest.main()
