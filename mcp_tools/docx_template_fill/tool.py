"""CLI entrypoint for the docx-template-fill MCP tool."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict

from .renderer import RenderingError, TemplateValidationError, render_template

LOGGER = logging.getLogger("docx_template_fill")
DEFAULT_LOG_PATH = os.getenv("DOCX_TEMPLATE_FILL_LOG_PATH", "/logs/docx-template-fill.log")
DEFAULT_LOG_LEVEL = os.getenv("DOCX_TEMPLATE_FILL_LOG_LEVEL", "INFO").upper()


class CliError(Exception):
    """Raised for CLI usage errors."""


def _configure_logging() -> None:
    level = getattr(logging, DEFAULT_LOG_LEVEL, logging.INFO)
    LOGGER.setLevel(level)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    )

    # Avoid duplicate handlers in repeated invocations (tests).
    if not LOGGER.handlers:
        file_handler_added = False
        try:
            log_path = Path(DEFAULT_LOG_PATH)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_path, encoding="utf-8")
            file_handler.setFormatter(formatter)
            file_handler.setLevel(level)
            LOGGER.addHandler(file_handler)
            file_handler_added = True
        except Exception:
            # Fallback to stderr if file handler cannot be created.
            pass

        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        stream_handler.setLevel(level)
        LOGGER.addHandler(stream_handler)

        if file_handler_added:
            LOGGER.debug("File logging initialised at %s", DEFAULT_LOG_PATH)


def _load_payload(args: argparse.Namespace) -> Dict[str, Any]:
    if args.payload:
        try:
            return json.loads(args.payload)
        except json.JSONDecodeError as exc:
            raise CliError(f"Invalid JSON in --payload: {exc}") from exc

    if args.payload_file:
        try:
            contents = Path(args.payload_file).read_text(encoding="utf-8")
        except OSError as exc:
            raise CliError(f"Unable to read payload file: {exc}") from exc
        try:
            return json.loads(contents)
        except json.JSONDecodeError as exc:
            raise CliError(f"Invalid JSON in payload file: {exc}") from exc

    raise CliError("Either --payload or --payload-file is required.")


def fill_docx_template(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise TemplateValidationError("payload must be a JSON object.")

    if "template" not in payload:
        raise TemplateValidationError("template is required.")
    if "output_filename" not in payload:
        raise TemplateValidationError("output_filename is required.")
    if "data" not in payload:
        raise TemplateValidationError("data is required.")

    try:
        return render_template(
            template=payload["template"],
            data=payload["data"],
            output_subdir=payload.get("output_subdir"),
            output_filename=payload["output_filename"],
        )
    except FileNotFoundError as exc:
        raise TemplateValidationError(str(exc)) from exc
    except ValueError as exc:
        raise TemplateValidationError(str(exc)) from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fill a DOCX template with data.")
    parser.add_argument("--payload", help="JSON payload containing template, data, output_subdir, output_filename.")
    parser.add_argument("--payload-file", help="Path to a JSON file containing the payload.")
    args = parser.parse_args(argv)

    _configure_logging()

    try:
        payload = _load_payload(args)
        result = fill_docx_template(payload)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except CliError as exc:
        LOGGER.error("CLI error: %s", exc)
        print(json.dumps({"error": str(exc)}))
        return 2
    except TemplateValidationError as exc:
        LOGGER.error("Validation error: %s", exc)
        print(json.dumps({"error": str(exc)}))
        return 1
    except RenderingError as exc:
        LOGGER.error("Rendering error: %s", exc)
        print(json.dumps({"error": str(exc)}))
        return 1
    except Exception as exc:  # pragma: no cover - safeguard
        LOGGER.exception("Unexpected error: %s", exc)
        print(json.dumps({"error": "unexpected error", "details": str(exc)}))
        return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
