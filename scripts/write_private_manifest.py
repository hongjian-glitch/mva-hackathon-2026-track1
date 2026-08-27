#!/usr/bin/env python3
"""Write an owner-only run manifest for controlled inputs and scored outputs."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from mva_solver.secure_io import secure_write_text


DATASET_REVISION = "59e322d27f399006b398d366d33e703e48a29914"
SPACE_REVISION = "d27c33953ecb0cfd7fa316c7cd93ff0ffb05cc1d"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_artifact(value: str) -> tuple[str, Path]:
    label, separator, filename = value.partition("=")
    if not separator or not label or not filename:
        raise argparse.ArgumentTypeError("artifacts must use label=/path/to/file")
    path = Path(filename)
    if not path.is_file():
        raise argparse.ArgumentTypeError(f"artifact does not exist: {path}")
    return label, path


def tool_version(command: list[str]) -> str:
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    return completed.stdout.splitlines()[0].strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", action="append", default=[], type=parse_artifact)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    artifacts = []
    for label, path in args.artifact:
        artifacts.append(
            {
                "label": label,
                "basename": path.name,
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )

    payload = {
        "schema_version": "1.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "privacy": "controlled/private; do not publish",
        "dataset_revision": DATASET_REVISION,
        "challenge_space_revision": SPACE_REVISION,
        "runtime": {
            "python": sys.version.splitlines()[0],
            "platform": platform.platform(),
            "bcftools": tool_version(["bcftools", "--version"]),
        },
        "artifacts": artifacts,
    }
    secure_write_text(args.output, json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"private_manifest_ok={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
