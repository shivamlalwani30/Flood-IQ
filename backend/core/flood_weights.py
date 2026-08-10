"""
core/flood_weights.py

Converts active flood zones into modified edge weights on the road graph,
implementing the core "flood-aware Dijkstra" idea: roads that are flooded
become expensive (slow) or impossible (impassable) to traverse, so the
shortest-path algorithm naturally routes around them.

Thresholds (must match frontend/src/utils/mapHelpers.js floodColor()):
    depth > 60cm  -> impassable (infinite weight)
    depth > 30cm  -> passable but slow (5x weight)
    depth > 0cm   -> minor slowdown (2x weight)
    depth == 0    -> unaffected
"""

import math
from typing import Iterable

DEPTH_IMPASSABLE_CM = 60
DEPTH_SLOW_CM = 30

WEIGHT_MULTIPLIER_SLOW = 5.0
WEIGHT_MULTIPLIER_MINOR = 2.0


def _point_in_circle(lat, lon, center_lat, center_lon, radius_m):
    """Cheap planar-approximation distance check; fine at city scale."""
    dy = (lat - center_lat) * 111_320
    dx = (lon - center_lon) * 111_320 * math.cos(math.radians(center_lat))
    return (dx * dx + dy * dy) ** 0.5 <= radius_m


def edge_intersects_zone(u_coords, v_coords, zone: dict) -> bool:
    """
    Check whether an edge (defined by its endpoint coordinates) intersects
    a flood zone. Zones are represented as a circle (center_lat, center_lng,
    radius_m) for simplicity and demo robustness — this is intentionally
    simpler than true polygon intersection so it's fast and predictable
    live on stage, while still being geographically meaningful.
    """
    center_lat = zone["center_lat"]
    center_lng = zone["center_lng"]
    radius_m = zone.get("radius_m", 250)

    for (lat, lon) in (u_coords, v_coords):
        if _point_in_circle(lat, lon, center_lat, center_lng, radius_m):
            return True

    # Also check the edge midpoint, so long edges that pass through a zone
    # without an endpoint inside it are still caught.
    mid_lat = (u_coords[0] + v_coords[0]) / 2
    mid_lon = (u_coords[1] + v_coords[1]) / 2
    return _point_in_circle(mid_lat, mid_lon, center_lat, center_lng, radius_m)


def get_flood_weight(base_weight: float, u_coords, v_coords, flood_zones: Iterable[dict]) -> float:
    """
    Given a base edge weight (e.g. travel time in seconds or length in
    meters) and the edge's endpoint coordinates, return a flood-adjusted
    weight. The edge is checked against every active flood zone; the
    worst (highest) applicable multiplier wins.
    """
    worst_multiplier = 1.0
    for zone in flood_zones:
        depth_cm = zone.get("depth_cm", 0)
        if depth_cm <= 0:
            continue
        if not edge_intersects_zone(u_coords, v_coords, zone):
            continue

        if depth_cm > DEPTH_IMPASSABLE_CM:
            return float("inf")
        elif depth_cm > DEPTH_SLOW_CM:
            worst_multiplier = max(worst_multiplier, WEIGHT_MULTIPLIER_SLOW)
        else:
            worst_multiplier = max(worst_multiplier, WEIGHT_MULTIPLIER_MINOR)

    return base_weight * worst_multiplier


def apply_flood_weights(graph, flood_zones: list[dict], weight_attr: str = "length") -> int:
    """
    Mutates the graph in place, setting a 'flood_weight' attribute on every
    edge based on current flood_zones. Returns the count of edges rendered
    impassable (useful for logging / demo narration).

    Call this once per flood-zone change, before running shortest_path with
    weight='flood_weight'.
    """
    impassable_count = 0
    for u, v, key, data in graph.edges(keys=True, data=True):
        base = data.get(weight_attr, 1)
        u_coords = (graph.nodes[u]["y"], graph.nodes[u]["x"])
        v_coords = (graph.nodes[v]["y"], graph.nodes[v]["x"])
        fw = get_flood_weight(base, u_coords, v_coords, flood_zones)
        data["flood_weight"] = fw
        if fw == float("inf"):
            impassable_count += 1
    return impassable_count
