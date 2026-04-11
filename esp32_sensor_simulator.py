#!/usr/bin/env python3
"""
ESP32 Sensor Data Simulator
Publishes realistic agricultural sensor data to MQTT broker
"""

import json
import time
import random
from datetime import datetime
from paho.mqtt.client import Client, CallbackAPIVersion

# Configuration
BROKER_HOST = "10.186.37.61"
BROKER_PORT = 1883
TOPIC = "farm/sensors/complete"
STATION_ID = "ESP32_01"
PUBLISH_INTERVAL = 6  # seconds

# Base sensor values (with random variation)
BASE_TEMPERATURE = 28.0  # °C
BASE_HUMIDITY = 65.0  # %
BASE_PRESSURE = 1013.25  # hPa
BASE_WIND_SPEED = 4.5  # m/s
BASE_WIND_DIRECTION = 180.0  # degrees (0-360)
BASE_RAINFALL = 0.0  # mm
BASE_SOIL_TEMP = 22.0  # °C
BASE_SOIL_MOISTURE = 45.0  # %
BASE_PM25 = 0.8  # µg/m³
BASE_PM10 = 1.2  # µg/m³
BASE_LIGHT_LEVEL = 15.0  # lux
BASE_UV_INDEX = 0.6  # UV index
BASE_BATTERY_VOLTAGE = 4.0  # V
BASE_SOLAR_VOLTAGE = 2.1  # V


class ESP32Simulator:
    def __init__(self, broker_host, broker_port, station_id):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.station_id = station_id
        self.client = Client(callback_api_version=CallbackAPIVersion.VERSION1)
        self.connected = False
        
        # Setup callbacks
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_publish = self.on_publish
    
    def on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            self.connected = True
            print(f"[OK] Connected to MQTT broker {self.broker_host}:{self.broker_port}")
        else:
            print(f"[ERROR] Connection failed with code {rc}")
    
    def on_disconnect(self, client, userdata, rc, properties=None):
        self.connected = False
        if rc != 0:
            print(f"[ERROR] Unexpected disconnection with code {rc}")
    
    def on_publish(self, client, userdata, mid):
        pass  # Silently acknowledge
    
    def generate_sensor_data(self):
        """Generate sensor data - exact format from earlier ESP32 publisher"""
        # Slight variations to simulate real environment
        temp_var = random.gauss(0, 0.5)
        humidity_var = random.gauss(0, 2)
        wind_speed_var = random.uniform(5.5, 7.5)
        wind_dir_var = random.uniform(310, 320)
        soil_temp_var = random.gauss(22.64, 0.3)
        
        # Occasional rainfall
        rainfall = 0.5 if random.random() < 0.15 else 0.0
        
        sensor_data = {
            "environment": {
                "temperature": 0,  # Not sending from remote publisher
                "humidity": 0,     # Not sending from remote publisher
                "pressure": 0      # Not sending from remote publisher
            },
            "wind": {
                "speed": round(wind_speed_var, 2),
                "direction": round(wind_dir_var, 1)
            },
            "rainfall": round(rainfall, 2),
            "soil": {
                "temperature": round(soil_temp_var, 2),
                "moisture": 0.0
            },
            "air_quality": {
                "pm25": round(0.79 + random.gauss(0, 0.15), 2),
                "pm10": round(1.19 + random.gauss(0, 0.2), 2)
            },
            "radiation": {
                "light_level": round(11.67 + random.gauss(0, 1), 2),
                "uv_index": round(0.65 + random.gauss(0, 0.1), 2)
            },
            "power": {
                "battery_voltage": round(4.05 + random.gauss(0, 0.08), 2),
                "solar_voltage": round(2.11 + random.gauss(0, 0.1), 2)
            },
            "id": self.station_id,
            "timestamp": int(time.time())
        }
        
        return sensor_data
    
    def connect(self):
        """Connect to MQTT broker"""
        try:
            print(f"[*] Connecting to {self.broker_host}:{self.broker_port}...")
            self.client.connect(self.broker_host, self.broker_port, keepalive=60)
            self.client.loop_start()
            time.sleep(1)  # Wait for connection callback
        except Exception as e:
            print(f"[ERROR] Failed to connect: {e}")
            return False
        return self.connected
    
    def publish_data(self):
        """Publish sensor data to MQTT"""
        if not self.connected:
            print("[ERROR] Not connected to MQTT broker")
            return False
        
        sensor_data = self.generate_sensor_data()
        payload = json.dumps(sensor_data)
        
        try:
            result = self.client.publish(TOPIC, payload, qos=1)
            if result.rc == 0:
                timestamp = datetime.fromtimestamp(sensor_data['timestamp']).strftime('%H:%M:%S')
                print(f"[OK] {timestamp} | Wind: {sensor_data['wind']['speed']}m/s | "
                      f"Rainfall: {sensor_data['rainfall']}mm | "
                      f"SoilTemp: {sensor_data['soil']['temperature']}°C | "
                      f"Battery: {sensor_data['power']['battery_voltage']}V")
                return True
            else:
                print(f"[ERROR] Publish failed with code {result.rc}")
                return False
        except Exception as e:
            print(f"[ERROR] Failed to publish: {e}")
            return False
    
    def run(self, duration=None):
        """Run the simulator continuously"""
        if not self.connect():
            return False
        
        print(f"\n[*] Starting ESP32 simulator - publishing to {TOPIC} every {PUBLISH_INTERVAL}s")
        print("[*] Press Ctrl+C to stop\n")
        
        try:
            start_time = time.time()
            while True:
                if duration and (time.time() - start_time) > duration:
                    break
                
                self.publish_data()
                time.sleep(PUBLISH_INTERVAL)
        
        except KeyboardInterrupt:
            print("\n[*] Stopping simulator...")
        finally:
            self.client.loop_stop()
            self.client.disconnect()
            print("[OK] Disconnected")
        
        return True


if __name__ == "__main__":
    simulator = ESP32Simulator(BROKER_HOST, BROKER_PORT, STATION_ID)
    simulator.run()
