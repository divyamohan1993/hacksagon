import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any

from sqlalchemy import Column, Integer, Float, String, DateTime, create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sensor_id = Column(String(50), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True, default=lambda: datetime.now(timezone.utc))
    pm25 = Column(Float, default=0.0)
    pm10 = Column(Float, default=0.0)
    no2 = Column(Float, default=0.0)
    co = Column(Float, default=0.0)
    aqi = Column(Integer, default=0)
    noise_db = Column(Float, default=0.0)
    trucks = Column(Integer, default=0)
    cars = Column(Integer, default=0)
    buses = Column(Integer, default=0)
    wind_speed = Column(Float, default=0.0)
    wind_direction = Column(Float, default=0.0)
    temperature = Column(Float, default=20.0)


def _get_async_url(url: str) -> str:
    """Convert a standard SQLite URL to an async-compatible one using aiosqlite."""
    if url.startswith("sqlite:///"):
        return url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    return url


_async_engine = None
_async_session_factory = None


def _get_engine():
    global _async_engine
    if _async_engine is None:
        async_url = _get_async_url(settings.DATABASE_URL)
        _async_engine = create_async_engine(
            async_url,
            echo=False,
            pool_pre_ping=True,
        )
    return _async_engine


def _get_session_factory():
    global _async_session_factory
    if _async_session_factory is None:
        engine = _get_engine()
        _async_session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _async_session_factory


async def init_db() -> None:
    """Create all database tables if they do not exist."""
    engine = _get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized successfully")


async def save_reading(
    sensor_id: str,
    pm25: float = 0.0,
    pm10: float = 0.0,
    no2: float = 0.0,
    co: float = 0.0,
    aqi: int = 0,
    noise_db: float = 0.0,
    trucks: int = 0,
    cars: int = 0,
    buses: int = 0,
    wind_speed: float = 0.0,
    wind_direction: float = 0.0,
    temperature: float = 20.0,
) -> None:
    """Persist a single sensor reading to the database."""
    session_factory = _get_session_factory()
    async with session_factory() as session:
        try:
            reading = SensorReading(
                sensor_id=sensor_id,
                timestamp=datetime.now(timezone.utc),
                pm25=pm25,
                pm10=pm10,
                no2=no2,
                co=co,
                aqi=aqi,
                noise_db=noise_db,
                trucks=trucks,
                cars=cars,
                buses=buses,
                wind_speed=wind_speed,
                wind_direction=wind_direction,
                temperature=temperature,
            )
            session.add(reading)
            await session.commit()
        except Exception as exc:
            await session.rollback()
            logger.error("Failed to save reading for sensor %s: %s", sensor_id, exc)
            raise


async def get_history(sensor_id: str, hours: int = 24) -> List[Dict[str, Any]]:
    """Return historical readings for a sensor within the last N hours."""
    session_factory = _get_session_factory()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    async with session_factory() as session:
        result = await session.execute(
            text(
                "SELECT id, sensor_id, timestamp, pm25, pm10, no2, co, aqi, "
                "noise_db, trucks, cars, buses, wind_speed, wind_direction, temperature "
                "FROM sensor_readings "
                "WHERE sensor_id = :sid AND timestamp >= :cutoff "
                "ORDER BY timestamp ASC"
            ),
            {"sid": sensor_id, "cutoff": cutoff},
        )
        rows = result.fetchall()

    records: List[Dict[str, Any]] = []
    for row in rows:
        records.append(
            {
                "id": row[0],
                "sensor_id": row[1],
                "timestamp": row[2].isoformat() if isinstance(row[2], datetime) else str(row[2]),
                "pm25": row[3],
                "pm10": row[4],
                "no2": row[5],
                "co": row[6],
                "aqi": row[7],
                "noise_db": row[8],
                "trucks": row[9],
                "cars": row[10],
                "buses": row[11],
                "wind_speed": row[12],
                "wind_direction": row[13],
                "temperature": row[14],
            }
        )
    return records


async def get_latest_readings() -> Dict[str, Dict[str, Any]]:
    """Return the most recent reading for every sensor."""
    session_factory = _get_session_factory()

    async with session_factory() as session:
        result = await session.execute(
            text(
                "SELECT sr.id, sr.sensor_id, sr.timestamp, sr.pm25, sr.pm10, sr.no2, sr.co, "
                "sr.aqi, sr.noise_db, sr.trucks, sr.cars, sr.buses, sr.wind_speed, "
                "sr.wind_direction, sr.temperature "
                "FROM sensor_readings sr "
                "INNER JOIN ("
                "  SELECT sensor_id, MAX(timestamp) AS max_ts "
                "  FROM sensor_readings GROUP BY sensor_id"
                ") latest ON sr.sensor_id = latest.sensor_id AND sr.timestamp = latest.max_ts"
            )
        )
        rows = result.fetchall()

    latest: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        latest[row[1]] = {
            "id": row[0],
            "sensor_id": row[1],
            "timestamp": row[2].isoformat() if isinstance(row[2], datetime) else str(row[2]),
            "pm25": row[3],
            "pm10": row[4],
            "no2": row[5],
            "co": row[6],
            "aqi": row[7],
            "noise_db": row[8],
            "trucks": row[9],
            "cars": row[10],
            "buses": row[11],
            "wind_speed": row[12],
            "wind_direction": row[13],
            "temperature": row[14],
        }
    return latest


async def close_db() -> None:
    """Dispose the async engine connection pool."""
    global _async_engine, _async_session_factory
    if _async_engine is not None:
        await _async_engine.dispose()
        _async_engine = None
        _async_session_factory = None
        logger.info("Database connection closed")
