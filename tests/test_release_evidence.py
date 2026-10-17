"""Release witness rejection controls; executed only in hosted CI/EC pool."""
from copy import deepcopy
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import zipfile

import pytest

from workloads.release_verify.common import (OS_NAMES, PYTHONS, RAW_NAMES,
                                            artifact_name, check_metadata,
                                            compare_cells, junit_counts, loads, read_zip)


def metadata():
    source, run_id, attempt = "a" * 40, "123456789", "1"
    run = {"id": int(run_id), "run_attempt": 1, "repository": {"id": 1392503057,
           "full_name": "taipei49314/ledgerwash"}, "head_repository": {"id": 1392503057},
           "workflow_id": 369035271, "path": ".github/workflows/ci.yml", "head_sha": source,
           "event": "pull_request", "status": "completed", "conclusion": "success"}
    jobs, artifacts = [], []
    for i, (os_name, python) in enumerate((o, p) for o in OS_NAMES for p in PYTHONS):
        jobs.append({"id": i + 1, "name": f"test ({os_name}, {python})", "run_id": int(run_id),
                     "run_attempt": 1, "head_sha": source, "status": "completed", "conclusion": "success",
                     "labels": [os_name], "started_at": "2026-10-17T12:00:00Z",
                     "completed_at": "2026-10-17T12:05:00Z"})
        artifacts.append({"id": i + 100, "name": artifact_name(run_id, attempt, os_name, python),
                          "workflow_run": {"id": int(run_id), "head_sha": source,
                                           "repository_id": 1392503057, "head_repository_id": 1392503057},
                          "expired": False, "digest": "sha256:" + "b" * 64, "size_in_bytes": 100,
                          "created_at": "2026-10-17T12:04:00Z"})
    return source, run_id, attempt, run, {"total_count": 9, "jobs": jobs}, {"total_count": 9, "artifacts": artifacts}


def test_exact_nine_cell_metadata_is_accepted():
    assert len(check_metadata(*metadata())) == 9


@pytest.mark.parametrize("fault", ["source", "attempt", "workflow", "foreign-repo", "failed-run",
                                  "missing-job", "duplicate-job", "failed-job", "job-source",
                                  "self-hosted", "no-digest", "expired", "wrong-artifact-source",
                                  "outside-job", "duplicate-artifact", "missing-artifact"])
def test_release_metadata_rejects_mismatched_primary_evidence(fault):
    args = list(deepcopy(metadata()))
    run, jobs, artifacts = args[3:]
    if fault == "source": run["head_sha"] = "c" * 40
    elif fault == "attempt": run["run_attempt"] = 2
    elif fault == "workflow": run["workflow_id"] = 1
    elif fault == "foreign-repo": run["head_repository"]["id"] = 1
    elif fault == "failed-run": run["conclusion"] = "failure"
    elif fault == "missing-job": jobs["jobs"].pop()
    elif fault == "duplicate-job": jobs["jobs"][1] = deepcopy(jobs["jobs"][0])
    elif fault == "failed-job": jobs["jobs"][0]["conclusion"] = "skipped"
    elif fault == "job-source": jobs["jobs"][0]["head_sha"] = "c" * 40
    elif fault == "self-hosted": jobs["jobs"][0]["labels"] = ["self-hosted"]
    elif fault == "no-digest": artifacts["artifacts"][0]["digest"] = None
    elif fault == "expired": artifacts["artifacts"][0]["expired"] = True
    elif fault == "wrong-artifact-source": artifacts["artifacts"][0]["workflow_run"]["head_sha"] = "c" * 40
    elif fault == "outside-job": artifacts["artifacts"][0]["created_at"] = "2026-10-17T12:06:00Z"
    elif fault == "duplicate-artifact": artifacts["artifacts"][1] = deepcopy(artifacts["artifacts"][0])
    elif fault == "missing-artifact": artifacts["artifacts"].pop()
    with pytest.raises(ValueError):
        check_metadata(*args)


def make_zip(fault=None):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in (*RAW_NAMES, "receipt.json", "suite.xml"):
            if fault == "missing" and name == "suite.xml":
                continue
            if fault == "symlink" and name == "receipt.json":
                info = zipfile.ZipInfo(name)
                info.create_system = 3
                info.external_attr = (stat.S_IFLNK | 0o777) << 16
                archive.writestr(info, b"elsewhere")
            else:
                archive.writestr(name, b"{}\n")
        if fault == "traversal": archive.writestr("../escape", b"bad")
        if fault == "case-alias": archive.writestr("Receipt.json", b"bad")
    return stream.getvalue()


def test_release_zip_has_exact_bounded_member_set():
    assert set(read_zip(make_zip())) == {*RAW_NAMES, "receipt.json", "suite.xml"}


@pytest.mark.parametrize("fault", ["missing", "symlink", "traversal", "case-alias"])
def test_release_zip_rejects_unsafe_or_incomplete_members(fault):
    with pytest.raises(ValueError):
        read_zip(make_zip(fault))


def test_comparison_does_not_normalize_changed_raw_bytes():
    cells = [{name: b'{"target":"ledger"}\n' for name in RAW_NAMES} for _ in range(9)]
    assert len(compare_cells(cells)) == 40
    cells[-1][RAW_NAMES[0]] = b'{"target":"ledger"}\r\n'
    with pytest.raises(ValueError, match="cross-platform"):
        compare_cells(cells)


def test_evidence_json_duplicate_keys_are_rejected():
    with pytest.raises(ValueError, match="duplicate"):
        loads('{"source_sha":"a","source_sha":"b"}')


def test_junit_skip_cannot_be_reported_as_release_pass():
    raw = b"<testsuite>" + b"<testcase/>" * 128 + b"<testcase><skipped/></testcase></testsuite>"
    with pytest.raises(ValueError):
        junit_counts(raw)


def test_cli_stdout_bytes_match_lf_file_bytes(mini_repo, tmp_path):
    target = tmp_path / "out.json"
    env = {k: v for k, v in os.environ.items() if not k.startswith("PYTHON")}
    env.update(PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1")
    args = [sys.executable, "-B", "-m", "ledgerwash", "scan", str(mini_repo)]
    stdout = subprocess.run(args, capture_output=True, env=env, timeout=90)
    file_run = subprocess.run([*args, "--out", str(target)], capture_output=True, env=env, timeout=90)
    assert stdout.returncode == file_run.returncode == 1
    assert not stdout.stderr and not file_run.stderr and not file_run.stdout
    assert b"\r" not in stdout.stdout
    assert stdout.stdout == target.read_bytes()
