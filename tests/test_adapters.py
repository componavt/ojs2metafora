import unittest
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.adapters import get_adapter
from src.adapters.base import OjsAdapter
from src.adapters.ojs24 import Ojs24Adapter


class TestGetAdapter(unittest.TestCase):

    def test_get_adapter_karrc_returns_ojs24_adapter(self):
        result = get_adapter("karrc")
        self.assertIsInstance(result, Ojs24Adapter)
        self.assertEqual(result.source_key, "karrc")

    def test_get_adapter_mgta_raises_not_implemented(self):
        with self.assertRaises(NotImplementedError) as cm:
            get_adapter("mgta")
        self.assertIn("mgta", str(cm.exception))
        self.assertIn("OJS 3.1", str(cm.exception))

    def test_get_adapter_unknown_source_raises_valueerror(self):
        with self.assertRaises(ValueError) as cm:
            get_adapter("unknown_source")
        self.assertIn("unknown_source", str(cm.exception))
        self.assertIn("karrc", str(cm.exception))
        self.assertIn("mgta", str(cm.exception))


class TestOjs24Adapter(unittest.TestCase):

    def setUp(self):
        self.env_patcher = patch.dict(
            os.environ,
            {
                "OJS24_DBHOST": "localhost",
                "OJS24_DBUSER": "ojs_user",
                "OJS24_DBPASSWORD": "ojs_pass",
                "OJS24_DBNAME": "ojs",
                "OJS24_DBCHARSET": "utf8mb4",
            },
            clear=True,
        )
        self.env_patcher.start()

    def tearDown(self):
        self.env_patcher.stop()

    @patch('src.adapters.ojs24.get_connection')
    def test_fetch_issue_article_ids_calls_get_connection_and_query(self, mock_get_conn):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = lambda x: mock_cursor
        mock_conn.cursor.return_value.__exit__ = lambda x, y, z, w: None
        mock_get_conn.return_value = mock_conn
        mock_cursor.fetchall.return_value = [
            {'article_id': 1, 'seq': 1, 'section_id': 10},
            {'article_id': 2, 'seq': 2, 'section_id': 10},
        ]

        adapter = Ojs24Adapter("karrc")
        result = adapter.fetch_issue_article_ids(100)

        mock_get_conn.assert_called_once_with("karrc")
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['article_id'], 1)
        self.assertEqual(result[1]['article_id'], 2)

    @patch('src.adapters.ojs24.get_connection')
    def test_fetch_issue_metadata_returns_expected_keys(self, mock_get_conn):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = lambda x: mock_cursor
        mock_conn.cursor.return_value.__exit__ = lambda x, y, z, w: None
        mock_get_conn.return_value = mock_conn

        mock_cursor.fetchone.side_effect = [
            {'issue_id': 100, 'journal_id': 1, 'volume': 5, 'number': 2, 'year': 2024, 'date_published': None},
            {'path': 'test-journal'},
        ]

        mock_cursor.fetchall.side_effect = [
            [
                {'setting_name': 'printIssn', 'locale': '', 'setting_value': '1234-5678'},
                {'setting_name': 'onlineIssn', 'locale': '', 'setting_value': '8765-4321'},
                {'setting_name': 'name', 'locale': 'ru_RU', 'setting_value': 'Test Journal Ru'},
                {'setting_name': 'name', 'locale': 'en_US', 'setting_value': 'Test Journal En'},
                {'setting_name': 'publisherInstitution', 'locale': '', 'setting_value': 'Test Publisher'},
            ],
        ]

        adapter = Ojs24Adapter("karrc")
        result = adapter.fetch_issue_metadata(100)

        mock_get_conn.assert_called_once_with("karrc")
        expected_keys = {
            'issue_id', 'journal_id', 'volume', 'number', 'year', 'date_published',
            'print_issn', 'online_issn', 'title_ru', 'title_en', 'publisher', 'journal_path'
        }
        self.assertEqual(set(result.keys()), expected_keys)
        self.assertEqual(result['print_issn'], '1234-5678')
        self.assertEqual(result['online_issn'], '8765-4321')
        self.assertEqual(result['title_ru'], 'Test Journal Ru')
        self.assertEqual(result['title_en'], 'Test Journal En')
        self.assertEqual(result['publisher'], 'Test Publisher')
        self.assertEqual(result['journal_path'], 'test-journal')

    @patch('src.adapters.ojs24.get_connection')
    def test_fetch_article_metadata_calls_get_connection(self, mock_get_conn):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = lambda x: mock_cursor
        mock_conn.cursor.return_value.__exit__ = lambda x, y, z, w: None
        mock_get_conn.return_value = mock_conn

        mock_cursor.fetchone.side_effect = [
            {'article_id': 2099, 'locale': 'ru_RU', 'journal_id': 1, 'section_id': 10, 'language': 'ru',
             'pages': '5-10', 'date_submitted': '2024-01-01', 'last_modified': '2024-01-15', 'status': 3, 'citations': 0},
            {'published_article_id': 1, 'issue_id': 100, 'date_published': '2024-01-01', 'seq': 1},
            {'issue_id': 100, 'journal_id': 1, 'volume': 5, 'number': 2, 'year': 2024, 'date_published': None},
            [],
            {'journal_id': 1, 'path': 'mathem', 'primary_locale': 'ru_RU', 'enabled': 1},
            [],
            {'section_id': 10, 'journal_id': 1, 'seq': 1, 'hide_title': 0},
            [],
            [],
            [],
            [],
            [],
        ]

        adapter = Ojs24Adapter("karrc")
        result = adapter.fetch_article_metadata(2099)

        mock_get_conn.assert_called_once_with("karrc")
        self.assertIsNotNone(result)
        self.assertEqual(result['article_id'], 2099)

    @patch('src.adapters.ojs24.get_connection')
    def test_get_section_titles_calls_get_connection_and_query(self, mock_get_conn):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = lambda x: mock_cursor
        mock_conn.cursor.return_value.__exit__ = lambda x, y, z, w: None
        mock_get_conn.return_value = mock_conn
        mock_cursor.fetchall.return_value = [
            {'setting_name': 'title', 'locale': 'ru_RU', 'setting_value': 'Section Ru'},
            {'setting_name': 'title', 'locale': 'en_US', 'setting_value': 'Section En'},
        ]

        adapter = Ojs24Adapter("karrc")
        result = adapter.get_section_titles(50)

        mock_get_conn.assert_called_once_with("karrc")
        self.assertEqual(result['title_ru'], 'Section Ru')
        self.assertEqual(result['title_en'], 'Section En')


