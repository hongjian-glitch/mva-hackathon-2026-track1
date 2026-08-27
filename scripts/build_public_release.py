#!/usr/bin/env python3
"""Build a clean, allowlisted public release tree.

The workspace contains controlled inputs and participant-derived outputs. This
builder copies only named source files into a new directory, rejects unresolved
report holds, writes a deterministic hash manifest, and runs the public privacy
scanner on the assembled tree.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import sys
from pathlib import Path

from scripts.privacy_check import scan_public_tree


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RELEASE_MANIFEST = "release_manifest.json"

PUBLIC_FILES = (
    ".github/workflows/ci.yml",
    ".gitignore",
    "LICENSE",
    "README.md",
    "pyproject.toml",
    "config/bub1b_mane_nm_001211.6.json",
    "docs/CONTRACT.md",
    "docs/PROVENANCE.md",
    "references/public_resources.sha256",
    "references/public_resources.tsv",
    "scripts/build_public_release.py",
    "scripts/check_official_scorer.py",
    "scripts/fetch_official_evaluator.sh",
    "scripts/fetch_public_references.sh",
    "scripts/privacy_check.py",
    "scripts/run_track1.sh",
    "scripts/write_private_manifest.py",
    "src/mva_solver/__init__.py",
    "src/mva_solver/__main__.py",
    "src/mva_solver/cli.py",
    "src/mva_solver/clinvar.py",
    "src/mva_solver/mane.py",
    "src/mva_solver/models.py",
    "src/mva_solver/pipeline.py",
    "src/mva_solver/secure_io.py",
    "src/mva_solver/submission.py",
    "src/mva_solver/vcf.py",
    "tests/test_mane.py",
    "tests/test_official_contract.py",
    "tests/test_pipeline.py",
    "tests/test_privacy.py",
    "tests/test_public_release.py",
    "tests/test_submission.py",
    "tests/test_vcf.py",
)

REPORT_HOLDS = (
    "[CONFIRM]",
    "[RELEASE HOLD",
    "(provisional)",
    "participant-review draft",
    "not submitted",
)

REQUIRED_REPORT_TEXT = (
    "## Required acknowledgement",
    "## Required dataset citation",
    "Repository URL and immutable commit:",
)

GITHUB_COMMIT_PATTERN = re.compile(
    r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:\.git)?\s+"
    r"(?:at|commit|revision)?\s*\b[0-9a-f]{40}\b",
    re.IGNORECASE,
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_report_text(text: str) -> list[str]:
    errors = []
    lower_text = text.lower()
    for hold in REPORT_HOLDS:
        if hold.lower() in lower_text:
            errors.append(f"report contains unresolved release text: {hold}")
    for required in REQUIRED_REPORT_TEXT:
        if required not in text:
            errors.append(f"report is missing required section or field: {required}")
    if not GITHUB_COMMIT_PATTERN.search(text):
        errors.append("report lacks a GitHub URL followed by an immutable 40-hex commit")
    return errors


def _copy_public_file(source_root: Path, output_dir: Path, relative: str) -> None:
    source = source_root / relative
    destination = output_dir / relative
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
    shutil.copyfile(source, destination)
    executable = stat.S_IMODE(source.stat().st_mode) & 0o111
    os.chmod(destination, 0o755 if executable else 0o644)


def _manifest_payload(output_dir: Path, relative_files: list[str]) -> dict:
    files = []
    for relative in sorted(relative_files):
        path = output_dir / relative
        files.append(
            {
                "path": relative,
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    return {"schema_version": "1.0", "files": files}


def build_release(
    source_root: Path,
    output_dir: Path,
    report_path: Path | None = None,
) -> Path:
    source_root = source_root.resolve()
    output_dir = output_dir.resolve()
    if source_root == output_dir or source_root in output_dir.parents:
        raise ValueError("release output must be outside the source workspace")
    if output_dir.exists():
        raise FileExistsError(f"release output already exists: {output_dir}")

    for relative in PUBLIC_FILES:
        source = source_root / relative
        if not source.is_file():
            raise FileNotFoundError(f"allowlisted source file is missing: {relative}")
        if source.is_symlink():
            raise ValueError(f"allowlisted source file cannot be a symlink: {relative}")

    report_text = None
    if report_path is not None:
        report_path = report_path.resolve()
        if not report_path.is_file() or report_path.is_symlink():
            raise ValueError(f"report must be a regular file: {report_path}")
        report_text = report_path.read_text(encoding="utf-8")
        report_errors = validate_report_text(report_text)
        if report_errors:
            raise ValueError("; ".join(report_errors))

    created = False
    try:
        output_dir.mkdir(parents=True, mode=0o755)
        created = True
        copied = []
        for relative in PUBLIC_FILES:
            _copy_public_file(source_root, output_dir, relative)
            copied.append(relative)

        if report_path is not None and report_text is not None:
            report_relative = report_path.name
            destination = output_dir / report_relative
            shutil.copyfile(report_path, destination)
            os.chmod(destination, 0o644)
            copied.append(report_relative)

        payload = _manifest_payload(output_dir, copied)
        manifest_path = output_dir / RELEASE_MANIFEST
        manifest_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.chmod(manifest_path, 0o644)

        errors = scan_public_tree(output_dir)
        if errors:
            raise ValueError("release privacy scan failed: " + "; ".join(errors))

        actual_files = {
            path.relative_to(output_dir).as_posix()
            for path in output_dir.rglob("*")
            if path.is_file()
        }
        expected_files = set(copied) | {RELEASE_MANIFEST}
        if actual_files != expected_files:
            unexpected = sorted(actual_files - expected_files)
            missing = sorted(expected_files - actual_files)
            raise ValueError(
                f"release tree mismatch; unexpected={unexpected}; missing={missing}"
            )
        return manifest_path
    except Exception:
        if created and output_dir.exists():
            shutil.rmtree(output_dir)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--report",
        type=Path,
        help="Optional approved report. Unresolved holds cause a fail-closed error.",
    )
    args = parser.parse_args()

    try:
        manifest_path = build_release(PROJECT_ROOT, args.output, args.report)
    except (FileNotFoundError, FileExistsError, OSError, ValueError) as error:
        print(f"release_error={error}", file=sys.stderr)
        return 2
    file_count = len(json.loads(manifest_path.read_text())["files"])
    print(f"public_release_ok={manifest_path.parent}")
    print(f"release_file_count={file_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
