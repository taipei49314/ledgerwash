"""POST_HOC_DRIFT: current task record differs from the anchor receipt's after_record."""

from __future__ import annotations

from ledgerwash.models import Finding, short_json, strict_eq

from .common import parse_ts


def _diff_keys(a, b, prefix: str = ""):
    """Yield (key path, value in a, value in b) for every difference, type-strict."""
    if isinstance(a, dict) and isinstance(b, dict):
        for key in sorted(set(a) | set(b)):
            key_path = f"{prefix}.{key}" if prefix else str(key)
            if key not in a:
                yield (key_path, None, b[key])
            elif key not in b:
                yield (key_path, a[key], None)
            else:
                yield from _diff_keys(a[key], b[key], key_path)
    elif not (type(a) is type(b) and a == b):
        yield (prefix, a, b)


def run(corpus) -> list[Finding]:
    findings: list[Finding] = []
    for task_id in sorted(corpus.ops_by_task()):
        task = corpus.tasks.get(task_id)
        if task is None:
            continue
        ops = corpus.ops_by_task()[task_id]
        anchor = max(ops, key=lambda r: (parse_ts(r.data.get("recorded_at")), r.name))
        after = anchor.data.get("after_record")
        if not isinstance(after, dict):
            continue
        if strict_eq(after, task.data):
            continue
        diffs = list(_diff_keys(after, task.data))
        keys = ", ".join(path for path, _a, _b in diffs[:6])
        more = f" (+{len(diffs) - 6} more)" if len(diffs) > 6 else ""
        findings.append(
            Finding(
                rule="POST_HOC_DRIFT",
                severity="high",
                message=(
                    f"current task record differs from anchor receipt {anchor.name} "
                    f"after_record ({len(diffs)} difference(s): {keys}{more})"
                ),
                path=task.path,
                locator=f"{task_id}:anchor={anchor.name}",
                before=short_json(diffs[0][1]),
                after=short_json(diffs[0][2]),
            )
        )
    return findings
