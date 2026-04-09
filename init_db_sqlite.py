import sqlite3
from datetime import datetime, timedelta
import random

# Use the sensor_data.db that already exists
conn = sqlite3.connect('sensor_data.db')
cursor = conn.cursor()

print("Initializing database schema...")

# Read and execute schema
with open('schema_sqlite.sql', 'r') as f:
    schema = f.read()
    cursor.executescript(schema)

print("✓ Schema created")

# Add sample data for the last 24 hours
print("Adding sample historical data...")
base_time = datetime.now()
station_id = 'WS01'

for i in range(24):
    timestamp = base_time - timedelta(hours=i)
    temp = 22 + 5 * random.random()
    humidity = 60 + 10 * random.random()
    rainfall = random.choice([0, 0, 0, 0.5, 1.0]) # 80% chance no rain
    
    cursor.execute("""
        INSERT INTO weather_data 
        (station_id, timestamp, temperature, humidity, pressure, wind_speed, 
         wind_direction, rainfall, soil_temperature, soil_moisture, pm25, pm10, 
         uv_index, lux, battery_voltage, solar_voltage)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        station_id,
        timestamp.isoformat(),
        temp,
        humidity,
        1013.25,
        3 + random.random(),
        'NE',
        rainfall,
        18 + 3 * random.random(),
        45 + 20 * random.random(),
        15 + 5 * random.random(),
        25 + 10 * random.random(),
        3.5,
        12000,
        4.2,
        5.0
    ))

conn.commit()
cursor.execute("SELECT COUNT(*) FROM weather_data")
count = cursor.fetchone()[0]
print(f"✓ Database initialized with {count} records")
conn.close()
