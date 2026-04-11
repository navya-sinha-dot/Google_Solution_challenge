"""
Populate SQLite database with test sensor data
"""
from tools import _get_session
from sqlalchemy import text
from datetime import datetime, timedelta
import random

def insert_test_data():
    """Insert test weather data into database"""
    db = _get_session()
    
    # Insert test weather data
    now = datetime.now()
    print("Populating database with sample historical data...")
    
    for i in range(24):
        timestamp = now - timedelta(hours=i)
        temperature = random.uniform(15, 35)
        humidity = random.uniform(30, 90)
        pressure = random.uniform(1000, 1020)
        
        try:
            query = text("""
                INSERT INTO weather_data 
                (station_id, timestamp, temperature, humidity, pressure, wind_speed, rainfall)
                VALUES (:station_id, :timestamp, :temperature, :humidity, :pressure, :wind_speed, :rainfall)
            """)
            
            db.execute(query, {
                "station_id": "STATION_001",
                "timestamp": timestamp,
                "temperature": round(temperature, 2),
                "humidity": round(humidity, 2),
                "pressure": round(pressure, 2),
                "wind_speed": round(random.uniform(0, 15), 2),
                "rainfall": round(random.uniform(0, 5), 2)
            })
        except Exception as e:
            print(f"Error inserting data: {e}")
    
    db.commit()
    db.close()
    print("✅ Test data inserted successfully into the active database!")

if __name__ == "__main__":
    insert_test_data()
