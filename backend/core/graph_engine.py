"""
core/graph_engine.py

Loads the Bengaluru road network as a NetworkX MultiDiGraph using OSMnx,
caches it to a .pkl file so subsequent loads are fast (~1-2s instead of
30-60s), and exposes helpers used by the routing layer.

Usage:
    from core.graph_engine import get_graph
    G = get_graph()  # loads from cache if present, else downloads + caches
"""

import os
import pickle
import logging
from pathlib import Path

import networkx as nx

logger = logging.getLogger("floodiq.graph_engine")

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
GRAPH_CACHE_PATH = DATA_DIR / "bengaluru_graph.pkl"

# Bengaluru bounding box (north, south, east, west) — kept tight around
# the core city to keep graph size (and route compute time) manageable.
# Roughly covers Koramangala, Indiranagar, MG Road, HSR, BTM, Whitefield-ish.
BBOX = {
    "north": 13.05,
    "south": 12.85,
    "east": 77.75,
    "west": 77.50,
}

DEFAULT_PLACE = "Bengaluru, India"

# In-process cache so repeated calls within the same server process don't
# even touch disk.
_GRAPH_SINGLETON: nx.MultiDiGraph | None = None


def _download_graph() -> nx.MultiDiGraph:
    """Download the drivable road network for Bengaluru from OSM."""
    import osmnx as ox  # lazy import: only required for the real download path

    logger.info("Downloading OSM graph for Bengaluru (bbox=%s)...", BBOX)
    ox.settings.log_console = False
    ox.settings.use_cache = True

    G = ox.graph_from_bbox(
        # IMPORTANT — version-sensitive tuple order, verified against
        # OSMnx's own docs: the bbox= tuple order is (north, south, east,
        # west) for OSMnx 1.x (pinned in requirements.txt as 1.9.4) but
        # changes to (west, south, east, north) in OSMnx 2.x. If this
        # pin is ever bumped to 2.x, this tuple order MUST also change —
        # otherwise the call still succeeds (no error) but silently
        # downloads the wrong geographic area, since the four numbers
        # just get reinterpreted as a different bbox. Confirmed via
        # OSMnx's internals reference and real migration reports.
        bbox=(BBOX["north"], BBOX["south"], BBOX["east"], BBOX["west"]),
        network_type="drive",
        simplify=True,
    )

    # Add edge travel-time / speed metadata used by the flood-weighting layer.
    G = ox.add_edge_speeds(G)
    G = ox.add_edge_travel_times(G)

    logger.info(
        "Downloaded graph: %d nodes, %d edges", G.number_of_nodes(), G.number_of_edges()
    )
    return G


def _build_fallback_graph() -> nx.MultiDiGraph:
    """
    Build a small synthetic grid graph that mimics a road network.

    Used when there is no network access (e.g. sandboxed dev environment)
    so the rest of the stack (routing, flood weights, websockets, frontend)
    can still be built and tested end-to-end without a live OSM download.
    Real deployment will use _download_graph() via get_graph(force_download=True).
    """
    logger.warning(
        "No network access or OSM download failed — building synthetic "
        "fallback grid graph centered on Bengaluru coordinates."
    )
    G = nx.MultiDiGraph()
    G.graph["crs"] = "epsg:4326"

    rows, cols = 12, 12
    lat0, lon0 = 12.935, 77.61  # roughly Koramangala
    step = 0.004  # ~440m grid spacing

    node_id = 0
    grid_ids = {}
    for r in range(rows):
        for c in range(cols):
            lat = lat0 + r * step
            lon = lon0 + c * step
            G.add_node(node_id, y=lat, x=lon, street_count=4)
            grid_ids[(r, c)] = node_id
            node_id += 1

    def add_edge(n1, n2):
        y1, x1 = G.nodes[n1]["y"], G.nodes[n1]["x"]
        y2, x2 = G.nodes[n2]["y"], G.nodes[n2]["x"]
        length = (
            (y2 - y1) ** 2 + (x2 - x1) ** 2
        ) ** 0.5 * 111_000  # rough degrees->meters
        speed_kph = 30
        travel_time = length / (speed_kph * 1000 / 3600)
        attrs = {
            "length": length,
            "speed_kph": speed_kph,
            "travel_time": travel_time,
            "geometry": None,
            "name": f"Synthetic Road {n1}-{n2}",
        }
        G.add_edge(n1, n2, **attrs)
        G.add_edge(n2, n1, **attrs)

    for r in range(rows):
        for c in range(cols):
            here = grid_ids[(r, c)]
            if c + 1 < cols:
                add_edge(here, grid_ids[(r, c + 1)])
            if r + 1 < rows:
                add_edge(here, grid_ids[(r + 1, c)])

    logger.info(
        "Fallback graph built: %d nodes, %d edges", G.number_of_nodes(), G.number_of_edges()
    )
    return G


def _save_to_cache(G: nx.MultiDiGraph, path: Path = GRAPH_CACHE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump(G, f, protocol=pickle.HIGHEST_PROTOCOL)
    logger.info("Graph cached to %s", path)


def _load_from_cache(path: Path = GRAPH_CACHE_PATH) -> nx.MultiDiGraph | None:
    if not path.exists():
        return None
    try:
        with open(path, "rb") as f:
            G = pickle.load(f)
        logger.info(
            "Loaded cached graph from %s: %d nodes, %d edges",
            path,
            G.number_of_nodes(),
            G.number_of_edges(),
        )
        return G
    except Exception as e:
        logger.warning("Failed to load cached graph (%s); will rebuild.", e)
        return None


def get_graph(force_download: bool = False, force_rebuild: bool = False) -> nx.MultiDiGraph:
    """
    Return the Bengaluru road graph, loading from in-memory singleton,
    then disk cache, then OSM download (or synthetic fallback) in that
    order of preference.
    """
    global _GRAPH_SINGLETON

    if _GRAPH_SINGLETON is not None and not force_rebuild and not force_download:
        return _GRAPH_SINGLETON

    if not force_rebuild and not force_download:
        cached = _load_from_cache()
        if cached is not None:
            _GRAPH_SINGLETON = cached
            return _GRAPH_SINGLETON

    try:
        G = _download_graph()
    except Exception as e:
        logger.warning("OSM download failed (%s). Using synthetic fallback graph.", e)
        G = _build_fallback_graph()

    _save_to_cache(G)
    _GRAPH_SINGLETON = G
    return _GRAPH_SINGLETON


def graph_stats(G: nx.MultiDiGraph) -> dict:
    return {
        "nodes": G.number_of_nodes(),
        "edges": G.number_of_edges(),
        "is_synthetic": G.graph.get("crs") == "epsg:4326" and "name" in next(iter(G.edges(data=True)))[2] and "Synthetic" in next(iter(G.edges(data=True)))[2].get("name", ""),
    }


def nearest_node(G: nx.MultiDiGraph, lat: float, lon: float) -> int:
    """Find nearest graph node to a given lat/lon using OSMnx if available,
    falling back to a brute-force scan for the synthetic graph."""
    try:
        import osmnx as ox
        return ox.nearest_nodes(G, X=lon, Y=lat)
    except Exception:
        best_node, best_dist = None, float("inf")
        for n, data in G.nodes(data=True):
            d = (data["y"] - lat) ** 2 + (data["x"] - lon) ** 2
            if d < best_dist:
                best_dist, best_node = d, n
        return best_node


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    graph = get_graph()
    print(graph_stats(graph))
