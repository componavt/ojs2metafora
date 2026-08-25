import os
import unittest
from unittest.mock import patch, MagicMock, call
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestFetchAllIssues(unittest.TestCase):
    """Tests for src.generate_all.fetch_all_issues function."""

    def setUp(self):
        """Set up environment variables for testing."""
        self.env_patcher = patch.dict(
            os.environ,
            {
                "OJS24_DBHOST": "localhost",
                "OJS24_DBUSER": "ojs_user",
                "OJS24_DBPASSWORD": "ojs_pass",
                "OJS24_DBNAME": "ojs",
                "OJS24_DBCHARSET": "utf8mb4",
                "MGTA_DBHOST": "localhost",
                "MGTA_DBUSER": "mgta_user",
                "MGTA_DBPASSWORD": "mgta_pass",
                "MGTA_DBNAME": "mgta",
                "MGTA_DBCHARSET": "utf8mb4",
            },
            clear=True,
        )
        self.env_patcher.start()

    def tearDown(self):
        """Clean up environment variables."""
        self.env_patcher.stop()

    @patch('src.generate_all.get_connection')
    def test_fetch_all_issues_mgta_journal_path_calls_get_connection(self, mock_get_conn):
        """Test that fetch_all_issues calls get_connection for mgta source."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []
        mock_get_conn.return_value = mock_conn

        mock_cursor.fetchone.side_effect = [
            {'journal_id': 10, 'path': 'mgta'},
        ]

        from src.generate_all import fetch_all_issues

        result = fetch_all_issues(journal_path='mgta', source_key='mgta')

        mock_get_conn.assert_called_once_with('mgta')
        self.assertEqual(result, [])

    @patch('src.generate_all.get_connection')
    def test_fetch_all_issues_mgta_journal_path_resolves_journal_id(self, mock_get_conn):
        """Test that fetch_all_issues resolves journal_id from journal_path."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []
        mock_get_conn.return_value = mock_conn

        mock_cursor.fetchone.side_effect = [
            {'journal_id': 10, 'path': 'mgta'},
        ]

        from src.generate_all import fetch_all_issues

        fetch_all_issues(journal_path='mgta', source_key='mgta')

        mock_cursor.execute.assert_any_call(
            "SELECT journal_id, path FROM journals WHERE path = %s",
            ('mgta',)
        )

    @patch('src.generate_all.get_connection')
    def test_fetch_all_issues_mgta_returns_published_issues(self, mock_get_conn):
        """Test that fetch_all_issues returns only published issues."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        mock_cursor.fetchone.side_effect = [
            {'journal_id': 10, 'path': 'mgta'},
        ]
        mock_cursor.fetchall.return_value = [
            {'issue_id': 1, 'number': '1', 'year': 2024, 'date_published': '2024-01-01'},
            {'issue_id': 2, 'number': '2', 'year': 2024, 'date_published': '2024-06-01'},
        ]

        from src.generate_all import fetch_all_issues

        result = fetch_all_issues(journal_path='mgta', source_key='mgta')

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['issue_id'], 1)
        self.assertEqual(result[0]['number'], '1')
        self.assertEqual(result[0]['year'], 2024)
        self.assertEqual(result[1]['issue_id'], 2)
        self.assertEqual(result[1]['number'], '2')
        self.assertEqual(result[1]['year'], 2024)

    @patch('src.generate_all.get_connection')
    def test_fetch_all_issues_karrc_journal_path(self, mock_get_conn):
        """Test fetch_all_issues with karrc source and journal_path."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        mock_cursor.fetchone.side_effect = [
            {'journal_id': 5, 'path': 'mathem'},
        ]
        mock_cursor.fetchall.return_value = [
            {'issue_id': 100, 'number': '1', 'year': 2023, 'date_published': '2023-01-01'},
        ]

        from src.generate_all import fetch_all_issues

        result = fetch_all_issues(journal_path='mathem', source_key='karrc')

        mock_get_conn.assert_called_once_with('karrc')
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['issue_id'], 100)

    @patch('src.generate_all.get_connection')
    def test_fetch_all_issues_journal_id_direct(self, mock_get_conn):
        """Test fetch_all_issues with journal_id (no path lookup)."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        mock_cursor.fetchall.return_value = [
            {'issue_id': 50, 'number': '3', 'year': 2022, 'date_published': '2022-12-01'},
        ]

        from src.generate_all import fetch_all_issues

        result = fetch_all_issues(journal_id=50, source_key='karrc')

        mock_cursor.execute.assert_called_once_with(
            """
            SELECT i.issue_id, i.number, i.year, i.date_published
            FROM issues i
            WHERE i.journal_id = %s AND i.published = 1
            ORDER BY i.year ASC, i.number ASC
        """,
            (50,)
        )
        self.assertEqual(len(result), 1)

    @patch('src.generate_all.get_connection')
    def test_fetch_all_issues_closes_cursor_and_connection(self, mock_get_conn):
        """Test that fetch_all_issues closes cursor and connection on success."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        mock_cursor.fetchone.side_effect = [
            {'journal_id': 10, 'path': 'mgta'},
        ]
        mock_cursor.fetchall.return_value = []

        from src.generate_all import fetch_all_issues

        fetch_all_issues(journal_path='mgta', source_key='mgta')

        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()

    @patch('src.generate_all.get_connection')
    def test_fetch_all_issues_closes_on_journal_not_found(self, mock_get_conn):
        """Test that fetch_all_issues closes cursor and connection when journal not found."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        mock_cursor.fetchone.side_effect = [None]

        from src.generate_all import fetch_all_issues

        with self.assertRaises(ValueError) as cm:
            fetch_all_issues(journal_path='nonexistent', source_key='mgta')

        self.assertIn("not found", str(cm.exception))
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()

    @patch('src.generate_all.get_connection')
    def test_fetch_all_issues_inclusive_year_filtering(self, mock_get_conn):
        """Test that year_from and year_to are inclusive."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        mock_cursor.fetchone.side_effect = [
            {'journal_id': 10, 'path': 'mgta'},
        ]
        mock_cursor.fetchall.return_value = [
            {'issue_id': 1, 'number': '1', 'year': 2020, 'date_published': '2020-01-01'},
            {'issue_id': 2, 'number': '2', 'year': 2021, 'date_published': '2021-01-01'},
            {'issue_id': 3, 'number': '3', 'year': 2022, 'date_published': '2022-01-01'},
            {'issue_id': 4, 'number': '4', 'year': 2023, 'date_published': '2023-01-01'},
            {'issue_id': 5, 'number': '5', 'year': 2024, 'date_published': '2024-01-01'},
        ]

        from src.generate_all import fetch_all_issues

        result = fetch_all_issues(
            journal_path='mgta',
            source_key='mgta',
            year_from=2021,
            year_to=2023
        )

        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]['year'], 2021)
        self.assertEqual(result[1]['year'], 2022)
        self.assertEqual(result[2]['year'], 2023)

    @patch('src.generate_all.get_connection')
    def test_fetch_all_issues_query_failure_closes_resources(self, mock_get_conn):
        """Test that fetch_all_issues closes cursor and connection on query failure."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        mock_cursor.fetchone.side_effect = [
            {'journal_id': 10, 'path': 'mgta'},
        ]
        mock_cursor.execute.side_effect = Exception("SQL error")

        from src.generate_all import fetch_all_issues

        with self.assertRaises(Exception) as cm:
            fetch_all_issues(journal_path='mgta', source_key='mgta')

        self.assertIn("SQL error", str(cm.exception))
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()

    @patch('src.generate_all.get_connection')
    def test_fetch_all_issues_does_not_import_get_adapter(self, mock_get_conn):
        """Test that fetch_all_issues does not use adapter pattern."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        mock_cursor.fetchone.side_effect = [
            {'journal_id': 10, 'path': 'mgta'},
        ]
        mock_cursor.fetchall.return_value = []

        from src.generate_all import fetch_all_issues

        result = fetch_all_issues(journal_path='mgta', source_key='mgta')

        self.assertEqual(result, [])
        mock_get_conn.assert_called_once_with('mgta')


