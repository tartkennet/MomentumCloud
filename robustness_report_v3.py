#!/usr/bin/env python3
"""Combine Momentum research variants into an objective robustness report."""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def compounded_return(values: pd.Series) -> float:
    """Compound percentage returns and return a percentage."""
    return float(((1.0 + values.astype(float) / 100.0).prod() - 1.0) * 100.0)


def rolling_windows(results: pd.DataFrame, variant: str, months: int) -> list[dict]:
    """Build overlapping monthly windows without using future data in a period."""
    rows: list[dict] = []
    if len(results) < months:
        return rows
    for end_index in range(months - 1, len(results)):
        window = results.iloc[end_index - months + 1 : end_index + 1]
        strategy = compounded_return(window["NetReturn_pct"])
        spy = compounded_return(window["SPYReturn_pct"])
        rows.append(
            {
                "Variant": variant,
                "WindowMonths": months,
                "StartEntryDate": str(window.iloc[0]["EntryDate"]),
                "EndExitDate": str(window.iloc[-1]["ExitDate"]),
                "NetReturn_pct": strategy,
                "SPYReturn_pct": spy,
                "EdgeVsSPY_pct": strategy - spy,
            }
        )
    return rows


def window_metrics(windows: pd.DataFrame, months: int) -> dict:
    subset = windows[windows["WindowMonths"] == months]
    prefix = f"Rolling{months}M"
    if subset.empty:
        return {
            f"{prefix}Windows": 0,
            f"{prefix}Positive_pct": None,
            f"{prefix}BeatSPY_pct": None,
            f"{prefix}WorstReturn_pct": None,
            f"{prefix}MedianReturn_pct": None,
            f"{prefix}WorstEdge_pct": None,
        }
    return {
        f"{prefix}Windows": int(len(subset)),
        f"{prefix}Positive_pct": float((subset["NetReturn_pct"] > 0).mean() * 100),
        f"{prefix}BeatSPY_pct": float((subset["EdgeVsSPY_pct"] > 0).mean() * 100),
        f"{prefix}WorstReturn_pct": float(subset["NetReturn_pct"].min()),
        f"{prefix}MedianReturn_pct": float(subset["NetReturn_pct"].median()),
        f"{prefix}WorstEdge_pct": float(subset["EdgeVsSPY_pct"].min()),
    }


def build_report(input_dir: Path, output_prefix: str = "Momentum_robustness") -> tuple[pd.DataFrame, pd.DataFrame]:
    summaries = sorted(input_dir.glob(f"{output_prefix}_*_summary.csv"))
    if not summaries:
        raise RuntimeError(f"No {output_prefix}_*_summary.csv files found in {input_dir}")

    comparison_rows: list[dict] = []
    all_windows: list[dict] = []
    for summary_path in summaries:
        variant = summary_path.name[len(output_prefix) + 1 : -len("_summary.csv")]
        results_path = input_dir / f"{output_prefix}_{variant}_results.csv"
        positions_path = input_dir / f"{output_prefix}_{variant}_positions.csv"
        if not results_path.exists() or not positions_path.exists():
            raise RuntimeError(f"Incomplete files for variant {variant}")

        summary = pd.read_csv(summary_path).iloc[0]
        results = pd.read_csv(results_path)
        positions = pd.read_csv(positions_path)
        windows = rolling_windows(results, variant, 3) + rolling_windows(results, variant, 6)
        all_windows.extend(windows)
        variant_windows = pd.DataFrame(windows)
        worst = positions.loc[positions["GrossReturn_pct"].astype(float).idxmin()]

        row = {
            "Variant": variant,
            "Periods": int(summary["Periods"]),
            "TotalReturn_pct": float(summary["TotalReturn_pct"]),
            "SPYTotalReturn_pct": float(summary["SPYTotalReturn_pct"]),
            "TotalEdgeVsSPY_pct": float(summary["TotalEdgeVsSPY_pct"]),
            "PeriodHitRate_pct": float(summary["PeriodHitRate_pct"]),
            "BestPeriod_pct": float(summary["BestPeriod_pct"]),
            "WorstPeriod_pct": float(summary["WorstPeriod_pct"]),
            "DailyMaxDrawdown_pct": float(summary["DailyMaxDrawdown_pct"]),
            "EarlyExitPositions": int(summary["EarlyExitPositions"]),
            "WorstPositionTicker": str(worst["Ticker"]),
            "WorstPositionReturn_pct": float(worst["GrossReturn_pct"]),
            "Execution": str(summary["Execution"]),
            "Universe": str(summary["Universe"]),
            "ResearchStatus": "LIMITED_CURRENT_UNIVERSE",
            "ProductionEligible": False,
        }
        row.update(window_metrics(variant_windows, 3))
        row.update(window_metrics(variant_windows, 6))
        comparison_rows.append(row)

    comparison = pd.DataFrame(comparison_rows).sort_values("Variant").reset_index(drop=True)
    windows_df = pd.DataFrame(all_windows).sort_values(
        ["Variant", "WindowMonths", "StartEntryDate"]
    ).reset_index(drop=True)
    comparison.to_csv(input_dir / f"{output_prefix}_comparison.csv", index=False)
    windows_df.to_csv(input_dir / f"{output_prefix}_rolling_windows.csv", index=False)
    return comparison, windows_df


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, default=Path("."))
    parser.add_argument("--output-prefix", default="Momentum_robustness")
    args = parser.parse_args()
    report, _ = build_report(args.input_dir, args.output_prefix)
    print(report.to_string(index=False))
