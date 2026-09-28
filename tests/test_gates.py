"""Frozen acceptance gates (A1–A8).

These gates are the tool's frozen acceptance, mirroring the SPEC. They may only
be strengthened, never weakened: a failing gate means the engine regressed, and
the fix must restore the gate, not delete it.
"""

from __future__ import annotations

import ast
import json
import re
import subprocess
from pathlib import Path

from ledgerwash.cli import main
from ledgerwash.engine import RULE_IDS, run_scan
from ledgerwash.qualify import cmd_qualify
from ledgerwash.qualify_corpus import EXPECTED, build_corpus

SRC = Path(__file__).resolve().parents[1] / "src" / "ledgerwash"
SPEC = Path(__file__).resolve().parents[1] / "SPEC.md"

# A1: no network. The tool is local-first by contract (SPEC §7).
FORBIDDEN_IMPORTS = {
    "socket",
    "ssl",
    "urllib",
    "http",
    "ftplib",
    "smtplib",
    "telnetlib",
    "requests",
    "httpx",
    "aiohttp",
}


def _imported_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.level == 0:
                roots.add(node.module.split(".")[0])
    return roots


def test_a1_no_network_imports():
    offenders = {}
    for path in sorted(SRC.rglob("*.py")):
        bad = _imported_roots(path) & FORBIDDEN_IMPORTS
        if bad:
            offenders[str(path)] = sorted(bad)
    assert not offenders, offenders


def run_scan_json(repo: Path) -> str:
    envelope = run_scan(repo)
    envelope["run"]["target"] = "<normalized>"
    return json.dumps(envelope, sort_keys=True, ensure_ascii=False)


def test_a2_determinism(tmp_path):
    envelopes = [run_scan_json(build_corpus(tmp_path / f"repo{i}")) for i in range(2)]
    assert envelopes[0] == envelopes[1]


def test_a3_rule_coverage(mini_envelope):
    fired = {f["rule"] for f in mini_envelope["findings"]}
    assert fired == set(RULE_IDS), fired ^ set(RULE_IDS)
    assert set(EXPECTED) == set(RULE_IDS)


def test_a4_clean_ledger_passes(clean_envelope):
    assert clean_envelope["verdict"] == "pass"
    assert clean_envelope["findings"] == []
    assert clean_envelope["residuals"] == []


def test_a5_exit_codes(mini_repo, tmp_path, capsys):
    assert main(["scan", str(mini_repo)]) == 1  # planted highs -> block
    capsys.readouterr()
    clean = build_corpus(tmp_path / "clean", planted=False)
    assert main(["scan", str(clean)]) == 0
    capsys.readouterr()
    assert main(["scan", str(tmp_path / "definitely-not-a-repo")]) == 2
    capsys.readouterr()


def test_a6_exit_code_matches_fail_on(mini_repo, capsys):
    assert main(["scan", str(mini_repo), "--fail-on", "critical"]) == 0
    capsys.readouterr()
    assert main(["scan", str(mini_repo), "--fail-on", "warn"]) == 1
    capsys.readouterr()


def test_a6_crash_never_exits_one(mini_repo, monkeypatch, capsys):
    """SPEC §6: any unexpected engine failure exits 2, never 1."""
    import ledgerwash.cli as cli_mod

    def boom(*_args, **_kwargs):
        raise ValueError("synthetic engine crash")

    monkeypatch.setattr(cli_mod, "run_scan", boom)
    assert main(["scan", str(mini_repo)]) == 2
    assert "synthetic engine crash" in capsys.readouterr().err


def test_a7_qualify_selfcheck(capsys):
    assert cmd_qualify() == 0
    assert "qualify ok" in capsys.readouterr().out


def test_a8_spec_rule_sync():
    spec_rows = set(re.findall(r"^\| `([A-Z_]+)` \| (?:info|warn|high|critical) \|",
                               SPEC.read_text(encoding="utf-8"), re.M))
    assert spec_rows == set(RULE_IDS), spec_rows ^ set(RULE_IDS)


def test_a9_empty_ledger_is_not_clean(tmp_path, capsys):
    """A repo with no ledger must not read as a clean ledger (SPEC §3)."""
    repo = tmp_path / "bare"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, capture_output=True, check=True)
    (repo / "README.md").write_text("not a ledger\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=repo, capture_output=True, check=True)
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t.invalid", "commit", "-m", "init"],
        cwd=repo, capture_output=True, check=True,
    )
    assert main(["scan", str(repo)]) == 0
    envelope = json.loads(capsys.readouterr().out)
    assert envelope["findings"] == []
    reasons = {r["reason"] for r in envelope["residuals"]}
    assert any("no task records" in r for r in reasons)
    assert any("no operation receipts" in r for r in reasons)
