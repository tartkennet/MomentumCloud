"""Authenticated, encrypted Actions cache for licensed raw research inputs.

The existing API credential is read only from the environment and is never
serialized. This cache is disposable; the separately encrypted research export
remains the durable, offline research record.
"""
import argparse
import hashlib
import hmac
import os
from pathlib import Path, PurePosixPath
import subprocess
import tarfile
import tempfile

MAGIC = b'MOMENTUM-SEALED-CACHE-1\n'


def transfer(mode, cache, sealed):
    key = os.environ.get('POLYGON_API_KEY')
    if not key:
        raise ValueError('POLYGON_API_KEY is required to protect the input cache')
    auth_key = hashlib.sha256(b'Momentum cache authentication\0' + key.encode()).digest()
    cache, sealed = Path(cache), Path(sealed)
    with tempfile.TemporaryDirectory() as directory:
        plain = Path(directory) / 'inputs.tar'
        cipher = Path(directory) / 'inputs.enc'
        command = ['openssl', 'enc', '-aes-256-cbc', '-pbkdf2', '-iter', '200000',
                   '-pass', 'env:POLYGON_API_KEY']
        if mode == 'seal':
            files = sorted(p for p in cache.rglob('*') if p.is_file())
            if not files or any(p.is_symlink() for p in files):
                raise ValueError('Empty or linked raw input cache')
            with tarfile.open(plain, 'w') as archive:
                for path in files:
                    archive.add(path, arcname=str(path.relative_to(cache)), recursive=False)
            subprocess.run(command + ['-salt', '-in', str(plain), '-out', str(cipher)], check=True)
            payload = cipher.read_bytes()
            tag = hmac.digest(auth_key, MAGIC + payload, 'sha256')
            temporary = sealed.with_suffix('.tmp')
            temporary.write_bytes(MAGIC + tag + payload)
            temporary.replace(sealed)
        else:
            blob = sealed.read_bytes()
            if not blob.startswith(MAGIC) or len(blob) <= len(MAGIC) + 32:
                raise ValueError('Unrecognized encrypted cache')
            tag, payload = blob[len(MAGIC):len(MAGIC) + 32], blob[len(MAGIC) + 32:]
            if not hmac.compare_digest(tag, hmac.digest(auth_key, MAGIC + payload, 'sha256')):
                raise ValueError('Encrypted cache authentication failed')
            cipher.write_bytes(payload)
            subprocess.run(command + ['-d', '-in', str(cipher), '-out', str(plain)], check=True)
            with tarfile.open(plain) as archive:
                members = archive.getmembers()
                for member in members:
                    path = PurePosixPath(member.name)
                    if path.is_absolute() or '..' in path.parts or not member.isfile():
                        raise ValueError('Unsafe encrypted cache entry')
                for member in members:
                    path = cache / member.name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(archive.extractfile(member).read())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('seal', 'unseal'))
    parser.add_argument('--cache-dir', default='.momentum_core_cache')
    parser.add_argument('--sealed', default='.momentum_core_cache.sealed')
    args = parser.parse_args()
    transfer(args.mode, args.cache_dir, args.sealed)
