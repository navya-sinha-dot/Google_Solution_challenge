"""
Chat & AI Routes
POST /api/chat              — general multi-agent chat
POST /api/weather-insight   — weather-focused LLM insight
POST /api/agriculture/qa    — structured farm Q&A
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from skyview.agents import mandi_agent, supervisor
from skyview.agents.agricultural_qa import generate_response as qa_generate
from skyview.data.queries import get_latest_weather, get_weather_history
from skyview.utils.config import get_settings
from skyview.utils.logger import get_logger
from skyview.utils.llm_pool import invoke_llm

router = APIRouter(tags=["AI / Chat"])
logger = get_logger(__name__)
settings = get_settings()


class ChatReq(BaseModel):
    message: str
    user_id: str = "default"


class InsightReq(BaseModel):
    message: str
    station_id: str = "WS01"
    user_id: str = "dashboard_user"


class QAReq(BaseModel):
    question: str
    station_id: str = "WS01"


def _sensor_context(station_id: str = "WS01") -> str:
    data = get_latest_weather(station_id)
    if not data:
        return ""
    return (
        f"Temperature: {data.get('temperature')}°C, "
        f"Humidity: {data.get('humidity')}%, "
        f"Pressure: {data.get('pressure')} hPa, "
        f"Wind: {data.get('wind_speed')} m/s, "
        f"Rainfall: {data.get('rainfall')} mm, "
        f"Soil Moisture: {data.get('soil_moisture')}%, "
        f"Soil Temp: {data.get('soil_temperature')}°C, "
        f"PM2.5: {data.get('pm25')} µg/m³, "
        f"UV Index: {data.get('uv_index')}"
    )


@router.post("/api/chat")
async def chat(req: ChatReq):
    sensor_ctx = _sensor_context()

    # Inject mandi context for commodity queries
    commodity = mandi_agent.detect_commodity(req.message)
    if commodity:
        rates = mandi_agent.fetch_rates(commodity=commodity, limit=10)
        mandi_ctx = "\n".join(
            f"  {r['commodity']} ({r['variety']}): ₹{r['modal_price']}/qtl "
            f"at {r['market']}, {r['state']}"
            for r in rates[:8]
        )
    else:
        mandi_ctx = mandi_agent.get_context_string()

    result = await supervisor.supervisor(
        message=req.message,
        sensor_context=sensor_ctx,
        mandi_context=mandi_ctx,
    )
    return {**result, "user_id": req.user_id, "timestamp": datetime.utcnow().isoformat()}


@router.post("/api/weather-insight")
async def weather_insight(req: InsightReq):
    ctx = _sensor_context(req.station_id)
    prompt = (
        f"You are an expert agricultural advisor.\n\n"
        f"Current sensor conditions:\n{ctx}\n\n"
        f"{req.message}\n\n"
        "Give 5 numbered, plain-text recommendations. No asterisks or markdown."
    )
    response = await invoke_llm([("user", prompt)], temperature=0.3, timeout=20)
    return {
        "response": response or "Unable to generate insights.",
        "status": "success",
        "station_id": req.station_id,
    }


@router.post("/api/agriculture/qa")
async def agriculture_qa(req: QAReq):
    latest = get_latest_weather(req.station_id)
    history = get_weather_history(req.station_id, hours=24, limit=24)

    sensor_data = {}
    if latest:
        sensor_data = {
            "env": {"t": latest.get("temperature"), "h": latest.get("humidity"), "p": latest.get("pressure")},
            "soil": {"t": latest.get("soil_temperature"), "m": latest.get("soil_moisture")},
            "wind": {"s": latest.get("wind_speed"), "d": latest.get("wind_direction")},
            "rain": latest.get("rainfall"),
        }

    answer, suggestions = await qa_generate(req.question, sensor_data, history)
    return {
        "question": req.question,
        "answer": answer,
        "suggestions": suggestions,
        "station_id": req.station_id,
        "timestamp": datetime.utcnow().isoformat(),
    }