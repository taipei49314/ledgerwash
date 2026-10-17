"""TIMESTAMP_MALFORMED / TIMELINE_INVERSION / CHAIN_BREAK."""

from __future__ import annotations

from ledgerwash.models import Finding

from .common import is_redacted_ts, ordered_ops, parse_ts, present_but_unparseable


def _timestamp_finding(corpus_receipt_path, locator, raw_value, task_id=None) -> Finding:
    if is_redacted_ts(raw_value):
        return Finding(
            rule="TIMESTAMP_REDACTED",
            severity="info",
            message=(
                f"timestamp is redacted (digit-masked or a range), not orderable: {raw_value!r}"
            ),
            path=corpus_receipt_path,
            locator=locator,
            after=str(raw_value),
        )
    return Finding(
        rule="TIMESTAMP_MALFORMED",
        severity="warn",
        message=f"timestamp does not parse as ISO-8601: {raw_value!r}",
        path=corpus_receipt_path,
        locator=locator,
        after=str(raw_value),
    )


def run(corpus) -> list[Finding]:
    findings: list[Finding] = []

    for receipt in corpus.receipts:
        rec_raw = receipt.data.get("recorded_at")
        rec = parse_ts(rec_raw)
        if rec is None:
            corpus.residuals.append({
                "path": receipt.path,
                "reason": "operation ordering and anchor verification skipped: "
                          "recorded_at is missing or unparseable",
            })
        if present_but_unparseable(rec_raw):
            findings.append(
                _timestamp_finding(
                    receipt.path, f"{receipt.name}#recorded_at", rec_raw
                )
            )
        request = receipt.data.get("request")
        req_raw = request.get("at") if isinstance(request, dict) else None
        req = parse_ts(req_raw)
        if present_but_unparseable(req_raw):
            findings.append(
                _timestamp_finding(receipt.path, f"{receipt.name}#request.at", req_raw)
            )
        if rec is not None and req is not None and rec < req:
            task_id = receipt.data.get("task_id")
            shown = task_id if isinstance(task_id, str) and task_id else "?"
            findings.append(
                Finding(
                    rule="TIMELINE_INVERSION",
                    severity="high",
                    message=(
                        f"task {shown}: recorded_at {rec_raw} is earlier than "
                        f"request.at {req_raw}; clock or timezone mislabeling suspected"
                    ),
                    path=receipt.path,
                    locator=f"{shown}:{receipt.name}",
                    before=str(req_raw),
                    after=str(rec_raw),
                )
            )

    for task in corpus.tasks.values():
        t_raw = task.data.get("time")
        if present_but_unparseable(t_raw):
            findings.append(
                _timestamp_finding(task.path, f"{task.id}#time", t_raw)
            )

    grouped = corpus.ops_by_task()
    for task_id in sorted(grouped):
        ordered = ordered_ops(grouped[task_id])
        if ordered is None:
            continue
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
