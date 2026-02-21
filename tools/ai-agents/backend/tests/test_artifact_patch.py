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

    def test_modified_item_gets_prev_value(self):
        """修改项应包含 _prev 字段记录旧值"""
        original = {"items": [{"id": "1", "val": "old", "other": "keep"}]}
        patch = {"items": [{"id": "1", "val": "new"}]}
        result = merge_artifacts(original, patch)

        item1 = result["items"][0]
        assert item1["val"] == "new"
        assert item1.get("_diff") == "modified"
        assert "_prev" in item1
        assert item1["_prev"]["val"] == "old"
        assert "other" not in item1["_prev"]  # 未修改字段不应出现在 _prev 中

    def test_nested_field_update_prev(self):
        """嵌套字段更新应记录旧值"""
        original = {"items": [{"id": "1", "meta": {"score": 10, "tag": "a"}}]}
        patch = {"items": [{"id": "1", "meta": {"score": 20}}]}
        result = merge_artifacts(original, patch)

        item1 = result["items"][0]
        assert item1["meta"]["score"] == 20
        assert "_prev" in item1
        assert item1["_prev"]["meta"]["score"] == 10

    def test_nested_feature_update_prev(self):
        """测试 Features 中的嵌套字段更新应记录旧值"""
        original = {
            "features": [
                {
                    "id": "f1",
                    "name": "Feature 1",
                    "desc": "Original Desc",
                    "priority": "P1"
                }
            ]
        }
        patch = {
            "features": [
                {
                    "id": "f1",
                    "name": "Feature 1 Updated",
                    "desc": "New Desc",
                    "priority": "P0"
                }
            ]
        }
        result = merge_artifacts(original, patch)

        feature = result["features"][0]
        assert feature["name"] == "Feature 1 Updated"
        assert feature["desc"] == "New Desc"
        assert feature["priority"] == "P0"
        
        assert "_prev" in feature
        assert feature["_prev"]["name"] == "Feature 1"
        assert feature["_prev"]["desc"] == "Original Desc"
        assert feature["_prev"]["priority"] == "P1"

    def test_nested_assumption_update_prev(self):
        """测试 Assumptions 中的嵌套字段更新应记录旧值"""
        original = {
            "assumptions": [
                {
                    "id": "a1",
                    "question": "Q1?",
                    "note": "Note 1",
                    "priority": "P2"
                }
            ]
        }
        patch = {
            "assumptions": [
                {
                    "id": "a1",
                    "question": "Q1 Updated?",
                    "note": "Note 1 Updated",
                    "priority": "P1"
                }
            ]
        }
        result = merge_artifacts(original, patch)

        assumption = result["assumptions"][0]
        assert assumption["question"] == "Q1 Updated?"
        assert assumption["note"] == "Note 1 Updated"
        assert assumption["priority"] == "P1"
        
        assert "_prev" in assumption
        assert assumption["_prev"]["question"] == "Q1?"
        assert assumption["_prev"]["note"] == "Note 1"
        assert assumption["_prev"]["priority"] == "P2"

    def test_transient_diff_cleanup(self):
        """测试瞬态 Diff 清理：Init -> Mod -> NoChange"""
        # Step 1: Init
        original = {"items": [{"id": "1", "val": "init"}]}
        
        # Step 2: Mod (Turn 1)
        patch1 = {"items": [{"id": "1", "val": "mod"}]}
        result1 = merge_artifacts(original, patch1)
        
        item1 = result1["items"][0]
        assert item1["val"] == "mod"
        
        # Step 3: NoChange (Turn 2)
        # Patch is empty or contains same value, so no change detected
        patch2 = {"items": [{"id": "1", "val": "mod"}]}
        # We pass result1 as the "original" for the next turn
        result2 = merge_artifacts(result1, patch2)
        
        item2 = result2["items"][0]
        assert item2["val"] == "mod"
        assert "_diff" not in item2
        assert "_prev" not in item2

    def test_transient_diff_cleanup_untouched_sections(self):
        """测试瞬态 Diff 清理：验证未被 Patch 触及的列表也能清除旧 Diff"""
        # Step 1: Init
        original = {
            "features": [{"id": "f1", "val": "init"}],
            "rules": [{"id": "r1", "val": "init"}]
        }
        
        # Step 2: Mod Feature (Turn 1)
        # 只有 features 被修改，rules 未动
        patch1 = {"features": [{"id": "f1", "val": "mod"}]}
        result1 = merge_artifacts(original, patch1)
        
        assert result1["features"][0].get("_diff") == "modified"
        
        # Manually verify rules didn't get tagged (as expected)
        assert "_diff" not in result1["rules"][0] if result1["rules"] else True
        
        # Step 3: Mod Rule (Turn 2)
        # 只有 rules 被修改，features 未动 (不在 patch 中)
        # 期望：features 中的 _diff 标记应该被清除！
        patch2 = {"rules": [{"id": "r1", "val": "mod"}]}
        result2 = merge_artifacts(result1, patch2)
        
        # Verify Rules are modified
        assert result2["rules"][0].get("_diff") == "modified"
        
        # CRITICAL CHECK: Features (untouched by patch2) should be CLEAN
        item_f1 = result2["features"][0]
        assert item_f1["val"] == "mod"
        assert "_diff" not in item_f1, "Diff tag persisted in untouched section!"
        assert "_prev" not in item_f1


