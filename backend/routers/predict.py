from fastapi import APIRouter
from pydantic import BaseModel
import pandas as pd
from core.ensemble_engine import EnsembleEngine

router = APIRouter()

class ForecastRequest(BaseModel):
    data: list
    horizon_days: int
    model_name: str = "ensemble"

@router.post('/')
def predict(req: ForecastRequest):
    df = pd.DataFrame(req.data)
    engine = EnsembleEngine(models_dir="backend/models")
    fc = engine.forecast(df, req.horizon_days, req.model_name)
    return {"forecast": fc.to_dict(orient='records'), "model_used": req.model_name}
