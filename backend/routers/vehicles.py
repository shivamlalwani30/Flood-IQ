"""
routers/vehicles.py

CRUD for emergency vehicles. Vehicle position updates and route
recalculation triggers are also pushed over WebSocket by main.py's
WebSocket endpoint (see core/websocket_manager.py); this router covers
the plain REST surface used by the dashboard on load.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.state import state

router = APIRouter(tags=["vehicles"])


class VehicleCreate(BaseModel):
    id: str
    lat: float
    lng: float
    type: str = "ambulance"


@router.get("/vehicles")
def list_vehicles():
    return {"vehicles": state.all_vehicles()}


@router.post("/vehicles")
def create_vehicle(v: VehicleCreate):
    try:
        return state.add_vehicle(v.id, v.lat, v.lng, v.type)
    except (TypeError, ValueError) as e:
        # add_vehicle validates lat/lng range itself (Pydantic only checks
        # they're floats, not that they're valid coordinates) — without
        # this catch, an out-of-range request like {"lat": 999} would
        # propagate as an unhandled 500 instead of a clean 400.
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/vehicles/{vehicle_id}")
def get_vehicle(vehicle_id: str):
    vehicle = state.get_vehicle(vehicle_id)
    if vehicle is None:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return vehicle


@router.delete("/vehicles/{vehicle_id}")
def delete_vehicle(vehicle_id: str):
    if vehicle_id in state.vehicles:
        del state.vehicles[vehicle_id]
        return {"deleted": vehicle_id}
    raise HTTPException(status_code=404, detail="Vehicle not found")
