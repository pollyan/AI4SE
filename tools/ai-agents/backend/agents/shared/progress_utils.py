"""
共享进度工具模块

提供 XML/JSON 解析、响应清理等通用功能。
Lisa 和 Alex 智能体共用此模块。

采用"全量状态快照"模式：LLM 每次回复都输出完整的 Plan JSON（含 status）。

### 输出格式演进
- **Legacy**: XML 标签 (<plan>, <artifact>, <artifact_template>)
- **New**: 末尾 JSON 代码块 (```json ... ```)

本模块同时支持两种格式，优先尝试 JSON 解析。
"""

import re
import json
import logging
from typing import Optional, List, Dict, Tuple

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# JSON 代码块解析 (新格式)
# ═══════════════════════════════════════════════════════════════════════════════

JSON_BLOCK_PATTERN = re.compile(
    r'```json\s*([\s\S]*?)\s*```',
    re.IGNORECASE
)


def parse_structured_json(text: str) -> Tuple[Optional[Dict], Optional[str]]:
    """
    从响应文本末尾提取结构化 JSON 块
    
    期望格式:
    ```json
    {
      "plan": [...],
      "current_stage_id": "...",
      "artifacts": [...],
      "message": "..."
    }
    ```
    
    Args:
        text: LLM 响应文本
        
    Returns:
        (parsed_data, message) 元组:
        - parsed_data: 解析后的字典，包含 plan, current_stage_id, artifacts
        - message: 用户可见的消息内容
        若解析失败则返回 (None, None)
    """
    matches = list(JSON_BLOCK_PATTERN.finditer(text))
    if not matches:
        return None, None
    
    last_match = matches[-1]
    json_str = last_match.group(1).strip()
    
    try:
        data = json.loads(json_str)
        
        if not isinstance(data, dict):
            logger.warning(f"JSON 格式错误: 期望字典，得到 {type(data)}")
            return None, None
        
        required_fields = ["plan", "current_stage_id", "message"]
        for field in required_fields:
            if field not in data:
                logger.warning(f"JSON 缺少必要字段: {field}")
                return None, None
        
        message = data.get("message", "")
        
        logger.info(f"解析到结构化 JSON: plan={len(data.get('plan', []))} 阶段, "
                   f"artifacts={len(data.get('artifacts', []))} 个")
        
        return data, message
        
    except json.JSONDecodeError as e:
        logger.warning(f"结构化 JSON 解析失败: {e}")
        return None, None


def extract_plan_from_structured(data: Dict) -> Optional[List[Dict]]:
    """
    从结构化 JSON 中提取 Plan 列表
    
    Args:
        data: parse_structured_json 返回的字典
        
    Returns:
        Plan 列表，每个阶段包含 id, name, status
    """
    plan = data.get("plan", [])
    if not isinstance(plan, list):
        return None
    
    normalized_plan = []
    for i, stage in enumerate(plan):
        normalized_stage = {
            "id": stage.get("id", f"stage_{i}"),
            "name": stage.get("name", f"阶段 {i+1}"),
            "status": stage.get("status", "pending"),
        }
        normalized_plan.append(normalized_stage)
    
    return normalized_plan


def extract_artifacts_from_structured(data: Dict) -> Tuple[List[Dict], Dict[str, str]]:
    """
    从结构化 JSON 中提取产出物信息
    
    Args:
        data: parse_structured_json 返回的字典
        
    Returns:
        (templates, artifacts) 元组:
        - templates: 产出物模板列表 [{stage_id, artifact_key, name}, ...]
        - artifacts: 已生成的产出物 {key: content, ...}
    """
    artifacts_list = data.get("artifacts", [])
    if not isinstance(artifacts_list, list):
        return [], {}
    
    templates = []
    artifacts = {}
    
    for item in artifacts_list:
        stage_id = item.get("stage_id")
        key = item.get("key")
        name = item.get("name")
        content = item.get("content")
        
        if stage_id and key and name:
            templates.append({
                "stage_id": stage_id,
                "artifact_key": key,
                "name": name,
            })
        
        if key and content:
            artifacts[key] = content
    
    return templates, artifacts


# ═══════════════════════════════════════════════════════════════════════════════
# XML 标签解析 (Legacy 格式)
# ═══════════════════════════════════════════════════════════════════════════════

PLAN_PATTERN = re.compile(
    r'<plan>\s*(\[.*?\])\s*</plan>',
    re.IGNORECASE | re.DOTALL
)

ARTIFACT_TEMPLATE_PATTERN = re.compile(
    r'<artifact_template\s+'
    r'stage=["\']([^"\']+)["\']\s+'
    r'key=["\']([^"\']+)["\']\s+'
    r'name=["\']([^"\']+)["\']\s*'
    r'/?>',
    re.IGNORECASE
)

CLEANUP_PATTERNS = [
    re.compile(r'<plan>.*?</plan>', re.IGNORECASE | re.DOTALL),
    re.compile(r'<artifact_template[^>]*>', re.IGNORECASE),
    JSON_BLOCK_PATTERN,
]


