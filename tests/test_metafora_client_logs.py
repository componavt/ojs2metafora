import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from unittest.mock import MagicMock, patch

from src.metafora_client import (
    load_log,
    save_log,
    cmd_status,
    cmd_sign,
    cmd_delete,
    cmd_upload,
    cmd_upload_all,
    cmd_sign_all,
    handle_upload_409,
    get_upload_log_path,
)
from src.output_paths import default_output_dir


class TestMetaforaClientLogPath(unittest.TestCase):

    def test_get_upload_log_path_karrc(self):
        result = get_upload_log_path("karrc")
        self.assertIn("karrc", str(result))
        self.assertEqual(result.name, "upload_log.json")

    def test_get_upload_log_path_mgta(self):
        result = get_upload_log_path("mgta")
        self.assertIn("mgta", str(result))
        self.assertEqual(result.name, "upload_log.json")

    def test_get_upload_log_path_resolves_correctly(self):
        result_karrc = get_upload_log_path("karrc")
        result_mgta = get_upload_log_path("mgta")
        self.assertNotEqual(result_karrc, result_mgta)
        self.assertIn("output/karrc/upload_log.json", str(result_karrc))
        self.assertIn("output/mgta/upload_log.json", str(result_mgta))

    def test_get_upload_log_path_unknown_raises_valueerror(self):
        with self.assertRaises(ValueError) as cm:
            get_upload_log_path("invalid")
        self.assertIn("invalid", str(cm.exception))


