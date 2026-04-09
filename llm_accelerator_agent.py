#!/usr/bin/env python3
"""
Integrated LLM + FPGA Agent for Agricultural Decisions
Combines Groq LLM reasoning with real FPGA accelerator results
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from langchain_groq import ChatGroq
from dotenv import load_dotenv

# Load from the script's directory
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)
logger = logging.getLogger(__name__)

class LLMAcceleratorAgent:
    """
    LLM Agent that uses REAL FPGA accelerator data for decision-making.
    Integrates with the sensor fusion and rain prediction accelerators.
    """
    
    def __init__(self):
        """Initialize LLM with Groq API"""
        api_key = os.getenv("GROQ_API_KEY")
        
        # Debug: Show what we got
        if api_key:
            logger.info(f"✅ Groq API Key loaded: {api_key[:10]}...")
        else:
            logger.warning("⚠️ GROQ_API_KEY not set - LLM features disabled")
            logger.debug(f"Available env vars: {list(os.environ.keys())[:10]}")
        
        if not api_key:
            self.llm = None
        else:
            try:
                self.llm = ChatGroq(
                    model="llama-3.1-8b-instant",
                    api_key=api_key,
                    temperature=0.3
                )
                logger.info("✅ LLM Agent initialized with Groq")
            except Exception as e:
                logger.warning(f"⚠️ Failed to initialize LLM: {e}")
                self.llm = None
    
    def analyze_sensor_fusion_result(self, fusion_result: Dict[str, Any]) -> str:
        """
        Use LLM to interpret sensor fusion accelerator results
        
        Args:
            fusion_result: Output from FPGA sensor fusion accelerator
            
        Returns:
            Natural language interpretation
        """
        if not self.llm:
            return self._default_fusion_analysis(fusion_result)
        
        try:
            fusion_score = fusion_result.get("fusion_score", 0)
            stress_index = fusion_result.get("stress_index", 0)
            alert_level = fusion_result.get("alert_level", 0)
            
            prompt = f"""You are an expert agricultural advisor analyzing real-time sensor data.

FPGA Sensor Fusion Accelerator Results:
- Fusion Score: {fusion_score}/100 (overall plant health)
- Stress Index: {stress_index}/100 (plant stress level)
- Alert Level: {alert_level}/4 (severity: 0=none, 4=critical)

Interpret these REAL measurements from our FPGA accelerator. What is the current plant health status?
Be concise and actionable (1-2 sentences max)."""
            
            response = self.llm.invoke([("user", prompt)])
            return response.content
        except Exception as e:
            logger.error(f"LLM fusion analysis failed: {e}")
            return self._default_fusion_analysis(fusion_result)
    
    def analyze_rain_prediction(self, rain_result: Dict[str, Any]) -> str:
        """
        Use LLM to interpret rain prediction from accelerator
        
        Args:
            rain_result: Output from FPGA rain predictor accelerator
            
        Returns:
            Natural language weather advisory
        """
        if not self.llm:
            return self._default_rain_analysis(rain_result)
        
        try:
            rain_prob = rain_result.get("rain_probability", 0)
            stress_level = rain_result.get("stress_level", 0)
            rain_alert = rain_result.get("rain_alert", 0)
            
            prompt = f"""You are a weather advisor for agricultural operations.

FPGA Rain Predictor Results:
- Rain Probability: {rain_prob}%
- Weather Stress Level: {stress_level}/100
- Rain Alert: {"TRUE" if rain_alert else "FALSE"}

Based on these REAL accelerator predictions, what is the weather outlook?
Give brief, actionable advice (1-2 sentences max)."""
            
            response = self.llm.invoke([("user", prompt)])
            return response.content
        except Exception as e:
            logger.error(f"LLM rain analysis failed: {e}")
            return self._default_rain_analysis(rain_result)
    
    def make_irrigation_decision(self, 
                                sensor_data: Dict[str, Any],
                                fusion_result: Dict[str, Any],
                                rain_result: Dict[str, Any]) -> str:
        """
        Use LLM to make irrigation decision using REAL accelerator data
        
        Args:
            sensor_data: Current sensor readings
            fusion_result: FPGA sensor fusion output
            rain_result: FPGA rain predictor output
            
        Returns:
            Natural language irrigation recommendation
        """
        if not self.llm:
            return self._default_decision(fusion_result, rain_result)
        
        try:
            prompt = f"""You are an AI irrigation controller with access to real agricultural data.

