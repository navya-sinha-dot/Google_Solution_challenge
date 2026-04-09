-- SQLite Schema for Agricultural IOT System
-- Compatible with SQLite (not PostgreSQL)

-- Weather Data Table
CREATE TABLE IF NOT EXISTS weather_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    station_id TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    temperature REAL,
    humidity REAL,
    pressure REAL,
    wind_speed REAL,
    wind_direction TEXT,
    rainfall REAL,
    soil_temperature REAL,
    soil_moisture REAL,
    pm25 REAL,
    pm10 REAL,
    uv_index REAL,
    lux REAL,
    battery_voltage REAL,
    solar_voltage REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Installations Table
CREATE TABLE IF NOT EXISTS installations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    station_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    location_name TEXT,
    installation_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'active',
    device_type TEXT,
    firmware_version TEXT,
    last_heartbeat DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Installation Sensors Table
CREATE TABLE IF NOT EXISTS installation_sensors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    installation_id INTEGER NOT NULL,
    sensor_type TEXT NOT NULL,
    sensor_name TEXT,
    unit TEXT,
    active INTEGER DEFAULT 1,
    FOREIGN KEY (installation_id) REFERENCES installations(id)
);

-- Alerts Table
CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    station_id TEXT NOT NULL,
    alert_type TEXT,
    severity TEXT,
    message TEXT,
    value REAL,
    threshold REAL,
    acknowledged INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    acknowledged_at DATETIME
);

-- User Preferences
CREATE TABLE IF NOT EXISTS user_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT UNIQUE NOT NULL,
    preferred_unit TEXT DEFAULT 'C',
    verbosity TEXT DEFAULT 'short',
    alert_channel TEXT DEFAULT 'whatsapp',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Historical Trends Cache
CREATE TABLE IF NOT EXISTS historical_trends (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    station_id TEXT NOT NULL,
    date DATE NOT NULL,
    avg_temperature REAL,
    max_temperature REAL,
    min_temperature REAL,
    total_rainfall REAL,
    avg_humidity REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(station_id, date)
);

-- Create Indexes for Performance
CREATE INDEX IF NOT EXISTS idx_weather_data_station_id ON weather_data(station_id);
CREATE INDEX IF NOT EXISTS idx_weather_data_timestamp ON weather_data(timestamp);
CREATE INDEX IF NOT EXISTS idx_installations_station_id ON installations(station_id);
CREATE INDEX IF NOT EXISTS idx_installations_status ON installations(status);
CREATE INDEX IF NOT EXISTS idx_installations_location ON installations(latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_alerts_station_id ON alerts(station_id);
CREATE INDEX IF NOT EXISTS idx_alerts_created_at ON alerts(created_at);
