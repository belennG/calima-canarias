# Calima Canarias

Analysis of Saharan dust (calima) episodes in the Canary Islands: recent evolution,
how accurate the forecasts were, and what the episodes affect (health, aviation).

This is a portfolio project. The audience is engineering teams at Earth-observation,
GIS, health-tech, oceanographic and aviation companies. Code quality, data quality and
clear reasoning matter more than the number of features.

## Why this exists (what other tools don't do)

Existing tools: Apalmet (CAMS forecast maps), AEMET / WMO Barcelona Dust Regional Center
(dust forecasts), the Gobierno de Canarias air quality network (real-time data and
health index), aqicn.org (real-time AQI).

None of them offer:
1. **Historical episode catalogue**: how many calima days per year and how intense,
   by island and station, since 2013.
2. **Forecast verification**: CAMS predicted X, the stations measured Y. Bias and
   hit rate by lead time (24/48/72 h).
3. **Impact and clarity**: episodes compared with airport visibility, and health guidance
   in one clear, accessible, mobile-friendly view (ES / EN / DE).

## Scope

### Phase 1: MVP (target: ~2 weeks)
- [ ] Ingest hourly PM10 from EEA (Canary Islands stations, 2013 to now) into PostGIS
- [ ] Ingest CAMS global forecasts (surface PM10, dust AOD) and extract them at the
      station locations
- [ ] Episode detection (versioned, tested) and an episode catalogue
- [ ] Forecast verification metrics
- [ ] GeoServer publishing stations and episodes as OGC services (WMS / WFS)
- [ ] Frontend pages: Now, History, Episode detail (case study: Feb 2020),
      Forecast accuracy, Methodology
- [ ] Docker Compose, GitHub Actions (lint + tests + build), deployed with a public URL

### Phase 2
- Airport visibility from METAR, correlated with PM10
- Satellite imagery layer for episode pages (NASA GIBS / Worldview true colour)
- Daily bulletin written by an LLM in ES / EN / DE, with an automated check that every
  number in the text matches the data (eval)
- Alerts: subscription by **email** and **Telegram bot** (user picks island/municipality,
  language, threshold), plus a public **Telegram channel** with the daily bulletin.
  Email needs double opt-in, an unsubscribe link and minimal stored data (GDPR).
  Every message says it is not an official warning and links to AEMET / Gobierno de Canarias.

### Phase 3
- Ocean chlorophyll (Copernicus Marine ocean colour) before vs after big episodes,
  compared against the seasonal climatology. Open scientific question around the islands.
- Optional second dust model (MONARCH, WMO Barcelona Dust Regional Center) if its
  archive is accessible.

## Data sources (verify each in the first spike)

| Source | What | Access | Notes |
|---|---|---|---|
| EEA Air Quality Download Service | Hourly PM10 per station, verified data 2013 to now | API, Parquet | Python lib `airbase` may help. Filter Canary Islands stations by coordinates. |
| CAMS global atmospheric composition forecasts | 5-day forecasts, 00 and 12 UTC runs, 0.4° grid (~40 km), 2015 to now | Atmosphere Data Store (ADS), `cdsapi` | Free ADS account; key in `.env`. |
| CAMS reanalysis (EAC4) | Consistent model history since 2003 | ADS | Optional context for longer trends. |
| Gobierno de Canarias air quality network | Real-time data, ICA health index | Website + data download | For the "Now" page and health messages. |
| METAR (phase 2) | Airport visibility, weather codes (DU, HZ...) | e.g. Iowa Environmental Mesonet archive | GCXO, GCTS, GCLP, GCRR, GCFV, GCLA, GCHI, GCGM. |
| WMO Barcelona Dust Regional Center (phase 3) | MONARCH dust forecasts | THREDDS | Archive access may be limited to met services. Check before planning on it. |

### CAMS: decisions and gotchas
- The CAMS **European regional** product (0.1°) covers 25°W–45°E, 30°N–72°N.
  The Canary Islands (~27.6–29.4°N) are **outside** it, so we use the **global** product.
- 0.4° is coarse for small islands: one grid cell can cover a whole island plus sea,
  and the Teide orography is not resolved. Interpolate to station coordinates
  (nearest / bilinear, decide and document) and expect biases. Explaining this is
  part of the result, not a bug.
