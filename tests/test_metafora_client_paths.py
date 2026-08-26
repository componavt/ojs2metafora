import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from unittest.mock import patch


class TestMetaforaClientBatchPaths(unittest.TestCase):

    def setUp(self):
        self.original_argv = sys.argv

    def tearDown(self):
        sys.argv = self.original_argv

    def _run_main(self, argv):
        from src.metafora_client import main
        sys.argv = ['metafora_client.py'] + argv
        try:
            main()
            return 0
        except SystemExit as e:
            return e.code


class TestMetaforaClientSafetyRegression(TestMetaforaClientBatchPaths):

    @patch('src.metafora_client.resolve_batch_output_dir')
    @patch('src.metafora_client.get_upload_log_path')
    def test_upload_all_with_year_mgta_source(self, mock_get_log_path, mock_resolve_dir):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            batch_dir = tmp_path / "mgta" / "2022"
            batch_dir.mkdir(parents=True)
            log_path = tmp_path / "mgta" / "upload_log.json"

            mock_resolve_dir.return_value = batch_dir
            mock_get_log_path.return_value = log_path

            argv = ['upload-all', '2022', '--source', 'mgta', '--dry-run']
            result = self._run_main(argv)
            self.assertEqual(result, 0, "Command succeeds in dry-run mode")

    @patch('src.metafora_client.resolve_batch_output_dir')
    @patch('src.metafora_client.get_upload_log_path')
    def test_upload_all_with_year_karrc_default(self, mock_get_log_path, mock_resolve_dir):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            batch_dir = tmp_path / "karrc" / "2025"
            batch_dir.mkdir(parents=True)
            log_path = tmp_path / "karrc" / "upload_log.json"

            mock_resolve_dir.return_value = batch_dir
            mock_get_log_path.return_value = log_path

            argv = ['upload-all', '2025', '--dry-run']
            result = self._run_main(argv)
            self.assertEqual(result, 0, "Command should succeed in dry-run mode")

    def test_upload_all_explicit_dir_is_literal(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            argv = ['upload-all', tmpdir, '--source', 'mgta', '--dry-run']
            result = self._run_main(argv)
            self.assertEqual(result, 0, "Command should succeed on empty directory in dry-run")

    @patch('src.metafora_client.resolve_batch_output_dir')
    @patch('src.metafora_client.get_upload_log_path')
    def test_sign_all_with_year_mgta_source(self, mock_get_log_path, mock_resolve_dir):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            batch_dir = tmp_path / "mgta" / "2022"
            batch_dir.mkdir(parents=True)
            log_path = tmp_path / "mgta" / "upload_log.json"

            mock_resolve_dir.return_value = batch_dir
            mock_get_log_path.return_value = log_path

            argv = ['sign-all', '2022', '--source', 'mgta']
            result = self._run_main(argv)
            self.assertEqual(result, 0, "Command succeeds (no files found)")

    @patch('src.metafora_client.resolve_batch_output_dir')
    @patch('src.metafora_client.get_upload_log_path')
    def test_sign_all_with_year_karrc_default(self, mock_get_log_path, mock_resolve_dir):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            batch_dir = tmp_path / "karrc" / "2025"
            batch_dir.mkdir(parents=True)
            log_path = tmp_path / "karrc" / "upload_log.json"

            mock_resolve_dir.return_value = batch_dir
            mock_get_log_path.return_value = log_path

            argv = ['sign-all', '2025']
            result = self._run_main(argv)
            self.assertEqual(result, 0, "Command should succeed (no files found)")

    def test_upload_all_invalid_source_rejected(self):
        argv = ['upload-all', '2022', '--source', 'invalid']
        result = self._run_main(argv)
        self.assertIsNotNone(result, "Invalid source should cause non-zero exit")
        self.assertNotEqual(result, 0, "Exit code should be non-zero")

    def test_sign_all_invalid_source_rejected(self):
        argv = ['sign-all', '2022', '--source', 'invalid']
        result = self._run_main(argv)
        self.assertIsNotNone(result, "Invalid source should cause non-zero exit")
        self.assertNotEqual(result, 0, "Exit code should be non-zero")


if __name__ == '__main__':
    unittest.main()
