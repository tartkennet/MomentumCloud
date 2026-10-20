"""Restore hash-checked v2 research inputs from the retained single ZIP.

Usage: python restore_risk_managed_inputs.py /path/to/checkpoint.zip
Code and supplementary corporate-action observations remain versioned in git.
"""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile


def restore(archive_path, destination):
    destination = destination.resolve()
    with zipfile.ZipFile(archive_path) as archive:
        manifest = json.loads(archive.read("input_manifest.json"))
        names = set(archive.namelist())
        expected = set(manifest["files"]) | {"input_manifest.json"}
        if names != expected or len(names) != len(archive.namelist()):
            raise ValueError("Incomplete, additional or duplicate archive members")
        for name, details in manifest["files"].items():
            target = (destination / name).resolve()
            if not target.is_relative_to(destination):
                raise ValueError("Archive member outside destination")
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_name(target.name + ".restore-partial")
            digest, size = hashlib.sha256(), 0
            with archive.open(name) as source, temporary.open("wb") as output:
                while chunk := source.read(1024 * 1024):
                    digest.update(chunk)
                    size += len(chunk)
                    output.write(chunk)
            if size != details["size"] or digest.hexdigest() != details["sha256"]:
                temporary.unlink()
                raise ValueError("Input hash mismatch: " + name)
            temporary.replace(target)
    cache_parts = sorted((destination / "frozen_recovery").glob("cache*.bin"))
    if len(cache_parts) != 16:
        raise ValueError("Unexpected cache chunk count")
    digest = hashlib.sha256()
    for path in cache_parts:
        with path.open("rb") as source:
            while chunk := source.read(1024 * 1024):
                digest.update(chunk)
    if digest.hexdigest() != manifest["cache_sha256"]:
        raise ValueError("Assembled cache hash mismatch")
    stale_index = destination / "frozen_recovery/request_index.json"
    stale_index.unlink(missing_ok=True)
    return {"status": "PASS_RESTORED_RISK_RESEARCH_INPUTS", "files": len(manifest["files"]),
            "cache_sha256": digest.hexdigest(), "adjusted_through": manifest["adjusted_through"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    parser.add_argument("--destination", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    print(json.dumps(restore(args.archive, args.destination)))
