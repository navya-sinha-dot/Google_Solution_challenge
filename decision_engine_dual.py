#!/usr/bin/env python3
"""
Agent Integration Example: Dual Accelerator Decision Engine
Shows how to use Sensor Fusion + Rain Predictor in your LangGraph agent
"""

from fpga_dual_bridge import DualAcceleratorBridge
from typing import Dict, List
import json
import time

class AgriculturalDecisionAgent:
    """
    LangGraph-compatible agent that uses both FPGA accelerators
    to make real-time farming decisions
    """
    
    def __init__(self, fpga_bridge=None, fpga_port: str = "COM4"):
        """
        Initialize agent with dual accelerator bridge
        
        Args:
            fpga_bridge: Optional pre-initialized DualAcceleratorBridge instance
                        If provided, will reuse this instead of creating a new one
            fpga_port: Port to use if creating a new bridge (ignored if fpga_bridge provided)
        """
        if fpga_bridge is not None:
            # Reuse existing bridge (most common case)
            self.bridge = fpga_bridge
        else:
            # Create new bridge if not provided
            self.bridge = DualAcceleratorBridge(port=fpga_port, simulation=False)
        
        self.history = []
    
    def process_sensor_burst(self, sensor_readings: Dict) -> Dict:
        """
        Process a sensor reading burst through both accelerators
        
        Args:
            sensor_readings: Dict with keys: soil, temperature, humidity, 
                           light, pressure, wind
        
        Returns:
            Decision dict with recommended actions and confidence
        """
        soil = sensor_readings.get("soil", 50)
        temp = sensor_readings.get("temperature", 25)
        humid = sensor_readings.get("humidity", 60)
        light = sensor_readings.get("light", 50)
        pressure = sensor_readings.get("pressure", 50)
        wind = sensor_readings.get("wind", 5)
        
        # Call both accelerators
        print(f"\n[AGENT] Processing sensors: T={temp}, H={humid}, P={pressure}, W={wind}")
        
        accel_result = self.bridge.process_all_sensors(
            soil, temp, humid, light, pressure, wind
        )
        
        # Extract results
        sf = accel_result["sensor_fusion"]
        rp = accel_result["rain_predictor"]
        
        # Agent decision logic
        decision = self._make_decision(sf, rp, sensor_readings)
        
        # Add accelerator results to decision dict for display
        decision["sensor_fusion"] = sf
        decision["rain_predictor"] = rp
        
        # Store in history
        self.history.append({
            "timestamp": time.time(),
            "inputs": sensor_readings,
            "sensor_fusion": sf,
            "rain_predictor": rp,
            "decision": decision
        })
        
        return decision
    
    def _make_decision(self, sf: Dict, rp: Dict, sensors: Dict) -> Dict:
        """
        Apply decision logic based on accelerator outputs
        This is where LangGraph agent reasoning would go
        """
        
        decision = {
            "action": "NONE",
            "confidence": 0.0,
            "reasoning": [],
            "alerts": [],
            "recommended_controls": {}
        }
        
        # Extract sensor values
        soil_moisture = sensors.get("soil", 50)
        temp = sensors.get("temperature", 25)
        humid = sensors.get("humidity", 60)
        light = sensors.get("light", 50)
        
        # ===== IRRIGATION DECISION =====
        if soil_moisture < 30 and sf["stress_index"] > 15:
            # Dry soil + plant stress → IRRIGATE
            decision["action"] = "IRRIGATE"
            decision["confidence"] = min(1.0, (100 - soil_moisture) / 100)
            decision["reasoning"].append("Low soil moisture + plant stress detected")
            decision["recommended_controls"]["irrigation"] = {
                "enabled": True,
                "duration_minutes": 30 + (30 - soil_moisture),
                "confidence": decision["confidence"]
            }
        
        elif rp["rain_probability"] > 50:
            # Rain coming → HOLD irrigation
            decision["action"] = "HOLD_IRRIGATION"
            decision["confidence"] = rp["rain_probability"] / 100
            decision["reasoning"].append(f"Rain expected ({rp['rain_probability']}%)")
            decision["recommended_controls"]["irrigation"] = {
                "enabled": False,
                "reason": "Rain inbound",
                "confidence": decision["confidence"]
            }
        
        # ===== FROST PROTECTION =====
        if temp < 5 and rp["stress_level"] > 20:
            decision["alerts"].append("FROST_RISK")
            decision["recommended_controls"]["heater"] = {
                "enabled": True,
                "target_temp": 10
            }
        
        # ===== PEST/DISEASE MONITORING =====
        if sf["stress_index"] > 30 and humid > 80:
            decision["alerts"].append("HIGH_DISEASE_RISK")
            decision["recommended_controls"]["fungicide"] = {
                "apply": True,
                "reason": "High humidity + plant stress"
            }
        
        # ===== LIGHT OPTIMIZATION =====
        if light < 30 and sf["alert_level"] < 2:
            decision["recommended_controls"]["supplemental_light"] = {
                "enabled": True,
                "duration_hours": 4
            }
        
        # ===== VENTILATION =====
        if temp > 35 and humid > 70:
            decision["recommended_controls"]["ventilation"] = {
                "enabled": True,
                "fan_speed": "HIGH",
                "reason": "High temp + humidity"
            }
        
        return decision
    
    def get_continuous_monitoring_report(self, window_size: int = 10) -> Dict:
        """Generate a report over last N measurements"""
        if len(self.history) < window_size:
            recent = self.history
        else:
            recent = self.history[-window_size:]
        
        # Aggregate statistics
        avg_sf_alert = sum(h["sensor_fusion"]["alert_level"] for h in recent) / len(recent)
        avg_rain_prob = sum(h["rain_predictor"]["rain_probability"] for h in recent) / len(recent)
        
        rain_alerts = sum(1 for h in recent if h["rain_predictor"]["rain_alert"] == 1)
        actions_taken = [h["decision"]["action"] for h in recent if h["decision"]["action"] != "NONE"]
        
        return {
            "window_size": len(recent),
            "avg_sf_alert_level": avg_sf_alert,
            "avg_rain_probability": avg_rain_prob,
            "rain_alert_count": rain_alerts,
            "actions_taken": actions_taken,
            "last_action": recent[-1]["decision"]["action"] if recent else "NONE",
            "most_common_alert": max(set([a for h in recent for a in h["decision"]["alerts"]]), 
                                     default="NONE")
        }