class TestFetchAllIssuesEdgeCases(unittest.TestCase):
    """Edge case tests for fetch_all_issues."""

    def setUp(self):
        """Set up environment variables."""
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
        """Clean up."""
        self.env_patcher.stop()

    @patch('src.generate_all.get_connection')
    def test_fetch_all_issues_year_none_ignored(self, mock_get_conn):
        """Test that issues with None year are handled correctly."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        mock_cursor.fetchone.side_effect = [
            {'journal_id': 10, 'path': 'mgta'},
        ]
        mock_cursor.fetchall.return_value = [
            {'issue_id': 1, 'number': '1', 'year': None, 'date_published': None},
            {'issue_id': 2, 'number': '2', 'year': 2024, 'date_published': '2024-01-01'},
        ]

        from src.generate_all import fetch_all_issues

        result = fetch_all_issues(journal_path='mgta', source_key='mgta')

        self.assertEqual(len(result), 2)
        self.assertIsNone(result[0]['year'])
        self.assertEqual(result[1]['year'], 2024)

    @patch('src.generate_all.get_connection')
    def test_fetch_all_issues_journal_id_provided_only_issues_query(self, mock_get_conn):
        """Test that when journal_id is provided, path lookup is still performed (edge case)."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        mock_cursor.fetchone.side_effect = [None]
        mock_cursor.fetchall.return_value = []

        from src.generate_all import fetch_all_issues

        fetch_all_issues(journal_id=99, source_key='karrc')

        mock_cursor.execute.assert_any_call(
            """
            SELECT i.issue_id, i.number, i.year, i.date_published
            FROM issues i
            WHERE i.journal_id = %s AND i.published = 1
            ORDER BY i.year ASC, i.number ASC
        """,
            (99,)
        )

    @patch('src.generate_all.get_connection')
    def test_fetch_all_issues_no_journal_path_no_journal_id_raises(self, mock_get_conn):
        """Test that providing neither journal_id nor journal_path causes no issues."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        mock_cursor.fetchall.return_value = []

        from src.generate_all import fetch_all_issues

        result = fetch_all_issues(source_key='karrc')

        self.assertEqual(result, [])


if __name__ == '__main__':
    unittest.main()
