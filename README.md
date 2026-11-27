# Calima Canarias

Analysis of Saharan dust (calima) episodes in the Canary Islands: recent evolution, how
accurate the forecasts were, and what the episodes affect (health, aviation). See
[`CLAUDE.md`](CLAUDE.md) for the full project scope, and [`docs/decisions.md`](docs/decisions.md)
for the architecture decisions behind what is built so far.

> This README is a work in progress. The full "why this exists", data source attribution
> and the honest framing about the 2013+ dataset still need to be written up here.

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
