"""
ml/backtest_chennai_2015.py

Backtests the trained flood model against a reconstructed approximation
of the December 2015 Chennai flood event — the single most-referenced
urban flood disaster in India, and explicitly flagged in the project plan
as a scenario judges are likely to ask about directly.

IMPORTANT HONESTY NOTE (also stated in docs/05_ml_model_documentation.md):
This is NOT the real IMD/NDMA Chennai 2015 dataset (that requires manual
download + licensing from imdpune.gov.in and was not available in this
sandboxed build environment). This script reconstructs the well-documented
public rainfall profile of the event (~1,049mm in a few days in early
December 2015, per IMD/NDMA public reporting) as a realistic input
sequence, and runs it through our trained model to check whether the
model's learned decision boundary correctly flags a known catastrophic
event as high-risk. This is a directional sanity check, not a claim of
validated historical accuracy — say this explicitly if judges ask.

Run with: python -m ml.backtest_chennai_2015
"""

import logging

import joblib
import numpy as np
import pandas as pd

from ml.train_model import MODEL_PATH, FEATURE_COLS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("floodiq.backtest")

# Reconstructed daily rainfall (mm) for Chennai, Dec 1-3 2015, based on
# widely reported IMD figures for the event (~250mm Dec 1, ~345mm Dec 2 peak).
# This is a simplified day-level reconstruction, not minute-level IMD telemetry.
CHENNAI_DEC_2015_DAILY_MM = {
    "2015-11-29": 40,
    "2015-11-30": 70,
    "2015-12-01": 250,
    "2015-12-02": 345,
    "2015-12-03": 180,
}

CHENNAI_ZONE_PROFILE = {"elevation_m": 6, "drainage_score": 2}  # Chennai: low-lying, historically poor drainage


def build_hourly_series():
    """Spread each day's total across 24 hours with an afternoon-peak skew,
    approximating typical monsoon depression rainfall distribution."""
    hourly = []
    diurnal_weights = np.array([
        0.01, 0.01, 0.01, 0.01, 0.02, 0.03, 0.04, 0.05,
        0.06, 0.07, 0.07, 0.07, 0.06, 0.06, 0.06, 0.06,
        0.06, 0.05, 0.05, 0.04, 0.03, 0.02, 0.02, 0.01,
    ])
    diurnal_weights = diurnal_weights / diurnal_weights.sum()

    for date, total_mm in CHENNAI_DEC_2015_DAILY_MM.items():
        for hour in range(24):
            hourly.append({"date": date, "hour": hour, "rainfall_1h_mm": total_mm * diurnal_weights[hour]})
    return pd.DataFrame(hourly)


def build_feature_frame(hourly_df: pd.DataFrame) -> pd.DataFrame:
    hourly_df = hourly_df.reset_index(drop=True)
    hourly_df["rainfall_6h_mm"] = hourly_df["rainfall_1h_mm"].rolling(6, min_periods=1).sum()
    hourly_df["rainfall_24h_mm"] = hourly_df["rainfall_1h_mm"].rolling(24, min_periods=1).sum()
    rain_72h = hourly_df["rainfall_1h_mm"].rolling(72, min_periods=1).sum()
    zone_capacity = 150 + CHENNAI_ZONE_PROFILE["drainage_score"] * 20
    hourly_df["soil_saturation"] = rain_72h / zone_capacity
    hourly_df["elevation_m"] = CHENNAI_ZONE_PROFILE["elevation_m"]
    hourly_df["drainage_score"] = CHENNAI_ZONE_PROFILE["drainage_score"]
    hourly_df["month"] = pd.to_datetime(hourly_df["date"]).dt.month
    hourly_df["rainfall_intensity_ratio"] = hourly_df["rainfall_1h_mm"] / (hourly_df["rainfall_6h_mm"] + 1e-3)
    return hourly_df


def run_backtest():
    if not MODEL_PATH.exists():
        raise FileNotFoundError("Model not found — run `python -m ml.train_model` first.")

    bundle = joblib.load(MODEL_PATH)
    clf, reg = bundle["classifier"], bundle["regressor"]

    hourly = build_hourly_series()
    features = build_feature_frame(hourly)
    X = features[FEATURE_COLS]

    proba = clf.predict_proba(X)[:, 1]
    pred_depth = reg.predict(X)

    features["flood_probability"] = proba
    features["predicted_depth_cm"] = pred_depth

    peak_idx = features["rainfall_24h_mm"].idxmax()
    peak_row = features.loc[peak_idx]

    logger.info("=== Chennai Dec 2015 Backtest ===")
    logger.info("Peak 24h rainfall window: %s hour %d -> %.1f mm",
                peak_row["date"], peak_row["hour"], peak_row["rainfall_24h_mm"])
    logger.info("Model flood probability at peak: %.1f%%", peak_row["flood_probability"] * 100)
    logger.info("Model predicted depth at peak: %.1f cm", peak_row["predicted_depth_cm"])

    pct_flagged_high_risk = (features["flood_probability"] > 0.5).mean() * 100
    logger.info("Pct of event hours flagged >50%% flood risk: %.1f%%", pct_flagged_high_risk)

    correctly_flagged = peak_row["flood_probability"] > 0.5
    logger.info("Did the model flag the known catastrophic peak as high-risk? %s",
                "YES" if correctly_flagged else "NO")

    return features, {
        "peak_probability": float(peak_row["flood_probability"]),
        "peak_predicted_depth_cm": float(peak_row["predicted_depth_cm"]),
        "pct_hours_flagged_high_risk": float(pct_flagged_high_risk),
        "correctly_flagged_peak": bool(correctly_flagged),
    }


if __name__ == "__main__":
    _, summary = run_backtest()
    print(summary)
