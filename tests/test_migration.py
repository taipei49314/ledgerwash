"""Preregistered spec5 migration controls; execute only in remote CI/pool.

These fixtures prove continuity checks, including their self-consistent forgery
limit. They do not execute the audited repository's source code.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from ledgerwash.engine import run_scan
from tests.test_negspace import commit, era_base, git, task, write


MANIFEST = "governance/task-store.json"
TARGET = "governance/tasks/T-800.json"
OLD_TIME = "2025-01-01T00:00:00Z"
LATE = "2026-06-02T00:00:00+00:00"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def migration_repo(tmp_path, case):
    repo = tmp_path / "migration"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "migration@example.invalid")
    git(repo, "config", "user.name", "migration control")
    git(repo, "config", "core.autocrlf", "false")
    write(repo, ".gitattributes", "* -text\n")
    data = task("T-800", time=OLD_TIME, handoff=None, evidence="old task note")
    if case == "escaped-pipes":
        data["description"] = r"old \| task with `a|b` and ``c|d``"
    if case == "unusable-time":
        data["time"] = "2025-01-01T00:0xZ"
    fields = [data[k] for k in ("id", "description", "status", "owner", "time", "evidence")]
    row = ("| " + " | ".join(fields) + " |").encode("utf-8")
    raw = b"# Legacy ledger\n" + row + b"\n"
    if case == "bom-crlf":
        raw = b"\xef\xbb\xbf" + raw.replace(b"\n", b"\r\n")
    if case == "duplicate-id":
        raw += row + b"\n"
    write(repo, "LEDGER.md", "placeholder\n")
    if case != "forged-parent":
        (repo / "LEDGER.md").write_bytes(raw)
    commit(repo, "legacy ledger", date="2025-06-01T00:00:00+00:00")
    older = git(repo, "rev-parse", "HEAD").decode().strip()
    era_base(repo)
    # Explicit residual: a fake pre-era row can be planted in a new parent.
    if case == "forged-parent":
        (repo / "LEDGER.md").write_bytes(raw)
        commit(repo, "invent old ledger row after era begins", date=LATE)
    if case == "missing-parent-ledger":
        (repo / "LEDGER.md").unlink()
        commit(repo, "remove ledger before migration", date=LATE)
    if case == "structured-parent":
        write(repo, MANIFEST, {})
        commit(repo, "pre-existing task store", date=LATE)
    parent = git(repo, "rev-parse", "HEAD").decode().strip()
    if case == "invented-archive":
        data["description"] = "invented replacement description"
        fields[1] = data["description"]
        row = ("| " + " | ".join(fields) + " |").encode("utf-8")
        raw = b"# Legacy ledger\n" + row + b"\n"
    if case == "wrong-row-id":
        raw += row.replace(b"T-800", b"T-801") + b"\n"
        # Establish the full authentic ledger in the actual parent as well.
        (repo / "LEDGER.md").write_bytes(raw)
        parent = commit(repo, "ledger also contains another task", date=LATE)
    archive_sha = "0" * 64 if case == "wrong-archive-digest" else sha(raw)
    archive_path = f"governance/task-history/ledger-before-{archive_sha}.md"
    history = {"kind": "migration", "source": archive_path, "sha256": archive_sha,
               "line": 2, "row_sha256": sha(raw.splitlines()[1])}
    if case == "wrong-row-digest":
        history["row_sha256"] = "0" * 64
    if case == "wrong-row-id":
        history.update(line=3, row_sha256=sha(raw.splitlines()[2]))
    if case == "changed-closure":
        data["time"] = "2024-01-01T00:00:00Z"
    if case == "boolean-line":
        history["line"] = True
    data["history"] = [history]
    migration = {"source": archive_path, "sha256": archive_sha, "at": "2026-06-02T00:00:00Z",
                 "actor": "agent-7", "task_id": "T-800", "source_commit": parent}
    if case == "older-source":
        migration["source_commit"] = older
    manifest = {"schema_version": 1, "kind": "ec-task-store", "hash_format": "canonical-json-utf8",
                "ledger_sha256": sha(raw), "migration": migration,
                "tasks": [{"id": "T-800", "sha256": sha(canonical(data))}]}
    if case == "unsupported-manifest":
        manifest["schema_version"] = True
    if case == "late-label":
        original = deepcopy(data)
        original["history"] = []
        write(repo, TARGET, original)
        commit(repo, "task exists without a migration binding", date=LATE)
    write(repo, TARGET, data)
    if case != "label-only":
        write(repo, MANIFEST, manifest)
        (repo / archive_path).parent.mkdir(parents=True, exist_ok=True)
        (repo / archive_path).write_bytes(raw)
    if case == "symlink-archive":
        # Set a Git tree mode, without needing native Windows symlink privileges.
        git(repo, "add", "-A")
        blob = git(repo, "hash-object", archive_path).decode().strip()
        git(repo, "update-index", "--cacheinfo", f"120000,{blob},{archive_path}")
        git(repo, "commit", "-q", "-m", "non-regular archive", date=LATE)
    else:
        commit(repo, "migration representation", date=LATE)
    birth = git(repo, "rev-parse", "HEAD").decode().strip()
    if case == "changed-archive":
        (repo / archive_path).write_bytes(raw + b"modified\n")
        commit(repo, "archive drift", date=LATE)
    if case == "changed-task":
        data["description"] = "post-migration rewrite"
        manifest["tasks"][0]["sha256"] = sha(canonical(data))
        write(repo, TARGET, data)
        write(repo, MANIFEST, manifest)
        commit(repo, "task drift with fresh manifest hash", date=LATE)
    return repo, birth, parent


CASES = [
    "lf", "bom-crlf", "escaped-pipes", "label-only", "invented-archive",
    "wrong-archive-digest", "wrong-row-digest", "wrong-row-id", "changed-closure",
    "boolean-line", "older-source", "missing-parent-ledger", "late-label",
    "changed-archive", "changed-task", "duplicate-id", "structured-parent",
    "unsupported-manifest", "symlink-archive", "forged-parent", "unusable-time",
]


@pytest.mark.parametrize("case", CASES)
def test_migration_continuity_contract(tmp_path: Path, case):
    repo, birth, parent = migration_repo(tmp_path, case)
    default = run_scan(repo)
    strict = run_scan(repo, require_complete=True)
    assert default["findings"] == strict["findings"]
    assert default["coverage"] == strict["coverage"]
    assert strict["verdict"] == "block"
    assert default["coverage"]["complete"] is False
    target_gaps = {(item["check"], item["status"]) for item in default["coverage"]["checks"]
                   if item["path"] == TARGET}
    assert ("task_profile", "unverified") in target_gaps
    assert ("history_event", "unverified") in target_gaps
    backdated = [f for f in default["findings"] if f["rule"] == "DONE_TIME_BACKDATED"]
    valid = {"lf", "bom-crlf", "escaped-pipes", "forged-parent"}
    if case in valid:
        assert default["findings"] == []
        assert default["verdict"] == "pass"
        assert git(repo, "rev-parse", birth + "^").decode().strip() == parent
    elif case == "unusable-time":
        assert backdated == []
        hits = [f for f in default["findings"] if f["rule"] == "DONE_TIME_UNESTABLISHED"]
        assert [(f["severity"], f["locator"]) for f in hits] == [("high", "T-800:state=DONE")]
        assert default["verdict"] == "block"
    else:
        assert [(f["severity"], f["locator"]) for f in backdated] == [("high", "T-800:state=DONE")]
        assert default["verdict"] == "block"
