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


class TestRunTestScriptRegression(unittest.TestCase):
    """Regression tests for src/run_test.sh shell script."""

    _SCRIPT_PATH = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "run_test.sh"
    )

    def test_invalid_source_exits_nonzero(self):
        """Verify bash src/run_test.sh --source invalid exits non-zero."""
        result = subprocess.run(
            ["/bin/bash", self._SCRIPT_PATH, "--source", "invalid"],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unknown", result.stderr.lower())

    def test_missing_source_value_exits_nonzero(self):
        """Verify bash src/run_test.sh --source (no value) exits non-zero."""
        result = subprocess.run(
            ["/bin/bash", self._SCRIPT_PATH, "--source"],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)

    def test_mgta_dry_run_no_failure_masking(self):
        """Assert MGTA dry-run command has no || true, 2>&1, or /dev/null."""
        with open(self._SCRIPT_PATH, "r", encoding="utf-8") as f:
            script_content = f.read()

        lines = script_content.split("\n")
        mgta_dry_run_found = False
        for i, line in enumerate(lines):
            if "generate_all.py --source mgta --journal-path mgta --dry-run" in line:
                mgta_dry_run_found = True
                self.assertNotIn("|| true", line)
                self.assertNotIn("2>&1", line)
                self.assertNotIn("/dev/null", line)
                break

        self.assertTrue(
            mgta_dry_run_found,
            "MGTA dry-run command not found in run_test.sh",
        )

    def test_mgta_success_messages_after_dry_run(self):
        """Assert MGTA smoke test messages occur after the dry-run command."""
        with open(self._SCRIPT_PATH, "r", encoding="utf-8") as f:
            script_content = f.read()

        dry_run_idx = script_content.find("generate_all.py --source mgta --journal-path mgta --dry-run")
        
        fetch_success = script_content.find("fetch_article.py (article_id=42, json format)")
        validate_success = script_content.find("main.py (issue_id=11, validate, verbose)")
        package_success = script_content.find("Package import smoke test for article XML construction")

        self.assertGreater(
            fetch_success,
            dry_run_idx,
            "fetch_article.py success message should appear after dry-run command",
        )
        self.assertGreater(
            validate_success,
            dry_run_idx,
            "main.py success message should appear after dry-run command",
        )
        self.assertGreater(
            package_success,
            dry_run_idx,
            "Package import success message should appear after dry-run command",
        )


if __name__ == "__main__":
    unittest.main()


if __name__ == "__main__":
    unittest.main()
