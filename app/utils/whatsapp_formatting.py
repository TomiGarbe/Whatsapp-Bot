"""Utilities for normalizing outbound text to WhatsApp formatting."""

import re

_MARKDOWN_BOLD_PATTERN = re.compile(r"\*\*(.*?)\*\*")


def normalize_whatsapp_formatting(text: str) -> str:
    """Convert Markdown bold segments (**text**) into WhatsApp bold (*text*)."""
    return _MARKDOWN_BOLD_PATTERN.sub(r"*\1*", text)

