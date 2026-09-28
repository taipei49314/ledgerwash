"""Finding model, severity ladder, type-strict equality, fingerprint canonicalization."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

SEVERITY_ORDER = ("info", "warn", "high", "critical")
SEVERITY_RANK = {name: rank for rank, name in enumerate(SEVERITY_ORDER)}


@dataclass
class Finding:
    rule: str
    severity: str
    message: str
    path: str = ""
    locator: str = ""
    before: str | None = None
    after: str | None = None
    fingerprint: str | None = None

    def sort_key(self) -> tuple[str, str, str]:
        return (self.rule, self.path, self.locator)


def finding_fingerprint(finding: Finding) -> str:
    payload = {
        "rule": finding.rule,
        "path": finding.path,
        "locator": finding.locator,
        "before": finding.before,
        "after": finding.after,
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    return f"{finding.rule}/{finding.path or '-'}/v1:{digest}"


def strict_eq(a, b) -> bool:
    """Type-strict structural equality.

    bool != int on purpose: a coerced field must show up as a change, not a no-op
    (EYE store.put lesson: {"x":1} -> {"x":true} is a real change that a loose
    equality would swallow).
    """
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        if a.keys() != b.keys():
            return False
        return all(strict_eq(a[key], b[key]) for key in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(strict_eq(x, y) for x, y in zip(a, b))
    return a == b


def short_json(value, limit: int = 120) -> str:
    text = json.dumps(value, sort_keys=True, ensure_ascii=False)
    return text if len(text) <= limit else text[: limit - 1] + "…"
