# Calima Canarias

Analysis of Saharan dust (calima) episodes in the Canary Islands: recent evolution, how
accurate the forecasts were, and what the episodes affect (health, aviation). See
[`CLAUDE.md`](CLAUDE.md) for the full project scope, and [`docs/decisions.md`](docs/decisions.md)
for the architecture decisions behind what is built so far.

## Why this exists

Existing tools already cover parts of this: [Apalmet](https://www.apalmet.es/) (CAMS
forecast maps), AEMET / the WMO Barcelona Dust Regional Center (dust forecasts), the
Gobierno de Canarias air quality network (real-time data and a health index), and
[aqicn.org](https://aqicn.org/) (real-time air quality index).

None of them offer:

1. **A historical episode catalogue** — how many calima days per year and how intense,
   by island and by station, since 2013.
2. **Forecast verification** — CAMS predicted X, the stations measured Y. Bias and hit
   rate by lead time (24h / 48h / 72h), tracked per year so model upgrades show up.
3. **Impact and clarity** — episodes compared against airport visibility, with health
   guidance in one clear, mobile-friendly view (ES / EN / DE).

## About the data: what 13 years can and can't tell us

Station data in this project starts in **2013**, because that is where the EEA's
*verified* air quality dataset for the Canary Islands begins — it is not an arbitrary
cutoff, it is where the authoritative source itself starts.

13 years is enough to describe the **recent evolution** of calima episodes — how many
per year, how intense, whether forecasts are improving. It is **not** enough, on its
own, to attribute a trend to climate change: climate studies normally need 30+ years of
record to separate a climate signal from natural year-to-year variability. For that
larger question, this project defers to published research rather than drawing its own
conclusion from a 13-year window, e.g.:

> Vasilakos, P. N., Upadhyay, A., Manousakas, M. I. et al. "Rising dust pollution across
> Europe in a changing climate." *Nature* **655**, 647–654 (2026).
> https://doi.org/10.1038/s41586-026-10743-w

That study documents a rise in desert dust intensity and frequency at monitored European
sites over the past decade, with the authors noting climate-driven desertification of the
Sahara as a likely (not definitively proven) contributor — the kind of claim a single
13-year regional series cannot support by itself, but a dedicated, longer-running,
continent-scale study can start to.

## Data sources and attribution

| Source | Used for | Licence / required attribution |
|---|---|---|
| [EEA Air Quality Download Service](https://eeadmz1-downloads-api-appservice.azurewebsites.net/swagger/index.html) | Hourly PM10 per station, 2013–now | CC BY 4.0 — "Air quality data: European Environment Agency (EEA), CC BY 4.0", with a link to the download service |
| [MITECO station layer](https://gis.miteco.gob.es/descargas/app/DescargaFichero?f=estaciones.zip) | Station coordinates (49 of 56 stations) | Spanish Law 37/2007 — "Origen de los datos: Ministerio para la Transición Ecológica y el Reto Demográfico (MITECO)", with the date of the last update |
| [Copernicus Atmosphere Monitoring Service (CAMS)](https://atmosphere.copernicus.eu/) | Global atmospheric composition forecasts (PM10, dust AOD), 2015–now | CC BY — "Contains modified Copernicus Atmosphere Monitoring Service information [year]. Neither the European Commission nor ECMWF is responsible for any use that may be made of the Copernicus information or data it contains." |
| Gobierno de Canarias air quality network | Real-time data and health index for the "Now" page | Gobierno de Canarias |
| [ArcGIS Maps SDK for JavaScript](https://developers.arcgis.com/) | Map rendering (basemap + station layer) | Powered by Esri |
| MITECO/CSIC "Episodios naturales de partículas" annual reports | `official_episodes`, to validate our own detection against the published record | Ministerio para la Transición Ecológica |

See [`docs/data-sources.md`](docs/data-sources.md) for the full access notes, gotchas and
licence text behind each row above.

> This README is a work in progress — Phase 2/3 data sources (METAR, ocean colour, a
> second dust model) will be added here once they are actually ingested, not before.

## Project layout

```
backend/        FastAPI app, models, ingestion commands, analysis (see backend/README.md)
frontend/       Angular app
geoserver/      GeoServer config (workspaces, layers, styles)
docs/           data-sources.md, decisions.md (short ADRs)
docker-compose.yml
```

## Database schema

One row per station (`stations`), with three tables hanging off it by `station_code`:
hourly measurements, CAMS forecasts, and the episodes we detect. `official_episodes` is
unrelated at the database level — it is the MITECO/CSIC published record, used to check
our own detection by eye, not joined against it (see `docs/decisions.md`).

```mermaid
erDiagram
    STATIONS ||--o{ MEASUREMENTS : "measured at"
    STATIONS ||--o{ CAMS_FORECASTS : "forecast at"
    STATIONS ||--o{ EPISODES : "peaked at"

    STATIONS {
        string station_code PK
        string eea_code
        string name
        string island
        float altitude_m
        string station_type
        string station_area
        geometry location
    }
    MEASUREMENTS {
        string station_code PK_FK
        datetime start_utc PK
        float value
        int validity
        string dataset
    }
    CAMS_FORECASTS {
        string station_code PK_FK
        datetime run_time PK
        int lead_time_hours PK
        datetime valid_time
        float pm10_forecast_ugm3
        float dust_aod_550
    }
    EPISODES {
        int id PK
        date start_date
        date end_date
        float peak_value
        string peak_station_code FK
        string definition_version
        string data_status
    }
    OFFICIAL_EPISODES {
        int id PK
        string region
        string dust_type
        date start_date
        date end_date
        string source_report
    }
```

GitHub renders this diagram automatically wherever this file is viewed on github.com.
