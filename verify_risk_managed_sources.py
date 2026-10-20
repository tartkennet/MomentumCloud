"""Reference coverage and fixed worst-five source checks for v2.

These observations are from the same vendor. Missing individual references
remain unverified; they are never silently counted as successful checks.
"""
import csv
import io
import json
import math
from datetime import datetime, timezone
from pathlib import Path

OUT = Path("audit_evidence/risk_managed_v2_20261020")


def match(a, b):
    return math.isclose(float(a), float(b), rel_tol=1e-6, abs_tol=1e-8)


def main():
    positions = list(csv.DictReader((OUT / "full_v2_positions.csv").open()))
    references = json.loads(Path("evidence/selection/selection_reference_histories.json").read_text())
    references.update(json.loads(Path("classification/verified_ticker_histories.json").read_text()))
    for path in Path("universe_evidence").glob("histories_*.json"):
        for ticker, bases in json.loads(path.read_text()).items():
            references[ticker] = {}
            for key, kind in [("true", "adjusted"), ("false", "raw")]:
                references[ticker][kind] = {
                    datetime.fromtimestamp(bar["t"]/1000, timezone.utc).date().isoformat():
                        dict(zip(("open", "high", "low", "close", "volume"),
                                 (bar["o"], bar["h"], bar["l"], bar["c"], bar["v"])))
                    for bar in bases[key].get("results", [])}
    sources = json.loads((OUT / "top5_individual_source_responses.json").read_text())
    fresh = {}
    for record in sources:
        rows = {}
        for bar in csv.DictReader(io.StringIO(record["response"])):
            day = datetime.fromtimestamp(float(bar["t"])/1000, timezone.utc).date().isoformat()
            rows[day] = {field: float(bar[key]) for field, key in
                         [("open", "o"), ("high", "h"), ("low", "l"), ("close", "c"), ("volume", "v")]}
        kind = "adjusted" if record["adjusted"] == "true" else "raw"
        fresh.setdefault(record["ticker"], {})[kind] = rows
        # The new windows augment availability; they do not replace a longer
        # existing formation history or mutate the backtest cache.
        references.setdefault(record["ticker"], {}).setdefault(kind, {}).update(rows)
    worst = sorted(positions, key=lambda row: float(row["GrossReturn_pct"]))[:5]
    if {p["Ticker"] for p in worst} != set(fresh):
        raise AssertionError("The preselected five cases changed")
    cases = []
    for p in worst:
        ticker = p["Ticker"]
        adjusted, raw = fresh[ticker]["adjusted"], fresh[ticker]["raw"]
        for day, field, value in [(p["SignalDate"], "close", p["SignalPrice_USD"]),
                                   (p["EntryDate"], "open", p["EntryPrice_USD"]),
                                   (p["ExitDate"], "open", p["ExitPrice_USD"])]:
            if not match(adjusted[day][field], value):
                raise AssertionError(f"Worst-five individual price mismatch: {ticker} {day}")
        if not match(raw[p["SignalDate"]]["close"], p["RawSignalPrice_USD"]):
            raise AssertionError("Raw signal mismatch")
        trigger = next((day for day in sorted(adjusted)
                        if p["EntryDate"] <= day < p["PlannedExitDate"]
                        and adjusted[day]["close"] / float(p["EntryPrice_USD"]) - 1 <= -.10 + 1e-12), None)
        following = min(day for day in adjusted if day > trigger) if trigger else None
        if (trigger, following) != (p["TriggerDate"], p["ExitDate"]):
            raise AssertionError("Independent stop chronology mismatch")
        cases.append({"ticker": ticker, "signal": p["SignalDate"], "result": "PASS",
                      "gross_return_pct": float(p["GrossReturn_pct"]),
                      "initial_weight_pct": float(p["Weight"]) * 100,
                      "portfolio_contribution_pp": float(p["Weight"]) * float(p["GrossReturn_pct"]),
                      "first_stop_signal": trigger, "next_open_exit": following})
    coverage, missing, errors, action_exits = 0, [], [], 0
    for p in positions:
        fields = [(p["SignalDate"], "close", "SignalPrice_USD"),
                  (p["EntryDate"], "open", "EntryPrice_USD")]
        if p["CorporateAction"]:
            action_exits += 1
        else:
            fields.append((p["ExitDate"], "open", "ExitPrice_USD"))
        for day, field, key in fields:
            row = references.get(p["Ticker"], {}).get("adjusted", {}).get(day)
            if row is None:
                missing.append({"signal": p["SignalDate"], "ticker": p["Ticker"], "day": day, "field": key})
            elif match(row[field], p[key]):
                coverage += 1
            else:
                errors.append({"signal": p["SignalDate"], "ticker": p["Ticker"], "day": day,
                               "field": key, "model": float(p[key]), "reference": row[field]})
    result = {"status": "PASS_AVAILABLE_REFERENCES_INCOMPLETE_FULL_COVERAGE" if not errors else "FAILED_REFERENCE_MISMATCH",
              "top5": cases, "top5_price_and_raw_signal_checks": 20,
              "matched_individual_point_checks": coverage, "missing_individual_point_checks": len(missing),
              "corporate_action_exit_units_require_converter": action_exits,
              "mismatches": errors, "remaining": missing,
              "limitation": "Same-vendor individual endpoints; not independent-provider or fill evidence. No claim of all-lot reference coverage."}
    (OUT / "source_price_audit.json").write_text(json.dumps(result, indent=2) + "\n")
    if errors:
        raise AssertionError("Individual reference mismatch")
    print(json.dumps({key: value for key, value in result.items() if key != "remaining"}, indent=2))


if __name__ == "__main__":
    main()
