"""Failure-path delivery tests. No network, remote writes or simulated trades."""
import contextlib
import io
import json
import unittest
from pathlib import Path
from unittest.mock import patch

import publish_h3_snapshot as publisher

ROOT=Path(__file__).resolve().parents[1]


class PublicationTests(unittest.TestCase):
    def test_observer_or_storage_failure_cannot_publish_a_healthy_update(self):
        for failure in ('observer','storage'):
            with self.subTest(failure=failure):
                captured={}
                def git(*args,cwd=publisher.ROOT):
                    if args[0]=='rev-parse':return '0'*40
                    if args[:2]==('worktree','add'):Path(args[3]).mkdir();return ''
                    if args[:3]==('diff','--cached','--name-only'):return 'public/data/h3.json'
                    if args[0]=='push':captured.update(json.loads((Path(cwd)/'public/data/h3.json').read_text()))
                    return ''
                with patch.object(publisher,'git',side_effect=git),contextlib.redirect_stdout(io.StringIO()):
                    publisher.publish(ROOT/'public/data/h3.json',ROOT/'no-previous-snapshot',
                                      'failure' if failure=='storage' else 'success',
                                      'failure' if failure=='observer' else 'success',ROOT/'no-manifest')
                self.assertEqual(captured['status'],'DATA_BLOCKED')
                self.assertEqual(captured['validation']['status'],'DATA_BLOCKED')
                self.assertTrue(captured['operations']['errors'])
                self.assertIsNone(captured['pending_intentions']);self.assertIsNone(captured['metrics'])
                self.assertEqual(captured['sessions'],0);self.assertEqual(captured['curve'],[])
                self.assertFalse(captured['live_approved']);self.assertFalse(captured['broker_orders_enabled'])
