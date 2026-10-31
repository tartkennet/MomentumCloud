# Quality & Earnings — data audit before strategy outcomes

Issue #35. Separate from frozen H3 and completed Momentum10 v1–v3.

Economic evidence: Chan/Jegadeesh/Lakonishok, Momentum Strategies (1995/1996)
find earnings news and price momentum contain distinct predictive information:
https://www.nber.org/papers/w5375
Novy-Marx's profitability study motivates profitable underlying businesses:
https://www.nber.org/papers/w15940
These historical cross-sectional findings are motivation, NOT proof for a
long-only ten-stock SEK20,000 retail portfolio or the coming implementation.
Accounting growth is not an earnings surprise without expectations data.

Saved inputs: authenticated 1001-file raw-price/PIT-universe/split/dividend
archive through 2026-10-28; original dated ECB FX; independent whole-share,
corporate-event, cash/claims and cost infrastructure. No archived as-filed
quarterly fundamentals or analyst-revision vintages were found in the repo.
Previously reviewed history is development data, never new untouched OOS.

Connected Massive probe: income statement and Benzinga earnings endpoints
return NOT_ENTITLED. App key permissions are separately probed in Actions,
without exposing the key. No new subscription. The legacy financial endpoint
was retired; the current three statement endpoints keep most recently filed
comparatives and currently active companies. Current EPS/share counts can
reflect later splits; merely joining old period ends/original filing dates
is not a valid as-reported panel. Do not substitute this for original filings.
https://massive.com/knowledge-base/article/does-massive-provide-the-filing-date-for-any-financial-reports
https://massive.com/knowledge-base/article/what-fields-can-i-expect-from-massives-financials-api

Free PRIMARY alternative: SEC submissions acceptance metadata and companyfacts
with accession numbers, filing dates, period bounds and units. Facts require
explicit standard-taxonomy selection, same-period checks, acceptance join,
amendment handling and unambiguous durations; missing/custom tags are not zero.
SEC frames choose last-filed observations and are not a vintage database.
No historical strategy return will be reported without verified as-filed
coverage, including delisted issuers and an independently audited timestamp
join. Current-only primary snapshots can instead seed future-only collection.
https://www.sec.gov/search-filings/edgar-application-programming-interfaces

The initial AAPL/MSFT requests test the data transport/parser only; they do
not define an investable universe or become a handpicked backtest sample.
Analyst revisions are EXCLUDED unless reliable original observation vintages
are available. No realised EPS substituted for prior analyst expectations.
