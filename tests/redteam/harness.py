"""Fixture construction only; original red-team cases import these helpers."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess

SRC_REL = "evidence/results/analysis.csv"
SRC_BYTES = b"task,verdict\nT-100,PASS\nT-101,PASS\n"


def git(repo, *args):
    env = dict(os.environ, GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
               GIT_AUTHOR_DATE="2026-09-28T00:00:00Z",
               GIT_COMMITTER_DATE="2026-09-28T00:00:00Z")
    for key in list(env):
        if key.startswith("GIT_CONFIG_KEY_") or key.startswith("GIT_CONFIG_VALUE_"):
            env.pop(key)
    env.pop("GIT_CONFIG_COUNT", None)
    env.pop("GIT_DIR", None)
    env.pop("GIT_WORK_TREE", None)
    return subprocess.run(["git", "-c", "core.hooksPath=" + os.devnull, *args],
                          cwd=repo, env=env, capture_output=True, check=True, timeout=60).stdout


def w(repo, rel, data):
    target = repo / rel
    if data is None:
        target.unlink(missing_ok=True)
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, bytes):
        target.write_bytes(data)
    else:
        target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8", newline="\n")


def commit(repo, msg, amend=False):
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", msg, *(["--amend"] if amend else []))


def task(tid, *, state="DONE", status="DONE", time="2026-09-28T12:00:00Z", **extra):
    data = {"schema_version": 1, "status": status, "state": state,
            "time": time, "owner": "agent-7", "title": f"task {tid}"}
    data.update(extra)
    return data


def receipt(tid, *, recorded_at="2026-09-28T10:00:00Z", at="2026-09-28T09:00:00Z",
            before=None, after=None, fps=None, expected_head=None, **extra):
    data = {"task_id": tid, "recorded_at": recorded_at,
            "request": {"actor": "agent-7", "at": at, "op": "run_analysis"},
            "before_record_sha256": before or "0" * 64,
            "after_record_sha256": after or "1" * 64}
    if fps is not None:
        data["source_fingerprints"] = fps
    if expected_head is not None:
        data["expected_head"] = expected_head
    data.update(extra)
    return data


def fp_entry(source=SRC_REL, digest=None, hf="raw-git-blob-bytes",
             origin="new-utf8-blob-in-containing-commit"):
    return {"hash_format": hf, "origin": origin, "source": source,
            "sha256": digest or "f" * 64}


def sha_of(data):
    return hashlib.sha256(data.encode("utf-8") if isinstance(data, str) else data).hexdigest()


def std_base(with_fingerprints=True, n_receipts=1, **_):
    def plan(repo):
        w(repo, ".gitattributes", b"* -text\n")
        w(repo, SRC_REL, SRC_BYTES)
        commit(repo, "sources")
        fps = [fp_entry(digest=sha_of(SRC_BYTES))] if with_fingerprints else None
        rec = receipt("T-100", fps=fps)
        rec["after_record_sha256"] = sha_of(json.dumps({"task_id": "T-100", "v": 1}))
        w(repo, "governance/tasks/T-100.json", task("T-100"))
        w(repo, "evidence/task-operations/r1.json", rec)
        commit(repo, "ledger")
    return plan


def build_repo(path, plan):
    path.mkdir(parents=True, exist_ok=False)
    template = path.parent / "empty-template"
    template.mkdir(exist_ok=True)
    git(path, "init", "-q", "-b", "main", "--template=" + str(template))
    git(path, "config", "user.email", "rt@rt.local")
    git(path, "config", "user.name", "rt")
    git(path, "config", "core.autocrlf", "false")
    plan(path)
    return git(path, "rev-parse", "HEAD").decode("ascii").strip()


def original_cases():
    from tests.redteam import cases
    entries = []
    def case(case_id, category, plan, hypothesis, note=""):
        entries.append({"id": case_id, "category": category, "plan": plan, "note": note})
    for name in ("register", "register_more", "register_last", "register_final", "register_a4c"):
        getattr(cases, name)(case, std_base)
    if len(entries) != 21 or len({item["id"] for item in entries}) != 21:
        raise ValueError("the preserved original suite must have 21 unique cases")
    if sum(item["category"] == "control" for item in entries) != 3:
        raise ValueError("the preserved suite must have three controls")
    return entries
