"""
main.py

FastAPI entry point for FloodIQ backend.
Run with: uvicorn main:app --reload --port 8000
"""

import asyncio
import logging
import time

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("floodiq.main")

app = FastAPI(
    title="FloodIQ API",
    description="Real-time flood-aware emergency routing system for Indian cities.",
    version="0.1.0",
)

# CORS — wide open for hackathon demo. Tighten origins before any real deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "floodiq-backend"}


@app.on_event("startup")
def on_startup():
    from core.graph_engine import get_graph, graph_stats
    from core.state import state

    logger.info("Warming road graph cache...")
    G = get_graph()
    logger.info("Graph ready: %s", graph_stats(G))

    # Warm the ML model too, not just the graph. Without this, the model
    # only loads lazily on the first call to predict_zone() — meaning the
    # frontend's bootstrap fetch to /predict and /predict/model-info could
    # race a cold disk read + joblib deserialize and momentarily show
    # empty predictions / null accuracy on first load, before any flood
    # has even been triggered. This makes the Forecast tab correct from
    # the very first paint instead of only after the first prediction call.
    try:
        from ml.predict import model_metrics
        m = model_metrics()
        logger.info("ML model warmed: accuracy=%.4f", m["accuracy"])
    except FileNotFoundError:
        logger.warning(
            "ML model not yet trained (ml/model.pkl missing) — "
            "run `python -m ml.train_model` before starting the server for full functionality."
        )
    except Exception as e:
        logger.warning("Could not warm ML model at startup: %s", e)

    # Pre-seed 3 demo vehicles so the map is never empty on first open.
    # Positioned around Koramangala / Indiranagar matching the demo script.
    demo_vehicles = [
        ("AMB_01", 12.9319, 77.6127, "ambulance"),
        ("AMB_02", 12.9512, 77.6234, "ambulance"),
        ("FIRE_01", 12.9401, 77.6398, "fire_truck"),
    ]
    for vid, lat, lng, vtype in demo_vehicles:
        if vid not in state.vehicles:
            state.add_vehicle(vid, lat, lng, vtype)
            logger.info("Seeded demo vehicle: %s", vid)

    # Set destinations so auto-reroute triggers work immediately on first flood.
    state.vehicles["AMB_01"]["destination_lat"] = 12.9610
    state.vehicles["AMB_01"]["destination_lng"] = 77.6387   # Manipal Hospital
    state.vehicles["AMB_02"]["destination_lat"] = 12.9720
    state.vehicles["AMB_02"]["destination_lng"] = 77.6412   # Indiranagar
    state.vehicles["FIRE_01"]["destination_lat"] = 12.9166
    state.vehicles["FIRE_01"]["destination_lng"] = 77.6101  # BTM


# --- Router registration ---
# Each router is added defensively: if a router module isn't built yet
# (e.g. early in Day 1), the app still boots so we can iterate incrementally.
def _try_include(router_import_path: str, attr: str = "router"):
    try:
        module = __import__(router_import_path, fromlist=[attr])
        app.include_router(getattr(module, attr))
        logger.info("Registered router: %s", router_import_path)
    except ModuleNotFoundError:
        logger.info("Router not yet implemented, skipping: %s", router_import_path)


_try_include("routers.routing")
_try_include("routers.flood_zones")
_try_include("routers.prediction")
_try_include("routers.vehicles")
_try_include("routers.verification")


