"""Shared rule helpers: string walking and timestamp parsing."""

from __future__ import annotations

import re
from datetime import datetime, timezone

MIN_TS = datetime.min.replace(tzinfo=timezone.utc)

# Date-level prefix — masking can eat the whole time part (…T02:xxZ).
_ISO_PREFIX = re.compile(r"\d{4}-\d{2}-\d{2}")


def iter_strings(value):
    """Yield every string in a JSON-shaped structure, keys included."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from iter_strings(key)
            yield from iter_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from iter_strings(item)


def parse_ts(value):
    """Aware datetime, or None.

    Naive timestamps are read as UTC. Callers must surface None as
    TIMESTAMP_MALFORMED wherever a rule depends on the value — a bad timestamp
    is a finding, never a silent skip (SPEC §4).
    """
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def ts_or_min(value):
    return parse_ts(value) or MIN_TS


def present_but_unparseable(value) -> bool:
    return value is not None and value != "" and parse_ts(value) is None


def is_redacted_ts(value) -> bool:
    """EC legacy redaction shape: digit-masked (`2026-07-27T15:2xZ`) or an
    `A → B` range. Unorderable by convention, not a malformed timestamp."""
    if not isinstance(value, str):
        return False
    if "→" in value:
        return True
    return bool(_ISO_PREFIX.search(value)) and any(ch in value for ch in "xX")
