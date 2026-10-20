"""Self-financing research ledger with net rebalances and explicit order fees."""
from dataclasses import asdict, dataclass
import math


@dataclass(frozen=True)
class Costs:
    name: str
    commission: float = .0025
    minimum_usd: float = 1.
    fx: float = .0025
    half_spread: float = .0005
    slippage: float = .0005

    def __post_init__(self):
        values = (self.commission, self.minimum_usd, self.fx, self.half_spread, self.slippage)
        if any(not math.isfinite(v) or v < 0 for v in values):
            raise ValueError("Invalid cost assumption")
        if sum(values[i] for i in (0, 2, 3, 4)) >= 1:
            raise ValueError("Invalid proportional cost")

    def charge(self, notional, settlement=False):
        if not math.isfinite(notional) or notional < 0:
            raise ValueError("Invalid order notional")
        if notional <= 1e-8:
            return dict(commission=0., fx=0., half_spread=0., slippage=0., total=0.)
        result = {
            "commission": 0. if settlement else max(self.minimum_usd, self.commission * notional),
            "fx": self.fx * notional,
            "half_spread": 0. if settlement else self.half_spread * notional,
            "slippage": 0. if settlement else self.slippage * notional,
        }
        return {**result, "total": sum(result.values())}


SCENARIOS = (
    Costs("fee_only_lower_bound", half_spread=0., slippage=0.),
    Costs("central_assumption"),
    Costs("execution_stress", half_spread=.0025, slippage=.0025),
)
ZERO = Costs("zero_diagnostic", 0., 0., 0., 0., 0.)


def carry_allowed(lot, final_period):
    return (not final_period and lot["ExitDate"] == lot["PlannedExitDate"]
            and lot["ExitReason"] == "REBALANCE" and not lot.get("CorporateAction"))


