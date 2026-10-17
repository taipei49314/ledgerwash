"""Bounded, token-free release evidence checks. Never execute archive contents."""
from __future__ import annotations

import hashlib
import io
import json
import re
import stat
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from datetime import datetime

REPOSITORY = "taipei49314/ledgerwash"
OS_NAMES = ("ubuntu-latest", "windows-latest", "macos-latest")
PYTHONS = ("3.11", "3.12", "3.13")
SCENARIOS = ("main", "era", "clean", "migration-lf", "migration-forged")
MODES = ("default", "strict")
SEEDS = ("1", "17")
TRANSPORTS = ("stdout", "file")
RAW_NAMES = tuple(f"{case}.{mode}.s{seed}.{transport}.json"
                  for case in SCENARIOS for mode in MODES
                  for seed in SEEDS for transport in TRANSPORTS)
MAIN_COUNTS = {
    "CHAIN_BREAK": 1, "CONTRACT_UNDOCUMENTED": 2, "DANGLING_REF": 1,
    "DONE_TIME_BACKDATED": 1, "DONE_TIME_UNESTABLISHED": 2,
    "FP_HASH_MISMATCH": 2, "FP_SOURCE_MISSING": 1, "NO_OPERATION_HISTORY": 1,
    "PIN_LOCAL_MISSING": 1, "PIN_NOT_COMMIT": 1, "PIN_UNROUTABLE": 1,
    "POST_HOC_DRIFT": 1, "RECEIPT_ORPHAN": 1, "RECORD_UNPARSEABLE": 1,
    "STATUS_STATE_MISMATCH": 1, "TIMELINE_INVERSION": 1,
    "TIMESTAMP_MALFORMED": 1, "TIMESTAMP_REDACTED": 1,
}
ERA_COUNTS = {"ERA_UNDETERMINABLE": 1, "DONE_TIME_UNESTABLISHED": 1,
              "RECEIPT_ORPHAN": 1}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def loads(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "duplicate JSON key")
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=unique,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def artifact_name(run, attempt, os_name, python):
    return f"lw-release-{run}-{attempt}-{os_name}-py{python}"


def junit_counts(raw):
    require(b"<!DOCTYPE" not in raw and b"<!ENTITY" not in raw, "XML entities refused")
    root = ET.fromstring(raw)
    cases = list(root.iter("testcase"))
    result = {"tests": len(cases), "failures": 0, "errors": 0, "skipped": 0}
    for case in cases:
        for kind, key in (("failure", "failures"), ("error", "errors"), ("skipped", "skipped")):
            result[key] += len(case.findall(kind))
    require(result["tests"] >= 128 and not any(result[k] for k in ("failures", "errors", "skipped")),
            "suite did not pass all cases")
    return result


def check_metadata(source, run_id, attempt, run, jobs, artifacts):
    require(run["id"] == int(run_id) and run["run_attempt"] == int(attempt), "run attempt mismatch")
    require(run["repository"]["id"] == 1392503057
            and run["repository"]["full_name"] == REPOSITORY
            and run["head_repository"]["id"] == 1392503057, "repository identity mismatch")
    require(run["workflow_id"] == 369035271 and run["path"] == ".github/workflows/ci.yml",
            "workflow identity mismatch")
    require(run["head_sha"] == source and run["event"] in ("push", "pull_request"), "run source/event mismatch")
    require(run["status"] == "completed" and run["conclusion"] == "success", "run not successful")
    expected_jobs = {f"test ({os_name}, {python})": (os_name, python)
                     for os_name in OS_NAMES for python in PYTHONS}
    require(jobs["total_count"] == 9 and len(jobs["jobs"]) == 9, "expected nine jobs")
    require({job["name"] for job in jobs["jobs"]} == set(expected_jobs), "job set mismatch")
    require(len({job["id"] for job in jobs["jobs"]}) == 9, "duplicate job identity")
    require(artifacts["total_count"] == len(artifacts["artifacts"]) <= 100, "artifact listing incomplete")
    require(len({item["id"] for item in artifacts["artifacts"]}) == len(artifacts["artifacts"]),
            "duplicate artifact identity")
    matched = {}
    for job in jobs["jobs"]:
        os_name, python = expected_jobs[job["name"]]
        require(job["run_id"] == int(run_id) and job["run_attempt"] == int(attempt)
                and job["head_sha"] == source and job["status"] == "completed"
                and job["conclusion"] == "success", "job source/attempt/result mismatch")
        require("self-hosted" not in job.get("labels", []), "unexpected self-hosted producer")
        name = artifact_name(run_id, attempt, os_name, python)
        found = [item for item in artifacts["artifacts"] if item["name"] == name]
        require(len(found) == 1, "missing or duplicate expected artifact")
        item = found[0]
        origin = item["workflow_run"]
        require(origin["id"] == int(run_id) and origin["head_sha"] == source
                and origin["repository_id"] == 1392503057
                and origin["head_repository_id"] == 1392503057, "artifact run/source mismatch")
        require(item["expired"] is False and re.fullmatch(r"sha256:[0-9a-f]{64}", item.get("digest") or ""),
                "artifact missing usable service digest")
        at = lambda value: datetime.fromisoformat(value.replace("Z", "+00:00"))
        require(at(job["started_at"]) <= at(item["created_at"]) <= at(job["completed_at"]),
                "artifact outside producer job interval")
        require(0 < item["size_in_bytes"] <= 4 * 1024 * 1024, "artifact size limit")
        matched[(os_name, python)] = item
    return matched


