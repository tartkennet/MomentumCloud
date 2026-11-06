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
