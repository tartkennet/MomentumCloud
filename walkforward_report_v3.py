#!/usr/bin/env python3
"""No-look-ahead walk-forward validation for Momentum stop-loss research."""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


STOP_VARIANTS = (
    "stop6_next_open",
    "stop8_next_open",
    "stop10_next_open",
    "stop12_next_open",
)


def compounded_return(values: pd.Series) -> float:
    return float(((1.0 + values.astype(float) / 100.0).prod() - 1.0) * 100.0)


def max_drawdown(values: pd.Series) -> float:
    equity = (1.0 + values.astype(float) / 100.0).cumprod()
    if equity.empty:
        return 0.0
    drawdown = equity / equity.cummax() - 1.0
    return float(min(0.0, drawdown.min()) * 100.0)


def trailing_sharpe(values: pd.Series) -> float:
    """Risk-adjusted score for ranking only; monthly risk-free rate is set to zero."""
    returns = values.astype(float)
    volatility = float(returns.std(ddof=1))
    if len(returns) < 2 or not np.isfinite(volatility) or volatility == 0:
        return float("-inf") if float(returns.mean()) <= 0 else float("inf")
    return float(returns.mean() / volatility * np.sqrt(12.0))


def load_aligned_results(input_dir: Path, prefix: str) -> dict[str, pd.DataFrame]:
    frames: dict[str, pd.DataFrame] = {}
    required = {"SignalDate", "EntryDate", "ExitDate", "NetReturn_pct", "SPYReturn_pct"}
    reference_dates: list[str] | None = None
    for variant in STOP_VARIANTS:
        path = input_dir / f"{prefix}_{variant}_results.csv"
        if not path.exists():
            raise RuntimeError(f"Missing walk-forward input: {path.name}")
        frame = pd.read_csv(path).sort_values("SignalDate").reset_index(drop=True)
        missing = required.difference(frame.columns)
        if missing:
            raise RuntimeError(f"{path.name} is missing columns: {sorted(missing)}")
        dates = frame["SignalDate"].astype(str).tolist()
        if len(dates) != len(set(dates)):
            raise RuntimeError(f"Duplicate SignalDate in {path.name}")
        if reference_dates is None:
            reference_dates = dates
        elif dates != reference_dates:
            raise RuntimeError("Stop variants do not contain identical chronological periods")
        frames[variant] = frame
    return frames


def choose_variant(frames: dict[str, pd.DataFrame], start: int, end: int) -> tuple[str, float]:
    """Select using training rows [start:end]; row end is never inspected."""
    scores = {
        variant: trailing_sharpe(frame.iloc[start:end]["NetReturn_pct"])
        for variant, frame in frames.items()
    }
    # Deterministic tie-break: prefer the less frequently triggered, wider stop.
    selected = max(STOP_VARIANTS, key=lambda variant: (scores[variant], int(variant[4:variant.index("_")])))
    return selected, scores[selected]


def summary_row(label: str, strategy: pd.Series, spy: pd.Series) -> dict:
    return {
        "Variant": label,
        "OOSPeriods": int(len(strategy)),
        "TotalReturn_pct": compounded_return(strategy),
        "SPYTotalReturn_pct": compounded_return(spy),
        "TotalEdgeVsSPY_pct": compounded_return(strategy) - compounded_return(spy),
        "WinningPeriods_pct": float((strategy.astype(float) > 0).mean() * 100.0),
        "BeatSPYPeriods_pct": float((strategy.astype(float).to_numpy() > spy.astype(float).to_numpy()).mean() * 100.0),
        "BestPeriod_pct": float(strategy.astype(float).max()),
        "WorstPeriod_pct": float(strategy.astype(float).min()),
        "RebalanceMaxDrawdown_pct": max_drawdown(strategy),
        "Execution": "SIGNAL_CLOSE_ENTRY_NEXT_SESSION",
        "Validation": "ROLLING_WALK_FORWARD_NO_LOOKAHEAD",
        "Universe": "CURRENT_TEMPLATE_SURVIVORSHIP_BIAS",
        "ProductionEligible": False,
    }


def build_walkforward_report(
    input_dir: Path,
    input_prefix: str = "Momentum_walk_forward",
    output_prefix: str = "Momentum_walk_forward",
    training_periods: int = 6,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if training_periods < 3:
        raise ValueError("training_periods must be at least 3")
    frames = load_aligned_results(input_dir, input_prefix)
    period_count = len(next(iter(frames.values())))
    if period_count <= training_periods:
        raise RuntimeError(
            f"Need more than {training_periods} periods; received {period_count}"
        )

    decisions: list[dict] = []
    for index in range(training_periods, period_count):
        train_start = index - training_periods
        selected, score = choose_variant(frames, train_start, index)
        source = frames[selected].iloc[index]
        decisions.append(
            {
                "SignalDate": str(source["SignalDate"]),
                "EntryDate": str(source["EntryDate"]),
                "ExitDate": str(source["ExitDate"]),
                "TrainingStartSignal": str(frames[selected].iloc[train_start]["SignalDate"]),
                "TrainingEndSignal": str(frames[selected].iloc[index - 1]["SignalDate"]),
                "TrainingPeriods": training_periods,
                "SelectedVariant": selected,
                "SelectedStop_pct": float(selected[4:selected.index("_")]),
                "TrainingSharpe": score,
                "OOSNetReturn_pct": float(source["NetReturn_pct"]),
                "OOSSPYReturn_pct": float(source["SPYReturn_pct"]),
                "OOSEdgeVsSPY_pct": float(source["NetReturn_pct"] - source["SPYReturn_pct"]),
            }
        )

    decisions_df = pd.DataFrame(decisions)
    spy = decisions_df["OOSSPYReturn_pct"]
    comparison_rows = [
        summary_row("walk_forward_selected", decisions_df["OOSNetReturn_pct"], spy)
    ]
    for variant in STOP_VARIANTS:
        oos = frames[variant].iloc[training_periods:].reset_index(drop=True)
        comparison_rows.append(summary_row(variant, oos["NetReturn_pct"], oos["SPYReturn_pct"]))
    comparison = pd.DataFrame(comparison_rows)

    selected = decisions_df["SelectedVariant"]
    comparison.loc[comparison["Variant"] == "walk_forward_selected", "StopSwitches"] = int(
        (selected != selected.shift()).sum() - 1
    )
    for variant in STOP_VARIANTS:
        comparison.loc[
            comparison["Variant"] == "walk_forward_selected", f"Selected_{variant}_periods"
        ] = int((selected == variant).sum())

    decisions_df.to_csv(input_dir / f"{output_prefix}_decisions.csv", index=False)
    comparison.to_csv(input_dir / f"{output_prefix}_comparison.csv", index=False)
    return decisions_df, comparison


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, default=Path("."))
    parser.add_argument("--input-prefix", default="Momentum_walk_forward")
    parser.add_argument("--output-prefix", default="Momentum_walk_forward")
    parser.add_argument("--training-periods", type=int, default=6)
    args = parser.parse_args()
    _, report = build_walkforward_report(
        args.input_dir, args.input_prefix, args.output_prefix, args.training_periods
    )
    print(report.to_string(index=False))
