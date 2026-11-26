"""SQLAlchemy models, matching the tables agreed on in docs/decisions.md."""

from datetime import date, datetime
from enum import Enum

from geoalchemy2 import Geometry, WKBElement
from sqlalchemy import ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Island(str, Enum):
    TENERIFE = "tenerife"
    GRAN_CANARIA = "gran_canaria"
    LA_PALMA = "la_palma"
    LA_GOMERA = "la_gomera"
    EL_HIERRO = "el_hierro"
    LANZAROTE = "lanzarote"
    FUERTEVENTURA = "fuerteventura"


class StationType(str, Enum):
    """EEA's AirQualityStationType. 4 of the 60 Canarias sampling points have none recorded."""

    INDUSTRIAL = "industrial"
    TRAFFIC = "traffic"
    BACKGROUND = "background"


class StationArea(str, Enum):
    """EEA's AirQualityStationArea. Every Canarias sampling point has one."""

    URBAN = "urban"
    SUBURBAN = "suburban"
    RURAL_REGIONAL = "rural-regional"
    RURAL_NEARCITY = "rural-nearcity"


class Dataset(str, Enum):
    VERIFIED = "verified"
    UP_TO_DATE = "up_to_date"


class DataStatus(str, Enum):
    PROVISIONAL = "provisional"
    CONFIRMED = "confirmed"


class DustType(str, Enum):
    AFRICAN = "african"
    BIOMASS_BURNING = "biomass_burning"
    EUROPEAN_SULFATE = "european_sulfate"


class Station(Base):
    __tablename__ = "stations"

    station_code: Mapped[str] = mapped_column(primary_key=True)
    eea_code: Mapped[str]
    name: Mapped[str]
    island: Mapped[Island]
    altitude_m: Mapped[float]
    station_type: Mapped[StationType | None]
    station_area: Mapped[StationArea]
    location: Mapped[WKBElement] = mapped_column(Geometry(geometry_type="POINT", srid=4326))


class Measurement(Base):
    """One row per station per hour. (station_code, start_utc) is the natural key."""

    __tablename__ = "measurements"

    station_code: Mapped[str] = mapped_column(ForeignKey("stations.station_code"), primary_key=True)
    start_utc: Mapped[datetime] = mapped_column(primary_key=True)
    value: Mapped[float]
    dataset: Mapped[Dataset]


class Episode(Base):
    """One calima episode detected by our own definition (see docs/decisions.md)."""

    __tablename__ = "episodes"

    id: Mapped[int] = mapped_column(primary_key=True)
    start_date: Mapped[date]
    end_date: Mapped[date]
    peak_value: Mapped[float]
    peak_station_code: Mapped[str] = mapped_column(ForeignKey("stations.station_code"))
    definition_version: Mapped[str]
    data_status: Mapped[DataStatus]


class OfficialEpisode(Base):
    """Hand-entered rows from the MITECO/CSIC annual reports, to validate our own detection."""

    __tablename__ = "official_episodes"

    id: Mapped[int] = mapped_column(primary_key=True)
    region: Mapped[str]  # always "CANARIAS" for the MVP, see docs/decisions.md
    dust_type: Mapped[DustType]
    start_date: Mapped[date]
    end_date: Mapped[date]
    source_report: Mapped[str]


class CamsForecast(Base):
    """One CAMS forecast value at a station, for one run and one lead time.

    (station_code, run_time, lead_time_hours) is the natural key, the same idea as
    measurements: together they identify one forecast value, with no row implying
    another. pm10_forecast_ugm3 is already converted from the raw kg/m3 CAMS gives us.
    """

    __tablename__ = "cams_forecasts"

    station_code: Mapped[str] = mapped_column(ForeignKey("stations.station_code"), primary_key=True)
    run_time: Mapped[datetime] = mapped_column(primary_key=True)
    lead_time_hours: Mapped[int] = mapped_column(primary_key=True)
    valid_time: Mapped[datetime]
    pm10_forecast_ugm3: Mapped[float]
    dust_aod_550: Mapped[float]