async def _apply_flood_event(zone_id: str, depth_cm: float):
    """
    Applies a flood depth to a single zone and propagates every consequence:
    rainfall injection, zone broadcast, vehicle auto-reroute, and prediction
    update. Shared by both trigger_flood and trigger_cascade (for the origin
    zone and every secondary cascade step) so this logic exists in exactly
    one place rather than being duplicated across event types.
    """
    from core.websocket_manager import manager
    from core.state import state
    from core.graph_engine import get_graph, nearest_node
    from core.flood_weights import apply_flood_weights
    from core.routing_engine import compute_flood_aware_path, NoPassableRouteError

    zone = state.set_flood_depth(zone_id, depth_cm)

    try:
        from ml.predict import inject_rainfall
        # Map depth event to an approximate rainfall signal so the
        # prediction model's "current state" stays consistent with
        # what the dispatcher/citizen just saw happen on the map.
        inject_rainfall(zone_id, rainfall_1h_mm=min(depth_cm * 0.8, 90))
    except Exception as e:
        logger.warning("Could not inject rainfall signal: %s", e)

    await manager.broadcast("flood_zone_update", zone)

    if depth_cm > 60:
        await manager.broadcast("alert", {
            "severity": "HIGH",
            "message": f"{zone.get('label', zone_id)} is now impassable ({depth_cm}cm). Rerouting affected vehicles.",
            "zones_affected": [zone_id],
        })

    # Auto-reroute every active vehicle so the dashboard updates within ~2s
    # without the dispatcher needing to click anything per vehicle.
    G = get_graph()
    apply_flood_weights(G, state.active_zones_raw())
    for v in state.all_vehicles():
        if v.get("destination_lat") is None:
            continue
        o_node = nearest_node(G, v["lat"], v["lng"])
        d_node = nearest_node(G, v["destination_lat"], v["destination_lng"])
        try:
            path_coords, distance_m, new_eta = compute_flood_aware_path(G, o_node, d_node)
            state.update_vehicle_route(v["id"], eta_seconds=new_eta, distance_m=distance_m)
            await manager.broadcast("vehicle_rerouted", {
                "vehicle_id": v["id"], "new_path": path_coords, "new_eta": new_eta,
            })
        except NoPassableRouteError:
            state.update_vehicle_route(v["id"], eta_seconds=None, distance_m=None, status="blocked")
            await manager.broadcast("alert", {
                "severity": "HIGH",
                "message": f"{v['id']} has no passable route — every connecting road is flooded.",
                "zones_affected": [zone_id],
            })
            logger.warning("No passable route for %s after flood update", v["id"])

    try:
        from ml.predict import predict_zone
        pred = predict_zone(zone_id)
        await manager.broadcast("prediction_update", {
            "zone_id": zone_id,
            "6h_probability": pred["probability_6h"],
            "predicted_depth_cm": pred["predicted_depth_cm"],
        })
    except FileNotFoundError:
        pass


async def _run_cascade_step(step: dict):
    """
    Waits for the planned delay, then applies a single cascade step's
    flood event and announces it. Runs as an independent asyncio task so
    multiple cascade steps can be in flight (waiting on their own delays)
    simultaneously without blocking the WebSocket receive loop or each other.
    """
    from core.websocket_manager import manager

    await asyncio.sleep(step["delay_ms"] / 1000)
    try:
        await _apply_flood_event(step["zone_id"], step["depth_cm"])
        await manager.broadcast("alert", {
            "severity": "HIGH" if step["depth_cm"] > 60 else "INFO",
            "message": (
                f"Cascade: {step['zone_id']} now flooding at {step['depth_cm']}cm "
                f"({step['reason']})."
            ),
            "zones_affected": [step["zone_id"]],
        })
    except Exception as e:
        logger.error("Cascade step failed for %s: %s", step["zone_id"], e)


