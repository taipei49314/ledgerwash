"""`ledgerwash qualify`: red-by-design self-check over the synthetic fixture."""

from __future__ import annotations

import sys
import tempfile
from collections import Counter
from pathlib import Path

from ledgerwash import SPEC_VERSION, __version__
from ledgerwash.engine import RULE_IDS, run_scan


def cmd_qualify() -> int:
    from ledgerwash.qualify_corpus import (
        EXPECTED_ALL,
        build_corpus,
        build_negspace_corpus,
    )

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    with tempfile.TemporaryDirectory() as tmp:
        repo = build_corpus(Path(tmp) / "mini-ledger")
        envelope = run_scan(repo)
        ns_repo = build_negspace_corpus(Path(tmp) / "negspace-ledger")
        ns_envelope = run_scan(ns_repo)

    actual = Counter(f["rule"] for f in envelope["findings"])
    actual.update(f["rule"] for f in ns_envelope["findings"])
    print(f"ledgerwash qualify @ {__version__} (spec {SPEC_VERSION})")
    for label, item in (("main", envelope), ("negspace", ns_envelope)):
        print(
            f"  {label}: epoch {item['run']['epoch'][:12]}  verdict {item['verdict']}  "
            f"findings {len(item['findings'])}  residuals {len(item['residuals'])}"
        )
    failures = 0
    for rule in RULE_IDS:
        want = EXPECTED_ALL[rule]
        got = actual[rule]
        ok = want == got
        failures += 0 if ok else 1
        print(f"  {'ok  ' if ok else 'FAIL'} {rule:<24} expected {want} actual {got}")
    for rule in sorted(set(actual) - set(EXPECTED_ALL)):
        failures += 1
        print(f"  FAIL {rule:<24} unexpected rule fired ({actual[rule]})")
    if failures:
        print(f"qualify FAILED ({failures} mismatch(es))")
        return 1
    print("qualify ok: every rule fires exactly as planted; nothing else fires")
    return 0
