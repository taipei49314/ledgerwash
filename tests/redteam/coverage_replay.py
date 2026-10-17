"""Remote paired-control acceptance with complete raw process evidence."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tests.redteam.coverage_cases import controls
from tests.redteam.harness import build_repo
from tests.redteam.replay import ROOT, scan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--candidate-sha", required=True)
    args = parser.parse_args()
    out, work = args.out.resolve(), args.work.resolve()
    out.mkdir(parents=True, exist_ok=False)
    work.mkdir(parents=True, exist_ok=False)
    records, problems = [], []
    for case in controls():
        repo = work / case["id"]
        epoch = build_repo(repo, case["plan"])
        item = {key: value for key, value in case.items() if key != "plan"}
        item.update(fixture_sha=epoch, modes={})
        for mode, strict in (("default", False), ("strict", True)):
            first = scan(repo, epoch, ROOT / "src", args.candidate_sha, out, f"{case['id']}-{mode}-seed1", strict=strict)
            second = scan(repo, epoch, ROOT / "src", args.candidate_sha, out, f"{case['id']}-{mode}-seed17", seed="17", strict=strict)
            first["raw_replay_equal"] = first["stdout_sha256"] == second["stdout_sha256"] and first["exit_code"] == second["exit_code"]
            item["modes"][mode] = first
            if first.get("error") or second.get("error") or not first["raw_replay_equal"]:
                problems.append(f"{case['id']}/{mode}: engine error or raw replay mismatch")
        default, strict = item["modes"]["default"], item["modes"]["strict"]
        if strict["exit_code"] != case["expected_strict"] or not strict.get("coverage"):
            problems.append(f"{case['id']}: strict control failed")
        report = strict.get("coverage") or {}
        counts = {status: sum(item["status"] == status for item in report.get("checks", []))
                  for status in ("verified", "unverified", "mismatch")}
        if (report.get("complete") != (case["expected_strict"] == 0) or report.get("counts") != counts
                or report.get("complete") != (counts["unverified"] == counts["mismatch"] == 0)):
            problems.append(f"{case['id']}: inconsistent completeness report")
        if default.get("findings") != strict.get("findings") or default.get("coverage") != strict.get("coverage"):
            problems.append(f"{case['id']}: gate changed findings or coverage")
        if case["expected_strict"] == 0 and (default["exit_code"] != 0 or not strict["coverage"]["complete"]):
            problems.append(f"{case['id']}: legitimate complete lifecycle failed")
        check = case.get("expected_check")
        if check and not any(c["check"] == check and c["status"] != "verified" for c in (strict.get("coverage") or {}).get("checks", [])):
            problems.append(f"{case['id']}: expected coverage gap {check} absent")
        rule = case.get("expected_rule")
        if rule and not any(f["rule"] == rule for f in default.get("findings", [])):
            problems.append(f"{case['id']}: expected default finding {rule} absent")
        records.append(item)
    result = {"schema_version": 1, "candidate_sha": args.candidate_sha,
              "control_count": len(records), "records": records, "passed": not problems, "problems": problems}
    (out / "results.json").write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                                      encoding="utf-8", newline="\n")
    print(json.dumps({key: result[key] for key in ("control_count", "passed", "problems")}))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
