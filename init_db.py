import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

def init_db():
    print("--- Database Initialization (PostgreSQL) ---")
    
    # 1. Load environment variables
    load_dotenv()
    db_url = os.getenv("DATABASE_URL")
    
    if not db_url:
        print("ERROR: DATABASE_URL not found in .env file.")
        return

    print(f"Connecting to database: {db_url.split('@')[-1]}")

    try:
        engine = create_engine(db_url)
        
        # 2. Define schema dynamically
        schema = """
        -- Clear out existing tables to ensure a completely clean slate
        DROP TABLE IF EXISTS users CASCADE;
        DROP TABLE IF EXISTS weather_data CASCADE;
        DROP TABLE IF EXISTS installations CASCADE;
        DROP TABLE IF EXISTS installation_sensors CASCADE;
        DROP TABLE IF EXISTS alerts CASCADE;
        DROP TABLE IF EXISTS user_preferences CASCADE;
        DROP TABLE IF EXISTS trends CASCADE;
        DROP TABLE IF EXISTS system_health CASCADE;

        -- Create Users Table (used for authentication & profile)
        CREATE TABLE users (
            phone VARCHAR(20) PRIMARY KEY,
            name VARCHAR(100),
            land_size_acres FLOAT,
            location VARCHAR(200),
            crops TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Create Weather Data Table
        CREATE TABLE weather_data (
            id SERIAL PRIMARY KEY,
            station_id VARCHAR(50) NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            temperature FLOAT,
            humidity FLOAT,
            pressure FLOAT,
            wind_speed FLOAT,
            wind_direction VARCHAR(20),
            rainfall FLOAT,
            soil_temperature FLOAT,
            soil_moisture FLOAT,
            pm25 FLOAT,
            pm10 FLOAT,
            uv_index FLOAT,
            lux FLOAT,
            battery_voltage FLOAT,
            solar_voltage FLOAT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Installations Table
        CREATE TABLE installations (
            id SERIAL PRIMARY KEY,
            station_id VARCHAR(50) UNIQUE NOT NULL,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            latitude FLOAT NOT NULL,
            longitude FLOAT NOT NULL,
            location_name VARCHAR(200),
            installation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status VARCHAR(20) DEFAULT 'active',
            device_type VARCHAR(50),
            firmware_version VARCHAR(50),
            last_heartbeat TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Installation Sensors Table
        CREATE TABLE installation_sensors (
            id SERIAL PRIMARY KEY,
            installation_id INTEGER REFERENCES installations(id) ON DELETE CASCADE,
            sensor_type VARCHAR(50) NOT NULL,
            sensor_name VARCHAR(100),
            unit VARCHAR(20),
            active BOOLEAN DEFAULT TRUE
        );

        -- Alerts Table
        CREATE TABLE alerts (
            id SERIAL PRIMARY KEY,
            user_id VARCHAR(50),
            station_id VARCHAR(50) NOT NULL,
            metric VARCHAR(50),
            operator VARCHAR(10),
            threshold FLOAT,
            unit VARCHAR(20),
            active BOOLEAN DEFAULT TRUE,
            last_triggered TIMESTAMP,
            cooldown_minutes INTEGER DEFAULT 30,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- User Preferences
        CREATE TABLE user_preferences (
            id SERIAL PRIMARY KEY,
            user_id VARCHAR(50) UNIQUE NOT NULL,
            preferred_unit VARCHAR(10) DEFAULT 'C',
            verbosity VARCHAR(20) DEFAULT 'short',
            alert_channel VARCHAR(20) DEFAULT 'whatsapp',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Historical Trends Cache
        CREATE TABLE trends (
            id SERIAL PRIMARY KEY,
            station_id VARCHAR(50) NOT NULL,
            metric VARCHAR(50) NOT NULL,
            period VARCHAR(20) NOT NULL,
            trend_direction VARCHAR(20),
            trend_rate FLOAT,
            confidence FLOAT,
            start_timestamp TIMESTAMP,
            end_timestamp TIMESTAMP
        );
        
        -- System Health Table
        CREATE TABLE system_health (
            id SERIAL PRIMARY KEY,
            station_id VARCHAR(50) NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            sensor_status VARCHAR(50),
            battery_level FLOAT,
            connectivity VARCHAR(50),
            last_data_received TIMESTAMP,
            uptime_hours FLOAT
        );
        """

        # 3. Execute SQL
        print("Applying PostgreSQL Schema...")
        with engine.begin() as conn:
            conn.execute(text(schema))
            
        print("SUCCESS: Full database schema strictly initialized.")
        print("Replaced older conflicting tables and successfully mapped all resources.")
        
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    init_db()
