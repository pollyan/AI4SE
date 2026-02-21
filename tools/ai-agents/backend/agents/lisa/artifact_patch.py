import re
from typing import Dict, Any, List
from copy import deepcopy
import logging

logger = logging.getLogger(__name__)

from typing import TypedDict, Optional

class PatchOperation(TypedDict):
    op: str
    path: str
    value: Optional[Any]
    from_path: Optional[str]  # For move/copy operations if needed


def merge_artifacts(original: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge a patch into an original artifact using ID-based matching for lists.

    Args:
        original: The original artifact dictionary.
        patch: The patch dictionary containing updates.

    Returns:
        A new dictionary with the merged result.
    """
    if not isinstance(patch, dict):
        logger.warning(f"Invalid patch format: expected dict, got {type(patch)}")
        return deepcopy(original)

    result = deepcopy(original)
    
    # [Fix] Globally clear transient _diff/_prev tags from the base copy
    # This ensures that any section NOT touched by the patch will be clean
    _remove_transient_tags(result)

    for key, value in patch.items():
        if key not in result:
            result[key] = value
            continue

        original_value = result[key]

        if isinstance(original_value, dict) and isinstance(value, dict):
            result[key] = merge_artifacts(original_value, value)

        elif isinstance(original_value, list) and isinstance(value, list):
            result[key] = _merge_lists(original_value, value)

        else:
            result[key] = value

    return result


def _has_content_changed(old: dict, new: dict) -> bool:
    """忽略 _diff 字段本身，比较实际内容是否变化"""
    old_clean = {k: v for k, v in old.items() if k not in ("_diff", "_prev")}
    new_clean = {k: v for k, v in new.items() if k not in ("_diff", "_prev")}
    return old_clean != new_clean


def _merge_lists(original_list: List, patch_list: List) -> List:
    if not patch_list:
        return original_list

    is_identifiable = (
        len(original_list) > 0
        and isinstance(original_list[0], dict)
        and "id" in original_list[0]
    ) or (
        len(patch_list) > 0
        and isinstance(patch_list[0], dict)
        and "id" in patch_list[0]
    )

    if not is_identifiable:
        return patch_list

    merged = list(original_list)
    
    # [Mod] Clear old _diff tags before processing new patch
    # This ensures that "added"/"modified" states are transient for one turn
    for item in merged:
        if isinstance(item, dict):
            item.pop("_diff", None)
            item.pop("_prev", None)

    id_map = {item["id"]: i for i, item in enumerate(merged)}

    for item in patch_list:
        if not isinstance(item, dict) or "id" not in item:
            continue

        item_id = item["id"]
        if item_id in id_map:
            idx = id_map[item_id]
            old_item = merged[idx]
            new_item = merge_artifacts(old_item, item)
            
            # [Mod] Check for modification
            if _has_content_changed(old_item, new_item):
                new_item["_diff"] = "modified"
                
                # Calculate _prev
                # Since new_item is fully merged, we can compare its fields with old_item partial match
                # WE need to compare keys present in new_item
                # Ignore metadata fields
                prev = {}
                old_clean = {k: v for k, v in old_item.items() if k not in ("_diff", "_prev", "id")}
                
                for key, new_val in new_item.items():
                    if key in ("_diff", "_prev", "id"):
                        continue
                        
                    # Only if key existed in old item
                    if key in old_clean:
                        old_val = old_clean[key]
                        if old_val != new_val:
                             prev[key] = old_val
                
                if prev:
                    new_item["_prev"] = prev
            
            merged[idx] = new_item
        else:
            # [Mod] Mark as added
            # Create a copy to avoid mutating the patch_list item accidentally 
            # (though in this context it might be fine, safety first)
            new_item = item.copy()
            new_item["_diff"] = "added"
            merged.append(new_item)
            id_map[item_id] = len(merged) - 1

    return merged


def apply_patch(doc: Dict[str, Any], patches: List[Any]) -> Dict[str, Any]:
    """
    应用 Patch 操作到文档 (Generic JSON Patch like)

    Args:
        doc: 原始文档 (dict)
        patches: Patch 操作列表 (list of dicts or objects with op, path, value)

    Returns:
        更新后的文档（深拷贝，不修改原文档）
    """
    result = deepcopy(doc)

    for patch in patches:
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
            pass

    return result
    return result


def _remove_transient_tags(item: Any) -> None:
    """Recursively remove _diff and _prev tags from a dictionary or list"""
    if isinstance(item, dict):
        item.pop("_diff", None)
        item.pop("_prev", None)
        for value in item.values():
            _remove_transient_tags(value)
    elif isinstance(item, list):
        for element in item:
            _remove_transient_tags(element)

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
