"""
core/cascade.py

Multi-zone cascading flood simulation. When a zone is flooded past a
critical threshold, nearby zones are evaluated for secondary flooding —
weighted by geographic proximity AND the ML model's own predicted risk
for that zone given current conditions. This makes the cascade a real
demonstration of the prediction system influencing behavior, rather than
a scripted "zone 2 floods after zone 1" animation with no model in the
loop.

The cascade runs as a sequence of discrete steps (not continuous
real-time decay) so the frontend can drive it visually one zone at a
time, matching the pacing of a live demo.
"""

import math
import logging

from core.state import state

logger = logging.getLogger("floodiq.cascade")

EARTH_RADIUS_M = 6_371_000


def _haversine_m(lat1, lng1, lat2, lng2) -> float:
    """Great-circle distance between two points in meters."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def nearby_zones(origin_zone_id: str, max_distance_m: float = 3000) -> list[tuple[str, float]]:
    """
    Returns [(zone_id, distance_m), ...] for all zones within max_distance_m
    of the origin zone, sorted nearest-first. Excludes the origin itself.
    """
    if origin_zone_id not in state.flood_zones:
        return []
    origin = state.flood_zones[origin_zone_id]
    results = []
    for zid, zone in state.flood_zones.items():
        if zid == origin_zone_id:
            continue
        dist = _haversine_m(origin["center_lat"], origin["center_lng"], zone["center_lat"], zone["center_lng"])
        if dist <= max_distance_m:
            results.append((zid, dist))
    results.sort(key=lambda pair: pair[1])
    return results


def compute_cascade_plan(origin_zone_id: str, origin_depth_cm: float, max_steps: int = 3) -> list[dict]:
    """
    Given a newly-triggered origin zone, returns an ordered cascade plan:
    a list of {zone_id, depth_cm, delay_ms, reason} dicts describing which
    nearby zones should flood next, in what order, with what severity, and
    why — driven by a blend of proximity and the ML model's own predicted
    risk for each candidate zone under current (post-trigger) conditions.

    This does NOT mutate state — it only plans. The caller (WebSocket
    handler) is responsible for executing the plan over time and
    broadcasting each step.
    """
    if origin_depth_cm <= 30:
        # Only a meaningfully severe trigger initiates a cascade; a minor
        # flood has no real basis for spreading to neighboring zones.
        return []

    candidates = nearby_zones(origin_zone_id, max_distance_m=3000)
    if not candidates:
        return []

    try:
        from ml.predict import predict_zone, inject_rainfall
    except Exception as e:
        logger.warning("Cascade planning: ML model unavailable (%s), falling back to proximity-only", e)
        predict_zone, inject_rainfall = None, None

    scored = []
    for zid, dist_m in candidates:
        proximity_score = max(0.0, 1.0 - dist_m / 3000)  # 1.0 at zone center, 0.0 at 3km out

        if predict_zone is not None and inject_rainfall is not None:
            try:
                # A severe flood event is rarely confined to one polygon —
                # the same storm cell that flooded the origin zone is
                # raining on its neighbors too, just less intensely the
                # further out you go. Without this, predict_zone() for a
                # nearby zone reflects only ITS OWN prior rainfall history,
                # which has nothing to do with the storm that just hit the
                # origin — so the cascade's risk scoring would be blind to
                # the very event that's supposedly causing it to spread.
                regional_rainfall_mm = origin_depth_cm * 0.8 * proximity_score
                if regional_rainfall_mm > 1:
                    inject_rainfall(zid, rainfall_1h_mm=min(regional_rainfall_mm, 90))
                pred = predict_zone(zid)
                model_risk = pred["probability_6h"]
            except Exception:
                model_risk = 0.3  # neutral fallback if prediction fails for this zone
        else:
            model_risk = 0.3

        # Blend: proximity matters (physically adjacent water has to go
        # somewhere) but the model's own assessment of that zone's
        # vulnerability (drainage, elevation, current saturation) should
        # weigh at least as much — otherwise this would just be "nearest
        # zone floods next" with the ML model along for the ride.
        combined_score = 0.45 * proximity_score + 0.55 * model_risk
        scored.append((zid, dist_m, model_risk, combined_score))

    scored.sort(key=lambda row: row[3], reverse=True)
    top = scored[:max_steps]

    plan = []
    for i, (zid, dist_m, model_risk, score) in enumerate(top):
        # Severity decays with cascade order and is modulated by the
        # model's own risk for that specific zone — a zone the model
        # considers low-risk floods less severely even if it's close.
        base_depth = origin_depth_cm * (0.75 ** (i + 1))
        depth_cm = round(base_depth * (0.5 + model_risk), 1)
        depth_cm = max(10.0, min(depth_cm, 95.0))

        plan.append({
            "zone_id": zid,
            "depth_cm": depth_cm,
            "delay_ms": 1800 * (i + 1),
            "distance_m": round(dist_m, 0),
            "model_risk": round(model_risk, 3),
            "reason": (
                f"{round(dist_m)}m from {origin_zone_id}, "
                f"model risk {model_risk*100:.0f}%"
            ),
        })

    logger.info("Cascade plan from %s: %s", origin_zone_id, [p["zone_id"] for p in plan])
    return plan
