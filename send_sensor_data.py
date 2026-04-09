"""
Populate SQLite database with test sensor data
"""
import sqlite3
from datetime import datetime, timedelta
import random

DATABASE_PATH = "sensor_data.db"

def insert_test_data():
    """Insert test weather data into database"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Insert test weather data
    now = datetime.now()
    for i in range(24):
        timestamp = now - timedelta(hours=i)
        temperature = random.uniform(15, 35)
        humidity = random.uniform(30, 90)
        pressure = random.uniform(1000, 1020)
        
        try:
            cursor.execute("""
                INSERT INTO weather_data 
                (station_id, timestamp, temperature, humidity, pressure, wind_speed, rainfall)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                "STATION_001",
                timestamp.isoformat(),
                round(temperature, 2),
                round(humidity, 2),
                round(pressure, 2),
                round(random.uniform(0, 15), 2),
                round(random.uniform(0, 5), 2)
            ))
        except Exception as e:
            print(f"Error inserting data: {e}")
    
    conn.commit()
    conn.close()
    print("✅ Test data inserted successfully!")
    print(f"Database: {DATABASE_PATH}")

if __name__ == "__main__":
    insert_test_data()
