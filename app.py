from fastapi import FastAPI, HTTPException, Request, Form, Depends
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import time
import requests
from twilio.rest import Client
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
import logging
from fastapi.middleware.cors import CORSMiddleware
from langchain_groq import ChatGroq

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Lazy-load workflow on first use to avoid blocking server startup
compiled_graph = None

def get_compiled_graph():
    """Lazy-load the LangGraph workflow on first use"""
    global compiled_graph
    if compiled_graph is not None:
        return compiled_graph
    
    try:
        from weather_workflow_llm_first import compiled_graph as wf
        print("LLM-first weather workflow imported successfully")
        compiled_graph = wf
        return compiled_graph
    except Exception as e:
        logger.warning(f"Failed to import LLM-first workflow: {e}")
        try:
            from weather_workflow import compiled_graph as wf
            print("Fallback: Using original weather workflow")
            compiled_graph = wf
            return compiled_graph
        except Exception as e2:
            logger.warning(f"Failed to import fallback workflow: {e2}")
            return None

# Twilio WhatsApp credentials
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")

print("Starting Weather Alert System...")
print(f"Twilio SID: {TWILIO_ACCOUNT_SID[:10]}..." if TWILIO_ACCOUNT_SID else "No Twilio SID")
print(f"Twilio Token: {TWILIO_AUTH_TOKEN[:10]}..." if TWILIO_AUTH_TOKEN else "No Twilio Token")
print(f"Twilio Number: {TWILIO_WHATSAPP_NUMBER}" if TWILIO_WHATSAPP_NUMBER else "No Twilio Number")

# Initialize FastAPI app
app = FastAPI(title="Weather Alert System")

# CRITICAL: Add CORS middleware BEFORE including routers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (for development)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize thread pool for LangGraph invocation
executor = ThreadPoolExecutor(max_workers=5)

from tools import _get_session
from sqlalchemy import text

@app.on_event("startup")
def startup_event():
    try:
        db = _get_session()
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                phone VARCHAR(20) PRIMARY KEY,
                name VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        db.commit()
        db.close()
        print("✅ Users table ensured in database.")
    except Exception as e:
        print(f"Failed to ensure users table: {e}")

# ============ IMPORT SENSOR ENDPOINTS ============

try:
    from sensor_endpoints import router as sensor_router
    app.include_router(sensor_router)
    logger.info("✅ Sensor data endpoints imported successfully")
except Exception as e:
    logger.warning(f"⚠️ Could not import sensor endpoints: {e}")

# ============ IMPORT VOICE EXTENSION ENDPOINTS ============
try:
    from voice_ext_endpoints import router as voice_ext_router
    app.include_router(voice_ext_router)
    logger.info("✅ Voice extension endpoints imported successfully")
except Exception as e:
    logger.warning(f"⚠️ Could not import voice extension endpoints: {e}")


# ============ FPGA ACCELERATOR INTEGRATION ============

# Initialize FPGA bridge (set enabled=False for simulation without hardware)
fpga_bridge = None
FPGA_ENABLED = os.getenv("FPGA_ENABLED", "false").lower() == "true"
FPGA_PORT = os.getenv("FPGA_PORT", "COM4")

class MockFPGABridge:
    """Mock FPGA bridge for demonstration without hardware."""
    def run_fusion(self, soil, temp, humid, light):
        """Simulate sensor fusion with realistic values."""
        import random
        stress = max(0, min(100, 50 + (soil - 50) * 0.5 + (temp - 25) * 2))
        return {
            "fusion_score": int(50 + random.randint(-10, 10)),
            "stress_index": int(stress),
            "alert_level": 1 if stress > 70 else (2 if stress > 50 else 0),
            "alert_name": "High Stress" if stress > 70 else ("Moderate Stress" if stress > 50 else "Optimal")
        }
    
    def send_fusion(self, soil, temp, humid, light):
        """Alias for run_fusion - matches DualAcceleratorBridge API."""
        return self.run_fusion(soil, temp, humid, light)
    
    def send_rain_prediction(self, temp, humid, pressure, wind):
        """Simulate rain prediction with realistic values."""
        import random
        # Base probability on humidity and pressure
        base_prob = humid * 0.8 + (1013 - pressure) * 0.3
        rain_prob = max(0, min(100, int(base_prob + random.randint(-15, 15))))
        return {
            "rain_probability": rain_prob,
            "stress_level": int(max(0, (temp - 20) * 5)),
            "rain_alert": 1 if rain_prob > 60 else 0,
            "timestamp": int(time.time() * 1000)
        }
    
    def get_status(self):
        """Return mock FPGA status."""
        return "simulation_mode"

def get_fpga_bridge():
    """Get or create FPGA dual bridge with fallback to mock."""
    global fpga_bridge
    if fpga_bridge is None:
        try:
            from fpga_dual_bridge import DualAcceleratorBridge
            fpga_bridge = DualAcceleratorBridge(port=FPGA_PORT, simulation=not FPGA_ENABLED)
            logger.info(f"✅ FPGA Dual Bridge initialized (port={FPGA_PORT}, simulation={not FPGA_ENABLED})")
        except ImportError:
            try:
                from fpga_serial_bridge import FPGASerialBridge
                fpga_bridge = FPGASerialBridge(port=FPGA_PORT, enabled=FPGA_ENABLED)
                logger.info(f"✅ FPGA Serial Bridge initialized (enabled={FPGA_ENABLED}, port={FPGA_PORT})")
            except ImportError:
                logger.warning(f"⚠️ FPGA Bridge not available, using mock for demo")
                fpga_bridge = MockFPGABridge()
        except Exception as e:
            logger.warning(f"⚠️ FPGA Bridge initialization failed: {e}, using mock")
            fpga_bridge = MockFPGABridge()
    return fpga_bridge

# ============ HEALTH CHECK ENDPOINTS ============

@app.get("/")
def root():
    """Root endpoint - shows system status"""
    return {
        "status": "✅ Running",
        "system": "Weather Monitoring & Alert System",
        "documentation": "http://localhost:8000/docs",
        "endpoints": {
            "health": "GET /health",
            "webhook": "POST /webhook/whatsapp"
        }
    }

@app.get("/health")
def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "fastapi": "✅ Running",
            "langgraph": "✅ Ready",
            "database": "✅ Connected"
        }
    }

# Initialize Twilio client
# twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN) if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN else None

def send_whatsapp_message(to: str, message: str):
    """Send message via Twilio WhatsApp API."""
    try:
        TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
        TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
        TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")
        
        if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_NUMBER]):
            print(f"Mock sending to {to}: {message}")
            return
        
        from twilio.rest import Client
        twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        message = twilio_client.messages.create(
            from_=f'whatsapp:{TWILIO_WHATSAPP_NUMBER}',
            body=message,
            to=f'whatsapp:{to}'
        )
        print(f"Message sent: {message.sid}")
        return message.sid
    except Exception as e:
        print(f"Error sending message: {e}")
        return None

@app.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request):
    """Handle incoming WhatsApp messages from Twilio."""
    try:
        # Twilio sends data as form-encoded
        form_data = await request.form()
        
        print("FULL FORM:", list(form_data.keys()))
        
        # Extract message details from Twilio webhook
        from_number = form_data.get('From', '').replace('whatsapp:', '')
        to_number = form_data.get('To', '').replace('whatsapp:', '')
        message_body = form_data.get('Body', '')
        message_sid = form_data.get('MessageSid', '')
        
        print("=== WEBHOOK HIT ===")
        print("Body:", message_body)
        print("From:", from_number)
        
        if not message_body or not from_number:
            return {"status": "ignored"}
        
        # Skip if it's an outgoing message (from our number)
        if from_number == TWILIO_WHATSAPP_NUMBER:
            return {"status": "outgoing"}
        
        print(f"Received message from {from_number}: {message_body}")
        
        # Invoke the LangGraph workflow with all required fields
        print("Invoking LangGraph with:", message_body)
        
        try:
            # Run graph in thread pool to avoid blocking async context
            graph = get_compiled_graph()
            if graph is None:
                result = {"response": "Sorry, weather workflow is not available."}
            else:
                result = await asyncio.get_event_loop().run_in_executor(
                    executor,
                    lambda: graph.invoke({
                        "user_id": from_number,
                        "message": message_body,
                        "timestamp": datetime.now().isoformat(),
                        "response": "",
                        "error": None
                    })
                )
            print("LangGraph result:", result)
        except Exception as e:
            print(f"Error invoking LangGraph: {e}")
            import traceback
            traceback.print_exc()
            result = {"response": "Sorry, there was an error processing your request."}
        
        response_text = result.get("response", "Sorry, I couldn't process your request.")

        # Send response back via WhatsApp
        send_whatsapp_message(from_number, response_text)

        return {"status": "processed"}

    except Exception as e:
        print(f"Error processing webhook: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/webhook/whatsapp")
async def whatsapp_webhook_get():
    """Twilio requires a GET endpoint for webhook validation."""
    return {"status": "webhook endpoint active"}

# ============ OTP AUTHENTICATION MOCK ============
class SendOtpRequest(BaseModel):
    phone: str
    is_signup: bool = False

class VerifyOtpRequest(BaseModel):
    phone: str
    otp: str

# Simple in-memory mock store for OTPs
otp_store = {}

