"""Rendering helpers for DOCX template filling."""

from __future__ import annotations

# Keep import declarations single to avoid syntax errors with future imports.
import logging
import os
from pathlib import Path
from typing import Dict, Set, Tuple, Type

from .validators import (
    validate_data_mapping,
    validate_output_filename,
    validate_output_subdir,
    validate_template_name,
)

LOGGER = logging.getLogger("docx_template_fill")

TEMPLATE_ROOT = Path(os.getenv("DOCX_TEMPLATE_ROOT", "/templates"))
OUTPUT_ROOT = Path(os.getenv("DOCX_OUTPUT_ROOT", "/output"))


class TemplateValidationError(ValueError):
    """Raised when input validation fails."""


class RenderingError(RuntimeError):
    """Raised for rendering failures."""


def _ensure_within_root(path: Path, root: Path) -> Path:
    resolved_root = root.resolve()
    resolved_path = path.resolve()
    if not str(resolved_path).startswith(str(resolved_root)):
        raise TemplateValidationError(f"Path {resolved_path} escapes base directory {resolved_root}.")
    return resolved_path


def _build_template_path(template: str) -> Path:
    validated = validate_template_name(template)
    candidate = _ensure_within_root(TEMPLATE_ROOT / validated, TEMPLATE_ROOT)
    if not candidate.is_file():
        raise FileNotFoundError(f"Template not found: {candidate}")
    return candidate


def _build_output_path(subdir: str | None, filename: str) -> Path:
    validated_filename = validate_output_filename(filename)
    validated_subdir = validate_output_subdir(subdir)

    base = OUTPUT_ROOT
    if validated_subdir:
        base = base / validated_subdir

    output_path = base / validated_filename
    resolved = _ensure_within_root(output_path, OUTPUT_ROOT)

    if resolved.exists():
        raise TemplateValidationError(f"Output file already exists: {resolved}")

    resolved.parent.mkdir(parents=True, exist_ok=True)
    return resolved


def _load_dependencies() -> Tuple[Type[object], Type[object], Type[object]]:
    try:
        from docxtpl import DocxTemplate  # type: ignore
    except ImportError as exc:  # pragma: no cover - dependency missing in environment
        raise RenderingError(
            "docxtpl is required to render templates; install docxtpl>=0.16."
        ) from exc

    try:
        from jinja2 import Environment, Undefined  # type: ignore
    except ImportError as exc:  # pragma: no cover - dependency missing in environment
        raise RenderingError("jinja2 is required to render templates.") from exc

    return DocxTemplate, Environment, Undefined


def _collect_placeholders(doc: object) -> Set[str]:
    try:
        variables = doc.get_undeclared_template_variables()  # type: ignore[attr-defined]
    except Exception as exc:  # pragma: no cover - defensive
        LOGGER.debug("Failed to collect placeholders from template: %s", exc)
        return set()

    return {str(item) for item in variables} if variables else set()


def render_template(
    *,
    template: str,
    data: Dict[str, object],
    output_subdir: str | None,
    output_filename: str,
) -> Dict[str, object]:
    """Render a DOCX template to the output path.

    Returns metadata about the rendering process.
    """

    LOGGER.info(
        "Rendering template",
        extra={"template": template, "output_subdir": output_subdir, "output_filename": output_filename},
    )

    try:
        validated_data = validate_data_mapping(data)
        template_path = _build_template_path(template)
        output_path = _build_output_path(output_subdir, output_filename)
    except TemplateValidationError:
        raise
    except FileNotFoundError:
        raise
    except ValueError as exc:
        raise TemplateValidationError(str(exc)) from exc

    DocxTemplateCls, JinjaEnv, JinjaUndefined = _load_dependencies()

    try:
        doc = DocxTemplateCls(str(template_path))  # type: ignore[call-arg]
    except Exception as exc:  # pragma: no cover - dependency error is environmental
        LOGGER.error("Failed to load template: %s", exc)
        raise RenderingError(f"Unable to open template: {exc}") from exc

    placeholders = _collect_placeholders(doc)
    missing_in_data = sorted([name for name in placeholders if name not in validated_data])
    unused_data_keys = sorted([key for key in validated_data if key not in placeholders])

    env = JinjaEnv(undefined=JinjaUndefined, autoescape=False)

    try:
        doc.render(validated_data, jinja_env=env)
        doc.save(str(output_path))
    except Exception as exc:  # pragma: no cover - docxtpl internal error
        LOGGER.error("Rendering failed: %s", exc)
        raise RenderingError(f"Rendering failed: {exc}") from exc

    LOGGER.info(
        "Rendered output created",
        extra={
            "output_path": str(output_path),
            "missing_placeholders": missing_in_data,
            "unused_keys": unused_data_keys,
        },
    )

    return {
        "output_file": str(output_path),
        "template": template,
        "placeholders_in_template": sorted(placeholders),
        "placeholders_missing": missing_in_data,
        "unused_data_keys": unused_data_keys,
    }
