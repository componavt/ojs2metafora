import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests
from unittest.mock import MagicMock, patch, Mock

from src.metafora_client import (
    load_log,
    save_log,
    cmd_status,
    cmd_sign,
    cmd_delete,
    cmd_upload,
    cmd_upload_all,
    cmd_sign_all,
    cmd_check_doi,
    handle_upload_409,
    resolve_file_uid,
    get_upload_log_path,
    safe_request,
    sign_all,
    SignResult,
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
    @patch('src.metafora_client.requests.get')
    @patch('src.metafora_client.load_log')
    @patch('src.metafora_client.save_log')
    def test_status_raw_uid_bypasses_local_log(self, mock_save_log, mock_load_log, mock_get, mock_get_log_path):
        raw_uid = "00000000-0000-0000-0000-000000000000"
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'data': {
                'file_uid': raw_uid,
                'xml': {'status': {'code': 2, 'status_text': 'Uploaded'}},
                'pdf': {'uploaded': False},
                'articles': [],
            }
        }
        mock_load_log.return_value = {}

        temp_dir = tempfile.mkdtemp()
        self.addCleanup(lambda: Path(temp_dir).unlink(missing_ok=True) if Path(temp_dir).exists() else None)
        self.addCleanup(lambda: shutil.rmtree(temp_dir, ignore_errors=True))
        temp_log_path = Path(temp_dir) / "karrc" / "upload_log.json"

        mock_get_log_path.return_value = temp_log_path

        args = MagicMock()
        args.FILE_OR_UID = raw_uid
        args.verbose = False
        args.source = "karrc"

        cmd_status(args)

        self.assertTrue(mock_get.called)
        call_params = mock_get.call_args[1]['params']
        self.assertEqual(call_params['file_uid'], raw_uid)

        self.assertFalse(
            temp_log_path.exists(),
            "No log file should be created for raw UID status check"
        )
        self.assertFalse(
            mock_save_log.called,
            "save_log should not be called for raw UID status check with no file_path"
        )

    @patch('src.metafora_client.get_upload_log_path')
    @patch('src.metafora_client.requests.get')
    @patch('src.metafora_client.requests.put')
    @patch('src.metafora_client.load_log')
    @patch('src.metafora_client.save_log')
    def test_sign_raw_uid_bypasses_local_file_lookup(
            self, mock_save_log, mock_load_log, mock_put, mock_get, mock_get_log_path):
        raw_uid = "11111111-1111-1111-1111-111111111111"
        article_uid_1 = "art-a111-1111-1111-1111"
        article_uid_2 = "art-a222-1111-1111-1111"

        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'data': {
                'file_uid': raw_uid,
                'xml': {'status': {'code': 3, 'status_text': 'Processed'}},
                'articles': [article_uid_1, article_uid_2],
            }
        }
        mock_put.return_value.status_code = 200
        mock_load_log.return_value = {}

        temp_dir = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(temp_dir, ignore_errors=True))
        temp_log_path = Path(temp_dir) / "mgta" / "upload_log.json"

        mock_get_log_path.return_value = temp_log_path

        args = MagicMock()
        args.FILE_OR_UID = raw_uid
        args.verbose = False
        args.source = "mgta"

        cmd_sign(args)

        self.assertTrue(mock_put.called)
        self.assertEqual(mock_put.call_count, 2)
        called_uids = set()
        for call in mock_put.call_args_list:
            parts = call[0][0].split('/')
            called_uids.add(parts[-3])
        self.assertEqual(called_uids, {article_uid_1, article_uid_2})

        self.assertFalse(
            temp_log_path.exists(),
            "No log file should be created for raw UID sign operation"
        )
        self.assertFalse(
            mock_save_log.called,
            "save_log should not be called for raw UID sign operation"
        )

    @patch('src.metafora_client.get_upload_log_path')
    @patch('src.metafora_client.requests.delete')
    @patch('src.metafora_client.load_log')
    @patch('src.metafora_client.save_log')
    def test_delete_raw_uid_bypasses_local_file_lookup(self, mock_save_log, mock_load_log, mock_delete, mock_get_log_path):
        raw_uid = "22222222-2222-2222-2222-222222222222"

        mock_delete.return_value.status_code = 204
        mock_load_log.return_value = {}
        mock_save_log.return_value = None

        temp_dir = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(temp_dir, ignore_errors=True))
        temp_log_path = Path(temp_dir) / "karrc" / "upload_log.json"

        mock_get_log_path.return_value = temp_log_path

        args = MagicMock()
        args.FILE_OR_UID = raw_uid
        args.verbose = False
        args.source = "karrc"

        cmd_delete(args)

        self.assertTrue(mock_delete.called)
        delete_url = mock_delete.call_args[0][0]
        self.assertIn(raw_uid, delete_url)

        self.assertFalse(
            temp_log_path.exists(),
            "No log file should be created/modified for raw UID delete operation"
        )
        self.assertFalse(
            mock_save_log.called,
            "save_log should not be called for raw UID delete operation"
        )

    def test_existing_xml_without_log_entry_raises_error_before_http_call(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            xml_path = tmp_path / "mathem_n1.xml"
            xml_path.write_text("<article/>", encoding="utf-8")
            log_path = tmp_path / "karrc" / "upload_log.json"
            log_path.parent.mkdir(parents=True, exist_ok=True)

            log_data = {}

            with self.assertRaises(SystemExit) as cm:
                resolve_file_uid(str(xml_path), log_data, verbose=False)
            self.assertEqual(cm.exception.code, 1)

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


class TestRawFileUIDResolution(unittest.TestCase):
    """Tests for raw file UID handling (bypassing local upload log)."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)

    def test_resolve_file_uid_raw_uuid(self):
        raw_uid = "00000000-0000-0000-0000-000000000000"
        log_data = {}
        uid, file_path = resolve_file_uid(raw_uid, log_data, verbose=False)
        self.assertEqual(uid, raw_uid)
        self.assertIsNone(file_path)

    def test_resolve_file_uid_with_existing_xml_in_log(self):
        xml_path = Path(self.tmpdir.name) / "mathem_n1.xml"
        xml_path.write_text("<article/>", encoding="utf-8")
        normalized = str(xml_path.resolve())
        log_data = {normalized: {'file_uid': 'existing-uid', 'status_code': 3}}
        uid, file_path = resolve_file_uid(str(xml_path), log_data, verbose=False)
        self.assertEqual(uid, 'existing-uid')
        self.assertEqual(file_path, str(xml_path))

    def test_resolve_file_uid_with_existing_xml_no_log_entry_raises(self):
        xml_path = Path(self.tmpdir.name) / "mathem_n1.xml"
        xml_path.write_text("<article/>", encoding="utf-8")
        log_data = {}
        with self.assertRaises(SystemExit) as cm:
            resolve_file_uid(str(xml_path), log_data, verbose=False)
        self.assertEqual(cm.exception.code, 1)


class TestMetaforaClientSafeRequest(unittest.TestCase):
    """Tests for safe_request helper function."""

    @patch('src.metafora_client.requests.get')
    def test_safe_request_success(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "OK"
        mock_get.return_value = mock_response

        response, error = safe_request(
            requests.get, "https://example.com", headers={}, timeout=30
        )

        self.assertIsNotNone(response)
        self.assertIsNone(error)
        mock_get.assert_called_once()

    @patch('src.metafora_client.requests.get')
    def test_safe_request_connection_error(self, mock_get):
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection reset")

        response, error = safe_request(
            requests.get, "https://example.com", headers={}, timeout=30
        )

        self.assertIsNone(response)
        self.assertIsNotNone(error)
        self.assertIn("Connection reset", error)

    @patch('src.metafora_client.requests.get')
    def test_safe_request_timeout(self, mock_get):
        mock_get.side_effect = requests.exceptions.Timeout("Request timeout")

        response, error = safe_request(
            requests.get, "https://example.com", headers={}, timeout=30
        )

        self.assertIsNone(response)
        self.assertIsNotNone(error)
        self.assertIn("Request timeout", error)

    @patch('src.metafora_client.requests.get')
    def test_safe_request_non_request_exception_not_swallowed(self, mock_get):
        mock_get.side_effect = ValueError("Some value error")

        with self.assertRaises(ValueError) as cm:
            safe_request(
                requests.get, "https://example.com", headers={}, timeout=30
            )
        self.assertIn("Some value error", str(cm.exception))


class TestMetaforaClientSignAll(unittest.TestCase):
    """Tests for sign_all function with network resilience."""

    @patch('src.metafora_client.requests.put')
    def test_sign_all_network_failure_then_success(self, mock_put):
        from src.metafora_client import safe_request
        mock_put.side_effect = [
            requests.exceptions.ConnectionError("reset"),
            Mock(status_code=200),
        ]

        result = sign_all(
            "file-uid-123",
            ["art-001", "art-002"],
            verbose=False
        )

        self.assertEqual(result.attempted, 2)
        self.assertEqual(result.signed, 1)
        self.assertEqual(result.failed, 1)

    @patch('src.metafora_client.requests.put')
    def test_sign_all_http_409_counts_as_signed(self, mock_put):
        mock_response = Mock()
        mock_response.status_code = 409
        mock_response.text = "Conflict"
        mock_put.return_value = mock_response

        result = sign_all(
            "file-uid-123",
            ["art-001"],
            verbose=False
        )

        self.assertEqual(result.signed, 1)
        self.assertEqual(result.failed, 0)

    @patch('src.metafora_client.requests.put')
    def test_sign_all_unexpected_http_status_counts_as_failed(self, mock_put):
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.json.return_value = {'error': 'server_error'}
        mock_put.return_value = mock_response

        result = sign_all(
            "file-uid-123",
            ["art-001"],
            verbose=False
        )

        self.assertEqual(result.failed, 1)

    @patch('src.metafora_client.requests.put')
    def test_sign_all_no_real_network_used(self, mock_put):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "OK"
        mock_put.return_value = mock_response

        sign_all("file-uid-123", ["art-001"], verbose=False)

        self.assertTrue(mock_put.called)
        mock_put.assert_called_once()


class TestMetaforaClientCmdSignAll(unittest.TestCase):
    """Tests for cmd_sign_all with partial failure handling."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)

    @patch('src.metafora_client.load_log')
    @patch('src.metafora_client.get_upload_log_path')
    @patch('src.metafora_client.resolve_batch_output_dir')
    @patch('src.metafora_client.requests.put')
    def test_cmd_sign_all_partial_network_failure_continues(self, mock_put, mock_resolve_dir, mock_get_log_path, mock_load_log):
        tmpdir = Path(self.tmpdir.name)
        batch_dir = tmpdir / "mgta" / "2022"
        batch_dir.mkdir(parents=True)

        karrc_log_path = tmpdir / "karrc" / "upload_log.json"
        karrc_log_path.parent.mkdir(parents=True, exist_ok=True)
        mgta_log_path = tmpdir / "mgta" / "upload_log.json"
        mgta_log_path.parent.mkdir(parents=True, exist_ok=True)

        xml_file_1 = batch_dir / "mathem_n1.xml"
        xml_file_1.write_text("<article/>")
        xml_file_2 = batch_dir / "mathem_n2.xml"
        xml_file_2.write_text("<article/>")

        karrc_log_data = {
            str(xml_file_1.resolve()): {
                'file_uid': 'file-1',
                'status_code': 3,
                'article_uids': ['art-1', 'art-2'],
            },
            str(xml_file_2.resolve()): {
                'file_uid': 'file-2',
                'status_code': 3,
                'article_uids': ['art-3'],
            },
        }

        mock_resolve_dir.return_value = batch_dir
        mock_get_log_path.side_effect = lambda source: karrc_log_path

        def side_effect(path):
            if 'karrc' in str(path):
                return karrc_log_data
            return {}
        mock_load_log.side_effect = side_effect

        put_calls = [
            Mock(status_code=200),
            requests.exceptions.ConnectionError("network down"),
            Mock(status_code=200),
        ]
        mock_put.side_effect = put_calls

        args = MagicMock()
        args.YEAR_OR_DIR = "2022"
        args.journal = None
        args.source = "karrc"
        args.verbose = False

        with patch('sys.stdout'):
            with self.assertRaises(SystemExit) as cm:
                cmd_sign_all(args)
            self.assertEqual(cm.exception.code, 1)

    @patch('src.metafora_client.load_log')
    @patch('src.metafora_client.get_upload_log_path')
    @patch('src.metafora_client.resolve_batch_output_dir')
    @patch('src.metafora_client.requests.put')
    def test_cmd_sign_all_all_signed_succeeds(self, mock_put, mock_resolve_dir, mock_get_log_path, mock_load_log):
        tmpdir = Path(self.tmpdir.name)
        batch_dir = tmpdir / "mgta" / "2022"
        batch_dir.mkdir(parents=True)

        mgta_log_path = tmpdir / "mgta" / "upload_log.json"
        mgta_log_path.parent.mkdir(parents=True, exist_ok=True)

        xml_file = batch_dir / "mathem_n1.xml"
        xml_file.write_text("<article/>")

        log_data = {
            str(xml_file.resolve()): {
                'file_uid': 'file-uid',
                'status_code': 3,
                'article_uids': ['art-001'],
            }
        }

        mock_resolve_dir.return_value = batch_dir
        mock_get_log_path.return_value = mgta_log_path
        mock_load_log.return_value = log_data
        mock_put.return_value.status_code = 200

        args = MagicMock()
        args.YEAR_OR_DIR = "2022"
        args.journal = None
        args.source = "mgta"
        args.verbose = False

        with patch('sys.stdout'):
            cmd_sign_all(args)


class TestMetaforaClientNetworkFailure(unittest.TestCase):
    """Tests for network error handling in various commands."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)

    @patch('src.metafora_client.resolve_file_uid')
    @patch('src.metafora_client.requests.post')
    def test_cmd_upload_network_failure(self, mock_post, mock_resolve_file_uid):
        mock_resolve_file_uid.return_value = ("file-uid", None)
        mock_post.side_effect = requests.exceptions.ConnectionError("network down")

        args = MagicMock()
        args.FILE = "/tmp/test.xml"
        args.source = "karrc"
        args.verbose = False
        args.max_wait = 300
        args.poll_interval = 5
        args.sign = False
        args.no_wait = False

        with patch('builtins.open', MagicMock()):
            with self.assertRaises(SystemExit) as cm:
                cmd_upload(args)
            self.assertEqual(cm.exception.code, 1)

    @patch('src.metafora_client.resolve_file_uid')
    @patch('src.metafora_client.requests.get')
    def test_cmd_status_network_failure(self, mock_get, mock_resolve_file_uid):
        mock_resolve_file_uid.return_value = ("file-uid", None)
        mock_get.side_effect = requests.exceptions.ConnectionError("network down")

        args = MagicMock()
        args.FILE_OR_UID = "file-uid"
        args.source = "karrc"
        args.verbose = False

        with self.assertRaises(SystemExit) as cm:
            cmd_status(args)
            self.assertEqual(cm.exception.code, 1)

    @patch('src.metafora_client.resolve_file_uid')
    @patch('src.metafora_client.requests.delete')
    def test_cmd_delete_network_failure(self, mock_delete, mock_resolve_file_uid):
        mock_resolve_file_uid.return_value = ("file-uid", None)
        mock_delete.side_effect = requests.exceptions.ConnectionError("network down")

        args = MagicMock()
        args.FILE_OR_UID = "file-uid"
        args.source = "karrc"
        args.verbose = False

        with self.assertRaises(SystemExit) as cm:
            cmd_delete(args)
            self.assertEqual(cm.exception.code, 1)

    @patch('src.metafora_client.requests.get')
    def test_cmd_check_doi_network_failure(self, mock_get):
        mock_get.side_effect = requests.exceptions.ConnectionError("network down")

        args = MagicMock()
        args.DOI = "10.1234/test"

        with self.assertRaises(SystemExit) as cm:
            cmd_check_doi(args)
        self.assertEqual(cm.exception.code, 1)


class TestMetaforaClientBatchUploadContinuation(unittest.TestCase):
    """Tests for batch upload continuation after transport failures."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)

    @patch('src.metafora_client.resolve_batch_output_dir')
    @patch('src.metafora_client.get_upload_log_path')
    @patch('src.metafora_client.requests.post')
    @patch('src.metafora_client.poll_status')
    def test_cmd_upload_all_continues_after_network_failure(self, mock_poll, mock_post, mock_get_log_path, mock_resolve_dir):
        tmpdir = Path(self.tmpdir.name)
        batch_dir = tmpdir / "karrc" / "2022"
        batch_dir.mkdir(parents=True)

        log_path = tmpdir / "karrc" / "upload_log.json"
        log_path.parent.mkdir(parents=True, exist_ok=True)

        xml_file_1 = batch_dir / "mathem_n1.xml"
        xml_file_1.write_text("<article/>")

        mock_resolve_dir.return_value = batch_dir
        mock_get_log_path.return_value = log_path

        post_calls = []
        def side_effect(*args, **kwargs):
            post_calls.append(1)
            if len(post_calls) == 1:
                raise requests.exceptions.ConnectionError("network down")
            response = Mock(status_code=200)
            response.json.return_value = {'data': {'file_uid': 'file-uid-2'}}
            return response
        mock_post.side_effect = side_effect
        mock_poll.return_value = ['art-1', 'art-2']

        args = MagicMock()
        args.YEAR_OR_DIR = "2022"
        args.journal = None
        args.source = "karrc"
        args.verbose = False
        args.max_wait = 300
        args.poll_interval = 5
        args.sign = False
        args.dry_run = False

        with patch('sys.stdout'):
            with self.assertRaises(SystemExit) as cm:
                cmd_upload_all(args)
            self.assertEqual(cm.exception.code, 1)


if __name__ == '__main__':
    unittest.main()
