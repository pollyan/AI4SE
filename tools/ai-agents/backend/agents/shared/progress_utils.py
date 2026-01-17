"""
共享进度工具模块

提供 JSON 解析、响应清理等通用功能。
Lisa 和 Alex 智能体共用此模块。

采用"全量状态快照"模式：LLM 每次回复都输出完整的 Plan JSON（含 status）。

### 输出格式
LLM 在回复末尾输出 JSON 代码块 (```json ... ```)
"""

import re
import json
import logging
from typing import Optional, List, Dict, Tuple

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# JSON 代码块解析
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
        
        # message 字段已移除 (混合模式下 message 在 JSON 外部)
        required_fields = ["plan", "current_stage_id"]
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
# 响应文本清理
# ═══════════════════════════════════════════════════════════════════════════════

def clean_response_text(text: str) -> str:
    """
    移除响应文本中的 JSON 代码块
    
    Args:
        text: 原始响应文本
        
    Returns:
        清理后的文本
    """
    result = JSON_BLOCK_PATTERN.sub('', text)
    
    # [NEW] 移除产出物 Markdown 块
    ARTIFACT_BLOCK_PATTERN = re.compile(r'```(?:markdown)?\s*\n#.*?(?:\n[\s\S]*?)?```', re.IGNORECASE | re.DOTALL)
    result = ARTIFACT_BLOCK_PATTERN.sub('', result)
    
    # 清理可能残留的多余空行
    result = re.sub(r'\n{3,}', '\n\n', result)
    
    return result.strip()


def clean_response_streaming(text: str) -> str:
    """
    流式响应文本清理 - 处理部分传输的 JSON 代码块
    
    1. 移除完整的 JSON 代码块
    2. 如果文本末尾包含部分未闭合的代码块标记，则截断
    
    Args:
        text: 当前累积的完整响应文本
        
    Returns:
        清理并安全截断后的文本（可安全展示给用户）
    """
    # 1. 先用常规逻辑移除完整的 JSON 代码块
    cleaned = JSON_BLOCK_PATTERN.sub('', text)
    
    # [NEW] 移除产出物 Markdown 块 (```markdown ... ```)
    # 匹配完整的产出物块
    ARTIFACT_BLOCK_PATTERN = re.compile(r'```(?:markdown)?\s*\n#.*?(?:\n[\s\S]*?)?```', re.IGNORECASE | re.DOTALL)
    cleaned = ARTIFACT_BLOCK_PATTERN.sub('', cleaned)
    
    # 2. 检查是否有 JSON 代码块片段 (混合模式)
    # 查找最后一个 ``` 的位置
    last_code_block = cleaned.rfind('```')
    if last_code_block != -1:
        suffix = cleaned[last_code_block:]
        
        # Case A: 正在输入 ```json 或 ```markdown
        markers = ["```json", "```markdown"]
        for marker in markers:
             if marker.startswith(suffix.lower()):
                # 截断正在传输的代码块标记
                return cleaned[:last_code_block]
        
        # Case B: 已经开始了 ```json ... 或 ```markdown ...
        if suffix.lower().startswith("```json"):
            return cleaned[:last_code_block]
            
        # Case C: 已经开始了 ```markdown ...
        # 特别注意：我们只移除是以 `#` 开头的产出物 (避免误删用户请求的代码示例)
        if suffix.lower().startswith("```markdown"):
            # 检查内容是否包含以 # 开头的行 (产出物标题)
            # 如果仅仅是 ```markdown\n 还没有内容，也先截断，等待后续确认
            lines_after = suffix.split('\n')
            if len(lines_after) > 1:
                first_line_content = lines_after[1].strip()
                if first_line_content.startswith('#') or len(lines_after) <= 2:
                     # 是产出物（或者刚开始无法判断），截断
                     return cleaned[:last_code_block]
            else:
                 # 刚输入 ```markdown，先截断
                 return cleaned[:last_code_block]
    
    # 3. 检查末尾是否有部分 ` 字符
    # 这处理 `, ``, ``` 正在传输的情况
    if cleaned.endswith('`'):
        # 找到末尾连续的 ` 开始位置
        i = len(cleaned) - 1
        while i > 0 and cleaned[i-1] == '`':
            i -= 1
        # 如果是 1-3 个反引号，可能是代码块开始，截断
        backtick_count = len(cleaned) - i
        if 1 <= backtick_count <= 3:
            return cleaned[:i]
            
    # [NEW] 最终清理：如果文本以换行符结尾，且看起来刚刚删除了产出物，清理多余的尾部换行
    return cleaned.rstrip()


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
