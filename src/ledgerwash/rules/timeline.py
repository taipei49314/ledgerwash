"""TIMESTAMP_MALFORMED / TIMELINE_INVERSION / CHAIN_BREAK."""

from __future__ import annotations

from ledgerwash.models import Finding

from .common import parse_ts, present_but_unparseable


def run(corpus) -> list[Finding]:
    findings: list[Finding] = []

    for receipt in corpus.receipts:
        rec_raw = receipt.data.get("recorded_at")
        rec = parse_ts(rec_raw)
        if present_but_unparseable(rec_raw):
            findings.append(
                Finding(
                    rule="TIMESTAMP_MALFORMED",
                    severity="medium",
                    message=f"receipt recorded_at does not parse as ISO-8601: {rec_raw!r}",
                    path=receipt.path,
                    locator=f"{receipt.name}#recorded_at",
                    after=str(rec_raw),
                )
            )
        request = receipt.data.get("request")
        req_raw = request.get("at") if isinstance(request, dict) else None
        req = parse_ts(req_raw)
        if present_but_unparseable(req_raw):
            findings.append(
                Finding(
                    rule="TIMESTAMP_MALFORMED",
                    severity="medium",
                    message=f"receipt request.at does not parse as ISO-8601: {req_raw!r}",
                    path=receipt.path,
                    locator=f"{receipt.name}#request.at",
                    after=str(req_raw),
                )
            )
        if rec is not None and req is not None and rec < req:
            findings.append(
                Finding(
                    rule="TIMELINE_INVERSION",
                    severity="high",
                    message=(
                        f"recorded_at {rec_raw} is earlier than request.at {req_raw}; "
                        "clock or timezone mislabeling suspected"
                    ),
                    path=receipt.path,
                    locator=receipt.name,
                    before=str(req_raw),
                    after=str(rec_raw),
                )
            )

    for task in corpus.tasks.values():
        t_raw = task.data.get("time")
        if present_but_unparseable(t_raw):
            findings.append(
                Finding(
                    rule="TIMESTAMP_MALFORMED",
                    severity="medium",
                    message=f"task time does not parse as ISO-8601: {t_raw!r}",
                    path=task.path,
                    locator=f"{task.id}#time",
                    after=str(t_raw),
                )
            )

    for task_id in sorted(corpus.ops_by_task()):
        ops = corpus.ops_by_task()[task_id]
        ordered = sorted(ops, key=lambda r: (parse_ts(r.data.get("recorded_at")), r.name))
        for prev, cur in zip(ordered, ordered[1:]):
            prev_after = prev.data.get("after_record_sha256")
            cur_before = cur.data.get("before_record_sha256")
            if (
                isinstance(prev_after, str)
                and isinstance(cur_before, str)
                and prev_after
                and cur_before
                and prev_after != cur_before
            ):
                findings.append(
                    Finding(
                        rule="CHAIN_BREAK",
                        severity="high",
                        message=(
                            f"chain break: {prev.name} after_record_sha256 {prev_after[:12]}… != "
                            f"{cur.name} before_record_sha256 {cur_before[:12]}…"
                        ),
                        path=cur.path,
                        locator=f"{task_id}:{cur.name}",
                        before=prev_after[:16],
                        after=cur_before[:16],
                    )
                )
    return findings
