from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import pandas as pd
import logging

from core.scheduler import run_scheduler

router = APIRouter()

class ScheduleRequest(BaseModel):
    data: list
    bess_power: float
    bess_energy: float
    horizon_days: int


@router.post("/")
def schedule(req: ScheduleRequest):
    """
    Returns schedule (charge/discharge/SOC).
    """

    try:
        df = pd.DataFrame(req.data)

        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df["mcp"] = pd.to_numeric(df["mcp"], errors="coerce")

        out = run_scheduler(df, req.bess_power, req.bess_energy, req.horizon_days)

        out["timestamp"] = out["timestamp"].astype(str)

        return {"schedule": out.to_dict(orient="records")}

    except Exception as e:
        logging.exception("Error in /schedule/")
        raise HTTPException(
            status_code=500,
            detail=f"Schedule failed: {str(e)}"
        )