class TestFacadeDelegation(unittest.TestCase):

    def setUp(self):
        self.env_patcher = patch.dict(
            os.environ,
            {
                "OJS24_DBHOST": "localhost",
                "OJS24_DBUSER": "ojs_user",
                "OJS24_DBPASSWORD": "ojs_pass",
                "OJS24_DBNAME": "ojs",
                "OJS24_DBCHARSET": "utf8mb4",
            },
            clear=True,
        )
        self.env_patcher.start()

    def tearDown(self):
        self.env_patcher.stop()

    @patch('src.fetch_article.get_adapter')
    def test_fetch_article_metadata_delegates_to_adapter(self, mock_get_adapter):
        mock_adapter = MagicMock()
        mock_get_adapter.return_value = mock_adapter
        mock_adapter.fetch_article_metadata.return_value = {'article_id': 123}

        from src.fetch_article import fetch_article_metadata
        result = fetch_article_metadata(123, source_key="karrc")

        mock_get_adapter.assert_called_once_with("karrc")
        mock_adapter.fetch_article_metadata.assert_called_once_with(123)
        self.assertEqual(result, {'article_id': 123})

    @patch('src.issue_builder.get_adapter')
    def test_fetch_issue_article_ids_delegates_to_adapter(self, mock_get_adapter):
        mock_adapter = MagicMock()
        mock_get_adapter.return_value = mock_adapter
        mock_adapter.fetch_issue_article_ids.return_value = []

        from src.issue_builder import fetch_issue_article_ids
        result = fetch_issue_article_ids(100, source_key="karrc")

        mock_get_adapter.assert_called_once_with("karrc")
        mock_adapter.fetch_issue_article_ids.assert_called_once_with(100)
        self.assertEqual(result, [])

    @patch('src.issue_builder.get_adapter')
    def test_fetch_issue_metadata_delegates_to_adapter(self, mock_get_adapter):
        mock_adapter = MagicMock()
        mock_get_adapter.return_value = mock_adapter
        mock_adapter.fetch_issue_metadata.return_value = {'issue_id': 100}

        from src.issue_builder import fetch_issue_metadata
        result = fetch_issue_metadata(100, source_key="karrc")

        mock_get_adapter.assert_called_once_with("karrc")
        mock_adapter.fetch_issue_metadata.assert_called_once_with(100)
        self.assertEqual(result, {'issue_id': 100})

    @patch('src.issue_builder.get_adapter')
    def test_get_section_titles_delegates_to_adapter(self, mock_get_adapter):
        mock_adapter = MagicMock()
        mock_get_adapter.return_value = mock_adapter
        mock_adapter.get_section_titles.return_value = {'title_ru': 'Ru', 'title_en': 'En'}

        from src.issue_builder import get_section_titles
        result = get_section_titles(50, source_key="karrc")

        mock_get_adapter.assert_called_once_with("karrc")
        mock_adapter.get_section_titles.assert_called_once_with(50)
        self.assertEqual(result, {'title_ru': 'Ru', 'title_en': 'En'})


if __name__ == '__main__':
    unittest.main()
