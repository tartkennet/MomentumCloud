import unittest
import copy
from datetime import datetime, timezone
from types import SimpleNamespace
from audit_action_price_install import install_compatible_action_prices


class InstalledPriceTests(unittest.TestCase):
    def build(self, cash=0, factor=10):
        action = dict(effective_date='2025-10-03', shares_per_share=1,
                      cash_per_share=cash, valuation_ticker='NEW')
        cache = {'2025-10-01': {'OLD': {'close': 28.74}},
                 '2025-10-03': {'NEW': {'close': 237.9}},
                 '2025-11-03': {'NEW': {'open': 114.1, 'close': 115}}}
        engine = SimpleNamespace(
            get_from_map=lambda rows, ticker: rows.get(ticker),
            resolve_exit_execution=lambda *args: ('2025-11-03', cache['2025-11-03']['NEW'], action),
            valuation_identity=lambda ticker, day: ('NEW', 1, action) if day >= '2025-10-03' else (ticker, 1, None),
            position_close_on_day=lambda rows, ticker, day: (rows[day][ticker]['close'], None))
        def paired(rows, ticker, day):
            if factor is None and ticker == 'NEW':
                raise RuntimeError('Missing verified basis')
            return factor if ticker == 'NEW' else 1
        install_compatible_action_prices(engine, paired)
        return engine, cache

    def test_exit_and_daily_use_same_units(self):
        engine, cache = self.build()
        _, row, action = engine.resolve_exit_execution(cache, sorted(cache), 'OLD', '2025-11-03', '2025-10-01', '2025-11-03')
        self.assertAlmostEqual(row['open'], 11.41)
        self.assertEqual(action['shares_per_share'], 1)
        self.assertAlmostEqual(engine.position_close_on_day(cache, 'OLD', '2025-10-03')[0], 23.79)
        self.assertAlmostEqual(engine.position_close_on_day(cache, 'OLD', '2025-11-03')[0], 11.5)
        self.assertAlmostEqual(engine.position_close_on_day(cache, 'OLD', '2025-10-01')[0], 28.74)

    def test_cash_component(self):
        engine, cache = self.build(cash=9)
        self.assertAlmostEqual(engine.position_close_on_day(cache, 'OLD', '2025-11-03')[0], 20.5)

    def test_missing_basis_stops_both_paths(self):
        engine, cache = self.build(factor=None)
        with self.assertRaises(RuntimeError):
            engine.position_close_on_day(cache, 'OLD', '2025-11-03')
        with self.assertRaises(RuntimeError):
            engine.resolve_exit_execution(cache, sorted(cache), 'OLD', '2025-11-03', '2025-10-01', '2025-11-03')

    def test_equal_basis_does_not_rescale(self):
        engine, cache = self.build(factor=1)
        self.assertAlmostEqual(engine.position_close_on_day(cache, 'OLD', '2025-11-03')[0], 115)


class ExecutionObservationTests(unittest.TestCase):
    def setup_case(self):
        action = dict(effective_date='2025-10-03', successor_ticker='NEW',
                      shares_per_share=1, valuation_ticker='NEW')
        cache = {'2025-10-01': {'OLD': {'close':10}},
                 '2025-10-03': {'OTHER': {'close':77}}}
        engine = SimpleNamespace(
            STOCK_CORPORATE_ACTIONS={'OLD':action},
            get_from_map=lambda rows,ticker:rows.get(ticker),
            resolve_exit_execution=lambda rows,days,ticker,target,entry,latest:
                (target,rows[target].get('NEW'),action),
            valuation_identity=lambda ticker,day,entry=None:
                ('NEW',1,action) if ticker=='OLD' and day>='2025-10-03' else (ticker,1,None),
            position_close_on_day=lambda rows,ticker,day:(rows[day][ticker]['close'],None))
        bar={'o':11,'h':12,'l':10,'c':11.5,'v':100,
             't':int(datetime(2025,10,3,tzinfo=timezone.utc).timestamp()*1000)}
        evidence={'OLD':{'effective_date':'2025-10-03','successor_ticker':'NEW',
                         'bases':{'true':{'results':[dict(bar)]},'false':{'results':[dict(bar)]}}}}
        return engine,cache,evidence

    def test_successor_execution_and_marks_do_not_change_formation_or_other_assets(self):
        engine,cache,evidence=self.setup_case()
        before=copy.deepcopy(cache)
        install_compatible_action_prices(engine,lambda *args:1,evidence)
        day,row,_=engine.resolve_exit_execution(cache,sorted(cache),'OLD','2025-10-03','2025-10-01','2025-10-03')
        self.assertEqual((day,row['open']),('2025-10-03',11))
        self.assertEqual(engine.position_close_on_day(cache,'OLD','2025-10-03','2025-10-01')[0],11.5)
        self.assertEqual(engine.position_close_on_day(cache,'OTHER','2025-10-03')[0],77)
        self.assertEqual(cache,before)

    def test_successor_observations_require_both_price_bases(self):
        engine,cache,evidence=self.setup_case()
        evidence['OLD']['bases']['false']['results']=[]
        with self.assertRaises(ValueError):
            install_compatible_action_prices(engine,lambda *args:1,evidence)

    def test_successor_observations_cannot_precede_the_dated_action(self):
        engine,cache,evidence=self.setup_case()
        evidence['OLD']['bases']['true']['results'][0]['t']-=86400000
        evidence['OLD']['bases']['false']['results'][0]['t']-=86400000
        with self.assertRaises(ValueError):
            install_compatible_action_prices(engine,lambda *args:1,evidence)


