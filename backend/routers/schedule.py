from fastapi import APIRouter
from pydantic import BaseModel
import pandas as pd
from core.scheduler import run_scheduler

router = APIRouter()

class ScheduleRequest(BaseModel):
    data: list
    bess_power: float
    bess_energy: float
    horizon_days: int

@router.post('/')
def schedule(req: ScheduleRequest):
    df = pd.DataFrame(req.data)
    schedule_df = run_scheduler(df, req.bess_power, req.bess_energy, req.horizon_days)
    return {"schedule": schedule_df.to_dict(orient='records')}
