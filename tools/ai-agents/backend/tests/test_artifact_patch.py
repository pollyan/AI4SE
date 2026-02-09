import pytest
from backend.agents.lisa.artifact_patch import merge_artifacts


class TestPatchOperations:
    def test_merge_dicts_recursively(self):
        original = {"a": 1, "b": {"c": 2}}
        patch = {"b": {"d": 3}}
        result = merge_artifacts(original, patch)
        assert result == {"a": 1, "b": {"c": 2, "d": 3}}

    def test_merge_list_by_id_update(self):
        original = {"items": [{"id": "1", "val": "old"}, {"id": "2", "val": "keep"}]}
        patch = {"items": [{"id": "1", "val": "new"}]}
        result = merge_artifacts(original, patch)
        assert result["items"][0]["val"] == "new"
        assert result["items"][1]["val"] == "keep"
        assert len(result["items"]) == 2

    def test_merge_list_by_id_append(self):
        original = {"items": [{"id": "1", "val": "a"}]}
        patch = {"items": [{"id": "2", "val": "b"}]}
        result = merge_artifacts(original, patch)
        assert len(result["items"]) == 2
        assert result["items"][1]["id"] == "2"

    def test_merge_list_without_id_overwrite(self):
        original = {"tags": ["a", "b"]}
        patch = {"tags": ["c"]}
        result = merge_artifacts(original, patch)
        assert result["tags"] == ["c"]

    def test_no_mutate_original(self):
        original = {"nested": {"a": 1}}
        patch = {"nested": {"a": 2}}
        result = merge_artifacts(original, patch)
        assert original["nested"]["a"] == 1
        assert result["nested"]["a"] == 2
