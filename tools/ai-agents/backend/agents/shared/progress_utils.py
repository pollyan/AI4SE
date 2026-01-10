"""
共享进度工具模块

提供 XML 解析、响应清理和 Plan 状态更新等通用功能。
Lisa 和 Alex 智能体共用此模块。
"""

import re
import logging
from typing import Optional, Tuple, List, Dict

logger = logging.getLogger(__name__)


# XML 标签正则表达式
UPDATE_STATUS_PATTERN = re.compile(
    r'<update_status\s+stage=["\']([^"\']+)["\']\s*>\s*(active|completed)\s*</update_status>',
    re.IGNORECASE
)

# Plan 标签正则表达式 - 用于提取 LLM 动态生成的阶段计划
PLAN_PATTERN = re.compile(
    r'<plan>\s*(\[.*?\])\s*</plan>',
    re.IGNORECASE | re.DOTALL
)

# 所有需要清理的 XML 标签模式
CLEANUP_PATTERNS = [
    re.compile(r'<update_status[^>]*>.*?</update_status>', re.IGNORECASE | re.DOTALL),
    re.compile(r'<plan>.*?</plan>', re.IGNORECASE | re.DOTALL),
]


def parse_progress_update(text: str) -> Optional[Tuple[str, str]]:
    """
    解析响应文本中的进度更新指令
    
    Args:
        text: LLM 响应文本
        
    Returns:
        (stage_id, new_status) 元组，若无指令则返回 None
        
    Example:
        >>> parse_progress_update("好的<update_status stage='strategy'>active</update_status>")
        ('strategy', 'active')
    """
    match = UPDATE_STATUS_PATTERN.search(text)
    if match:
        stage_id = match.group(1)
        new_status = match.group(2).lower()
        logger.info(f"解析到进度更新指令: stage={stage_id}, status={new_status}")
        return (stage_id, new_status)
    return None


def parse_plan(text: str) -> Optional[List[Dict]]:
    """
    解析响应文本中的动态 Plan 定义
    
    LLM 应输出格式如:
    <plan>[{"id": "clarify", "name": "需求澄清"}, {"id": "analysis", "name": "评审分析"}]</plan>
    
    Args:
        text: LLM 响应文本
        
    Returns:
        解析后的 Plan 列表，每个阶段包含 id, name, status (默认 pending)
        若无 plan 标签或解析失败则返回 None
        
    Example:
        >>> parse_plan('<plan>[{"id": "clarify", "name": "需求澄清"}]</plan>')
        [{"id": "clarify", "name": "需求澄清", "status": "active"}]
    """
    import json
    
    # 1. 尝试标准 XML 提取
    match = PLAN_PATTERN.search(text)
    json_str = ""
    
    if match:
        json_str = match.group(1)
    else:
        # 2. Fallback: 尝试直接提取 <plan> 后的 JSON 列表
        # 即使缺少 </plan> 也能工作
        start_tag = "<plan>"
        start_idx = text.lower().find(start_tag)
        if start_idx != -1:
            content_start = start_idx + len(start_tag)
            # 从 content_start 开始找第一个 [
            list_start = text.find("[", content_start)
            if list_start != -1:
                # 尝试找到匹配的 ]
                # 简单处理：找最后一个 ]，或者尝试解析
                # 这里我们假设 plan 是单行的或者紧凑的，尝试提取一段可能的 JSON
                # 更稳健的方法是逐字符匹配
                balance = 0
                list_end = -1
                for i in range(list_start, len(text)):
                    if text[i] == "[":
                        balance += 1
                    elif text[i] == "]":
                        balance -= 1
                        if balance == 0:
                            list_end = i + 1
                            break
                
                if list_end != -1:
                    json_str = text[list_start:list_end]
                    logger.warning("使用 Fallback 逻辑提取 Plan JSON")

    if not json_str:
        return None
    
    try:
        plan_data = json.loads(json_str)
        
        if not isinstance(plan_data, list):
            logger.warning(f"Plan 格式错误: 期望列表，得到 {type(plan_data)}")
            return None
        
        # 确保每个阶段有必要字段，第一个阶段设为 active
        normalized_plan = []
        for i, stage in enumerate(plan_data):
            normalized_stage = {
                "id": stage.get("id", f"stage_{i}"),
                "name": stage.get("name", f"阶段 {i+1}"),
                "status": "active" if i == 0 else "pending"
            }
            normalized_plan.append(normalized_stage)
        
        logger.info(f"解析到动态 Plan: {len(normalized_plan)} 个阶段")
        return normalized_plan
        
    except json.JSONDecodeError as e:
        logger.error(f"Plan JSON 解析失败: {e}")
        return None


