"""
ml/train_model.py

Trains a RandomForest classifier (flood / no-flood) and a companion
regressor (predicted depth_cm) for 6-hour-ahead flood prediction.

Data note (be upfront about this in docs/09_limitations_and_future_work.md):
Real IMD rainfall CSVs (imdpune.gov.in) and NDMA flood event records should
replace this synthetic generator before any real deployment. This script
generates physically-plausible synthetic training data so the full ML
pipeline (feature engineering -> train -> evaluate -> backtest -> serve)
is real, working code end-to-end during the hackathon, with a clearly
documented, swappable data source.

Run with: python -m ml.train_model
"""

import logging
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
)
from sklearn.model_selection import train_test_split

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("floodiq.train_model")

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
MODEL_PATH = Path(__file__).resolve().parent / "model.pkl"
RAINFALL_CSV = DATA_DIR / "rainfall_history.csv"

FEATURE_COLS = [
    "rainfall_1h_mm", "rainfall_6h_mm", "rainfall_24h_mm",
    "elevation_m", "drainage_score", "soil_saturation", "month", "hour",
    "rainfall_intensity_ratio",
]

ZONE_PROFILES = {
    # zone_id: (elevation_m, drainage_score 1-10 [low=poor drainage])
    "KRM_01": (905, 3),  # Koramangala — known low-lying, poor drainage
    "KRM_02": (910, 4),
    "BTM_01": (898, 3),
    "HSR_01": (912, 5),
    "IND_01": (920, 6),
}