# --- WebSocket endpoint ---
# Implements the client -> server events from the architecture doc:
#   trigger_flood, add_vehicle, request_route
# and broadcasts the corresponding server -> client events:
#   flood_zone_update, vehicle_rerouted, prediction_update, alert
async def _handle_ws_event(websocket: WebSocket, event: str, data: dict):
    """
    Dispatches a single parsed WebSocket event. Raises KeyError/TypeError/
    ValueError on malformed payloads (missing keys, wrong types, etc) —
    the caller (websocket_endpoint) catches these so one bad message never
    kills the connection. Keeping this as a separate function (rather than
    inline in the receive loop) is what makes that try/except boundary
    possible without duplicating the loop structure.
    """
    from core.websocket_manager import manager
    from core.state import state
    from core.graph_engine import get_graph, nearest_node
    from core.flood_weights import apply_flood_weights
    from core.routing_engine import compute_flood_aware_path, NoPassableRouteError

    if event == "trigger_flood":
        zone_id = data["zone_id"]
        depth_cm = data["depth_cm"]
        if not isinstance(depth_cm, (int, float)):
            raise TypeError(f"depth_cm must be a number, got {type(depth_cm).__name__}: {depth_cm!r}")
        depth_cm = max(0.0, min(float(depth_cm), 500.0))  # clamp to a sane physical range

        await _apply_flood_event(zone_id, depth_cm)

    elif event == "trigger_cascade":
        zone_id = data["zone_id"]
        depth_cm = data["depth_cm"]
        if not isinstance(depth_cm, (int, float)):
            raise TypeError(f"depth_cm must be a number, got {type(depth_cm).__name__}: {depth_cm!r}")
        depth_cm = max(0.0, min(float(depth_cm), 500.0))

        # Flood the origin zone immediately, exactly like trigger_flood does.
        await _apply_flood_event(zone_id, depth_cm)

        # Then plan and schedule secondary flooding of nearby zones, each
        # weighted by proximity AND the ML model's own risk assessment —
        # see core/cascade.py for the full scoring logic. Each step is
        # scheduled as an independent background task so this handler
        # returns immediately; the cascade unfolds visually over the next
        # several seconds exactly like a real storm spreading.
        from core.cascade import compute_cascade_plan
        plan = compute_cascade_plan(zone_id, depth_cm)

        if not plan:
            await manager.broadcast("alert", {
                "severity": "INFO",
                "message": f"No nearby zones at sufficient risk to cascade from {zone_id}.",
                "zones_affected": [],
            })
        else:
            await manager.broadcast("alert", {
                "severity": "INFO",
                "message": f"Cascade risk detected: {', '.join(p['zone_id'] for p in plan)} may flood next.",
                "zones_affected": [p["zone_id"] for p in plan],
            })
            for step in plan:
                asyncio.create_task(_run_cascade_step(step))

    elif event == "add_vehicle":
        v = state.add_vehicle(data["id"], data["lat"], data["lng"], data.get("type", "ambulance"))
        await manager.broadcast("vehicle_added", v)

    elif event == "request_route":
        vehicle_id = data["vehicle_id"]
        vehicle = state.get_vehicle(vehicle_id)
        if not vehicle:
            return
        dest_lat, dest_lng = data["destination_lat"], data["destination_lng"]
        G = get_graph()
        apply_flood_weights(G, state.active_zones_raw())
        o_node = nearest_node(G, vehicle["lat"], vehicle["lng"])
        d_node = nearest_node(G, dest_lat, dest_lng)
        try:
            path_coords, distance_m, eta = compute_flood_aware_path(G, o_node, d_node)
            state.vehicles[vehicle_id]["destination_lat"] = dest_lat
            state.vehicles[vehicle_id]["destination_lng"] = dest_lng
            state.update_vehicle_route(vehicle_id, eta_seconds=eta, distance_m=distance_m)
            await manager.broadcast("vehicle_rerouted", {
                "vehicle_id": vehicle_id, "new_path": path_coords, "new_eta": eta,
            })
        except NoPassableRouteError:
            await manager.send_personal(websocket, "alert", {
                "severity": "HIGH",
                "message": f"No passable route currently exists for {vehicle_id}.",
                "zones_affected": [],
            })
    else:
        logger.info("Unhandled WS event: %s", event)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    from core.websocket_manager import manager
    import json

    await manager.connect(websocket)
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning("Received non-JSON WS message: %s", raw)
                continue

            event = msg.get("event")
            data = msg.get("data", {})

            try:
                await _handle_ws_event(websocket, event, data)
            except (KeyError, TypeError, ValueError) as e:
                # Malformed event payload (missing key, wrong type, out-of-range
                # value) — log it and tell the sender, but never let a single
                # bad message kill the connection for this client or anyone
                # else. Without this, e.g. a non-numeric depth_cm in a
                # trigger_flood event would raise an unhandled TypeError deep
                # inside flood weight math and silently terminate the socket.
                logger.warning("Malformed WS event '%s': %s", event, e)
                try:
                    await manager.send_personal(websocket, "alert", {
                        "severity": "LOW",
                        "message": f"Ignored malformed '{event}' event: {e}",
                        "zones_affected": [],
                    })
                except Exception:
                    pass  # connection may already be in a bad state; don't compound it

    except WebSocketDisconnect:
        manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

