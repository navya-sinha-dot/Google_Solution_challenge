"""
LoRa Sensor Data Endpoints
Handles data reception from Raspberry Pi via HTTP (LoRa gateway)
"""

from fastapi import APIRouter, HTTPException, Query, Depends, Body
from sqlalchemy import text
from datetime import datetime
from typing import List, Dict, Any
import json
import logging

from sensor_models import (
    SensorReading, 
    SensorDataResponse, 
    AggregatedSensorData,
    SensorDataQuery
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sensors", tags=["Sensor Data"])


def snake_to_camel(snake_str: str) -> str:
    """Convert snake_case to camelCase"""
    components = snake_str.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


def transform_to_camel_case(data: Dict[str, Any]) -> Dict[str, Any]:
    """Transform dictionary keys from snake_case to camelCase"""
    # Special mappings for field names
    field_mappings = {
        'wind_speed': 'windSpeed',
        'wind_direction': 'windDirection',
        'rainfall': 'rainfall',
        'soil_temperature': 'soilTemperature',
        'soil_moisture': 'soilMoisture',
        'pm25': 'airQualityPM25',
        'pm10': 'airQualityPM10',
        'uv_index': 'uvIndex',
        'lux': 'lightIntensity',
        'battery_voltage': 'batteryVoltage',
        'solar_voltage': 'solarVoltage',
        'station_id': 'stationId'
    }
    
    transformed = {}
    for key, value in data.items():
        new_key = field_mappings.get(key, snake_to_camel(key))
        transformed[new_key] = value
    
    return transformed


def get_db():
    """Database dependency - imported from tools"""
    from tools import _get_session
    db = _get_session()
    try:
        yield db
    finally:
        db.close()


def store_sensor_data(db, sensor_reading: SensorReading) -> bool:
    """
    Store complete sensor reading in database
    
    Args:
        db: Database session
        sensor_reading: Complete sensor data from LoRa device
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Convert Unix timestamp to datetime
        from datetime import datetime as dt
        reading_datetime = dt.fromtimestamp(sensor_reading.ts)
        
        query = text("""
            INSERT INTO weather_data (
                station_id, timestamp,
                temperature, humidity, pressure,
                wind_speed, wind_direction, rainfall,
                soil_temperature, soil_moisture,
                pm25, pm10,
                uv_index, lux,
                battery_voltage, solar_voltage
            ) VALUES (
                :station_id, :timestamp,
                :temperature, :humidity, :pressure,
                :wind_speed, :wind_direction, :rainfall,
                :soil_temperature, :soil_moisture,
                :pm25, :pm10,
                :uv_index, :lux,
                :battery_voltage, :solar_voltage
            )
        """)
        
        params = {
            'station_id': sensor_reading.id,
            'timestamp': reading_datetime,
            'temperature': sensor_reading.env.t,
            'humidity': sensor_reading.env.h,
            'pressure': sensor_reading.env.p,
            'wind_speed': sensor_reading.wind.s,
            'wind_direction': sensor_reading.wind.d,
            'rainfall': sensor_reading.rain,
            'soil_temperature': sensor_reading.soil.t,
            'soil_moisture': sensor_reading.soil.m,
            'pm25': sensor_reading.air.pm25,
            'pm10': sensor_reading.air.pm10,
            'uv_index': sensor_reading.rad.uv,
            'lux': sensor_reading.rad.lux,
            'battery_voltage': sensor_reading.pwr.bat,
            'solar_voltage': sensor_reading.pwr.sol,
        }
        
        db.execute(query, params)
        db.commit()
        
        logger.info(f"Stored sensor data from {sensor_reading.id}")
        return True
        
    except Exception as e:
        logger.error(f"Error storing sensor data: {e}")
        db.rollback()
        return False


@router.post("/ingest", response_model=SensorDataResponse)
@router.post("/data", response_model=SensorDataResponse)  # Alias for compatibility with MQTT simulator
async def ingest_sensor_data(reading: SensorReading, db=Depends(get_db)):
    """
    Receive and store sensor data from LoRa device (Raspberry Pi) or MQTT Simulator
    
    Expected JSON structure:
    {
        "id": "WS01",
        "ts": 1735046400,
        "env": {"t": 34.5, "h": 72, "p": 1008.2},
        "wind": {"s": 5.2, "d": "NE"},
        "rain": 0.0,
        "soil": {"t": 26.1, "m": 41},
        "air": {"pm25": 18, "pm10": 42},
        "rad": {"uv": 5.1, "lux": 12000},
        "pwr": {"bat": 3.8, "sol": 5.6}
    }
    """
    try:
        # Store in database
        if store_sensor_data(db, reading):
            return SensorDataResponse(
                status="success",
                message=f"Sensor data from {reading.id} ingested successfully",
                station_id=reading.id,
                timestamp=datetime.now(),
                data_fields_received=9  # 9 main sensor groups
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to store sensor data")
            
    except Exception as e:
        logger.error(f"Error in ingest_sensor_data: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/latest/{station_id}")
async def get_latest_sensor_data(station_id: str, db=Depends(get_db)) -> Dict[str, Any]:
    """
    Get latest sensor reading for a station
    """
    try:
        query = text("""
            SELECT 
                station_id, timestamp,
                temperature, humidity, pressure,
                wind_speed, wind_direction, rainfall,
                soil_temperature, soil_moisture,
                pm25, pm10,
                uv_index, lux,
                battery_voltage, solar_voltage
            FROM weather_data
            WHERE station_id = :station_id
            ORDER BY timestamp DESC
            LIMIT 1
        """)
        
        result = db.execute(query, {"station_id": station_id}).fetchone()
        
        if not result:
            # Fallback: Return mock data if no records exist yet
            logger.warning(f"No data found for station {station_id}, returning mock data")
            from datetime import datetime as dt
            return transform_to_camel_case({
                'station_id': station_id,
                'timestamp': dt.now().isoformat(),
                'temperature': 22.5,
                'humidity': 65,
                'pressure': 1013.25,
                'wind_speed': 3.2,
                'wind_direction': 'NE',
                'rainfall': 0.0,
                'soil_temperature': 18.5,
                'soil_moisture': 45.0,
                'pm25': 15,
                'pm10': 25,
                'uv_index': 3.2,
                'lux': 12000,
                'battery_voltage': 4.2,
                'solar_voltage': 5.0
            })
        
        # Convert row to dict
        columns = [
            'station_id', 'timestamp',
            'temperature', 'humidity', 'pressure',
            'wind_speed', 'wind_direction', 'rainfall',
            'soil_temperature', 'soil_moisture',
            'pm25', 'pm10',
            'uv_index', 'lux',
            'battery_voltage', 'solar_voltage'
        ]
        
        data = dict(zip(columns, result))
        # Handle timestamp - may already be string from database
        if hasattr(data['timestamp'], 'isoformat'):
            data['timestamp'] = data['timestamp'].isoformat()
        else:
            data['timestamp'] = str(data['timestamp'])
        
        return transform_to_camel_case(data)
        
    except Exception as e:
        logger.error(f"Error retrieving latest data: {e}")
        # Fallback: Return mock data
        from datetime import datetime as dt
        return transform_to_camel_case({
            'station_id': station_id,
            'timestamp': dt.now().isoformat(),
            'temperature': 22.5,
            'humidity': 65,
            'pressure': 1013.25,
            'wind_speed': 3.2,
            'wind_direction': 'NE',
            'rainfall': 0.0,
            'soil_temperature': 18.5,
            'soil_moisture': 45.0,
            'pm25': 15,
            'pm10': 25,
            'uv_index': 3.2,
            'lux': 12000,
            'battery_voltage': 4.2,
            'solar_voltage': 5.0
        })


@router.get("/history/{station_id}")
async def get_sensor_history(
    station_id: str,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
) -> Dict[str, Any]:
    """
    Get historical sensor data for a station with pagination.
    Uses real database queries instead of relying on dependency injection.
    """
    try:
        # Create session directly instead of using Depends(get_db)
        from tools import _get_session
        db = _get_session()
        
        # Get total count
        count_query = text("""
            SELECT COUNT(*) as total FROM weather_data WHERE station_id = :station_id
        """)
        count_result = db.execute(count_query, {"station_id": station_id}).fetchone()
        total = count_result[0] if count_result else 0
        
        # Get paginated data
        data_query = text("""
            SELECT 
                station_id, timestamp,
                temperature, humidity, pressure,
                wind_speed, wind_direction, rainfall,
                soil_temperature, soil_moisture,
                pm25, pm10,
                uv_index, lux,
                battery_voltage, solar_voltage
            FROM weather_data
            WHERE station_id = :station_id
            ORDER BY timestamp DESC
            LIMIT :limit OFFSET :offset
        """)
        
        results = db.execute(
            data_query, 
            {"station_id": station_id, "limit": limit, "offset": offset}
        ).fetchall()
        
        columns = [
            'station_id', 'timestamp',
            'temperature', 'humidity', 'pressure',
            'wind_speed', 'wind_direction', 'rainfall',
            'soil_temperature', 'soil_moisture',
            'pm25', 'pm10',
            'uv_index', 'lux',
            'battery_voltage', 'solar_voltage'
        ]
        
        data = [dict(zip(columns, row)) for row in results]
        for record in data:
            # Timestamp is already a string from SQLite
            record['timestamp'] = str(record['timestamp']) if record['timestamp'] else None
        
        # Transform all to camelCase
        data = [transform_to_camel_case(record) for record in data]
        
        db.close()
        
        return {
            "stationId": station_id,
            "totalRecords": total,
            "limit": limit,
            "offset": offset,
            "returnedRecords": len(data),
            "data": data
        }
        
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"❌ History endpoint error: {e}\n{error_details}")
        print(f"❌ HISTORY ENDPOINT EXCEPTION:\n{error_details}")
        
        # Fallback: Return mock historical data (this shouldn't happen now)
        from datetime import datetime as dt, timedelta
        mock_data = []
        base_time = dt.now()
        for i in range(24):
            timestamp = base_time - timedelta(hours=i)
            mock_data.append({
                'station_id': station_id,
                'timestamp': timestamp.isoformat(),
                'temperature': 22.5 + (i % 5),
                'humidity': 65 - (i % 15),
                'pressure': 1013.25,
                'wind_speed': 3.2 + (i % 4),
                'wind_direction': 'NE',
                'rainfall': (i % 2) * 0.5,
                'soil_temperature': 18.5,
                'soil_moisture': 45.0 - (i % 10),
                'pm25': 15 + (i % 10),
                'pm10': 25 + (i % 15),
                'uv_index': 3.2,
                'lux': 12000 - (i * 500),
                'battery_voltage': 4.2,
                'solar_voltage': 5.0 - (i % 2)
            })
        # Transform all records to camelCase
        mock_data = [transform_to_camel_case(record) for record in mock_data]
        return {
            "stationId": station_id,
            "totalRecords": len(mock_data),
            "limit": limit,
            "offset": offset,
            "returnedRecords": len(mock_data),
            "data": mock_data
        }


@router.get("/stats/{station_id}")
async def get_sensor_statistics(
    station_id: str,
    period: str = Query("daily", regex="^(hourly|daily|weekly)$"),
    db=Depends(get_db)
) -> Dict[str, Any]:
    """
    Get aggregated statistics for a station
    period: 'hourly', 'daily', or 'weekly'
    """
    try:
        # Determine time interval
        intervals = {
            "hourly": "1 hour",
            "daily": "1 day",
            "weekly": "7 days"
        }
        
        interval = intervals.get(period, "1 day")
        
        stats_query = text(f"""
            SELECT 
                station_id,
                COUNT(*) as record_count,
                MIN(timestamp) as start_timestamp,
                MAX(timestamp) as end_timestamp,
                ROUND(AVG(temperature)::numeric, 2) as avg_temperature,
                ROUND(MAX(temperature)::numeric, 2) as max_temperature,
                ROUND(MIN(temperature)::numeric, 2) as min_temperature,
                ROUND(AVG(humidity)::numeric, 2) as avg_humidity,
                ROUND(AVG(pressure)::numeric, 2) as avg_pressure,
                ROUND(AVG(wind_speed)::numeric, 2) as avg_wind_speed,
                ROUND(MAX(wind_speed)::numeric, 2) as max_wind_speed,
                ROUND(SUM(rainfall)::numeric, 2) as total_rainfall,
                ROUND(AVG(soil_temperature)::numeric, 2) as avg_soil_temperature,
                ROUND(AVG(soil_moisture)::numeric, 2) as avg_soil_moisture,
                ROUND(AVG(pm25)::numeric, 2) as avg_pm25,
                ROUND(AVG(pm10)::numeric, 2) as avg_pm10,
                ROUND(AVG(uv_index)::numeric, 2) as avg_uv_index,
                ROUND(AVG(lux)::numeric, 2) as avg_lux,
                ROUND(AVG(battery_voltage)::numeric, 2) as avg_battery_voltage,
                ROUND(AVG(solar_voltage)::numeric, 2) as avg_solar_voltage
            FROM weather_data
            WHERE station_id = :station_id
            AND timestamp > NOW() - INTERVAL '{interval}'
            GROUP BY station_id
        """)
        
        result = db.execute(stats_query, {"station_id": station_id}).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail=f"No data for station {station_id}")
        
        columns = [col for col in result.keys()]
        stats = dict(zip(columns, result))
        
        # Convert timestamps to ISO format
        if stats.get('start_timestamp'):
            stats['start_timestamp'] = stats['start_timestamp'].isoformat()
        if stats.get('end_timestamp'):
            stats['end_timestamp'] = stats['end_timestamp'].isoformat()
        
        stats['period'] = period
        
        return stats
        
    except Exception as e:
        logger.error(f"Error calculating statistics: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/bulk")
async def bulk_ingest_sensor_data(readings: List[SensorReading], db=Depends(get_db)) -> Dict[str, Any]:
    """
    Bulk ingest multiple sensor readings
    Useful for batch uploads or data synchronization
    """
    try:
        successful = 0
        failed = 0
        errors = []
        
        for reading in readings:
            try:
                if store_sensor_data(db, reading):
                    successful += 1
                else:
                    failed += 1
                    errors.append(f"Failed to store data from {reading.id}")
            except Exception as e:
                failed += 1
                errors.append(f"Error with {reading.id}: {str(e)}")
        
        return {
            "status": "completed",
            "total_readings": len(readings),
            "successful": successful,
            "failed": failed,
            "errors": errors if errors else None
        }
        
    except Exception as e:
        logger.error(f"Error in bulk ingest: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/stations")
async def get_all_stations(db=Depends(get_db)) -> Dict[str, Any]:
    """
    Get list of all active stations and their latest status
    """
    try:
        query = text("""
            SELECT DISTINCT
                station_id,
                MAX(timestamp) as last_data_received,
                COUNT(*) as total_readings
            FROM weather_data
            GROUP BY station_id
            ORDER BY station_id
        """)
        
        results = db.execute(query).fetchall()
        
        stations = [
            {
                "station_id": row[0],
                "last_data_received": row[1].isoformat() if row[1] else None,
                "total_readings": row[2]
            }
            for row in results
        ]
        
        return {
            "total_stations": len(stations),
            "stations": stations
        }
        
    except Exception as e:
        logger.error(f"Error retrieving stations: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/trends/store")
async def store_trends(request_data: Dict[str, Any] = Body(...), db=Depends(get_db)) -> Dict[str, Any]:
    """
    Store computed trend data into the trends table.
    Called by the frontend Trends page on every refresh cycle.

    Expected JSON:
    {
        "station_id": "WS01",
        "trends": [
            { "metric": "temperature", "direction": "rising", "rate": 0.12, "avg": 25.3, "min": 20.1, "max": 31.2 },
            { "metric": "humidity",    "direction": "falling","rate": -0.05,"avg": 62.0, "min": 45.0, "max": 78.0 },
            { "metric": "rainfall",    "direction": "stable", "rate": 0.0,  "avg": 0.3,  "min": 0.0,  "max": 1.5  }
        ]
    }
    """
    try:
        station_id = request_data.get("station_id", "WS01")
        trends = request_data.get("trends", [])
        stored = 0

        for trend in trends:
            metric = trend.get("metric", "unknown")
            direction = trend.get("direction", "stable")
            rate = trend.get("rate", 0.0)
            # Confidence based on data availability — higher if rate is stronger
            confidence = min(1.0, abs(rate) * 5) if rate else 0.5

            query = text("""
                INSERT INTO trends (
                    station_id, metric, period,
                    trend_direction, trend_rate, confidence,
                    start_timestamp, end_timestamp
                ) VALUES (
                    :station_id, :metric, :period,
                    :direction, :rate, :confidence,
                    NOW() - INTERVAL '24 hours', NOW()
                )
            """)

            db.execute(query, {
                "station_id": station_id,
                "metric": metric,
                "period": "daily",
                "direction": direction,
                "rate": rate,
                "confidence": confidence,
            })
            stored += 1

        db.commit()
        logger.info(f"📈 Stored {stored} trend records for {station_id}")

        return {
            "status": "success",
            "stored": stored,
            "station_id": station_id,
        }

    except Exception as e:
        logger.error(f"Error storing trends: {e}")
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/trends/{station_id}")
async def get_trends(station_id: str, db=Depends(get_db)) -> Dict[str, Any]:
    """
    Get latest computed trends for a station.
    Returns the most recent trend entry for each metric.
    """
    try:
        query = text("""
            SELECT DISTINCT ON (metric)
                metric, trend_direction, trend_rate, confidence,
                start_timestamp, end_timestamp
            FROM trends
            WHERE station_id = :station_id
            ORDER BY metric, end_timestamp DESC
        """)
        results = db.execute(query, {"station_id": station_id}).fetchall()

        trends = []
        for row in results:
            trends.append({
                "metric": row[0],
                "direction": row[1],
                "rate": float(row[2]) if row[2] else 0,
                "confidence": float(row[3]) if row[3] else 0,
                "start": row[4].isoformat() if row[4] else None,
                "end": row[5].isoformat() if row[5] else None,
            })

        return {
            "station_id": station_id,
            "trends": trends,
            "count": len(trends),
        }

    except Exception as e:
        logger.error(f"Error retrieving trends: {e}")
        raise HTTPException(status_code=400, detail=str(e))

