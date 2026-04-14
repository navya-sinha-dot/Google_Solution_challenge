import os
import json
import requests
from typing import TypedDict, Annotated, List, Dict, Any, Optional
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END
from datetime import datetime, timedelta
import joblib
import pandas as pd
from tools import (
    get_latest_weather, get_weather_range, create_alert_rule,
    disable_alert_rule, get_active_alerts, get_system_health,
    get_trends, insert_trend_data, insert_health_data
)
from dotenv import load_dotenv

load_dotenv()

print(f"GROQ_API_KEY in weather_workflow: {os.getenv('GROQ_API_KEY')[:10] if os.getenv('GROQ_API_KEY') else 'None'}")

# Simplified State - LLM-first design
class WeatherState(TypedDict):
    user_id: str
    message: str
    timestamp: str
    response: str
    error: Optional[str]

# Initialize LLM
try:
    llm = ChatGroq(model="llama-3.1-8b-instant", api_key=os.getenv("GROQ_API_KEY"))
    print("LLM initialized successfully")
except Exception as e:
    print(f"LLM initialization failed: {e}")
    llm = None

# ============ TOOL FUNCTIONS (Simple, non-decorated) ============

def get_current_weather_data() -> str:
    """Get the latest weather readings."""
    try:
        sensor_id = "WS01"
        
        # First, try database
        try:
            data = get_latest_weather(sensor_id)
            if data:
                return json.dumps({"status": "success", "data": data})
        except Exception as db_error:
            print(f"Database fallback: {db_error}")
            pass
        
        # Fallback to HTTP sensor endpoint
        try:
            response = requests.get(f"http://localhost:8000/api/sensors/latest/{sensor_id}", timeout=5)
            if response.status_code == 200:
                data = response.json()
                # Map the response fields
                weather_data = {
                    "temperature": data.get("temperature"),
                    "humidity": data.get("humidity"),
                    "pressure": data.get("pressure"),
                    "wind_speed": data.get("windSpeed"),
                    "rainfall": data.get("rainfall"),
                    "soil_temperature": data.get("soilTemperature"),
                    "soil_moisture": data.get("soilMoisture"),
                    "air_quality_pm25": data.get("airQualityPM25"),
                    "light_intensity": data.get("lightIntensity"),
                    "timestamp": data.get("timestamp")
                }
                return json.dumps({"status": "success", "data": weather_data})
        except Exception as http_error:
            print(f"HTTP endpoint fallback failed: {http_error}")
        
        return json.dumps({"status": "error", "message": "No weather data available"})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

def predict_rain_data() -> str:
    """Predict rain probability using RTL logic."""
    return predict_rain_rtl()

