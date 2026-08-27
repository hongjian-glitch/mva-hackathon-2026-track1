from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_public_release import (
    PUBLIC_FILES,
    RELEASE_MANIFEST,
    build_release,
    validate_report_text,
)
from scripts.privacy_check import scan_public_tree


class PublicReleaseTest(unittest.TestCase):
    def test_builder_copies_only_the_allowlist(self) -> None:
        source_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "release"
            manifest_path = build_release(source_root, output)
            payload = json.loads(manifest_path.read_text())
            self.assertEqual(
                {item["path"] for item in payload["files"]},
                set(PUBLIC_FILES),
            )
            self.assertEqual(scan_public_tree(output), [])
            actual = {
                path.relative_to(output).as_posix()
                for path in output.rglob("*")
                if path.is_file()
            }
            self.assertEqual(actual, set(PUBLIC_FILES) | {RELEASE_MANIFEST})

    def test_report_with_release_holds_is_rejected(self) -> None:
        errors = validate_report_text(
            "participant-review draft\n"
            "## Required acknowledgement\n"
            "## Required dataset citation\n"
            "Repository URL and immutable commit: [RELEASE HOLD]\n"
        )
        self.assertTrue(errors)

    def test_held_report_leaves_no_partial_release(self) -> None:
        source_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            report = temp_root / "draft.md"
            report.write_text(
                "participant-review draft\n"
                "## Required acknowledgement\n"
                "## Required dataset citation\n"
                "Repository URL and immutable commit: [RELEASE HOLD]\n"
            )
            output = temp_root / "release"
            with self.assertRaises(ValueError):
                build_release(source_root, output, report)
            self.assertFalse(output.exists())

    def test_release_ready_report_is_accepted(self) -> None:
        text = (
            "## Required acknowledgement\n"
            "## Required dataset citation\n"
            "Dataset citation text.\n"
            "Repository URL and immutable commit: "
            "https://github.com/example/mva-solver commit "
            "0123456789abcdef0123456789abcdef01234567\n"
        )
        self.assertEqual(validate_report_text(text), [])


if __name__ == "__main__":
    unittest.main()
