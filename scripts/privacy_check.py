#!/usr/bin/env python3
"""Fail closed if a public release contains controlled data or credentials."""

from __future__ import annotations

import os
import re
import stat
import sys
from pathlib import Path


PRIVATE_DIRS = {"data/raw", "data/derived", "outputs/private", "qa"}
EXCLUDED_RELEASE_DIRS = {
    ".git",
    ".pytest_cache",
    ".venv",
    "data/public",
    "data/raw",
    "data/derived",
    "node_modules",
    "official_challenge_space",
    "outputs/private",
    "qa",
}
FORBIDDEN_SUFFIXES = {
    ".bam",
    ".bcf",
    ".cram",
    ".csi",
    ".docx",
    ".fastq",
    ".fq",
    ".pdf",
    ".tbi",
    ".vcf",
}
SECRET_PATTERNS = {
    "Hugging Face token": re.compile(rb"\bhf_[A-Za-z0-9]{20,}\b"),
    "GitHub token": re.compile(rb"\b(?:ghp|github_pat)_[A-Za-z0-9_]{20,}\b"),
    "API token": re.compile(rb"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "private key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "VCF body": re.compile(rb"(?m)^#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO"),
}


def public_paths(root: Path) -> list[Path]:
    paths: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        relative_text = relative.as_posix()
        if "__pycache__" in relative.parts:
            continue
        if any(
            relative_text == excluded or relative_text.startswith(f"{excluded}/")
            for excluded in EXCLUDED_RELEASE_DIRS
        ):
            continue
        paths.append(path)
    return sorted(paths)


def scan_public_tree(root: Path) -> list[str]:
    errors: list[str] = []
    for path in public_paths(root):
        relative = path.relative_to(root)
        suffixes = {suffix.lower() for suffix in path.suffixes}
        blocked = sorted(suffixes & FORBIDDEN_SUFFIXES)
        if blocked:
            errors.append(f"{relative}: forbidden public-data suffix {blocked[-1]}")
            continue
        try:
            content = path.read_bytes()
        except OSError as error:
            errors.append(f"{relative}: could not read ({error})")
            continue
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(content):
                errors.append(f"{relative}: contains {label}")
    return errors


def check_private_permissions(root: Path) -> list[str]:
    if os.name != "posix":
        return []
    errors: list[str] = []
    for dirname in sorted(PRIVATE_DIRS):
        base = root / dirname
        if not base.exists():
            continue
        for path in (base, *base.rglob("*")):
            if path.is_symlink():
                errors.append(f"{path.relative_to(root)}: symlink inside private tree")
                continue
            mode = stat.S_IMODE(path.stat().st_mode)
            if path.is_dir() and mode & 0o077:
                errors.append(
                    f"{path.relative_to(root)}: private directory mode {mode:o}, expected 700"
                )
            elif path.is_file() and mode & 0o077:
                errors.append(
                    f"{path.relative_to(root)}: private file mode {mode:o}, expected 600"
                )
    return errors


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    errors = scan_public_tree(root) + check_private_permissions(root)
    if errors:
        for error in errors:
            print(error)
        return 2
    print("privacy_check_ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
