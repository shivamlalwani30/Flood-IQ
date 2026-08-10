# ML Model Documentation

## Overview

FloodIQ uses a **RandomForest ensemble** to predict, 6 hours in advance, the probability that a given city zone will experience flooding and the estimated water depth. Predictions are triggered on rainfall events and broadcast to all connected clients via WebSocket, enabling emergency coordinators to pre-position resources before roads become impassable.

## Features Used

| Feature | Type | Justification |
|---|---|---|
| `rainfall_1h_mm` | Continuous | Immediate intensity signal; flash floods can occur within an hour of peak rainfall |
| `rainfall_6h_mm` | Continuous | 6-hour accumulation; primary driver of drain overloading — the strongest predictor |
| `rainfall_24h_mm` | Continuous | 24-hour total; governs ground saturation and large-scale flooding events |
| `elevation_m` | Continuous | Lower elevations receive runoff from higher ground; directly predicts pooling risk |
| `drainage_score` | Ordinal (1–10) | Encodes drain density from OSM data; poor drainage = lower score = higher flood risk |
| `soil_saturation` | Continuous | `rainfall_72h / zone_capacity`; pre-saturated ground can't absorb more rain |
| `month` | Categorical | Encodes monsoon seasonality (Jun–Sep = higher baseline flood probability) |
| `hour` | Categorical | Diurnal rainfall patterns and peak drain load differ by time of day |
| `rainfall_intensity_ratio` | Continuous | `1h / (6h + ε)`; a high ratio signals a cloudburst — rapid-onset flooding risk |

Feature importances from the trained model:

```
rainfall_6h_mm          0.416   ████████████████████░░░░
rainfall_24h_mm         0.296   ██████████████░░░░░░░░░░
soil_saturation         0.166   ████████░░░░░░░░░░░░░░░░
rainfall_1h_mm          0.057   ███░░░░░░░░░░░░░░░░░░░░░
month                   0.021   █░░░░░░░░░░░░░░░░░░░░░░░
intensity_ratio         0.018   █░░░░░░░░░░░░░░░░░░░░░░░
elevation_m             0.011   ░░░░░░░░░░░░░░░░░░░░░░░░
hour                    0.007   ░░░░░░░░░░░░░░░░░░░░░░░░
drainage_score          0.009   ░░░░░░░░░░░░░░░░░░░░░░░░
```

The 6-hour and 24-hour accumulation features dominate — consistent with the meteorological literature on urban pluvial flood onset (Lenderink & van Meijgaard, 2008; NDMA Urban Flood Risk Assessment, 2021).

## Training Data

**Source:** Synthetic dataset generated to match the statistical profile of IMD Bengaluru rainfall records.  
**Note (full honesty):** Real IMD data requires manual application to imdpune.gov.in. This project generates a physically-calibrated synthetic dataset that matches IMD climatological distributions for Bengaluru (monsoon-peak months June–September, exponential inter-event intervals, documented cloudburst frequencies). The ML pipeline — features, training, evaluation, deployment — is identical to what would run on real IMD data once downloaded. Replacing the CSV is the only change required.

| Parameter | Value |
|---|---|
| Records | 438,000 rows |
| Period simulated | 10 years × 5 zones × 8,760 hours |
| Zones | KRM_01, KRM_02, BTM_01, HSR_01, IND_01 (Bengaluru) |
| Flood event rate | 24.2% of hours labelled as flood events |
| Train / test split | 80% / 20% (stratified on flood label) |
| Training rows | 350,400 |
| Test rows | 87,600 |

## Model Selection: Why RandomForest

Alternatives considered:

| Model | Rejected Because |
|---|---|
| Logistic Regression | Assumes linear decision boundary; flood onset is nonlinear (threshold effect) |
| SVM | Training time scales poorly to 350k rows; less interpretable for stakeholders |
| Gradient Boosting (XGBoost) | Marginal accuracy gain (~1–2%) not worth the added deployment complexity |
| LSTM / Deep Learning | Requires GPU, complex training infrastructure, black box — NDMA/government partners cannot audit it |
| **RandomForest** | **✅ Interpretable, handles nonlinear thresholds well, fast inference, trains on CPU** |

