"""
Input sanitizers and normalizers.

Functions for cleaning and normalizing user inputs.
"""

from __future__ import annotations


def sanitize_name(name: str) -> str:
    """
    Sanitize a name input.

    Args:
        name: Raw name input.

    Returns:
        Sanitized name with trimmed whitespace.
    """
    return name.strip()


__all__ = [
    "sanitize_name",
]
