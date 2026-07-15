"""Stockage mémoire des .docx générés (POC, worker unique)."""

import uuid

_FILES: dict[str, dict] = {}


def save_file(content: bytes, filename: str) -> str:
    file_id = uuid.uuid4().hex
    _FILES[file_id] = {"content": content, "filename": filename}
    return file_id


def get_file(file_id: str) -> dict | None:
    return _FILES.get(file_id)
