import re
from typing import Dict, Any, List, Union
from copy import deepcopy


def apply_patch(doc: Dict[str, Any], patches: List[Dict]) -> Dict[str, Any]:
    """
    应用 Patch 操作到文档 (Generic JSON Patch like)

    Args:
        doc: 原始文档 (dict)
        patches: Patch 操作列表 (list of dicts with op, path, value)

    Returns:
        更新后的文档（深拷贝，不修改原文档）
    """
    result = deepcopy(doc)

    for patch in patches:
        # Support generic dict or Pydantic object
        if hasattr(patch, "op"):
            op = patch.op
            path = patch.path
            value = patch.value
        else:
            op = patch.get("op")
            path = patch.get("path", "")
            value = patch.get("value")

        if op == "update_field":
            _set_value_at_path(result, path, value)
        elif op == "update_item":
            _set_value_at_path(result, path, value)
        elif op == "add_item":
            arr = _get_value_at_path(result, path)
            if isinstance(arr, list):
                arr.append(value)
        elif op == "remove_item":
            # Basic implementation for remove
            # Expect path to point to the list, value to be the index or item ID?
            # For simplicity, let's assume we don't need complex remove yet
            pass

    return result


def _parse_path(path: str) -> List[str]:
    """解析路径为段列表，如 'assumptions[0].status' -> ['assumptions', '0', 'status']"""
    if not path:
        return []
    # 将 [n] 转换为 .n
    normalized = re.sub(r"\[(\d+)\]", r".\1", path)
    return [p for p in normalized.split(".") if p]


def _get_value_at_path(doc: Dict, path: str) -> Any:
    """获取路径对应的值"""
    segments = _parse_path(path)
    current = doc
    for seg in segments:
        if isinstance(current, list) and seg.isdigit():
            idx = int(seg)
            if 0 <= idx < len(current):
                current = current[idx]
            else:
                return None
        elif isinstance(current, dict):
            current = current.get(seg)
        else:
            return None

        if current is None:
            return None
    return current


def _set_value_at_path(doc: Dict, path: str, value: Any) -> None:
    """设置路径对应的值"""
    segments = _parse_path(path)
    if not segments:
        return

    current = doc
    # Iterate until the last segment
    for i, seg in enumerate(segments[:-1]):
        next_seg = segments[i + 1]

        # Determine if we need to enter a list or a dict
        if isinstance(current, list):
            if seg.isdigit():
                idx = int(seg)
                if 0 <= idx < len(current):
                    current = current[idx]
                else:
                    return  # Index out of bounds
            else:
                return  # Cannot access list with non-digit

        elif isinstance(current, dict):
            if seg not in current:
                # Need to create intermediate structure
                # If next segment is digit, create list? No, usually dict unless explicit.
                # Let's default to dict creation for simplicity
                current[seg] = {}
            current = current[seg]
        else:
            return  # Cannot traverse non-container

    # Handle the last segment
    last_seg = segments[-1]
    if isinstance(current, list):
        if last_seg.isdigit():
            idx = int(last_seg)
            if 0 <= idx < len(current):
                current[idx] = value
    elif isinstance(current, dict):
        current[last_seg] = value
