"""
Agricultural Q&A Assistant
Handles farmer questions about sensor data with LLM-powered responses
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple
from langchain_groq import ChatGroq
from dotenv import load_dotenv
import json

load_dotenv()
logger = logging.getLogger(__name__)

class AgriculturalQAAssistant:
    """
    LLM-powered Q&A assistant for agricultural data.
    Processes farmer questions and provides data-driven answers with suggestions.
    """
    
    def __init__(self):
        """Initialize the Q&A assistant with Groq LLM"""
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            logger.warning("⚠️ GROQ_API_KEY not set - Q&A assistant disabled")
            self.llm = None
            return
        
        try:
            self.llm = ChatGroq(
                temperature=0.25,
                model_name="llama-3.1-8b-instant",
                api_key=api_key
            )
            logger.info("✅ Agricultural Q&A Assistant initialized (Groq)")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Q&A assistant: {e}")
            self.llm = None
    
    def analyze_question(self, question: str) -> Dict[str, Any]:
        """
        Analyze farmer's question to understand intent
        
        Returns:
            Dictionary with intent, keywords, and data_type needed
        """
        if not self.llm:
            return {
                "intent": "unknown",
                "keywords": [],
                "data_type": "general"
            }
        
        try:
            analysis_prompt = f"""Analyze this agricultural question and identify:
1. The farmer's main intent (check_health, optimize_irrigation, plan_planting, weather_forecast, pest_alert, etc.)
2. Key topics mentioned (soil, water, temperature, humidity, rainfall, crop, disease, etc.)
3. What type of data would be helpful (current, historical, forecast, etc.)

Question: "{question}"

Respond in JSON format:
{{
    "intent": "...",
    "keywords": [...],
    "data_type": "..."
}}"""
            
            response = self.llm.invoke(analysis_prompt)
            
            try:
                # Extract JSON from response
                import json
                json_str = response.content
                if '```json' in json_str:
                    json_str = json_str.split('```json')[1].split('```')[0]
                elif '```' in json_str:
                    json_str = json_str.split('```')[1].split('```')[0]
                
                return json.loads(json_str)
            except:
                return {
                    "intent": "general_query",
                    "keywords": question.lower().split(),
                    "data_type": "current"
                }
        except Exception as e:
            logger.warning(f"Error analyzing question: {e}")
            return {
                "intent": "unknown",
                "keywords": [],
                "data_type": "general"
            }
    
    def generate_response(self, 
                         question: str, 
                         sensor_data: Dict[str, Any],
                         llm_analysis: Dict[str, Any] = None,
                         historical_data: List[Dict] = None) -> Tuple[str, List[str]]:
        """
        Generate response based on question and available data
        
        Returns:
            Tuple of (response_text, suggestions)
        """
        if not self.llm:
            # Fallback response
            return self._generate_fallback_response(question, sensor_data)
        
        try:
            # Build context from sensor data
            context = self._format_sensor_context(sensor_data, llm_analysis, historical_data)
            
            prompt = f"""You are AgroBot, a highly efficient expert agricultural advisor replying via WhatsApp.
Use ALL available sensor readings and FPGA/accelerator analysis to generate a detailed advisory.

FARM DATA:
{context}

FARMER'S QUESTION:
{question}

Instructions:
- Begin with a direct answer to the farmer's question.
- Use the exact sensor readings from FARM DATA, and NEVER invent values.
- Provide a detailed advisory that includes: Summary, Condition, Recommendation, and Risk assessment.
- Bold ONLY the most important numeric values using markdown bold, such as critical thresholds or values that drive the recommendation. Leave other numbers unchanged.
- Keep the language clear, practical, and actionable for a farmer.
- Use plain WhatsApp text only: no code blocks, no JSON, no tables.

