"""
ESP32 MQTT Sensor Data Simulator for Mumbai
Simulates realistic sensor data from an ESP32 stationed in Mumbai via MQTT → RPi → HTTP
Sends data to the backend for storage and frontend consumption
"""

import requests
import time
import random
import json
from datetime import datetime, timedelta
import threading
import sys

# Mumbai-specific climate parameters
MUMBAI_CONFIG = {
    "location": "Mumbai, India (19.0760°N, 72.8777°E)",
    "elevation": 14,  # meters
    "avg_temp": 27,  # Celsius (annual average)
    "monsoon_season": (6, 9),  # June to September
    "station_id": "WS01",
}

class MumbaiSensorSimulator:
    """Simulates realistic sensor readings for Mumbai climate"""
    
    def __init__(self, backend_url="http://localhost:8000"):
        self.backend_url = backend_url
        self.station_id = MUMBAI_CONFIG["station_id"]
        self.running = True
        self.connection_status = False
        
        # Initial conditions
        self.current_temp = 27.5
        self.current_humidity = 70
        self.current_pressure = 1013.25
        self.current_wind_speed = 5.2
        self.current_rain = 0
        self.current_soil_temp = 26.0
        self.current_soil_moisture = 55.0
        
        # Air quality baseline (Mumbai has moderate-to-high PM values)
        self.pm25 = 65.0  # µg/m³ (Mumbai average)
        self.pm10 = 120.0  # µg/m³ (Mumbai average)
        
        # Solar and UV
        self.uv_index = 3.0
        self.lux = 45000.0  # Full daylight
        
        # Power
        self.battery_voltage = 12.5  # V
        self.solar_voltage = 13.5  # V
        
        # Time tracking
        self.start_time = datetime.now()
        print(f"🌾 Mumbai Sensor Simulator initialized for {MUMBAI_CONFIG['location']}")
    
    def get_current_hour(self):
        """Get current hour of day"""
        return datetime.now().hour
    
    def get_current_month(self):
        """Get current month"""
        return datetime.now().month
    
    def simulate_temperature_variation(self):
        """
        Simulate Mumbai temperature with daily and seasonal variation
        - Morning: cooler (23-26°C)
        - Noon: hottest (30-35°C) 
        - Evening: moderate (28-32°C)
        - Night: cooler (24-28°C)
        """
        hour = self.get_current_hour()
        month = self.get_current_month()
        
        # Seasonal variation (Summer: Mar-May hotter, Winter: Nov-Jan cooler)
        if month in [3, 4, 5]:  # March to May - Hot season
            base_temp = 32.0
        elif month in [6, 7, 8, 9]:  # June to Sept - Monsoon (cooler)
            base_temp = 28.0
        elif month in [10, 11]:  # Oct-Nov - Post-monsoon (warm)
            base_temp = 30.0
        else:  # Dec-Feb - Winter (mildly cool)
            base_temp = 26.0
        
        # Diurnal variation (daily cycle)
        if 6 <= hour < 10:  # Morning heating
            temp_offset = -2.0 + (hour - 6) * 2
        elif 10 <= hour < 15:  # Peak heating
            temp_offset = 5.0 + random.uniform(-2, 3)
        elif 15 <= hour < 18:  # Afternoon cooling
            temp_offset = 4.0 - (hour - 15) * 1.5
        elif 18 <= hour < 22:  # Evening cooling
            temp_offset = 1.0 - (hour - 18) * 0.5
        else:  # Night cooling
            temp_offset = -3.0
        
        # Add random fluctuation (±1°C)
        noise = random.gauss(0, 0.5)
        self.current_temp = base_temp + temp_offset + noise
        self.current_temp = max(20, min(40, self.current_temp))  # Clamp 20-40°C
        
        return round(self.current_temp, 1)
    
    def simulate_humidity_variation(self):
        """
        Simulate Mumbai humidity with monsoon effects
        - Monsoon (Jun-Sep): 85-95% RH
        - Post-monsoon (Oct-Nov): 70-80% RH
        - Summer (Mar-May): 60-75% RH
        - Winter (Dec-Feb): 65-75% RH
        """
        month = self.get_current_month()
        hour = self.get_current_hour()
        
        # Seasonal humidity patterns
        if month in [6, 7, 8, 9]:  # Monsoon
            base_humidity = 88.0
        elif month in [10, 11]:  # Post-monsoon
            base_humidity = 75.0
        elif month in [3, 4, 5]:  # Summer (hot and dry)
            base_humidity = 65.0
        else:  # Winter
            base_humidity = 70.0
        
        # Daily variation (humidity higher at night/early morning)
        if 3 <= hour < 8:  # Early morning peak
            humidity_offset = 5.0
        elif 14 <= hour < 17:  # Afternoon low
            humidity_offset = -8.0
        else:
            humidity_offset = 0
        
        # Temperature-based inverse relationship
        temp_effect = (27 - self.current_temp) * 0.3
        
        # Add randomness
        noise = random.gauss(0, 1.5)
        self.current_humidity = base_humidity + humidity_offset + temp_effect + noise
        self.current_humidity = max(40, min(100, self.current_humidity))  # Clamp 40-100%
        
        return round(self.current_humidity, 1)
    
    def simulate_pressure_variation(self):
        """
        Simulate atmospheric pressure
        - Monsoon: Lower (1008-1012 hPa) during active phase
        - Normal: Around 1013 hPa
        - Add diurnal variation: ±1 hPa
        """
        month = self.get_current_month()
        hour = self.get_current_hour()
        
        # Seasonal variation
        if month in [6, 7, 8, 9]:  # Monsoon low pressure
            base_pressure = 1009.5
        else:
            base_pressure = 1013.25
        
        # Diurnal variation (pressure peaks at 10am and 22pm, lows at 4am and 16pm)
        if hour == 10 or hour == 22:
            pressure_offset = 0.8
        elif hour == 4 or hour == 16:
            pressure_offset = -0.8
        else:
            pressure_offset = random.uniform(-0.3, 0.3)
        
        self.current_pressure = base_pressure + pressure_offset
        return round(self.current_pressure, 2)
    
    def simulate_wind_variation(self):
        """
        Simulate wind speed with monsoon effects
        - Monsoon: Higher (8-15 m/s)
        - Normal: Lower (2-6 m/s)
        - Early morning: Calmer (1-3 m/s)
        - Afternoon: More wind (5-10 m/s)
        """
        month = self.get_current_month()
        hour = self.get_current_hour()
        
        # Seasonal wind patterns
        if month in [6, 7, 8, 9]:  # Southwest monsoon (strong)
            base_wind = 10.0
        elif month in [10, 11]:  # Post-monsoon (moderate)
            base_wind = 6.0
        else:  # Winter/Summer (weak to moderate)
            base_wind = 4.0
        
        # Diurnal variation
        if 4 <= hour < 7:  # Early morning calm
            wind_offset = -2.0
        elif 12 <= hour < 16:  # Afternoon peak
            wind_offset = 3.0
        else:
            wind_offset = 0
        
        # Random gusts
        gust = random.gauss(0, 1.5)
        self.current_wind_speed = base_wind + wind_offset + gust
        self.current_wind_speed = max(0, min(25, self.current_wind_speed))
        
        return round(self.current_wind_speed, 1)
    
    def simulate_rainfall(self):
        """
        Simulate rainfall patterns
        - Monsoon (Jun-Sep): Often rain (30-40% chance, 5-25mm per event)
        - Post-monsoon: Occasional drizzle (10% chance, 1-5mm)
        - Summer/Winter: Rare (2-5% chance)
        """
        month = self.get_current_month()
        
        if month in [6, 7, 8, 9]:  # Monsoon heavy rain
            rain_chance = 0.35
            if random.random() < rain_chance:
                return round(random.uniform(5, 25), 1)
        elif month in [10, 11]:  # Post-monsoon drizzle
            rain_chance = 0.10
            if random.random() < rain_chance:
                return round(random.uniform(1, 5), 1)
        else:  # Summer/Winter rare rain
            rain_chance = 0.03
            if random.random() < rain_chance:
                return round(random.uniform(0.5, 3), 1)
        
        return 0.0
    
    def simulate_soil_conditions(self):
        """
        Simulate soil temperature and moisture
        - Soil temp: Usually 2-3°C lower than air temp in monsoon, close in summer
        - Soil moisture: Higher in monsoon (70-85%), lower in summer (30-40%)
        """
        month = self.get_current_month()
        
        # Soil temperature (lags air temperature)
        self.current_soil_temp = self.current_temp - random.uniform(0, 2)
        self.current_soil_temp = max(15, min(35, self.current_soil_temp))
        
        # Soil moisture
        if month in [6, 7, 8, 9]:  # Monsoon
            base_moisture = 75.0
        elif month in [10, 11]:  # Post-monsoon
            base_moisture = 60.0
        else:
            base_moisture = 40.0
        
        # Add some daily variation
        moisture_variation = random.gauss(0, 5)
        self.current_soil_moisture = base_moisture + moisture_variation
        self.current_soil_moisture = max(20, min(95, self.current_soil_moisture))
        
        return round(self.current_soil_temp, 1), round(self.current_soil_moisture, 1)
    
    def simulate_air_quality(self):
        """
        Simulate PM2.5 and PM10 levels
        - Mumbai baseline: PM2.5 ~65, PM10 ~120 µg/m³
        - Higher during dry season (March-May)
        - Lower during monsoon
        - Higher during rush hours
        """
        month = self.get_current_month()
        hour = self.get_current_hour()
        
        # Seasonal variation
        if month in [3, 4, 5]:  # Pre-monsoon dust
            pm25_base = 85.0
            pm10_base = 160.0
        elif month in [6, 7, 8, 9]:  # Monsoon (cleaner)
            pm25_base = 45.0
            pm10_base = 85.0
        else:
            pm25_base = 65.0
            pm10_base = 120.0
        
        # Rush hour increase (7-9am, 5-8pm)
        if (7 <= hour <= 9) or (17 <= hour <= 20):
            rush_factor = 1.3
        else:
            rush_factor = 1.0
        
        # Daily variation
        self.pm25 = pm25_base * rush_factor + random.gauss(0, 10)
        self.pm10 = pm10_base * rush_factor + random.gauss(0, 20)
        
        self.pm25 = max(5, min(300, self.pm25))
        self.pm10 = max(10, min(400, self.pm10))
        
        return round(self.pm25, 1), round(self.pm10, 1)
    
    def simulate_solar_radiation(self):
        """
        Simulate UV index and light intensity (lux)
        - UV: 0-2 (night), ramps up morning, peaks noon (5-7), decreases evening
        - Light: 0-100 (night), ramps up, peaks ~50k lux (noon), clouds reduce by 20-40%
        """
        hour = self.get_current_hour()
        
        # UV Index
        if 6 <= hour <= 18:  # Daytime (6am to 6pm)
            time_from_noon = abs(hour - 12)
            uv_base = max(0, 7 - time_from_noon * 0.5)  # Peak at noon
            self.uv_index = uv_base + random.gauss(0, 0.3)
        else:
            self.uv_index = 0.0
        
        # Light Intensity (Lux)
        if 5 <= hour <= 19:  # Daytime
            time_from_noon = abs(hour - 12.5)
            lux_base = 50000 * max(0, 1 - (time_from_noon / 7.5) ** 2)
            
            # Clouds (monsoon season has more clouds)
            month = self.get_current_month()
            if month in [6, 7, 8, 9]:
                cloud_factor = random.uniform(0.5, 0.8)  # 20-50% reduction
            else:
                cloud_factor = random.uniform(0.7, 1.0)  # 0-30% reduction
            
            self.lux = lux_base * cloud_factor
        else:
            self.lux = 100.0 if 19 < hour < 21 or 4 < hour < 5 else 10.0  # Twilight/night
        
        self.lux = max(0, min(100000, self.lux))
        
        return round(self.uv_index, 1), round(self.lux, 0)
    
    def simulate_power_system(self):
        """
        Simulate battery and solar panel voltages
        - Solar: 10V-14V (higher during day, lower at night)
        - Battery: 11V-13V (depletes at night, charges during day)
        """
        hour = self.get_current_hour()
        
        # Solar voltage variation
        if 6 <= hour <= 18:
            solar_base = 13.0
            time_from_noon = abs(hour - 12)
            solar_variation = max(0, (1 - (time_from_noon / 6) ** 2)) * 2
            self.solar_voltage = solar_base + solar_variation
        else:
            self.solar_voltage = 10.0  # Night (no charging)
        
        # Battery voltage (depletes at night, charges during day)
        if hour < 6 or hour > 18:  # Night (discharge)
            self.battery_voltage -= 0.01 * random.random()
            self.battery_voltage = max(11.2, self.battery_voltage)
        else:  # Day (charge)
            self.battery_voltage += 0.005 * random.random()
            self.battery_voltage = min(13.5, self.battery_voltage)
        
        return round(self.solar_voltage, 2), round(self.battery_voltage, 2)
    
    def get_wind_direction(self):
        """Get wind direction based on season"""
        month = self.get_current_month()
        
        if month in [6, 7, 8, 9]:  # Monsoon
            # Southwest winds (monsoon winds)
            directions = ["SW", "WSW", "S"]
            return random.choice(directions)
        elif month in [12, 1, 2]:  # Winter
            # Northeast winds (dry season)
            directions = ["NE", "N"]
            return random.choice(directions)
        else:  # Transition seasons
            directions = ["NW", "N", "NE", "E", "SE", "S", "SW", "W"]
            return random.choice(directions)
    
    def generate_sensor_data(self):
        """Generate complete sensor data payload"""
        # Simulate all parameters
        self.simulate_temperature_variation()
        self.simulate_humidity_variation()
        self.simulate_pressure_variation()
        self.simulate_wind_variation()
        
        soil_temp, soil_moisture = self.simulate_soil_conditions()
        pm25, pm10 = self.simulate_air_quality()
        uv_index, lux = self.simulate_solar_radiation()
        solar_voltage, battery_voltage = self.simulate_power_system()
        rainfall = self.simulate_rainfall()
        wind_direction = self.get_wind_direction()
        
        # Create sensor data payload (matches the expected format in app.py)
        payload = {
            "id": self.station_id,
            "ts": int(datetime.now().timestamp()),
            "env": {
                "t": self.current_temp,
                "h": self.current_humidity,
                "p": self.current_pressure
            },
            "wind": {
                "s": self.current_wind_speed,
                "d": wind_direction
            },
            "rain": rainfall,
            "soil": {
                "t": soil_temp,
                "m": soil_moisture
            },
            "air": {
                "pm25": pm25,
                "pm10": pm10
            },
            "rad": {
                "uv": uv_index,
                "lux": lux
            },
            "pwr": {
                "bat": battery_voltage,
                "sol": solar_voltage
            }
        }
        
        return payload
    
    def send_sensor_data(self, data):
        """Send sensor data to backend"""
        try:
            response = requests.post(
                f"{self.backend_url}/api/sensors/data",
                json=data,
                timeout=5
            )
            
            if response.status_code == 200:
                self.connection_status = True
                return True, "✅ Data sent successfully"
            else:
                self.connection_status = False
                return False, f"❌ Backend error: {response.status_code}"
        
        except requests.exceptions.ConnectionError:
            self.connection_status = False
            return False, "❌ Cannot connect to backend"
        except Exception as e:
            self.connection_status = False
            return False, f"❌ Error: {str(e)}"
    
    def display_sensor_data(self, data):
        """Display sensor data in a readable format"""
        env = data["env"]
        wind = data["wind"]
        soil = data["soil"]
        air = data["air"]
        rad = data["rad"]
        pwr = data["pwr"]
        
        print("\n" + "="*70)
        print(f"📊 SENSOR DATA - {MUMBAI_CONFIG['location']}")
        print(f"⏰ Timestamp: {datetime.fromtimestamp(data['ts']).strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        print(f"🌡️  Environment:")
        print(f"   Temperature: {env['t']:.1f}°C | Humidity: {env['h']:.1f}% | Pressure: {env['p']:.2f} hPa")
        print(f"💨 Wind:")
        print(f"   Speed: {wind['s']:.1f} m/s | Direction: {wind['d']}")
        print(f"🌧️  Rainfall: {data['rain']:.1f} mm")
        print(f"🌱 Soil:")
        print(f"   Temperature: {soil['t']:.1f}°C | Moisture: {soil['m']:.1f}%")
        print(f"💨 Air Quality:")
        print(f"   PM2.5: {air['pm25']:.1f} µg/m³ | PM10: {air['pm10']:.1f} µg/m³")
        print(f"☀️  Radiation:")
        print(f"   UV Index: {rad['uv']:.1f} | Light: {rad['lux']:.0f} lux")
        print(f"🔋 Power System:")
        print(f"   Battery: {pwr['bat']:.2f}V | Solar: {pwr['sol']:.2f}V")
        print(f"📡 Backend Status: {'🟢 Connected' if self.connection_status else '🔴 Disconnected'}")
        print("="*70)
    
    def run_continuous(self, interval=30):
        """
        Run continuous sensor simulation and data sending
        
        Args:
            interval: Time between sensor readings (seconds)
        """
        print(f"🚀 Starting continuous sensor simulation (interval: {interval}s)")
        print("Press Ctrl+C to stop\n")
        
        reading_count = 0
        
        try:
            while self.running:
                reading_count += 1
                
                # Generate sensor data
                data = self.generate_sensor_data()
                
                # Display the data
                self.display_sensor_data(data)
                
                # Send to backend
                success, message = self.send_sensor_data(data)
                print(f"📤 {message}")
                print(f"📈 Total readings sent: {reading_count}\n")
                
                # Wait for next reading
                time.sleep(interval)
        
        except KeyboardInterrupt:
            print("\n\n⛔ Sensor simulation stopped by user")
            print(f"📊 Total readings sent: {reading_count}")
            self.running = False


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Mumbai ESP32 MQTT Sensor Data Simulator"
    )
    parser.add_argument(
        "--backend",
        default="http://localhost:8000",
        help="Backend URL (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=30,
        help="Sensor reading interval in seconds (default: 30)"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Send one test reading and exit"
    )
    
    args = parser.parse_args()
    
    # Initialize simulator
    simulator = MumbaiSensorSimulator(backend_url=args.backend)
    
    if args.test:
        # Send single test reading
        print("📤 Sending single test reading...")
        data = simulator.generate_sensor_data()
        simulator.display_sensor_data(data)
        success, message = simulator.send_sensor_data(data)
        print(f"📤 {message}")
    else:
        # Run continuous simulation
        simulator.run_continuous(interval=args.interval)


if __name__ == "__main__":
    main()