def clean_response_text(text: str) -> str:
    """
    移除响应文本中的所有进度相关 XML 标签
    
    Args:
        text: 原始响应文本
        
    Returns:
        清理后的文本
    """
    result = text
    for pattern in CLEANUP_PATTERNS:
        result = pattern.sub('', result)
    
    # 清理可能残留的多余空行
    result = re.sub(r'\n{3,}', '\n\n', result)
    
    return result.strip()


def clean_response_streaming(text: str) -> str:
    """
    流式响应文本清理 - 处理部分传输的标签
    
    1. 移除完整的 XML 标签
    2. 如果文本末尾包含部分未闭合的标签前缀（<plan, <update_status），则截断
    
    Args:
        text: 当前累积的完整响应文本
        
    Returns:
        清理并安全截断后的文本（可安全展示给用户）
    """
    # 1. 先用常规逻辑移除完整的标签
    cleaned = text
    for pattern in CLEANUP_PATTERNS:
        cleaned = pattern.sub('', cleaned)
    
    # 2. 检查是否有未闭合的特定标签 (Plan B)
    # 如果经过正则清理后，开头仍然是敏感标签，说明该标签未闭合
    lower_cleaned = cleaned.lower()
    sensitive_prefixes = ["<plan", "<update_status"]
    
    for prefix in sensitive_prefixes:
        if lower_cleaned.startswith(prefix):
            # 标签位于开头且未被移除，说明未闭合 -> 隐藏全部
            return ""
            
    # 3. 检查末尾是否有未闭合的标签片段 (Plan C)
    # 查找最后一个 '<' 的位置
    last_open_bracket = cleaned.rfind('<')
    if last_open_bracket != -1:
        # 获取从 '<' 开始的后缀
        suffix = cleaned[last_open_bracket:]
        suffix_lower = suffix.lower()
        
        for prefix in sensitive_prefixes:
            # Case A: suffix 是 prefix 的一部分 (例如 "<p", "<pla")
            # 意味着标签正在传输中
            if prefix.startswith(suffix_lower):
                return cleaned[:last_open_bracket]
            
            # Case B: suffix 已经包含了 prefix (例如 "<plan>", "<update_status stage=...")
            # 意味着标签已经开始，但可能因为未闭合而没有被步骤1的完整正则移除
            if suffix_lower.startswith(prefix):
                 return cleaned[:last_open_bracket]
            
    return cleaned


def update_plan_status(
    plan: List[Dict],
    target_stage_id: str,
    new_status: str = "active"
) -> List[Dict]:
    """
    更新 Plan 中指定阶段的状态
    
    采用线性阶段推进逻辑:
    - 目标阶段之前的所有阶段标记为 completed
    - 目标阶段标记为 new_status (通常是 active)
    - 目标阶段之后的所有阶段保持 pending
    
    Args:
        plan: 当前的计划列表
        target_stage_id: 目标阶段 ID
        new_status: 目标阶段的新状态 (默认 "active")
        
    Returns:
        更新后的计划列表 (新对象)
    """
    if not plan:
        return plan
    
    # 找到目标阶段的索引
    target_index = -1
    for i, stage in enumerate(plan):
        if stage.get("id") == target_stage_id:
            target_index = i
            break
    
    if target_index == -1:
        logger.warning(f"未找到阶段: {target_stage_id}")
        return plan
    
    # 创建新的 plan 列表
    new_plan = []
    for i, stage in enumerate(plan):
        new_stage = dict(stage)  # 浅拷贝
        if i < target_index:
            new_stage["status"] = "completed"
        elif i == target_index:
            new_stage["status"] = new_status
        else:
            new_stage["status"] = "pending"
        new_plan.append(new_stage)
    
    logger.info(f"Plan 状态已更新: 目标阶段 {target_stage_id} -> {new_status}")
    return new_plan


def get_current_stage_id(plan: List[Dict]) -> Optional[str]:
    """
    从 Plan 中获取当前活跃阶段的 ID
    
    Args:
        plan: 计划列表
        
    Returns:
        活跃阶段的 ID，若无则返回 None
    """
    for stage in plan:
        if stage.get("status") == "active":
            return stage.get("id")
    return None
