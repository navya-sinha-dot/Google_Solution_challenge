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
                    "timestamp": data.get("timestamp")
                }
                return json.dumps({"status": "success", "data": weather_data})
        except Exception as http_error:
            print(f"HTTP endpoint fallback failed: {http_error}")
        
        return json.dumps({"status": "error", "message": "No weather data available"})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

def predict_rain_data() -> str:
    """Predict rain probability using ML model."""
    try:
        # Try to load the rain model
        try:
            model = joblib.load('rain_model.pkl')
        except:
            # Fallback if model not available
            print("Warning: rain_model.pkl not found, using simulation")
            return json.dumps({"status": "success", "probability": 25.0, "note": "simulated"})
        
        sensor_id = "WS01"
        latest_data = get_latest_weather(sensor_id)
        
        if not latest_data:
            latest_data = {
                "temperature": 25.0,
                "humidity": 70.0,
                "pressure": 1010.0,
                "wind_speed": 5.0
            }
        
        try:
            end = datetime.now()
            start = end - timedelta(hours=1)
            recent_data = get_weather_range(sensor_id, start.isoformat(), end.isoformat())
            
            if len(recent_data) >= 2:
                pressures = [d.get('pressure') for d in recent_data if d.get('pressure') is not None]
                pressure_change = pressures[-1] - pressures[0] if len(pressures) >= 2 else 0
            else:
                pressure_change = 0
        except:
            pressure_change = 0
        
        features = {
            'temperature': latest_data.get('temperature', 25),
            'humidity': latest_data.get('humidity', 60),
            'pressure': latest_data.get('pressure', 1010),
            'wind_speed': latest_data.get('wind_speed', 3),
            'hour': datetime.now().hour,
            'pressure_change_30min': pressure_change
        }
        
        df = pd.DataFrame([features])
        prob = model.predict_proba(df)[0][1]
        
        return json.dumps({
            "status": "success",
            "probability": round(prob * 100, 1),
            "features": features
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
    reasoning_prompt = f"""You are an intelligent assistant for a REAL weather monitoring system with physical sensors.

User question: "{user_message}"

Available data sources:
- get_current_weather: Real-time sensor readings (temperature, humidity, pressure, wind, rain)
- predict_rain: ML model predictions based on current conditions
- get_trends: Historical patterns from database
- get_system_health: Sensor status and battery levels

Think step by step:
1. What specific data does the user need?
2. Which tool should I call to get that data?
3. Do I need real sensor data or can I answer from general knowledge?

Respond with ONLY the tool name you need, or "GENERAL" if no tool needed.
Examples:
- "What's the temperature?" → get_current_weather
- "Will it rain?" → predict_rain  
- "Why does pressure drop?" → GENERAL
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
        
        elif "health" in tool_choice or "status" in tool_choice or "sensor" in user_lower:
            print(f"[TOOL] CALLED: get_system_health_data()")
            observation = get_system_health_data()
            tool_data = json.loads(observation)
        
        # STEP 3: ReAct - Observation + Response (LLM uses real data)
        if observation:
            print(f"[OBSERVATION] {observation[:200]}...")
            
            response_prompt = f"""You are a weather monitoring assistant with access to REAL sensor data.

User asked: "{user_message}"

REAL DATA from our sensors/system:
{observation}

Provide a natural, helpful response using these ACTUAL values. Be specific with the numbers and readings."""
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
        elif "health" in user_lower or "sensor" in user_lower:
            data = get_system_health_data()
            return {"response": f"System Status:\n{data}"}
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
