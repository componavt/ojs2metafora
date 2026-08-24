import os
import sys
import unittest
import subprocess


class TestCLIImportModes(unittest.TestCase):
    """Tests for CLI import modes and package imports."""

    def test_main_help_succeeds(self):
        """Verify python3 src/main.py --help returns exit code 0."""
        result = subprocess.run(
            [sys.executable, "src/main.py", "--help"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            result.returncode, 0, msg=f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

    def test_generate_all_help_succeeds(self):
        """Verify python3 src/generate_all.py --help returns exit code 0."""
        result = subprocess.run(
            [sys.executable, "src/generate_all.py", "--help"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            result.returncode, 0, msg=f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

    def test_fetch_article_help_succeeds(self):
        """Verify python3 src/fetch_article.py --help returns exit code 0."""
        result = subprocess.run(
            [sys.executable, "src/fetch_article.py", "--help"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            result.returncode, 0, msg=f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

    def test_package_imports_succeed(self):
        """Verify package-mode imports of all src.* modules succeed."""
        script_path = os.path.join(os.path.dirname(__file__), "verify_imports.py")
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(
                """
import sys
import os

# Ensure repository root is on sys.path for package imports
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

import src.db_connector
import src.issue_builder
import src.fetch_article
import src.generate_all
import src.main
import src.explore_db
"""
            )
        try:
            result = subprocess.run(
                [sys.executable, script_path],
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                result.returncode, 0, msg=f"stdout: {result.stdout}\\nstderr: {result.stderr}"
            )
        finally:
            if os.path.exists(script_path):
                os.remove(script_path)


if __name__ == "__main__":
    unittest.main()
