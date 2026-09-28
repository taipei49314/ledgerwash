"""Shared rule helpers: string walking and timestamp parsing."""

from __future__ import annotations

from datetime import datetime, timezone

MIN_TS = datetime.min.replace(tzinfo=timezone.utc)


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
