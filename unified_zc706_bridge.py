"""
Unified MQTT + FPGA Accelerator + Backend Bridge
Runs on ZC706 SoC - listens to ESP32 MQTT, processes via accelerators, stores in backend

Architecture:
ESP32 --MQTT--> ZC706 (this script) --FPGA Accelerators--> AI Decision Engine --HTTP--> Backend DB --> Frontend
"""

import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion
import json
import requests
import time
import logging
from datetime import datetime
from typing import Dict, Any
from threading import RLock, Thread
import sys
import os
from dotenv import load_dotenv
from twilio.rest import Client

load_dotenv()
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class UnifiedZC706Bridge:
    def __init__(self, 
                 mqtt_broker="localhost",
                 mqtt_port=1883,
                 backend_url="http://localhost:8000/api/sensors/ingest",
                 station_id="WS01",
                 fpga_enabled=True,
                 fpga_port="COM4"):
        """
        Unified bridge for ZC706 FPGA acceleration + MQTT + Backend storage
        
        Architecture:
        - Listen to ESP32 sensor data via MQTT
        - Process through ZC706 FPGA accelerators (Sensor Fusion + Rain Prediction)
        - Make agricultural decisions
        - Store results in backend database
        
        Args:
            mqtt_broker: MQTT broker address (on ZC706 or external)
            mqtt_port: MQTT broker port
            backend_url: FastAPI backend ingest endpoint
            station_id: Station ID for this sensor collection
            fpga_enabled: Enable FPGA acceleration
            fpga_port: Serial port for FPGA (e.g., COM4, /dev/ttyUSB0)
        """
        self.mqtt_broker = mqtt_broker
        self.mqtt_port = mqtt_port
        self.backend_url = backend_url
        self.station_id = station_id
        self.fpga_enabled = fpga_enabled
        self.fpga_port = fpga_port
        
        # Initialize FPGA bridge
        self.fpga_bridge = None
        if fpga_enabled:
            try:
                from fpga_dual_bridge import DualAcceleratorBridge
                self.fpga_bridge = DualAcceleratorBridge(port=fpga_port, simulation=False)
                logger.info(f"✅ FPGA Bridge initialized on {fpga_port}")
            except Exception as e:
                logger.warning(f"⚠️  FPGA Bridge not available: {e}")
                self.fpga_bridge = None
        
        # Initialize decision engine
        try:
            from decision_engine_dual import AgriculturalDecisionAgent
            # Pass the fpga_bridge to the decision engine so it doesn't try to create its own
            self.decision_agent = AgriculturalDecisionAgent(fpga_bridge=self.fpga_bridge)
            logger.info("✅ Decision Engine initialized")
        except Exception as e:
            logger.warning(f"⚠️  Decision Engine not available: {e}")
            self.decision_agent = None
        
        # Initialize LLM Agent (for natural language reasoning with accelerator data)
        try:
            from llm_accelerator_agent import LLMAcceleratorAgent
            self.llm_agent = LLMAcceleratorAgent()
            logger.info("✅ LLM Accelerator Agent initialized (Groq Llama-3.1)")
        except Exception as e:
            logger.warning(f"⚠️  LLM Agent not available: {e}")
            self.llm_agent = None
        
        # Initialize Twilio WhatsApp client for alerts
        self.twilio_client = None
        self.twilio_enabled = False
        self.twilio_number = None
        self.alert_recipient = None
        self.init_twilio()
        
        # Track alert timestamps to prevent spam
        self.last_stress_alert_time = 0
        self.last_rain_alert_time = 0
        self.last_critical_alert_time = 0
        self.last_clear_alert_time = 0
        self.alert_throttle_seconds = 600  # 10 minutes minimum between same alert type
        
        # Sensor data buffer
        self.sensor_data_lock = RLock()  # Use RLock to allow recursive locking
        self.sensor_data = {
            "env": {},
            "wind": {},
            "soil": {},
            "air": {},
            "rad": {},
            "pwr": {},
            "rain": 0.0
        }
        self.last_update_time = time.time()
        self.last_backend_send_time = 0
        self.min_send_interval = 2  # seconds - minimum between backend sends (reduced for testing)
        
        # MQTT client
        self.client = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION1)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        
    def on_connect(self, client, userdata, flags, rc):
        """Called when connected to MQTT broker"""
        if rc == 0:
            logger.info(f"✅ Connected to MQTT broker at {self.mqtt_broker}:{self.mqtt_port}")
            
            # Subscribe to all sensor topics
            topics = [
                ("farm/sensors/temperature", 1),
                ("farm/sensors/humidity", 1),
                ("farm/sensors/pressure", 1),
                ("farm/sensors/wind_speed", 1),
                ("farm/sensors/wind_direction", 1),
                ("farm/sensors/rainfall", 1),
                ("farm/sensors/soil_temperature", 1),
                ("farm/sensors/soil_moisture", 1),
                ("farm/sensors/pm25", 1),
                ("farm/sensors/pm10", 1),
                ("farm/sensors/uv_index", 1),
                ("farm/sensors/light_level", 1),
                ("farm/sensors/battery_voltage", 1),
                ("farm/sensors/solar_voltage", 1),
                ("farm/sensors/complete", 1),  # Complete sensor reading
            ]
            
            for topic, qos in topics:
                client.subscribe(topic, qos)
                logger.info(f"📡 Subscribed to {topic}")
        else:
            logger.error(f"❌ Failed to connect to MQTT broker (rc={rc})")
    
    def on_message(self, client, userdata, msg):
        """Called when message received from MQTT"""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            
            # Handle complete sensor reading (fast path)
            if topic == "farm/sensors/complete":
                try:
                    complete_reading = json.loads(payload)
                    logger.info(f"📥 MQTT: Complete reading received from {complete_reading.get('id', 'UNKNOWN')}")
                    
                    with self.sensor_data_lock:
                        # Map actual MQTT format to internal schema
                        # MQTT sends: environment, wind, rainfall, soil, air_quality, radiation, power
                        self.sensor_data = {
                            "env": {
                                "t": complete_reading.get("environment", {}).get("temperature", 0),
                                "h": complete_reading.get("environment", {}).get("humidity", 0),
                                "p": complete_reading.get("environment", {}).get("pressure", 1008)
                            },
                            "wind": {
                                "s": complete_reading.get("wind", {}).get("speed", 0),
                                "d": str(complete_reading.get("wind", {}).get("direction", "N"))
                            },
                            "rain": complete_reading.get("rainfall", 0),
                            "soil": {
                                "t": complete_reading.get("soil", {}).get("temperature", 0),
                                "m": complete_reading.get("soil", {}).get("moisture", 0)
                            },
                            "air": {
                                "pm25": complete_reading.get("air_quality", {}).get("pm25", 0),
                                "pm10": complete_reading.get("air_quality", {}).get("pm10", 0)
                            },
                            "rad": {
                                "uv": complete_reading.get("radiation", {}).get("uv_index", 0),
                                "lux": complete_reading.get("radiation", {}).get("light_level", 0)
                            },
                            "pwr": {
                                "bat": complete_reading.get("power", {}).get("battery_voltage", 0),
                                "sol": complete_reading.get("power", {}).get("solar_voltage", 0)
                            }
                        }
                        self.last_update_time = time.time()
                        logger.info(f"✅ Complete reading loaded - T={self.sensor_data['env']['t']}°C, H={self.sensor_data['env']['h']}%")
                        self.check_and_process()
                except json.JSONDecodeError:
                    logger.error(f"❌ Invalid JSON in complete reading: {payload}")
                return
            
            # Handle individual sensor messages (original path)
            try:
                value = json.loads(payload)
                # If it's a dict with 'value' key (from simulator), extract just the value
                if isinstance(value, dict) and 'value' in value:
                    value = value['value']
            except:
                # Try to convert to float, otherwise keep as string
                try:
                    value = float(payload)
                except ValueError:
                    value = payload  # Keep as string
            
            # Log all messages at INFO level so user can see them
            logger.info(f"📥 MQTT: {topic} = {value}")
            
            # Store in buffer based on topic
            with self.sensor_data_lock:
                if "temperature" in topic:
                    self.sensor_data["env"]["t"] = float(value) if isinstance(value, (int, float)) else value
                elif "humidity" in topic:
                    self.sensor_data["env"]["h"] = float(value) if isinstance(value, (int, float)) else value
                elif "pressure" in topic:
                    self.sensor_data["env"]["p"] = float(value) if isinstance(value, (int, float)) else value
                elif "wind_speed" in topic:
                    self.sensor_data["wind"]["s"] = float(value) if isinstance(value, (int, float)) else value
                elif "wind_direction" in topic:
                    self.sensor_data["wind"]["d"] = str(value)
                    logger.debug(f"  → Stored wind_direction as '{str(value)}'")
                elif "rainfall" in topic:
                    self.sensor_data["rain"] = float(value) if isinstance(value, (int, float)) else value
                elif "soil_temperature" in topic:
                    self.sensor_data["soil"]["t"] = float(value) if isinstance(value, (int, float)) else value
                elif "soil_moisture" in topic:
                    self.sensor_data["soil"]["m"] = float(value) if isinstance(value, (int, float)) else value
                elif "pm25" in topic:
                    self.sensor_data["air"]["pm25"] = float(value) if isinstance(value, (int, float)) else value
                elif "pm10" in topic:
                    self.sensor_data["air"]["pm10"] = float(value) if isinstance(value, (int, float)) else value
                elif "uv_index" in topic:
                    self.sensor_data["rad"]["uv"] = float(value) if isinstance(value, (int, float)) else value
                elif "light_level" in topic:
                    self.sensor_data["rad"]["lux"] = float(value) if isinstance(value, (int, float)) else value
                elif "battery_voltage" in topic:
                    self.sensor_data["pwr"]["bat"] = float(value) if isinstance(value, (int, float)) else value
                elif "solar_voltage" in topic:
                    self.sensor_data["pwr"]["sol"] = float(value) if isinstance(value, (int, float)) else value
                
                self.last_update_time = time.time()
                logger.debug(f"  → Calling check_and_process()")
                
                # Check if we should process and send
                self.check_and_process()
                logger.debug(f"  → check_and_process() completed")
                
        except Exception as e:
            logger.error(f"❌ Error processing MQTT message from {msg.topic}: {type(e).__name__}: {e}", exc_info=True)
    
    def init_twilio(self):
        """Initialize Twilio WhatsApp client for alerts"""
        try:
            account_sid = os.getenv("TWILIO_ACCOUNT_SID")
            auth_token = os.getenv("TWILIO_AUTH_TOKEN")
            twilio_number = os.getenv("TWILIO_WHATSAPP_NUMBER")
            alert_recipient = os.getenv("TWILIO_ALERT_RECIPIENT")
            
            if account_sid and auth_token and twilio_number and alert_recipient:
                self.twilio_client = Client(account_sid, auth_token)
                self.twilio_number = twilio_number
                self.alert_recipient = alert_recipient
                self.twilio_enabled = True
                logger.info(f"✅ Twilio WhatsApp alerts enabled (recipient: {alert_recipient})")
            else:
                logger.info("⚠️  Twilio credentials not configured - alerts disabled")
                logger.info("   To enable: Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_NUMBER, TWILIO_ALERT_RECIPIENT")
        except Exception as e:
            logger.warning(f"⚠️  Twilio initialization failed: {e}")
    
    def send_whatsapp_alert(self, alert_type: str, message: str):
        """Send WhatsApp alert via Twilio"""
        if not self.twilio_enabled:
            logger.debug(f"📵 Alert (mock): [{alert_type}] {message}")
            return
        
        try:
            msg = self.twilio_client.messages.create(
                from_=f"whatsapp:{self.twilio_number}",
                body=message,
                to=f"whatsapp:{self.alert_recipient}"
            )
            logger.info(f"📱 WhatsApp alert sent: {msg.sid}")
        except Exception as e:
            logger.error(f"❌ Failed to send WhatsApp alert: {e}")
    
    def check_and_send_alerts(self, accel_results: Dict[str, Any]):
        """Check accelerator results and send alerts if thresholds exceeded"""
        current_time = time.time()
        
        try:
            # Extract key metrics
            fusion_score = accel_results.get("sf_score", 50)
            alert_level = accel_results.get("sf_alert", 0)
            rain_probability = accel_results.get("rp_probability", 0)
            rain_alert = accel_results.get("rp_alert", 0)
            
            # 🚨 CRITICAL ALERT: High stress/critical conditions
            if alert_level > 2 and (current_time - self.last_critical_alert_time) > self.alert_throttle_seconds:
                message = f"🚨 CRITICAL ALERT\n\nPlant Health Critical: {fusion_score}/100\nAlert Level: {alert_level}/4\n\nImmediate irrigation action required!"
                self.send_whatsapp_alert("CRITICAL", message)
                self.last_critical_alert_time = current_time
            
            # 🌾 STRESS ALERT: Plant stress detected
            elif fusion_score < 40 and (current_time - self.last_stress_alert_time) > self.alert_throttle_seconds:
                message = f"🌾 PLANT STRESS DETECTED\n\nFusion Score: {fusion_score}/100\n\nConsider irrigation within 2 hours."
                self.send_whatsapp_alert("STRESS", message)
                self.last_stress_alert_time = current_time
            
            # 💧 RAIN ALERT: Heavy rain forecasted
            if rain_probability > 60 and rain_alert == 1 and (current_time - self.last_rain_alert_time) > self.alert_throttle_seconds:
                message = f"💧 RAIN FORECASTED\n\nRain Probability: {rain_probability}%\n\nConsider delaying irrigation."
                self.send_whatsapp_alert("RAIN", message)
                self.last_rain_alert_time = current_time
            
            # ✅ ALL CLEAR ALERT: Optimal conditions
            elif fusion_score > 75 and alert_level == 0 and (current_time - self.last_clear_alert_time) > self.alert_throttle_seconds * 2:
                message = f"✅ ALL CLEAR\n\nPlant Health Optimal: {fusion_score}/100\n\nAll conditions favorable. No action needed."
                self.send_whatsapp_alert("CLEAR", message)
                self.last_clear_alert_time = current_time
        
        except Exception as e:
            logger.error(f"❌ Error checking alerts: {e}")
    
    def on_disconnect(self, client, userdata, rc):
        """Called when disconnected from MQTT broker"""
        if rc != 0:
            logger.warning(f"⚠️  Unexpected disconnection from MQTT broker (rc={rc})")
    
    def is_data_complete(self) -> bool:
        """Check if we have minimum required sensor data"""
        has_temp = "t" in self.sensor_data["env"]
        has_humidity = "h" in self.sensor_data["env"]
        has_wind_speed = "s" in self.sensor_data["wind"]
        has_wind_dir = "d" in self.sensor_data["wind"]
        has_soil_moisture = "m" in self.sensor_data["soil"]
        
        is_complete = has_temp and has_humidity and has_wind_speed and has_wind_dir and has_soil_moisture
        
        if not is_complete:
            logger.debug(f"⏸️  Incomplete data - T:{has_temp}, H:{has_humidity}, WS:{has_wind_speed}, WD:{has_wind_dir}, SM:{has_soil_moisture}")
        
        return is_complete
    
    def check_and_process(self):
        """Check if data should be processed and send to backend"""
        try:
            current_time = time.time()
            time_since_last_send = current_time - self.last_backend_send_time
            
            # Debug: show current state
            is_complete = self.is_data_complete()
            time_ok = time_since_last_send > self.min_send_interval
            
            if is_complete and time_ok:
                self.process_and_send()
            elif is_complete and not time_ok:
                time_remaining = self.min_send_interval - time_since_last_send
                logger.debug(f"⏳ Data complete but waiting {time_remaining:.1f}s before next send")
        except Exception as e:
            logger.error(f"❌ Error in check_and_process(): {type(e).__name__}: {e}", exc_info=True)
    
    def process_through_accelerators(self, sensor_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process sensor data through ZC706 FPGA accelerators
        
        Returns accelerator results (stress, rain probability, etc.)
        """
        if not self.fpga_bridge:
            logger.debug("⚠️  FPGA Bridge not available, using fallback")
            return {
                "sf_score": 50,
                "sf_stress": 25,
                "sf_alert": 0,
                "rp_probability": 30,
                "rp_stress": 20,
                "rp_alert": 0
            }
        
        try:
            # Extract values for accelerators (convert floats to ints)
            soil = int(sensor_dict.get("soil_moisture", 0))
            temp = int(sensor_dict.get("temperature", 25))
            humid = int(sensor_dict.get("humidity", 50))
            light = int(sensor_dict.get("light_level", 500))
            pressure = int(sensor_dict.get("pressure", 1008))
            wind = int(sensor_dict.get("wind_speed", 0))
            
            # Call FPGA accelerators
            sf_result = self.fpga_bridge.send_fusion(soil, temp, humid, light)
            rp_result = self.fpga_bridge.send_rain_prediction(temp, humid, pressure, wind)
            
            logger.info(f"🔧 FPGA Results - SF: {sf_result}, RP: {rp_result}")
            
            return {
                "sf_score": sf_result.get("fusion_score", 0),
                "sf_stress": sf_result.get("stress_index", 0),
                "sf_alert": sf_result.get("alert_level", 0),
                "rp_probability": rp_result.get("rain_probability", 0),
                "rp_stress": rp_result.get("stress_level", 0),
                "rp_alert": rp_result.get("rain_alert", 0)
            }
            
        except Exception as e:
            logger.error(f"❌ Error calling FPGA accelerators: {e}")
            return None
    
    def make_decision(self, sensor_dict: Dict[str, Any], accelerator_results: Dict[str, Any]) -> str:
        """Make agricultural decision based on sensors and accelerator results"""
        if not self.decision_agent:
            return "NO_DECISION (Engine unavailable)"
        
        try:
            # Combine sensor data with accelerator results
            enhanced_sensor_data = {**sensor_dict, **accelerator_results}
            
            # Get decision from agent (returns a dict)
            decision_result = self.decision_agent.process_sensor_burst(enhanced_sensor_data)
            decision_text = decision_result.get("decision", "NO_DECISION") if isinstance(decision_result, dict) else str(decision_result)
            
            logger.info(f"🎯 Decision: {decision_text}")
            
            return decision_text
            
        except Exception as e:
            logger.error(f"❌ Error making decision: {e}")
            return "ERROR"
    
    def process_and_send(self):
        """Process sensor data through accelerators and send to backend"""
        try:
            with self.sensor_data_lock:
                # Only process if we have core data
                if not self.is_data_complete():
                    logger.debug("⏭️  Skipping - incomplete data")
                    return
                
                logger.info(f"📊 Processing sensor data batch...")
                
                # Build sensor reading
                sensor_reading = {
                    "id": self.station_id,
                    "ts": int(time.time()),
                    "env": {
                        "t": self.sensor_data["env"].get("t", 0),
                        "h": self.sensor_data["env"].get("h", 0),
                        "p": self.sensor_data["env"].get("p", 1008)
                    },
                    "wind": {
                        "s": self.sensor_data["wind"].get("s", 0),
                        "d": self.sensor_data["wind"].get("d", "N")
                    },
                    "rain": self.sensor_data["rain"],
                    "soil": {
                        "t": self.sensor_data["soil"].get("t", 0),
                        "m": self.sensor_data["soil"].get("m", 0)
                    },
                    "air": {
                        "pm25": self.sensor_data["air"].get("pm25", 0),
                        "pm10": self.sensor_data["air"].get("pm10", 0)
                    },
                    "rad": {
                        "uv": self.sensor_data["rad"].get("uv", 0),
                        "lux": self.sensor_data["rad"].get("lux", 0)
                    },
                    "pwr": {
                        "bat": self.sensor_data["pwr"].get("bat", 0),
                        "sol": self.sensor_data["pwr"].get("sol", 0)
                    }
                }
                
                # Convert to sensor dict for accelerators
                sensor_dict = {
                    "temperature": sensor_reading["env"]["t"],
                    "humidity": sensor_reading["env"]["h"],
                    "soil_moisture": sensor_reading["soil"]["m"],
                    "light_level": sensor_reading["rad"]["lux"],
                    "wind_speed": sensor_reading["wind"]["s"],
                    "rainfall": sensor_reading["rain"],
                }
            
            # Process through FPGA accelerators
            logger.info(f"📊 Processing sensor batch through ZC706 FPGA accelerators...")
            accel_results = self.process_through_accelerators(sensor_dict)
            
            if not accel_results:
                logger.error("❌ Accelerator processing failed")
                return
            
            # Get LLM analysis of accelerator results
            llm_analysis = None
            if self.llm_agent:
                try:
                    logger.info(f"🤖 Getting LLM analysis of FPGA results...")
                    
                    fusion_analysis = self.llm_agent.analyze_sensor_fusion_result({
                        "fusion_score": accel_results["sf_score"],
                        "stress_index": accel_results["sf_stress"],
                        "alert_level": accel_results["sf_alert"]
                    })
                    
                    rain_analysis = self.llm_agent.analyze_rain_prediction({
                        "rain_probability": accel_results["rp_probability"],
                        "stress_level": accel_results["rp_stress"],
                        "rain_alert": accel_results["rp_alert"]
                    })
                    
                    decision_analysis = self.llm_agent.make_irrigation_decision(
                        sensor_dict,
                        {
                            "fusion_score": accel_results["sf_score"],
                            "stress_index": accel_results["sf_stress"],
                            "alert_level": accel_results["sf_alert"]
                        },
                        {
                            "rain_probability": accel_results["rp_probability"],
                            "stress_level": accel_results["rp_stress"],
                            "rain_alert": accel_results["rp_alert"]
                        }
                    )
                    
                    llm_analysis = {
                        "fusion": fusion_analysis,
                        "rain": rain_analysis,
                        "decision": decision_analysis
                    }
                    
                    logger.info(f"✨ LLM Decision: {decision_analysis}")
                except Exception as e:
                    logger.warning(f"⚠️  LLM analysis failed: {e}")
            
            # Check and send WhatsApp alerts based on accelerator results
            self.check_and_send_alerts(accel_results)
            
            # Make traditional AI decision (fallback)
            decision = self.make_decision(sensor_dict, accel_results)
            
            # Send to backend with LLM analysis included
            sensor_reading["llm_analysis"] = llm_analysis if llm_analysis else {}
            sensor_reading["accelerator_results"] = accel_results
            
            logger.info(f"📤 Sending to backend: {self.backend_url}")
            response = requests.post(self.backend_url, json=sensor_reading, timeout=5)
            response.raise_for_status()
            
            logger.info(f"✅ Sent: T={sensor_reading['env']['t']}°C, "
                       f"H={sensor_reading['env']['h']}%, "
                       f"SM={sensor_reading['soil']['m']}%, "
                       f"Decision={decision}")
            
            self.last_backend_send_time = time.time()
            
        except requests.exceptions.ConnectionError:
            logger.warning(f"⚠️  Cannot connect to backend")
        except Exception as e:
            logger.error(f"❌ Error in process_and_send: {e}")
    
    def start(self):
        """Start the unified bridge"""
        try:
            logger.info("=" * 70)
            logger.info("🚀 ZC706 FPGA + MQTT + Backend Unified Bridge Starting")
            logger.info("=" * 70)
            logger.info(f"📡 MQTT Broker: {self.mqtt_broker}:{self.mqtt_port}")
            logger.info(f"🔧 FPGA: {'Enabled' if self.fpga_enabled else 'Disabled'}")
            logger.info(f"🔗 Backend: {self.backend_url}")
            logger.info(f"📍 Station ID: {self.station_id}")
            logger.info("=" * 70)
            
            self.client.connect(self.mqtt_broker, self.mqtt_port, keepalive=60)
            self.client.loop_forever()
            
        except ConnectionRefusedError:
            logger.error(f"❌ MQTT broker not running at {self.mqtt_broker}:{self.mqtt_port}")
            logger.error("🔧 To start MQTT broker on Windows:")
            logger.error("   - Download Mosquitto: https://mosquitto.org/download/")
            logger.error("   - Or use WSL: wsl; sudo apt install mosquitto; mosquitto")
            logger.error("   - Or Docker: docker run -p 1883:1883 eclipse-mosquitto")
            logger.error("\n⏹️ Stopping bridge")
        except KeyboardInterrupt:
            logger.info("\n⏹️ Bridge stopped by user")
        except Exception as e:
            logger.error(f"❌ Error starting bridge: {e}")

def main():
    """Run the unified bridge"""
    # Configuration
    mqtt_broker = "192.168.137.83"
    mqtt_port = 1883
    backend_url = "http://localhost:8000/api/sensors/ingest"
    station_id = "WS01"
    fpga_enabled = True
    fpga_port = "COM4"
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        mqtt_broker = sys.argv[1]
    if len(sys.argv) > 2:
        mqtt_port = int(sys.argv[2])
    if len(sys.argv) > 3:
        backend_url = sys.argv[3]
    if len(sys.argv) > 4:
        station_id = sys.argv[4]
    if len(sys.argv) > 5:
        fpga_enabled = sys.argv[5].lower() == "true"
    if len(sys.argv) > 6:
        fpga_port = sys.argv[6]
    
    # Create and start bridge
    bridge = UnifiedZC706Bridge(
        mqtt_broker=mqtt_broker,
        mqtt_port=mqtt_port,
        backend_url=backend_url,
        station_id=station_id,
        fpga_enabled=fpga_enabled,
        fpga_port=fpga_port
    )
    bridge.start()

if __name__ == "__main__":
    main()
