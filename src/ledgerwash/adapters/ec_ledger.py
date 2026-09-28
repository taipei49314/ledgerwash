"""ec-ledger adapter: the only module that knows the EC ledger layout (SPEC §3)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from ledgerwash.epoch import Epoch

TASKS_DIR = "governance/tasks"
RECEIPTS_DIR = "evidence/task-operations"
SNAPSHOT_PATH = "governance/github-snapshot.json"
CURRENT_PATH = "CURRENT.md"

# Reference grammar for task-record strings (SPEC §3).
REFERENCE_RE = r"(?:evidence|docs|governance|tools)/[A-Za-z0-9._/\-]+"

# Closed fingerprint contract table (SPEC §3): (hash_format, origin) -> anchor kind.
CONTRACT_TABLE = {
    ("raw-git-blob-bytes", "new-utf8-blob-in-containing-commit"): "birth",
    ("raw-git-blob-bytes", "expected-head-blob"): "expected_head",
}


@dataclass
class TaskRec:
    id: str
    path: str
    data: dict


@dataclass
class Receipt:
    path: str
    name: str
    data: dict
    birth: str | None = None


@dataclass
class Corpus:
    epoch: Epoch
    tasks: dict[str, TaskRec] = field(default_factory=dict)
    receipts: list[Receipt] = field(default_factory=list)
    births: dict[str, str] = field(default_factory=dict)
    unparsed: list[dict] = field(default_factory=list)
    residuals: list[dict] = field(default_factory=list)
    snapshot: dict | None = None
    current_text: str | None = None

    def ops_by_task(self) -> dict[str, list[Receipt]]:
        grouped: dict[str, list[Receipt]] = {}
        for receipt in self.receipts:
            task_id = receipt.data.get("task_id")
            if isinstance(task_id, str) and task_id:
                grouped.setdefault(task_id, []).append(receipt)
        return grouped


def load(epoch: Epoch) -> Corpus:
    corpus = Corpus(epoch=epoch)

    for name in sorted(epoch.list_dir(TASKS_DIR)):
        if not (name.startswith("T-") and name.endswith(".json")):
            continue
        rel = f"{TASKS_DIR}/{name}"
        raw = epoch.read_bytes(rel)
        if raw is None:
            corpus.residuals.append({"path": rel, "reason": "task file unreadable at epoch"})
            continue
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            corpus.unparsed.append({"path": rel, "reason": f"json: {exc}"})
            continue
        if not isinstance(data, dict):
            corpus.unparsed.append({"path": rel, "reason": "task record is not a JSON object"})
            continue
        task_id = name[: -len(".json")]
        corpus.tasks[task_id] = TaskRec(id=task_id, path=rel, data=data)
        if data.get("schema_version") != 1:
            corpus.residuals.append(
                {
                    "path": rel,
                    "reason": f"schema_version {data.get('schema_version')!r} != 1",
                }
            )
        if not isinstance(data.get("status"), str) or not isinstance(data.get("state"), str):
            corpus.residuals.append({"path": rel, "reason": "status/state not both strings"})

    corpus.births = epoch.birth_map(RECEIPTS_DIR)
    for name in sorted(epoch.list_dir(RECEIPTS_DIR)):
        if not name.endswith(".json"):
            continue
        rel = f"{RECEIPTS_DIR}/{name}"
        raw = epoch.read_bytes(rel)
        if raw is None:
            corpus.residuals.append({"path": rel, "reason": "receipt unreadable at epoch"})
            continue
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            corpus.unparsed.append({"path": rel, "reason": f"json: {exc}"})
            continue
        if not isinstance(data, dict):
            corpus.unparsed.append({"path": rel, "reason": "receipt is not a JSON object"})
            continue
        if not isinstance(data.get("task_id"), str):
            corpus.residuals.append({"path": rel, "reason": "receipt has no string task_id"})
        corpus.receipts.append(Receipt(path=rel, name=name, data=data, birth=corpus.births.get(rel)))

    snap_raw = epoch.read_bytes(SNAPSHOT_PATH)
    if snap_raw is not None:
        try:
            snapshot = json.loads(snap_raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            corpus.residuals.append({"path": SNAPSHOT_PATH, "reason": "snapshot json unparseable"})
        else:
            corpus.snapshot = snapshot if isinstance(snapshot, dict) else None

    corpus.current_text = epoch.read_text(CURRENT_PATH)
    return corpus
