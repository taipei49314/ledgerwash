"""CLI: scan / qualify subcommands (SPEC §6 exit codes)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ledgerwash import SPEC_VERSION, __version__
from ledgerwash.engine import ADAPTERS, run_scan
from ledgerwash.epoch import EpochError
from ledgerwash.models import SEVERITY_ORDER


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ledgerwash",
        description=(
            "Flags mechanically-checkable patterns of weakened evidence in agent "
            "work ledgers at a pinned revision. Read-only; exit 0 is not proof the "
            "ledger is honest."
        ),
    )
    parser.add_argument(
        "--version", action="version", version=f"ledgerwash {__version__} (spec {SPEC_VERSION})"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_scan = sub.add_parser("scan", help="scan a ledger repo at a pinned revision")
    p_scan.add_argument("repo", help="path to the target repo")
    p_scan.add_argument(
        "--at", dest="at", default=None, help="pin the epoch to this ref (default HEAD)"
    )
    p_scan.add_argument("--out", default=None, help="write the envelope to this file")
    p_scan.add_argument("--fail-on", choices=SEVERITY_ORDER, default="high")
    p_scan.add_argument("--adapter", choices=sorted(ADAPTERS), default="ec-ledger")
    p_scan.add_argument("--require-complete", action="store_true",
                        help="also block when supported mechanical verification inputs are incomplete")

    sub.add_parser(
        "qualify",
        help="scan the built-in red-by-design corpus and assert the expected finding matrix",
    )
    return parser


def main(argv=None) -> int:
    args = _build_parser().parse_args(argv)

    if args.command == "qualify":
        from ledgerwash.qualify import cmd_qualify

        return cmd_qualify()

    try:
        envelope = run_scan(Path(args.repo), args.at, args.adapter, args.fail_on, args.require_complete)
    except EpochError as exc:
        print(f"ledgerwash: engine error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # a crash must not exit 1 (SPEC §6)
        print(f"ledgerwash: engine error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    text = json.dumps(envelope, sort_keys=True, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8", newline="\n")
    else:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        sys.stdout.write(text)
    return 1 if envelope["verdict"] == "block" else 0