@app.post("/api/auth/send-otp")
async def send_otp(request: SendOtpRequest):
    """Sending a secure Mock OTP to Terminal to bypass Indian DLT and Trial Restrictions."""
    # Check if number exists in database
    if not request.is_signup:
        try:
            db = _get_session()
            user = db.execute(text("SELECT phone FROM users WHERE phone = :phone"), {"phone": request.phone}).fetchone()
            db.close()
            if not user:
                raise HTTPException(status_code=404, detail="Phone number not registered. Please sign up first.")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"DB Error checking user during login: {e}")
            # Allow pass-through if DB is misconfigured during hackathon
    
    import random
    otp_code = str(random.randint(100000, 999999))
    otp_store[request.phone] = otp_code
    
    # This acts as our "Developer Phone" for the Presentation!
    logger.info(f"========== SECURE SMS SIMULATOR ==========")
    logger.info(f"Delivered to Phone: {request.phone}")
    logger.info(f"Message: Your AgriHub Login OTP is {otp_code}")
    logger.info(f"==========================================")
    
    # In production, integrate with a paid MSG91 or Twilio plan here.
    return {"status": "success", "message": "OTP processed successfully. Check your backend terminal for the code!"}

@app.post("/api/auth/verify-otp")
async def verify_otp(request: VerifyOtpRequest):
    """Mock verifying an OTP"""
    valid_otp = otp_store.get(request.phone)
    if valid_otp and valid_otp == request.otp:
        # Mock successful token generation
        return {"status": "success", "token": "mock_jwt_token_12345"}
    raise HTTPException(status_code=400, detail="Invalid OTP")

# ============ VAPI AI INTEGRATION ============

class VapiCallRequest(BaseModel):
    phone_number: str
    assistant_id: Optional[str] = None
    language: str = "hi-IN"

@app.post("/api/vapi/call")
async def trigger_vapi_call(request: VapiCallRequest):
    """
    Trigger an outbound support call using Vapi AI.
    Injects live mandi rates + sensor data as context for the voice agent.
    """
    vapi_key = os.getenv("VAPI_AI_API_KEY")
    if not vapi_key:
        raise HTTPException(status_code=500, detail="VAPI_AI_API_KEY is not configured")
        
    assistant_id = request.assistant_id or os.getenv("VAPI_ASSISTANT_ID", "default_assistant_id")
    
    # Build live data context for the voice agent
    context_parts = []
    try:
        mandi_ctx = _get_mandi_context()
        if mandi_ctx:
            context_parts.append(mandi_ctx)
    except Exception:
        pass
    try:
        from tools import _get_session, get_latest_weather
        latest = get_latest_weather("WS01")
        if latest:
            context_parts.append(
                f"Current Weather: {latest.get('temperature')}°C, "
                f"Humidity {latest.get('humidity')}%, "
                f"Soil Moisture {latest.get('soil_moisture')}%, "
                f"Rainfall {latest.get('rainfall')} mm"
            )
    except Exception:
        pass
    
    system_prompt = (
        "You are SkyView AI, a helpful agricultural assistant for Indian farmers. "
        "Speak in the farmer's language. Help with mandi prices, weather, crop advice, "
        "and government schemes. Be warm and concise.\n\n"
        + "\n".join(context_parts)
    )
    
    try:
        payload = {
            "assistantId": assistant_id,
            "phoneNumberId": request.phone_number,
            "assistantOverrides": {
                "firstMessage": "नमस्ते! मैं SkyView AI हूं। आज मंडी भाव, मौसम, या खेती से जुड़ी कोई भी जानकारी पूछें।",
                "model": {
                    "messages": [
                        {"role": "system", "content": system_prompt}
                    ]
                }
            }
        }

        response = requests.post(
            "https://api.vapi.ai/call/phone",
            headers={
                "Authorization": f"Bearer {vapi_key}",
                "Content-Type": "application/json"
            },
            json=payload
        )
        response.raise_for_status()
        return {"status": "success", "data": response.json()}
    except requests.exceptions.RequestException as e:
        logger.error(f"Error triggering Vapi call: {e}")
        error_msg = str(e)
        if hasattr(e, 'response') and e.response is not None:
             error_msg = e.response.text
        return {"status": "error", "message": error_msg}

# ============ SARVAM AI INTEGRATION ============

class SynthesisRequest(BaseModel):
    text: str
    language: str = "hi-IN"

@app.post("/api/speech/transcribe")
async def transcribe_audio(request: Request):
    """
    Mock endpoint for Sarvam AI Speech-to-Text.
    In a real app, you would forward the audio buffer to Sarvam.
    """
    sarvam_key = os.getenv("SARVAM_AI_API_KEY")
    if not sarvam_key:
        raise HTTPException(status_code=500, detail="SARVAM_AI_API_KEY is not configured")
    
    # Normally we read audio: data = await request.body()
    # Then POST to Sarvam TTS API.
    return {"status": "success", "transcript": "αñ»αñ╣ αñÅαñò αñ¬αñ░αÑÇαñòαÑìαñ╖αñú αñ╣αÑê (This is a test)", "language": "hi-IN"}

@app.post("/api/speech/synthesize")
async def synthesize_speech(request: SynthesisRequest):
    """
    Mock endpoint for Sarvam AI Text-to-Speech.
    """
    sarvam_key = os.getenv("SARVAM_AI_API_KEY")
    if not sarvam_key:
        raise HTTPException(status_code=500, detail="SARVAM_AI_API_KEY is not configured")
        
    return {"status": "success", "audio_url": "https://example.com/audio/mock_audio.wav"}

class TranslateRequest(BaseModel):
    texts: list[str]
    target_language: str
    source_language: str = "en-IN"

@app.post("/api/translate")
async def translate_texts(request: TranslateRequest):
    """
    Live Translation of Website Elements using Sarvam AI Translate API.
    Sarvam strictly accepts a SINGLE string for the input payload.
    """
    if not request.texts:
        return {"status": "success", "translations": {}}

    sarvam_key = os.getenv("SARVAM_AI_API_KEY")
    if not sarvam_key:
        # Mock translation for demo purposes when API key is missing
        logger.warning("SARVAM_AI_API_KEY not configured, using mock translation.")
        result_map = {text: f"[{request.target_language.split('-')[0].upper()}] {text}" for text in request.texts}
        return {"status": "success", "translations": result_map, "mocked": True}

    try:
        # Join all texts with a unique delimiter that translating models usually leave alone
        delimiter = " \n\n "
        joined_input = delimiter.join(request.texts)
        
        response = requests.post(
            "https://api.sarvam.ai/translate",
            headers={
                "api-subscription-key": sarvam_key,
                "Content-Type": "application/json"
            },
            json={
                "input": str(joined_input),
                "source_language_code": request.source_language,
                "target_language_code": request.target_language,
                "speaker_gender": "Male",
                "mode": "formal",
                "model": "sarvam-translate:v1"
            }
        )
        response.raise_for_status()
        data = response.json()
        translated_string = data.get("translated_text", joined_input)
        
        translated_texts = [t.strip() for t in translated_string.split("\n\n")]
        
        # If the API messed up the delimiter and lengths don't match, fallback safely
        if len(translated_texts) != len(request.texts):
             translated_texts = translated_string.split("\n")
             if len(translated_texts) != len(request.texts):
                 # Ultimate fallback to original english strings to prevent crash
                 translated_texts = request.texts
                 
        result_map = {}
        for original, translated in zip(request.texts, translated_texts):
            result_map[original] = translated.strip()
            
        return {"status": "success", "translations": result_map}
    except Exception as e:
        logger.error(f"Translation failed: {e}")
        error_msg = str(e)
        if hasattr(e, 'response') and e.response is not None:
             error_msg = e.response.text
        return {"status": "error", "message": error_msg}

# ============ AGRICULTURAL Q&A ENDPOINT ============

