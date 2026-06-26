import tempfile
import unittest
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from codelevelup.code_graph import build_code_graph, query_code_graph


class CodeGraphTests(unittest.TestCase):
    def test_builds_local_code_graph_inside_target_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "src"
            src.mkdir()
            (src / "service.py").write_text(
                "import json\n\nclass Service:\n    def level_up(self):\n        return json.dumps({})\n",
                encoding="utf-8",
            )

            graph = build_code_graph(root)

            self.assertEqual(graph["state_dir"], ".codelevelup")
            self.assertTrue((root / ".codelevelup" / "graph" / "graph.json").is_file())
            node_names = {node.get("name") for node in graph["nodes"]}
            self.assertIn("Service", node_names)
            self.assertIn("level_up", node_names)
            edge_types = {edge["type"] for edge in graph["edges"]}
            self.assertIn("defines", edge_types)
            self.assertIn("imports", edge_types)

    def test_queries_graph_for_symbols_and_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "src"
            src.mkdir()
            (src / "upgrade.py").write_text("def patch_vulnerability():\n    return True\n", encoding="utf-8")
            build_code_graph(root)

            result = query_code_graph(root, "patch_vulnerability")

        self.assertEqual(result["query"], "patch_vulnerability")
        self.assertEqual(result["matches"][0]["path"], "src/upgrade.py")
        self.assertEqual(result["matches"][0]["name"], "patch_vulnerability")

    def test_extracts_call_edges_between_functions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "src"
            src.mkdir()
            (src / "app.py").write_text(
                "def helper():\n    return 1\n\ndef caller():\n    return helper()\n",
                encoding="utf-8",
            )
            graph = build_code_graph(root)

        call_edges = [e for e in graph["edges"] if e["type"] == "calls"]
        self.assertEqual(len(call_edges), 1)
        self.assertIn("caller", call_edges[0]["source"])
        self.assertIn("helper", call_edges[0]["target"])

    def test_extracts_method_nodes_and_call_edges(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "src"
            src.mkdir()
            (src / "service.py").write_text(
                "class Service:\n    def level_up(self):\n        return 1\n",
                encoding="utf-8",
            )
            graph = build_code_graph(root)

        method_nodes = [n for n in graph["nodes"] if n["type"] == "Method"]
        self.assertEqual(len(method_nodes), 1)
        self.assertEqual(method_nodes[0]["name"], "level_up")

        has_method_edges = [e for e in graph["edges"] if e["type"] == "has_method"]
        self.assertEqual(len(has_method_edges), 1)


if __name__ == "__main__":
    unittest.main()
