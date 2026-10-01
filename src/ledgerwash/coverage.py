"""Mechanical coverage of the supported EC record profile, never authenticity."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import PurePosixPath
import re
import uuid

from ledgerwash.adapters.ec_ledger import CONTRACT_TABLE, RECEIPTS_DIR, TASKS_DIR
from ledgerwash.models import strict_eq
from ledgerwash.rules.common import parse_ts

FIELDS = {"schema_version", "id", "description", "status", "state", "owner", "time",
          "evidence", "handoff", "history"}
STATES = {"TODO", "CLAIMED", "BLOCKED", "DONE", "SUPERSEDED", "CANCELLED"}
TASK_ID = re.compile(r"T-\d+(?:[a-z]|-[a-z]+)?")
HEX = re.compile(r"[0-9a-f]{64}")


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def text(value, empty=False):
    return isinstance(value, str) and "\x00" not in value and (empty or bool(value.strip()))


def safe_path(value):
    if not text(value) or "\\" in value or ":" in value:
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and ".." not in path.parts and str(path) == value and value != "."


def canonical_uuid(value):
    try:
        return isinstance(value, str) and str(uuid.UUID(value)) == value
    except (ValueError, AttributeError, TypeError):
        return False


def operation_event(value):
    return (isinstance(value, dict) and set(value) == {"kind", "source", "hash_format"}
            and value["kind"] == "operation" and value["hash_format"] == "git-commit-bound"
            and safe_path(value["source"]) and str(PurePosixPath(value["source"]).parent) == RECEIPTS_DIR
            and value["source"].endswith(".json"))


def record_shape(record, task_id):
    """Supported task-store shape; migration history has its own unverified profile."""
    if not isinstance(record, dict) or set(record) != FIELDS:
        return False
    if type(record["schema_version"]) is not int or record["schema_version"] != 1:
        return False
    if record["id"] != task_id or not isinstance(task_id, str) or not TASK_ID.fullmatch(task_id):
        return False
    if not all(text(record[key], empty=key in {"owner", "time", "evidence"})
               for key in ("description", "status", "owner", "time", "evidence")):
        return False
    owner = record["owner"]
    if owner != owner.strip() or any(char in owner for char in "\r\n|`"):
        return False
    state = record["state"]
    if not isinstance(state, str) or state not in STATES:
        return False
    if not re.match(r"^" + re.escape(state) + r"\b", record["status"].replace("**", "")):
        return False
    handoff = record["handoff"]
    if handoff is not None:
        if (not isinstance(handoff, dict) or set(handoff) != {"checked_at", "progress", "next_step", "source"}
                or not all(text(value) for value in handoff.values()) or not safe_path(handoff["source"])):
            return False
        stamp = parse_ts(handoff["checked_at"])
        if stamp is None or not handoff["checked_at"].endswith("Z") or stamp.utcoffset().total_seconds() != 0:
            return False
    history = record["history"]
    return (isinstance(history, list) and bool(history) and all(operation_event(item) for item in history)
            and len({item["source"] for item in history}) == len(history))


def build(corpus):
    checks = []

    def add(path, locator, check, status, reason):
        checks.append(dict(path=path, locator=locator, check=check, status=status, reason=reason))

    def verify(path, locator, check, good, reason, bad="unverified"):
        add(path, locator, check, "verified" if good else bad,
            "supported contract verified" if good else reason)

    verify(TASKS_DIR, "", "nonempty_tasks", bool(corpus.tasks), "no loaded tasks")
    verify(RECEIPTS_DIR, "", "nonempty_receipts", bool(corpus.receipts), "no loaded receipts")
    for item in corpus.unparsed:
        add(item["path"], "", "record_parse", "unverified", item["reason"])
    for item in corpus.residuals:
        add(item["path"], "", "adapter_residual", "unverified", item["reason"])

    receipts = {receipt.path: receipt for receipt in corpus.receipts}
    attached = set()
    for task_id, task in sorted(corpus.tasks.items()):
        valid = record_shape(task.data, task_id)
        verify(task.path, task_id, "task_profile", valid, "unsupported task shape or history profile")
        history = task.data.get("history")
        if not isinstance(history, list) or not history:
            add(task.path, task_id, "task_history", "unverified", "nonempty operation history required")
            continue
        previous = None
        for index, event in enumerate(history):
            locator = f"{task_id}#history[{index}]"
            if not operation_event(event):
                add(task.path, locator, "history_event", "unverified", "unsupported operation or migration history event")
                previous = None
                continue
            receipt = receipts.get(event["source"])
            good = receipt is not None and receipt.data.get("task_id") == task_id
            verify(task.path, locator, "history_receipt", good, "history receipt missing or task identity differs", "mismatch")
            if not good:
                previous = None
                continue
            attached.add(receipt.path)
            before, after = receipt.data.get("before_record"), receipt.data.get("after_record")
            bound = isinstance(after, dict) and strict_eq(after.get("history"), history[:index + 1])
            verify(task.path, locator, "history_prefix", bound, "receipt after history differs from current history prefix", "mismatch")
            if index:
                chain = isinstance(previous, dict) and isinstance(before, dict) and strict_eq(previous, before)
            else:
                request = receipt.data.get("request")
                chain = (before is None and "before_record" in receipt.data and isinstance(request, dict)
                         and request.get("operation") == "claim")
            verify(task.path, locator, "record_chain", chain, "before record does not continue the prior operation", "mismatch")
            previous = after
        verify(task.path, task_id, "current_record", isinstance(previous, dict) and strict_eq(previous, task.data),
               "last attached after_record does not match current task", "mismatch")

    anchors = corpus.epoch.commits([value for receipt in corpus.receipts
                                  for value in (receipt.birth, receipt.data.get("expected_head"))])
    blobs = {}
    request_ids = {}
    for receipt in corpus.receipts:
        data, path, locator = receipt.data, receipt.path, receipt.name
        supported = type(data.get("schema_version")) is int and data.get("schema_version") == 2 and data.get("kind") in (
            "ec-task-operation", "ec-task-repair")
        verify(path, locator, "receipt_profile", supported, "unsupported legacy or migration receipt profile")
        verify(path, locator, "receipt_attached", path in attached, "receipt not attached to its current task history", "mismatch")
        task_id = data.get("task_id")
        verify(path, locator, "task_identity", isinstance(task_id, str) and task_id in corpus.tasks,
               "receipt task_id must name a loaded task")
        request = data.get("request")
        if not isinstance(request, dict):
            add(path, locator, "request_profile", "unverified", "request object required")
            request = {}
        verify(path, locator, "recorded_at", parse_ts(data.get("recorded_at")) is not None, "recorded_at missing or unorderable")
        verify(path, locator, "request_at", parse_ts(request.get("at")) is not None, "request.at missing or unorderable")
        verify(path, locator, "birth_commit", receipt.birth in anchors, "receipt birth commit unavailable")
        if receipt.birth in anchors:
            verify(path, locator, "receipt_immutable", corpus.epoch.blob_at(receipt.birth, path) == corpus.epoch.read_bytes(path),
                   "receipt bytes changed since containing birth commit", "mismatch")
        expected = data.get("expected_head")
        verify(path, locator, "expected_commit", isinstance(expected, str) and expected in anchors, "expected_head commit unavailable")
        transport = request.get("expected")
        verify(path, locator, "expected_head_binding", isinstance(transport, dict) and transport.get("head") == expected
               and isinstance(expected, str), "request.expected.head differs from receipt expected_head", "mismatch")
        verify(path, locator, "operation_kind", request.get("operation") in (
            "claim", "progress", "finish", "handoff", "resume", "retire", "repair"), "unsupported request operation")
        operation_id = data.get("operation_id")
        verify(path, locator, "operation_identity", canonical_uuid(operation_id) and receipt.name == str(operation_id) + ".json",
               "operation UUID and receipt filename must agree", "mismatch")
        if data.get("kind") == "ec-task-operation":
            request_id = data.get("request_id")
            identity = canonical_uuid(request_id) and request.get("request_id") == request_id and request.get("operation_id") == operation_id
            verify(path, locator, "request_identity", identity, "receipt/request UUID identity differs", "mismatch")
            if canonical_uuid(request_id):
                request_ids.setdefault(request_id, []).append(path)
            intent = deepcopy(request)
            intent.pop("operation_id", None)
            intent.pop("at", None)
            intent_shape = True
            for field, transport in (("expected", "head"), ("summary", "checked_at")):
                value = intent.get(field, {})
                if not isinstance(value, dict):
                    intent_shape = False
                else:
                    value.pop(transport, None)
            verify(path, locator, "intent_digest", intent_shape and data.get("intent_sha256") == digest(intent),
                   "intent digest does not match request canonical bytes", "mismatch")
        for field in ("before_record", "after_record"):
            record = data.get(field)
            is_null = field == "before_record" and record is None and field in data and request.get("operation") == "claim"
            shape = is_null or record_shape(record, task_id)
            verify(path, locator, field + "_profile", shape, "explicit supported record required; null before only for claim")
            want = data.get(field + "_sha256")
            matches = field + "_sha256" in data and ((is_null and want is None) or (
                isinstance(record, dict) and isinstance(want, str) and HEX.fullmatch(want) and want == digest(record)))
            verify(path, locator, field + "_digest", bool(matches), "record digest missing or differs from canonical bytes", "mismatch")
        before, after = data.get("before_record"), data.get("after_record")
        prior_history = before.get("history") if isinstance(before, dict) else [] if before is None else None
        event = {"kind": "operation", "hash_format": "git-commit-bound", "source": path}
        bound = ("before_record" in data and isinstance(prior_history, list) and isinstance(after, dict)
                 and strict_eq(after.get("history"), prior_history + [event]))
        verify(path, locator, "receipt_history", bound, "after history must append exactly this receipt", "mismatch")
        if data.get("kind") == "ec-task-repair":
            repair = request.get("operation") == "repair" and isinstance(before, dict) and isinstance(after, dict) and all(
                strict_eq(before.get(key), after.get(key)) for key in ("id", "owner", "description", "state", "status"))
            verify(path, locator, "repair_identity", repair, "repair must preserve task identity and state", "mismatch")

        sources, entries = request.get("sources"), data.get("source_fingerprints")
        source_shape = isinstance(sources, list) and bool(sources) and all(safe_path(source) for source in sources)
        entry_shape = isinstance(entries, list) and bool(entries) and all(isinstance(entry, dict) for entry in entries)
        verify(path, locator, "source_list", source_shape, "nonempty safe request.sources required")
        verify(path, locator, "fingerprint_list", entry_shape, "nonempty source_fingerprints objects required")
        if not source_shape or not entry_shape:
            continue
        declared = [entry.get("source") for entry in entries]
        unique = len(set(sources)) == len(sources) and all(safe_path(value) for value in declared)
        unique = unique and len(set(declared)) == len(declared) and set(sources) == set(declared)
        verify(path, locator, "source_contract_set", unique, "source lists must be unique and correspond one-to-one", "mismatch")
        for index, entry in enumerate(entries):
            key = f"{locator}#source_fingerprints[{index}]"
            hf, origin = entry.get("hash_format"), entry.get("origin")
            kind = CONTRACT_TABLE.get((hf, origin)) if isinstance(hf, str) and isinstance(origin, str) else None
            source, want = entry.get("source"), entry.get("sha256")
            good = kind is not None and safe_path(source) and isinstance(want, str) and HEX.fullmatch(want)
            verify(path, key, "source_contract", bool(good), "unsupported fingerprint contract or source/digest shape")
            if not good:
                continue
            anchor = receipt.birth if kind == "birth" else expected
            if not isinstance(anchor, str) or anchor not in anchors:
                add(path, key, "source_bytes", "unverified", "fingerprint anchor commit unavailable")
                continue
            blob_key = (anchor, source)
            if blob_key not in blobs:
                blobs[blob_key] = corpus.epoch.blob_at(anchor, source)
            blob = blobs[blob_key]
            if blob is None:
                add(path, key, "source_bytes", "unverified", "source blob missing at documented anchor")
            else:
                verify(path, key, "source_bytes", hashlib.sha256(blob).hexdigest() == want,
                       "source digest differs from anchor blob bytes", "mismatch")
    for request_id, paths in sorted(request_ids.items()):
        if len(paths) > 1:
            for path in paths:
                add(path, request_id, "request_unique", "mismatch", "ordinary request UUID reused by multiple receipts")
    checks.sort(key=lambda item: (item["path"], item["locator"], item["check"], item["reason"]))
    counts = {status: sum(item["status"] == status for item in checks) for status in ("verified", "unverified", "mismatch")}
    complete = counts["unverified"] == counts["mismatch"] == 0
    return {"version": 1, "complete": complete, "counts": counts, "checks": checks,
            "scope": "supported EC task/ordinary-repair receipt inputs, records, history and source bytes",
            "limitations": ["execution authenticity and decision authority unverified", "timestamps are untrusted claims",
                            "legacy and migration binding unsupported", "other evidence paths outside adapter scope"]}
