import os
import json
from typing import Dict, List, Any
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta

from dotenv import load_dotenv

load_dotenv()

# Lazy-load DATABASE_URL to ensure systemd environment is available
_engine = None
_SessionLocal = None

def _get_engine():
    """Lazy initialize database engine from environment or use default SQLite"""
    global _engine, _SessionLocal
    if _engine is None:
        load_dotenv()
        DATABASE_URL = os.getenv("DATABASE_URL")
        
        if DATABASE_URL:
            # Clean up the URL if it's a Neon URL with pooler options
            if "neon.tech" in DATABASE_URL and "sslmode" not in DATABASE_URL:
                if "?" in DATABASE_URL:
                    DATABASE_URL += "&sslmode=require"
                else:
                    DATABASE_URL += "?sslmode=require"
            
            print(f"\n[DB INIT] Connecting to PostgreSQL (Neon): {DATABASE_URL.split('@')[-1].split('/')[0]}")
            _engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=5, max_overflow=10)
        else:
            # Fallback to local SQLite only if no DATABASE_URL is found
            db_path = "sensor_data.db"
            DATABASE_URL = f"sqlite:///{db_path}"
            print(f"\n[DB INIT] No DATABASE_URL found. Falling back to local SQLite: {DATABASE_URL}")
            _engine = create_engine(DATABASE_URL)
        
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    
    return _engine, _SessionLocal

def _get_session():
    """Get database session"""
    engine, SessionLocal = _get_engine()
    return SessionLocal()

def get_db():
    db = _get_session()
    try:
        yield db
    finally:
        db.close()

def get_latest_weather(sensor_id: str) -> Dict[str, Any]:
    """Get the latest weather data for a sensor - includes all sensor fields."""
    try:
        db = _get_session()
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
        result = db.execute(query, {"station_id": sensor_id}).fetchone()
        db.close()
        if result:
            return {
                "station_id": result[0],
                "timestamp": str(result[1]) if result[1] else None,  # Timestamp is already string from DB
                "temperature": float(result[2]) if result[2] else None,
                "humidity": float(result[3]) if result[3] else None,
                "pressure": float(result[4]) if result[4] else None,
                "wind_speed": float(result[5]) if result[5] else None,
                "wind_direction": result[6],
                "rainfall": float(result[7]) if result[7] else None,
                "soil_temperature": float(result[8]) if result[8] else None,
                "soil_moisture": float(result[9]) if result[9] else None,
                "air_quality_pm25": float(result[10]) if result[10] else None,
                "air_quality_pm10": float(result[11]) if result[11] else None,
                "uv_index": float(result[12]) if result[12] else None,
                "light_intensity": float(result[13]) if result[13] else None,
                "battery_voltage": float(result[14]) if result[14] else None,
                "solar_voltage": float(result[15]) if result[15] else None
            }
    except Exception as e:
        print(f"Database error in get_latest_weather: {e}")
    # Return empty if no data or DB error
    return {}

def get_weather_range(sensor_id: str, start: str, end: str) -> List[Dict[str, Any]]:
    """Get weather data for a sensor within a time range."""
    try:
        db = _get_session()
        query = text("""
            SELECT temperature, humidity, pressure, wind_speed, rainfall, battery_voltage, timestamp
            FROM weather_data
            WHERE station_id = :station_id AND timestamp BETWEEN :start AND :end
            ORDER BY timestamp
        """)
        results = db.execute(query, {"station_id": sensor_id, "start": start, "end": end}).fetchall()
        db.close()
        data = []
        for row in results:
            data.append({
                "temperature": float(row[0]) if row[0] else None,
                "humidity": float(row[1]) if row[1] else None,
                "pressure": float(row[2]) if row[2] else None,
                "wind_speed": float(row[3]) if row[3] else None,
                "rainfall": float(row[4]) if row[4] else None,
                "battery_voltage": float(row[5]) if row[5] else None,
                "timestamp": row[6].isoformat() if row[6] else None
            })
        return data
    except:
        return []  # Return empty on error

