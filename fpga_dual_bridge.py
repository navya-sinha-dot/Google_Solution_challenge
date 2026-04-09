#!/usr/bin/env python3
"""
Dual Accelerator Serial Bridge
Communicates with both Sensor Fusion and Rain Predictor accelerators on ZC706
Protocol V2: Supports both FUSION and RAIN commands
"""

import serial
import time
import struct
import os
from typing import Dict, Tuple, Optional
import sys

class DualAcceleratorBridge:
    @staticmethod
    def list_available_ports():
        """List all available COM ports"""
        try:
            import serial.tools.list_ports
            ports = [port.device for port in serial.tools.list_ports.comports()]
            return ports
        except:
            return []
    
    def __init__(self, port: str = "COM4", baud: int = 115200, timeout: float = 3.0, simulation: bool = False):
        """
        Initialize connection to dual accelerators
        
        Args:
            port: Serial port (e.g., COM4 on Windows, /dev/ttyUSB0 on Linux)
            baud: Baud rate (115200)
            timeout: Read timeout in seconds
            simulation: If True, simulate without hardware
        """
        self.simulation = simulation
        self.port = port
        self.baud = baud
        self.timeout = timeout
        self.serial = None
        
        if not simulation:
            try:
                # Show available ports
                available = self.list_available_ports()
                print(f"[INFO] Available COM ports: {available if available else 'None detected'}")
                
                if port not in available:
                    print(f"[WARNING] {port} not in available ports. Attempting anyway...")
                
                # Try to open serial port with retries
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        self.serial = serial.Serial(port, baud, timeout=timeout)
                        time.sleep(1)  # Wait for firmware to be ready
                        
                        # Clear any leftover data from previous sessions
                        print("[INFO] Flushing serial buffers...")
                        self.serial.reset_input_buffer()
                        self.serial.reset_output_buffer()
                        time.sleep(0.5)
                        
                        # Drain any leftover responses by reading with short timeout
                        self.serial.timeout = 0.1
                        while True:
                            try:
                                data = self.serial.read(1)
                                if not data:
                                    break
                            except:
                                break
                        self.serial.timeout = timeout  # Restore normal timeout
                        
                        print(f"[OK] Connected to {port} @ {baud} baud")
                        
                        # Send warm-up command to synchronize firmware
                        # Firmware protocol requires initial "priming" command
                        try:
                            print("[INFO] Sending warm-up command...")
                            self.serial.write(b"FUSION:50,50,50,50\n")
                            self.serial.flush()
                            time.sleep(0.2)
                            _ = self.serial.readline()  # Drain warm-up response
                            print("[INFO] Firmware synchronized - ready for commands")
                        except Exception as warm_err:
                            print(f"[WARNING] Warm-up command failed: {warm_err}")
                            # Continue - firmware might still work
                        
                        return
                    except serial.SerialException as se:
                        print(f"[RETRY {attempt+1}/{max_retries}] Failed to open {port}: {se}")
                        time.sleep(0.5)
                        continue
                
                # All retries failed
                raise Exception(f"Could not open {port} after {max_retries} attempts")
            except Exception as e:
                print(f"[ERROR] Failed to connect to {port}: {e}")
                print(f"[INFO] Available ports were: {self.list_available_ports()}")
                self.simulation = True
                print("[FALLBACK] Running in simulation mode")
    
    def close(self):
        """Close serial connection"""
        if self.serial and self.serial.is_open:
            self.serial.close()
    
    def _send_command(self, cmd: str, retries: int = 3) -> str:
        """Send command and receive response with retry logic"""
        if self.simulation:
            return self._simulate_response(cmd)
        
        if not self.serial or not self.serial.is_open:
            print(f"[ERROR] Serial port not open")
            return ""
        
        # Determine expected response prefix
        expected_prefix = "SF_RESULT:" if cmd.startswith("FUSION:") else "RP_RESULT:" if cmd.startswith("RAIN:") else ""
        
        for attempt in range(retries):
            try:
                # CRITICAL: Drain ALL buffered data from previous commands
                # The FPGA firmware may have leftover responses in the buffer
                self.serial.reset_input_buffer()
                old_timeout = self.serial.timeout
                self.serial.timeout = 0.05  # Very short timeout for draining
                drained = 0
                while True:
                    leftover = self.serial.readline()
                    if not leftover or leftover == b'':
                        break
                    drained += 1
                    print(f"[DRAIN] Cleared leftover: {leftover.decode(errors='ignore').strip()[:50]}")
                self.serial.timeout = old_timeout  # Restore normal timeout
                
                if drained > 0:
                    print(f"[DRAIN] Cleared {drained} leftover line(s)")
                
                # Wait for firmware to be fully ready
                time.sleep(0.25)
                
                # Send command
                self.serial.write((cmd + "\n").encode())
                self.serial.flush()
                
                # Wait for firmware to process — ZC706 needs ~300ms
                time.sleep(0.35)
                
                # Read response lines — scan for the expected prefix
                for line_attempt in range(8):
                    response = self.serial.readline().decode(errors='ignore').strip()
                    
                    if response and expected_prefix and response.startswith(expected_prefix):
                        print(f"[OK] Got response: {response}")
                        return response
                    elif response and not expected_prefix:
                        return response
                    elif not response:
                        time.sleep(0.1)
                        continue
                    else:
                        print(f"[SKIP] Non-result line: {response[:60]}")
                        continue
                
                print(f"[RETRY {attempt+1}/{retries}] No valid response for: {cmd[:30]}")
                    
            except Exception as e:
                print(f"[ERROR] Attempt {attempt+1}/{retries} failed: {e}")
                time.sleep(0.3)
        
        print(f"[WARNING] All retries exhausted for: {cmd[:30]}")
        return ""
    
    def _simulate_response(self, cmd: str) -> str:
        """Simulate accelerator responses for testing without hardware"""
        if cmd.startswith("FUSION:"):
            # FUSION:soil,temp,humid,light → SF_RESULT:fusion,stress,alert
            parts = cmd.split(":")[1].split(",")
            soil, temp, humid, light = map(int, parts)
            
            # Simple simulation: average the inputs
            fusion_score = (soil + temp + humid + light) // 4
            stress_index = max(0, min(100, abs(temp - 25) * 2))
            alert = 1 if stress_index > 50 else 0
            
            return f"SF_RESULT:{fusion_score},{stress_index},{alert}"
        
        elif cmd.startswith("RAIN:"):
            # RAIN:temp,humid,press,wind → RP_RESULT:rain_prob,stress,alert
            parts = cmd.split(":")[1].split(",")
            temp, humid, press, wind = map(int, parts)
            
            # Simple simulation
            rain_prob = 0
            if humid > 70 and press < 40:
                rain_prob = min(100, humid * 0.8)
            
            stress = 0
            if humid > 85 or press < 30 or wind > 15:
                stress = 60
            
            alert = 1 if rain_prob > 60 and press < 40 else 0
            
            return f"RP_RESULT:{int(rain_prob)},{stress},{alert}"
        
        return ""
    
    def send_fusion(self, soil: int, temp: int, humid: int, light: int) -> Dict:
        """
        Send sensor data to Sensor Fusion accelerator
        
        Returns dict with keys:
            - fusion_score (0-100)
            - stress_index (0-100)
            - alert_level (0-4)
        """
        cmd = f"FUSION:{soil},{temp},{humid},{light}"
        response = self._send_command(cmd)
        
        if response and response.startswith("SF_RESULT:"):
            try:
                parts = response.split(":")[1].split(",")
                fusion = int(parts[0])
                stress = int(parts[1])
                alert = int(parts[2])
                
                return {
                    "fusion_score": fusion,
                    "stress_index": stress,
                    "alert_level": alert,
                    "alert_name": "Critical" if alert >= 3 else "High Stress" if alert >= 2 else "Moderate" if alert >= 1 else "Normal",
                    "timestamp": int(time.time() * 1000),
                    "source": "fpga_hardware"
                }
            except Exception as e:
                print(f"[ERROR] Parsing SF result: {e}")
        
        # Compute meaningful fallback from actual sensor inputs
        print(f"[FALLBACK] Computing fusion from sensor inputs: soil={soil}, temp={temp}, humid={humid}, light={light}")
        
        # Realistic computation based on sensor data
        optimal_temp = 25
        temp_stress = min(100, abs(temp - optimal_temp) * 4)
        moisture_stress = max(0, min(100, abs(soil - 50) * 2))
        humidity_factor = max(0, min(100, abs(humid - 60) * 2))
        
        stress_index = int((temp_stress * 0.4 + moisture_stress * 0.35 + humidity_factor * 0.25))
        fusion_score = max(0, min(100, 100 - stress_index))
        alert_level = 3 if stress_index > 75 else 2 if stress_index > 50 else 1 if stress_index > 30 else 0
        
        return {
            "fusion_score": fusion_score,
            "stress_index": stress_index,
            "alert_level": alert_level,
            "alert_name": "Critical" if alert_level >= 3 else "High Stress" if alert_level >= 2 else "Moderate" if alert_level >= 1 else "Normal",
            "timestamp": int(time.time() * 1000),
            "source": "computed_fallback"
        }
    
    def send_rain_prediction(self, temp: int, humid: int, pressure: int, wind: int) -> Dict:
        """
        Send weather data to Rain Predictor accelerator
        
        Returns dict with keys:
            - rain_probability (0-100%)
            - stress_level (0-100)
            - rain_alert (0 or 1)
        """
        cmd = f"RAIN:{temp},{humid},{pressure},{wind}"
        response = self._send_command(cmd)
        
        if response and response.startswith("RP_RESULT:"):
            try:
                parts = response.split(":")[1].split(",")
                rain_prob = int(parts[0])
                stress = int(parts[1])
                alert = int(parts[2])
                
                return {
                    "rain_probability": rain_prob,
                    "stress_level": stress,
                    "rain_alert": alert,
                    "timestamp": int(time.time() * 1000),
                    "source": "fpga_hardware"
                }
            except Exception as e:
                print(f"[ERROR] Parsing RP result: {e}")
        
        # Compute meaningful fallback from actual weather inputs
        print(f"[FALLBACK] Computing rain prediction from inputs: temp={temp}, humid={humid}, pressure={pressure}, wind={wind}")
        
        # Realistic rain probability based on humidity + pressure
        humidity_factor = max(0, (humid - 40)) * 1.2  # Higher humidity = more rain
        pressure_factor = max(0, (1013 - pressure)) * 0.5  # Lower pressure = more rain
        wind_factor = max(0, wind - 5) * 0.3  # Higher wind adds slight chance
        rain_prob = int(max(0, min(100, humidity_factor + pressure_factor + wind_factor)))
        
        stress_level = int(max(0, min(100, abs(temp - 25) * 3 + max(0, humid - 70))))
        rain_alert = 1 if rain_prob > 60 else 0
        
        return {
            "rain_probability": rain_prob,
            "stress_level": stress_level,
            "rain_alert": rain_alert,
            "timestamp": int(time.time() * 1000),
            "source": "computed_fallback"
        }
    
    def process_all_sensors(self, soil: int, temp: int, humid: int, light: int, 
                           pressure: int, wind: int) -> Dict:
        """
        Process sensor data through BOTH accelerators
        Returns combined results
        """
        sf_result = self.send_fusion(soil, temp, humid, light)
        rp_result = self.send_rain_prediction(temp, humid, pressure, wind)
        
        # Combine results
        combined = {
            "sensor_fusion": sf_result,
            "rain_predictor": rp_result,
            "combined_alert": 0,
            "recommended_action": "NONE"
        }
        
        # Decision logic: combine both accelerators
        if sf_result["alert_level"] >= 3 and rp_result["rain_alert"] == 1:
            combined["combined_alert"] = 1
            combined["recommended_action"] = "IRRIGATE_NOW"
        elif rp_result["rain_probability"] > 70:
            combined["combined_alert"] = 1
            combined["recommended_action"] = "WAIT_FOR_RAIN"
        elif sf_result["alert_level"] >= 2:
            combined["recommended_action"] = "MONITOR"
        
        return combined


