from fastapi import APIRouter, UploadFile, File, Request
from pydantic import BaseModel
from typing import Optional, List, Dict
import os
import json
import uuid
from groq import Groq

router = APIRouter()

# ==========================================
# 2. GLOBAL VOICE STT & NLP PROCESSING 
# ==========================================

farmer_profile_db = {}

@router.post("/api/voice/process")
async def process_voice_audio(audio: UploadFile = File(...)):
    """
    Receives an audio file from the browser, passes it to Groq Whisper for fast STT,
    then uses ChatGroq (Llama3) to extract structured user profile data.
    """
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        return {"status": "error", "message": "GROQ_API_KEY missing", "identified_fields": {}}

    client = Groq(api_key=groq_api_key)
    
    # Save uploaded file temporarily
    import tempfile
    temp_file_path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}_{audio.filename}")
    try:
        with open(temp_file_path, "wb") as buffer:
            buffer.write(await audio.read())
            
        # 1. WHISPER STT (Speech-to-Text)
        with open(temp_file_path, "rb") as file:
            transcription = client.audio.transcriptions.create(
                file=(audio.filename, file.read()),
                model="whisper-large-v3",
                response_format="text",
                language="en"
            )
            
        transcript_text = transcription
        print(f"🎙️ Transcribed: {transcript_text}")
        
    except Exception as e:
        print(f"STT Error: {e}")
        return {"status": "error", "message": f"STT Failed: {e}", "identified_fields": {}}
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            
    # 2. NLP EXTRACTION (GPT / LLM)
    try:
        from langchain_groq import ChatGroq
        from langchain_core.messages import SystemMessage, HumanMessage
        
        chat = ChatGroq(temperature=0.1, model_name="llama-3.1-8b-instant", groq_api_key=groq_api_key)
        system_prompt = """
        You are an AI data extractor for a farmer platform.
        Extract any of the following fields from the user's transcript:
        - name
        - phone (string)
        - land_size_acres (number)
        - crops (list of strings)
        - location (string)
        
        Respond ONLY with a valid JSON object containing the fields found.
        """
        
        response = chat.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Transcript: {transcript_text}")
        ])
        
        content = response.content.strip()
        if "```json" in content:
            content = content.split("```json")[-1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].strip()
            
        try:
            data = json.loads(content)
        except json.JSONDecodeError as je:
            print(f"JSON Parse Error: {je} from content: {content}")
            data = {}
        
        # Save to mock DB
        user_id = "123" # Hardcoded for now
        if user_id not in farmer_profile_db:
             farmer_profile_db[user_id] = {}
        farmer_profile_db[user_id].update(data)
        
        return {
            "status": "success",
            "transcript": transcript_text,
            "identified_fields": data,
            "message": "Successfully processed audio and extracted data!"
        }
    except Exception as e:
        print(f"NLP Error: {e}")
        return {"status": "error", "message": str(e), "identified_fields": {}, "transcript": transcript_text}

# ==========================================
# 3. GOVERNMENT SCHEME RECOMMENDATIONS
# ==========================================

@router.get("/api/profile")
async def get_profile(phone: str = None, user_id: str = "123"):
    """Fetches profile either from DB by phone or memory by user_id."""
    if phone:
        try:
            from tools import _get_session
            from sqlalchemy import text
            db = _get_session()
            user = db.execute(text("SELECT name, phone, land_size_acres, location, crops FROM users WHERE phone = :phone"), 
                              {"phone": phone}).fetchone()
            db.close()
            if user:
                return {
                    "status": "success", 
                    "profile": {
                        "name": user[0],
                        "phone": user[1],
                        "land_size_acres": user[2],
                        "location": user[3],
                        "crops": user[4].split(",") if user[4] else []
                    }
                }
        except Exception as e:
            print(f"Failed to fetch user from DB: {e}")
            
    return {"status": "success", "profile": farmer_profile_db.get(user_id, {})}

