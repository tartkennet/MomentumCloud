"""Independent CSV accounting and selection/risk contract checks for v3."""
import csv
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path

OUT = Path("audit_evidence/selection_v3_20261020")


def close(left, right, label):
    if not math.isclose(float(left), float(right), rel_tol=1e-10, abs_tol=1e-8):
        raise AssertionError(label + f": {left} != {right}")


def read(path):
    with path.open() as source:
        return list(csv.DictReader(source))


def main():
    comparison = json.loads((OUT / "comparison.json").read_text())
    if not comparison["status"].startswith("COMPLETE_"):
        raise AssertionError("Incomplete primary comparison")
    for filename, digest in comparison["source_sha256"].items():
        if hashlib.sha256(Path(filename).read_bytes()).hexdigest() != digest:
            raise AssertionError("Source changed after replay: " + filename)
    archived = json.loads(Path("audit_evidence/risk_managed_v2_20261020/comparison.json").read_text())
    if comparison["risk_configuration_unchanged"] != archived["configuration"]:
        raise AssertionError("Risk policy changed")
    equivalence = {}
    for filename in ("risk_managed_momentum.py", "run_risk_managed_research.py"):
        reference = (OUT / "reference_source" / filename).read_bytes()
        current = Path(filename).read_bytes()
        reference_hash = hashlib.sha256(reference).hexdigest()
        if reference_hash != archived["source_sha256"][filename]:
            raise AssertionError("Archived shared source does not match its recorded hash")
        if current.rstrip(b"\r\n") != reference.rstrip(b"\r\n"):
            raise AssertionError("Shared risk/execution implementation changed")
        equivalence[filename] = {
            "archived_sha256": reference_hash,
            "replayed_sha256": hashlib.sha256(current).hexdigest(),
            "identical_except_trailing_newlines": True,
        }
    (OUT / "shared_source_equivalence.json").write_text(json.dumps(equivalence, indent=2) + "\n")
    signals = {row["signal"]: row for row in json.loads((OUT / "signals.json").read_text())}
    unfilled = json.loads((OUT / "unfilled_orders.json").read_text())
    if len(signals) != 43:
        raise AssertionError("Signal coverage")
    for name in comparison["blocked_variants"]:
        if name in comparison["models"]:
            raise AssertionError("A blocked selector has a whole-sample return")
    stale = comparison.get("stale_marks", [])
    if bool(stale) == comparison["observed_only_validation"]:
        raise AssertionError("Stale-quote uncertainty must remain explicit")
    for mark in stale:
        if mark["fresh_close_observed"] or not mark["entry"] <= mark["last_observed_day"] < mark["day"]:
            raise AssertionError("Stale price mislabeled or drawn from the future")
    checks, years, selection_diagnostics = {}, {}, {}
    for name in [*comparison["models"], *comparison["benchmarks"]]:
        positions = read(OUT / (name + "_positions.csv"))
        periods = read(OUT / (name + "_results.csv"))
        nav = read(OUT / (name + "_daily_nav.csv"))
        if len(periods) != 43 or len(nav) != 943:
            raise AssertionError("Monthly or daily coverage changed")
        grouped = defaultdict(list)
        for p in positions:
            if not p["SignalDate"] < p["EntryDate"] < p["ExitDate"] <= p["PlannedExitDate"]:
                raise AssertionError("Invalid execution chronology")
            entry, exit_price, weight = map(float, (p["EntryPrice_USD"], p["ExitPrice_USD"], p["Weight"]))
            if not all(math.isfinite(v) and v > 0 for v in (entry, exit_price, weight)):
                raise AssertionError("Invalid trade values")
            close((exit_price/entry-1)*100, p["GrossReturn_pct"], "Trade return")
            grouped[p["SignalDate"]].append(p)
        nav_by_signal = defaultdict(list)
        for mark in nav:
            nav_by_signal[mark["SignalDate"]].append(mark)
        capital = gross_capital = stress_capital = 100.
        yearly = defaultdict(lambda: [1., 0])
        high_vol_lots = extension_lots = negative_momentum_lots = 0
        for period in periods:
            signal = period["SignalDate"]
            group = grouped[signal]
            if len({p["Ticker"] for p in group}) != len(group):
                raise AssertionError("Duplicate trade")
            exposure = sum(float(p["Weight"]) for p in group)
            if not 0 <= exposure <= 1 + 1e-12:
                raise AssertionError("Borrowed capital")
            if name in comparison["models"]:
                state = signals[signal]["variants"][name]
                canceled = [p for p in unfilled if p["variant"] == name and p["signal"] == signal]
                choices = {p["ticker"]: p for p in state["selected"]}
                if set(choices) != {p["Ticker"] for p in group} | {p["ticker"] for p in canceled}:
                    raise AssertionError("A chosen stock was silently omitted/replaced")
                target = sum(state["weights"].values())
                close(exposure + sum(p["intended_weight"] for p in canceled), target, "Unfilled allocations stay cash")
                close(target + state["sizing"]["cash_weight"], 1., "Initial risk budget")
                if state["sizing"]["forecast_volatility"] > .15 + 1e-12 or not 0 <= state["sizing"]["scale"] <= 1:
                    raise AssertionError("Changed unlevered risk target")
                for p in group:
                    c = choices[p["Ticker"]]
                    close(p["Weight"], state["weights"][p["Ticker"]], "Causal initial weight")
                    if float(p["Weight"]) > .05 + 1e-12:
                        raise AssertionError("Initial name cap")
                    if c["raw_price"] < 5 or c["raw_adv20"] < 2_000_000 or min(c["vol63"], c["vol126"]) <= 0:
                        raise AssertionError("Basic tradeability gate")
                    high_vol_lots += max(c["vol63"], c["vol126"]) > .6
                    extension_lots += c["extension50"] > .25
                    negative_momentum_lots += min(c["mom12_1"], c["mom6_1"], c["mom3_1"]) <= 0
            gross = sum(float(p["Weight"]) * (float(p["ExitPrice_USD"])/float(p["EntryPrice_USD"])-1) for p in group)
            cost = .003 if group else 0
            close(exposure, period["InitialExposure"], "Actual initial exposure")
            close(gross*100, period["GrossReturn_pct"], "Weighted monthly return")
            close((gross-cost)*100, period["NetReturn_pct"], "Full invested-month cost")
            capital *= 1 + gross - cost
            gross_capital *= 1 + gross
            stress_capital *= 1 + gross - 2*cost
            close(capital, period["PortfolioIndex"], "Compounded monthly capital")
            marks = nav_by_signal[signal]
            if marks[0]["Date"] != period["EntryDate"] or marks[-1]["Date"] != period["ExitDate"]:
                raise AssertionError("Valuation calendar")
            close(marks[-1]["PortfolioIndex"], capital, "Daily/monthly endpoint")
            yearly[signal[:4]][0] *= 1 + gross - cost
            yearly[signal[:4]][1] += 1
        peak, drawdown = 100., 0.
        for mark in nav:
            value = float(mark["PortfolioIndex"])
            if not math.isfinite(value) or value <= 0:
                raise AssertionError("Invalid NAV")
            peak = max(peak, value)
            drawdown = min(drawdown, value/peak-1)
        metrics = comparison["models"].get(name, comparison["benchmarks"].get(name))
        for value, key in [(capital-100,"net_return_pct"),(gross_capital-100,"gross_return_pct"),
                           (stress_capital-100,"cost_stress_060_return_pct"),(drawdown*100,"daily_drawdown_pct")]:
            close(value, metrics[key], key)
        checks[name] = {"status":"PASS", "positions":len(positions), "periods":43, "drawdown_marks":943,
                        "net_return_pct":capital-100,"daily_drawdown_pct":drawdown*100}
        years[name] = {year: {"signal_months":count,"net_return_pct":(value-1)*100}
                       for year,(value,count) in sorted(yearly.items())}
        if name in comparison["models"]:
            selection_diagnostics[name] = {"executed_lots_above_old_volatility_limit":high_vol_lots,
                "executed_lots_above_old_extension_limit":extension_lots,
                "executed_lots_with_nonpositive_completed_momentum":negative_momentum_lots}
    close(checks["spy_buy_hold"]["net_return_pct"],70.20238513471013,"Frozen SPY comparison")
    for key in ("net_return_pct","gross_return_pct","daily_drawdown_pct"):
        close(comparison["models"]["strict_v2"][key],archived["models"]["full_v2"][key],"Strict v2 parity")
    result = {"status":"PASS_INDEPENDENT_PRIMARY_SELECTION_RECONCILIATION", "checks":checks,
              "selection_diagnostics":selection_diagnostics, "by_signal_year":years,
              "blocked_variants":comparison["blocked_variants"], "documented_unfilled_orders":unfilled,
              "stale_quote_uses":stale,
              "limitation":"Arithmetic and contract audit, not an independent-provider check of every stock or unseen validation."}
    (OUT/"independent_check.json").write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__ == "__main__":
    main()
