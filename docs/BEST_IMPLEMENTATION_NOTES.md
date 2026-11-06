# BEST v1 implementation and validation notes

The preregistered numeric score, absolute eligibility, strong pool and all risk
caps remain unchanged. No historical outcome fitting has been performed.

2026-11-06: First real inventory inspected 5,311 dated reference records; 1,724
complete liquid unique issuers and 191 strong candidates. Formation blocked
because provider ticker metadata returned SIC 0000 for TBBB. The strong name was
not dropped or replaced to force a ten-stock result. Added a data repair using
the same authenticated provider's original SEC filing *filer reference metadata*,
limited to filings dated on/before the signal and matching the exact issuer CIK.
No fundamental ranking or inferred industry is introduced. Missing or future-only
classification still blocks formation. Both reference and filing evidence are
hashed and cached. The earlier blocked runs are validation receipts, not trades.

Inventory batches are complete-universe checkpoints, not a top-N filter. Every
reference symbol must appear once as evaluated or excluded, with a reason. Changed
source, universe, or protocol fingerprints invalidate old checkpoints. Recovery
caches are encrypted using the existing protected market-data credential and
saved even on collection failure. No credential value is serialized or logged.

The BEST-only data adapter now uses the current New York session only after
16:15 local time. Before that it requests prior completed dates; the observed
SPY calendar handles holidays/weekends. This fixes the legacy adapter's UTC
yesterday lag without altering any legacy code or frozen BEST score parameters.
Reference requests retry only transient 429/502/503/504 responses; permissions
errors remain explicit and never trigger a different investment universe.

The vendor's foreign-filer coverage did not resolve TBBB. The existing primary
SEC client is therefore reused for classification reference evidence. A current
SEC reference is admissible only if its archived observation is on/before the
signal date in New York; otherwise only an original filing header dated by the
signal is admissible. Exact CIK and SIC, observation time, source URL and content
hash are preserved. Future-only classification is rejected, and the candidate
is never silently dropped. This repairs missing metadata, not model parameters.

PR approval now explicitly requires the independently audited full inventory,
ten common-stock members, funded integer orders and an independently reconciled
BEST state. A gracefully reported data block is not a green release gate. Daily
production still publishes honest failure status without erasing prior history.

The same provider's dated financial filing reference may also supply SIC when
ticker-reference and SEC-filing-index metadata omit foreign issuers. Only CIK,
SIC, filing date, source URL and receipt hash are consumed; earnings/fundamental
values are not ranking inputs. Source failures are recorded by ticker and
redacted status code. Primary SEC requests are serialized under its rate limit.

Product release readiness is distinct from execution: a funded, reconciled cash
account with ten audited precommitted whole-share buys can be published as
PAPER_EXPERIMENT before the next market opening. It remains paper_started=false,
fully_invested=false and shows zero executed positions until real opening quotes
are recorded. An actual-ten-holdings flag cannot be inferred from a plan.
