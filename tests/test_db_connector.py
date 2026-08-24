import os
import unittest
from unittest.mock import patch, MagicMock

from src.db_connector import get_connection


class TestGetConnection(unittest.TestCase):
    """Tests for get_connection function."""

    def setUp(self):
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
        self.connect_patcher = patch("src.db_connector.pymysql.connect")
        self.mock_connect = self.connect_patcher.start()

    def tearDown(self):
        self.env_patcher.stop()
        self.connect_patcher.stop()

    def test_get_connection_karrc_calls_connect_with_ojs24_values(self):
        result = get_connection("karrc")
        self.mock_connect.assert_called_once()
        call_kwargs = self.mock_connect.call_args.kwargs
        self.assertEqual(call_kwargs["host"], "localhost")
        self.assertEqual(call_kwargs["user"], "ojs_user")
        self.assertEqual(call_kwargs["password"], "ojs_pass")
        self.assertEqual(call_kwargs["database"], "ojs")
        self.assertEqual(call_kwargs["charset"], "utf8mb4")
        self.assertEqual(call_kwargs["cursorclass"], __import__("pymysql").cursors.DictCursor)
        self.assertEqual(result, self.mock_connect.return_value)

    def test_get_connection_mgta_calls_connect_with_mgta_values(self):
        result = get_connection("mgta")
        self.mock_connect.assert_called_once()
        call_kwargs = self.mock_connect.call_args.kwargs
        self.assertEqual(call_kwargs["host"], "localhost")
        self.assertEqual(call_kwargs["user"], "mgta_user")
        self.assertEqual(call_kwargs["password"], "mgta_pass")
        self.assertEqual(call_kwargs["database"], "mgta")
        self.assertEqual(call_kwargs["charset"], "utf8mb4")
        self.assertEqual(call_kwargs["cursorclass"], __import__("pymysql").cursors.DictCursor)
        self.assertEqual(result, self.mock_connect.return_value)

    def test_get_connection_default_uses_karrc(self):
        result = get_connection()
        self.mock_connect.assert_called_once()
        call_kwargs = self.mock_connect.call_args.kwargs
        self.assertEqual(call_kwargs["host"], "localhost")
        self.assertEqual(call_kwargs["user"], "ojs_user")
        self.assertEqual(call_kwargs["password"], "ojs_pass")
        self.assertEqual(call_kwargs["database"], "ojs")
        self.assertEqual(call_kwargs["charset"], "utf8mb4")

    def test_get_connection_blank_charset_fallbacks_to_utf8mb4(self):
        os.environ["OJS24_DBCHARSET"] = ""
        result = get_connection("karrc")
        self.mock_connect.assert_called_once()
        call_kwargs = self.mock_connect.call_args.kwargs
        self.assertEqual(call_kwargs["charset"], "utf8mb4")

    def test_get_connection_missing_dbhost_raises_valueerror(self):
        del os.environ["OJS24_DBHOST"]
        with self.assertRaises(ValueError) as cm:
            get_connection("karrc")
        self.assertIn("OJS24_DBHOST", str(cm.exception))
        self.mock_connect.assert_not_called()

    def test_get_connection_missing_dbuser_raises_valueerror(self):
        del os.environ["OJS24_DBUSER"]
        with self.assertRaises(ValueError) as cm:
            get_connection("karrc")
        self.assertIn("OJS24_DBUSER", str(cm.exception))
        self.mock_connect.assert_not_called()

    def test_get_connection_missing_dbname_raises_valueerror(self):
        del os.environ["OJS24_DBNAME"]
        with self.assertRaises(ValueError) as cm:
            get_connection("karrc")
        self.assertIn("OJS24_DBNAME", str(cm.exception))
        self.mock_connect.assert_not_called()

    def test_get_connection_unknown_source_key_raises_valueerror(self):
        with self.assertRaises(ValueError) as cm:
            get_connection("unknown_source")
        self.assertIn("unknown_source", str(cm.exception))
        self.assertIn("Available sources", str(cm.exception))
        self.mock_connect.assert_not_called()


if __name__ == "__main__":
    unittest.main()
