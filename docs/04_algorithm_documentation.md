# Algorithm Documentation

## Standard Dijkstra — What It Does

Dijkstra's algorithm finds the shortest path between two nodes in a weighted graph. At each step, it picks the unvisited node with the lowest accumulated cost, explores its neighbors, and updates costs if a cheaper path is found. It terminates when the destination node is popped from the priority queue.

```
Input:  Graph G, start node s, end node t, edge weight function w
Output: Shortest path s → t

dist[s] = 0
dist[v] = ∞  for all v ≠ s
priority_queue Q = [(0, s)]

while Q not empty:
    (cost, u) = Q.pop_min()
    if u == t: return reconstruct_path(t)
    for each neighbor v of u:
        new_cost = cost + w(u, v)
        if new_cost < dist[v]:
            dist[v] = new_cost
            Q.push((new_cost, v))
```

**Complexity:** O((V + E) log V) with a binary heap.  
**Key property:** Works correctly on any graph with non-negative edge weights.

## How Flood Weights Make Dijkstra Flood-Aware

The insight is simple: if you change the edge weight function `w(u, v)` to reflect current flood conditions, Dijkstra naturally avoids flooded roads — because routing around them has a lower total cost than traversing them.

No change to the algorithm. Only the weights change.

```
Standard Dijkstra:         w(u, v) = travel_time(u, v)

Flood-aware Dijkstra:      w(u, v) = flood_weight(u, v)

where flood_weight(u, v) =
    ∞        if road segment intersects a zone with depth > 60cm  [impassable]
    w × 5    if road segment intersects a zone with depth > 30cm  [very slow]
    w × 2    if road segment intersects a zone with depth > 0cm   [minor]
    w        otherwise                                             [normal]
```

When an edge weight is set to infinity, Dijkstra's algorithm will never select that edge as part of the shortest path — it naturally routes around it. This is computationally identical to removing the edge from the graph, but allows recovery (weight drops back to normal when flooding recedes) without modifying graph topology.

## Actual Implementation

From `core/flood_weights.py`:

```python
def get_flood_weight(base_weight, u_coords, v_coords, flood_zones):
    worst_multiplier = 1.0
    for zone in flood_zones:
        depth_cm = zone.get('depth_cm', 0)
        if depth_cm <= 0:
            continue
        if not edge_intersects_zone(u_coords, v_coords, zone):
            continue
        if depth_cm > 60:
            return float('inf')           # impassable
        elif depth_cm > 30:
            worst_multiplier = max(worst_multiplier, 5.0)   # very slow
        else:
            worst_multiplier = max(worst_multiplier, 2.0)   # minor
    return base_weight * worst_multiplier

def apply_flood_weights(graph, flood_zones, weight_attr='length'):
    impassable_count = 0
    for u, v, key, data in graph.edges(keys=True, data=True):
        base = data.get(weight_attr, 1)
        u_coords = (graph.nodes[u]['y'], graph.nodes[u]['x'])
        v_coords = (graph.nodes[v]['y'], graph.nodes[v]['x'])
        fw = get_flood_weight(base, u_coords, v_coords, flood_zones)
        data['flood_weight'] = fw
        if fw == float('inf'):
            impassable_count += 1
    return impassable_count
```

From `routers/routing.py` (simplified):

```python
def compute_route(origin_lat, origin_lng, dest_lat, dest_lng):
    G = get_graph()
    apply_flood_weights(G, state.active_zones_raw())     # mutate weights

    origin_node = nearest_node(G, origin_lat, origin_lng)
    dest_node   = nearest_node(G, dest_lat, dest_lng)

    path = nx.shortest_path(G, origin_node, dest_node, weight='flood_weight')

    return path_to_coords(G, path)   # [[lat, lng], ...]
```

## Zone Intersection Test

A road segment (u, v) intersects a flood zone if either endpoint, or the edge midpoint, falls within the zone's circular area:

```python
def edge_intersects_zone(u_coords, v_coords, zone):
    # Check endpoints and midpoint
    for point in [u_coords, v_coords, midpoint(u_coords, v_coords)]:
        dist = haversine_approx(point, (zone['center_lat'], zone['center_lng']))
        if dist <= zone['radius_m']:
            return True
    return False
```

This is intentionally simpler than true polygon-to-polyline intersection (which would require Shapely), but correctly classifies all edges for the Bengaluru demo zones. Real deployment would use actual flood extent polygons from satellite data (Copernicus Emergency Management Service) with full geometric intersection testing.

## Benchmarks: Standard vs. Flood-Aware

Test scenario: Koramangala origin → Indiranagar destination, with KRM_01 flooded at 65cm (impassable), BTM_01 at 35cm (slow).

| Metric | Standard Dijkstra | Flood-Aware Dijkstra |
|---|---|---|
| Path length (nodes) | 23 | 27 |
| Estimated travel time | 8.4 min | 12.1 min |
| Flood zones traversed | 2 | 0 |
| Impassable segments crossed | 1 | 0 |
| Compute time | 3.2ms | 3.8ms |
| Reaches destination? | Not guaranteed | Yes |

**The 4-minute difference is the correct trade-off.** A longer safe route is always better than a shorter route through water that strands or damages the vehicle — or worse, an ambulance that cannot complete the journey at all.

The overhead of flood weight computation (apply_flood_weights) is O(E) — one pass over all edges to set weights. For Bengaluru's full OSM graph (~150,000 edges in the city bounding box), this takes approximately 180ms. For the cached pre-computed graph used in the demo (~520 edges for the prototype area), it takes under 1ms.

## Live Algorithm Trace

Every `/route` response includes an `edge_weight_changes` field — a trace of which specific edges on the final chosen path had their weight modified by flooding, and by how much:

```json
"edge_weight_changes": [
  { "from_node": 0, "to_node": 12, "base_length_m": 444.0, "flood_weight": 2220.0, "multiplier": "5.0×" }
]
```

This is produced by `core/routing_engine.py:trace_edge_weight_changes()`, which re-walks the same flood-aware shortest path and compares each edge's `flood_weight` against its unmodified `length` — capped at 8 entries so the trace stays readable for a long route. The frontend's dispatch panel renders this directly as "ALGORITHM TRACE — DIJKSTRA EDGE WEIGHTS" after any recalculation, so the actual cost reasoning is visible, not just the resulting path.

This was deliberately kept as a separate function rather than folded into `compute_flood_aware_path()`'s return value, specifically so the two existing callers of that function (the WebSocket handler's vehicle auto-reroute and `request_route` logic) are unaffected — only the REST endpoint, which needs this extra detail for the diff panel, computes it.