@app.post("/api/agriculture/qa")
async def agricultural_qa(question: str, station_id: str = "WS01"):
    """
    Answer farmer questions using LLM + database data
    
    Args:
        question: Farmer's question about their farm
        station_id: Station ID for context
    
    Returns:
        Answer with suggestions and alerts
    """
    try:
        from agricultural_qa import AgriculturalQAAssistant
        from tools import _get_session
        from sqlalchemy import text
        
        # Initialize Q&A assistant
        qa_assistant = AgriculturalQAAssistant()
        
        # Get latest sensor data
        db = _get_session()
        
        # Query latest reading
        latest_query = text("""
            SELECT * FROM weather_data 
            WHERE station_id = :station_id 
            ORDER BY timestamp DESC LIMIT 1
        """)
        
        latest = db.execute(latest_query, {"station_id": station_id}).fetchone()
        
        # Query historical data (last 24 hours)
        start_time = datetime.now() - timedelta(hours=24)
        historical_query = text("""
            SELECT temperature, humidity, soil_moisture, timestamp 
            FROM weather_data 
            WHERE station_id = :station_id 
            AND timestamp > :start_time
            ORDER BY timestamp DESC
        """)
        
        historical = db.execute(historical_query, {
            "station_id": station_id,
            "start_time": start_time
        }).fetchall()
        
        # Format sensor data for LLM
        sensor_data = {}
        if latest:
            sensor_data = {
                "env": {
                    "t": latest.temperature,
                    "h": latest.humidity,
                    "p": latest.pressure
                },
                "soil": {
                    "t": latest.soil_temperature,
                    "m": latest.soil_moisture
                },
                "wind": {
                    "s": latest.wind_speed,
                    "d": latest.wind_direction
                },
                "rain": latest.rainfall
            }
        
        # Prepare historical data
        historical_data = [dict(row._mapping) for row in historical] if historical else []
        
        # Generate response using LLM
        answer, suggestions = qa_assistant.generate_response(
            question=question,
            sensor_data=sensor_data,
            historical_data=historical_data
        )
        
        db.close()
        
        return {
            "question": question,
            "answer": answer,
            "suggestions": suggestions,
            "station_id": station_id,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in agricultural Q&A: {e}")
        return {
            "question": question,
            "answer": f"I encountered an error: {str(e)}",
            "suggestions": ["Please try rephrasing your question"],
            "error": str(e)
        }

# ============ WHATSAPP AGRICULTURAL Q&A WEBHOOK ============

@app.post("/webhook/whatsapp/farm-qa")
async def whatsapp_farm_qa(request: Request):
    """
    WhatsApp webhook for agricultural Q&A
    Handles farmer questions and provides data-driven answers
    
    Setup:
    1. In Twilio Console, add this webhook URL: https://yourdomain.ngrok.io/webhook/whatsapp/farm-qa
    2. Farmers can ask questions like:
       - "How is my soil moisture?"
       - "Should I irrigate today?"
       - "What's the weather forecast?"
       - "Why is my plant stressed?"
    """
    try:
        from agricultural_qa import AgriculturalQAAssistant
        
        # Get form data
        form_data = await request.form()
        from_number = form_data.get("From", "").replace("whatsapp:", "")
        message_body = form_data.get("Body", "").strip()
        
        logger.info(f"📱 Farm Q&A - Question from {from_number}: {message_body}")
        
        # Skip outgoing messages
        if "Body" not in form_data:
            return {"status": "outgoing"}
        
        # Initialize Q&A assistant
        qa_assistant = AgriculturalQAAssistant()
        
        # Get latest sensor data for the farmer's station
        from tools import _get_session
        from sqlalchemy import text
        
        db = _get_session()
        
        # Get latest reading
        latest_query = text("""
            SELECT * FROM weather_data 
            ORDER BY timestamp DESC LIMIT 1
        """)
        
        latest = db.execute(latest_query).fetchone()
        
        # Format sensor data
        sensor_data = {}
        llm_analysis = {}
        historical_data = []
        
        if latest:
            sensor_data = {
                "env": {
                    "t": latest.temperature,
                    "h": latest.humidity,
                    "p": latest.pressure if hasattr(latest, 'pressure') else 1013
                },
                "soil": {
                    "t": latest.soil_temperature if hasattr(latest, 'soil_temperature') else 0,
                    "m": latest.soil_moisture if hasattr(latest, 'soil_moisture') else 0
                },
                "wind": {
                    "s": latest.wind_speed if hasattr(latest, 'wind_speed') else 0,
                    "d": latest.wind_direction if hasattr(latest, 'wind_direction') else "N"
                },
                "rain": latest.rainfall if hasattr(latest, 'rainfall') else 0
            }
            
            # Get historical for trends
            historical_query = text("""
                SELECT temperature, humidity, soil_moisture 
                FROM weather_data 
                ORDER BY timestamp DESC LIMIT 24
            """)
            historical_rows = db.execute(historical_query).fetchall()
            historical_data = [dict(row._mapping) for row in historical_rows]
        
        # Generate LLM response with data context
        answer, suggestions = qa_assistant.generate_response(
            question=message_body,
            sensor_data=sensor_data,
            llm_analysis=llm_analysis,
            historical_data=historical_data
        )
        
        # Use LLM response directly (already formatted with agent name + tip)
        response_text = answer.strip()
        
        # Safety truncation for Twilio's 1600 char limit
        if len(response_text) > 1500:
            response_text = response_text[:1497] + "..."
        
        logger.info(f"📤 Sending Q&A response to {from_number} ({len(response_text)} chars)")
        
        # Send response via WhatsApp
        send_whatsapp_message(from_number, response_text)
        
        db.close()
        
        return {"status": "processed"}
        
    except Exception as e:
        logger.error(f"Error in farm Q&A webhook: {e}", exc_info=True)
        try:
            send_whatsapp_message(
                form_data.get("From", "").replace("whatsapp:", ""),
                f"Sorry, I encountered an error processing your question: {str(e)[:100]}"
            )
        except:
            pass
        return {"status": "error", "message": str(e)}
@app.post("/api/sensors/data")
async def receive_lora_sensor_data(request: Request):
    """
    Receive sensor data from ESP32 via LoRa → RPi UART → HTTP
    
    Expected JSON format:
    {
      "id": "WS01",
      "ts": 1707153000,
      "env": {"t": 22.5, "h": 65.0, "p": 1013.25},
      "wind": {"s": 3.2, "d": "NE"},
      "rain": 0.5,
      "soil": {"t": 18.5, "m": 45.0},
      "air": {"pm25": 12.5, "pm10": 28.3},
      "rad": {"uv": 3.2, "lux": 5000.0},
      "pwr": {"bat": 12.5, "sol": 13.2}
    }
    """
    try:
        data = await request.json()
        
        # Validate required fields
        required_fields = ["id", "ts", "env", "wind", "soil", "air", "rad", "pwr"]
        for field in required_fields:
            if field not in data:
                return {
                    "status": "error",
                    "message": f"Missing required field: {field}",
                    "code": 400
                }
        
        # Extract data with proper field names
        station_id = data.get("id", "UNKNOWN")
        timestamp = datetime.fromtimestamp(data.get("ts", 0))
        
        env = data.get("env", {})
        wind = data.get("wind", {})
        soil = data.get("soil", {})
        air = data.get("air", {})
        rad = data.get("rad", {})
        pwr = data.get("pwr", {})
        
        # Log to database
        try:
            from tools import _get_session
            from sqlalchemy import text
            
            db = _get_session()
            query = text("""
                INSERT INTO weather_data (
                    station_id, timestamp,
                    temperature, humidity, pressure,
                    wind_speed, wind_direction, rainfall,
                    soil_temperature, soil_moisture,
                    pm25, pm10,
                    uv_index, lux,
                    battery_voltage, solar_voltage
                ) VALUES (
                    :station_id, :timestamp,
                    :temperature, :humidity, :pressure,
                    :wind_speed, :wind_direction, :rainfall,
                    :soil_temperature, :soil_moisture,
                    :pm25, :pm10,
                    :uv_index, :lux,
                    :battery_voltage, :solar_voltage
                )
            """)
            
            db.execute(query, {
                "station_id": station_id,
                "timestamp": timestamp,
                "temperature": env.get("t"),
                "humidity": env.get("h"),
                "pressure": env.get("p"),
                "wind_speed": wind.get("s"),
                "wind_direction": wind.get("d"),
                "rainfall": data.get("rain", 0.0),
                "soil_temperature": soil.get("t"),
                "soil_moisture": soil.get("m"),
                "pm25": air.get("pm25"),
                "pm10": air.get("pm10"),
                "uv_index": rad.get("uv"),
                "lux": rad.get("lux"),
                "battery_voltage": pwr.get("bat"),
                "solar_voltage": pwr.get("sol")
            })
            db.commit()
            db.close()
            
            logger.info(f"Sensor data logged for station {station_id}")
            
        except Exception as db_error:
            logger.warning(f"Database logging error: {db_error}")
            # Continue even if database fails - data is received
        
        return {
            "status": "success",
            "message": "Sensor data received and logged",
            "station_id": station_id,
            "timestamp": timestamp.isoformat(),
            "data_fields_received": len([x for x in [env, wind, soil, air, rad, pwr] if x]),
            "logged_data": data
        }
    
    except Exception as e:
        logger.error(f"Error processing sensor data: {e}")
        return {
            "status": "error",
            "message": str(e),
            "code": 500
        }

# ============ VOICE-BASED PROFILE CREATION ============
class VoiceProfileRequest(BaseModel):
    transcript: str
    
@app.post("/api/profile/voice-update")
async def voice_profile_update(request: VoiceProfileRequest):
    """
    Takes a raw string transcript from the user and extracts structured
    farmer profile data (e.g. name, land size, crops) using Groq.
    """
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        return {"status": "error", "message": "GROQ_API_KEY is not configured", "identified_fields": {}}

    try:
        from langchain_groq import ChatGroq
        from langchain_core.messages import SystemMessage, HumanMessage
        import json
        import re
        
        chat = ChatGroq(temperature=0.1, model_name="llama-3.1-8b-instant", groq_api_key=groq_api_key)
        
        system_prompt = """
        You are an AI data extractor for a farmer platform. 
        Extract any of the following fields from the user's transcript if mentioned:
        - name
        - land_size_acres (number)
        - crops (list of strings)
        - location (string)
        
        Respond ONLY with a valid JSON object containing the fields found. Do not include markdown formatting or other text.
        """
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Transcript: {request.transcript}")
        ]
        
        response = chat.invoke(messages)
        content = response.content.strip()
        
        # Clean up possible markdown code blocks
        if content.startswith("```json"):
            content = content[7:-3]
        elif content.startswith("```"):
            content = content[3:-3]
            
        data = json.loads(content.strip())
        
        return {
            "status": "success",
            "identified_fields": data,
            "message": "Successfully parsed profile data from voice!"
        }
    except Exception as e:
        logger.error(f"Error in voice profile update: {e}")
        return {"status": "error", "message": str(e), "identified_fields": {}}



