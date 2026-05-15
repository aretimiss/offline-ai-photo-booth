from __future__ import annotations

import secrets
import string
from pathlib import Path


CODE_ALPHABET = string.ascii_uppercase + string.digits


def generate_image_code(length: int = 8) -> str:
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(length))


def output_filename(code: str, extension: str = ".jpg") -> str:
    extension = extension if extension.startswith(".") else f".{extension}"
    return f"{code}{extension}"


def safe_delete(path: str | Path) -> None:
    file_path = Path(path)
    if file_path.exists() and file_path.is_file():
        file_path.unlink(missing_ok=True)
