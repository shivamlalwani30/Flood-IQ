"""
routers/prediction.py

GET /predict — returns the 6-hour-ahead flood probability and predicted
depth for every known zone, using the trained RandomForest model.
"""

import logging

from fastapi import APIRouter, HTTPException

from core.state import state
from ml.predict import predict_all_zones, model_metrics

logger = logging.getLogger("floodiq.prediction")
router = APIRouter(tags=["prediction"])


@router.get("/predict")
def get_predictions():
    zone_ids = list(state.flood_zones.keys())
    try:
        predictions = predict_all_zones(zone_ids)
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Prediction model not yet trained: {e}",
        )
    return {"predictions": predictions}


@router.get("/predict/model-info")
def get_model_info():
    try:
        metrics = model_metrics()
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
    return metrics
