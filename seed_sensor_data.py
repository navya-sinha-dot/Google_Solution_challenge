#!/usr/bin/env python3
"""
Seed sensor data directly into Neon PostgreSQL.
Inserts realistic MQTT-like sensor readings so you can verify the DB works.
"""

import os
import sys
import random
import math
from datetime import datetime, timedelta
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Fix Windows console encoding for emoji
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

load_dotenv()

def seed_data(num_readings=20):
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ DATABASE_URL not set in .env")
        return

    print(f"🌱 Seeding {num_readings} sensor readings into Neon PostgreSQL...")
    print(f"   Host: {db_url.split('@')[-1].split('/')[0]}")
    
    engine = create_engine(db_url, pool_pre_ping=True)
    
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
    
    directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    base_time = datetime.now()
    
    with engine.begin() as conn:
        for i in range(num_readings):
            # Time goes backwards from now, 5 minutes apart
            ts = base_time - timedelta(minutes=i * 5)
            hour = ts.hour
            daily_factor = math.sin((hour / 24.0) * math.pi)
            
            params = {
                'station_id':       'WS01',
                'timestamp':        ts,
                'temperature':      round(20 + daily_factor * 10 + random.gauss(0, 1.5), 2),
                'humidity':         round(max(10, min(100, 55 + daily_factor * 15 + random.gauss(0, 4))), 2),
                'pressure':         round(1010 + random.gauss(0, 3), 2),
                'wind_speed':       round(max(0, 3 + daily_factor * 5 + random.gauss(0, 1.2)), 2),
                'wind_direction':   random.choice(directions),
                'rainfall':         round(max(0, random.choice([0, 0, 0, 0, 0.2, 0.5, 1.0])), 2),
                'soil_temperature': round(18 + daily_factor * 4 + random.gauss(0, 0.8), 2),
                'soil_moisture':    round(max(5, min(95, 55 + random.gauss(0, 8))), 2),
                'pm25':             round(max(0, 14 + random.gauss(0, 4)), 2),
                'pm10':             round(max(0, 28 + random.gauss(0, 7)), 2),
                'uv_index':         round(max(0, daily_factor * 8 + random.gauss(0, 0.5)), 2),
                'lux':              round(max(0, 200 + daily_factor * 800 + random.gauss(0, 60)), 2),
                'battery_voltage':  round(max(2.8, min(4.5, 3.9 + random.gauss(0, 0.15))), 2),
                'solar_voltage':    round(max(0, min(5.5, 2.5 + daily_factor * 2 + random.gauss(0, 0.3))), 2),
            }
            
            conn.execute(query, params)
            
            print(f"   ✅ [{i+1}/{num_readings}] {ts.strftime('%H:%M:%S')} | "
                  f"T={params['temperature']}°C, H={params['humidity']}%, "
                  f"P={params['pressure']}hPa, SM={params['soil_moisture']}%, "
                  f"Rain={params['rainfall']}mm, Wind={params['wind_speed']}m/s {params['wind_direction']}")
    
    print(f"\n🎉 Successfully inserted {num_readings} readings into weather_data!")
    print(f"   Run `python query_neon_db.py` to see all data.\n")


if __name__ == "__main__":
    seed_data(20)
