# Data sources

Findings from the data spike (branch `spike/data-source`, notebooks in `spikes/`).
Last updated: 2026-11-26.

## Verdict (preliminary)

| Source | Use | Status |
|---|---|---|
| EEA air quality measurements | Hourly PM10 at stations: history (2013–2025) and "Now" (2026) | Usable |
| MITECO station layer | Station coordinates | Usable for 49 of 56 stations |
| CAMS global forecasts | PM10 and dust forecasts to verify | Access works, data check pending |

The final go/no-go comes after the CAMS check (section 3).

---

## 1. EEA air quality measurements (PM10)

### What it is

Hourly PM10 concentrations that Spain's air quality networks report to the European Environment Agency (EEA) under the Air Quality Directive. In the Canary Islands, all stations belong to a single network: `NET-ES205A`.

### Access

- Download API (Swagger): https://eeadmz1-downloads-api-appservice.azurewebsites.net/swagger/index.html
- `POST /ParquetFile/urls` returns a CSV list with one Parquet URL per file. Body we use:
  ```json
  {"countries": ["ES"], "cities": [], "pollutants": ["PM10"], "dataset": 2, "source": "API"}
  ```
  This endpoint ignores dates and has no station filter, so we filter the list on our side.
- `POST /DownloadSummary` returns the number of files and their size in MB.
- The response starts with a BOM: decode it with `utf-8-sig`.
- Station metadata: https://ereporting.blob.core.windows.net/downloadservice/metadata.csv (tab-separated, 44,523 rows × 25 columns).

### Datasets

| | Dataset 2 (E1a, verified) | Dataset 1 (E2a, up-to-date) |
|---|---|---|
| URL folder | `airquality-p-e1a` | `airquality-p` |
| Coverage we found | 2013-01-01 → 2025-12-31 | 2026-01-01 → now |
| Delay | Published once a year | Minutes |
| `Verification` flag | 1 (verified) | 3 (not verified) |
| Canary Islands | 121 files, 56 stations | 49 files, 49 stations |
| Use in the app | History, episodes, forecast verification | "Now" page |

The two datasets meet on 2026-01-01 without overlapping. When the EEA publishes the verified 2026 data, it replaces the up-to-date data, so the database must store the source dataset of every row.

The user manual says dataset 2 covers 2013–2022, but the data reaches the end of 2025.

### Coverage for the Canary Islands

- The national station code has 8 digits: province (2) + municipality (3) + station (3). Canary Islands codes start with `35` (Las Palmas) or `38` (Santa Cruz de Tenerife).
- 56 stations have verified PM10 data; 49 have up-to-date data in 2026.
- In `metadata.csv`: 60 sampling points at 52 stations. Altitude ranges from 3 to 595 m. Station types: 26 industrial, 16 background, 6 traffic and 4 without a type.
- No station measures above the marine boundary layer. The Izaña observatory (AEMET, ~2,370 m) is not in the EEA data. Candidate for phase 2 through AERONET.

### Format

- One Parquet file per sampling point and measurement method: `SP_<station_code>_10_<suffix>.parquet`.
- One row = one hour at one sampling point.
- Columns we use: `Start`, `End`, `Value`, `Unit`, `Validity`, `Verification`. Other columns: `Samplingpoint`, `Pollutant`, `AggType`, `ResultTime`, `DataCapture`, `FkObservationLog`.
- Unit: always `ug.m-3` (µg/m³) in the Canary Islands.
- Official code lists:
  - Validity: https://dd.eionet.europa.eu/vocabulary/aq/observationvalidity (−99 not valid due to maintenance or calibration, −1 not valid, 1 valid, 2 and 3 valid but below the detection limit, 4 valid, ozone only)
  - Verification: https://dd.eionet.europa.eu/vocabulary/aq/observationverification (1 verified, 2 preliminary verified, 3 not verified)

### Gotchas and how we handle them

