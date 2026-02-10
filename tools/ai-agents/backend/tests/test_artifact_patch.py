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
        assert original["nested"]["a"] == 1
        assert result["nested"]["a"] == 2


class TestMergeDiffTagging:
    """测试 Merge 时的 Diff 标记逻辑"""

    def test_new_item_gets_added_tag(self):
        """新增项应标记 _diff='added'"""
        original = {"items": [{"id": "1", "val": "old"}]}
        patch = {"items": [{"id": "2", "val": "new"}]}
        result = merge_artifacts(original, patch)
        
        item2 = next(i for i in result["items"] if i["id"] == "2")
        assert item2.get("_diff") == "added"
        
        item1 = next(i for i in result["items"] if i["id"] == "1")
        assert "_diff" not in item1

    def test_modified_item_gets_modified_tag(self):
        """修改项应标记 _diff='modified'"""
        original = {"items": [{"id": "1", "val": "old"}]}
        patch = {"items": [{"id": "1", "val": "new"}]}
        result = merge_artifacts(original, patch)
        
        item1 = result["items"][0]
        assert item1["val"] == "new"
        assert item1.get("_diff") == "modified"

    def test_unchanged_item_has_no_tag(self):
        """未修改项不应有标记"""
        original = {"items": [{"id": "1", "val": "same"}]}
        patch = {"items": [{"id": "1", "val": "same"}]}
        result = merge_artifacts(original, patch)
        
        item1 = result["items"][0]
        assert "_diff" not in item1

    def test_old_diff_tags_are_cleared(self):
        """旧的 _diff 标记在合并前应被清除"""
        # 原始数据中残留了上一轮的 tagged 数据
        original = {
            "items": [
                {"id": "1", "val": "old", "_diff": "added"},
                {"id": "2", "val": "static", "_diff": "modified"}
            ]
        }
        # patch 修改了 id=1，未触碰 id=2
        patch = {"items": [{"id": "1", "val": "new"}]}
        
        result = merge_artifacts(original, patch)
        
        # id=1 被修改 -> modified
        item1 = next(i for i in result["items"] if i["id"] == "1")
        assert item1.get("_diff") == "modified"
        
        # id=2 未被修改 -> 标记应被清除
        item2 = next(i for i in result["items"] if i["id"] == "2")
        assert "_diff" not in item2

