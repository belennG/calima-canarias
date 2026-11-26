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

## 2026-11-26 — Enums for closed-set columns, and a new `stations.station_area`

**Decision:** map `island`, `station_type`, `dataset`, `data_status` and `dust_type` to
Python `Enum` classes (SQLAlchemy creates a native Postgres `ENUM` type for each), instead
of plain strings. The database itself then rejects any value outside the closed set,
instead of relying on application code to behave.

Checked the real values first, in `data/raw/canarias_pm10_samplingpoints.csv` (the EEA
sampling-point metadata for Canarias, 60 rows): `AirQualityStationType` is one of
`industrial` / `traffic` / `background`, but 4 of the 60 rows have none recorded — so
`stations.station_type` stays **nullable**.

**Added `stations.station_area`** (EEA's `AirQualityStationArea`: `urban` / `suburban` /
`rural-regional` / `rural-nearcity`), not originally planned. Every one of the 60 rows has
it (no nulls), and it matters for the project's own analysis: a `rural-regional` station is
more representative of a large-scale Saharan dust event than an `urban`/`traffic` one,
which picks up more local pollution. `station_type` alone does not capture that.

**Left as plain strings, deliberately:** `region` (always `"CANARIAS"` for the MVP — an
Enum for a column we only ever write one value to would be designing for scope we are not
building yet), `definition_version` (meant to grow every time the detection rule changes;
an Enum would force a migration on every change) and `source_report` (a new value every
year, e.g. `episodiosnaturales2021`).

## 2026-11-26 — `measurements.validity`, and why `value` is nullable

**Found while checking real data before running Alembic:** the EEA parquet files carry
their own `Validity` code per row (1 = valid, -1 seen so far = not valid). When
`Validity = -1`, `Value` is not a real reading — it is the sentinel `-999`. Checked 15
files (853k rows): ~5.3% of rows are this sentinel. Loading `-999` as a real µg/m³ value
would silently poison any mean or episode threshold.

**Decision:** add `measurements.validity` (the raw EEA code, kept as-is — same reasoning
as `dataset`: never lose the source's own provenance), and make `value` nullable. The
ingestion code converts the `-999` sentinel to `NULL` before inserting, instead of storing
it as a number. `validity` is NOT an Enum: the EEA's documented code list has more values
than we have evidence for in our own data so far (we have only seen `1` and `-1`); storing
the raw int keeps us from blocking ingestion on a code we have not catalogued yet.

**Out of scope for the schema:** detecting a *saturated* sensor (a valid-but-implausible
reading, e.g. pegged at the sensor's ceiling for hours) is not something the `Validity`
code captures — EEA considers it a valid reading. That is application logic (part of
episode detection), not a column we can add here.

**Also checked, no change:** CAMS's own GRIB missing-value sentinel
(`3.4028234663852886e+38`, the float32 max) is an ingestion-time check, not a schema
concern — `cams_forecasts` has no per-row validity code to preserve, there is nothing to
store besides the already-clean value.

## Episode definition v1

A day where the daily mean PM10 is above the threshold at N or more stations on the
same island (see `CLAUDE.md`, Domain notes). The exact threshold and N are set when the
detection logic is written, not fixed here. Versioned via `episodes.definition_version`
so a later change to the rule does not silently rewrite history.
