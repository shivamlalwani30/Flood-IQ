"""
core/routing_engine.py

The actual flood-aware pathfinding computation: given a graph (already
weighted by core/flood_weights.py) and an origin/destination node, returns
the path coordinates, distance, and flood-adjusted travel time.

This lives in core/ rather than routers/ specifically so it has no FastAPI
dependency — it's pure graph logic, used identically by:
  - routers/routing.py's POST /route REST endpoint
  - main.py's WebSocket handler (trigger_flood auto-reroute, request_route)

Originally this logic was duplicated in both places, and the WebSocket
copy had two real bugs: it ignored the flood-weight multiplier when
computing ETA (so the broadcast ETA didn't reflect flood slowdowns at
all), and it only caught nx.NetworkXNoPath, missing the case where a path
exists topologically but its total flood-weighted cost is infinite
(every connecting road crosses an impassable zone). Both bugs are fixed
here, once, for both callers.
"""

import networkx as nx


class NoPassableRouteError(Exception):
    """
    Raised when no finite-cost route exists between two nodes — either
    because the graph is topologically disconnected (nx.NetworkXNoPath),
    or because every connecting path crosses an impassable (>60cm) flood
    zone, giving every candidate path an infinite flood_weight cost.
    """
    pass


def compute_flood_aware_path(G, origin_node, dest_node):
    """
    Compute the flood-aware shortest path between two graph nodes.

    Returns (path_coords, distance_m, travel_seconds).
    Raises NoPassableRouteError if no usable route exists.
    """
    try:
        node_path = nx.shortest_path(G, origin_node, dest_node, weight="flood_weight")
    except nx.NetworkXNoPath:
        raise NoPassableRouteError("No topological path exists between these points.")

    path_cost = nx.path_weight(G, node_path, weight="flood_weight")
    if path_cost == float("inf"):
        # The graph IS connected — nx.shortest_path found *a* path — but
        # every edge on every possible route between these two points
        # crosses an impassable flood zone, so the cheapest available
        # path still costs infinity. NetworkXNoPath is not raised in this
        # case because the graph is genuinely connected; we have to check
        # the resulting path's cost explicitly to catch this scenario.
        raise NoPassableRouteError(
            "A path exists topologically, but every connecting road crosses an impassable flood zone."
        )

    path_coords = [[G.nodes[n]["y"], G.nodes[n]["x"]] for n in node_path]

    distance_m = 0.0
    travel_seconds = 0.0
    for u, v in zip(node_path[:-1], node_path[1:]):
        # A MultiDiGraph can have multiple parallel edges between the same
        # two nodes; pick the one Dijkstra actually used (lowest flood_weight).
        edge_data = min(G.get_edge_data(u, v).values(), key=lambda d: d.get("flood_weight", d.get("length", 1)))
        distance_m += edge_data.get("length", 0)

        base_length = edge_data.get("length", 1)
        base_travel_time = edge_data.get("travel_time", base_length / (30 * 1000 / 3600))
        travel_seconds += base_travel_time

        # Apply the same flood slowdown multiplier to travel time that was
        # used for routing cost, so a "slow" (2x/5x weight) edge correctly
        # adds real minutes to the ETA, not just to the abstract routing score.
        flood_weight = edge_data.get("flood_weight", base_length)
        if base_length > 0 and flood_weight != float("inf"):
            multiplier = flood_weight / base_length
            if multiplier > 1:
                travel_seconds += base_travel_time * (multiplier - 1)

    return path_coords, distance_m, travel_seconds


def trace_edge_weight_changes(G, origin_node, dest_node, max_entries: int = 8) -> list[dict]:
    """
    Re-walks the same flood-aware shortest path and returns a trace of
    which edges had a flood-modified weight, for display in a "what did
    the algorithm actually do" diff panel. Kept as a separate function
    (rather than folding into compute_flood_aware_path's return value) so
    the two existing callers of that function — main.py's vehicle
    auto-reroute and request_route handlers — are completely unaffected;
    only routers/routing.py's REST endpoint, which needs this extra detail
    for the diff panel, calls this.

    Capped at max_entries since a long route could have dozens of
    flood-affected edges; the panel only needs enough to make the point.
    """
    try:
        node_path = nx.shortest_path(G, origin_node, dest_node, weight="flood_weight")
    except nx.NetworkXNoPath:
        return []

    changes = []
    for u, v in zip(node_path[:-1], node_path[1:]):
        edge_data = min(G.get_edge_data(u, v).values(), key=lambda d: d.get("flood_weight", d.get("length", 1)))
        base_length = edge_data.get("length", 1)
        flood_weight = edge_data.get("flood_weight", base_length)
        if flood_weight != base_length and base_length > 0:
            multiplier = "∞ (impassable)" if flood_weight == float("inf") else f"{flood_weight / base_length:.1f}×"
            changes.append({
                "from_node": u,
                "to_node": v,
                "base_length_m": round(base_length, 1),
                "flood_weight": None if flood_weight == float("inf") else round(flood_weight, 1),
                "multiplier": multiplier,
            })
            if len(changes) >= max_entries:
                break

    return changes
