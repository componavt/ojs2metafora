import unittest
import subprocess
import sys
import os
from unittest.mock import patch, MagicMock, call

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.fetch_article import fetch_article_metadata
from src.issue_builder import (
    fetch_issue_article_ids,
    fetch_issue_metadata,
    get_section_titles,
    build_journal_xml,
)
from src.generate_all import fetch_all_issues
from src.adapters import get_adapter


class TestSourcePropagation(unittest.TestCase):

    def test_fetch_article_metadata_default_source(self):
        with patch('src.fetch_article.get_adapter') as mock_get_adapter:
            mock_adapter = MagicMock()
            mock_get_adapter.return_value = mock_adapter
            mock_adapter.fetch_article_metadata.return_value = None

            fetch_article_metadata(123)

            mock_get_adapter.assert_called_once_with("karrc")

    def test_fetch_article_metadata_explicit_mgta(self):
        with patch('src.fetch_article.get_adapter') as mock_get_adapter:
            mock_adapter = MagicMock()
            mock_get_adapter.return_value = mock_adapter
            mock_adapter.fetch_article_metadata.return_value = None

            fetch_article_metadata(123, source_key="mgta")

            mock_get_adapter.assert_called_once_with("mgta")

    def test_fetch_issue_article_ids_passes_source_key(self):
        with patch('src.issue_builder.get_adapter') as mock_get_adapter:
            mock_adapter = MagicMock()
            mock_get_adapter.return_value = mock_adapter
            mock_adapter.fetch_issue_article_ids.return_value = []

            fetch_issue_article_ids(100, source_key="mgta")

            mock_get_adapter.assert_called_once_with("mgta")

    def test_fetch_issue_metadata_passes_source_key(self):
        with patch('src.issue_builder.get_adapter') as mock_get_adapter:
            mock_adapter = MagicMock()
            mock_get_adapter.return_value = mock_adapter
            mock_adapter.fetch_issue_metadata.return_value = {
                'issue_id': 100, 'journal_id': 1, 'volume': 1, 'number': 1,
                'year': 2024, 'date_published': None, 'print_issn': '', 'online_issn': '',
                'title_ru': '', 'title_en': '', 'publisher': '', 'journal_path': ''
            }

            fetch_issue_metadata(100, source_key="mgta")

            mock_get_adapter.assert_called_once_with("mgta")

    def test_get_section_titles_passes_source_key(self):
        with patch('src.issue_builder.get_adapter') as mock_get_adapter:
            mock_adapter = MagicMock()
            mock_get_adapter.return_value = mock_adapter
            mock_adapter.get_section_titles.return_value = {'title_ru': '', 'title_en': ''}

            get_section_titles(50, source_key="mgta")

            mock_get_adapter.assert_called_once_with("mgta")

    def test_build_journal_xml_propagates_source_key(self):
        mock_fetch_issue_metadata = MagicMock(return_value={
            'issue_id': 100,
            'journal_id': 1,
            'volume': '1',
            'number': '1',
            'year': '2024',
            'date_published': None,
            'print_issn': '1234-5678',
            'online_issn': '8765-4321',
            'title_ru': 'Test Journal Ru',
            'title_en': 'Test Journal En',
            'publisher': 'Test Publisher',
            'journal_path': 'test',
        })
        mock_fetch_issue_article_ids = MagicMock(return_value=[
            {'article_id': 200, 'seq': 1, 'section_id': 10},
        ])
        mock_fetch_article_metadata = MagicMock(return_value={
            'article_id': 200,
            'article': {
                'article_id': 200,
                'journal_id': 1,
                'section_id': 10,
                'language': 'ru',
                'pages': '5-10',
                'status': 3,
            },
            'journal': {'path': 'test'},
            'journal_settings': [],
            'section': {'section_id': 10},
            'section_settings': [],
            'article_settings': [],
            'authors': [],
            'author_settings': [],
            'citations': [],
            'issue': {'year': '2024', 'volume': '1', 'number': '1'},
        })
        mock_get_section_titles = MagicMock(return_value={
            'title_ru': 'Section Ru',
            'title_en': 'Section En',
        })

        with patch('src.issue_builder.fetch_issue_metadata', mock_fetch_issue_metadata), \
             patch('src.issue_builder.fetch_issue_article_ids', mock_fetch_issue_article_ids), \
             patch('src.issue_builder.fetch_article_metadata', mock_fetch_article_metadata), \
             patch('src.issue_builder.get_section_titles', mock_get_section_titles):

            build_journal_xml(100, source_key="mgta")

        mock_fetch_issue_metadata.assert_called_once_with(100, source_key="mgta")
        mock_fetch_issue_article_ids.assert_called_once_with(100, source_key="mgta")
        mock_fetch_article_metadata.assert_called_once_with(200, source_key="mgta")
        mock_get_section_titles.assert_called_once_with(10, source_key="mgta")

    def test_fetch_all_issues_passes_source_key(self):
        with patch('src.generate_all.get_connection') as mock_get_conn:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_get_conn.return_value = mock_conn

            mock_cursor.fetchone.side_effect = [
                None
            ]
            mock_cursor.fetchall.return_value = []

            fetch_all_issues(journal_id=1, source_key="mgta")

            mock_get_conn.assert_called_once_with("mgta")


class TestCLISourceOption(unittest.TestCase):

    def test_main_py_source_help(self):
        result = subprocess.run(
            [sys.executable, "src/main.py", "--help"],
            capture_output=True,
            text=True,
            cwd="/data/all/projects/git/ojs2metafora"
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("--source", result.stdout)

    def test_main_py_invalid_source(self):
        result = subprocess.run(
            [sys.executable, "src/main.py", "151", "--source", "nonexistent"],
            capture_output=True,
            text=True,
            cwd="/data/all/projects/git/ojs2metafora"
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid choice", result.stderr)

    def test_generate_all_py_source_help(self):
        result = subprocess.run(
            [sys.executable, "src/generate_all.py", "--help"],
            capture_output=True,
            text=True,
            cwd="/data/all/projects/git/ojs2metafora"
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("--source", result.stdout)

    def test_generate_all_py_invalid_source(self):
        result = subprocess.run(
            [sys.executable, "src/generate_all.py", "--source", "nonexistent"],
            capture_output=True,
            text=True,
            cwd="/data/all/projects/git/ojs2metafora"
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid choice", result.stderr)

    def test_fetch_article_py_source_help(self):
        result = subprocess.run(
            [sys.executable, "src/fetch_article.py", "--help"],
            capture_output=True,
            text=True,
            cwd="/data/all/projects/git/ojs2metafora"
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("--source", result.stdout)

    def test_fetch_article_py_invalid_source(self):
        result = subprocess.run(
            [sys.executable, "src/fetch_article.py", "123", "--source", "nonexistent"],
            capture_output=True,
            text=True,
            cwd="/data/all/projects/git/ojs2metafora"
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid choice", result.stderr)

    def test_explore_db_py_source_help(self):
        result = subprocess.run(
            [sys.executable, "src/explore_db.py", "--help"],
            capture_output=True,
            text=True,
            cwd="/data/all/projects/git/ojs2metafora"
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("--source", result.stdout)

    def test_explore_db_py_invalid_source(self):
        result = subprocess.run(
            [sys.executable, "src/explore_db.py", "--source", "nonexistent"],
            capture_output=True,
            text=True,
            cwd="/data/all/projects/git/ojs2metafora"
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid choice", result.stderr)


if __name__ == '__main__':
    unittest.main()
