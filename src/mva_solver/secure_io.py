from __future__ import annotations

import os
import tempfile
from collections.abc import Callable
from pathlib import Path


Validator = Callable[[Path], list[str]]


def secure_write_text(
    output: str | Path,
    content: str,
    *,
    validator: Validator | None = None,
) -> None:
    """Atomically write patient-derived text with owner-only permissions."""
    path = Path(output)
    parent_was_missing = not path.parent.exists()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if parent_was_missing or path.parent.name == "private":
        path.parent.chmod(0o700)

    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        text=True,
    )
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        if validator is not None:
            errors = validator(temporary)
            if errors:
                raise ValueError("Output validation failed: " + "; ".join(errors))
        os.replace(temporary, path)
        path.chmod(0o600)
    finally:
        temporary.unlink(missing_ok=True)
