from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.privacy_check import scan_public_tree


class PrivacyCheckTest(unittest.TestCase):
    def test_safe_source_tree_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "src").mkdir()
            (root / "src" / "safe.py").write_text("print('safe')\n")
            self.assertEqual(scan_public_tree(root), [])

    def test_token_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "docs").mkdir()
            (root / "docs" / "bad.md").write_text("hf_" + "a" * 30)
            self.assertTrue(scan_public_tree(root))

    def test_vcf_file_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "tests").mkdir()
            (root / "tests" / "subject.vcf").write_text("test")
            self.assertTrue(scan_public_tree(root))

    def test_unexpected_directory_is_still_scanned(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "unexpected").mkdir()
            (root / "unexpected" / "subject.vcf").write_text("test")
            self.assertTrue(scan_public_tree(root))


if __name__ == "__main__":
    unittest.main()