def predict_rain_rtl() -> str:
    """Predict rain probability using RTL logic (from rain_predictor.v)."""
    try:
        sensor_id = "WS01"
        latest_data = get_latest_weather(sensor_id)
        
        if not latest_data:
            latest_data = {
                "temperature": 25.0,
                "humidity": 70.0,
                "pressure": 1010.0,
                "wind_speed": 5.0
            }
        
        # Extract values (assuming they are in proper units)
        temp = latest_data.get('temperature', 25.0)
        humid = latest_data.get('humidity', 60.0)
        press = latest_data.get('pressure', 1010.0)
        wind = latest_data.get('wind_speed', 3.0)
        
        # Convert to Q8.8 format (multiply by 256)
        temp_q88 = int(temp * 256)
        humid_q88 = int(humid * 256)
        press_q88 = int(press * 256)  # Note: pressure is in hPa, may need scaling
        wind_q88 = int(wind * 256)
        
        # Constants from RTL
        Q88_70 = 0x4600   # 70.0 * 256
        Q88_100 = 0x6400  # 100.0 * 256
        Q88_50 = 0x3200   # 50.0 * 256
        Q88_30 = 0x1E00   # 30.0 * 256
        Q88_60 = 0x3C00   # 60.0 * 256
        Q88_25 = 0x1900   # 25.0 * 256
        Q88_15 = 0x0F00   # 15.0 * 256
        Q88_85 = 0x5500   # 85.0 * 256
        Q88_40 = 0x2800   # 40.0 * 256
        Q88_80 = 0x5000   # 80.0 * 256
        Q88_95 = 0x5F00   # 95.0 * 256
        Q88_20 = 0x1400   # 20.0 * 256
        Q88_45 = 0x2D00   # 45.0 * 256
        Q88_5 = 0x0500    # 5.0 * 256
        Q88_35 = 0x2300   # 35.0 * 256
        Q88_90 = 0x5A00   # 90.0 * 256
        
        # Rain score calculation
        rain_score = 0
        
        # High humidity contribution
        if humid_q88 > Q88_70:
            rain_score += 35 + ((humid_q88 - Q88_70) // 256)  # 35 + (humid - 70)
        elif humid_q88 > Q88_50:
            rain_score += ((humid_q88 - Q88_50) * 28) // (256 * 16)  # (humid - 50) * 1.75
        
        # Pressure contribution (lower = more rain)
        if press_q88 < Q88_30:
            rain_score += ((Q88_30 - press_q88) * 21) // (256 * 16)  # (30 - press) * 1.33
        elif press_q88 < Q88_50:
            rain_score += ((Q88_50 - press_q88) * 6) // (256 * 16)   # (50 - press) * 0.4
        
        # Temperature contribution
        if temp_q88 >= Q88_15 and temp_q88 <= Q88_25:
            rain_score += 15
        elif temp_q88 > Q88_25 and temp_q88 < Q88_35:
            rain_score += 10
        elif temp_q88 >= Q88_5 and temp_q88 < Q88_15:
            rain_score += 12
        
        # Wind contribution
        if wind_q88 > Q88_5 and wind_q88 < Q88_15:
            rain_score += 10
        elif wind_q88 >= Q88_15:
            rain_score += 8
        
        # Clamp to 0-100
        rain_score = min(max(rain_score, 0), 100)
        
        # Stress level calculation
        stress_score = 0
        
        # Humidity extremes
        if humid_q88 > Q88_90 or humid_q88 < Q88_20:
            stress_score += 25
        elif humid_q88 > Q88_80 or humid_q88 < Q88_30:
            stress_score += 15
        
        # Pressure instability
        if press_q88 < Q88_20:
            stress_score += 30
        elif press_q88 < Q88_30:
            stress_score += 20
        
        # Temperature extremes
        if temp_q88 > 0x2800 or temp_q88 < Q88_5:  # >40 or <5
            stress_score += 20
        elif temp_q88 > Q88_35 or temp_q88 < 0x0500:  # >35 or <5
            stress_score += 10
        
        # Wind extremes
        if wind_q88 > 0x1400:  # >20
            stress_score += 25
        elif wind_q88 > Q88_15:
            stress_score += 15
        
        stress_score = min(max(stress_score, 0), 100)
        
        # Rain alert
        alert = 0
        if rain_score > 60 and press_q88 < Q88_40:
            alert = 1
        if humid_q88 > Q88_85 and press_q88 < Q88_45:
            alert = 1
        if stress_score > 70 and rain_score > 50:
            alert = 1
        
        return json.dumps({
            "status": "success",
            "probability": rain_score,
            "stress_level": stress_score,
            "rain_alert": bool(alert),
            "features": {
                "temperature": temp,
                "humidity": humid,
                "pressure": press,
                "wind_speed": wind
            }
        })
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

def sensor_fusion_analysis() -> str:
    """Perform sensor fusion analysis using RTL logic (from sensor_fusion.v)."""
    try:
        sensor_id = "WS01"
        latest_data = get_latest_weather(sensor_id)
        
        if not latest_data:
            latest_data = {
                "soil_moisture": 50.0,
                "temperature": 25.0,
                "humidity": 60.0,
                "light_level": 50.0
            }
        
        # Extract values (assuming 0-100 range for soil, temp, humid; scale light from lux to 0-100)
        soil = latest_data.get('soil_moisture', 50.0)
        temp = latest_data.get('temperature', 25.0)
        humid = latest_data.get('humidity', 60.0)
        light_lux = latest_data.get('light_intensity', 50000.0)  # Default 50000 lux
        light = min(light_lux / 1000.0, 100.0)  # Scale 0-100000 lux to 0-100
        
        # Convert to Q8.8 (multiply by 256)
        soil_q88 = int(soil * 256)
        temp_q88 = int(temp * 256)
        humid_q88 = int(humid * 256)
        light_q88 = int(light * 256)
        
        # Weights from RTL
        w_soil = 0x0059   # 0.35 * 256
        w_temp = 0x0040   # 0.25 * 256
        w_humid = 0x0033  # 0.20 * 256
        w_light = 0x0033  # 0.20 * 256
        
        # Weighted multiplication (simulate DSP48E1)
        mult_soil = soil_q88 * w_soil
        mult_temp = temp_q88 * w_temp
        mult_humid = humid_q88 * w_humid
        mult_light = light_q88 * w_light
        
        # Sum (two stages)
        sum1 = mult_soil + mult_temp
        sum2 = mult_humid + mult_light
        fusion_full = sum1 + sum2
        
        # Extract Q8.8 result (divide by 256)
        fusion_score = fusion_full // 256
        
        # Stress index: |fusion - 50| * 2
        optimal = 0x3200  # 50.0 * 256
        if fusion_score > 50:
            stress_raw = fusion_score - 50
        else:
            stress_raw = 50 - fusion_score
        stress_index = stress_raw * 2
        
        # Clamp stress to 0-100
        stress_index = min(max(stress_index, 0), 100)
        
        # Alert level based on thresholds
        if stress_index >= 80:
            alert_level = 4  # CRITICAL
        elif stress_index >= 60:
            alert_level = 3  # HIGH
        elif stress_index >= 40:
            alert_level = 2  # MODERATE
        elif stress_index >= 20:
            alert_level = 1  # LOW
        else:
            alert_level = 0  # NONE
        
        return json.dumps({
            "status": "success",
            "fusion_score": fusion_score,
            "stress_index": stress_index,
            "alert_level": alert_level,
            "inputs": {
                "soil_moisture": soil,
                "temperature": temp,
                "humidity": humid,
                "light_intensity": light_lux,
                "light_level_scaled": light
            }
        })
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

def get_system_health_data() -> str:
    """Get system health status."""
    try:
        health = get_system_health()
        return json.dumps({"status": "success", "data": health})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

def get_trends_data() -> str:
    """Get weather trends."""
    try:
        sensor_id = "WS01"
        trends = []
        for metric in ["temperature", "humidity", "pressure"]:
            metric_trends = get_trends(sensor_id, metric, "daily")
            trends.extend(metric_trends)
        return json.dumps({"status": "success", "trends": trends})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

# ============ LLM-FIRST SUPERVISOR NODE ============
# This is now the primary brain

def llm_supervisor(state: WeatherState) -> WeatherState:
    """
    TRUE ReAct Architecture:
    - LLM reasons about what data it needs
    - Calls appropriate tool functions
    - Observes real sensor data
    - Generates response based on actual data from database
    """
    if llm is None:
        return {"response": "Sorry, the AI system is temporarily unavailable."}
    
    import json
    
    user_message = state["message"]
    user_id = state["user_id"]
    user_lower = user_message.lower()
    
    # Check if this is about farming/agriculture advice
    farming_keywords = ["plant", "seed", "crop", "soil", "irrigation", "fertilizer", "harvest", "farm", "agriculture", "grow", "cultivation"]
    is_farming_question = any(keyword in user_lower for keyword in farming_keywords)
    
    # For farming questions, use LLM directly with context
    if is_farming_question:
        try:
            prompt = f"""You are an agricultural advisor with knowledge of farming, crops, and soil management.
            
User is asking about farming/agriculture. They may also have access to real-time weather and soil data from sensors.

User question: "{user_message}"

Provide helpful, practical farming advice. Consider weather and soil conditions if mentioned in the question."""
            
            response = llm.invoke([("user", prompt)])
            return {"response": response.content}
        except Exception as e:
            print(f"[ERROR] Farming advice LLM error: {e}")
            return {"response": "I can help with farming advice, but I'm having technical difficulties. Please try again."}
    
    # STEP 1: ReAct - Reasoning (LLM decides what data is needed)
    reasoning_prompt = f"""You are an intelligent assistant for a REAL agricultural monitoring system with physical sensors.

User question: "{user_message}"

Available data sources:
- get_current_weather: Real-time sensor readings (temperature, humidity, pressure, wind, rain, soil moisture)
- predict_rain: RTL-based rain predictions using sensor fusion
- sensor_fusion: Overall sensor analysis using RTL fusion algorithm
- get_trends: Historical patterns from database

Think step by step:
1. What specific data does the user need?
2. Which tool should I call to get that data?
3. Do I need real sensor data or can I answer from general knowledge?

Respond with ONLY the tool name you need, or "GENERAL" if no tool needed.
Examples:
- "What's the temperature?" → get_current_weather
- "Will it rain?" → predict_rain  
- "How are my crops doing?" → sensor_fusion
- "Show trends" → get_trends

Your response (one word):"""
    
    try:
        reasoning_response = llm.invoke([("user", reasoning_prompt)])
        tool_choice = reasoning_response.content.strip().lower()
        
        # STEP 2: ReAct - Acting (Execute the chosen tool)
        tool_data = None
        observation = None
        
        if "weather" in tool_choice or "current" in tool_choice or "temperature" in user_lower or "humidity" in user_lower:
            print(f"[TOOL] CALLED: get_current_weather_data()")
            observation = get_current_weather_data()
            tool_data = json.loads(observation)
        
        elif "rain" in tool_choice or "rain" in user_lower or "precipitation" in user_lower:
            print(f"[TOOL] CALLED: predict_rain_data()")
            observation = predict_rain_data()
            tool_data = json.loads(observation)
        
        elif "trend" in tool_choice:
            print(f"[TOOL] CALLED: get_trends_data()")
            observation = get_trends_data()
            tool_data = json.loads(observation)
        
        elif "fusion" in tool_choice or "sensor" in tool_choice or "crop" in user_lower or "plant" in user_lower or "health" in user_lower:
            print(f"[TOOL] CALLED: sensor_fusion_analysis()")
            observation = sensor_fusion_analysis()
            tool_data = json.loads(observation)
        
        # STEP 3: ReAct - Observation + Response (LLM uses real data)
        if observation:
            print(f"[OBSERVATION] {observation[:200]}...")
            
            response_prompt = f"""You are an agricultural monitoring assistant with access to REAL sensor data from RTL-based analysis.

User asked: "{user_message}"

REAL DATA from our sensors and RTL analysis:
{observation}

Provide a natural, helpful response using these ACTUAL values from our FPGA-accelerated sensor fusion. Be specific with the numbers and analysis results."""
        else:
            # No tool needed - general knowledge
            print(f"[GENERAL] KNOWLEDGE response (no tool needed)")
            response_prompt = user_message
        
        final_response = llm.invoke([("user", response_prompt)])
        return {"response": final_response.content}
        
    except Exception as e:
        print(f"[ERROR] Error in ReAct supervisor: {e}")
        import traceback
        traceback.print_exc()
        
        # Fallback: keyword-based tool selection
        if "rain" in user_lower:
            data = predict_rain_data()
            return {"response": f"Rain Forecast:\n{data}"}
        elif any(word in user_lower for word in ["temp", "weather", "humidity", "wind", "pressure"]):
            data = get_current_weather_data()
            return {"response": f"Current Readings:\n{data}"}
        elif "trend" in user_lower:
            data = get_trends_data()
            return {"response": f"Trends:\n{data}"}
        elif "health" in user_lower or "sensor" in user_lower or "crop" in user_lower or "plant" in user_lower:
            data = sensor_fusion_analysis()
            return {"response": f"Overall Analysis:\n{data}"}
        else:
            try:
                response = llm.invoke([("user", user_message)])
                return {"response": response.content}
            except Exception as fallback_err:
                print(f"[FALLBACK ERROR] LLM unavailable: {fallback_err}")
                # If LLM fails, provide helpful generic response
                return {"response": f"I'm having trouble reaching my AI right now, but I can help with: weather questions, rain forecasts, agricultural trends, or system status. What would you like to know?"}
        return {"response": f"I encountered an error processing your request: {str(e)}"}

# ============ BUILD GRAPH ============

graph = StateGraph(WeatherState)
graph.add_node("llm_supervisor", llm_supervisor)
graph.add_edge(START, "llm_supervisor")
graph.add_edge("llm_supervisor", END)

compiled_graph = graph.compile()

if __name__ == "__main__":
    # Test the LLM-first workflow
    test_messages = [
        "Will it rain today?",
        "What's the current temperature?",
        "Explain why pressure drops before rain",
    ]
    
    for msg in test_messages:
        print(f"\n{'='*60}")
        print(f"User: {msg}")
        print('='*60)
        
        try:
            result = compiled_graph.invoke({
                "user_id": "test_user",
                "message": msg,
                "timestamp": datetime.now().isoformat(),
                "response": "",
                "error": None
            })
            
            print(f"Assistant: {result.get('response')}")
        except Exception as e:
            print(f"Error: {e}")
