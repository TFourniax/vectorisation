"""Fail CI when documented benchmark evidence no longer matches its source blobs.

The evidence manifest records the Git blob SHA-1 of every source file whose
behavior materially contributed to a promoted result. Git's blob identity is a
content hash over ``b'blob <len>\\0' + bytes``. Recomputing it locally lets CI
catch a subtle but common research failure mode: code changes while old numbers
remain in the README/status document as if they described the new implementation.

Artifact digests/run IDs are recorded for provenance but cannot be verified
without GitHub network access; source freshness is fully checkable offline.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs" / "evidence-manifest.json"


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    prefix = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(prefix + data).hexdigest()


def main() -> int:
    if not MANIFEST.exists():
        print(f"evidence manifest missing: {MANIFEST.relative_to(ROOT)}", file=sys.stderr)
        return 2
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if int(payload.get("schema_version", 0)) != 1:
        print("unsupported evidence manifest schema", file=sys.stderr)
        return 2
    entries = payload.get("evidence", {})
    if not isinstance(entries, dict) or not entries:
        print("evidence manifest contains no evidence entries", file=sys.stderr)
        return 2

    stale: list[str] = []
    malformed: list[str] = []
    checked = 0
    for evidence_id, entry in sorted(entries.items()):
        if entry.get("status") != "promoted":
            continue
        run_id = entry.get("workflow_run_id")
        artifact_digest = str(entry.get("artifact_sha256", ""))
        if not isinstance(run_id, int) or run_id <= 0:
            malformed.append(f"{evidence_id}: invalid workflow_run_id")
        if not artifact_digest.startswith("sha256:") or len(artifact_digest) != 71:
            malformed.append(f"{evidence_id}: invalid artifact_sha256")
        source_blobs = entry.get("source_blobs", {})
        if not isinstance(source_blobs, dict) or not source_blobs:
            malformed.append(f"{evidence_id}: no source_blobs")
            continue
        for relative, expected in sorted(source_blobs.items()):
            path = ROOT / relative
            if not path.is_file():
                stale.append(f"{evidence_id}: missing source {relative}")
                continue
            actual = git_blob_sha1(path)
            checked += 1
            if actual != expected:
                stale.append(
                    f"{evidence_id}: {relative} changed (manifest {expected}, current {actual})"
                )

    if malformed:
        print("Malformed evidence manifest:", file=sys.stderr)
        for line in malformed:
            print(f"  - {line}", file=sys.stderr)
    if stale:
        print("Stale promoted evidence:", file=sys.stderr)
        for line in stale:
            print(f"  - {line}", file=sys.stderr)
        print(
            "Regenerate the affected benchmark on the current source, then update docs/evidence-manifest.json.",
            file=sys.stderr,
        )
    if malformed or stale:
        return 1
    print(f"Evidence freshness OK: {checked} promoted source blobs match the manifest.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