def create_alert_rule(user_id: str, metric: str, operator: str, threshold: float, station_id: str = "station_01", unit: str = "C", cooldown_minutes: int = 30) -> Dict[str, Any]:
    """Create a new alert rule."""
    try:
        db = _get_session()
        query = text("""
            INSERT INTO alerts (user_id, station_id, metric, operator, threshold, unit, cooldown_minutes)
            VALUES (:user_id, :station_id, :metric, :operator, :threshold, :unit, :cooldown)
            RETURNING id
        """)
        result = db.execute(query, {
            "user_id": user_id,
            "station_id": station_id,
            "metric": metric,
            "operator": operator,
            "threshold": threshold,
            "unit": unit,
            "cooldown": cooldown_minutes
        })
        db.commit()
        alert_id = result.fetchone()[0]
        db.close()
        return {"alert_id": alert_id, "status": "created"}
    except Exception as e:
        return {"error": str(e)}

def disable_alert_rule(alert_id: int) -> Dict[str, Any]:
    """Disable an alert rule."""
    db = _get_session()
    query = text("UPDATE alerts SET active = FALSE WHERE id = :alert_id")
    db.execute(query, {"alert_id": alert_id})
    db.commit()
    db.close()
    return {"status": "disabled"}

def get_active_alerts(user_id: str) -> List[Dict[str, Any]]:
    """Get all active alert rules for a user."""
    try:
        db = _get_session()
        query = text("""
            SELECT id, station_id, metric, operator, threshold, unit, last_triggered, cooldown_minutes
            FROM alerts
            WHERE user_id = :user_id AND active = TRUE
        """)
        results = db.execute(query, {"user_id": user_id}).fetchall()
        db.close()
        alerts = []
        for row in results:
            alerts.append({
                "id": row[0],
                "station_id": row[1],
                "metric": row[2],
                "operator": row[3],
                "threshold": float(row[4]) if row[4] is not None else None,
                "unit": row[5],
                "last_triggered": row[6].isoformat() if row[6] else None,
                "cooldown_minutes": row[7]
            })
        return alerts
    except:
        return []

def get_system_health() -> Dict[str, Any]:
    """Get system health status."""
    try:
        db = _get_session()
        query = text("""
            SELECT sensor_status, battery_level, connectivity, last_data_received, uptime_hours
            FROM system_health
            WHERE station_id = 'station_01'
            ORDER BY timestamp DESC
            LIMIT 1
        """)
        result = db.execute(query).fetchone()
        db.close()
        if result:
            return {
                "sensor_status": result[0],
                "battery_level": float(result[1]) if result[1] else None,
                "connectivity": result[2],
                "last_data_received": result[3].isoformat() if result[3] else None,
                "uptime_hours": float(result[4]) if result[4] else None
            }
    except Exception as e:
        print(f"Database error: {e}")
    return {
        "status": "unknown",
        "battery_level": None,
        "connectivity": "unknown",
        "last_data_received": None,
        "uptime_hours": None
    }

def get_trends(station_id: str, metric: str, period: str = "daily") -> List[Dict[str, Any]]:
    """Get trend data for a specific metric and period."""
    try:
        db = _get_session()
        query = text("""
            SELECT trend_direction, trend_rate, confidence, start_timestamp, end_timestamp
            FROM trends
            WHERE station_id = :station_id AND metric = :metric AND period = :period
            ORDER BY end_timestamp DESC
            LIMIT 5
        """)
        results = db.execute(query, {"station_id": station_id, "metric": metric, "period": period}).fetchall()
        db.close()
        trends = []
        for row in results:
            trends.append({
                "trend_direction": row[0],
                "trend_rate": float(row[1]) if row[1] else None,
                "confidence": float(row[2]) if row[2] else None,
                "start_timestamp": row[3].isoformat() if row[3] else None,
                "end_timestamp": row[4].isoformat() if row[4] else None
            })
        return trends
    except Exception as e:
        print(f"Database error: {e}")
    return []

