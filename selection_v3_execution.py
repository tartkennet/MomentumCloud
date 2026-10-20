"""Source-backed execution facts for the broadened universe, never filters."""
import csv
import io
import json
import math
from datetime import datetime, timezone
from pathlib import Path

USX_SOURCE = "https://www.sec.gov/Archives/edgar/data/923571/000110465923078157/tm2320467d1_8k.htm"
ENTRY_HALTS = {
    "LBPH": {"effective_date": "2024-12-02", "source": "https://nasdaqtrader.com/TraderNews.aspx?id=ECA2024-589"},
    "EVRI": {"effective_date": "2025-07-01", "source": "https://www.sec.gov/Archives/edgar/data/1318568/000119312525153550/d159300dex991.htm"},
    "CRNX": {"effective_date": "2026-09-01", "source": "https://www.nasdaqtrader.com/TraderNews.aspx?id=ECA2026-628"},
}


def install_action(engine):
    # Closing was June 30; the SEC filing specifically dates the conversion
    # July 1 at 12:02 EDT. Retain the true effective day, even on a weekend.
    engine.CASH_CORPORATE_ACTIONS["USX"] = {
        "effective_date": "2023-07-01", "cash_per_share": 6.15,
        "reason": "CASH_MERGER", "execution": "cash-settlement",
        "source": USX_SOURCE,
    }


def documented_unfilled_entry(engine, cache, ticker, entry_day):
    """An order cannot create shares after a documented trading cessation.

    An arbitrary absent quote is still an evidence failure, not a canceled
    trade. No reserve is bought and the original allocation remains cash.
    """
    fact = ENTRY_HALTS.get(ticker)
    if not fact or entry_day < fact["effective_date"]:
        return None
    if engine.get_from_map(cache.get(entry_day, {}), ticker) is not None:
        raise RuntimeError("A quote conflicts with documented entry cessation: " + ticker)
    return {"status": "DOCUMENTED_UNFILLED_ORDER", "entry_day": entry_day,
            "ticker": ticker, "source": fact["source"],
            "reason": "Trading ceased before the intended entry; allocation remains cash, no replacement."}


def install_disclosed_stale_marks(engine, cache, days, source_paths, context):
    """Carry the last observed mark only on paired-source-confirmed gaps.

    This estimates NAV using a dated old quote; it is NOT a newly observed
    close, proof of no trading, or an executable fill. Every use is retained.
    The observed-only opening execution function is unchanged. No formation
    cache is edited. Any unconfirmed missing observation still fails closed.
    """
    pairs, allowed, uses = {}, {}, {}
    for path in source_paths:
        for record in json.loads(Path(path).read_text()):
            rows = {}
            if not record["response"].startswith("v,"):
                continue
            for row in csv.DictReader(io.StringIO(record["response"])):
                day = datetime.fromtimestamp(float(row["t"])/1000, timezone.utc).date().isoformat()
                rows[day] = {field: float(row[key]) for field, key in [("open","o"),("high","h"),("low","l"),("close","c")]}
            bounds = record["request"]["path"].split("/")[-2:]
            pairs.setdefault((record["ticker"], *bounds), {})[record["adjusted"]] = rows
    for (ticker, start, end), bases in pairs.items():
        if set(bases) != {"true", "false"}:
            continue
        if set(bases["true"]) != set(bases["false"]):
            raise RuntimeError("Paired session mismatch: " + ticker)
        for day, row in bases["true"].items():
            cached = engine.get_from_map(cache.get(day, {}), ticker)
            for field, price in row.items():
                if not math.isclose(price, bases["false"][day][field], rel_tol=1e-6, abs_tol=1e-8):
                    raise RuntimeError("Stale-mark source has an incompatible adjusted/raw basis: " + ticker)
                if cached and not math.isclose(price, float(cached[field]), rel_tol=1e-6, abs_tol=1e-8):
                    raise RuntimeError("Stale-mark source/cache price mismatch: " + ticker + " " + day)
        for day in days:
            if start <= day <= end and day not in bases["true"]:
                allowed[ticker, day] = bases["true"]
    original = engine.position_close_on_day

    def marked(cache, ticker, day, entry=None):
        value, action = original(cache, ticker, day, entry)
        if value is not None or action or entry is None or (ticker, day) not in allowed:
            return value, action
        source = allowed[ticker, day]
        prior = [d for d in source if entry <= d < day]
        if not prior:
            return None, action
        source_day = max(prior)
        last, prior_action = original(cache, ticker, source_day, entry)
        if last is None or prior_action or not math.isclose(last, source[source_day]["close"], rel_tol=1e-6):
            raise RuntimeError("No compatible last observation for stale NAV")
        key = (context.get("variant"), ticker, day, entry, context.get("stage"))
        uses[key] = {"variant": context.get("variant"), "stage": context.get("stage"),
                     "ticker": ticker, "day": day, "entry": entry, "last_observed_day": source_day,
                     "last_observed_close": float(last), "fresh_close_observed": False,
                     "convention": "Last reported mark carried; no new price or execution inferred."}
        return last, None

    engine.position_close_on_day = marked
    return uses
