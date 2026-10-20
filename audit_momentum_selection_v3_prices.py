"""Inventory available individual-price references without concealing gaps."""
import csv
from datetime import datetime, timezone
import io
import json
import math
from pathlib import Path

OUT = Path("audit_evidence/selection_v3_20261020")


def day_of(value):
    return datetime.fromtimestamp(float(value)/1000, timezone.utc).date().isoformat()


def main():
    refs = json.loads(Path("evidence/selection/selection_reference_histories.json").read_text())
    refs.update(json.loads(Path("classification/verified_ticker_histories.json").read_text()))
    for path in Path("universe_evidence").glob("histories_*.json"):
        for ticker, bases in json.loads(path.read_text()).items():
            refs[ticker] = {"adjusted": {day_of(row["t"]): {"open":row["o"],"close":row["c"]}
                                         for row in bases["true"].get("results", [])}}
    records = json.loads(Path("audit_evidence/robust_top20_source_batch_20261019.json").read_text())["records"]
    windows = [(row["request"]["ticker"], row["request"]["params"]["adjusted"], row["response_csv"]) for row in records]
    for name in ("execution_original_responses.json", "last_window_original_responses.json"):
        windows += [(row["ticker"],row["adjusted"],row["response"]) for row in json.loads((OUT/name).read_text())]
    for ticker, adjusted, text in windows:
        if adjusted != "true" or not text.startswith("v,"):
            continue
        target = refs.setdefault(ticker, {}).setdefault("adjusted", {})
        for row in csv.DictReader(io.StringIO(text)):
            target[day_of(row["t"])] = {"open":float(row["o"]),"close":float(row["c"])}
    comparison = json.loads((OUT/"comparison.json").read_text())
    summaries, missing, mismatches = {}, [], []
    for name in comparison["models"]:
        with (OUT/(name+"_positions.csv")).open() as file:
            positions = list(csv.DictReader(file))
        checked, unavailable, actions = 0, 0, 0
        for p in positions:
            observations = [(p["SignalDate"],"close","SignalPrice_USD"),
                            (p["EntryDate"],"open","EntryPrice_USD")]
            if p["CorporateAction"]:
                actions += 1
            else:
                observations.append((p["ExitDate"],"open","ExitPrice_USD"))
            for day, field, key in observations:
                row = refs.get(p["Ticker"],{}).get("adjusted",{}).get(day)
                if row is None:
                    unavailable += 1
                    missing.append({"variant":name,"signal":p["SignalDate"],"ticker":p["Ticker"],"day":day,"field":key})
                elif math.isclose(float(row[field]),float(p[key]),rel_tol=1e-6,abs_tol=1e-8):
                    checked += 1
                else:
                    mismatches.append({"variant":name,"signal":p["SignalDate"],"ticker":p["Ticker"],
                                       "day":day,"field":key,"model":float(p[key]),"reference":float(row[field])})
        summaries[name] = {"matched_point_checks":checked,"missing_point_checks":unavailable,
                            "corporate_action_exits_requiring_unit_converter":actions}
    result = {"status":"PASS_AVAILABLE_PRICE_REFERENCES_INCOMPLETE_COVERAGE" if not mismatches else "FAILED_REFERENCE_MISMATCH",
              "summaries":summaries,"mismatches":mismatches,"remaining":missing,
              "limitation":"Same-vendor individual endpoints. This does not validate fresh closes on stale-mark days, every issuer identity, or actual fills."}
    (OUT/"price_reference_audit.json").write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!="remaining"},indent=2))
    if mismatches:
        raise AssertionError("Selected individual quote mismatch")


if __name__ == "__main__":
    main()
