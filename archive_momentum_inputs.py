"""Create a private, reproducible input snapshot; the workflow encrypts it.

Never upload the plaintext snapshot to a public repository or public artifact.
This module performs no data requests and cannot change strategy parameters.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from run_momentum_core import SOURCE_FILES, source_fingerprint


def create_snapshot(cache_dir, decision_path, destination):
    cache = Path(cache_dir).resolve()
    files = sorted(p for p in cache.rglob("*") if p.is_file())
    if not files:
        raise ValueError("No market input files to preserve")
    if any(p.is_symlink() for p in files):
        raise ValueError("Input snapshot must not follow symbolic links")
    decision = json.loads(Path(decision_path).read_text())
    manifest = {
        "snapshot_version": 1, "created_at": datetime.now(timezone.utc).isoformat(),
        "model": decision["model"], "start": decision["start"], "end": decision["end"],
        "decision_status": decision["status"], "source_fingerprint": source_fingerprint(),
        "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "files": {},
    }
    subprocess.run(["git", "diff", "--quiet", "HEAD", "--", *SOURCE_FILES], check=True)
    for path in files:
        with path.open("rb") as stream:
            manifest["files"][str(path.relative_to(cache))] = hashlib.file_digest(stream, "sha256").hexdigest()
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        (root / "snapshot.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        with (root / "source.tar.gz").open("wb") as stream:
            subprocess.run(["git", "archive", "--format=tar.gz", "HEAD"], stdout=stream, check=True)
        with tarfile.open(destination, "w:gz", compresslevel=1) as archive:
            archive.add(root / "snapshot.json", arcname="snapshot.json")
            archive.add(root / "source.tar.gz", arcname="source.tar.gz")
            archive.add(decision_path, arcname="decision.json")
            for path in files:
                archive.add(path, arcname="cache/" + str(path.relative_to(cache)))
    print(json.dumps({"snapshot_files": len(files), "bytes": destination.stat().st_size,
                      "source_fingerprint": manifest["source_fingerprint"]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-dir", default=".momentum_core_cache")
    parser.add_argument("--decision", default="core_results/Momentum_core_decision.json")
    parser.add_argument("--output", required=True)
    options = parser.parse_args()
    create_snapshot(options.cache_dir, options.decision, options.output)
