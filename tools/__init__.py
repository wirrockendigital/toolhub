"""Tool registry for Toolhub Python utilities."""

from . import docx_render

TOOLS = {
    "docx-render": {
        "handler": docx_render.handler,
        "description": "Fill a DOCX template with placeholder data",
    }
}