def generate_synthetic_dataset(n_years: int = 10, seed: int = 42) -> pd.DataFrame:
    """
    Generates hourly synthetic rainfall + flood-label records per zone
    across n_years of (synthetic) monsoon seasons, calibrated so that
    heavy rainfall + low elevation + poor drainage produces flooding —
    mirroring the real causal structure IMD/NDMA data would show.
    """
    rng = np.random.default_rng(seed)
    rows = []

    hours_per_year = 24 * 365
    for zone_id, (elevation_m, drainage_score) in ZONE_PROFILES.items():
        for year in range(n_years):
            # Simulate monsoon-weighted rainfall (Jun-Sep heavier, per IMD climatology)
            rain_1h = np.zeros(hours_per_year)
            for month in range(1, 13):
                start = (month - 1) * 30 * 24
                end = month * 30 * 24
                end = min(end, hours_per_year)
                monsoon_factor = 3.5 if month in (6, 7, 8, 9) else 0.6
                base_rate = rng.exponential(scale=monsoon_factor, size=max(end - start, 0))
                # occasional cloudburst spikes
                spikes = rng.random(max(end - start, 0)) < 0.01
                base_rate[spikes] += rng.uniform(40, 90, size=spikes.sum())
                rain_1h[start:end] = base_rate

            rain_6h = pd.Series(rain_1h).rolling(6, min_periods=1).sum().values
            rain_24h = pd.Series(rain_1h).rolling(24, min_periods=1).sum().values
            rain_72h = pd.Series(rain_1h).rolling(72, min_periods=1).sum().values

            zone_capacity = 150 + drainage_score * 20  # better drainage -> higher effective capacity
            soil_saturation = rain_72h / zone_capacity

            for h in range(hours_per_year):
                month = (h // (30 * 24)) % 12 + 1
                hour_of_day = h % 24

                # Intensity ratio: how concentrated is the rain in the last hour
                # vs the last 6 — a high ratio signals a cloudburst (flash-flood
                # risk) even when 6h/24h totals look moderate.
                intensity_ratio = rain_1h[h] / (rain_6h[h] + 1e-3)

                flood_score = (
                    0.32 * min(rain_6h[h] / 80, 1.5)
                    + 0.22 * min(rain_24h[h] / 150, 1.5)
                    + 0.18 * soil_saturation[h]
                    + 0.14 * (1 - drainage_score / 10)
                    + 0.05 * max(0, (920 - elevation_m) / 30)
                    + 0.09 * min(intensity_ratio, 1.0)
                )
                # Sharper decision boundary: real urban flooding is closer to a
                # threshold effect (drains overflow once capacity is exceeded)
                # than a smooth logistic blend, so a higher slope here gives
                # cleaner, more learnable separation between flood/no-flood
                # while keeping a realistic transition band (not a hard cliff).
                flood_prob_true = 1 / (1 + np.exp(-10 * (flood_score - 0.55)))
                is_flood = rng.random() < flood_prob_true
                depth_cm = 0.0
                if is_flood:
                    depth_cm = float(np.clip(rng.normal(loc=flood_score * 90, scale=15), 5, 150))

                rows.append({
                    "zone_id": zone_id,
                    "rainfall_1h_mm": round(float(rain_1h[h]), 2),
                    "rainfall_6h_mm": round(float(rain_6h[h]), 2),
                    "rainfall_24h_mm": round(float(rain_24h[h]), 2),
                    "elevation_m": elevation_m,
                    "drainage_score": drainage_score,
                    "soil_saturation": round(float(soil_saturation[h]), 3),
                    "month": month,
                    "hour": hour_of_day,
                    "rainfall_intensity_ratio": round(float(intensity_ratio), 3),
                    "flood_label": int(is_flood),
                    "depth_cm": round(depth_cm, 1),
                })

    df = pd.DataFrame(rows)
    return df


def load_or_generate_dataset() -> pd.DataFrame:
    if RAINFALL_CSV.exists():
        logger.info("Loading existing rainfall history from %s", RAINFALL_CSV)
        return pd.read_csv(RAINFALL_CSV)
    logger.info("No rainfall_history.csv found — generating synthetic IMD-style dataset")
    df = generate_synthetic_dataset()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(RAINFALL_CSV, index=False)
    logger.info("Saved synthetic dataset: %d rows to %s", len(df), RAINFALL_CSV)
    return df


def train():
    df = load_or_generate_dataset()
    logger.info("Dataset: %d rows, flood rate %.1f%%", len(df), 100 * df["flood_label"].mean())

    X = df[FEATURE_COLS]
    y_clf = df["flood_label"]
    y_reg = df["depth_cm"]

    X_train, X_test, y_clf_train, y_clf_test, y_reg_train, y_reg_test = train_test_split(
        X, y_clf, y_reg, test_size=0.2, random_state=42, stratify=y_clf
    )

    clf = RandomForestClassifier(
        n_estimators=200, max_depth=12, min_samples_leaf=5,
        class_weight="balanced", random_state=42, n_jobs=-1,
    )
    clf.fit(X_train, y_clf_train)

    reg = RandomForestRegressor(
        n_estimators=200, max_depth=12, min_samples_leaf=5, random_state=42, n_jobs=-1,
    )
    # Depth regressor only meaningful where flooding actually occurs.
    flood_mask_train = y_clf_train == 1
    reg.fit(X_train[flood_mask_train], y_reg_train[flood_mask_train])

    y_pred = clf.predict(X_test)
    metrics = {
        "accuracy": accuracy_score(y_clf_test, y_pred),
        "precision": precision_score(y_clf_test, y_pred, zero_division=0),
        "recall": recall_score(y_clf_test, y_pred, zero_division=0),
        "f1": f1_score(y_clf_test, y_pred, zero_division=0),
        "confusion_matrix": confusion_matrix(y_clf_test, y_pred).tolist(),
        "feature_importance": dict(zip(FEATURE_COLS, clf.feature_importances_.round(4).tolist())),
        "n_train": len(X_train),
        "n_test": len(X_test),
    }

    logger.info("=== Model Evaluation ===")
    for k, v in metrics.items():
        logger.info("%s: %s", k, v)

    joblib.dump({"classifier": clf, "regressor": reg, "metrics": metrics, "feature_cols": FEATURE_COLS}, MODEL_PATH)
    logger.info("Model saved to %s", MODEL_PATH)
    return metrics


if __name__ == "__main__":
    train()
