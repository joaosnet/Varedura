import json
from pathlib import Path


PRIVATE_SOURCE_FILES = {
    ".camera-locations.private.json",
    "camera_bridge_state.json",
    "credenciais.json",
    "ips_conhecidos.json",
    "regioes.json",
    "roteador_creds.txt",
}


def test_graphify_artifact_excludes_private_runtime_sources():
    graph_path = Path(__file__).parents[1] / "graphify-out" / "graph.json"
    if not graph_path.is_file():
        return

    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    source_files = {
        Path(str(node["source_file"])).name
        for node in graph.get("nodes", [])
        if isinstance(node, dict) and node.get("source_file")
    }
    assert source_files.isdisjoint(PRIVATE_SOURCE_FILES)