def main():
    """Test both accelerators"""
    # Check if FPGA_ENABLED env var is set
    fpga_enabled = os.getenv("FPGA_ENABLED", "false").lower() == "true"
    port = os.getenv("FPGA_PORT", "COM4")
    
    if not fpga_enabled:
        print("[INFO] FPGA_ENABLED not set. Running in simulation mode.")
        print("[TIP] To use hardware: set FPGA_ENABLED=true and FPGA_PORT=COM4")
        bridge = DualAcceleratorBridge(port=port, simulation=True)
    else:
        print(f"[INFO] Connecting to hardware at {port}")
        bridge = DualAcceleratorBridge(port=port, simulation=False)
    
    print("\n" + "=" * 60)
    print("  Dual Accelerator Test")
    print("=" * 60 + "\n")
    
    # Test Case 1: Spring Morning
    print("[TEST 1] Spring Morning - Moderate Conditions")
    soil, temp, humid, light = 50, 18, 75, 45
    pressure, wind = 45, 6
    
    result = bridge.process_all_sensors(soil, temp, humid, light, pressure, wind)
    print(f"  Sensor Fusion → Fusion: {result['sensor_fusion']['fusion_score']}, Alert: {result['sensor_fusion']['alert_level']}")
    print(f"  Rain Predictor → Prob: {result['rain_predictor']['rain_probability']}%, Alert: {result['rain_predictor']['rain_alert']}")
    print(f"  → Action: {result['recommended_action']}\n")
    
    # Test Case 2: Drought Risk
    print("[TEST 2] Drought Conditions")
    soil, temp, humid, light = 20, 35, 30, 85
    pressure, wind = 55, 2
    
    result = bridge.process_all_sensors(soil, temp, humid, light, pressure, wind)
    print(f"  Sensor Fusion → Fusion: {result['sensor_fusion']['fusion_score']}, Alert: {result['sensor_fusion']['alert_level']}")
    print(f"  Rain Predictor → Prob: {result['rain_predictor']['rain_probability']}%, Alert: {result['rain_predictor']['rain_alert']}")
    print(f"  → Action: {result['recommended_action']}\n")
    
    # Test Case 3: Incoming Storm
    print("[TEST 3] Incoming Storm - High Rain Risk")
    soil, temp, humid, light = 65, 22, 88, 35
    pressure, wind = 38, 10
    
    result = bridge.process_all_sensors(soil, temp, humid, light, pressure, wind)
    print(f"  Sensor Fusion → Fusion: {result['sensor_fusion']['fusion_score']}, Alert: {result['sensor_fusion']['alert_level']}")
    print(f"  Rain Predictor → Prob: {result['rain_predictor']['rain_probability']}%, Alert: {result['rain_predictor']['rain_alert']}")
    print(f"  → Action: {result['recommended_action']}\n")
    
    # Test Case 4: Optimal Conditions
    print("[TEST 4] Optimal Growing Conditions")
    soil, temp, humid, light = 60, 25, 60, 70
    pressure, wind = 50, 4
    
    result = bridge.process_all_sensors(soil, temp, humid, light, pressure, wind)
    print(f"  Sensor Fusion → Fusion: {result['sensor_fusion']['fusion_score']}, Alert: {result['sensor_fusion']['alert_level']}")
    print(f"  Rain Predictor → Prob: {result['rain_predictor']['rain_probability']}%, Alert: {result['rain_predictor']['rain_alert']}")
    print(f"  → Action: {result['recommended_action']}\n")
    
    bridge.close()
    print("=" * 60)
    print("  Tests Complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