def insert_trend_data(station_id: str, metric: str, period: str, trend_direction: str, trend_rate: float, confidence: float, start_timestamp: datetime, end_timestamp: datetime) -> Dict[str, Any]:
    """Insert new trend data."""
    try:
        db = _get_session()
        query = text("""
            INSERT INTO trends (station_id, metric, period, trend_direction, trend_rate, confidence, start_timestamp, end_timestamp)
            VALUES (:station_id, :metric, :period, :trend_direction, :trend_rate, :confidence, :start_timestamp, :end_timestamp)
        """)
        db.execute(query, {
            "station_id": station_id,
            "metric": metric,
            "period": period,
            "trend_direction": trend_direction,
            "trend_rate": trend_rate,
            "confidence": confidence,
            "start_timestamp": start_timestamp,
            "end_timestamp": end_timestamp
        })
        db.commit()
        db.close()
        return {"status": "inserted"}
    except Exception as e:
        return {"error": str(e)}

def insert_health_data(station_id: str, sensor_status: str, battery_level: float, connectivity: str, uptime_hours: float) -> Dict[str, Any]:
    """Insert new health data."""
    try:
        db = _get_session()
        query = text("""
            INSERT INTO system_health (station_id, sensor_status, battery_level, connectivity, uptime_hours)
            VALUES (:station_id, :sensor_status, :battery_level, :connectivity, :uptime_hours)
        """)
        db.execute(query, {
            "station_id": station_id,
            "sensor_status": sensor_status,
            "battery_level": battery_level,
            "connectivity": connectivity,
            "uptime_hours": uptime_hours
        })
        db.commit()
        db.close()
        return {"status": "inserted"}
    except Exception as e:
        return {"error": str(e)}

def insert_weather_data(sensor_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Insert new weather data. Used by monitoring system."""
    try:
        db = _get_session()
        query = text("""
            INSERT INTO weather_data (station_id, timestamp, temperature, humidity, pressure, wind_speed, rainfall, battery_voltage)
            VALUES (:station_id, :timestamp, :temperature, :humidity, :pressure, :wind_speed, :rainfall, :battery_voltage)
        """)
        db.execute(query, {
            "station_id": sensor_id,
            "timestamp": data.get("timestamp", datetime.now()),
            "temperature": data.get("temperature"),
            "humidity": data.get("humidity"),
            "pressure": data.get("pressure"),
            "wind_speed": data.get("wind_speed"),
            "rainfall": data.get("rainfall"),
            "battery_voltage": data.get("battery_voltage")
        })
        db.commit()
        db.close()
        return {"status": "inserted"}
    except Exception as e:
        return {"error": str(e)}

def check_alerts(sensor_id: str) -> List[Dict[str, Any]]:
    """Check if any alerts should be triggered based on latest data."""
    latest = get_latest_weather(sensor_id)
    if not latest:
        return []

    triggered = []
    try:
        db = _get_session()
        # Get all active alerts for this station
        query = text("""
            SELECT id, user_id, metric, operator, threshold, last_triggered, cooldown_minutes
            FROM alerts
            WHERE station_id = :station_id AND active = TRUE
        """)
        alerts = db.execute(query, {"station_id": sensor_id}).fetchall()
        db.close()

        for alert in alerts:
            alert_id, user_id, metric, operator, threshold, last_triggered, cooldown = alert
            value = latest.get(metric)
            if value is None:
                continue

            # Check condition
            trigger = False
            if operator == ">" and value > threshold:
                trigger = True
            elif operator == "<" and value < threshold:
                trigger = True
            elif operator == ">=" and value >= threshold:
                trigger = True
            elif operator == "<=" and value <= threshold:
                trigger = True
            elif operator == "==" and value == threshold:
                trigger = True

            if trigger:
                # Check cooldown
                now = datetime.now()
                if last_triggered:
                    time_diff = now - last_triggered
                    if time_diff < timedelta(minutes=cooldown):
                        continue  # Still in cooldown

                # Trigger alert
                triggered.append({
                    "alert_id": alert_id,
                    "user_id": user_id,
                    "metric": metric,
                    "value": value,
                    "threshold": threshold,
                    "operator": operator
                })

                # Update last_triggered
                update_query = text("UPDATE alerts SET last_triggered = :now WHERE id = :alert_id")
                db.execute(update_query, {"now": now, "alert_id": alert_id})

        db.commit()
    except Exception as e:
        print(f"Error checking alerts: {e}")

    return triggered