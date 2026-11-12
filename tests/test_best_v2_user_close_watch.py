import unittest
from datetime import datetime,timedelta
from best_v2_user_close_watch import plan,published,watch


def report(day):
    return dict(price_as_of=day,errors=[],technical_readiness={'status':'PASS'},
                paper={'valuation_as_of':day,'statistics_audit':{'status':'PASS'}})


class CloseWatchTests(unittest.TestCase):
    def test_actual_missed_close_is_covered_by_started_afternoon_runs(self):
        for stamp,wait in [('2026-11-12T20:49:14+00:00',25*60+46),
                           ('2026-11-12T16:56:00+00:00',259*60)]:
            p=plan(datetime.fromisoformat(stamp))
            self.assertEqual(p['status'],'WATCH')
            self.assertEqual(p['session'],'2026-11-12')
            self.assertEqual(p['wait_seconds'],wait)

    def test_holidays_half_days_and_us_swedish_dst_gap(self):
        for stamp,status,due in [
            ('2026-11-26T20:00:00Z','EXCHANGE_CLOSED',None),
            ('2026-11-14T20:00:00Z','EXCHANGE_CLOSED',None),
            ('2026-11-12T13:00:00Z','TOO_EARLY','2026-11-12T21:15:00+00:00'),
            ('2026-11-27T17:00:00Z','WATCH','2026-11-27T18:15:00+00:00'),
            ('2026-03-20T19:00:00Z','WATCH','2026-03-20T20:15:00+00:00'),
            ('2026-10-27T19:00:00Z','WATCH','2026-10-27T20:15:00+00:00')]:
            with self.subTest(stamp=stamp):
                p=plan(datetime.fromisoformat(stamp))
                self.assertEqual(p['status'],status)
                if due:self.assertEqual(p['due'],due)

    def test_waits_for_close_then_dispatches_without_another_cron_event(self):
        clock=[datetime.fromisoformat('2026-11-12T20:49:14Z')]
        calls=[];saved=[report('2026-11-11')]
        def sleep(seconds):clock[0]+=timedelta(seconds=seconds)
        def start(repo,day,token):
            calls.append((clock[0],day,token));saved[0]=report(day)
        proof=watch('owner/repo','fixture',now=lambda:clock[0],sleep=sleep,
                    read=lambda repo:saved[0],start=start,
                    status=lambda *args:dict(id=123,status='completed',conclusion='success'))
        self.assertEqual(proof['status'],'VERIFIED')
        self.assertEqual(calls[0][0].isoformat(),'2026-11-12T21:15:00+00:00')
        self.assertEqual(len(calls),1)

    def test_retries_failed_collection_but_never_accepts_wrong_session(self):
        clock=[datetime.fromisoformat('2026-11-12T22:00:00Z')];calls=[]
        def sleep(seconds):clock[0]+=timedelta(seconds=seconds)
        def start(*args):calls.append(args)
        def status(*args):return dict(id=123,status='completed',conclusion='failure')
        with self.assertRaisesRegex(RuntimeError,'CLOSE_VALUATION_NOT_PUBLISHED'):
            watch('owner/repo','fixture',now=lambda:clock[0],sleep=sleep,
                  read=lambda repo:report('2026-11-11'),start=start,status=status)
        self.assertEqual(len(calls),3)
        self.assertFalse(published(report('2026-11-11'),'2026-11-12'))

    def test_already_published_day_is_idempotent(self):
        def never(*args):raise AssertionError('Unexpected dispatch')
        result=watch('owner/repo','fixture',now=lambda:datetime.fromisoformat('2026-11-12T22:00:00Z'),
                     read=lambda repo:report('2026-11-12'),start=never)
        self.assertEqual(result['status'],'ALREADY_VERIFIED')

    def test_manual_validation_exercises_dispatch_even_for_published_close(self):
        calls=[]
        result=watch('owner/repo','fixture',now=lambda:datetime.fromisoformat('2026-11-12T22:00:00Z'),
                     read=lambda repo:report('2026-11-12'),refresh=True,
                     start=lambda *args:calls.append(args),
                     status=lambda *args:dict(id=123,status='completed',conclusion='success'))
        self.assertEqual(result['status'],'VERIFIED')
        self.assertEqual(len(calls),1)