def read_zip(raw):
    require(len(raw) <= 4 * 1024 * 1024, "ZIP compressed size limit")
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        infos = archive.infolist()
        expected = {*RAW_NAMES, "receipt.json", "suite.xml"}
        names = [item.filename for item in infos]
        require(len(names) == len(set(names)) and set(names) == expected,
                "unexpected, missing or duplicate ZIP members")
        require(sum(item.file_size for item in infos) <= 16 * 1024 * 1024,
                "ZIP expanded size limit")
        result = {}
        for item in infos:
            mode = item.external_attr >> 16
            require(not item.is_dir() and not stat.S_ISLNK(mode)
                    and stat.S_IFMT(mode) in (0, stat.S_IFREG), "nonregular ZIP member")
            require(item.file_size <= 2 * 1024 * 1024, "ZIP member size limit")
            require(not (item.flag_bits & 1), "encrypted ZIP member")
            result[item.filename] = archive.read(item)
        return result


def check_envelope(raw, case, mode, epoch):
    require(raw.endswith(b"\n") and b"\r" not in raw, "output must use LF")
    envelope = loads(raw.decode("utf-8"))
    require(raw == (json.dumps(envelope, sort_keys=True, ensure_ascii=False,
                               indent=2) + "\n").encode("utf-8"), "noncanonical output")
    run = envelope["run"]
    require(run == {"adapter": "ec-ledger", "epoch": epoch,
                    "ledgerwash_version": "0.5.0", "ref": epoch,
                    "spec_version": 5, "target": "ledger",
                    "require_complete": mode == "strict"}, "envelope invocation identity")
    require(envelope["ledgerwash_findings_version"] == 2, "envelope version")
    counts = dict(Counter(item["rule"] for item in envelope["findings"]))
    expected = MAIN_COUNTS if case == "main" else ERA_COUNTS if case == "era" else {}
    require(counts == expected, "finding plants changed")
    finding_verdict = "block" if case in ("main", "era") else "pass"
    verdict = "block" if mode == "strict" else finding_verdict
    require(envelope["finding_verdict"] == finding_verdict
            and envelope["verdict"] == verdict, "unexpected verdict")
    require(envelope["coverage"]["complete"] is False, "unexpected complete coverage")
    return 1 if verdict == "block" else 0


def check_cell(members, source, run, attempt, os_name, python):
    receipt = loads(members["receipt.json"])
    require(receipt["schema_version"] == 1 and receipt["status"] == "pass", "producer failure")
    require(receipt["repository"] == REPOSITORY and receipt["source_sha"] == source,
            "producer source mismatch")
    require(str(receipt["run_id"]) == str(run) and str(receipt["run_attempt"]) == str(attempt),
            "producer attempt mismatch")
    require(receipt["cell"] == {"os": os_name, "python": python}, "producer cell mismatch")
    expected_platform = {"ubuntu-latest": "Linux", "windows-latest": "Windows",
                         "macos-latest": "Darwin"}[os_name]
    require(receipt["runtime"]["system"] == expected_platform
            and receipt["runtime"]["python"].startswith(python + "."), "runtime mismatch")
    require(receipt["source_clean"] is True, "dirty producer source")
    require(receipt["suite"] == junit_counts(members["suite.xml"]), "suite count mismatch")
    require(set(receipt["epochs"]) == set(SCENARIOS), "fixture family set")
    require(set(receipt["files"]) == {*RAW_NAMES, "suite.xml"}, "file digest set")
    for name, identity in receipt["files"].items():
        require(identity == {"sha256": sha(members[name]), "bytes": len(members[name])},
                "producer file digest mismatch")
    require(receipt["qualify"]["exit_code"] == 0
            and "qualify ok" in receipt["qualify"]["stdout"], "qualify failed")
    require(len(receipt["commands"]) == 40, "missing scan commands")
    require({item["output"] for item in receipt["commands"]} == set(RAW_NAMES),
            "duplicate or missing scan command")
    command_index = {item["output"]: item for item in receipt["commands"]}
    for case in SCENARIOS:
        epoch = receipt["epochs"][case]
        require(re.fullmatch(r"[0-9a-f]{40}", epoch), "invalid fixture epoch")
        for mode in MODES:
            expected_bytes = members[f"{case}.{mode}.s1.stdout.json"]
            for seed in SEEDS:
                for transport in TRANSPORTS:
                    name = f"{case}.{mode}.s{seed}.{transport}.json"
                    raw = members[name]
                    code = check_envelope(raw, case, mode, epoch)
                    command = command_index[name]
                    require(command["exit_code"] == code and not command["stderr"]
                            and command["seed"] == seed, "scan command result mismatch")
                    require(raw == expected_bytes, "seed or transport byte mismatch")
    return receipt


def compare_cells(cells):
    require(len(cells) == 9, "expected nine producer cells")
    reference = cells[0]
    for cell in cells[1:]:
        for name in RAW_NAMES:
            require(cell[name] == reference[name], f"cross-platform byte mismatch: {name}")
    return {name: {"sha256": sha(reference[name]), "bytes": len(reference[name])}
            for name in RAW_NAMES}
