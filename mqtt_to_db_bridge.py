"""
Lightweight MQTT-to-Database Bridge
Subscribes to MQTT broker, receives sensor data, stores directly to Neon PostgreSQL.
No FPGA, no LLM — pure data pipeline: MQTT -> PostgreSQL -> Dashboard

Usage:
    python mqtt_to_db_bridge.py [broker_ip] [port]
"""

import os
import sys
import json
import time
import logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Force UTF-8 for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("mqtt_bridge")

import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import threading

# ── Configuration ──
STATION_ID = "WS01"
MQTT_TOPICS = [
    "farm/sensors/temperature",
    "farm/sensors/humidity",
    "farm/sensors/pressure",
    "farm/sensors/wind_speed",
    "farm/sensors/wind_direction",
    "farm/sensors/rainfall",
    "farm/sensors/soil_temperature",
    "farm/sensors/soil_moisture",
    "farm/sensors/pm25",
    "farm/sensors/pm10",
    "farm/sensors/uv_index",
    "farm/sensors/light_level",
    "farm/sensors/battery_voltage",
    "farm/sensors/solar_voltage",
    "farm/sensors/complete",
]

# ── Database ──
_engine = None
_SessionLocal = None

def get_db_session():
    global _engine, _SessionLocal
    if _engine is None:
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            logger.error("DATABASE_URL not set in .env!")
            return None
        if "sslmode" not in db_url:
            db_url += ("&" if "?" in db_url else "?") + "sslmode=require"
        logger.info(f"Connecting to DB: {db_url.split('@')[-1].split('/')[0]}")
        _engine = create_engine(db_url, pool_pre_ping=True, pool_size=3)
        _SessionLocal = sessionmaker(bind=_engine)
    return _SessionLocal()


