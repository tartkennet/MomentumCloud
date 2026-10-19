"""Audit explicit cash flows without inventing fills, settlement dates or FX.

This isolated accounting tool does not select stocks, allocate a rebalance,
change the fixed-exit engine, or produce investment returns/NAV. A missing
settlement remains a receivable; a missing exit remains an open position.
Amounts are actual cash amounts supplied by the caller, never price estimates.
Same-timestamp events retain input order, so availability is never inferred.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation


def _amount(value):
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError("Cash amounts must be finite and non-negative") from None
    if not result.is_finite() or result < 0:
        raise ValueError("Cash amounts must be finite and non-negative")
    return result


def _time(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("An explicit timezone is required")
    return result.astimezone(timezone.utc)


def _currency(value):
    if not isinstance(value, str) or len(value) != 3 or not value.isascii() or not value.isupper() or not value.isalpha():
        raise ValueError("Currency must be an explicit three-letter uppercase code")
    return value


def replay_cash_availability(initial_cash, events):
    """Return a cash journal; reject unsupported funding before mutating state.

    BUY: lot_id, amount, currency, optional planned_exit (ISO date).
    EXIT: lot_id, receivable_id, amount, currency; creates no available cash.
    RECEIVE: receivable_id; releases exactly that receivable in its currency.
    FX: currency, amount, receive_currency, receive_amount; explicit cash legs.
    FEE: amount, currency. Every event also needs id, at, kind, source.

    Source strings are trace references, not machine proof of valid evidence.
    No event is scheduled, inferred, fetched, or executed by this function.
    """
    cash = {_currency(k): _amount(v) for k, v in initial_cash.items()}
    lots, receivables, journal = {}, {}, []
    used_events, used_lots, used_receivables = set(), set(), set()
    previous = None

    for event in events:
        event_id = event.get("id")
        if not isinstance(event_id, str) or not event_id.strip() or event_id in used_events:
            raise ValueError("A unique event id is required")
        if not isinstance(event.get("source"), str) or not event["source"].strip():
            raise ValueError("An evidence source reference is required")
        at = _time(event["at"])
        if previous is not None and at < previous:
            raise ValueError("Cash events must be chronological; no backdating")
        kind = event["kind"]

        if kind in {"BUY", "FEE", "FX"}:
            currency = _currency(event["currency"])
            amount = _amount(event["amount"])
            if amount == 0:
                raise ValueError("A debit must be positive")
            if amount > cash.get(currency, Decimal(0)):
                raise ValueError(f"Unavailable {currency} cash for {event_id}")
        if kind == "BUY":
            lot_id = event["lot_id"]
            if not isinstance(lot_id, str) or not lot_id.strip() or lot_id in used_lots:
                raise ValueError("A unique lot id is required")
            planned = event.get("planned_exit")
            if planned is not None:
                planned_date = datetime.strptime(planned, "%Y-%m-%d").date()
                if planned_date < at.date():
                    raise ValueError("Planned exit precedes entry")
            cash[currency] -= amount
            lots[lot_id] = {"cost": amount, "currency": currency, "planned_exit": planned}
            used_lots.add(lot_id)
        elif kind == "EXIT":
            lot_id, receivable_id = event["lot_id"], event["receivable_id"]
            if lot_id not in lots:
                raise ValueError("Exit requires an open lot")
            if not isinstance(receivable_id, str) or not receivable_id.strip() or receivable_id in used_receivables:
                raise ValueError("A unique receivable id is required")
            currency, amount = _currency(event["currency"]), _amount(event["amount"])
            receivables[receivable_id] = {"amount": amount, "currency": currency, "lot_id": lot_id}
            used_receivables.add(receivable_id)
            del lots[lot_id]
        elif kind == "RECEIVE":
            receivable_id = event["receivable_id"]
            if receivable_id not in receivables:
                raise ValueError("Receipt requires an outstanding receivable")
            claim = receivables.pop(receivable_id)
            currency, amount = claim["currency"], claim["amount"]
            cash[currency] = cash.get(currency, Decimal(0)) + amount
        elif kind == "FX":
            other = _currency(event["receive_currency"])
            received = _amount(event["receive_amount"])
            if other == currency or received == 0:
                raise ValueError("FX needs two currencies and positive explicit amounts")
            cash[currency] -= amount
            cash[other] = cash.get(other, Decimal(0)) + received
        elif kind == "FEE":
            cash[currency] -= amount
        else:
            raise ValueError(f"Unsupported cash event {kind}")

        used_events.add(event_id)
        previous = at
        journal.append({
            "id": event_id, "at": at.isoformat(), "kind": kind,
            "source": event["source"],
            "available_cash": {k: str(v) for k, v in sorted(cash.items())},
            "open_lots": {k: {**v, "cost": str(v["cost"])} for k, v in sorted(lots.items())},
            "overdue_open_lots": sorted(k for k, v in lots.items() if v["planned_exit"] and v["planned_exit"] <= at.date().isoformat()),
            "receivables": {k: {**v, "amount": str(v["amount"])} for k, v in sorted(receivables.items())},
        })
    return {"status": "ACCOUNTING_ONLY_NO_NAV_OR_EXECUTION_APPROVAL", "journal": journal,
            "open_lot_count": len(lots), "unreceived_claim_count": len(receivables)}


if __name__ == "__main__":
    import argparse
    import hashlib
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.input.resolve() == args.output.resolve():
        parser.error("Input and output must be different files")
    raw = args.input.read_bytes()
    payload = json.loads(raw)
    try:
        result = replay_cash_availability(payload["initial_cash"], payload["events"])
        failed = False
    except (ValueError, KeyError, TypeError) as error:
        result = {"status": "BLOCKED_CASH_FLOW_AUDIT", "error": str(error)}
        failed = True
    result["input_sha256"] = hashlib.sha256(raw).hexdigest()
    result["historical_execution_approved"] = False
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    raise SystemExit(1 if failed else 0)
