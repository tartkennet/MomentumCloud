"""Restore supplied audit archives locally, with fixed evidence hashes and no network."""
import argparse
import hashlib
import io
import json
import shutil
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CACHE_SHA256 = '638589917ba5a37c0c69bdd0e057b4fb873618981c286bde3d88488135313ee2'
CHUNK_SIZE = 32 * 1024 * 1024


def safe_destination(root, name):
    destination = (root / name).resolve()
    if not destination.is_relative_to(root.resolve()):
        raise ValueError('Archive member outside destination: ' + name)
    destination.parent.mkdir(parents=True, exist_ok=True)
    return destination


def extract_zip(archive, destination):
    for member in archive.infolist():
        target = safe_destination(destination, member.filename)
        if member.is_dir():
            target.mkdir(exist_ok=True)
        else:
            with archive.open(member) as source, target.open('wb') as output:
                shutil.copyfileobj(source, output)


class JoinedFrozenParts(io.RawIOBase):
    def __init__(self, paths):
        self.paths = iter(paths)
        self.archive = None
        self.source = None

    def readable(self):
        return True

    def readinto(self, buffer):
        while True:
            if self.source is None:
                path = next(self.paths, None)
                if path is None:
                    return 0
                self.archive = zipfile.ZipFile(path)
                if self.archive.namelist() != ['chunk.bin']:
                    raise ValueError('Unexpected frozen part: ' + str(path))
                self.source = self.archive.open('chunk.bin')
            data = self.source.read(len(buffer))
            if data:
                buffer[:len(data)] = data
                return len(data)
            self.source.close()
            self.archive.close()
            self.source = self.archive = None

    def close(self):
        if self.source is not None:
            self.source.close()
            self.archive.close()
        super().close()


def restore(source_dir, output):
    recovery = source_dir / 'MomentumCloud_recovery_checkpoint_20261012.zip'
    expected = json.loads((ROOT / 'audit_evidence/recovery_artifacts_20261012.json').read_text())
    expected = {record['name']: record['sha256'] for record in expected['artifacts']}
    checks = []
    with zipfile.ZipFile(recovery) as archive:
        for name in archive.namelist():
            if not name.startswith('artifacts/') or not name.endswith('.zip'):
                continue
            data = archive.read(name)
            stem = Path(name).stem
            key = {'classification': 'MomentumCloud_verified_gap_classification',
                   'raw-evidence': 'MomentumCloud_relaxed_selection_audit'}.get(stem, stem)
            actual = hashlib.sha256(data).hexdigest()
            if actual != expected[key]:
                raise ValueError('Recovered artifact hash mismatch: ' + name)
            directory = ('classification' if stem == 'classification' else
                         'raw_evidence' if stem == 'raw-evidence' else 'universe_evidence')
            with zipfile.ZipFile(io.BytesIO(data)) as inner:
                extract_zip(inner, ROOT / directory)
            checks.append({'artifact': key, 'sha256': actual, 'status': 'PASS'})
    if len(checks) != len(expected):
        raise ValueError('Incomplete recovery archive set')

    with zipfile.ZipFile(source_dir / 'MomentumCloud_prisunderlag_2026-10-08.zip') as archive:
        extract_zip(archive, ROOT / 'evidence/selection')

    frozen = ROOT / 'frozen_recovery'
    frozen.mkdir(exist_ok=True)
    for stale in frozen.glob('cache*.bin'):
        stale.unlink()
    digest = hashlib.sha256()
    cache_size = 0
    cache_parts = 0
    members = 0
    joined = JoinedFrozenParts([source_dir / f'frozen-part-{i}.zip' for i in range(3)])
    with io.BufferedReader(joined) as stream:
        with tarfile.open(fileobj=stream, mode='r|gz') as archive:
            for member in archive:
                if member.isdir():
                    safe_destination(frozen, member.name).mkdir(exist_ok=True)
                    continue
                if not member.isfile():
                    raise ValueError('Unsupported frozen member: ' + member.name)
                members += 1
                source = archive.extractfile(member)
                if member.name == 'frozen/.momentum_backtest_cache.json':
                    while True:
                        data = source.read(CHUNK_SIZE)
                        if not data:
                            break
                        digest.update(data)
                        cache_size += len(data)
                        (frozen / f'cache{cache_parts:03d}.bin').write_bytes(data)
                        cache_parts += 1
                else:
                    with safe_destination(frozen, member.name).open('wb') as target:
                        shutil.copyfileobj(source, target)
                source.close()
    if digest.hexdigest() != CACHE_SHA256 or cache_size != 507412232:
        raise ValueError('Frozen cache bytes do not match the verified source')
    shutil.copyfile(frozen / 'frozen/.momentum_point_in_time_universe.json',
                    ROOT / '.momentum_point_in_time_universe.json')
    payload = json.loads(b''.join(path.read_bytes() for path in sorted(frozen.glob('cache*.bin'))))
    if payload['version'] != 3 or payload['adjusted_through'] != '2026-10-06':
        raise ValueError('Unexpected frozen cache provenance')
    result = {'status': 'PASS_RESTORED_FIXED_INPUTS', 'artifacts': checks,
              'cache_sha256': digest.hexdigest(), 'cache_bytes': cache_size,
              'cache_parts': cache_parts, 'cache_sessions': len(payload['sessions']),
              'frozen_files': members, 'adjusted_through': payload['adjusted_through'],
              'limitation': 'Input recovery only; not a fresh model or execution approval.'}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source_dir', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    arguments = parser.parse_args()
    restore(arguments.source_dir, arguments.output)