| # | Gotcha | Evidence | How we handle it |
|---|---|---|---|
| 1 | **Survivorship bias in `metadata.csv`**: it only lists current stations | Matching URLs against `metadata.csv`: 105 files, 47 stations. Filtering by code prefix: 121 files, 56 stations | Filter URLs by the `35`/`38` prefix, not by `metadata.csv` |
| 2 | **Empty coordinates** in `metadata.csv` | `Latitude` and `Longitude` are NaN in all rows | Take coordinates from MITECO (section 2) |
| 3 | **Two files per station**, one after the other | Station `35002001`: `_47` covers 2013-01-01 → 2017-01-01 and `_A` covers 2017-01-01 → 2026-01-01 | Concatenate the files of each station |
| 4 | **`Value` is stored as `Decimal`** | dtype `object`, displayed as `16.000000000000000000` | Convert with `.astype(float)` when reading |
| 5 | **Fill value −999** | 240,096 rows (4.4%), all −999 with `Validity` −1. No other negative values, 2,145 valid zeros, no NaN | Keep only `Validity == 1`, before any calculation |
| 6 | **More invalid rows in up-to-date data** | 2026 file of `35002001`: 1,209 of 7,889 rows (15%) have `Validity` −1 | Same filter; expect more gaps on the "Now" page |
| 7 | **Timestamps without a timezone** | `datetime64[ns]` with no timezone. `metadata.csv` declares UTC+01 for all Spanish networks. At 17:18 UTC on 2026-11-25, the hour 17:00–18:00 was already published, so timestamps are ahead of UTC | Treat timestamps as UTC+01: subtract 1 hour to get UTC. To confirm with an independent source |
| 8 | **Same file names in both datasets** | `SP_35002001_10_A.parquet` exists in dataset 1 and dataset 2 | One folder per dataset. Our download skips existing files, so a shared folder would silently keep the old file |
| 9 | **Swagger placeholders** | `DownloadSummary` returned 0 files with `"cities": ["string"]` | Send a minimal body without placeholders |
| 10 | **Two sampling points measuring at the same time** | 15,165 valid hours appear twice, in 4 stations (`35004001`, `35016012`, `35024001`, `38011005`). Each station chains three files: `47` (2013–2015), `49` (2015–2024) and `A` (from 2025). In 2015, `47` and `49` overlapped for 4 to 10 months | In duplicated hours, keep the sampling point that continues afterwards (`49`). Pending: compare both in the overlap to check whether the change of equipment adds an artificial step to the series |

### Volume

- All verified PM10 for Spain: 773 files, 450 MB.
- Canary Islands: 121 files, ~70 MB, about 1.5 minutes to download. The download is I/O bound (5.8 s of CPU time).
- Reading and concatenating the 121 files takes about 3 seconds: 5,468,972 rows.
- A station with a single file has rows for ~98–99% of the hours. Valid coverage is lower (see gotcha 5).

### Licence and attribution

CC BY 4.0. Attribution: "Air quality data: European Environment Agency (EEA), CC BY 4.0", with a link to the download service.

---

## 2. Station coordinates (MITECO)

### Source

- Layer "Estaciones para la evaluación de calidad del aire 2024", from the Spanish Ministry for the Ecological Transition (MITECO). Shapefile, updated 2025-10-01:
  https://gis.miteco.gob.es/descargas/app/DescargaFichero?f=estaciones.zip
- CRS: EPSG:4326 (WGS 84, latitude and longitude in degrees), the same as CAMS.
- 4,641 rows: one per station × pollutant × statistic.

### What we use

- `COD_NACION`: the 8-digit national code. It is read as a float (`1022001.0` instead of `01022001`), so we convert it to text with `.astype(int).astype(str).str.zfill(8)`.
- `COD_ESTACI` (EEA station code, e.g. `ES1745A`), `NOMBRE`, `LATITUD_G`, `LONGITUD_G`.

### Result

- 51 stations in the Canary Islands, one row each. 49 of them match our 56 PM10 stations.
- Saved to `data/processed/canarias_station_coordinates.csv`.
- 7 stations without coordinates: `35002002`, `35002003`, `35016013`, `35019002`, `35022002`, `38006002`, `38024001`. Most are probably closed, but `35002003` still reports in 2026.

### Why not the EEA

- `metadata.csv` has empty coordinates.
- The EEA ArcGIS station service (`AirQuality/AirQualityDownloadServiceEUMonitoringStations/MapServer`, layer 0) timed out on the `air.`, `eeha.` and `forest.discomap.eea.europa.eu` domains on 24 and 25 November 2026.

### Candidates for the 7 missing stations

- The EEA ArcGIS service, when it is back.
- MITECO historical WMS (stations used since 2001): https://wms.mapama.gob.es/sig/EvaluacionAmbiental/CalidadAire/RedEstacionesCa/wms.aspx
- The Canary Islands Government network site: https://www3.gobiernodecanarias.org/medioambiente/calidaddelaire/

