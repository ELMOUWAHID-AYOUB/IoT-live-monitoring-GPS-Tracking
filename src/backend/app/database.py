"""
Database - SQLAlchemy async avec PostgreSQL
Choix PostgreSQL: ACID, intégrité référentielle, requêtes spatiales
"""
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey, func
)

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://tracker:tracker_secret@localhost:5432/gps_tracking"
).replace("postgresql://", "postgresql+asyncpg://")

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Runner(Base):
    __tablename__ = "runners"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(200), unique=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class Device(Base):
    __tablename__ = "devices"
    id = Column(Integer, primary_key=True)
    runner_id = Column(Integer, ForeignKey("runners.id", ondelete="CASCADE"))
    ipv6_address = Column(String(50), nullable=False)
    device_type = Column(String(20), nullable=False)  # gps|battery|temperature
    coap_port = Column(Integer, nullable=False)
    api_key = Column(String(64), nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class Session(Base):
    __tablename__ = "sessions"
    id = Column(Integer, primary_key=True)
    runner_id = Column(Integer, ForeignKey("runners.id", ondelete="CASCADE"))
    started_at = Column(DateTime, server_default=func.now())
    ended_at = Column(DateTime, nullable=True)
    total_distance_m = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)


class GPSMeasurement(Base):
    __tablename__ = "gps_measurements"
    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"))
    device_id = Column(Integer, ForeignKey("devices.id"))
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    altitude = Column(Float, nullable=True)
    timestamp = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class BatteryMeasurement(Base):
    __tablename__ = "battery_measurements"
    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"))
    device_id = Column(Integer, ForeignKey("devices.id"))
    level_percent = Column(Float, nullable=False)
    voltage = Column(Float, nullable=True)
    timestamp = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class TemperatureMeasurement(Base):
    __tablename__ = "temperature_measurements"
    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"))
    device_id = Column(Integer, ForeignKey("devices.id"))
    celsius = Column(Float, nullable=False)
    humidity = Column(Float, nullable=True)
    pressure = Column(Float, nullable=True)
    timestamp = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
