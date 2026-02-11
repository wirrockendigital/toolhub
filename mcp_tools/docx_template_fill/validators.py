"""Validation helpers for the docx-template-fill MCP tool."""

from __future__ import annotations

import re
from typing import Dict

TEMPLATE_EXTENSION = ".docx"
OUTPUT_EXTENSION = ".docx"

_TEMPLATE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")
_OUTPUT_FILENAME_PATTERN = re.compile(r"^[A-Za-z0-9_-]+\.docx$", re.IGNORECASE)
_OUTPUT_SUBDIR_PATTERN = re.compile(r"^[A-Za-z0-9_\-/]*$")


def _ensure_docx(name: str, field: str) -> None:
    if not name.lower().endswith(TEMPLATE_EXTENSION):
        raise ValueError(f"{field} must end with '{TEMPLATE_EXTENSION}'.")


def validate_template_name(name: str) -> str:
    """Validate the template filename and ensure it is a simple DOCX name."""
    if not isinstance(name, str) or not name.strip():
        raise ValueError("template must be a non-empty string.")

    if name.startswith(("/", "\\")):
        raise ValueError("template must be a filename, not an absolute path.")

    if "/" in name or "\\" in name:
        raise ValueError("template must not contain path separators.")

    if ".." in name:
        raise ValueError("template must not contain parent directory traversal.")

    if not _TEMPLATE_NAME_PATTERN.match(name):
        raise ValueError("template contains invalid characters; only letters, digits, '_', '-', '.' are allowed.")

    _ensure_docx(name, "template")
    return name


def validate_output_filename(filename: str) -> str:
    """Validate the desired output filename."""
    if not isinstance(filename, str) or not filename.strip():
        raise ValueError("output_filename is required and must be a non-empty string.")

    if "/" in filename or "\\" in filename:
        raise ValueError("output_filename must not contain path separators.")

    if ".." in filename:
        raise ValueError("output_filename must not contain parent directory traversal.")

    if not _OUTPUT_FILENAME_PATTERN.match(filename):
        raise ValueError("output_filename may only contain letters, digits, '_', '-' and end with .docx.")

    _ensure_docx(filename, "output_filename")
    return filename


def validate_output_subdir(subdir: str | None) -> str | None:
    """Validate an optional output subdirectory string."""
    if subdir is None:
        return None

    if not isinstance(subdir, str):
        raise ValueError("output_subdir must be a string if provided.")

    cleaned = subdir.strip()
    if not cleaned:
        return None

    if cleaned.startswith(("/", "\\")):
        raise ValueError("output_subdir must be relative and must not start with a slash.")

    if ".." in cleaned:
        raise ValueError("output_subdir must not contain parent directory traversal.")

    if not _OUTPUT_SUBDIR_PATTERN.match(cleaned):
        raise ValueError("output_subdir may only contain letters, digits, '_', '-', and '/'.")

    return cleaned.strip("/")


def validate_data_mapping(data: Dict[str, object]) -> Dict[str, str]:
    """Ensure payload data is a flat dict of string keys/values."""
    if not isinstance(data, dict):
        raise ValueError("data must be an object with string key/value pairs.")

    validated: Dict[str, str] = {}
    for key, value in data.items():
        if not isinstance(key, str):
            raise ValueError("data keys must be strings.")
        if value is None:
            raise ValueError(f"data[{key!r}] must not be null.")
        if isinstance(value, (list, dict)):
            raise ValueError(f"data[{key!r}] must be a string, not a nested structure.")
        validated[key] = str(value)

    return validated