REAL SENSOR DATA:
- Temperature: {sensor_data.get('temperature')}°C
- Humidity: {sensor_data.get('humidity')}%
- Soil Moisture: {sensor_data.get('soil_moisture')}/100
- Pressure: {sensor_data.get('pressure')} hPa

FPGA ACCELERATOR RESULTS:
Sensor Fusion:
  - Health Score: {fusion_result.get('fusion_score')}/100
  - Stress: {fusion_result.get('stress_index')}/100
  - Alert: {fusion_result.get('alert_level')}/4

Rain Prediction:
  - Probability: {rain_result.get('rain_probability')}%
  - Weather Stress: {rain_result.get('stress_level')}/100
  - Rain Alert: {bool(rain_result.get('rain_alert'))}

Based on ALL this REAL data from our accelerators, should we irrigate now?
Respond with ONE action: IRRIGATE_NOW, REDUCE_IRRIGATION, MONITOR, or SKIP.
Then explain briefly (1 sentence)."""
            
            response = self.llm.invoke([("user", prompt)])
            return response.content
        except Exception as e:
            logger.error(f"LLM decision failed: {e}")
            return self._default_decision(fusion_result, rain_result)
    
    # ===== FALLBACK METHODS (when LLM unavailable) =====
    
    def _default_fusion_analysis(self, fusion_result: Dict) -> str:
        """Fallback analysis without LLM"""
        score = fusion_result.get("fusion_score", 0)
        if score >= 75:
            return "Plant health: Excellent. Optimal growth conditions."
        elif score >= 50:
            return "Plant health: Good. Monitor for minor stress."
        else:
            return "Plant health: Poor. Intervention may be needed."
    
    def _default_rain_analysis(self, rain_result: Dict) -> str:
        """Fallback rain analysis without LLM"""
        prob = rain_result.get("rain_probability", 0)
        if prob >= 70:
            return "High rain probability. Irrigation not recommended."
        elif prob >= 40:
            return "Moderate rain chance. Monitor forecast."
        else:
            return "Low rain probability. Plan irrigation accordingly."
    
    def _default_decision(self, fusion_result: Dict, rain_result: Dict) -> str:
        """Fallback irrigation decision without LLM"""
        fusion_score = fusion_result.get("fusion_score", 0)
        rain_prob = rain_result.get("rain_probability", 0)
        
        if rain_prob > 70:
            return "SKIP - High rain probability expected."
        elif fusion_score < 40 and rain_prob < 30:
            return "IRRIGATE_NOW - Low soil health and no rain expected."
        elif fusion_score < 60:
            return "MONITOR - Stress detected. Prepare irrigation if needed."
        else:
            return "REDUCE_IRRIGATION - Conditions are favorable."


def main():
    """Test the LLM agent independently"""
    agent = LLMAcceleratorAgent()
    
    # Simulate accelerator results
    fusion_result = {
        "fusion_score": 55,
        "stress_index": 45,
        "alert_level": 2
    }
    
    rain_result = {
        "rain_probability": 35,
        "stress_level": 40,
        "rain_alert": 0
    }
    
    sensor_data = {
        "temperature": 28,
        "humidity": 55,
        "soil_moisture": 45,
        "pressure": 1010
    }
    
    print("\n=== LLM Agent Test ===\n")
    
    print("[FUSION ANALYSIS]")
    print(agent.analyze_sensor_fusion_result(fusion_result))
    print()
    
    print("[RAIN ANALYSIS]")
    print(agent.analyze_rain_prediction(rain_result))
    print()
    
    print("[IRRIGATION DECISION]")
    print(agent.make_irrigation_decision(sensor_data, fusion_result, rain_result))


if __name__ == "__main__":
    main()
