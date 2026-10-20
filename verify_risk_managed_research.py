"""Independently reconcile exported prices, weights, costs, NAV and choices.

Pure Python standard library: does not call the model or replay aggregator.
This validates arithmetic and contracts, not a second market-data vendor.
"""
import csv
import json
import math
from collections import defaultdict
from pathlib import Path

ROOT = Path("audit_evidence/risk_managed_v2_20261020")


def read(name):
    with (ROOT / name).open() as source:
        return list(csv.DictReader(source))


def close(a, b, what):
    if not math.isclose(float(a), float(b), rel_tol=1e-10, abs_tol=1e-8):
        raise AssertionError(what + f": {a} != {b}")


def main():
    comparison = json.loads((ROOT / "comparison.json").read_text())
    if comparison["status"] != "COMPLETE_PREREGISTERED_RESEARCH_REPLAY":
        raise AssertionError("Cannot approve an incomplete replay")
    all_positions, checks, annual = {}, {}, {}
    signal_records = {row["signal"]: row for row in json.loads((ROOT / "signals.json").read_text())}
    if len(signal_records) != 43:
        raise AssertionError("Unexpected signal coverage")
    for row in signal_records.values():
        sizing = row["sizing"]
        if not 0 <= sizing["scale"] <= 1 or sizing["forecast_volatility"] > .15 + 1e-12:
            raise AssertionError("Causal risk target violated")
        close(sum(row["weights"].values()) + sizing["cash_weight"], 1, "Risk/cash budget")
        if not row["risk_on"] and row["selected"]:
            raise AssertionError("Risk-off signal invested")
    for name in [*comparison["models"], *comparison["benchmarks"]]:
        positions, periods, nav = [read(name + suffix) for suffix in ("_positions.csv", "_results.csv", "_daily_nav.csv")]
        all_positions[name] = positions
        if len(periods) != 43 or len(nav) != 943:
            raise AssertionError("Unexpected period/valuation coverage")
        grouped = defaultdict(list)
        for row in positions:
            if not row["SignalDate"] < row["EntryDate"] <= row["ExitDate"] <= row["PlannedExitDate"]:
                raise AssertionError("Execution chronology error")
            entry, exit_price, weight = map(float, (row["EntryPrice_USD"], row["ExitPrice_USD"], row["Weight"]))
            if not all(math.isfinite(v) and v > 0 for v in (entry, exit_price, weight)):
                raise AssertionError("Invalid price/weight")
            close((exit_price / entry - 1) * 100, row["GrossReturn_pct"], "Lot return")
            if name in comparison["models"]:
                if weight > .05 + 1e-12:
                    raise AssertionError("Initial position cap violated")
                signal = signal_records[row["SignalDate"]]
                selected = {p["ticker"]: p for p in signal["selected"]}
                c = selected[row["Ticker"]]
                if c["raw_price"] < 10 or c["raw_adv20"] < 20_000_000 or max(c["vol63"], c["vol126"]) > .6:
                    raise AssertionError("Selection gate violated")
                if c["max_abs_daily63"] > .25 or c["extension50"] > .25:
                    raise AssertionError("Recent risk limit violated")
                expected_weight = .04 if name == "selection_equal" else signal["weights"][row["Ticker"]]
                close(expected_weight, weight, "Initial causal weight")
            grouped[row["SignalDate"]].append(row)
        nav_by_period = defaultdict(list)
        for row in nav:
            nav_by_period[row["SignalDate"]].append(row)
        capital = gross_capital = stress_capital = 100.0
        yearly = defaultdict(lambda: [1.0, 0])
        for period in periods:
            key = period["SignalDate"]
            group = grouped[key]
            if len({p["Ticker"] for p in group}) != len(group):
                raise AssertionError("Duplicate position")
            exposure = sum(float(p["Weight"]) for p in group)
            if exposure > 1 + 1e-12:
                raise AssertionError("Borrowed capital")
            gross = sum(float(p["Weight"]) * (float(p["ExitPrice_USD"]) / float(p["EntryPrice_USD"]) - 1) for p in group)
            cost = .003 if group else 0
            close(exposure, period["InitialExposure"], "Exposure")
            close(gross * 100, period["GrossReturn_pct"], "Weighted monthly return")
            close((gross - cost) * 100, period["NetReturn_pct"], "Monthly cost")
            capital *= 1 + gross - cost
            gross_capital *= 1 + gross
            stress_capital *= 1 + gross - 2 * cost
            close(capital, period["PortfolioIndex"], "Compounded capital")
            marks = nav_by_period[key]
            close(capital, marks[-1]["PortfolioIndex"], "Daily terminal capital")
            if marks[0]["Date"] != period["EntryDate"] or marks[-1]["Date"] != period["ExitDate"]:
                raise AssertionError("Daily interval mismatch")
            yearly[key[:4]][0] *= 1 + gross - cost
            yearly[key[:4]][1] += 1
        peak, drawdown = 100.0, 0.0
        for row in nav:
            value = float(row["PortfolioIndex"])
            if not math.isfinite(value) or value <= 0:
                raise AssertionError("Invalid NAV")
            peak = max(peak, value)
            drawdown = min(drawdown, value / peak - 1)
        saved = comparison["models"].get(name, comparison["benchmarks"].get(name))
        for observed, key in [(capital - 100, "net_return_pct"), (gross_capital - 100, "gross_return_pct"),
                              (stress_capital - 100, "cost_stress_060_return_pct"), (drawdown * 100, "daily_drawdown_pct")]:
            close(observed, saved[key], key)
        checks[name] = {"status": "PASS", "positions": len(positions), "periods": len(periods),
                        "nav_marks": len(nav), "net_return_pct": capital - 100,
                        "daily_drawdown_pct": drawdown * 100}
        annual[name] = {year: {"signal_months": count, "net_return_pct": (growth - 1) * 100}
                        for year, (growth, count) in sorted(yearly.items())}
    keys = lambda name: {(p["SignalDate"], p["Ticker"]): p for p in all_positions[name]}
    equal, sized, full = map(keys, ("selection_equal", "selection_sized", "full_v2"))
    if equal.keys() != sized.keys() or equal.keys() != full.keys():
        raise AssertionError("Ablation choices changed")
    for key in equal:
        for field in ("EntryDate", "EntryPrice_USD", "ExitDate", "ExitPrice_USD", "ExitReason"):
            if equal[key][field] != sized[key][field]:
                raise AssertionError("Sizing ablation changed execution")
        for field in ("EntryDate", "EntryPrice_USD", "Weight"):
            if sized[key][field] != full[key][field]:
                raise AssertionError("Daily gate ablation changed entries or allocation")
    # Price benchmark must match the existing frozen comparison exactly.
    close(checks["spy_buy_hold"]["net_return_pct"], 70.20238513471013, "Frozen SPY baseline")
    result = {"status": "PASS_INDEPENDENT_CSV_RECONCILIATION", "checks": checks,
              "same_choices_and_component_contracts": True, "by_signal_year": annual,
              "limitation": "Checks exported arithmetic/contracts. Does not independently source market prices or prove future alpha."}
    (ROOT / "independent_check.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