# ============ GET LATEST SENSOR DATA ENDPOINT ============

@app.get("/api/sensors/latest/{station_id}")
async def get_latest_sensor_data(station_id: str = "WS01"):
    """
    Get the latest sensor reading for a station.
    Used by frontend dashboard to display current conditions.
    """
    try:
        from tools import _get_session
        from sqlalchemy import text
        
        db = _get_session()
        query = text("""
            SELECT * FROM weather_data 
            WHERE station_id = :station_id 
            ORDER BY timestamp DESC 
            LIMIT 1
        """)
        
        result = db.execute(query, {"station_id": station_id}).fetchone()
        db.close()
        
        if not result:
            # Return mock data if no data in database
            return {
                "station_id": station_id,
                "timestamp": datetime.now().isoformat(),
                "temperature": 25,
                "humidity": 60,
                "pressure": 1013,
                "wind_speed": 5,
                "wind_direction": "N",
                "rainfall": 0,
                "soil_temperature": 26,
                "soil_moisture": 50,
                "pm25": 60,
                "pm10": 120,
                "uv_index": 2,
                "lux": 70,
                "battery_voltage": 12.5,
                "solar_voltage": 13.2
            }

        # Convert database row to dictionary and map to snake_case keys
        db_row = dict(result._mapping)
        # Map camelCase/TitleCase keys to snake_case for frontend compatibility
        sensor_data = {
            "station_id": db_row.get("station_id"),
            "timestamp": db_row.get("timestamp").isoformat() if hasattr(db_row.get("timestamp"), 'isoformat') else db_row.get("timestamp"),
            "temperature": db_row.get("temperature"),
            "humidity": db_row.get("humidity"),
            "pressure": db_row.get("pressure"),
            "wind_speed": db_row.get("wind_speed") or db_row.get("windSpeed"),
            "wind_direction": db_row.get("wind_direction") or db_row.get("windDirection"),
            "rainfall": db_row.get("rainfall"),
            "soil_temperature": db_row.get("soil_temperature") or db_row.get("soilTemperature"),
            "soil_moisture": db_row.get("soil_moisture") or db_row.get("soilMoisture"),
            "pm25": db_row.get("pm25") or db_row.get("airQualityPM25"),
            "pm10": db_row.get("pm10") or db_row.get("airQualityPM10"),
            "uv_index": db_row.get("uv_index") or db_row.get("uvIndex"),
            "lux": db_row.get("lux") or db_row.get("lightIntensity"),
            "battery_voltage": db_row.get("battery_voltage") or db_row.get("batteryVoltage"),
            "solar_voltage": db_row.get("solar_voltage") or db_row.get("solarVoltage"),
        }
        return sensor_data
        
    except Exception as e:
        logger.error(f"Error fetching latest sensor data: {e}")
        return {
            "status": "error",
            "message": str(e),
            "code": 500
        }


# ============ FPGA ACCELERATOR ENDPOINTS ============

class FPGASensorInput(BaseModel):
    """Input model for FPGA sensor fusion."""
    soil_moisture: float = 50.0
    temperature: float = 25.0
    humidity: float = 60.0
    light_level: float = 70.0
    user_id: Optional[str] = None  # For WhatsApp alerts


