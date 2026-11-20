# Data model and large data volumes (LDV)

**Verdict:** model for the volume you'll have in 3 years, not today: standard objects first, keep children per parent and records per owner under 10,000, design selective queries from day one, and decide archiving before the object is big. Archiving strategy is a human decision when LDV applies (ARCH-005).
Confidence: thresholds [verified from Salesforce docs/Trailhead, 2026-11] — Salesforce notes they can change; design rules [high].

## Design rules
| # | Rule | Why |
|---|---|---|
| 1 | Standard object first; custom only when no standard object fits | standard features, reports, packages work out of the box |
| 2 | Master-detail when the child can't exist alone and should inherit sharing/roll-ups; lookup otherwise | wrong choice is expensive to change |
| 3 | Record types for variants of the same thing; separate objects for different things | avoids "god objects" |
| 4 | External ID (unique) on every object fed by an integration | idempotent upserts; also gives a custom index |
| 5 | Every new object/field states expected volume in 3 years (ticket `metadata` + DAT-02) | LDV is designed in, not fixed later |

## Skew (avoid > 10,000)
| Type | What | Mitigation |
|---|---|---|
| Account / parent-child skew | > 10,000 children under one parent | spread over more parents; avoid "Unassigned" parents |
| Lookup skew | huge number of records pointing to one lookup record | review heavy concurrent insert/update objects; spread or remove lookup |
| Ownership skew | one user owns > 10,000 records of an object | spread owners; if unavoidable, the owner has **no role** (keeps sharing recalculation out of the role hierarchy) |
Symptoms: `UNABLE_TO_LOCK_ROW`, slow ownership changes, long sharing recalculations.

## Selective queries
- Standard index used when the filter matches < 30% of the first million records and < 15% beyond (cap 1M).
- Custom index (incl. Unique / External ID fields) used when < 10% of the first million and < 5% beyond (cap 333,333).
- Non-selective queries in triggers fail on objects with more than 1 million records → every SOQL in a trigger path must be selective.
- Check with the Query Plan tool; filter with `=`/`IN`; avoid leading-wildcard `LIKE`, `!=`, nulls on unindexed fields; empty the recycle bin effect into account.
- Custom indexes on other fields and skinny tables: request via Salesforce Support.

## Volume tactics
Bulk API 2.0 for loads above ~2,000 records · defer sharing calculations for big loads [med] · data tiering (keep hot data, move cold data) · Big Objects or external archive for history · External Objects (Salesforce Connect) when data should stay in its source.

## Options (ARCH-005 archiving — only when an object is expected to exceed ~1M records)
| | A. Delete with retention policy | B. Big Objects | C. External archive (data warehouse / archive product) | D. External Objects (data stays in source) |
|---|---|---|---|---|
| Keeps history in SF | no | yes, limited querying | no (linked) | read live |
| Effort | low | medium (async SOQL, custom UI) | medium–high | medium |
| Signals | no legal need to keep | must stay in SF platform | analytics / compliance elsewhere | source system remains master |

## Sources
Trailhead "Large Data Volumes — Design Your Data Model"; Salesforce Large Data Volumes best practices (indexes); Query Plan Tool FAQ (Salesforce Help); Salesforce Developers blog on data skew.
