from unittest.mock import patch
import sys

print("Before import:", sys.modules.get("backend.agents.lisa.nodes.artifact_node"))
import backend.agents.lisa.nodes.artifact_node
print("Type of artifact_node:", type(backend.agents.lisa.nodes.artifact_node))

try:
    with patch("backend.agents.lisa.nodes.artifact_node.get_stream_writer") as mock_writer:
        print("Patch success!")
except Exception as e:
    print("Patch error:", type(e), e)
