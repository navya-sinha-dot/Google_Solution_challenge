"""
ESP32 MQTT Data Simulator
Generates realistic agricultural sensor data and publishes to MQTT topics
Mimics the sensor data that would come from an actual ESP32 device

Usage:
    python esp32_mqtt_simulator.py [broker] [mode]
    
    broker: MQTT broker address (default: localhost)
    mode: 'realistic' (default) or 'stress' or 'rainfall' or 'clear'
"""

import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion
import json
import time
import random
import math
import logging
import sys
from datetime import datetime, timedelta
from typing import Dict, Any

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ESP32MQTTSimulator:
    """Simulates ESP32 sensor data publishing to MQTT"""
    
    def __init__(self, broker="localhost", port=1883, station_id="SIM01"):
        """
        Initialize simulator
        
        Args:
            broker: MQTT broker address
            port: MQTT broker port
            station_id: Simulation station ID
        """
        self.broker = broker
        self.port = port
        self.station_id = station_id
        
        # MQTT client
        self.client = mqtt.Client(
            callback_api_version=CallbackAPIVersion.VERSION1,
            client_id=f"esp32_simulator_{station_id}"
        )
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        
        # The 14 topics that bridge expects
        self.topics = [
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
        ]
        
        # Realistic base values for sensor data
        self.base_values = {
            "temperature": 25.0,
            "humidity": 60.0,
            "pressure": 1013.25,
            "wind_speed": 5.0,
            "wind_direction": 180.0,
            "rainfall": 0.0,
            "soil_temperature": 20.0,
            "soil_moisture": 65.0,
            "pm25": 15.0,
            "pm10": 30.0,
            "uv_index": 5.0,
            "light_level": 500.0,
            "battery_voltage": 4.2,
            "solar_voltage": 3.8,
        }
        
        # Time tracking for sine wave variations
        self.time_offset = 0
    
    def on_connect(self, client, userdata, flags, rc):
        """MQTT callback - on connection"""
        if rc == 0:
            logger.info(f"✅ Connected to MQTT broker at {self.broker}:{self.port}")
            logger.info(f"🌾 Simulating {self.station_id} sensor data")
        else:
            logger.error(f"❌ Failed to connect (rc={rc})")
    
    def on_disconnect(self, client, userdata, rc):
        """MQTT callback - on disconnect"""
        if rc != 0:
            logger.warning(f"⚠️  Unexpected disconnect (rc={rc})")
        else:
            logger.info("Simulator stopped")
    
    def generate_realistic_data(self, mode="realistic") -> Dict[str, Any]:
        """
        Generate realistic sensor data with daily and hourly variations
        
        Args:
            mode: 'realistic', 'stress', 'rainfall', or 'clear'
        
        Returns:
            Dict with sensor values
        """
        now = datetime.now()
        hour = now.hour
        minute = now.minute
        
        # Time of day variation (0 to 1, peak at noon)
        time_of_day = (hour + minute/60) / 24.0
        daily_factor = math.sin(time_of_day * math.pi)  # 0 to 1 to 0
        
        # Random noise
        noise = lambda base, variation: base + random.gauss(0, variation)
        
        data = {}
        
        if mode == "realistic":
            # Normal agricultural conditions
            data["temperature"] = 15 + daily_factor * 10 + random.gauss(0, 1)
            data["humidity"] = 50 + daily_factor * 20 + random.gauss(0, 3)
            data["pressure"] = 1013.25 + random.gauss(0, 2)
            data["wind_speed"] = 3 + daily_factor * 5 + random.gauss(0, 1)
            data["wind_direction"] = random.uniform(0, 360)
            data["rainfall"] = random.choice([0, 0, 0, 0.2, 0.5])  # Occasional rain
            data["soil_temperature"] = 18 + daily_factor * 5 + random.gauss(0, 0.5)
            data["soil_moisture"] = 60 + random.gauss(0, 5)
            data["pm25"] = 12 + random.gauss(0, 3)
            data["pm10"] = 25 + random.gauss(0, 5)
            data["uv_index"] = max(0, daily_factor * 10 + random.gauss(0, 0.5))
            data["light_level"] = 300 + daily_factor * 700 + random.gauss(0, 50)
            data["battery_voltage"] = 4.0 + random.gauss(0, 0.1)
            data["solar_voltage"] = 2.0 + daily_factor * 2 + random.gauss(0, 0.2)
        
        elif mode == "stress":
            # Plant stress conditions (high temp, low moisture)
            data["temperature"] = 35 + random.gauss(0, 2)
            data["humidity"] = 20 + random.gauss(0, 3)
            data["pressure"] = 1013.25 + random.gauss(0, 2)
            data["wind_speed"] = 8 + random.gauss(0, 1)
            data["wind_direction"] = random.uniform(0, 360)
            data["rainfall"] = 0
            data["soil_temperature"] = 30 + random.gauss(0, 1)
            data["soil_moisture"] = 25 + random.gauss(0, 3)  # CRITICAL LOW
            data["pm25"] = 30 + random.gauss(0, 5)
            data["pm10"] = 60 + random.gauss(0, 10)
            data["uv_index"] = 10 + random.gauss(0, 0.5)
            data["light_level"] = 1000 + random.gauss(0, 50)
            data["battery_voltage"] = 3.7 + random.gauss(0, 0.1)
            data["solar_voltage"] = 3.5 + random.gauss(0, 0.2)
        
        elif mode == "rainfall":
            # Heavy rainfall conditions
            data["temperature"] = 18 + random.gauss(0, 1)
            data["humidity"] = 85 + random.gauss(0, 3)
            data["pressure"] = 1008 + random.gauss(0, 2)
            data["wind_speed"] = 12 + random.gauss(0, 2)
            data["wind_direction"] = random.uniform(0, 360)
            data["rainfall"] = 5.0 + random.gauss(0, 1)  # HEAVY RAIN
            data["soil_temperature"] = 16 + random.gauss(0, 0.5)
            data["soil_moisture"] = 85 + random.gauss(0, 3)  # HIGH
            data["pm25"] = 5 + random.gauss(0, 1)
            data["pm10"] = 10 + random.gauss(0, 2)
            data["uv_index"] = 1 + random.gauss(0, 0.2)
            data["light_level"] = 100 + random.gauss(0, 20)
            data["battery_voltage"] = 4.1 + random.gauss(0, 0.1)
            data["solar_voltage"] = 0.5 + random.gauss(0, 0.1)
        
        elif mode == "clear":
            # Clear, perfect weather
            data["temperature"] = 25 + random.gauss(0, 0.5)
            data["humidity"] = 55 + random.gauss(0, 2)
            data["pressure"] = 1013.25 + random.gauss(0, 1)
            data["wind_speed"] = 2 + random.gauss(0, 0.5)
            data["wind_direction"] = random.uniform(0, 360)
            data["rainfall"] = 0
            data["soil_temperature"] = 22 + random.gauss(0, 0.5)
            data["soil_moisture"] = 70 + random.gauss(0, 2)
            data["pm25"] = 8 + random.gauss(0, 1)
            data["pm10"] = 15 + random.gauss(0, 2)
            data["uv_index"] = 6 + random.gauss(0, 0.5)
            data["light_level"] = 600 + random.gauss(0, 30)
            data["battery_voltage"] = 4.2 + random.gauss(0, 0.05)
            data["solar_voltage"] = 4.0 + random.gauss(0, 0.1)
        
        # Ensure reasonable bounds
        data["temperature"] = max(-10, min(50, data["temperature"]))
        data["humidity"] = max(0, min(100, data["humidity"]))
        data["soil_moisture"] = max(0, min(100, data["soil_moisture"]))
        data["wind_speed"] = max(0, data["wind_speed"])
        data["rainfall"] = max(0, data["rainfall"])
        data["pm25"] = max(0, data["pm25"])
        data["pm10"] = max(0, data["pm10"])
        data["uv_index"] = max(0, data["uv_index"])
        data["light_level"] = max(0, data["light_level"])
        data["battery_voltage"] = max(2.5, min(4.5, data["battery_voltage"]))
        data["solar_voltage"] = max(0, min(5, data["solar_voltage"]))
        
        return data
    
    def publish_data(self, mode="realistic", interval=5):
        """
        Start publishing simulated sensor data
        
        Args:
            mode: 'realistic', 'stress', 'rainfall', or 'clear'
            interval: Publishing interval in seconds
        """
        try:
            self.client.connect(self.broker, self.port, keepalive=60)
            self.client.loop_start()
            
            logger.info(f"🚀 Publishing {mode} sensor data every {interval}s")
            logger.info("Press Ctrl+C to stop\n")
            
            publish_count = 0
            try:
                while True:
                    # Generate data for this cycle
                    data = self.generate_realistic_data(mode=mode)
                    
                    # Method 1: Publish each sensor value to individual topics
                    for sensor_name, value in data.items():
                        topic = f"farm/sensors/{sensor_name}"
                        payload = json.dumps({
                            "value": round(value, 2),
                            "station": self.station_id,
                            "timestamp": datetime.now().isoformat(),
                            "unit": self._get_unit(sensor_name)
                        })
                        
                        self.client.publish(topic, payload, qos=1)
                        publish_count += 1
                    
                    # Method 2: Also publish complete sensor reading in structured format
                    # This ensures the bridge gets all data in one shot
                    complete_reading = {
                        "id": self.station_id,
                        "ts": int(time.time()),
                        "env": {
                            "t": round(data["temperature"], 2),
                            "h": round(data["humidity"], 2),
                            "p": round(data["pressure"], 2)
                        },
                        "wind": {
                            "s": round(data["wind_speed"], 2),
                            "d": str(round(data["wind_direction"], 1))
                        },
                        "rain": round(data["rainfall"], 2),
                        "soil": {
                            "t": round(data["soil_temperature"], 2),
                            "m": round(data["soil_moisture"], 2)
                        },
                        "air": {
                            "pm25": round(data["pm25"], 2),
                            "pm10": round(data["pm10"], 2)
                        },
                        "rad": {
                            "uv": round(data["uv_index"], 2),
                            "lux": round(data["light_level"], 2)
                        },
                        "pwr": {
                            "bat": round(data["battery_voltage"], 2),
                            "sol": round(data["solar_voltage"], 2)
                        }
                    }
                    
                    # Publish complete reading to special topic
                    self.client.publish(
                        "farm/sensors/complete",
                        json.dumps(complete_reading),
                        qos=1
                    )
                    
                    # Log summary
                    temp = data["temperature"]
                    humidity = data["humidity"]
                    soil_moisture = data["soil_moisture"]
                    rainfall = data["rainfall"]
                    pressure = data["pressure"]
                    wind_speed = data["wind_speed"]
                    pm25 = data["pm25"]
                    soil_temp = data["soil_temperature"]
                    
                    logger.info(
                        f"📊 Cycle {publish_count//14} | "
                        f"🌡️ {temp:.1f}°C | "
                        f"💧 {humidity:.0f}% | "
                        f"🌱 {soil_moisture:.0f}% | "
                        f"🌧️ {rainfall:.2f}mm | "
                        f"💨 {wind_speed:.1f}m/s | "
                        f"💨 P={pressure:.1f}hPa | "
                        f"🌱 ST={soil_temp:.1f}°C | "
                        f"✨ PM2.5={pm25:.0f}µg"
                    )
                    
                    time.sleep(interval)
            
            except KeyboardInterrupt:
                logger.info("\n⏹️  Stopping simulator...")
        
        finally:
            self.client.loop_stop()
            self.client.disconnect()
    
    @staticmethod
    def _get_unit(sensor_name: str) -> str:
        """Get unit for sensor value"""
        units = {
            "temperature": "°C",
            "humidity": "%",
            "pressure": "hPa",
            "wind_speed": "m/s",
            "wind_direction": "°",
            "rainfall": "mm",
            "soil_temperature": "°C",
            "soil_moisture": "%",
            "pm25": "µg/m³",
            "pm10": "µg/m³",
            "uv_index": "index",
            "light_level": "lux",
            "battery_voltage": "V",
            "solar_voltage": "V",
        }
        return units.get(sensor_name, "")


def main():
    """CLI entry point"""
    broker = sys.argv[1] if len(sys.argv) > 1 else "localhost"
    mode = sys.argv[2] if len(sys.argv) > 2 else "realistic"
    
    if mode not in ["realistic", "stress", "rainfall", "clear"]:
        print(f"❌ Unknown mode: {mode}")
        print("   Valid modes: realistic, stress, rainfall, clear")
        sys.exit(1)
    
    simulator = ESP32MQTTSimulator(broker=broker)
    simulator.publish_data(mode=mode, interval=5)


if __name__ == "__main__":
    main()
