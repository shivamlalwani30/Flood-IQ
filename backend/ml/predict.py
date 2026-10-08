"""
ml/predict.py

Inference layer: loads the trained model bundle and exposes a simple
predict_zone() function used by routers/prediction.py. Also maintains a
lightweight in-memory rainfall accumulator per zone, fed by simulated
rainfall events (admin panel / scripted demo), so predictions respond
to what's actually happening in the live demo rather than static numbers.
"""

import logging
import time
import datetime
from pathlib import Path

import joblib
import numpy as np

from ml.train_model import FEATURE_COLS, ZONE_PROFILES

logger = logging.getLogger("floodiq.predict")

MODEL_PATH = Path(__file__).resolve().parent / "model.pkl"

_model_bundle = None


def _load_bundle():
    global _model_bundle
    if _model_bundle is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                "ml/model.pkl not found. Run `python -m ml.train_model` first."
            )
        _model_bundle = joblib.load(MODEL_PATH)
        logger.info("Loaded model bundle (trained on %d rows)", _model_bundle["metrics"]["n_train"])
    return _model_bundle


# Per-zone rolling rainfall state, fed by simulated rainfall events.
# This is intentionally simple in-memory state (no DB, per architecture).
_zone_rainfall_state: dict[str, dict] = {}


def clear_all_rainfall_state():
    """
    Wipes every zone's rainfall accumulator. Used by core/state.py's
    reset_all() — without this, a demo-day reset would correctly show
    every zone as dry (depth_cm=0) while predictions still reflected
    stale injected rainfall from before the reset, since this module's
    state is independent of core/state.py's flood_zones dict.
    """
    _zone_rainfall_state.clear()


def inject_rainfall(zone_id: str, rainfall_1h_mm: float):
    """Called when the admin panel / demo simulates a rainfall event for a zone."""
    now = time.time()
    state = _zone_rainfall_state.setdefault(zone_id, {"history": []})
    state["history"].append((now, rainfall_1h_mm))
    # Keep last 200 entries; in demo time this comfortably covers 72h of
    # simulated rolling windows without unbounded growth.
    state["history"] = state["history"][-200:]


def _rolling_sum(history: list[tuple[float, float]], window_entries: int) -> float:
    if not history:
        return 0.0
    return float(sum(v for _, v in history[-window_entries:]))


def predict_zone(zone_id: str) -> dict:
    """
    Returns {probability_6h, predicted_depth_cm} for a zone, using injected
    rainfall history if present, else zone defaults (dry state).
    """
    bundle = _load_bundle()
    clf, reg = bundle["classifier"], bundle["regressor"]

    elevation_m, drainage_score = ZONE_PROFILES.get(zone_id, (905, 4))
    history = _zone_rainfall_state.get(zone_id, {}).get("history", [])

    rain_1h = history[-1][1] if history else 0.0
    rain_6h = _rolling_sum(history, 6)
    rain_24h = _rolling_sum(history, 24)
    rain_72h = _rolling_sum(history, 72)

    zone_capacity = 150 + drainage_score * 20
    soil_saturation = rain_72h / zone_capacity
    intensity_ratio = rain_1h / (rain_6h + 1e-3)

    now = datetime.datetime.now()

    import pandas as pd
    features = pd.DataFrame([[
        rain_1h, rain_6h, rain_24h, elevation_m, drainage_score,
        soil_saturation, now.month, now.hour, intensity_ratio,
    ]], columns=FEATURE_COLS)

    proba = float(clf.predict_proba(features)[0, 1])
    depth = float(reg.predict(features)[0]) if proba > 0.15 else 0.0

    return {
        "zone_id": zone_id,
        "probability_6h": round(proba, 3),
        "predicted_depth_cm": round(max(depth, 0), 1),
    }


def predict_all_zones(zone_ids: list[str]) -> list[dict]:
    return [predict_zone(zid) for zid in zone_ids]


def model_metrics() -> dict:
    bundle = _load_bundle()
    return bundle["metrics"]
