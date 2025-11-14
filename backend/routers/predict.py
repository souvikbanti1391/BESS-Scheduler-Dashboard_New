from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import pandas as pd
import logging

from core.ensemble_engine import EnsembleEngine

router = APIRouter()

class ForecastRequest(BaseModel):
    data: list
    horizon_days: int
    model_name: str = "ensemble"


@router.post("/")
def predict(req: ForecastRequest):
    """
    Returns MCP forecast for N days.
    """

    try:
        # Convert incoming JSON to DataFrame
        df = pd.DataFrame(req.data)

        # Defensive coercion
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df["mcp"] = pd.to_numeric(df["mcp"], errors="coerce")

        # Load ensemble engine
        engine = EnsembleEngine(models_dir="backend/models")

        # Get forecast
        fc = engine.forecast(df, req.horizon_days, req.model_name)

        # Convert timestamps to strings for JSON
        fc["timestamp"] = fc["timestamp"].astype(str)

        return {
            "forecast": fc.to_dict(orient="records"),
            "model_used": req.model_name,
        }

    except Exception as e:
        logging.exception("Error in /predict/")
        raise HTTPException(
            status_code=500,
            detail=f"Predict failed: {str(e)}"
        )
