"""
routers/flood_zones.py

GET /zones — returns the current set of flood zones (with rendered
polygons) for the frontend to draw as map overlays.
"""

from fastapi import APIRouter, HTTPException

from core.state import state

router = APIRouter(tags=["flood_zones"])


@router.get("/zones")
def get_zones():
    return {"zones": state.all_zones_public()}


@router.get("/zones/{zone_id}")
def get_zone(zone_id: str):
    zones = {z["zone_id"]: z for z in state.all_zones_public()}
    if zone_id not in zones:
        raise HTTPException(status_code=404, detail=f"Unknown zone: {zone_id}")
    return zones[zone_id]


@router.get("/scenarios")
def get_scenarios():
    """
    Lists available historical replay scenarios (e.g. Bengaluru 2022,
    Chennai 2015) for the admin panel's replay selector.
    """
    from core.historical_replay import list_scenarios
    return {"scenarios": list_scenarios()}


@router.get("/scenarios/{scenario_id}")
def get_scenario_detail(scenario_id: str):
    from core.historical_replay import get_scenario
    scenario = get_scenario(scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail=f"Unknown scenario: {scenario_id}")
    return scenario