@router.post("/api/profile/save")
async def save_profile(request: Request):
    data = await request.json()
    user_id = data.get("user_id", "123")
    if user_id not in farmer_profile_db:
         farmer_profile_db[user_id] = {}
    farmer_profile_db[user_id].update(data)
    
    phone = data.get("phone")
    name = data.get("name", "Farmer")
    land_size = data.get("land_size_acres")
    location = data.get("location")
    crops = data.get("crops", [])
    if isinstance(crops, list):
        crops_str = ",".join(crops)
    else:
        crops_str = str(crops)
    
    # Save to persistent users database
    if phone:
        try:
            from tools import _get_session
            from sqlalchemy import text
            
            db = _get_session()
            # Try to update first, if not exists, then insert
            update_query = text("""
                UPDATE users SET name = :name, land_size_acres = :land_size, location = :location, crops = :crops 
                WHERE phone = :phone
            """)
            result = db.execute(update_query, {
                "name": name, "land_size": land_size, "location": location, "crops": crops_str, "phone": phone
            })
            
            if result.rowcount == 0:
                # Insert if not exists
                insert_query = text("""
                    INSERT INTO users (phone, name, land_size_acres, location, crops) 
                    VALUES (:phone, :name, :land_size, :location, :crops)
                """)
                db.execute(insert_query, {
                    "phone": phone, "name": name, "land_size": land_size, "location": location, "crops": crops_str
                })
            
            db.commit()
            db.close()
        except Exception as e:
            print(f"Failed to save user to DB: {e}")

    return {"status": "success", "message": "Profile saved", "profile": {
        "name": name, "phone": phone, "land_size_acres": land_size, "location": location, "crops": crops
    }}

class SchemeRecommendation(BaseModel):
    scheme_name: str
    description: str
    eligibility: bool
    required_docs: List[str]
    link: str

import requests

@router.get("/api/schemes/recommendations", response_model=List[SchemeRecommendation])
async def get_scheme_recommendations(phone: Optional[str] = None, land_size: Optional[float] = None, state: Optional[str] = None):
    """
    Fetches schemes from Data.gov.in based on user profile.
    """
    # If phone is provided, let's try to get more accurate profile from DB
    if phone and (land_size is None or state is None):
        try:
            from tools import _get_session
            from sqlalchemy import text
            db = _get_session()
            user = db.execute(text("SELECT land_size_acres, location FROM users WHERE phone = :phone"), 
                              {"phone": phone}).fetchone()
            db.close()
            if user:
                if land_size is None: land_size = user[0]
                if state is None: state = user[1]
        except Exception as e:
            print(f"Failed to fetch user context for schemes: {e}")

    api_key = os.getenv("DATAGOV_API_KEY")
    schemes = []

    # Fetch live mandi (commodity market) prices from Data.gov.in
    # Resource 35985678-0d79-46b4-9ed6-6f13308a1d24 = Agmarknet daily commodity prices (78M+ records)
    try:
        params = {
            "api-key": api_key,
            "format": "json",
            "limit": 5,
            "sort[Arrival_Date]": "desc",
        }
        if state:
            params["filters[State]"] = state.title()
        response = requests.get(
            "https://api.data.gov.in/resource/35985678-0d79-46b4-9ed6-6f13308a1d24",
            params=params,
            timeout=8.0
        )
        data = response.json()
        records = data.get("records", [])
        if records:
            print(f"✅ Live mandi data: {len(records)} records from Data.gov.in (state={state})")
            for r in records:
                commodity = r.get("Commodity", "Commodity")
                market    = r.get("Market", "")
                district  = r.get("District", "")
                modal     = r.get("Modal_Price", "N/A")
                min_p     = r.get("Min_Price", "N/A")
                max_p     = r.get("Max_Price", "N/A")
                date      = r.get("Arrival_Date", "")
                schemes.append(
                    SchemeRecommendation(
                        scheme_name=f"Today's Mandi Price: {commodity}",
                        description=f"{market}, {district} ({date}) — Min: ₹{min_p} | Modal: ₹{modal} | Max: ₹{max_p} per quintal",
                        eligibility=True,
                        required_docs=[],
                        link="https://agmarknet.gov.in/",
                        source="Live Data.gov.in — Agmarknet"
                    )
                )
        else:
            print(f"⚠️ Mandi API returned no records (state={state}).")
    except Exception as e:
        print(f"❌ Live mandi fetch failed: {e}")

    # Fallback to smart local recommendations to ensure user sees multiple options
    fallback_schemes = [
        SchemeRecommendation(
            scheme_name="PM-Kisan Samman Nidhi",
            description="Direct income support of Rs. 6,000 per year to all landholding farmer families.",
            eligibility=True if land_size and float(land_size) < 10 else False,
            required_docs=["Aadhar Card", "Bank Passbook", "Land Ownership Proof"],
            link="https://pmkisan.gov.in/"
        ),
        SchemeRecommendation(
            scheme_name="Pradhan Mantri Fasal Bima Yojana (PMFBY)",
            description="Financial support to farmers suffering crop loss/damage arising out of natural calamities.",
            eligibility=True,
            required_docs=["Aadhar Card", "Sowing Certificate", "Bank Passbook"],
            link="https://pmfby.gov.in/"
        ),
        SchemeRecommendation(
            scheme_name="Soil Health Card Scheme",
            description="Helps farmers to understand the nutrient status of their soil and use fertilizers judiciously.",
            eligibility=True,
            required_docs=["Aadhar Card", "Soil Sample Collection Report"],
            link="https://soilhealth.dac.gov.in/"
        ),
        SchemeRecommendation(
            scheme_name="Kisan Credit Card (KCC)",
            description="Provides farmers with timely access to credit for their cultivation and other needs.",
            eligibility=True,
            required_docs=["Aadhar Card", "Land Records", "Passport Size Photograph"],
            link="https://www.myscheme.gov.in/schemes/kcc"
        ),
        SchemeRecommendation(
            scheme_name="Paramparagat Krishi Vikas Yojana (PKVY)",
            description="Promotion of organic farming through a cluster approach and PGS certification.",
            eligibility=True if state and state.lower() in ["maharashtra", "karnataka", "sikkim"] else False,
            required_docs=["Aadhar Card", "Cluster Registration Proof"],
            link="https://pgsindia-ncof.dac.gov.in/pkvy/"
        )
    ]
    
    # Return a mix of API results and fallbacks
    return schemes + [s for s in fallback_schemes if s.eligibility]



