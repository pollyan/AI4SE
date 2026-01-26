import pytest
from backend.agents.lisa.artifact_patch import apply_patch, PatchOperation
from backend.agents.lisa.artifact_models import DesignNode, DesignDoc


class TestPatchOperations:

    def test_add_node(self):
        root = DesignNode(id="ROOT", label="Root", type="group", children=[])
        patch = PatchOperation(
            op="add",
            parent_id="ROOT",
            node=DesignNode(id="TP-001", label="新测试点", type="point", method="边界值"),
        )
        result = apply_patch(root, [patch])
        assert len(result.children) == 1
        assert result.children[0].id == "TP-001"
        assert result.children[0].is_new is True

    def test_modify_node(self):
        root = DesignNode(
            id="ROOT",
            label="Root",
            type="group",
            children=[DesignNode(id="TP-001", label="旧名称", type="point")],
        )
        patch = PatchOperation(
            op="modify",
            target_id="TP-001",
            field="label",
            value="新名称",
        )
        result = apply_patch(root, [patch])
        assert result.children[0].label == "新名称"

    def test_delete_node(self):
        root = DesignNode(
            id="ROOT",
            label="Root",
            type="group",
            children=[
                DesignNode(id="TP-001", label="保留", type="point"),
                DesignNode(id="TP-002", label="删除", type="point"),
            ],
        )
        patch = PatchOperation(op="delete", target_id="TP-002")
        result = apply_patch(root, [patch])
        assert len(result.children) == 1
        assert result.children[0].id == "TP-001"

    def test_multiple_patches(self):
        root = DesignNode(id="ROOT", label="Root", type="group", children=[])
        patches = [
            PatchOperation(
                op="add",
                parent_id="ROOT",
                node=DesignNode(id="TP-001", label="测试点1", type="point"),
            ),
            PatchOperation(
                op="add",
                parent_id="ROOT",
                node=DesignNode(id="TP-002", label="测试点2", type="point"),
            ),
        ]
        result = apply_patch(root, patches)
        assert len(result.children) == 2

    def test_nested_add(self):
        root = DesignNode(
            id="ROOT",
            label="Root",
            type="group",
            children=[
                DesignNode(id="GRP-001", label="分组", type="group", children=[])
            ],
        )
        patch = PatchOperation(
            op="add",
            parent_id="GRP-001",
            node=DesignNode(id="TP-001", label="嵌套测试点", type="point"),
        )
        result = apply_patch(root, [patch])
        assert result.children[0].children[0].id == "TP-001"

    def test_patch_does_not_mutate_original(self):
        root = DesignNode(id="ROOT", label="Root", type="group", children=[])
        patch = PatchOperation(
            op="add",
            parent_id="ROOT",
            node=DesignNode(id="TP-001", label="新测试点", type="point"),
        )
        apply_patch(root, [patch])
        assert root.children == []
