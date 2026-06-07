"""
Marketplace Routes
POST /api/marketplace/match  — AI buyer/seller matching
"""

from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from skyview.utils.llm_pool import invoke_llm
from skyview.utils.logger import get_logger

router = APIRouter(prefix="/api/marketplace", tags=["Marketplace"])
logger = get_logger(__name__)


class MarketplaceMatchReq(BaseModel):
    crop: Optional[str] = None
    quantity_kg: Optional[float] = None
    location: Optional[str] = None
    preferred_price: Optional[float] = None
    message: Optional[str] = None


@router.post("/match")
async def marketplace_match(req: MarketplaceMatchReq):
    """Find potential buyers/traders for a farmer's produce."""
    details = []
    if req.crop:
        details.append(f"Crop: {req.crop}")
    if req.quantity_kg:
        details.append(f"Quantity: {req.quantity_kg} kg")
    if req.location:
        details.append(f"Location: {req.location}")
    if req.preferred_price:
        details.append(f"Desired price: ₹{req.preferred_price}/kg")
    if req.message:
        details.append(f"Note: {req.message}")

    context = "; ".join(details) if details else "General produce"

    prompt = (
        f"You are an Indian agricultural marketplace assistant. Farmer wants to sell: {context}.\n"
        "Suggest 4 realistic buyer/trader options and tips to get a good price. "
        'JSON: {"matches":[{"type":"Trader/FPO/APMC/Export","name":"...","contact_hint":"...","price_range":"..."}],'
        '"tips":["..."],"best_time_to_sell":"..."}'
    )

    raw = await invoke_llm([("user", prompt)], temperature=0.4, timeout=15)

    result = {}
    if raw:
        import json
        try:
            cleaned = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
            result = json.loads(cleaned)
        except Exception:
            result = {"matches": [], "tips": [raw[:300]], "best_time_to_sell": "Contact local APMC"}

    return {"status": "success", "request": context, **result}