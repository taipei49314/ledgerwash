"""Read private EC Git epochs; write all raw evidence only to the private job out."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess

from tests.redteam.harness import git
from tests.redteam.replay import ROOT, baseline_source, scan


def finding_keys(record):
    return sorted((item["rule"], item["path"], item.get("locator", "")) for item in record.get("findings", []))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--ec-source", type=Path, required=True)
    parser.add_argument("--historical-sha", required=True)
    parser.add_argument("--current-sha", required=True)
    parser.add_argument("--candidate-sha", required=True)
    args = parser.parse_args()
    out, work, source = args.out.resolve(), args.work.resolve(), args.ec_source.resolve()
    out.mkdir(parents=True, exist_ok=False)
    work.mkdir(parents=True, exist_ok=False)
    if git(source, "rev-parse", "--is-shallow-repository").strip() != b"false":
        raise ValueError("EC corpus source must have full history")
    for epoch in (args.historical_sha, args.current_sha):
        if git(source, "rev-parse", "--verify", epoch + "^{commit}").decode().strip() != epoch:
            raise ValueError("EC corpus commit identity mismatch")
    repo = work / "ec-corpus"
    # Never check out or execute private subject code; no token/config is copied.
    git(work, "clone", "--no-hardlinks", "--no-checkout", "--", str(source), str(repo))
    baseline, baseline_sha = baseline_source(work)
    records, problems = [], []
    for name, epoch in (("historical", args.historical_sha), ("current", args.current_sha)):
        item = {"name": name, "epoch": epoch, "judges": {}}
        for judge, src, pin, strict in (
            ("baseline", baseline, baseline_sha, False),
            ("candidate", ROOT / "src", args.candidate_sha, False),
            ("candidate-strict", ROOT / "src", args.candidate_sha, True),
        ):
            first = scan(repo, epoch, src, pin, out, f"{name}-{judge}-seed1", strict=strict, timeout=600)
            second = scan(repo, epoch, src, pin, out, f"{name}-{judge}-seed17", seed="17", strict=strict, timeout=600)
            first["raw_replay_equal"] = (first["stdout_sha256"] == second["stdout_sha256"]
                                          and first["exit_code"] == second["exit_code"])
            if first.get("error") or second.get("error") or not first["raw_replay_equal"]:
                problems.append(f"{name}/{judge}: engine error or replay mismatch")
            item["judges"][judge] = first
        before, after = item["judges"]["baseline"], item["judges"]["candidate"]
        old_keys, new_keys = set(finding_keys(before)), set(finding_keys(after))
        item["finding_changes"] = {"added": sorted(new_keys - old_keys), "removed": sorted(old_keys - new_keys)}
        # Coverage additions must not silently change existing finding identities.
        if old_keys != new_keys:
            problems.append(f"{name}: existing finding identity drift requires explicit triage")
        if after.get("run", {}).get("spec_version") != 4:
            problems.append(f"{name}: coverage phase requires the separately activated spec 4")
        records.append(item)
    result = {"schema_version": 1, "records": records, "passed": not problems, "problems": problems,
              "meaning": "pinned raw replay and contract compatibility; real ledgers need not pass strict"}
    (out / "results.json").write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                                      encoding="utf-8", newline="\n")
    print(json.dumps({"epochs": len(records), "passed": result["passed"], "problems": problems}))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
