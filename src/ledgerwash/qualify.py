"""`ledgerwash qualify`: red-by-design self-check over the synthetic fixture."""

from __future__ import annotations

import sys
import tempfile
from collections import Counter
from pathlib import Path

from ledgerwash import SPEC_VERSION, __version__
from ledgerwash.engine import RULE_IDS, run_scan


def cmd_qualify() -> int:
    from ledgerwash.qualify_corpus import EXPECTED, build_corpus

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    with tempfile.TemporaryDirectory() as tmp:
        repo = build_corpus(Path(tmp) / "mini-ledger")
        envelope = run_scan(repo)

    actual = Counter(f["rule"] for f in envelope["findings"])
    print(f"ledgerwash qualify @ {__version__} (spec {SPEC_VERSION})")
    print(
        f"epoch {envelope['run']['epoch'][:12]}  verdict {envelope['verdict']}  "
        f"findings {len(envelope['findings'])}  residuals {len(envelope['residuals'])}"
    )
    failures = 0
    for rule in RULE_IDS:
        want = EXPECTED[rule]
        got = actual[rule]
        ok = want == got
        failures += 0 if ok else 1
        print(f"  {'ok  ' if ok else 'FAIL'} {rule:<24} expected {want} actual {got}")
    for rule in sorted(set(actual) - set(EXPECTED)):
        failures += 1
        print(f"  FAIL {rule:<24} unexpected rule fired ({actual[rule]})")
    if failures:
        print(f"qualify FAILED ({failures} mismatch(es))")
        return 1
    print("qualify ok: every rule fires exactly as planted; nothing else fires")
    return 0