If a station cannot be located, it is left out of the maps and the CAMS comparison, and the Methodology page explains it. Its measurements still count for the history.

### Licence and attribution

Reuse is allowed under Spanish Law 37/2007 if the source is cited: "Origen de los datos: Ministerio para la Transición Ecológica y el Reto Demográfico (MITECO)", with the date of the last update. We must not suggest that MITECO endorses the project.

---

## 3. CAMS global atmospheric composition forecasts

### Access

- Dataset `cams-global-atmospheric-composition-forecasts` on the Atmosphere Data Store (ADS).
- Free account. Python client `cdsapi`, with the key in `~/.cdsapirc` (outside the repo, never committed). The dataset licence must be accepted once on the web form.
- We use the global product because the regional European domain does not cover the Canary Islands. The global grid is 0.4°.

### Test request

```python
request = {
    "date": ["2020-02-22/2020-02-22"],
    "time": ["00:00"],
    "leadtime_hour": [str(h) for h in range(73)],   # 0–72 h
    "type": ["forecast"],
    "data_format": "netcdf_zip",
    "variable": ["particulate_matter_10um", "dust_aerosol_optical_depth_550nm"],
    "area": [30, -19, 27, -13],                     # North, West, South, East
}
```

### Gotchas so far

| # | Gotcha | How we handle it |
|---|---|---|
| 1 | **Data older than 30 days is on tape** ("slow access"). On 2026-11-25: 60 requests running and ~1,470 queued. Our first request was still queued after several hours | Plan the historical download in days, not minutes. Recent data (last 30 days) is on disk and fast |
| 2 | **ADS protection measures** (October 2026): requests must be sequential and valid, and the user profile accurate. Non-compliant activity can get the account suspended | Historical ingestion runs one request at a time, is idempotent and can resume. Always test a small request before a loop |
| 3 | **GRIB needs extra system libraries** | Request netCDF (zipped) and read it with `xarray` |
| 4 | **Cost limit per request**: days × lead times × variables, at most 10,000. A whole year at hourly lead times costs 88,572 | Lead times every 3 hours (0, 3, …, 72) and half a year per request: 9,100–9,200 each. 22 requests for 2015–2025. The download script checks the cost before sending (`spikes/download_cams.py`) |
| 5 | **About one day in the queue per request**, and requests must go one at a time | Download 2020–2025 first (MVP), then 2019 back to 2015. The MVP does not wait for the full history |

### To check when the data arrives

- File structure: dimensions, coordinates, variable names.
- Units: PM10 is probably in kg/m³, which needs × 10⁹ to get µg/m³. To confirm.
- Which grid cell each station falls in.
- February 2020: CAMS PM10 against the station measurements.
- Total download time for 2015–2025.

### Licence and attribution

CC BY since July 2025. Attribution text: "Contains modified Copernicus Atmosphere Monitoring Service information [year]. Neither the European Commission nor ECMWF is responsible for any use that may be made of the Copernicus information or data it contains." Also cite the dataset's ADS catalogue entry (DOI).

---

## 4. Open questions

- The 7 stations without coordinates.
- Why 5 stations in `metadata.csv` (`ES0197A`, `ES1132A`, `ES1133A`, `ES1748A`, `ES1757A`) have no verified files.
- Timezone: confirm UTC+01 with an independent source.
- CAMS: everything in "To check when the data arrives".
- The ADS terms-of-use change announced in October 2026.
- Does EEA dataset 4 (CAMS forecast at station level) include the Canary Islands?
- The official list of African dust episodes (MITECO/CSIC reports "Episodios naturales de partículas"): format and years available. It can validate our episode detection.

## 5. Decisions from the spike

To move to `docs/decisions.md` when the MVP starts.

1. Filter EEA files by station-code prefix (`35`/`38`), not by `metadata.csv`.
2. Keep only rows with `Validity == 1`.
3. Treat EEA timestamps as UTC+01 and convert them to UTC.
4. Verified data for history; up-to-date data for "Now"; store the source dataset of every row.
5. Coordinates from MITECO. Stations without coordinates are left out of the maps and the CAMS comparison until we find them.
6. CAMS global product, not the regional one.
7. When two sampling points of a station report the same hour, keep the one that continues afterwards.
8. CAMS lead times every 3 hours (hourly only for selected episodes, such as February 2020), half a year per request, 2020–2025 first.