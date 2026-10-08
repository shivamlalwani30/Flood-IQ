"""
routers/routing.py

POST /route — the core endpoint. Given an origin and destination
(either as lat/lng or free-text place names), returns a flood-aware
shortest path through the road graph.
"""

import logging
import time

import networkx as nx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.graph_engine import get_graph, nearest_node
from core.flood_weights import apply_flood_weights
from core.routing_engine import compute_flood_aware_path, trace_edge_weight_changes, NoPassableRouteError
from core.state import state

logger = logging.getLogger("floodiq.routing")
router = APIRouter(tags=["routing"])

# Minimal geocoding for citizen-view free-text inputs. In production this
# would call a real geocoder (Nominatim/Google); for the hackathon demo we
# resolve a small set of well-known Bengaluru landmarks plus a graph-center
# fallback, which keeps the demo deterministic and fast (no external call
# means no network flakiness during judging).
PLACE_LOOKUP = {
    "koramangala": (12.9352, 77.6142),
    "manipal hospital": (12.9610, 77.6387),
    "btm layout": (12.9166, 77.6101),
    "hsr layout": (12.9121, 77.6386),
    "indiranagar": (12.9719, 77.6412),
    "mg road": (12.9759, 77.6063),
    "whitefield": (12.9698, 77.7500),
    "electronic city": (12.8456, 77.6603),
    "silk board": (12.9172, 77.6228),
}


def geocode(text: str) -> tuple[float, float]:
    key = text.strip().lower()
    if key in PLACE_LOOKUP:
        return PLACE_LOOKUP[key]
    # Fuzzy contains-match fallback so "Manipal Hospital, Bengaluru" still resolves.
    for name, coords in PLACE_LOOKUP.items():
        if name in key or key in name:
            return coords
    raise HTTPException(status_code=404, detail=f"Could not resolve location: '{text}'")


class RouteRequest(BaseModel):
    origin_lat: float | None = None
    origin_lng: float | None = None
    destination_lat: float | None = None
    destination_lng: float | None = None
    origin_text: str | None = None
    destination_text: str | None = None
    vehicle_id: str | None = None


class RouteResponse(BaseModel):
    path_coords: list[list[float]]
    distance_m: float
    eta_seconds: float
    impassable_edges_avoided: int
    compute_ms: float
    # The route a flood-naive system (e.g. standard Google Maps) would have
    # taken — computed on the same graph using plain distance/travel-time
    # weights, ignoring flood conditions entirely. Included so the frontend
    # can render both routes together: "here's what you would have driven
    # into, here's what we routed you around instead."
    original_path_coords: list[list[float]] | None = None
    original_distance_m: float | None = None
    original_eta_seconds: float | None = None
    crosses_flood_zone: bool = False
    # A small trace of which edges on the FINAL chosen route had a
    # flood-modified weight, for the algorithm diff panel — lets a
    # technical judge see the actual Dijkstra cost reasoning live,
    # rather than just the resulting path.
    edge_weight_changes: list[dict] = []


def _resolve_point(lat, lng, text) -> tuple[float, float]:
    if lat is not None and lng is not None:
        return lat, lng
    if text:
        return geocode(text)
    raise HTTPException(status_code=400, detail="Must provide either lat/lng or text for this point")


def _shortest_parallel_edge(G, u, v) -> dict:
    """
    A MultiDiGraph can have multiple parallel edges between the same two
    nodes (e.g. divided roads represented as separate carriageways). When
    we just need *an* edge's attributes for an ETA estimate (not routing
    cost, which already correctly picks the cheapest one via Dijkstra),
    the shortest one is the most representative choice.
    """
    edges = G.get_edge_data(u, v)
    best_key = min(edges, key=lambda k: edges[k].get("length", 1))
    return edges[best_key]


@router.post("/route", response_model=RouteResponse)
def compute_route(req: RouteRequest):
    t0 = time.perf_counter()

    origin_lat, origin_lng = _resolve_point(req.origin_lat, req.origin_lng, req.origin_text)
    dest_lat, dest_lng = _resolve_point(req.destination_lat, req.destination_lng, req.destination_text)

    G = get_graph()
    impassable = apply_flood_weights(G, state.active_zones_raw(), weight_attr="length")

    origin_node = nearest_node(G, origin_lat, origin_lng)
    dest_node = nearest_node(G, dest_lat, dest_lng)

    try:
        path_coords, distance_m, travel_seconds = compute_flood_aware_path(G, origin_node, dest_node)
    except NoPassableRouteError as e:
        raise HTTPException(
            status_code=409,
            detail=f"No passable route exists between these points given current flood conditions. {e}",
        )

    edge_weight_changes = trace_edge_weight_changes(G, origin_node, dest_node)

    # Compute the comparison route: what a flood-naive system would have
    # done, using plain distance as the weight (ignoring flood_weight
    # entirely). This is always computable as long as the graph is
    # connected at all — it ignores impassability by design, since the
    # whole point is to show "this is the route you would have driven
    # into water on."
    original_path_coords = None
    original_distance_m = None
    original_eta_seconds = None
    crosses_flood_zone = False
    try:
        naive_node_path = nx.shortest_path(G, origin_node, dest_node, weight="length")
        original_path_coords = [[G.nodes[n]["y"], G.nodes[n]["x"]] for n in naive_node_path]
        naive_cost = nx.path_weight(G, naive_node_path, weight="flood_weight")
        original_distance_m = nx.path_weight(G, naive_node_path, weight="length")
        original_eta_seconds = sum(
            _shortest_parallel_edge(G, u, v).get("travel_time", 30)
            for u, v in zip(naive_node_path[:-1], naive_node_path[1:])
        )
        # If the naive route's flood-weighted cost differs from its plain
        # distance, at least one edge on it intersects an active flood zone.
        crosses_flood_zone = naive_cost != original_distance_m
    except nx.NetworkXNoPath:
        pass  # graph genuinely disconnected; leave comparison fields as None

    compute_ms = (time.perf_counter() - t0) * 1000

    if req.vehicle_id:
        state.update_vehicle_route(req.vehicle_id, eta_seconds=travel_seconds, distance_m=distance_m)

    logger.info(
        "Route computed: %.0fm, %.0fs, %d impassable edges avoided, %.1fms",
        distance_m, travel_seconds, impassable, compute_ms,
    )

    return RouteResponse(
        path_coords=path_coords,
        distance_m=distance_m,
        eta_seconds=travel_seconds,
        impassable_edges_avoided=impassable,
        compute_ms=compute_ms,
        original_path_coords=original_path_coords,
        original_distance_m=original_distance_m,
        original_eta_seconds=original_eta_seconds,
        crosses_flood_zone=crosses_flood_zone,
        edge_weight_changes=edge_weight_changes,
    )
