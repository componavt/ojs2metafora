import tempfile
import unittest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from unittest.mock import patch

from src.output_paths import (
    get_output_namespace,
    default_output_dir,
    resolve_generation_output_dir,
    resolve_batch_output_dir,
    get_upload_log_path,
    PROJECT_ROOT,
    OUTPUT_ROOT,
)


class TestOutputPaths(unittest.TestCase):

    def test_get_output_namespace_karrc(self):
        self.assertEqual(get_output_namespace("karrc"), "karrc")

    def test_get_output_namespace_mgta(self):
        self.assertEqual(get_output_namespace("mgta"), "mgta")

    def test_get_output_namespace_unknown_raises_valueerror(self):
        with self.assertRaises(ValueError) as cm:
            get_output_namespace("unknown")
        error_msg = str(cm.exception)
        self.assertIn("unknown", error_msg)
        self.assertIn("karrc", error_msg)
        self.assertIn("mgta", error_msg)

    def test_default_output_dir_karrc(self):
        result = default_output_dir("karrc")
        self.assertTrue(result.is_absolute())
        self.assertEqual(result.name, "karrc")

    def test_default_output_dir_mgta(self):
        result = default_output_dir("mgta")
        self.assertTrue(result.is_absolute())
        self.assertEqual(result.name, "mgta")

    def test_default_output_dir_ends_with_namespace(self):
        self.assertTrue(str(default_output_dir("karrc")).endswith("output/karrc"))
        self.assertTrue(str(default_output_dir("mgta")).endswith("output/mgta"))

    def test_resolve_generation_output_dir_none_uses_default(self):
        result = resolve_generation_output_dir("mgta", None)
        self.assertEqual(result, default_output_dir("mgta"))

    def test_resolve_generation_output_dir_explicit_literal(self):
        explicit = "/tmp/literal-output"
        result = resolve_generation_output_dir("mgta", explicit)
        self.assertEqual(result, Path(explicit))
        self.assertNotIn("mgta", str(result))

    def test_resolve_generation_output_dir_karrc_default(self):
        result = resolve_generation_output_dir("karrc", None)
        self.assertEqual(result, default_output_dir("karrc"))

    def test_resolve_batch_output_dir_existing_dir_literal(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = resolve_batch_output_dir("mgta", tmpdir)
            self.assertEqual(result, Path(tmpdir))
            self.assertNotIn("mgta", str(result))
            self.assertNotIn("2022", str(result))

    def test_resolve_batch_output_dir_year_mgta(self):
        result = resolve_batch_output_dir("mgta", "2022")
        expected = default_output_dir("mgta") / "2022"
        self.assertEqual(result, expected)

    def test_resolve_batch_output_dir_year_karrc(self):
        result = resolve_batch_output_dir("karrc", "2025")
        expected = default_output_dir("karrc") / "2025"
        self.assertEqual(result, expected)

    def test_resolve_batch_output_dir_preserves_posix(self):
        result = resolve_batch_output_dir("mgta", "2022")
        self.assertEqual(result.parts[-2:], ("mgta", "2022"))

    def test_project_root_constant(self):
        self.assertTrue(PROJECT_ROOT.is_absolute())
        self.assertTrue(PROJECT_ROOT.exists())

    def test_output_root_constant(self):
        self.assertEqual(OUTPUT_ROOT, PROJECT_ROOT / "output")

    def test_get_upload_log_path_karrc(self):
        result = get_upload_log_path("karrc")
        expected = default_output_dir("karrc") / "upload_log.json"
        self.assertEqual(result, expected)
        self.assertEqual(result.name, "upload_log.json")

    def test_get_upload_log_path_mgta(self):
        result = get_upload_log_path("mgta")
        expected = default_output_dir("mgta") / "upload_log.json"
        self.assertEqual(result, expected)
        self.assertEqual(result.name, "upload_log.json")

    def test_get_upload_log_path_resolves_source_namespace(self):
        karrc_path = get_upload_log_path("karrc")
        mgta_path = get_upload_log_path("mgta")
        self.assertIn("karrc", str(karrc_path))
        self.assertIn("mgta", str(mgta_path))
        self.assertNotEqual(karrc_path, mgta_path)

    def test_get_upload_log_path_unknown_source_raises(self):
        with self.assertRaises(ValueError):
            get_upload_log_path("invalid_source")

    def test_get_upload_log_path_does_not_create_file_or_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('src.output_paths.OUTPUT_ROOT', Path(tmpdir)):
                result = get_upload_log_path("karrc")
                log_path = Path(tmpdir) / "karrc" / "upload_log.json"
                self.assertFalse(log_path.exists())
                self.assertFalse(log_path.parent.exists())


if __name__ == '__main__':
    unittest.main()
