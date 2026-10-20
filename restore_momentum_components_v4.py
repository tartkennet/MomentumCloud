"""Restore the exact component ledgers from the git-retained archive parts.

Usage: python restore_momentum_components_v4.py
The earlier frozen research input ZIP is separate and is not needed merely
to audit these saved order/cash books with verify_momentum_components_v4.py.
"""
import hashlib
import io
import json
from pathlib import Path
import tarfile


def restore(root):
    root=Path(root).resolve()
    manifest=json.loads((root/"audit_evidence/components_v4_archive_20261020/manifest.json").read_text())
    chunks=[]
    for name,info in manifest["parts"].items():
        data=(root/name).read_bytes()
        if len(data)!=info["bytes"] or hashlib.sha256(data).hexdigest()!=info["sha256"]:
            raise ValueError("Archive part hash mismatch: "+name)
        chunks.append(data)
    data=b"".join(chunks)
    if hashlib.sha256(data).hexdigest()!=manifest["archive_sha256"]:
        raise ValueError("Assembled archive mismatch")
    with tarfile.open(fileobj=io.BytesIO(data),mode="r:gz") as archive:
        names=[m.name for m in archive.getmembers()]
        if len(names)!=len(set(names)) or set(names)!=set(manifest["files"]):
            raise ValueError("Archive member coverage mismatch")
        for member in archive.getmembers():
            target=(root/member.name).resolve()
            if not member.isfile() or not target.is_relative_to(root):
                raise ValueError("Unsafe archive member")
            content=archive.extractfile(member).read()
            expected=manifest["files"][member.name]
            if len(content)!=expected["bytes"] or hashlib.sha256(content).hexdigest()!=expected["sha256"]:
                raise ValueError("Evidence file mismatch: "+member.name)
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(content)
    return {"status":"PASS_RESTORED_COMPONENT_EVIDENCE","files":len(names)}


if __name__=="__main__":
    print(json.dumps(restore(Path(__file__).resolve().parent)))
