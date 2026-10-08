"""
core/state.py

Shared in-memory application state, as specified in the architecture:
no database for the MVP. Flood zones are also mirrored to a JSON file
(data/flood_zones.json) so the current state survives a backend restart
and can be inspected/edited directly during the hackathon if needed.
"""

import json
import logging
from pathlib import Path
from threading import Lock

logger = logging.getLogger("floodiq.state")

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
FLOOD_ZONES_PATH = DATA_DIR / "flood_zones.json"

_lock = Lock()

# Preset zones for Bengaluru, used by both the admin panel dropdown and the
# scripted demo. center_lat/center_lng anchor a circular flood-impact area;
# radius_m controls how much of the road network around that point floods.
DEFAULT_ZONES = {
    "KRM_01": {"zone_id": "KRM_01", "label": "Koramangala 5th Block", "center_lat": 12.935, "center_lng": 77.614, "radius_m": 600, "depth_cm": 0},
    "KRM_02": {"zone_id": "KRM_02", "label": "Koramangala 80ft Road", "center_lat": 12.940, "center_lng": 77.625, "radius_m": 450, "depth_cm": 0},
    "BTM_01": {"zone_id": "BTM_01", "label": "BTM Layout", "center_lat": 12.916, "center_lng": 77.610, "radius_m": 500, "depth_cm": 0},
    "HSR_01": {"zone_id": "HSR_01", "label": "HSR Layout", "center_lat": 12.912, "center_lng": 77.638, "radius_m": 500, "depth_cm": 0},
    "IND_01": {"zone_id": "IND_01", "label": "Indiranagar 100ft Road", "center_lat": 12.971, "center_lng": 77.640, "radius_m": 450, "depth_cm": 0},
}


def _polygon_for_zone(zone: dict, n_points: int = 16) -> list[list[float]]:
    """Approximate the circular zone as an n-gon polygon for frontend rendering."""
    import math

    lat0, lon0, r = zone["center_lat"], zone["center_lng"], zone["radius_m"]
    points = []
    for i in range(n_points):
        theta = 2 * math.pi * i / n_points
        dlat = (r * math.cos(theta)) / 111_320
        dlon = (r * math.sin(theta)) / (111_320 * math.cos(math.radians(lat0)))
        points.append([lat0 + dlat, lon0 + dlon])
    return points


class AppState:
    def __init__(self):
        self.flood_zones: dict[str, dict] = {}
        self.vehicles: dict[str, dict] = {}
        self._load_zones()

    def _load_zones(self):
        if FLOOD_ZONES_PATH.exists():
            try:
                with open(FLOOD_ZONES_PATH) as f:
                    self.flood_zones = json.load(f)
                logger.info("Loaded %d flood zones from disk", len(self.flood_zones))
                return
            except Exception as e:
                logger.warning("Failed to load flood_zones.json (%s); using defaults", e)
        self.flood_zones = {k: dict(v) for k, v in DEFAULT_ZONES.items()}
        self._save_zones()

    def _save_zones(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(FLOOD_ZONES_PATH, "w") as f:
            json.dump(self.flood_zones, f, indent=2)

    def reset_all(self):
        """
        Demo-day recovery: clears every zone back to dry (0cm) and removes
        all vehicles, without restarting the backend process. Use when a
        live demo gets into a confusing state (multiple zones flooded,
        vehicles blocked) and the fastest way forward is a clean start
        rather than untangling exactly what's currently active.
        """
        with _lock:
            for zid in self.flood_zones:
                self.flood_zones[zid]["depth_cm"] = 0
            self._save_zones()
            self.vehicles = {}

        try:
            from ml.predict import clear_all_rainfall_state
            clear_all_rainfall_state()
        except Exception as e:
            logger.warning("Could not clear rainfall state during reset: %s", e)

        logger.info("Full state reset: all zones dry, all vehicles cleared, rainfall state cleared")

    def set_flood_depth(self, zone_id: str, depth_cm: float) -> dict:
        if not isinstance(depth_cm, (int, float)) or isinstance(depth_cm, bool):
            raise TypeError(f"depth_cm must be a number, got {type(depth_cm).__name__}: {depth_cm!r}")
        depth_cm = max(0.0, min(float(depth_cm), 500.0))  # clamp to a sane physical range

        with _lock:
            if zone_id not in self.flood_zones:
                base = DEFAULT_ZONES.get(zone_id, {
                    "zone_id": zone_id, "label": zone_id,
                    "center_lat": 12.935, "center_lng": 77.61, "radius_m": 400,
                })
                self.flood_zones[zone_id] = dict(base)
            self.flood_zones[zone_id]["depth_cm"] = depth_cm
            self._save_zones()
            return self.zone_public(zone_id)

    def zone_public(self, zone_id: str) -> dict:
        """Public representation including a rendered polygon, for the frontend."""
        z = self.flood_zones[zone_id]
        return {
            "zone_id": z["zone_id"],
            "label": z.get("label", z["zone_id"]),
            "depth_cm": z["depth_cm"],
            "center_lat": z["center_lat"],
            "center_lng": z["center_lng"],
            "radius_m": z["radius_m"],
            "polygon": _polygon_for_zone(z),
        }

    def all_zones_public(self) -> list[dict]:
        return [self.zone_public(zid) for zid in self.flood_zones]

    def active_zones_raw(self) -> list[dict]:
        """Zones with depth > 0, in the raw format flood_weights.py expects."""
        return [z for z in self.flood_zones.values() if z.get("depth_cm", 0) > 0]

    def add_vehicle(self, vehicle_id: str, lat: float, lng: float, vtype: str) -> dict:
        for name, val in (("lat", lat), ("lng", lng)):
            if not isinstance(val, (int, float)) or isinstance(val, bool):
                raise TypeError(f"{name} must be a number, got {type(val).__name__}: {val!r}")
        if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
            raise ValueError(f"lat/lng out of valid range: ({lat}, {lng})")

        with _lock:
            v = {
                "id": vehicle_id, "lat": lat, "lng": lng, "type": vtype,
                "destination_lat": None, "destination_lng": None,
                "eta_seconds": None, "distance_m": None, "status": "idle",
            }
            self.vehicles[vehicle_id] = v
            return v

    def update_vehicle_route(self, vehicle_id: str, eta_seconds: float, distance_m: float, status: str = "en_route"):
        with _lock:
            if vehicle_id in self.vehicles:
                self.vehicles[vehicle_id].update(
                    eta_seconds=eta_seconds, distance_m=distance_m, status=status
                )

    def get_vehicle(self, vehicle_id: str) -> dict | None:
        return self.vehicles.get(vehicle_id)

    def all_vehicles(self) -> list[dict]:
        return list(self.vehicles.values())


# Module-level singleton shared across routers.
state = AppState()