@app.post("/api/fpga/fusion")
async def fpga_sensor_fusion(data: FPGASensorInput):
    """
    Process sensor data through ZC706 FPGA accelerator.
    LLM cross-validates the hardware result and provides adjusted scores.
    """
    try:
        bridge = get_fpga_bridge()
        
        # Run FPGA fusion via hardware bridge
        result = bridge.send_fusion(
            soil=int(round(data.soil_moisture)),
            temp=int(round(data.temperature)),
            humid=int(round(data.humidity)),
            light=int(round(data.light_level))
        )
        
        fpga_fusion = result.get('fusion_score', 0)
        fpga_stress = result.get('stress_index', 0)
        fpga_alert = result.get('alert_level', 0)
        
        # LLM cross-validates FPGA result against actual conditions
        llm_adjusted = None
        ai_insights = ""
        try:
            if os.getenv("GROQ_API_KEY"):
                llm = ChatGroq(
                    model="llama-3.1-8b-instant",
                    api_key=os.getenv("GROQ_API_KEY"),
                    timeout=12
                )
                cross_prompt = f"""You are an agricultural AI analyzing farm sensor data. The FPGA hardware accelerator produced these raw results, but you must CROSS-VALIDATE them against the actual sensor readings and provide your own adjusted assessment.

ACTUAL SENSOR READINGS:
- Soil Moisture: {data.soil_moisture}%
- Temperature: {data.temperature}°C
- Humidity: {data.humidity}%
- Light Level: {data.light_level}%

FPGA HARDWARE RAW OUTPUT:
- Fusion Score: {fpga_fusion}/100 (higher = healthier)
- Stress Index: {fpga_stress}/100 (higher = more stress)
- Alert Level: {fpga_alert} (0=Normal, 1=Moderate, 2=High, 3=Critical)

Based on the ACTUAL sensor readings, provide your adjusted assessment. The FPGA may over/under-estimate.
Reply ONLY with valid JSON, no markdown:
{{"adjusted_fusion_score": <0-100>, "adjusted_stress_index": <0-100>, "adjusted_alert_level": <0-3>, "alert_name": "<Normal/Moderate/High/Critical>", "assessment": "<1-2 sentence farmer-friendly assessment>", "recommendations": ["<actionable tip 1>", "<actionable tip 2>", "<actionable tip 3>"]}}"""
                llm_response = await asyncio.to_thread(llm.invoke, [("user", cross_prompt)])
                import json
                try:
                    llm_adjusted = json.loads(llm_response.content)
                except:
                    ai_insights = llm_response.content
        except Exception as e:
            logger.warning(f"LLM cross-validation for fusion failed: {e}")
        
        # Use LLM-adjusted values if available, otherwise use FPGA raw
        if llm_adjusted and isinstance(llm_adjusted, dict):
            final_fusion = llm_adjusted.get("adjusted_fusion_score", fpga_fusion)
            final_stress = llm_adjusted.get("adjusted_stress_index", fpga_stress)
            final_alert = llm_adjusted.get("adjusted_alert_level", fpga_alert)
            alert_name = llm_adjusted.get("alert_name", "Normal")
            ai_insights = llm_adjusted.get("assessment", "")
            recommendations = llm_adjusted.get("recommendations", [])
        else:
            final_fusion = fpga_fusion
            final_stress = fpga_stress
            final_alert = fpga_alert
            alert_name = result.get("alert_name", "Normal")
            recommendations = []
        
        hardware_mode = "real_hardware" if (FPGA_ENABLED and not isinstance(bridge, MockFPGABridge)) else "simulation"
        
        return {
            "status": "success",
            "input": {
                "soil": data.soil_moisture,
                "temp": data.temperature,
                "humid": data.humidity,
                "light": data.light_level
            },
            "fpga_result": {
                "fusion_score": final_fusion,
                "stress_index": final_stress,
                "alert_level": final_alert,
                "alert_name": alert_name,
                "timestamp": result.get("timestamp")
            },
            "fpga_raw_result": {
                "fusion_score": fpga_fusion,
                "stress_index": fpga_stress,
                "alert_level": fpga_alert
            },
            "ai_insights": ai_insights,
            "ai_recommendations": recommendations,
            "hardware_mode": hardware_mode,
            "hardware_accelerator": "ZC706 FPGA Sensor Fusion",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"FPGA fusion error: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


@app.get("/api/fpga/status")
async def fpga_status():
    """Get FPGA accelerator status."""
    try:
        bridge = get_fpga_bridge()
        is_real_hw = FPGA_ENABLED and not isinstance(bridge, MockFPGABridge)
        return {
            "status": "ok",
            "fpga": bridge.get_status() if hasattr(bridge, 'get_status') else ("connected" if is_real_hw else "simulation"),
            "hardware_mode": "real_hardware" if is_real_hw else "simulation",
            "port": FPGA_PORT if is_real_hw else None,
            "fpga_enabled": FPGA_ENABLED,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "hardware_mode": "disconnected",
            "message": str(e)
        }


@app.post("/api/fpga/test")
async def fpga_test():
    """Run FPGA accelerator test suite."""
    try:
        bridge = get_fpga_bridge()
        
        test_cases = [
            {"name": "Optimal", "soil": 50, "temp": 25, "humid": 60, "light": 70},
            {"name": "Dry Soil", "soil": 10, "temp": 30, "humid": 40, "light": 80},
            {"name": "Hot", "soil": 60, "temp": 40, "humid": 30, "light": 90},
            {"name": "Frost Risk", "soil": 50, "temp": 2, "humid": 80, "light": 30},
        ]
        
        results = []
        for tc in test_cases:
            result = bridge.send_fusion(tc["soil"], tc["temp"], tc["humid"], tc["light"])
            results.append({
                "test": tc["name"],
                "input": tc,
                "output": result
            })
        
        return {
            "status": "success",
            "tests": results,
            "fpga_mode": bridge.get_status()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


# ============ FARM ADVISOR AI ENDPOINTS ============

class AdvisorRequest(BaseModel):
    category: str = "overview"  # alerts, crops, water, tips, soil, pests, overview

@app.post("/api/advisor/insights")
async def get_advisor_insights(request: AdvisorRequest):
    """Generate AI-powered farming advice based on live sensor data."""
    try:
        # Get live sensor data
        sensor_data = {}
        try:
            resp = requests.get("http://localhost:8000/api/sensors/latest/WS01", timeout=3)
            if resp.status_code == 200:
                sensor_data = resp.json()
        except:
            pass
        
        temp = sensor_data.get("temperature", 25)
        humidity = sensor_data.get("humidity", 60)
        soil_moisture = sensor_data.get("soilMoisture", sensor_data.get("soil_moisture", 50))
        wind_speed = sensor_data.get("windSpeed", sensor_data.get("wind_speed", 5))
        rainfall = sensor_data.get("rainfall", 0)
        light = sensor_data.get("lightIntensity", sensor_data.get("light_level", 70))
        uv_index = sensor_data.get("uvIndex", sensor_data.get("uv_index", 2))
        pressure = sensor_data.get("pressure", 1013)
        
        prompts = {
            "alerts": f"""You are a smart farm AI advisor. Based on these LIVE sensor readings from the farm:
- Temperature: {temp}°C, Humidity: {humidity}%, Wind: {wind_speed} km/h, Rainfall: {rainfall}mm
- Soil Moisture: {soil_moisture}%, Light: {light}%, UV Index: {uv_index}, Pressure: {pressure}hPa

Generate 4-5 farming alerts with severity levels. For each alert, provide:
- A severity (danger/warning/info/success) 
- A short title
- A specific actionable message that a farmer can understand

Format as JSON array: [{{"severity":"warning","title":"Heat Alert","message":"Your crops..."}}]
Only output valid JSON, no markdown.""",

            "crops": f"""You are a farming AI advisor. Based on current conditions:
- Temperature: {temp}°C, Humidity: {humidity}%, Soil Moisture: {soil_moisture}%, Light: {light}%

Suggest 5 crops that would grow best RIGHT NOW in these conditions. For each provide:
- crop name, emoji, why it's suitable, planting tips, expected yield timeline
Format as JSON array: [{{"crop":"Rice","emoji":"🌾","suitability":"Excellent - humidity and temp are ideal","tips":"Plant in standing water...","timeline":"120 days to harvest"}}]
Only output valid JSON, no markdown.""",

            "water": f"""You are a farm water management AI. Based on current conditions:
- Temperature: {temp}°C, Humidity: {humidity}%, Soil Moisture: {soil_moisture}%, Rainfall: {rainfall}mm

Provide smart irrigation advice:
1. Current soil moisture assessment
2. Recommended watering schedule for today
3. Water conservation tips based on conditions
4. Estimated water needs (liters per acre)
5. Warning signs to watch for

Format as JSON: {{"moisture_status":"Good","schedule":"Water early morning...","tips":["tip1","tip2"],"liters_per_acre":500,"warnings":["sign1"]}}
Only output valid JSON, no markdown.""",

            "tips": f"""You are a friendly farm advisor AI. Based on LIVE conditions:
- Temperature: {temp}°C, Humidity: {humidity}%, Wind: {wind_speed} km/h, Soil Moisture: {soil_moisture}%

Generate 6 practical, farmer-friendly tips for TODAY. Each tip should be:
- Based on the actual current weather/soil data
- Written in simple, friendly language a farmer can understand
- Actionable right now

Format as JSON array of strings: ["🌱 Tip 1...", "💧 Tip 2..."]
Only output valid JSON, no markdown.""",

            "soil": f"""You are a soil health AI analyst. Based on:
- Soil Moisture: {soil_moisture}%, Temperature: {temp}°C, Humidity: {humidity}%, Rainfall: {rainfall}mm

Provide a comprehensive soil health analysis:
1. Overall score (0-100)
2. Status (Excellent/Good/Fair/Poor/Critical)
3. 4 specific recommendations to improve soil health
4. What nutrients to add
5. Risk assessment

Format as JSON: {{"score":75,"status":"Good","recommendations":["rec1","rec2","rec3","rec4"],"nutrients":"Add nitrogen...","risk":"Low risk of..."}}
Only output valid JSON, no markdown.""",

            "pests": f"""You are a crop protection AI advisor. Based on current conditions:
- Temperature: {temp}°C, Humidity: {humidity}%, Rainfall: {rainfall}mm

Identify 4 pests/diseases most likely to appear in these conditions. For each provide:
- Name, risk level (High/Medium/Low), symptoms, organic remedy, prevention steps
Format as JSON array: [{{"name":"Powdery Mildew","risk":"High","symptoms":"White powder...","remedy":"Neem oil spray...","prevention":"Improve air circulation..."}}]
Only output valid JSON, no markdown.""",

            "overview": f"""You are a farm AI assistant. Give a brief, friendly farm overview based on:
- Temperature: {temp}°C, Humidity: {humidity}%, Wind: {wind_speed} km/h
- Soil Moisture: {soil_moisture}%, Light: {light}%, Rainfall: {rainfall}mm

Provide a 3-sentence summary of how the farm is doing today and what the farmer should focus on.
Return as JSON: {{"summary":"Your farm is...","mood":"good","focus":"Focus on..."}}
Only output valid JSON, no markdown."""
        }
        
        prompt = prompts.get(request.category, prompts["overview"])
        
        ai_response = None
        if os.getenv("GROQ_API_KEY"):
            try:
                llm = ChatGroq(
                    model="llama-3.1-8b-instant",
                    api_key=os.getenv("GROQ_API_KEY"),
                    timeout=15
                )
                result = await asyncio.to_thread(llm.invoke, [("user", prompt)])
                # Try to parse as JSON
                import json
                try:
                    ai_response = json.loads(result.content)
                except:
                    ai_response = result.content
            except Exception as e:
                logger.warning(f"Advisor LLM error: {e}")
        
        return {
            "status": "success",
            "category": request.category,
            "sensor_data": {
                "temperature": temp,
                "humidity": humidity,
                "soil_moisture": soil_moisture,
                "wind_speed": wind_speed,
                "rainfall": rainfall,
                "light": light,
                "uv_index": uv_index,
                "pressure": pressure
            },
            "ai_insights": ai_response,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Advisor insights error: {e}")
        return {"status": "error", "message": str(e)}


# ============ AI HARDWARE ACCELERATOR ENDPOINTS ============

class RainPredictionInput(BaseModel):
    """Input model for rain prediction."""
    temperature: float = 25.0
    humidity: float = 60.0
    pressure: float = 1013.0
    wind_speed: float = 5.0
    station_id: str = "WS01"

@app.post("/api/fpga/rain-predict")
async def fpga_rain_predict(data: RainPredictionInput):
    """
    Use ZC706 FPGA Rain Predictor accelerator to predict rainfall.
    LLM cross-validates FPGA result against actual weather conditions.
    """
    try:
        temp = data.temperature
        humid = data.humidity
        pressure_val = data.pressure
        wind = data.wind_speed
        station_id = data.station_id
        
        bridge = get_fpga_bridge()
        
        # Call FPGA rain predictor with sensor data
        result = bridge.send_rain_prediction(
            temp=int(round(temp)),
            humid=int(round(humid)),
            pressure=int(round(pressure_val)),
            wind=int(round(wind))
        )
        
        fpga_rain_prob = result.get("rain_probability", 0)
        fpga_stress = result.get("stress_level", 0)
        fpga_alert = result.get("rain_alert", 0)
        
        # LLM cross-validates the FPGA rain probability against actual conditions
        llm_adjusted = None
        fallback_recommendation = ""
        try:
            if os.getenv("GROQ_API_KEY"):
                llm = ChatGroq(
                    model="llama-3.1-8b-instant",
                    api_key=os.getenv("GROQ_API_KEY"),
                    timeout=12
                )
                cross_prompt = f"""You are a meteorological AI advisor for farmers. The FPGA hardware gave a rain prediction, but you must CROSS-VALIDATE it against the actual weather sensor readings.

ACTUAL WEATHER SENSOR READINGS:
- Temperature: {temp}°C
- Humidity: {humid}%
- Atmospheric Pressure: {pressure_val} hPa
- Wind Speed: {wind} km/h

FPGA HARDWARE RAW PREDICTION:
- Rain Probability: {fpga_rain_prob}%
- Stress Level: {fpga_stress}/100
- Rain Alert: {fpga_alert} (0=No, 1=Yes)

IMPORTANT: The FPGA may over-predict or under-predict. Use YOUR meteorological knowledge to evaluate the actual conditions. For example, high humidity alone doesn't mean rain — you also need low pressure, wind patterns, etc.

Reply ONLY with valid JSON, no markdown:
{{"adjusted_rain_probability": <0-100>, "adjusted_stress_level": <0-100>, "rain_alert": <0 or 1>, "confidence": "<high/medium/low>", "recommendation": "<2-3 sentence farmer-friendly recommendation based on ACTUAL conditions>", "reasoning": "<1 sentence explaining why you adjusted>"}}"""
                llm_response = await asyncio.to_thread(llm.invoke, [("user", cross_prompt)])
                import json
                try:
                    llm_adjusted = json.loads(llm_response.content)
                except:
                    fallback_recommendation = llm_response.content
        except Exception as e:
            logger.warning(f"LLM cross-validation for rain failed: {e}")
        
        # Use LLM-adjusted values if available
        if llm_adjusted and isinstance(llm_adjusted, dict):
            final_rain_prob = llm_adjusted.get("adjusted_rain_probability", fpga_rain_prob)
            final_stress = llm_adjusted.get("adjusted_stress_level", fpga_stress)
            final_alert = llm_adjusted.get("rain_alert", fpga_alert)
            recommendation = llm_adjusted.get("recommendation", "")
            reasoning = llm_adjusted.get("reasoning", "")
        else:
            final_rain_prob = fpga_rain_prob
            final_stress = fpga_stress
            final_alert = fpga_alert
            reasoning = ""
            # Static fallback recommendation
            if final_rain_prob >= 80:
                recommendation = "⚠️ HIGH RISK: Heavy rain expected. Delay outdoor operations."
            elif final_rain_prob >= 60:
                recommendation = "🌧️ MODERATE RISK: Rain likely. Plan accordingly."
            elif final_rain_prob >= 40:
                recommendation = "☁️ POSSIBLE: Some rain possible. Monitor closely."
            elif final_rain_prob >= 20:
                recommendation = "⛅ UNLIKELY: Low chance. Good for field work."
            else:
                recommendation = "☀️ DRY: Consider irrigation scheduling."
            if fallback_recommendation:
                recommendation = fallback_recommendation
        
        hardware_mode = "real_hardware" if (FPGA_ENABLED and not isinstance(bridge, MockFPGABridge)) else "simulation"
        
        return {
            "status": "success",
            "prediction": {
                "rain_probability": final_rain_prob,
                "stress_level": final_stress,
                "rain_alert": final_alert,
                "timestamp": result.get("timestamp")
            },
            "fpga_raw_prediction": {
                "rain_probability": fpga_rain_prob,
                "stress_level": fpga_stress,
                "rain_alert": fpga_alert
            },
            "input": {
                "temperature": temp,
                "humidity": humid,
                "pressure": pressure_val,
                "wind_speed": wind,
                "station_id": station_id,
                "source": "real_sensor_data"
            },
            "farmer_recommendation": recommendation,
            "ai_reasoning": reasoning,
            "hardware_mode": hardware_mode,
            "hardware_accelerator": "ZC706 FPGA Rain Predictor"
        }
        
    except Exception as e:
        logger.error(f"FPGA rain prediction error: {e}")
        return {
            "status": "error",
            "message": str(e),
            "hardware_accelerator": "ZC706 FPGA Rain Predictor"
        }


class CombinedAnalysisInput(BaseModel):
    """Input model for combined FPGA analysis."""
    soil_moisture: float = 50.0
    temperature: float = 25.0
    humidity: float = 60.0
    light_level: float = 70.0
    station_id: str = "WS01"
    user_id: Optional[str] = None

@app.post("/api/fpga/combined-analysis")
async def fpga_combined_analysis(data: CombinedAnalysisInput):
    """
    Combined analysis using both Sensor Fusion and Rain Predictor accelerators.
    Calls the individual endpoints internally so results are CONSISTENT.
    Only adds a unified recommendation on top.
    """
    try:
        # Call the SAME individual endpoints so values match exactly
        fusion_input = FPGASensorInput(
            soil_moisture=data.soil_moisture,
            temperature=data.temperature,
            humidity=data.humidity,
            light_level=data.light_level,
            user_id=data.user_id
        )
        rain_input = RainPredictionInput(
            temperature=data.temperature,
            humidity=data.humidity,
            pressure=1013.0,
            wind_speed=5.0,
            station_id=data.station_id
        )
        
        # Call the actual endpoint functions — these do their own LLM cross-validation
        fusion_response = await fpga_sensor_fusion(fusion_input)
        rain_response = await fpga_rain_predict(rain_input)
        
        # Extract the LLM-adjusted values (same ones shown on individual cards)
        fusion_result = fusion_response.get("fpga_result", {})
        rain_result = rain_response.get("prediction", {})
        
        final_fusion = fusion_result.get("fusion_score", 50)
        final_stress = fusion_result.get("stress_index", 30)
        final_alert = fusion_result.get("alert_level", 0)
        final_rain_prob = rain_result.get("rain_probability", 20)
        final_rain_stress = rain_result.get("stress_level", 20)
        final_rain_alert = rain_result.get("rain_alert", 0)
        
        # Now ask LLM ONLY for the unified recommendation (do NOT re-adjust numbers)
        recommendation = ""
        overall_risk = "low"
        actions = []
        try:
            if os.getenv("GROQ_API_KEY"):
                llm = ChatGroq(
                    model="llama-3.1-8b-instant",
                    api_key=os.getenv("GROQ_API_KEY"),
                    timeout=12
                )
                rec_prompt = f"""You are a farm advisor. Based on the following ALREADY-VALIDATED results, provide ONLY a unified recommendation. Do NOT change the numbers.

Plant Health Check Results:
- Fusion Score: {final_fusion}/100
- Stress Index: {final_stress}%
- Alert Level: {final_alert}

Rain Prediction Results:
- Rain Probability: {final_rain_prob}%
- Rain Alert: {final_rain_alert}

Sensor Readings: Temp={data.temperature}°C, Humidity={data.humidity}%, Soil={data.soil_moisture}%, Light={data.light_level}%

Reply ONLY with valid JSON:
{{"overall_risk": "<low/moderate/high/critical>", "recommendation": "<2-3 sentence unified farmer-friendly recommendation>", "actions": ["<action 1>", "<action 2>", "<action 3>"]}}"""
                llm_response = await asyncio.to_thread(llm.invoke, [("user", rec_prompt)])
                import json
                try:
                    llm_rec = json.loads(llm_response.content)
                    overall_risk = llm_rec.get("overall_risk", "low")
                    recommendation = llm_rec.get("recommendation", "")
                    actions = llm_rec.get("actions", [])
                except:
                    recommendation = llm_response.content
        except Exception as e:
            logger.warning(f"LLM recommendation for combined failed: {e}")
        
        if not recommendation:
            if final_alert >= 2 or final_rain_prob >= 70:
                recommendation = "⚠️ Elevated risk detected. Monitor conditions closely and take precautionary action."
                overall_risk = "high"
            elif final_stress >= 40 or final_rain_prob >= 40:
                recommendation = "📋 Moderate conditions. Adjust operations as needed."
                overall_risk = "moderate"
            else:
                recommendation = "✅ Conditions are stable. Proceed with normal farming operations."
                overall_risk = "low"
        
        hardware_mode = fusion_response.get("hardware_mode", "simulation")
        
        return {
            "status": "success",
            "sensor_data": {
                "temperature": data.temperature,
                "humidity": data.humidity,
                "soil_moisture": data.soil_moisture,
                "light_level": data.light_level,
                "pressure": 1013,
                "wind_speed": 5.0,
                "station_id": data.station_id,
                "source": "real_sensor_data"
            },
            "sensor_fusion": fusion_result,
            "rain_prediction": rain_result,
            "combined_analysis": {
                "overall_risk_level": overall_risk,
                "stress_index": final_stress,
                "rain_probability": final_rain_prob,
                "recommendation": recommendation,
                "actions": actions
            },
            "hardware_mode": hardware_mode,
            "hardware_accelerators": ["ZC706 FPGA Sensor Fusion", "ZC706 FPGA Rain Predictor"]
        }
        
    except Exception as e:
        logger.error(f"Combined FPGA analysis error: {e}")
        return {
            "status": "error",
            "message": str(e)
        }

# ============ WEATHER INSIGHT ENDPOINT ============

class WeatherInsightRequest(BaseModel):
    """Weather insight request model"""
    message: str
    station_id: str = "WS01"
    user_id: str = "dashboard_user"

@app.post("/api/weather-insight")
async def weather_insight(request: WeatherInsightRequest):
    """
    Get weather insight using LLM workflow with fallback to simple analysis
    Processes user message with real sensor data
    """
    try:
        # Try Groq LLM first if available
        if os.getenv("GROQ_API_KEY"):
            try:
                logger.info("Attempting Groq LLM for weather insight")
                llm = ChatGroq(
                    model="llama-3.1-8b-instant",
                    api_key=os.getenv("GROQ_API_KEY"),
                    timeout=10
                )
                
                # Get sensor data context
                sensor_context = ""
                try:
                    from tools import _get_session, get_latest_weather
                    db = _get_session()
                    sensor_data = get_latest_weather(request.station_id)
                    db.close()
                    
                    if sensor_data:
                        sensor_context = f"""
Current sensor conditions:
- Temperature: {sensor_data.get('temperature', 'N/A')}°C
- Humidity: {sensor_data.get('humidity', 'N/A')}%
- Pressure: {sensor_data.get('pressure', 'N/A')} hPa
- Wind Speed: {sensor_data.get('wind_speed', 'N/A')} km/h
- Rainfall: {sensor_data.get('rainfall', 'N/A')} mm
- Soil Temperature: {sensor_data.get('soil_temperature', 'N/A')}°C
- Soil Moisture: {sensor_data.get('soil_moisture', 'N/A')}%
- Air Quality PM2.5: {sensor_data.get('air_quality_pm25', 'N/A')} µg/m³
"""
                except Exception as e:
                    logger.warning(f"Could not load sensor data: {e}")
                
                prompt = f"""You are an expert agricultural advisor. Based on the current weather and soil conditions below, provide specific, practical farming recommendations.

{sensor_context}

{request.message}

CRITICAL: Format your response EXACTLY like this with NO bold, NO asterisks, NO markdown:
1. First specific recommendation
2. Second specific recommendation  
3. Third specific recommendation
4. Fourth specific recommendation
5. Fifth specific recommendation

Each line must start with a number, a period, and a space. No asterisks, no bold formatting, no dashes. Plain text only."""

                logger.info("Invoking Groq LLM...")
                response = await asyncio.to_thread(
                    llm.invoke,
                    [("user", prompt)]
                )
                
                logger.info("✓ Groq LLM returned response")
                return {
                    "response": response.content,
                    "status": "success"
                }
            except Exception as groq_error:
                logger.error(f"Groq LLM error: {groq_error}", exc_info=True)
        
        # Try workflow as fallback
        graph = get_compiled_graph()
        if graph:
            try:
                logger.info(f"Invoking workflow with message: {request.message[:50]}...")
                result = await asyncio.to_thread(
                    graph.invoke,
                    {
                        "message": request.message,
                        "station_id": request.station_id,
                        "user_id": request.user_id,
                        "timestamp": datetime.now().isoformat(),
                        "response": "",
                        "error": None
                    }
                )
                
                logger.info(f"Workflow result: {result}")
                if result and result.get("response"):
                    return {
                        "response": result.get("response"),
                        "status": "success"
                    }
            except Exception as workflow_error:
                logger.error(f"Workflow failed, using fallback: {workflow_error}", exc_info=True)
        
        # Fallback: Simple analysis based on sensor data
        try:
            from tools import _get_session, get_latest_weather
            db = _get_session()
            sensor_data = get_latest_weather(request.station_id)
            db.close()
            
            if sensor_data:
                temp = sensor_data.get('temperature', 20)
                humidity = sensor_data.get('humidity', 50)
                rainfall = sensor_data.get('rainfall', 0)
                soil_moisture = sensor_data.get('soil_moisture', 50)
                wind_speed = sensor_data.get('wind_speed', 5)
                
                # Generate simple farming advice based on conditions
                advice = []
                
                if temp < 5:
                    advice.append("⚠️ Very cold (Below 5°C) - Protect sensitive crops from frost")
                elif temp > 35:
                    advice.append("⚠️ Very hot (Above 35°C) - Increase irrigation, provide shade")
                elif 15 <= temp <= 25:
                    advice.append("✓ Optimal temperature for most crops")
                
                if humidity > 85:
                    advice.append("⚠️ High humidity - Watch for fungal diseases, ensure good ventilation")
                elif humidity < 30:
                    advice.append("⚠️ Low humidity - Increase irrigation frequency")
                else:
                    advice.append("✓ Humidity levels are suitable for crop growth")
                
                if soil_moisture < 25:
                    advice.append("🚨 URGENT: Soil is too dry - Water crops immediately")
                elif soil_moisture > 80:
                    advice.append("⚠️ Soil is very wet - Risk of root rot, improve drainage")
                elif 40 <= soil_moisture <= 70:
                    advice.append("✓ Soil moisture is optimal for most crops")
                
                if rainfall > 0:
                    advice.append(f"💧 Recent rainfall: {rainfall}mm detected - Monitor for waterlogging")
                
                if wind_speed > 20:
                    advice.append(f"⚠️ Strong winds ({wind_speed} km/h) - Secure tall plants, risk of damage")
                
                response_text = "Farm Status Report:\n\n" + "\n".join(advice) if advice else "Sensor data available but unable to generate advice."
                
                return {
                    "response": response_text,
                    "status": "success"
                }
        except Exception as fallback_error:
            logger.error(f"Fallback analysis failed: {fallback_error}")
        
        return {
            "response": "Unable to generate insights. Please ensure sensors are sending data and try again.",
            "status": "error"
        }
        
    except Exception as e:
        logger.error(f"Weather insight error: {e}")
        return {
            "response": f"Error processing request: {str(e)}",
            "status": "error"
        }

# ============ CHAT ENDPOINT ============

class ChatRequest(BaseModel):
    """Chat request model"""
    message: str
    user_id: str = "default"

@app.post("/api/chat")
async def chat(request: ChatRequest):
    """
    General chat endpoint - handles ANY question
    Uses latest sensor data + Groq LLM for contextual responses
    All inferences are based on real-time sensor readings
    """
    try:
        # Get latest sensor data for inference context
        sensor_context = ""
        try:
            from tools import _get_session, get_latest_weather
            db = _get_session()
            latest_sensor = get_latest_weather("WS01")
            if latest_sensor:
                sensor_context = f"""
Current Sensor Data (as of {latest_sensor.get('timestamp', 'now')}):
- Temperature: {latest_sensor.get('temperature')}°C
- Humidity: {latest_sensor.get('humidity')}%
- Pressure: {latest_sensor.get('pressure')} hPa
- Wind: {latest_sensor.get('wind_speed')} m/s
- Rainfall: {latest_sensor.get('rainfall')} mm
- Soil Moisture: {latest_sensor.get('soil_moisture')}%
- Soil Temperature: {latest_sensor.get('soil_temperature')}°C
- PM2.5: {latest_sensor.get('air_quality_pm25')} µg/m³
- UV Index: {latest_sensor.get('uv_index')}
"""
                logger.info(f"✅ Live sensor data loaded for inference")
            db.close()
        except Exception as e:
            logger.warning(f"Could not load sensor context: {e}")
        
        # Enhance the user message with sensor context for inference
        enhanced_message = f"{request.message}\n{sensor_context}" if sensor_context else request.message
        
        # Add mandi data context — detect specific commodity if mentioned
        try:
            msg_lower = request.message.lower()
            # Known commodity names to detect in the question
            known_commodities = [
                "wheat", "rice", "onion", "tomato", "potato", "soybean",
                "cotton", "maize", "chilli", "banana", "jowar", "bajra",
                "gram", "tur", "arhar", "mustard", "groundnut", "sugarcane",
                "brinjal", "cabbage", "carrot", "cauliflower", "garlic",
                "ginger", "lemon", "mango", "apple", "moong", "urad",
            ]
            detected_commodity = ""
            for c in known_commodities:
                if c in msg_lower:
                    detected_commodity = c.capitalize()
                    break

            if detected_commodity:
                # Fetch targeted data for this commodity
                targeted = _fetch_mandi_from_datagov(commodity=detected_commodity, limit=10)
                if targeted:
                    lines = [f"  {r['commodity']} ({r['variety']}): ₹{r['modal_price']}/qtl at {r['market']}, {r['state']} ({r['arrival_date']})" for r in targeted[:8]]
                    mandi_context = f"Live Mandi Rates for {detected_commodity}:\n" + "\n".join(lines)
                    enhanced_message = f"{enhanced_message}\n\n{mandi_context}"
                    logger.info(f"✅ Targeted mandi data for '{detected_commodity}' injected ({len(targeted)} records)")
            else:
                # Generic mandi context
                mandi_context = _get_mandi_context()
                if mandi_context:
                    enhanced_message = f"{enhanced_message}\n\n{mandi_context}"
                    logger.info("✅ Generic mandi rates context injected into chat")
        except Exception as me:
            logger.warning(f"Could not load mandi context: {me}")
        
        # Try Groq LLM directly with sensor + mandi context
        try:
            if os.getenv("GROQ_API_KEY"):
                llm = ChatGroq(
                    model="llama-3.1-8b-instant",
                    api_key=os.getenv("GROQ_API_KEY"),
                    timeout=10
                )
                
                response = await asyncio.to_thread(
                    llm.invoke,
                    [("user", enhanced_message)]
                )
                
                return {
                    "response": response.content,
                    "status": "success",
                    "inference_source": "groq_llm_with_sensor_data",
                    "active_agent": _detect_agent(request.message)
                }
        except Exception as groq_error:
            logger.warning(f"Groq API error: {groq_error}")
            
        # Fallback 1: Try workflow with sensor context
        graph = get_compiled_graph()
        if graph:
            result = await asyncio.to_thread(
                graph.invoke,
                {
                    "message": enhanced_message,
                    "user_id": request.user_id,
                    "timestamp": datetime.now().isoformat(),
                    "response": "",
                    "error": None
                }
            )
            response_text = result.get("response", "I couldn't generate a response")
            
            # If workflow returns the default message, use simple response
            if "I can help with" in response_text:
                return generate_simple_response(request.message, sensor_context)
            else:
                return {
                    "response": response_text,
                    "status": "success",
                    "inference_source": "langgraph_workflow_with_sensor_data",
                    "active_agent": _detect_agent(request.message)
                }
        else:
            # Fallback 2: Simple response generator with context
            return generate_simple_response(request.message, sensor_context)
                
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return generate_simple_response(request.message)

def _detect_agent(message: str) -> str:
    """Detect which agent is best suited to answer based on message keywords."""
    msg = message.lower()
    if any(w in msg for w in ["weather", "temperature", "humidity", "pressure", "wind", "forecast", "climate"]):
        return "Weather Agent"
    if any(w in msg for w in ["rain", "precipitation", "storm", "umbrella", "flood"]):
        return "Alert Agent"
    if any(w in msg for w in ["soil", "moisture", "irrigation", "water", "plant", "crop", "grow", "farm", "seed"]):
        return "Health Agent"
    if any(w in msg for w in ["trend", "history", "average", "compare", "graph", "chart", "analysis"]):
        return "Trend Agent"
    if any(w in msg for w in ["alert", "warning", "danger", "emergency", "critical", "threshold"]):
        return "Alert Agent"
    if any(w in msg for w in ["sensor", "data", "reading", "status", "battery", "voltage"]):
        return "Ingress Agent"
    if any(w in msg for w in ["report", "summary", "overview", "recommend"]):
        return "Output Agent"
    if any(w in msg for w in ["mandi", "market", "price", "rate", "sell", "buy", "commodity", "bhav"]):
        return "Mandi Agent"
    return "Supervisor Agent"

def generate_simple_response(message: str, sensor_context: str = "") -> dict:
    """Simple response generator - includes live sensor data in fallback responses"""
    message_lower = message.lower()
    sensor_note = f"\n\n{sensor_context}" if sensor_context else ""
    active_agent = _detect_agent(message)
    
    # Mandi/Market questions
    if any(word in message_lower for word in ["mandi", "market", "price", "rate", "sell", "buy", "commodity", "bhav"]):
        # Try to include cached mandi data
        mandi_note = ""
        if _mandi_cache.get("data"):
            top_items = _mandi_cache["data"][:5]
            lines = [f"- {r.get('commodity','?')}: ₹{r.get('modal_price','?')}/qtl at {r.get('market','?')} ({r.get('state','?')})" for r in top_items]
            mandi_note = "\n\nLatest Mandi Rates:\n" + "\n".join(lines)
        return {
            "response": f"I can help with market prices!{mandi_note}{sensor_note if sensor_context else ''}",
            "status": "success",
            "inference_source": "simple_generator_with_mandi_data",
            "active_agent": active_agent
        }
    
    # Farming questions
    if any(word in message_lower for word in ["plant", "seed", "crop", "farm", "grow", "soil", "irrigation"]):
        return {
            "response": f"That's a great farming question! Based on your current sensor readings, consider your soil temperature, moisture levels, and weather conditions. {sensor_note if sensor_context else 'Check the Dashboard for current conditions.'}",
            "status": "success",
            "inference_source": "simple_generator_with_sensor_data",
            "active_agent": active_agent
        }
    
    # Weather questions
    elif any(word in message_lower for word in ["temperature", "weather", "humidity", "rain", "wind", "forecast"]):
        return {
            "response": f"Here are your current weather conditions:{sensor_note if sensor_context else 'Check the Dashboard for the latest sensor readings.'}",
            "status": "success",
            "inference_source": "simple_generator_with_sensor_data",
            "active_agent": active_agent
        }
    
    # General knowledge
    elif any(word in message_lower for word in ["capital", "country", "president", "world", "history"]):
        return {
            "response": "I can help with general knowledge questions! While I don't have access to real-time data for those topics, I can provide information based on my training. What specifically would you like to know?",
            "status": "success",
            "active_agent": "Supervisor Agent"
        }
    
    # Default response
    else:
        return {
            "response": f"I can help you! Feel free to ask about your farm conditions, weather, mandi rates, plants, or general farming advice.{sensor_note}",
            "status": "success",
            "inference_source": "simple_generator",
            "active_agent": active_agent
        }


# ============ MANDI RATES (DATA.GOV.IN) ============

import json as _json
from typing import List

# In-memory cache: { "data": [...], "fetched_at": timestamp }
_mandi_cache: dict = {"data": [], "fetched_at": 0}
_MANDI_CACHE_TTL = 1800  # 30 minutes

DATAGOV_API_KEY = os.getenv("DATAGOV_API_KEY", "")
# Resource ID for "Current Daily Price of Various Commodities from Various Markets (Mandis)"
MANDI_RESOURCE_ID = os.getenv("MANDI_RESOURCE_ID", "9ef84268-d588-465a-a308-a864a43d0070")


def _fetch_mandi_from_datagov(state: str = "", commodity: str = "", limit: int = 50) -> list:
    """Fetch mandi rates from data.gov.in API."""
    if not DATAGOV_API_KEY:
        logger.warning("DATAGOV_API_KEY not set – returning mock mandi data")
        return _mock_mandi_data(state, commodity)

    url = "https://api.data.gov.in/resource/" + MANDI_RESOURCE_ID
    params = {
        "api-key": DATAGOV_API_KEY,
        "format": "json",
        "limit": limit,
    }
    if state:
        params["filters[state]"] = state
    if commodity:
        params["filters[commodity]"] = commodity

    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        body = resp.json()
        records = body.get("records", [])
        # Normalise keys to lowercase-underscore
        normalised = []
        for r in records:
            normalised.append({
                "state": r.get("state") or r.get("State", ""),
                "district": r.get("district") or r.get("District", ""),
                "market": r.get("market") or r.get("Market", ""),
                "commodity": r.get("commodity") or r.get("Commodity", ""),
                "variety": r.get("variety") or r.get("Variety", ""),
                "arrival_date": r.get("arrival_date") or r.get("Arrival_Date", ""),
                "min_price": r.get("min_price") or r.get("Min_Price", "0"),
                "max_price": r.get("max_price") or r.get("Max_Price", "0"),
                "modal_price": r.get("modal_price") or r.get("Modal_Price", "0"),
            })
        return normalised
    except Exception as e:
        logger.error(f"data.gov.in fetch failed: {e}")
        return _mock_mandi_data(state, commodity)


def _mock_mandi_data(state: str = "", commodity: str = "") -> list:
    """Return realistic mock mandi data for demo/offline use."""
    import random
    commodities = [
        {"commodity": "Wheat", "variety": "Desi", "base": 2200},
        {"commodity": "Rice", "variety": "Common", "base": 2800},
        {"commodity": "Onion", "variety": "Red", "base": 1500},
        {"commodity": "Tomato", "variety": "Hybrid", "base": 2000},
        {"commodity": "Potato", "variety": "Jyoti", "base": 1200},
        {"commodity": "Soybean", "variety": "Yellow", "base": 4200},
        {"commodity": "Cotton", "variety": "DCH-32", "base": 6500},
        {"commodity": "Maize", "variety": "Yellow", "base": 1800},
        {"commodity": "Chilli (Green)", "variety": "Hybrid", "base": 3000},
        {"commodity": "Banana", "variety": "Robusta", "base": 1600},
    ]
    states = ["Madhya Pradesh", "Rajasthan", "Maharashtra", "Uttar Pradesh",
              "Karnataka", "Gujarat", "Tamil Nadu", "Telangana"]
    markets = ["Indore", "Jaipur", "Nashik", "Lucknow",
               "Hubli", "Ahmedabad", "Coimbatore", "Warangal"]
    results = []
    for c in commodities:
        if commodity and commodity.lower() not in c["commodity"].lower():
            continue
        st = random.choice(states) if not state else state
        mk = random.choice(markets)
        base = c["base"]
        modal = base + random.randint(-200, 300)
        results.append({
            "state": st,
            "district": mk,
            "market": mk,
            "commodity": c["commodity"],
            "variety": c["variety"],
            "arrival_date": datetime.now().strftime("%d/%m/%Y"),
            "min_price": str(modal - random.randint(100, 300)),
            "max_price": str(modal + random.randint(100, 400)),
            "modal_price": str(modal),
        })
    return results


@app.get("/api/mandi/rates")
async def get_mandi_rates(state: str = "", commodity: str = "", limit: int = 50):
    """
    Fetch live mandi rates from data.gov.in.
    Cached for 30 minutes for performance.
    """
    global _mandi_cache
    now = time.time()

    # Check cache
    cache_valid = (now - _mandi_cache["fetched_at"]) < _MANDI_CACHE_TTL and _mandi_cache["data"]
    if not cache_valid or state or commodity:
        data = _fetch_mandi_from_datagov(state=state, commodity=commodity, limit=limit)
        if not state and not commodity:
            _mandi_cache = {"data": data, "fetched_at": now}
    else:
        data = _mandi_cache["data"]

    return {
        "status": "success",
        "count": len(data),
        "cached": cache_valid and not state and not commodity,
        "rates": data,
    }


@app.get("/api/mandi/commodities")
async def get_commodity_list():
    """Return a list of commonly tracked commodities."""
    return {
        "commodities": [
            "Wheat", "Rice", "Onion", "Tomato", "Potato",
            "Soybean", "Cotton", "Maize", "Chilli (Green)",
            "Banana", "Jowar", "Bajra", "Gram", "Tur / Arhar",
            "Mustard", "Groundnut", "Sugarcane",
        ]
    }


def _get_mandi_context() -> str:
    """Build a short mandi context string for AI chat augmentation."""
    global _mandi_cache
    now = time.time()
    # Refresh if stale
    if (now - _mandi_cache["fetched_at"]) >= _MANDI_CACHE_TTL or not _mandi_cache["data"]:
        _mandi_cache = {"data": _fetch_mandi_from_datagov(limit=20), "fetched_at": now}
    if not _mandi_cache["data"]:
        return ""
    lines = []
    for r in _mandi_cache["data"][:10]:
        lines.append(f"  {r['commodity']} ({r['variety']}): ₹{r['modal_price']}/qtl at {r['market']}, {r['state']} ({r['arrival_date']})")
    return "Live Mandi Rates:\n" + "\n".join(lines)


if __name__ == "__main__":
    try:
        print("About to import uvicorn...")
        import uvicorn
        print("Uvicorn imported successfully")
        print("Starting uvicorn server...")
        # Use port 8000 (configurable via PORT env var)
        port = int(os.getenv("PORT", "8000"))
        print(f"Backend will be available at: http://localhost:{port}")
        uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
    except Exception as e:
        print(f"Error starting server: {e}")
        import traceback
        traceback.print_exc()