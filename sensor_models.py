"""
Pydantic models for IoT sensor data received via LoRa
Defines the complete sensor data structure for Raspberry Pi integration
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class EnvironmentalData(BaseModel):
    """Environmental sensor readings"""
    t: float = Field(..., description="Temperature in °C", alias="t")
    h: float = Field(..., description="Humidity in %", alias="h")
    p: float = Field(..., description="Pressure in hPa", alias="p")


class WindData(BaseModel):
    """Wind sensor readings"""
    s: float = Field(..., description="Wind speed in m/s", alias="s")
    d: str = Field(..., description="Wind direction (N, NE, E, SE, S, SW, W, NW)", alias="d")


class SoilData(BaseModel):
    """Soil sensor readings"""
    t: float = Field(..., description="Soil temperature in °C", alias="t")
    m: float = Field(..., description="Soil moisture in %", alias="m")


class AirQualityData(BaseModel):
    """Air quality sensor readings"""
    pm25: float = Field(..., description="PM2.5 particulate matter in µg/m³", alias="pm25")
    pm10: float = Field(..., description="PM10 particulate matter in µg/m³", alias="pm10")


class RadiationData(BaseModel):
    """Radiation sensor readings"""
    uv: float = Field(..., description="UV index", alias="uv")
    lux: float = Field(..., description="Light intensity in lux", alias="lux")


class PowerData(BaseModel):
    """Power/Battery sensor readings"""
    bat: float = Field(..., description="Battery voltage in V", alias="bat")
    sol: float = Field(..., description="Solar panel voltage in V", alias="sol")


class SensorReading(BaseModel):
    """Complete IoT sensor data structure for LoRa transmission"""
    id: str = Field(..., description="Device/Station ID", alias="id")
    ts: int = Field(..., description="Unix timestamp", alias="ts")
    env: EnvironmentalData = Field(..., description="Environmental data", alias="env")
    wind: WindData = Field(..., description="Wind data", alias="wind")
    rain: float = Field(..., description="Rainfall in mm", alias="rain")
    soil: SoilData = Field(..., description="Soil data", alias="soil")
    air: AirQualityData = Field(..., description="Air quality data", alias="air")
    rad: RadiationData = Field(..., description="Radiation data", alias="rad")
    pwr: PowerData = Field(..., description="Power data", alias="pwr")

    class Config:
        populate_by_name = True  # Allow both field name and alias


class SensorDataResponse(BaseModel):
    """Response after successful sensor data ingestion"""
    status: str
    message: str
    station_id: str
    timestamp: datetime
    data_fields_received: int


class SensorDataQuery(BaseModel):
    """Query parameters for sensor data retrieval"""
    station_id: str = Field(..., description="Station/Device ID")
    limit: int = Field(default=100, description="Number of records to return")
    offset: int = Field(default=0, description="Offset for pagination")


class AggregatedSensorData(BaseModel):
    """Aggregated sensor statistics"""
    station_id: str
    period: str  # "hourly", "daily", "weekly"
    
    # Environmental aggregates
    avg_temperature: Optional[float] = None
    max_temperature: Optional[float] = None
    min_temperature: Optional[float] = None
    avg_humidity: Optional[float] = None
    avg_pressure: Optional[float] = None
    
    # Wind aggregates
    avg_wind_speed: Optional[float] = None
    max_wind_speed: Optional[float] = None
    
    # Rainfall aggregate
    total_rainfall: Optional[float] = None
    
    # Soil aggregates
    avg_soil_temperature: Optional[float] = None
    avg_soil_moisture: Optional[float] = None
    
    # Air quality aggregates
    avg_pm25: Optional[float] = None
    avg_pm10: Optional[float] = None
    
    # Radiation aggregates
    avg_uv_index: Optional[float] = None
    avg_lux: Optional[float] = None
    
    # Power aggregates
    avg_battery_voltage: Optional[float] = None
    avg_solar_voltage: Optional[float] = None
    
    record_count: int
    start_timestamp: datetime
    end_timestamp: datetime
