"""Tool registry for Toolhub Python utilities."""

TOOLS = {}

try:
    from . import docx_render

    TOOLS["docx-render"] = {
        "handler": docx_render.handler,
        "description": "Fill a DOCX template with placeholder data",
    }
except Exception:  # noqa: BLE001
    # Keep registry importable even when optional runtime dependencies are missing.
    pass

try:
    from mcp_tools.docx_template_fill.tool import fill_docx_template

    # Wrap mcp_tools output in the webhook status envelope for consistent /run responses.
    TOOLS["docx-template-fill"] = {
        "handler": lambda payload: {"status": "ok", **fill_docx_template(payload)},
        "description": "Fill a DOCX template using docxtpl and write output to DOCX_OUTPUT_ROOT",
    }
except Exception:  # noqa: BLE001
    # Keep registry importable even when optional runtime dependencies are missing.
    pass