- Download only what we need: bbox around the islands (approx. 27–30°N, 19–13°W),
  surface PM10 and dust AOD 550 nm, 00 UTC run, lead times 0–72 h. Download month by
  month in a background job; ADS requests are queued and can be slow.
- CAMS upgrades its model about once a year. Report verification per year so we can
  see whether forecasts improved.
- Time windows: **trends from 2013** (stations), **forecast verification from 2015** (CAMS).

## Domain notes

- PM10 = particles < 10 µm, measured by ground stations. Satellites measure AOD
  (light blocked by particles in the whole air column), not ground-level PM10.
- PM10 reference values: EU daily limit 50 µg/m³; WHO 2021 daily guideline 45 µg/m³.
- During extreme episodes PM10 analysers can **saturate** for hours. Flag saturated,
  missing and suspicious values instead of showing them as real numbers.
- An "episode" is a definition we choose: make it explicit, configurable and versioned.
  First version: a day where the daily mean PM10 is above the threshold at N or more
  stations on the same island. Refine later (e.g. use CAMS dust fraction to separate
  dust from local pollution). Document every change in `docs/decisions.md`.
- Verification metrics: bias, MAE, and for "PM10 > 50" events: probability of detection
  (POD) and false alarm ratio (FAR), by lead time and by year.

## README must say (honest framing)
- Station data starts in 2013 because that is where the EEA verified dataset starts.
- 13 years describes the **recent evolution**; it is too short to attribute a trend to
  climate change on its own (climate studies usually use 30+ years). For attribution,
  reference published studies (e.g. the 2026 Nature / CSIC study on Saharan dust).
- What existing tools do, and what this project adds.
- Data sources with attribution (Copernicus / CAMS, EEA, Esri, etc.).

## Architecture

- **Backend:** Python 3.12, FastAPI, SQLAlchemy + Alembic, PostgreSQL 16 + PostGIS
- **Ingestion:** CLI commands (Typer), run on a schedule. They must be **idempotent**
  (running twice does not duplicate data) and retry on network errors.
- **Analysis:** pandas / xarray for CAMS NetCDF and GRIB files
- **GIS:** GeoServer publishing PostGIS tables as OGC WMS / WFS
- **Frontend:** Angular (latest, standalone components, signals), TypeScript,
  **ArcGIS Maps SDK for JavaScript** for maps (consuming our GeoServer / GeoJSON layers),
  Vega-Lite for charts, i18n ES / EN / DE
- **Infra:** Docker Compose (db, api, geoserver, frontend), GitHub Actions (ruff, pytest,
  frontend lint/test/build, deploy), `/health` endpoint

```
backend/        FastAPI app, models, ingestion commands, analysis
frontend/       Angular app
geoserver/      GeoServer config (workspaces, layers, styles)
docs/           data-sources.md, decisions.md (short ADRs), screenshots
docker-compose.yml
```

### Secrets and keys
- Backend secrets (ADS key, DB password) only in `.env` (in `.gitignore`), with a
  `.env.example`.
- The ArcGIS API key ends up in the browser, so it is public by nature: restrict it by
  referrer (our domain + localhost) and set usage limits in the ArcGIS Location Platform
  dashboard. Include the required Esri attribution.

## How to work with me (María)

I'm a frontend developer (Vue, TypeScript) moving into full stack. I'm learning backend,
SQL, GIS and DevOps through this project, so:

- **Plan before code.** For anything non-trivial, propose a short plan and wait for my OK.
- **Explain decisions.** When you choose a library, pattern or schema, tell me why and
  what the alternative was. Add the important ones to `docs/decisions.md`.
- **I write some parts myself first:** SQL queries, the episode-detection logic and the
  verification metrics. Review my version and tell me what you would change and why.
  Don't just replace it.
- **Team workflow:** one branch per feature, a pull request with a description, CI green
  before merge. Small commits with clear messages.
- **Tests** for every piece of logic (parsers, episode detection, metrics).
- **No new dependencies without asking.**
- When something fails, show me how to debug it (logs, queries) before fixing it.
- When you get something wrong and we catch it, add a line to `docs/ai-workflow.md`
  (what happened, how we caught it).
- Code, comments and docs in **English**.