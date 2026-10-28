import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from cache_momentum_inputs import transfer


class ProtectedInputCacheTests(unittest.TestCase):
    def test_roundtrip_and_wrong_key_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source' / 'raw-v1'
            source.mkdir(parents=True)
            (source / 'day.json.gz').write_bytes(b'licensed input')
            sealed = root / 'cache.sealed'
            with patch.dict(os.environ, POLYGON_API_KEY='synthetic-test-credential'):
                transfer('seal', root / 'source', sealed)
                transfer('unseal', root / 'restored', sealed)
            self.assertEqual((root / 'restored/raw-v1/day.json.gz').read_bytes(), b'licensed input')
            self.assertNotIn(b'licensed input', sealed.read_bytes())
            with patch.dict(os.environ, POLYGON_API_KEY='different-test-credential'):
                with self.assertRaisesRegex(ValueError, 'authentication failed'):
                    transfer('unseal', root / 'wrong', sealed)
            self.assertFalse((root / 'wrong').exists())

    def test_modified_ciphertext_rejected_before_extraction(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source'
            source.mkdir()
            (source / 'input').write_bytes(b'original')
            sealed = root / 'cache.sealed'
            with patch.dict(os.environ, POLYGON_API_KEY='synthetic-test-credential'):
                transfer('seal', source, sealed)
                blob = bytearray(sealed.read_bytes())
                blob[-1] ^= 1
                sealed.write_bytes(blob)
                with self.assertRaisesRegex(ValueError, 'authentication failed'):
                    transfer('unseal', root / 'restored', sealed)
            self.assertFalse((root / 'restored').exists())
