"""Versioned raw inputs for Core. No adjusted legacy price cache is accepted."""
from __future__ import annotations

import gzip
import hashlib
import json
import logging
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from backtest_momentum_v3 import (
    CASH_CORPORATE_ACTIONS, STOCK_CORPORATE_ACTIONS, fetch_spy_trading_calendar,
)
from momentum_core import DataBlocked


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    text = json.dumps(value, separators=(",", ":"), allow_nan=False)
    if path.suffix == ".gz":
        with gzip.open(temporary, "wt", encoding="utf-8") as stream:
            stream.write(text)
    else:
        temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def read_json(path):
    if Path(path).suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as stream:
            return json.load(stream)
    return json.loads(Path(path).read_text(encoding="utf-8"))


def paginate(client, path, params):
    result = []
    seen = set()
    while True:
        payload = client._get(path, params)
        if not isinstance(payload.get("results"), list):
            # Empty, successful endpoints may omit results.
            if payload.get("status") not in ("OK", "DELAYED"):
                raise DataBlocked(f"Unusable response from {path}")
        result.extend(payload.get("results") or [])
        next_url = payload.get("next_url")
        if not next_url:
            return result
        parsed = urlparse(str(next_url))
        if parsed.path != path or parsed.netloc not in ("api.polygon.io", "api.massive.com"):
            raise DataBlocked("Unexpected corporate/reference pagination destination")
        params = {k: v[-1] for k, v in parse_qs(parsed.query).items()
                  if k.lower() != "apikey" and v}
        signature = json.dumps(params, sort_keys=True)
        if signature in seen:
            raise DataBlocked("Repeated pagination cursor")
        seen.add(signature)


class CoreData:
    cash_actions = CASH_CORPORATE_ACTIONS
    stock_actions = STOCK_CORPORATE_ACTIONS

    def __init__(self, client, start, end, cache_dir=".momentum_core_cache"):
        self.client = client
        self.root = Path(cache_dir)
        self.root.mkdir(parents=True, exist_ok=True)
        warmup = (date.fromisoformat(start) - timedelta(days=550)).isoformat()
        self.days = fetch_spy_trading_calendar(client, warmup, end)
        self.index = {day: i for i, day in enumerate(self.days)}
        self.sessions = [day for day in self.days if start <= day <= end]
        logging.info("Core calendar: requested %s..%s; observed %s..%s (%d days); replay %s (%d days)",
                     warmup, end, self.days[0], self.days[-1], len(self.days),
                     self.sessions[0] if self.sessions else None, len(self.sessions))
        if len(self.sessions) < 2 or self.index[self.sessions[0]] < 252:
            # Diagnose entitlement separately: aggregate and grouped endpoints
            # can expose different historical depths. Never shorten the test.
            probe = self.client._get("/v2/aggs/grouped/locale/us/market/stocks/2023-01-03",
                                     {"adjusted": "false", "include_otc": "false"})
            logging.info("Core older raw-data probe 2023-01-03: %d rows, SPY=%s", 
                         len(probe.get("results", [])),
                         any(r.get("T") == "SPY" for r in probe.get("results", [])))
            raise DataBlocked(
                f"Incomplete calendar: requested {warmup}..{end}; observed "
                f"{self.days[0]}..{self.days[-1]} ({len(self.days)} days); "
                f"replay count={len(self.sessions)}, prior sessions="
                f"{self.index[self.sessions[0]] if self.sessions else 0}")
        self.used_inputs = {}
        self.splits = self._events("splits", warmup, end)
        self.dividends = self._events("dividends", start, end)
        for event in self.splits:
            if not event.get("ticker") or not event.get("execution_date"):
                raise DataBlocked("Incomplete split identity/date")
        self.splits_by_ticker = {}
        for event in self.splits:
            self.splits_by_ticker.setdefault(event["ticker"], []).append(event)
        for event in self.dividends:
            if not event.get("ticker") or not event.get("ex_dividend_date"):
                raise DataBlocked("Incomplete dividend identity/ex-date")

    def _remember(self, label, value):
        self.used_inputs[label] = hashlib.sha256(
            json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        ).hexdigest()

    def _events(self, kind, start, end):
        path = self.root / f"{kind}-{start}-{end}-v1.json.gz"
        column = "execution_date" if kind == "splits" else "ex_dividend_date"
        if path.exists():
            events = read_json(path)
        else:
            events = paginate(self.client, f"/stocks/v1/{kind}",
                              {column + ".gte": start, column + ".lte": end,
                               "sort": column + ".asc", "limit": 5000})
            unique = {}
            for event in events:
                key = event.get("id") or json.dumps(event, sort_keys=True)
                unique[key] = event
            events = list(unique.values())
            atomic_json(path, events)
        self._remember(f"{kind}/{start}/{end}", events)
        logging.info("Core %s: %d events", kind, len(events))
        return events

    @lru_cache(maxsize=270)
    def bars(self, day):
        if day not in self.index:
            raise DataBlocked(f"Requested non-session price {day}")
        path = self.root / "raw-v1" / f"{day}.json.gz"
        if path.exists():
            payload = read_json(path)
            if payload.get("basis") != "RAW" or payload.get("date") != day:
                raise DataBlocked(f"Invalid raw cache metadata {day}")
            result = payload["bars"]
        else:
            response = self.client._get(f"/v2/aggs/grouped/locale/us/market/stocks/{day}",
                                        {"adjusted": "false", "include_otc": "false"})
            result = {r["T"]: [r.get("o"), r.get("c"), r.get("v")]
                      for r in response.get("results", []) if r.get("T")}
            if "SPY" not in result:
                raise DataBlocked(f"No SPY in raw grouped session {day}")
            atomic_json(path, {"basis": "RAW", "version": 1, "date": day, "bars": result})
            logging.info("Core raw session %s: %d securities", day, len(result))
        self._remember(f"raw/{day}", result)
        return result

    def history(self, day, ticker, count):
        end = self.index[day]
        if end + 1 < count:
            return []
        return [(stamp, self.bars(stamp).get(ticker))
                for stamp in reversed(self.days[end + 1 - count:end + 1])]

    def universe(self, day):
        path = self.root / "universe-v1" / f"{day}.json.gz"
        if path.exists():
            payload = read_json(path)
            if payload.get("date") != day or payload.get("basis") != "PIT_REFERENCE_V1":
                raise DataBlocked(f"Invalid historical universe cache {day}")
            records = payload["records"]
        else:
            records = paginate(self.client, "/v3/reference/tickers",
                               {"market": "stocks", "type": "CS", "date": day,
                                "active": "true", "order": "asc", "limit": 1000,
                                "sort": "ticker"})
            if not records:
                raise DataBlocked(f"Empty historical universe {day}")
            atomic_json(path, {"basis": "PIT_REFERENCE_V1", "date": day, "records": records})
            logging.info("Core point-in-time universe %s: %d records", day, len(records))
        self._remember(f"universe/{day}", records)
        return records

    def first_is_month_boundary(self):
        i = self.index[self.sessions[0]]
        return i > 0 and self.days[i - 1][:7] != self.sessions[0][:7]

    def input_fingerprint(self):
        return hashlib.sha256(json.dumps(self.used_inputs, sort_keys=True).encode()).hexdigest()