class MQTTSensorBridge:
    def __init__(self, broker, port=1883):
        self.broker = broker
        self.port = port
        self.lock = threading.Lock()
        self.msg_count = 0
        self.db_writes = 0
        self.last_store_time = 0
        self.min_interval = 8  # seconds between DB writes
        
        # Accumulate individual topic data here
        self.sensor_data = {
            "temperature": None,
            "humidity": None,
            "pressure": None,
            "wind_speed": None,
            "wind_direction": None,
            "rainfall": None,
            "soil_temperature": None,
            "soil_moisture": None,
            "pm25": None,
            "pm10": None,
            "uv_index": None,
            "light_level": None,
            "battery_voltage": None,
            "solar_voltage": None,
        }
        
        # MQTT client
        self.client = mqtt.Client(
            callback_api_version=CallbackAPIVersion.VERSION2,
            client_id=f"agri_bridge_{int(time.time())}"
        )
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect

    def on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            logger.info(f"CONNECTED to MQTT broker at {self.broker}:{self.port}")
            for topic in MQTT_TOPICS:
                client.subscribe(topic, qos=1)
                logger.info(f"  Subscribed: {topic}")
        else:
            logger.error(f"MQTT connection failed (rc={rc})")

    def on_disconnect(self, client, userdata, flags, rc, properties=None):
        if rc != 0:
            logger.warning(f"Unexpected MQTT disconnect (rc={rc}), will auto-reconnect")

    def on_message(self, client, userdata, msg):
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode())
            self.msg_count += 1
            
            # Handle complete sensor reading (all-in-one JSON)
            if topic == "farm/sensors/complete":
                logger.info(f"[MSG #{self.msg_count}] Complete reading received")
                self.handle_complete_reading(payload)
                return
            
            # Handle individual sensor topics
            sensor_name = topic.split("/")[-1]  # e.g. "temperature"
            value = payload.get("value", payload) if isinstance(payload, dict) else payload
            
            with self.lock:
                self.sensor_data[sensor_name] = value
            
            logger.debug(f"[MSG #{self.msg_count}] {sensor_name} = {value}")
            
            # Check if we have enough data to store
            self.try_store()
            
        except Exception as e:
            logger.error(f"Error processing message on {msg.topic}: {e}")

    def handle_complete_reading(self, data):
        """Handle a complete sensor reading from farm/sensors/complete topic"""
        try:
            reading = {
                "station_id": data.get("id", STATION_ID),
                "timestamp": datetime.fromtimestamp(data.get("ts", time.time())),
                "temperature": data.get("env", {}).get("t"),
                "humidity": data.get("env", {}).get("h"),
                "pressure": data.get("env", {}).get("p"),
                "wind_speed": data.get("wind", {}).get("s"),
                "wind_direction": str(data.get("wind", {}).get("d", "N")),
                "rainfall": data.get("rain", 0),
                "soil_temperature": data.get("soil", {}).get("t"),
                "soil_moisture": data.get("soil", {}).get("m"),
                "pm25": data.get("air", {}).get("pm25"),
                "pm10": data.get("air", {}).get("pm10"),
                "uv_index": data.get("rad", {}).get("uv"),
                "lux": data.get("rad", {}).get("lux"),
                "battery_voltage": data.get("pwr", {}).get("bat"),
                "solar_voltage": data.get("pwr", {}).get("sol"),
            }
            self.store_reading(reading)
        except Exception as e:
            logger.error(f"Error handling complete reading: {e}")

    def try_store(self):
        """Try to store accumulated individual-topic data if enough time has passed"""
        now = time.time()
        if (now - self.last_store_time) < self.min_interval:
            return
        
        with self.lock:
            # Need at least temperature and humidity
            if self.sensor_data["temperature"] is None or self.sensor_data["humidity"] is None:
                return
            
            reading = {
                "station_id": STATION_ID,
                "timestamp": datetime.now(),
                "temperature": self.sensor_data["temperature"],
                "humidity": self.sensor_data["humidity"],
                "pressure": self.sensor_data.get("pressure"),
                "wind_speed": self.sensor_data.get("wind_speed"),
                "wind_direction": str(self.sensor_data.get("wind_direction", "N")),
                "rainfall": self.sensor_data.get("rainfall", 0),
                "soil_temperature": self.sensor_data.get("soil_temperature"),
                "soil_moisture": self.sensor_data.get("soil_moisture"),
                "pm25": self.sensor_data.get("pm25"),
                "pm10": self.sensor_data.get("pm10"),
                "uv_index": self.sensor_data.get("uv_index"),
                "lux": self.sensor_data.get("light_level"),
                "battery_voltage": self.sensor_data.get("battery_voltage"),
                "solar_voltage": self.sensor_data.get("solar_voltage"),
            }
            
            # Reset for next batch
            for key in self.sensor_data:
                self.sensor_data[key] = None
        
        self.store_reading(reading)

    def store_reading(self, reading):
        """Write a sensor reading to PostgreSQL"""
        db = get_db_session()
        if not db:
            logger.error("No database session available!")
            return
        
        try:
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
            
            db.execute(query, reading)
            db.commit()
            self.db_writes += 1
            self.last_store_time = time.time()
            
            t = reading.get('temperature', '?')
            h = reading.get('humidity', '?')
            sm = reading.get('soil_moisture', '?')
            r = reading.get('rainfall', '?')
            logger.info(
                f"DB STORED #{self.db_writes} | "
                f"T={t}C H={h}% SM={sm}% Rain={r}mm | "
                f"Station={reading['station_id']}"
            )
            
        except Exception as e:
            logger.error(f"DB write failed: {e}")
            db.rollback()
        finally:
            db.close()

    def start(self):
        logger.info("=" * 60)
        logger.info("  MQTT -> PostgreSQL Bridge")
        logger.info("=" * 60)
        logger.info(f"  Broker:  {self.broker}:{self.port}")
        logger.info(f"  Station: {STATION_ID}")
        logger.info(f"  Topics:  {len(MQTT_TOPICS)} sensor topics")
        logger.info("=" * 60)
        
        try:
            self.client.connect(self.broker, self.port, keepalive=60)
            logger.info("MQTT connection initiated, waiting for messages...")
            self.client.loop_forever()
        except ConnectionRefusedError:
            logger.error(f"MQTT broker refused connection at {self.broker}:{self.port}")
        except KeyboardInterrupt:
            logger.info("Bridge stopped by user")
        except Exception as e:
            logger.error(f"Bridge error: {e}")
        finally:
            self.client.disconnect()


def main():
    broker = sys.argv[1] if len(sys.argv) > 1 else "10.145.110.61"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 1883
    
    bridge = MQTTSensorBridge(broker=broker, port=port)
    bridge.start()


if __name__ == "__main__":
    main()