def agent_workflow_example():
    """
    Example workflow showing how to use the agent with MQTT data
    """
    print("=" * 70)
    print("  Agricultural Decision Agent - Dual Accelerator Integration")
    print("=" * 70)
    
    agent = AgriculturalDecisionAgent(fpga_port="COM4")
    
    # Simulate multiple sensor readings over time
    test_scenarios = [
        {
            "name": "TEST 1: Dry Soil + Plant Stress → IRRIGATE",
            "data": {"soil": 25, "temperature": 30, "humidity": 35, 
                    "light": 90, "pressure": 51, "wind": 4}
        },
        {
            "name": "TEST 2: Heavy Rain Coming → HOLD_IRRIGATION",
            "data": {"soil": 60, "temperature": 22, "humidity": 88, 
                    "light": 40, "pressure": 38, "wind": 10}
        },
        {
            "name": "TEST 3: Frost + High Stress Risk",
            "data": {"soil": 55, "temperature": 3, "humidity": 75, 
                    "light": 10, "pressure": 45, "wind": 2}
        },
        {
            "name": "TEST 4: High Temperature + High Humidity → VENTILATION",
            "data": {"soil": 50, "temperature": 38, "humidity": 75, 
                    "light": 85, "pressure": 50, "wind": 2}
        },
        {
            "name": "TEST 5: High Stress + High Humidity → DISEASE RISK",
            "data": {"soil": 45, "temperature": 28, "humidity": 85, 
                    "light": 50, "pressure": 48, "wind": 3}
        },
        {
            "name": "TEST 6: Low Light + No Stress → SUPPLEMENTAL_LIGHT",
            "data": {"soil": 55, "temperature": 22, "humidity": 60, 
                    "light": 15, "pressure": 50, "wind": 3}
        },
        {
            "name": "TEST 7: Optimal Growing Conditions",
            "data": {"soil": 60, "temperature": 25, "humidity": 65, 
                    "light": 80, "pressure": 50, "wind": 3}
        },
    ]
    
    for scenario in test_scenarios:
        print(f"\n[SCENARIO] {scenario['name']}")
        print("-" * 70)
        
        decision = agent.process_sensor_burst(scenario["data"])
        
        print(f"✓ Sensor Fusion:")
        print(f"  → Fusion Score: {decision.get('sensor_fusion', {}).get('fusion_score', 'N/A')}")
        print(f"  → Stress Level: {decision.get('sensor_fusion', {}).get('stress_index', 'N/A')}")
        
        print(f"✓ Rain Predictor:")
        print(f"  → Rain Probability: {decision.get('rain_predictor', {}).get('rain_probability', 'N/A')}%")
        print(f"  → Rain Alert: {decision.get('rain_predictor', {}).get('rain_alert', 'N/A')}")
        
        print(f"\n→ DECISION: {decision['action']}")
        print(f"→ CONFIDENCE: {decision['confidence']:.2f}")
        if decision['reasoning']:
            print(f"→ REASONING: {'; '.join(decision['reasoning'])}")
        if decision['alerts']:
            print(f"→ ALERTS: {', '.join(decision['alerts'])}")
        if decision['recommended_controls']:
            print(f"→ CONTROLS:")
            for control, config in decision['recommended_controls'].items():
                print(f"   • {control}: {config}")
        
        time.sleep(1)  # Simulate time between measurements
    
    # Print monitoring report
    print("\n" + "=" * 70)
    print("  Continuous Monitoring Report")
    print("=" * 70)
    
    report = agent.get_continuous_monitoring_report(window_size=10)
    print(f"\nAnalyzing last {report['window_size']} measurements:")
    print(f"  • Avg SF Alert Level: {report['avg_sf_alert_level']:.2f}")
    print(f"  • Avg Rain Probability: {report['avg_rain_probability']:.1f}%")
    print(f"  • Rain Alerts Triggered: {report['rain_alert_count']}")
    print(f"  • Actions Taken: {', '.join(report['actions_taken']) if report['actions_taken'] else 'NONE'}")
    print(f"  • Most Common Alert: {report['most_common_alert']}")
    
    print("\n" + "=" * 70)
    agent.bridge.close()


if __name__ == "__main__":
    agent_workflow_example()