class TestMetaforaClientSourceIsolation(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)

        self.karrc_namespace = "karrc"
        self.mgta_namespace = "mgta"

        self.karrc_log_dir = Path(self.tmpdir.name) / self.karrc_namespace
        self.mgta_log_dir = Path(self.tmpdir.name) / self.mgta_namespace

        self.karrc_log_path = self.karrc_log_dir / "upload_log.json"
        self.mgta_log_path = self.mgta_log_dir / "upload_log.json"

        self.karrc_xml_path = self.karrc_log_dir / "mathem_n1.xml"
        self.mgta_xml_path = self.mgta_log_dir / "game_n1.xml"

        self.karrc_log_dir.mkdir(parents=True)
        self.mgta_log_dir.mkdir(parents=True)

        self.karrc_file_uid = "karrc-file-12345678-1234-1234-1234-123456789abc"
        self.mgta_file_uid = "mgta-file-abc98765-4321-4321-4321-cba987654321"

        self.karrc_article_uids = ["art-karrc-001", "art-karrc-002"]
        self.mgta_article_uids = ["art-mgta-001"]

        self._init_logs()

    def _init_logs(self):
        self.karrc_log_path.write_text(json.dumps({
            str(self.karrc_xml_path): {
                'file_uid': self.karrc_file_uid,
                'file_path': str(self.karrc_xml_path),
                'status_code': 3,
                'status_text': 'Processed',
                'article_uids': self.karrc_article_uids,
            }
        }))
        self.mgta_log_path.write_text(json.dumps({
            str(self.mgta_xml_path): {
                'file_uid': self.mgta_file_uid,
                'file_path': str(self.mgta_xml_path),
                'status_code': 3,
                'status_text': 'Processed',
                'article_uids': self.mgta_article_uids,
            }
        }))

    def test_missing_log_is_readonly(self):
        tmpdir = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(tmpdir, ignore_errors=True))
        mgta_log_path = Path(tmpdir) / "mgta" / "upload_log.json"
        self.assertFalse(mgta_log_path.exists())

        log_data = load_log(mgta_log_path)
        self.assertEqual(log_data, {})
        self.assertFalse(mgta_log_path.exists())

    @patch('src.metafora_client.get_upload_log_path')
    @patch('src.metafora_client.requests.get')
    def test_status_uses_selected_source_log(self, mock_get, mock_get_log_path):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'data': {
                'file_uid': self.karrc_file_uid,
                'xml': {'status': {'code': 3, 'status_text': 'Processed'}},
                'pdf': {'uploaded': True},
                'articles': self.karrc_article_uids,
            }
        }

        mock_get_log_path.side_effect = lambda source: (
            self.karrc_log_path if source == "karrc" else self.mgta_log_path
        )

        karrc_args = MagicMock()
        karrc_args.FILE_OR_UID = str(self.karrc_xml_path)
        karrc_args.verbose = False
        karrc_args.source = "karrc"

        with open(self.karrc_xml_path, 'w') as f:
            f.write("<article/>")

        cmd_status(karrc_args)

        with open(self.karrc_log_path, 'r') as f:
            karrc_data = json.load(f)
        self.assertEqual(karrc_data[str(self.karrc_xml_path)]['status_code'], 3)

    @patch('src.metafora_client.get_upload_log_path')
    @patch('src.metafora_client.requests.get')
    @patch('src.metafora_client.requests.put')
    def test_sign_uses_selected_source_article_uids(self, mock_put, mock_get, mock_get_log_path):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'data': {
                'file_uid': self.mgta_file_uid,
                'xml': {'status': {'code': 3, 'status_text': 'Processed'}},
                'articles': self.mgta_article_uids,
            }
        }

        mock_put.return_value.status_code = 200

        mock_get_log_path.side_effect = lambda source: (
            self.karrc_log_path if source == "karrc" else self.mgta_log_path
        )

        mgta_args = MagicMock()
        mgta_args.FILE_OR_UID = str(self.mgta_xml_path)
        mgta_args.verbose = False
        mgta_args.source = "mgta"

        with open(self.mgta_xml_path, 'w') as f:
            f.write("<article/>")

        cmd_sign(mgta_args)

        self.assertTrue(mock_put.called)
        call_args = mock_put.call_args_list
        self.assertEqual(len(call_args), 1)
        self.assertIn("art-mgta-001", str(call_args[0]))

    @patch('src.metafora_client.get_upload_log_path')
    @patch('src.metafora_client.requests.delete')
    def test_delete_affects_only_selected_source_log(self, mock_delete, mock_get_log_path):
        mock_delete.return_value.status_code = 204

        mock_get_log_path.side_effect = lambda source: (
            self.karrc_log_path if source == "karrc" else self.mgta_log_path
        )

        self.karrc_xml_path.write_text("<article karrc/>")
        self.mgta_xml_path.write_text("<article mgta/>")

        with open(self.mgta_log_path, 'r') as f:
            mgta_log_before = f.read()

        with open(self.karrc_log_path, 'r') as f:
            karrc_log_before = f.read()

        mgta_args = MagicMock()
        mgta_args.FILE_OR_UID = str(self.mgta_xml_path)
        mgta_args.verbose = False
        mgta_args.source = "mgta"

        cmd_delete(mgta_args)

        with open(self.mgta_log_path, 'r') as f:
            mgta_log_after = f.read()

        with open(self.karrc_log_path, 'r') as f:
            karrc_log_after = f.read()

        self.assertNotEqual(mgta_log_before, mgta_log_after)
        self.assertEqual(karrc_log_before, karrc_log_after)

    @patch('src.metafora_client.get_upload_log_path')
    def test_http_409_recovery_persists_only_to_selected_log(self, mock_get_log_path):
        karrc_log_data_before = json.loads(self.karrc_log_path.read_text())
        mgta_log_data_before = json.loads(self.mgta_log_path.read_text())

        mock_get_log_path.side_effect = lambda source: (
            self.karrc_log_path if source == "karrc" else self.mgta_log_path
        )

        response = MagicMock()
        response.status_code = 409
        response.reason = "Conflict"
        response.json.return_value = {
            'error': 'XML_ALREADY_EXISTS',
            'data': {
                'exists_file_uid': self.mgta_file_uid,
            }
        }

        mgta_args = MagicMock()
        mgta_args.no_wait = True
        mgta_args.sign = False
        mgta_args.verbose = False
        mgta_args.max_wait = 300
        mgta_args.poll_interval = 5
        mgta_args.source = "mgta"

        result = handle_upload_409(response, str(self.mgta_xml_path), self.mgta_log_path, {}, mgta_args)

        self.assertIsNotNone(result)
        self.assertEqual(result['file_uid'], self.mgta_file_uid)

        mgta_data_after = json.loads(self.mgta_log_path.read_text())
        karrc_data_after = json.loads(self.karrc_log_path.read_text())

        self.assertIn(str(self.mgta_xml_path), mgta_data_after)
        self.assertEqual(karrc_data_after, karrc_log_data_before)

    @patch('src.metafora_client.get_upload_log_path')
    @patch('src.metafora_client.resolve_batch_output_dir')
    @patch('src.metafora_client.load_log')
    def test_upload_all_uses_selected_source_log(self, mock_load_log, mock_resolve_dir, mock_get_log_path):
        mock_load_log.return_value = {}
        mock_resolve_dir.return_value = Path(self.tmpdir.name) / "mgta" / "2022"
        mock_get_log_path.side_effect = lambda source: (
            self.karrc_log_path if source == "karrc" else self.mgta_log_path
        )

        batch_dir = Path(self.tmpdir.name) / "mgta" / "2022"
        batch_dir.mkdir(parents=True)
        xml_file = batch_dir / "game_n1.xml"
        xml_file.write_text("<article/>")

        args = MagicMock()
        args.YEAR_OR_DIR = "2022"
        args.journal = None
        args.sign = False
        args.dry_run = True
        args.source = "mgta"
        args.verbose = False
        args.max_wait = 300
        args.poll_interval = 5

        result = cmd_upload_all(args)
        self.assertIsNone(result)

    @patch('src.metafora_client.get_upload_log_path')
    @patch('src.metafora_client.resolve_batch_output_dir')
    def test_sign_all_ignores_entries_from_other_source_logs(self, mock_resolve_dir, mock_get_log_path):
        mock_resolve_dir.return_value = Path(self.tmpdir.name) / "mgta" / "2022"
        mock_get_log_path.side_effect = lambda source: (
            self.karrc_log_path if source == "karrc" else self.mgta_log_path
        )

        batch_dir = Path(self.tmpdir.name) / "mgta" / "2022"
        batch_dir.mkdir(parents=True)
        xml_file = batch_dir / "game_n1.xml"
        xml_file.write_text("<article/>")

        mgta_log_data = {}
        karrc_log_data = {
            str(xml_file): {
                'file_uid': 'some-uid',
                'status_code': 3,
                'article_uids': ['art-001'],
            }
        }

        with patch('src.metafora_client.load_log', side_effect=lambda p: karrc_log_data if 'karrc' in str(p) else mgta_log_data):
            args = MagicMock()
            args.YEAR_OR_DIR = "2022"
            args.journal = None
            args.source = "mgta"
            args.verbose = False

            with patch('sys.stdout'):
                cmd_sign_all(args)

    @patch('src.metafora_client.get_upload_log_path')
    def test_explicit_directory_is_literal(self, mock_get_log_path):
        explicit_dir = Path(self.tmpdir.name) / "explicit"
        explicit_dir.mkdir()

        mock_get_log_path.side_effect = lambda source: (
            self.karrc_log_path if source == "karrc" else self.mgta_log_path
        )

        xml_file = explicit_dir / "test_n1.xml"
        xml_file.write_text("<article/>")

        args = MagicMock()
        args.YEAR_OR_DIR = str(explicit_dir)
        args.journal = None
        args.sign = False
        args.dry_run = True
        args.source = "mgta"
        args.verbose = False
        args.max_wait = 300
        args.poll_interval = 5

        result = cmd_upload_all(args)
        self.assertIsNone(result)


class TestLoadSaveLogFunctionality(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)

    def test_load_log_returns_empty_for_missing_file(self):
        log_path = Path(self.tmpdir.name) / "missing" / "upload_log.json"
        log_data = load_log(log_path)
        self.assertEqual(log_data, {})

    def test_load_log_returns_empty_dict_not_created_file(self):
        log_path = Path(self.tmpdir.name) / "new_dir" / "upload_log.json"
        self.assertFalse(log_path.parent.exists())
        log_data = load_log(log_path)
        self.assertEqual(log_data, {})
        self.assertFalse(log_path.exists())

    def test_save_log_creates_parent_directories(self):
        log_path = Path(self.tmpdir.name) / "new_dir" / "upload_log.json"
        log_data = {"test": "data"}
        save_log(log_path, log_data)
        self.assertTrue(log_path.parent.exists())
        self.assertTrue(log_path.exists())
        with open(log_path, 'r') as f:
            saved_data = json.load(f)
        self.assertEqual(saved_data, log_data)


if __name__ == '__main__':
    unittest.main()
