from typing import List, Optional, Literal, Any, cast
from pydantic import BaseModel, Field
from .artifact_models import DesignNode


class PatchOperation(BaseModel):
    op: Literal["add", "modify", "delete"] = Field(description="操作类型")
    parent_id: Optional[str] = Field(
        default=None, description="父节点 ID (add 时必填)"
    )
    target_id: Optional[str] = Field(
        default=None, description="目标节点 ID (modify/delete)"
    )
    node: Optional[DesignNode] = Field(
        default=None, description="新节点 (add 时必填)"
    )
    field: Optional[str] = Field(default=None, description="要修改的字段 (modify)")
    value: Optional[Any] = Field(default=None, description="新值 (modify)")


def _find_node(root: DesignNode, node_id: str) -> Optional[DesignNode]:
    if root.id == node_id:
        return root
    if root.children:
        for child in root.children:
            found = _find_node(child, node_id)
            if found:
                return found
    return None


def _delete_node_recursive(node: DesignNode, target_id: str) -> bool:
    if node.children:
        for i, child in enumerate(node.children):
            if child.id == target_id:
                node.children.pop(i)
                return True
            if _delete_node_recursive(child, target_id):
                return True
    return False


def apply_patch(root: DesignNode, patches: List[PatchOperation]) -> DesignNode:
    result = root.model_copy(deep=True)

    for patch in patches:
        if patch.op == "add" and patch.parent_id and patch.node:
            parent = _find_node(result, cast(str, patch.parent_id))
            if parent:
                if parent.children is None:
                    parent.children = []
                new_node = cast(DesignNode, patch.node).model_copy(deep=True)
                new_node.is_new = True
                parent.children.append(new_node)

        elif patch.op == "modify" and patch.target_id:
            target = _find_node(result, cast(str, patch.target_id))
            if target and patch.field:
                setattr(target, patch.field, patch.value)

        elif patch.op == "delete" and patch.target_id:
            _delete_node_recursive(result, cast(str, patch.target_id))

    return result