# ==========================================
# 6. SMART FARMING CALENDAR
# ==========================================

class CalendarEvent(BaseModel):
    event_id: Optional[str] = None
    title: str
    date: str
    type: str  # e.g., 'watering', 'fertilizer', 'scheme_deadline'

# Mock DB for Calendar
calendar_db: Dict[str, List[CalendarEvent]] = {}

@router.get("/api/calendar")
async def get_calendar(user_id: str):
    return {"status": "success", "events": calendar_db.get(user_id, [])}

@router.post("/api/calendar")
async def add_calendar_event(user_id: str, event: CalendarEvent):
    if user_id not in calendar_db:
        calendar_db[user_id] = []
    
    event.event_id = str(uuid.uuid4())
    calendar_db[user_id].append(event)
    return {"status": "success", "event": event}

# ==========================================
# 7. MARKETPLACE MATCHING (CSV)
# ==========================================

# Mock DB generated from an 'uploaded CSV'
MARKETPLACE_CSV = [
    {"type": "labor", "name": "Ramu K", "location": "Punjab", "rate": "500/day", "available": True},
    {"type": "equipment", "name": "Tractor X2", "location": "Punjab", "rate": "1000/day", "available": True},
    {"type": "seeds", "name": "Wheat Seeds 10kg", "location": "Haryana", "rate": "800", "available": True}
]

class MarketplaceMatchRequest(BaseModel):
    need_type: str
    location: str

@router.post("/api/marketplace/match")
async def match_marketplace(request: MarketplaceMatchRequest):
    """
    Retrieves resources from CSV data based on farmer needs.
    """
    matches = [
        item for item in MARKETPLACE_CSV
        if item['type'].lower() == request.need_type.lower() and 
           item['location'].lower() == request.location.lower() and
           item['available']
    ]
    return {"status": "success", "matches": matches}