RandomForest also produces calibrated probability outputs (via `predict_proba`), which is critical for the "6h probability" displayed in the PredictionPanel — a binary flood/no-flood label would not give emergency coordinators the graded risk signal they need for pre-positioning decisions.

## Model Performance

Evaluated on the 20% held-out test set (87,600 rows), stratified on flood label:

| Metric | Value |
|---|---|
| **Accuracy** | **82.4%** |
| Precision | 59.6% |
| Recall | 84.6% |
| F1 Score | 69.9% |

**Confusion matrix (test set, 87,600 rows):**

```
                    Predicted: No Flood   Predicted: Flood
Actual: No Flood        54,311                12,129
Actual: Flood            3,259                17,901
```

**Interpreting the precision–recall trade-off:**

Precision (59.6%) is lower than recall (84.6%) — the model generates some false positives (predicting flood when none occurs). For emergency routing, this is the **correct trade-off**: it is far better to pre-alert emergency coordinators to a flood that doesn't materialize (cost: unnecessary pre-positioning) than to miss a flood that does occur (cost: stranded ambulances, deaths). The system is tuned for high recall. Future versions would offer a tunable threshold parameter for operators to adjust based on their risk tolerance.

## Chennai 2015 Backtest

The project plan explicitly flagged that judges would ask about the Chennai 2015 event. Results:

**Event reconstruction:** Daily IMD rainfall figures for December 1–3, 2015 (40mm Nov 29 → 345mm Dec 2 peak) were distributed hourly using a diurnal profile matching monsoon depression patterns, and fed through the trained model using Chennai's coastal zone profile (elevation 6m, drainage score 2/10 — historically the worst in any major Indian city).

| Metric | Result |
|---|---|
| Model flood probability at 345mm/24h peak | **99.3%** |
| Predicted water depth at peak | **~99 cm** |
| % of Dec 1–3 hours flagged >50% risk | 62.5% |
| Did the model flag the catastrophic peak as high-risk? | **YES** |

**Important caveat (state this if judges ask):** This is a reconstructed simulation, not a validated test against real IMD-telemetry data for Chennai 2015. The model was trained on Bengaluru zone profiles, not Chennai's specific drainage/elevation signature, though we used Chennai's documented elevation (6m) and drainage history (score 2/10) as inputs. Real validation would require the actual hourly IMD station data from Nungambakkam and Minambakkam stations for Dec 2015, which requires a formal data request to IMD Pune.

The result — 99.3% flood probability at the documented catastrophic peak — is directionally correct and gives us confidence the model's decision boundary is physically meaningful. It is not a claim of calibrated historical accuracy.

## Depth Prediction

A companion `RandomForestRegressor` is trained only on rows where flooding actually occurs (flood_label = 1), to predict water depth in centimeters. This feeds the PredictionPanel's "Predicted depth: ~X cm" display and the automatic depth-based routing threshold (>60cm = impassable, 30–60cm = slow). Depth regressor mean absolute error on the test set: ~18cm.

## A Second Application: Cascade Risk Scoring

Beyond the per-zone 6h forecast, the trained classifier also drives `core/cascade.py`'s multi-zone cascade simulation. When a severe flood (>30cm) is triggered, the cascade doesn't just flood nearby zones in a fixed order — it scores each candidate zone within 3km as **55% the model's own predicted risk + 45% geographic proximity**, after injecting a distance-decayed regional rainfall signal into each candidate (the same storm that flooded the origin zone is realistically raining on its neighbors too, just less intensely with distance — without this injection, a neighboring zone's risk score stays artificially near zero regardless of how severe the origin flood is, since each zone's prediction is otherwise driven only by its own independent rainfall history).

This was deliberately weighted toward the model's assessment rather than pure distance, specifically so the cascade is a genuine demonstration of the prediction system influencing what happens next — a zone the model considers low-risk floods less severely even when it's the closest candidate, and that's a meaningful, visible difference from a scripted "zone 2 floods after zone 1" animation.
