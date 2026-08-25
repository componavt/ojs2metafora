import unittest
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.adapters import get_adapter
from src.adapters.ojs31 import Ojs31Adapter


class TestGetAdapterMGTA(unittest.TestCase):

    def setUp(self):
        self.env_patcher = patch.dict(
            os.environ,
            {
                "MGTA_DBHOST": "localhost",
                "MGTA_DBUSER": "mgta_user",
                "MGTA_DBPASSWORD": "mgta_pass",
                "MGTA_DBNAME": "mgta_db",
                "MGTA_DBCHARSET": "utf8mb4",
            },
            clear=True,
        )
        self.env_patcher.start()

    def tearDown(self):
        self.env_patcher.stop()

    def test_get_adapter_mgta_returns_ojs31_adapter(self):
        result = get_adapter("mgta")
        self.assertIsInstance(result, Ojs31Adapter)
        self.assertEqual(result.source_key, "mgta")


class TestOjs31AdapterIssueArticleIds(unittest.TestCase):

    def setUp(self):
        self.env_patcher = patch.dict(
            os.environ,
            {
                "MGTA_DBHOST": "localhost",
                "MGTA_DBUSER": "mgta_user",
                "MGTA_DBPASSWORD": "mgta_pass",
                "MGTA_DBNAME": "mgta_db",
                "MGTA_DBCHARSET": "utf8mb4",
            },
            clear=True,
        )
        self.env_patcher.start()

    def tearDown(self):
        self.env_patcher.stop()

    @patch('src.adapters.ojs31.get_connection')
    def test_fetch_issue_article_ids(self, mock_get_conn):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.__enter__ = lambda x: mock_cursor
        mock_cursor.__exit__ = lambda x, y, z, w: None
        mock_get_conn.return_value = mock_conn
        mock_cursor.fetchall.return_value = [
            {'article_id': 42, 'seq': 1, 'section_id': 1},
            {'article_id': 43, 'seq': 2, 'section_id': 1},
        ]

        adapter = Ojs31Adapter("mgta")
        result = adapter.fetch_issue_article_ids(11)

        mock_get_conn.assert_called_once_with("mgta")
        mock_cursor.execute.assert_called_once()
        sql = mock_cursor.execute.call_args[0][0]
        self.assertIn('published_submissions', sql)
        self.assertIn('submission_id AS article_id', sql)
        self.assertEqual(len(result), 2)


class TestOjs31AdapterIssueMetadata(unittest.TestCase):

    def setUp(self):
        self.env_patcher = patch.dict(
            os.environ,
            {
                "MGTA_DBHOST": "localhost",
                "MGTA_DBUSER": "mgta_user",
                "MGTA_DBPASSWORD": "mgta_pass",
                "MGTA_DBNAME": "mgta_db",
                "MGTA_DBCHARSET": "utf8mb4",
            },
            clear=True,
        )
        self.env_patcher.start()

    def tearDown(self):
        self.env_patcher.stop()

    @patch('src.adapters.ojs31.get_connection')
    def test_fetch_issue_metadata(self, mock_get_conn):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.__enter__ = lambda x: mock_cursor
        mock_cursor.__exit__ = lambda x, y, z, w: None
        mock_get_conn.return_value = mock_conn

        mock_cursor.fetchone.side_effect = [
            {'issue_id': 11, 'journal_id': 1, 'volume': 14, 'number': 1, 'year': 2022, 'date_published': None},
            {'path': 'mgta'},
        ]

        mock_cursor.fetchall.return_value = [
            {'setting_name': 'printIssn', 'locale': '', 'setting_value': '2074-9872'},
            {'setting_name': 'onlineIssn', 'locale': '', 'setting_value': ''},
            {'setting_name': 'name', 'locale': 'ru_RU', 'setting_value': 'Test Ru'},
            {'setting_name': 'name', 'locale': 'en_US', 'setting_value': 'Test En'},
            {'setting_name': 'publisherInstitution', 'locale': '', 'setting_value': 'Publisher'},
        ]

        adapter = Ojs31Adapter("mgta")
        result = adapter.fetch_issue_metadata(11)

        expected_keys = {
            'issue_id', 'journal_id', 'volume', 'number', 'year', 'date_published',
            'print_issn', 'online_issn', 'title_ru', 'title_en', 'publisher', 'journal_path'
        }
        self.assertEqual(set(result.keys()), expected_keys)
        self.assertEqual(result['print_issn'], '2074-9872')


class TestOjs31AdapterSectionTitles(unittest.TestCase):

    def setUp(self):
        self.env_patcher = patch.dict(
            os.environ,
            {
                "MGTA_DBHOST": "localhost",
                "MGTA_DBUSER": "mgta_user",
                "MGTA_DBPASSWORD": "mgta_pass",
                "MGTA_DBNAME": "mgta_db",
                "MGTA_DBCHARSET": "utf8mb4",
            },
            clear=True,
        )
        self.env_patcher.start()

    def tearDown(self):
        self.env_patcher.stop()

    @patch('src.adapters.ojs31.get_connection')
    def test_get_section_titles_empty_en(self, mock_get_conn):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.__enter__ = lambda x: mock_cursor
        mock_cursor.__exit__ = lambda x, y, z, w: None
        mock_get_conn.return_value = mock_conn
        mock_cursor.fetchall.return_value = [
            {'setting_name': 'title', 'locale': 'ru_RU', 'setting_value': 'Section Ru'},
        ]

        adapter = Ojs31Adapter("mgta")
        result = adapter.get_section_titles(1)

        self.assertEqual(result['title_ru'], 'Section Ru')
        self.assertEqual(result['title_en'], '')

    @patch('src.adapters.ojs31.get_connection')
    def test_get_section_titles_both(self, mock_get_conn):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.__enter__ = lambda x: mock_cursor
        mock_cursor.__exit__ = lambda x, y, z, w: None
        mock_get_conn.return_value = mock_conn
        mock_cursor.fetchall.return_value = [
            {'setting_name': 'title', 'locale': 'ru_RU', 'setting_value': 'Section Ru'},
            {'setting_name': 'title', 'locale': 'en_US', 'setting_value': 'Section En'},
        ]

        adapter = Ojs31Adapter("mgta")
        result = adapter.get_section_titles(50)

        self.assertEqual(result['title_ru'], 'Section Ru')
        self.assertEqual(result['title_en'], 'Section En')


if __name__ == '__main__':
    unittest.main()