def simulate(periods, lots, unit_marks, days, costs, initial_usd=10_000.):
    """Each lot has a UnitPath key and an unchanged signal-time Weight.

    Retained shares reset the monthly stop reference without a fictional trade.
    Costs are deducted on order dates. Same-ticker boundary orders are netted.
    """
    if not math.isfinite(initial_usd) or initial_usd <= 0:
        raise ValueError("Invalid initial capital")
    cash, carry = initial_usd, {}
    orders, allocations, nav, results = [], [], [], []
    grouped = {p["SignalDate"]: [] for p in periods}
    for lot in lots:
        grouped[lot["SignalDate"]].append(lot)
    for index, period in enumerate(periods):
        signal, entry, end = period["SignalDate"], period["EntryDate"], period["ExitDate"]
        group = grouped[signal]
        if len({p["Ticker"] for p in group}) != len(group):
            raise AssertionError("Duplicate lot")
        by_name = {p["Ticker"]: p for p in group}
        if any(not 0 < p["Weight"] <= 1 for p in group) or sum(p["Weight"] for p in group) > 1+1e-12:
            raise AssertionError("Borrowed allocation")
        old_values = {ticker: p["quantity"] * p["price"] for ticker, p in carry.items()}
        pre_nav = cash + sum(old_values.values())
        if pre_nav <= 0:
            raise RuntimeError("Portfolio insolvent")
        for ticker in set(carry) & set(by_name):
            if not math.isclose(carry[ticker]["price"], by_name[ticker]["EntryPrice_USD"], rel_tol=1e-10):
                raise RuntimeError("Cannot net different share-price units: " + ticker)
        names = sorted(set(carry) | set(by_name))

        def rebalance_cost(budget):
            return sum(costs.charge(abs(budget * by_name.get(t, {}).get("Weight", 0.) - old_values.get(t, 0.)))["total"]
                       for t in names)

        # Minimum fees are discontinuous at a zero order. Keep a feasible
        # budget and any residual in cash rather than force exact expenditure.
        low, high = 0., pre_nav
        if rebalance_cost(0.) > pre_nav:
            raise RuntimeError("Insufficient capital for required liquidation costs")
        for _ in range(90):
            trial = (low+high)/2
            if trial + rebalance_cost(trial) <= pre_nav:
                low = trial
            else:
                high = trial
        budget = low
        period_orders_start = len(orders)
        for ticker in names:
            target = budget * by_name.get(ticker, {}).get("Weight", 0.)
            delta = target - old_values.get(ticker, 0.)
            if abs(delta) <= 1e-8:
                continue
            price = by_name[ticker]["EntryPrice_USD"] if ticker in by_name else carry[ticker]["price"]
            fee = costs.charge(abs(delta))
            orders.append({"SignalDate": signal, "Date": entry, "Ticker": ticker,
                           "Side": "BUY" if delta > 0 else "SELL", "Reason": "NET_REBALANCE",
                           "Quantity": abs(delta)/price, "Price": price, "Notional": abs(delta),
                           **{k+"_USD": v for k, v in fee.items()}})
        entry_fees = sum(row["total_USD"] for row in orders[period_orders_start:])
        active = {}
        for lot in group:
            quantity = budget * lot["Weight"] / lot["EntryPrice_USD"]
            allocated = {**lot, "Quantity": quantity, "AllocationBudget_USD": budget,
                         "PreTradeNAV_USD": pre_nav, "CarryAtEnd": carry_allowed(lot, index == len(periods)-1)}
            allocations.append(allocated)
            active[lot["Ticker"]] = allocated
        cash = pre_nav - sum(p["Quantity"] * p["EntryPrice_USD"] for p in active.values()) - entry_fees
        if cash < -1e-6:
            raise AssertionError("Fees were financed by borrowing")
        period_nav_start = len(nav)
        for day in days:
            if not entry <= day <= end:
                continue
            for ticker, lot in list(active.items()):
                if day != lot["ExitDate"] or lot["CarryAtEnd"]:
                    continue
                notional = lot["Quantity"] * lot["ExitPrice_USD"]
                settlement = lot["ExitReason"] == "CASH_MERGER"
                fee = costs.charge(notional, settlement)
                cash += notional - fee["total"]
                orders.append({"SignalDate": signal, "Date": day, "Ticker": ticker,
                               "Side": "CASH_SETTLEMENT" if settlement else "SELL",
                               "Reason": lot["ExitReason"], "Quantity": lot["Quantity"],
                               "Price": lot["ExitPrice_USD"], "Notional": notional,
                               **{k+"_USD": v for k, v in fee.items()}})
                del active[ticker]
            holding_value = sum(lot["Quantity"] * (lot["ExitPrice_USD"] if day == lot["ExitDate"]
                                else unit_marks[lot["UnitPath"]][day]) for lot in active.values())
            if cash < -1e-6 or not math.isfinite(cash+holding_value):
                raise AssertionError("Invalid funded daily NAV")
            nav.append({"SignalDate": signal, "Date": day, "Cash_USD": cash,
                        "Holdings_USD": holding_value, "Equity_USD": cash+holding_value})
        carry = {ticker: {"quantity": lot["Quantity"], "price": lot["ExitPrice_USD"]}
                 for ticker, lot in active.items()}
        if any(not p["CarryAtEnd"] for p in active.values()):
            raise AssertionError("Unresolved monthly lot")
        month_orders = orders[period_orders_start:]
        final_value = nav[-1]["Equity_USD"]
        results.append({"SignalDate": signal, "EntryDate": entry, "ExitDate": end,
                        "PreTradeNAV_USD": pre_nav, "AllocationBudget_USD": budget,
                        "Equity_USD": final_value, "NetReturn_pct": (final_value/pre_nav-1)*100,
                        "InitialExposure_pct": sum(p["Weight"] for p in group)*budget/pre_nav*100,
                        "OrderCount": sum(o["Side"] != "CASH_SETTLEMENT" for o in month_orders),
                        "TradedNotional_USD": sum(o["Notional"] for o in month_orders if o["Side"] != "CASH_SETTLEMENT"),
                        "Cost_USD": sum(o["total_USD"] for o in month_orders),
                        "ValuationMarks": len(nav)-period_nav_start})
    peak, dd = initial_usd, 0.
    for row in nav:
        peak = max(peak, row["Equity_USD"])
        dd = min(dd, (row["Equity_USD"] / peak - 1)*100)
    total_fees = {key: sum(o[key+"_USD"] for o in orders) for key in
                  ("commission", "fx", "half_spread", "slippage", "total")}
    return {"summary": {"net_return_pct": (nav[-1]["Equity_USD"]/initial_usd-1)*100,
                         "daily_drawdown_pct": dd, "initial_usd": initial_usd,
                         "final_usd": nav[-1]["Equity_USD"], "positions": len(lots),
                         "market_orders": sum(o["Side"] != "CASH_SETTLEMENT" for o in orders),
                         "cash_settlements": sum(o["Side"] == "CASH_SETTLEMENT" for o in orders),
                         "total_cost_usd": total_fees,
                         "average_initial_exposure_pct": sum(r["InitialExposure_pct"] for r in results)/len(results),
                         "sum_traded_notional_over_period_start_nav": sum(r["TradedNotional_USD"]/r["PreTradeNAV_USD"] for r in results),
                         "cost_configuration": asdict(costs)},
            "orders": orders, "allocations": allocations, "nav": nav, "results": results}
