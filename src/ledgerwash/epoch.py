"""Epoch: read-only git snapshot reader pinned to a ref.

The only module that runs git (ARCHITECTURE). Every corpus read — task records,
receipts, referenced paths, fingerprint anchors — goes through git at the pinned
ref, so the target's checkout state is irrelevant and the pin is part of the
output, not a manual pre-step.
"""

from __future__ import annotations

import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

_HEX40 = re.compile(r"^[0-9a-fA-F]{40}$")


class EpochError(Exception):
    """Git unreadable or ref unresolvable; the engine maps this to exit 2."""


class Epoch:
    def __init__(self, repo: Path, ref: str | None = None):
        self.repo = Path(repo)
        if not self.repo.is_dir():
            raise EpochError(f"target is not a directory: {self.repo}")
        self.ref = ref or "HEAD"
        self.sha = self._rev_parse()
        self._tree_files: set[str] | None = None
        self._tree_dirs: set[str] | None = None

    # -- core git plumbing ---------------------------------------------------

    def _git(self, *args: str, input_bytes: bytes | None = None) -> bytes:
        try:
            proc = subprocess.run(
                ["git", *args], cwd=self.repo, input=input_bytes, capture_output=True
            )
        except OSError as exc:
            raise EpochError(f"git could not run against {self.repo}: {exc}") from exc
        if proc.returncode != 0:
            detail = proc.stderr.decode("utf-8", "replace").strip()
            raise EpochError(f"git {' '.join(args[:3])} failed: {detail}")
        return proc.stdout

    def _rev_parse(self) -> str:
        out = self._git("rev-parse", "--verify", f"{self.ref}^{{commit}}")
        sha = out.decode("ascii", "replace").strip()
        if not _HEX40.fullmatch(sha):
            raise EpochError(f"ref {self.ref!r} did not resolve to a commit")
        return sha

    # -- snapshot reads ------------------------------------------------------

    def read_bytes(self, rel: str) -> bytes | None:
        proc = subprocess.run(
            ["git", "cat-file", "blob", f"{self.sha}:{rel}"],
            cwd=self.repo,
            capture_output=True,
        )
        return proc.stdout if proc.returncode == 0 else None

    def read_text(self, rel: str) -> str | None:
        raw = self.read_bytes(rel)
        return None if raw is None else raw.decode("utf-8", "replace")

    def list_dir(self, rel: str) -> list[str]:
        """Direct children of a directory in the epoch tree; [] if the dir is absent."""
        proc = subprocess.run(
            ["git", "ls-tree", "--name-only", f"{self.sha}:{rel}"],
            cwd=self.repo,
            capture_output=True,
        )
        if proc.returncode != 0:
            return []
        return [line for line in proc.stdout.decode("utf-8", "replace").splitlines() if line]

    def tree_files(self) -> set[str]:
        """All file paths in the epoch tree (cached)."""
        if self._tree_files is None:
            out = self._git("ls-tree", "-r", "--name-only", self.sha)
            self._tree_files = {
                line for line in out.decode("utf-8", "replace").splitlines() if line
            }
        return self._tree_files

    def tree_dirs(self) -> set[str]:
        """All directory paths in the epoch tree (cached)."""
        if self._tree_dirs is None:
            out = self._git("ls-tree", "-r", "-d", "--name-only", self.sha)
            self._tree_dirs = {
                line for line in out.decode("utf-8", "replace").splitlines() if line
            }
        return self._tree_dirs

    def path_exists(self, rel: str) -> bool:
        """Existence in the epoch tree, file or directory (worktree `exists()` parity).

        Trailing slashes are stripped: git tree names carry none, but references
        like `evidence/hosts/` name a directory.
        """
        probe = rel.rstrip("/")
        if not probe:
            return True
        return probe in self.tree_files() or probe in self.tree_dirs()

    # -- object/pin checks ---------------------------------------------------

    def has_objects(self, shas) -> set[str]:
        candidates = sorted({s for s in shas if isinstance(s, str) and _HEX40.fullmatch(s)})
        if not candidates:
            return set()
        stdin = ("\n".join(candidates) + "\n").encode("ascii")
        out = self._git("cat-file", "--batch-check", input_bytes=stdin)
        have = set()
        for line in out.decode("ascii", "replace").splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[1].lower() in ("commit", "tag", "blob", "tree"):
                have.add(parts[0])
        return have

    def commits(self, shas) -> set[str]:
        """Shas that resolve to commit objects.

        Fingerprint anchors must be commits: hashing `blob-sha:path` fails even
        when the object exists, which would masquerade as FP_SOURCE_MISSING.
        """
        candidates = sorted({s for s in shas if isinstance(s, str) and _HEX40.fullmatch(s)})
        if not candidates:
            return set()
        stdin = ("\n".join(candidates) + "\n").encode("ascii")
        out = self._git("cat-file", "--batch-check", input_bytes=stdin)
        have = set()
        for line in out.decode("ascii", "replace").splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[1].lower() == "commit":
                have.add(parts[0])
        return have

    def object_types(self, shas) -> dict[str, str]:
        """Object type per existing sha, batched; absent shas are left out.

        PIN_LOCAL_MISSING stays "not an object of the target repo" (any type
        counts as present); the type map is what lets PIN_NOT_COMMIT separate
        an existing non-commit pin from a commit one.
        """
        candidates = sorted({s for s in shas if isinstance(s, str) and _HEX40.fullmatch(s)})
        if not candidates:
            return {}
        stdin = ("\n".join(candidates) + "\n").encode("ascii")
        out = self._git("cat-file", "--batch-check", input_bytes=stdin)
        types: dict[str, str] = {}
        for line in out.decode("ascii", "replace").splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[1].lower() in ("commit", "tag", "blob", "tree"):
                types[parts[0]] = parts[1].lower()
        return types

    def commit_dates(self, shas) -> dict[str, str]:
        """Committer date per commit sha as UTC ISO-8601, one batched read.

        Used only as file-history corroboration for DONE_TIME_BACKDATED — a
        claim about when a path first appears, never a trusted execution
        clock (SPEC §3.1). Non-commits and missing shas are left out.
        """
        candidates = sorted({s for s in shas if isinstance(s, str) and _HEX40.fullmatch(s)})
        if not candidates:
            return {}
        stdin = ("\n".join(candidates) + "\n").encode("ascii")
        out = self._git("cat-file", "--batch", input_bytes=stdin)
        dates: dict[str, str] = {}
        offset = 0
        while offset < len(out):
            newline = out.find(b"\n", offset)
            if newline < 0:
                break
            header = out[offset:newline].decode("ascii", "replace").split()
            if len(header) == 2 and header[1] == "missing":
                offset = newline + 1
                continue
            if len(header) >= 3:
                try:
                    size = int(header[2])
                except ValueError:
                    offset = newline + 1
                    continue
                body = out[newline + 1 : newline + 1 + size]
                offset = newline + 1 + size + 1
                if header[1] == "commit":
                    for line in body.decode("utf-8", "replace").splitlines():
                        if line.startswith("committer "):
                            fields = line.rsplit(" ", 2)
                            if len(fields) == 3 and fields[1].isdigit():
                                moment = datetime.fromtimestamp(
                                    int(fields[1]), tz=timezone.utc
                                )
                                dates[header[0]] = moment.strftime("%Y-%m-%dT%H:%M:%S+00:00")
                            break
                continue
            offset = newline + 1
        return dates

    def blob_at(self, commit: str, rel: str) -> bytes | None:
        proc = subprocess.run(
            ["git", "cat-file", "blob", f"{commit}:{rel}"],
            cwd=self.repo,
            capture_output=True,
        )
        return proc.stdout if proc.returncode == 0 else None

    def parent(self, commit: str) -> str | None:
        proc = subprocess.run(
            ["git", "rev-parse", "--verify", f"{commit}^"],
            cwd=self.repo,
            capture_output=True,
        )
        if proc.returncode != 0:
            return None
        sha = proc.stdout.decode("ascii", "replace").strip()
        return sha if _HEX40.fullmatch(sha) else None

    # -- birth map -----------------------------------------------------------

    def birth_map(self, rel_dir: str) -> dict[str, str]:
        """Map each file under rel_dir to its latest addition at the pinned epoch.

        Every filename under a commit header is mapped; round-0's scan_birth
        mapped only the first file of each commit and silently dropped the rest.
        Deletion/recreation starts a new incarnation; renames add the new path.
        """
        out = self._git(
            "log", "--no-renames", "--diff-filter=A", "--format=%x01%H",
            "--name-only", self.sha, "--", rel_dir
        )
        births: dict[str, str] = {}
        current: str | None = None
        for line in out.decode("utf-8", "replace").splitlines():
            if line.startswith("\x01"):
                current = line[1:].strip() or None
            elif line.strip() and current:
                births.setdefault(line.strip(), current)
        return births
