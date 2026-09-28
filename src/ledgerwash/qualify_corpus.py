"""Deterministic synthetic EC-format ledger with planted weaknesses.

This is the red-by-design fixture: `ledgerwash qualify` builds it in a temp dir,
scans it at HEAD, and asserts EXPECTED — the frozen finding matrix. A rule that
stops firing, fires twice, or fires on the clean control fails qualification
instead of passing silently. Content is fully deterministic: fixed timestamps in
records, fixed git author/committer dates, no clock anywhere.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

# Expected finding counts at HEAD for the planted corpus (SPEC §4 coverage).
EXPECTED = {
    "CHAIN_BREAK": 1,
    "CONTRACT_UNDOCUMENTED": 2,
    "DANGLING_REF": 1,
    "FP_HASH_MISMATCH": 1,
    "FP_SOURCE_MISSING": 1,
    "PIN_LOCAL_MISSING": 1,
    "PIN_UNROUTABLE": 1,
    "POST_HOC_DRIFT": 1,
    "RECORD_UNPARSEABLE": 1,
    "STATUS_STATE_MISMATCH": 1,
    "TIMELINE_INVERSION": 1,
    "TIMESTAMP_MALFORMED": 1,
}

_NOTE_V1 = "clean note v1\n"
_CHANGING_V1 = "changing v1\n"
_CHANGING_V2 = "changing v2\n"
_DIGEST_NOTE = hashlib.sha256(_NOTE_V1.encode("utf-8")).hexdigest()
_DIGEST_CHANGING_V1 = hashlib.sha256(_CHANGING_V1.encode("utf-8")).hexdigest()
_BARE_PIN = "a" * 40  # referenced in a task record; not an object of this repo
_FAKE_HEAD = "b" * 40  # planted as expected_head; not an object of this repo


def _sha256_obj(obj) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def _write(repo: Path, rel: str, content: str):
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def _write_json(repo: Path, rel: str, obj):
    _write(repo, rel, json.dumps(obj, sort_keys=True, ensure_ascii=False, indent=2) + "\n")


def _git(repo: Path, *args: str, date: str | None = None):
    env = dict(os.environ)
    env.update(
        {
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_AUTHOR_DATE": date or "2026-01-01T00:00:00+00:00",
            "GIT_COMMITTER_DATE": date or "2026-01-01T00:00:00+00:00",
        }
    )
    proc = subprocess.run(["git", *args], cwd=repo, env=env, capture_output=True, input=b"")
    if proc.returncode != 0:
        raise RuntimeError(
            f"fixture git {' '.join(args)} failed: {proc.stderr.decode('utf-8', 'replace')}"
        )


def _commit(repo: Path, message: str, date: str):
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", message, date=date)


def _receipt(base: dict, task_id: str, recorded_at: str, request_at: str, actor: str) -> dict:
    receipt = {
        "kind": "ec-task-operation",
        "task_id": task_id,
        "recorded_at": recorded_at,
        "request": {"at": request_at, "actor": actor, "operation": "update"},
        "schema_version": 2,
    }
    receipt.update(base)
    return receipt


def _task(task_id: str, state: str, status: str, time: str, description: str) -> dict:
    return {
        "schema_version": 1,
        "id": task_id,
        "owner": "human/nelson",
        "state": state,
        "status": status,
        "time": time,
        "description": description,
    }


def build_corpus(root: Path, planted: bool = True) -> Path:
    """Build the fixture repo under `root`; returns the repo path."""
    repo = root
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.name", "ledgerwash")
    _git(repo, "config", "user.email", "ledgerwash@example.invalid")
    _git(repo, "config", "core.autocrlf", "false")
    _git(repo, "config", "commit.gpgsign", "false")

    t900_c1 = {
        "schema_version": 1,
        "id": "T-900",
        "owner": "human/nelson",
        "state": "CLAIMED",
        "status": "**CLAIMED**",
        "time": "2026-01-01T00:00:00Z",
        "description": "clean control task",
        "handoff": {"checked_at": "2026-01-01T00:00:00Z", "progress": "claim recorded"},
        "history": [
            {"hash_format": "git-commit-bound", "kind": "operation",
             "source": "evidence/task-operations/r900a.json"}
        ],
    }
    t900_final = {
        **t900_c1,
        "state": "DONE",
        "status": "**DONE**",
        "time": "2026-01-02T00:00:00Z",
        "handoff": {"checked_at": "2026-01-02T00:00:00Z", "progress": "done, verified"},
        "history": [
            {"hash_format": "git-commit-bound", "kind": "operation",
             "source": "evidence/task-operations/r900a.json"},
            {"hash_format": "git-commit-bound", "kind": "operation",
             "source": "evidence/task-operations/r900b.json"},
        ],
    }
    r900a = _receipt(
        {
            "source_fingerprints": [
                {"hash_format": "raw-git-blob-bytes",
                 "origin": "new-utf8-blob-in-containing-commit",
                 "source": "evidence/notes/clean-note.md", "sha256": _DIGEST_NOTE}
            ],
            "before_record_sha256": None,
            "after_record_sha256": _sha256_obj(t900_c1),
            "after_record": t900_c1,
        },
        "T-900", "2026-01-01T00:00:10Z", "2026-01-01T00:00:00Z", "human/nelson",
    )
    r900b = _receipt(
        {
            "before_record_sha256": _sha256_obj(t900_c1),
            "after_record_sha256": _sha256_obj(t900_final),
            "after_record": t900_final,
        },
        "T-900", "2026-01-02T00:00:10Z", "2026-01-02T00:00:00Z", "human/nelson",
    )

    _write(repo, "evidence/notes/clean-note.md", _NOTE_V1)
    _write_json(repo, "governance/tasks/T-900.json", t900_c1)
    _write_json(repo, "evidence/task-operations/r900a.json", r900a)
    _write(repo, "CURRENT.md", "# CURRENT\n\n| T-900 | clean control | CLAIMED |\n")
    _write_json(
        repo,
        "governance/github-snapshot.json",
        {"expires_at": "2026-01-05T00:00:00Z", "owner": "taipei49314"},
    )

    if planted:
        _write_json(
            repo, "governance/tasks/T-901.json",
            _task("T-901", "DONE", "**DONE**", "2026-01-01T00:00:00Z",
                  "references docs/gone-path.md which was never created"),
        )
        _write_json(
            repo, "governance/tasks/T-902.json",
            _task("T-902", "DONE", "**DONE**", "2026-01-01T00:00:00Z",
                  "fingerprint cases"),
        )
        _write_json(
            repo, "governance/tasks/T-903.json",
            _task("T-903", "DONE", "**DONE**", "2026-01-01T00:00:00Z",
                  "timeline and chain cases"),
        )
        _write_json(
            repo, "governance/tasks/T-904.json",
            _task("T-904", "DONE", "**DONE**", "2026-01-01T00:00:00Z",
                  "malformed timestamp case"),
        )
        _write_json(
            repo, "governance/tasks/T-905.json",
            _task("T-905", "CLAIMED", "**CLAIMED**", "2026-01-01T00:00:00Z",
                  "post-hoc drift case"),
        )
        _write_json(
            repo, "governance/tasks/T-906.json",
            _task("T-906", "DONE", "**DONE**", "2026-01-01T00:00:00Z",
                  f"pins commit {_BARE_PIN} from another repository"),
        )
        _write(repo, "governance/tasks/T-907.json", "{oops")  # not JSON
        _write_json(
            repo, "governance/tasks/T-908.json",
            _task("T-908", "DONE", "DONE（兩台）", "2026-01-01T00:00:00Z",
                  "CJK-annotated status; must normalize and stay silent"),
        )
        _write_json(
            repo, "governance/tasks/T-909.json",
            _task("T-909", "CLAIMED", "**DONE**", "2026-01-01T00:00:00Z",
                  "status/state mismatch case"),
        )
        _write(repo, "evidence/notes/changing.md", _CHANGING_V1)
    _commit(repo, "c1: tasks, first evidence, first receipt", "2026-01-01T00:00:00+00:00")
    sha_c1 = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, check=True
    ).stdout.decode("ascii").strip()

    _write_json(repo, "governance/tasks/T-900.json", t900_final)
    _write_json(repo, "evidence/task-operations/r900b.json", r900b)
    if planted:
        _write(repo, "evidence/notes/changing.md", _CHANGING_V2)
        _write_json(repo, "evidence/task-operations/r902a.json", _receipt(
            {"expected_head": sha_c1,
             "source_fingerprints": [
                 {"hash_format": "raw-git-blob-bytes", "origin": "expected-head-blob",
                  "source": "evidence/notes/clean-note.md", "sha256": _DIGEST_NOTE}]},
            "T-902", "2026-01-02T00:00:10Z", "2026-01-02T00:00:00Z", "agent/mimo",
        ))  # era-valid at expected_head: silent
        _write_json(repo, "evidence/task-operations/r902b.json", _receipt(
            {"expected_head": sha_c1,
             "source_fingerprints": [
                 {"hash_format": "raw-git-blob-bytes", "origin": "expected-head-blob",
                  "source": "evidence/notes/clean-note.md", "sha256": "0" * 64}]},
            "T-902", "2026-01-02T00:00:11Z", "2026-01-02T00:00:00Z", "agent/mimo",
        ))  # FP_HASH_MISMATCH at expected_head
        _write_json(repo, "evidence/task-operations/r902c.json", _receipt(
            {"source_fingerprints": [
                {"hash_format": "raw-git-blob-bytes", "origin": "mystery-pre-image",
                 "source": "evidence/notes/changing.md", "sha256": _DIGEST_CHANGING_V1}]},
            "T-902", "2026-01-02T00:00:12Z", "2026-01-02T00:00:00Z", "agent/mimo",
        ))  # undocumented; matches at birth^ (pre-image): CONTRACT_UNDOCUMENTED only
        _write_json(repo, "evidence/task-operations/r902d.json", _receipt(
            {"source_fingerprints": [
                {"hash_format": "raw-git-blob-bytes", "origin": "mystery-nothing",
                 "source": "evidence/notes/changing.md", "sha256": "f" * 64}]},
            "T-902", "2026-01-02T00:00:13Z", "2026-01-02T00:00:00Z", "agent/mimo",
        ))  # undocumented; matches nothing: CONTRACT_UNDOCUMENTED
        _write_json(repo, "evidence/task-operations/r902e.json", _receipt(
            {"source_fingerprints": [
                {"hash_format": "raw-git-blob-bytes",
                 "origin": "new-utf8-blob-in-containing-commit",
                 "source": "evidence/notes/never-created.md", "sha256": "1" * 64}]},
            "T-902", "2026-01-02T00:00:14Z", "2026-01-02T00:00:00Z", "agent/mimo",
        ))  # FP_SOURCE_MISSING at birth
        _write_json(repo, "evidence/task-operations/r903a.json", _receipt(
            {"before_record_sha256": None, "after_record_sha256": "d" * 64},
            "T-903", "2026-01-02T08:00:00Z", "2026-01-02T12:00:00Z", "agent/mimo",
        ))  # TIMELINE_INVERSION (recorded before requested)
        _write_json(repo, "evidence/task-operations/r904a.json", _receipt(
            {}, "T-904", "not-a-timestamp", "2026-01-02T00:00:00Z", "agent/mimo",
        ))  # TIMESTAMP_MALFORMED
    _commit(repo, "c2: done ops, fingerprint cases, timeline cases", "2026-01-02T00:00:00+00:00")

    if planted:
        _write_json(repo, "evidence/task-operations/r903b.json", _receipt(
            {"before_record_sha256": "e" * 64, "after_record_sha256": "5" * 64},
            "T-903", "2026-01-03T00:00:10Z", "2026-01-03T00:00:00Z", "agent/mimo",
        ))  # CHAIN_BREAK (prev after d… != cur before e…)
        _write_json(repo, "evidence/task-operations/r905a.json", _receipt(
            {"after_record": _task("T-905", "CLAIMED", "**CLAIMED**",
                                   "2026-01-01T00:00:00Z", "post-hoc drift case"),
             "after_record_sha256": "6" * 64},
            "T-905", "2026-01-03T00:00:10Z", "2026-01-03T00:00:00Z", "agent/mimo",
        ))
        _write_json(repo, "evidence/task-operations/r906a.json", _receipt(
            {"expected_head": _FAKE_HEAD},
            "T-906", "2026-01-03T00:00:11Z", "2026-01-03T00:00:00Z", "agent/mimo",
        ))  # PIN_LOCAL_MISSING (expected_head not an object)
        (repo / "evidence/notes/clean-note.md").unlink()  # era-awareness: r900a stays silent
    _commit(repo, "c3: chain break, drift anchor, pin cases; clean-note removed",
            "2026-01-03T00:00:00+00:00")

    if planted:
        _write_json(
            repo, "governance/tasks/T-905.json",
            _task("T-905", "DONE", "**DONE**", "2026-01-04T00:00:00Z",
                  "post-hoc drift case"),  # direct hand edit, no receipt -> POST_HOC_DRIFT
        )
        _commit(repo, "c4: direct task edit outside the operation chain",
                "2026-01-04T00:00:00+00:00")
    return repo