def parse_plan(text: str) -> Optional[List[Dict]]:
    """
    解析响应文本中的动态 Plan 定义
    
    采用"全量快照"模式：LLM 输出的 JSON 必须包含 status 字段，
    本函数直接信赖输入的 status，不再进行默认状态推断。
    
    LLM 应输出格式如:
    <plan>[{"id": "clarify", "name": "需求澄清", "status": "completed"}, 
           {"id": "strategy", "name": "策略制定", "status": "active"}]</plan>
    
    Args:
        text: LLM 响应文本
        
    Returns:
        解析后的 Plan 列表，每个阶段包含 id, name, status
        若无 plan 标签或解析失败则返回 None
        
    Example:
        >>> parse_plan('<plan>[{"id": "clarify", "name": "需求澄清", "status": "active"}]</plan>')
        [{"id": "clarify", "name": "需求澄清", "status": "active"}]
    """
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
                # 逐字符匹配找到对应的 ]
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
        
        # 直接信赖 LLM 输出的 status，仅确保必要字段存在
        normalized_plan = []
        for i, stage in enumerate(plan_data):
            normalized_stage = {
                "id": stage.get("id", f"stage_{i}"),
                "name": stage.get("name", f"阶段 {i+1}"),
                "status": stage.get("status", "pending"),  # 信赖输入，默认 pending
            }
            normalized_plan.append(normalized_stage)
        
        logger.info(f"解析到动态 Plan: {len(normalized_plan)} 个阶段")
        return normalized_plan
        
    except json.JSONDecodeError as e:
        logger.error(f"Plan JSON 解析失败: {e}")
        return None


def parse_artifact_template(text: str) -> Optional[Dict[str, str]]:
    """
    解析响应文本中的第一个 artifact_template 标签
    
    Args:
        text: LLM 响应文本
        
    Returns:
        {"stage_id": "xxx", "artifact_key": "yyy", "name": "zzz"} 或 None
        
    Example:
        >>> parse_artifact_template('<artifact_template stage="cases" key="test_cases" name="测试用例集"/>')
        {"stage_id": "cases", "artifact_key": "test_cases", "name": "测试用例集"}
    """
    match = ARTIFACT_TEMPLATE_PATTERN.search(text)
    if match:
        result = {
            "stage_id": match.group(1),
            "artifact_key": match.group(2),
            "name": match.group(3),
        }
        logger.info(f"解析到产出物模板: stage={result['stage_id']}, key={result['artifact_key']}, name={result['name']}")
        return result
    return None


def parse_all_artifact_templates(text: str) -> List[Dict[str, str]]:
    """
    解析响应文本中的所有 artifact_template 标签
    
    Args:
        text: LLM 响应文本
        
    Returns:
        [{"stage_id": "...", "artifact_key": "...", "name": "..."}, ...] 列表
    """
    results = []
    for match in ARTIFACT_TEMPLATE_PATTERN.finditer(text):
        results.append({
            "stage_id": match.group(1),
            "artifact_key": match.group(2),
            "name": match.group(3),
        })
    
    if results:
        logger.info(f"解析到 {len(results)} 个产出物模板")
    
    return results


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
    2. 如果文本末尾包含部分未闭合的标签前缀（<plan），则截断
    
    Args:
        text: 当前累积的完整响应文本
        
    Returns:
        清理并安全截断后的文本（可安全展示给用户）
    """
    # 1. 先用常规逻辑移除完整的标签
    cleaned = text
    for pattern in CLEANUP_PATTERNS:
        cleaned = pattern.sub('', cleaned)
    
    # 2. 检查是否有未闭合的特定标签
    # 如果经过正则清理后，开头仍然是敏感标签，说明该标签未闭合
    lower_cleaned = cleaned.lower()
    sensitive_prefixes = ["<plan", "<artifact_template"]
    
    for prefix in sensitive_prefixes:
        if lower_cleaned.startswith(prefix):
            # 标签位于开头且未被移除，说明未闭合 -> 隐藏全部
            return ""
            
    # 3. 检查末尾是否有未闭合的标签片段
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
            
            # Case B: suffix 已经包含了 prefix (例如 "<plan>", "<artifact_template ...")
            # 意味着标签已经开始，但可能因为未闭合而没有被步骤1的完整正则移除
            if suffix_lower.startswith(prefix):
                return cleaned[:last_open_bracket]
            
    # 4. 检查是否有 JSON 代码块片段 (混合模式)
    # 查找最后一个 ``` 的位置
    last_code_block = cleaned.rfind('```')
    if last_code_block != -1:
        suffix = cleaned[last_code_block:]
        # Case A: 正在输入 ```json (例如 "`", "``", "```j", "```json")
        json_marker = "```json"
        if json_marker.startswith(suffix.lower()):
            # 只有当它看起来不像正常的代码块结束（即前面没有配对的 ```json）时才截断
            # 但流式传输中很难判断，这里宁可错杀不可放过（只截断末尾）
            return cleaned[:last_code_block]
        
        # Case B: 已经开始了 ```json ...
        if suffix.lower().startswith(json_marker):
            return cleaned[:last_code_block]

    return cleaned


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
