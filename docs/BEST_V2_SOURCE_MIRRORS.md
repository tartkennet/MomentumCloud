# Required-original source policy

No source, event or selection control is waived. A public alternate copy of a
required SEC original is admissible only after matching CIK, accession, form,
public filing date and complete material content against the primary SEC index
and readable original. Pin the downloaded copy's SHA-256; do not claim its bytes
are identical to SEC's rendering. Verify all indexed material exhibits/items,
company, signature and document markers. Unknown, changed or incomplete copies
remain blocked. Availability must precede the actual prospective decision.

The registry in data/filing_mirrors.json records two verified sources:
- SharkNinja 6-K 0001628280-25-049846, filed 2025-11-06: official issuer IR/Q4
  complete PDF, 71 pages, cover and exhibits 99.1–99.4. Actions verifies identity,
  full extraction, all markers and pinned hash. Source gate now clears SN.
- Stagwell 8-K/A 0001104659-26-120692, filed 2026-10-30: public Yahoo original
  HTML copy. Primary SEC index lists one narrative file and Item 5.02, no
  material exhibits. Complete original text concerns Beth J. Kaplan's committee
  appointment, with signature and dates. Provider parsed 8-K endpoint omits this
  amendment even when 8-K/A is explicitly requested; the full original copy is
  therefore checked rather than treating the missing document as empty.

Direct SEC retrieval in Actions returns 403; existing authenticated provider
original paths for these documents return 404. The web reader can inspect the
primary originals/indexes; it grants no authenticated Actions access. Public
mirrors use a separate request and never receive the market-data API key.

Cached original documents and extraction/identity receipts remain in encrypted
Actions inputs. No credential or raw provider document is committed to source.
The same policy applies to every issuer; this is not an eligibility exception.

BBB Foods extends the same registry policy: twelve 6-Ks, nineteen complete
narrative/exhibit originals matched to primary SEC index tables; plus the latest
20-F and subsequent 20-F/A with all eleven narrative/certification documents.
All thirty downloads returned 200 and pinned fingerprints in source probe
42358749529. The legacy financial service returned zero TBBB records. The
annual baseline is therefore required from the separate complete SEC index,
including the amendment, rather than declaring missing annual coverage CLEAR.
Bundles require exact required-file lists and verify every individual hash;
a missing/changed exhibit fails both unit regression and prospective formation.
