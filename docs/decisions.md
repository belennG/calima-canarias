# Decisions

Short architecture decision records (ADRs) for `calima-canarias`: one entry per
non-trivial decision, with the date, why we chose it, and the alternative we did not
pick. Decisions made during the data spike itself are already recorded in
`docs/data-sources.md` (section 5) and are not repeated here; this file covers
decisions from the MVP build onward.

## 2026-11-26 — Core tables: `stations`, `measurements`, `episodes`

**Decision:** three base tables, plus a materialized view for daily means (not a base
table — it is recalculated after every load, never written to directly).

- **`stations`** — one row per monitoring station. Primary key `station_code` (the
  8-digit national code). Columns: `eea_code`, `name`, `island`, `altitude_m`,
  `station_type`, `location` (PostGIS point).
- **`measurements`** — one row per station per hour. Composite primary key
  `(station_code, start_utc)`. Columns: `value` (µg/m³), `dataset` (`verified` /
  `up_to_date`), so a row's provenance is never lost once the EEA publishes the
  verified replacement for a period.
- **`episodes`** — one row per calima episode *we* detect. Columns: `id`
  (autoincrement), `start_date`, `end_date`, `peak_value`, `peak_station_code`
  (FK → `stations`), `definition_version` (which version of the detection rule produced
  this row), `data_status` (`provisional` / `confirmed`).

**Why `data_status` on `episodes`:** episodes detected from the current year's data run
on the `up_to_date` (unverified) dataset. Once the EEA publishes the verified
replacement — usually the following year — the same days must be re-detected on
`verified` data, and the result can change near the threshold. `data_status` tracks
which pass produced the row instead of silently overwriting it.

**Alternative considered for `episodes`' key:** a natural key `(island, start_date)`,
assuming only one open episode per island at a time. Rejected — not safe to assume as a
rule, and an autoincrement `id` costs nothing.

## 2026-11-26 — `official_episodes`: schema, and why it is scoped down for the MVP

**Decision:** `official_episodes` stores entries from the MITECO/CSIC "Episodios
naturales de partículas" annual reports, to validate our own detection — not a full
automated import of every available year for the MVP.

Columns: `id`, `region` (one of the report's nine zones — we only load `CANARIAS`),
`dust_type` (`african` / `biomass_burning` / `european_sulfate`), `start_date`,
`end_date`, `source_report` (e.g. `episodiosnaturales2020`).

**What we found opening the 2020 report** (`episodiosnaturales2020_tcm30-529865.pdf`,
306 pages): every monthly chapter opens with a table with one column per region and one
row per dust type; each cell holds one or more day ranges for that month. For February,
`AFRICANOS` × `CANARIAS` lists two ranges: `1-20` and `22-29`. The report's own text
singles out the 22-24 sub-period as the most intense:

> "En febrero el episodio más destacado fue el de los días 22-24, que afectó a
> Canarias, con fuertes vientos de componente este que dieron lugar a una intensa
> irrupción de polvo sahariano."

So the February 2020 episode is confirmed in the official record.

**Important caveat:** the report's `CANARIAS` column covers the whole archipelago from
a handful of regional background stations — it is not broken down per island. Our own
detection (see the episode definition below) is per island. A match against
`official_episodes` can only ever confirm "some island in Canarias had an episode that
month," not which one.

**Why scoped down:** the table layout is not consistent enough across report years to
parse reliably with a generic script — columns do not align at fixed character
positions, and a cell can hold one to three day ranges. For the MVP we hand-enter the
relevant Canarias ranges (starting with February 2020). A general PDF-table parser for
all available years (2013–2025) is a phase-2 task if we end up needing full automated
validation.

## Episode definition v1

A day where the daily mean PM10 is above the threshold at N or more stations on the
same island (see `CLAUDE.md`, Domain notes). The exact threshold and N are set when the
detection logic is written, not fixed here. Versioned via `episodes.definition_version`
so a later change to the rule does not silently rewrite history.
