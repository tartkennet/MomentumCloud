#!/usr/bin/env python3
"""Revalue a separate Nov 9 hypothetical paper scenario. NEVER modify observed paper ledgers."""
import datetime as dt
import json
import os
import pathlib
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

FILE=pathlib.Path("public/data/best-v2-paper-start.json")
NY=ZoneInfo("America/New_York")


def fetch_daily(ticker, start, end, key):
    base=f"https://api.massive.com/v2/aggs/ticker/{urllib.parse.quote(ticker)}/range/1/day/{start}/{end}"
    url=base+"?"+urllib.parse.urlencode({"adjusted":"false","sort":"asc","limit":"50000","apiKey":key})
    request=urllib.request.Request(url,headers={"User-Agent":"MomentumCloud-paper-reconstruction/1.0"})
    with urllib.request.urlopen(request,timeout=25) as response:
        payload=json.load(response)
    if payload.get("status") not in ("OK","DELAYED") or not payload.get("results"):
        raise ValueError("MISSING_CONFIRMED_DAILY_BAR_"+ticker)
    bars=[]
    for bar in payload["results"]:
        if bar.get("c") and bar.get("t"):
            day=dt.datetime.fromtimestamp(bar["t"]/1000,NY).date().isoformat()
            if start<=day<=end:
                bars.append((day,float(bar["c"])))
    if not bars:
        raise ValueError("NO_DATED_CLOSE_"+ticker)
    return bars[-1]


def main():
    key=os.environ.get("POLYGON_API_KEY")
    if not key:
        raise ValueError("MISSING_PROVIDER_CREDENTIAL")
    data=json.loads(FILE.read_text())
    assert data["kind"]=="HYPOTHETICAL_PAPER_RECONSTRUCTION"
    assert data["trade_day"]=="2026-11-09" and data["initial_sek"]==25000
    holdings=data["holdings"]
    assert len(holdings)==10 and len({p["ticker"] for p in holdings})==10
    today=dt.datetime.now(dt.timezone.utc).astimezone(NY).date().isoformat()
    if today<data["trade_day"]:
        return
    marks={h["ticker"]:fetch_daily(h["ticker"],data["trade_day"],today,key) for h in holdings}
    dates={date for date,_ in marks.values()}
    if len(dates)!=1:
        raise ValueError("INCONSISTENT_SESSION_DATES")
    day=next(iter(dates))
    prior=data.get("mark_date","2026-11-09")
    if day<prior:
        raise ValueError("NONMONOTONIC_MARK_DATE")
    if day==prior:
        print("UNCHANGED_MARK_SESSION",day)
        return
    for h in holdings:
        h["mark_usd"]=marks[h["ticker"]][1]
    data["mark_date"]=day
    data["mark_observed_at"]=dt.datetime.now(dt.timezone.utc).isoformat()
    data["mark_source"]="Massive unadjusted completed daily bar, after regular session"
    FILE.write_text(json.dumps(data,indent=2,ensure_ascii=False)+"\n")
    print("PAPER_RECONSTRUCTION_MARK_UPDATED",day,"positions",len(holdings))


if __name__=="__main__":
    main()