Example structure:
Summary: ...
Condition: ...
Recommendation: ...
Risk: ...
"""
            response = self.llm.invoke(prompt)
            answer_text = response.content
            
            # Parse response
            suggestions = []
            if "SUGGESTIONS:" in answer_text:
                suggestions_section = answer_text.split("SUGGESTIONS:")[1].split("ALERTS:")[0]
                suggestions = [s.strip().lstrip("- ") for s in suggestions_section.strip().split("\n") if s.strip().startswith("-")]
            
            return answer_text, suggestions
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return self._generate_fallback_response(question, sensor_data)
    
    def _format_sensor_context(self, 
                              sensor_data: Dict[str, Any],
                              llm_analysis: Dict[str, Any] = None,
                              historical_data: List[Dict] = None) -> str:
        """Format sensor data for LLM context"""
        context = "CURRENT READINGS:\n"
        
        # Current environmental values
        if "env" in sensor_data:
            env = sensor_data["env"]
            context += f"- Temperature: {env.get('t', 'N/A')}°C\n"
            context += f"- Humidity: {env.get('h', 'N/A')}%\n"
            context += f"- Pressure: {env.get('p', 'N/A')} hPa\n"
            if env.get('dew_point') is not None:
                context += f"- Dew Point: {env.get('dew_point')}°C\n"
        
        # Soil values
        if "soil" in sensor_data:
            soil = sensor_data["soil"]
            context += f"- Soil Temperature: {soil.get('t', 'N/A')}°C\n"
            context += f"- Soil Moisture: {soil.get('m', 'N/A')}%\n"
            if soil.get('ec') is not None:
                context += f"- Soil EC: {soil.get('ec', 'N/A')} mS/cm\n"
        
        # Wind values
        if "wind" in sensor_data:
            wind = sensor_data["wind"]
            context += f"- Wind Speed: {wind.get('s', 'N/A')} m/s\n"
            context += f"- Wind Direction: {wind.get('d', 'N/A')}\n"
            if wind.get('gust') is not None:
                context += f"- Wind Gust: {wind.get('gust', 'N/A')} m/s\n"
        
        # Rain and light values
        if "rain" in sensor_data:
            rain = sensor_data["rain"]
            context += f"- Rainfall: {rain.get('mm', 'N/A')} mm\n"
            context += f"- Rain Rate: {rain.get('rate', 'N/A')} mm/h\n"
        if "light" in sensor_data:
            light = sensor_data["light"]
            context += f"- Light Intensity: {light.get('lux', 'N/A')} lux\n"
            context += f"- PAR: {light.get('par', 'N/A')}\n"
        
        # Air quality and power
        if "air_quality" in sensor_data:
            air = sensor_data["air_quality"]
            context += f"- PM2.5: {air.get('pm25', 'N/A')} µg/m3\n"
            context += f"- PM10: {air.get('pm10', 'N/A')} µg/m3\n"
        if "uv_index" in sensor_data:
            context += f"- UV Index: {sensor_data.get('uv_index', 'N/A')}\n"
        if "power" in sensor_data:
            power = sensor_data["power"]
            context += f"- Battery Voltage: {power.get('battery_voltage', 'N/A')} V\n"
            context += f"- Solar Voltage: {power.get('solar_voltage', 'N/A')} V\n"
        
        # FPGA / accelerator analysis
        if "accelerator_results" in sensor_data:
            acc = sensor_data["accelerator_results"]
            context += f"\nFPGA ANALYSIS:\n"
            context += f"- Plant Health Score: {acc.get('sf_score', 'N/A')}/100\n"
            context += f"- Stress Level: {acc.get('sf_stress', 'N/A')}/100\n"
            context += f"- Rain Probability: {acc.get('rp_probability', 'N/A')}%\n"
            if acc.get('alert_level') is not None:
                context += f"- Alert Level: {acc.get('alert_level')}\n"
        
        # LLM Insights
        if llm_analysis and "decision" in llm_analysis:
            context += f"\nAI INSIGHTS:\n{llm_analysis['decision']}\n"
        
        # Historical trends
        if historical_data:
            context += "\nRECENT TRENDS (Last 24 hours):\n"
            if len(historical_data) > 0:
                avg_temp = sum(d.get('temperature', 0) for d in historical_data) / len(historical_data)
                avg_humid = sum(d.get('humidity', 0) for d in historical_data) / len(historical_data)
                context += f"- Average Temperature: {avg_temp:.1f}°C\n"
                context += f"- Average Humidity: {avg_humid:.1f}%\n"
                if any(d.get('rainfall') is not None for d in historical_data):
                    avg_rain = sum(d.get('rainfall', 0) for d in historical_data) / len(historical_data)
                    context += f"- Average Rainfall: {avg_rain:.1f} mm\n"
        
        return context
    
    def _generate_fallback_response(self, question: str, sensor_data: Dict[str, Any]) -> Tuple[str, List[str]]:
        """Generate response without LLM"""
        suggestions = []
        
        # Basic rule-based responses
        answer = "I'm analyzing your farm data to answer your question.\n\n"
        
        if any(word in question.lower() for word in ["water", "irrigation", "moisture"]):
            soil_moisture = sensor_data.get("soil", {}).get("m", 0)
            if soil_moisture < 30:
                answer += f"Your soil moisture is low ({soil_moisture}%). Consider irrigation soon."
                suggestions = [
                    "Increase irrigation frequency",
                    "Monitor soil moisture daily",
                    "Check irrigation system for leaks"
                ]
            elif soil_moisture > 70:
                answer += f"Your soil moisture is adequate ({soil_moisture}%). Avoid overwatering."
                suggestions = [
                    "Reduce irrigation frequency",
                    "Ensure proper drainage",
                    "Monitor weather for rain"
                ]
        
        elif any(word in question.lower() for word in ["temperature", "heat", "cold"]):
            temp = sensor_data.get("env", {}).get("t", 0)
            answer += f"Current temperature is {temp}°C. "
            if temp < 15:
                answer += "This is cold for most crops."
                suggestions = ["Protect crops from cold", "Monitor for frost damage", "Prepare frost protection"]
            elif temp > 35:
                answer += "This is hot for most crops."
                suggestions = ["Increase irrigation", "Provide shade if possible", "Monitor for heat stress"]
            else:
                answer += "This is optimal for most crops."
                suggestions = ["Continue current care routine", "Monitor for pests", "Maintain irrigation schedule"]
        
        else:
            answer += "I see you're asking about your farm. Based on current conditions, everything appears to be within normal ranges. "
            suggestions = [
                "Monitor soil moisture regularly",
                "Check weather forecast",
                "Inspect crops for pests or disease"
            ]
        
        return answer, suggestions
    
    def extract_intent_data_needs(self, question: str) -> Dict[str, Any]:
        """Determine what database queries are needed to answer the question"""
        keywords = question.lower().split()
        
        needs = {
            "current_data": True,  # Always need current data
            "historical_data": any(word in keywords for word in ["trend", "average", "change", "last", "past"]),
            "forecast_data": any(word in keywords for word in ["forecast", "predict", "rain", "storm", "weather"]),
            "anomalies": any(word in keywords for word in ["unusual", "strange", "wrong", "problem", "alert"])
        }
        
        return needs
