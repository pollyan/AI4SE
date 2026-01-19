"""
Workflow Test Design Node - 测试设计工作流节点

处理测试设计工作流的核心逻辑，包括需求澄清、策略制定、用例编写和文档交付。
"""

import logging
import re
from typing import Any, List, Dict

from langchain_core.messages import SystemMessage, AIMessage, HumanMessage
from langgraph.config import get_stream_writer

from ..state import LisaState, ArtifactKeys
from ..schemas import UpdateArtifact
from ..prompts.workflows import build_workflow_prompt
from backend.agents.shared.artifact_summary import get_artifacts_summary
from ..prompts.artifacts import (
    ARTIFACT_CLARIFY_REQUIREMENTS,
    ARTIFACT_STRATEGY_BLUEPRINT,
    ARTIFACT_CASES_SET,
    ARTIFACT_DELIVERY_FINAL,
    ARTIFACT_REQ_REVIEW_RECORD
)
from backend.agents.shared.data_stream import (
    stream_tool_call,
    stream_tool_result
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# 默认计划定义
# ═══════════════════════════════════════════════════════════════════════════════

DEFAULT_TEST_DESIGN_PLAN: List[Dict[str, str]] = [
    {"id": "clarify", "name": "需求澄清", "status": "pending"},
    {"id": "strategy", "name": "策略制定", "status": "pending"},
    {"id": "cases", "name": "用例设计", "status": "pending"},
    {"id": "delivery", "name": "文档交付", "status": "pending"},
]

DEFAULT_REQUIREMENT_REVIEW_PLAN: List[Dict[str, str]] = [
    {"id": "clarify", "name": "需求澄清", "status": "pending"},
    {"id": "analysis", "name": "需求分析", "status": "pending"},
    {"id": "risk", "name": "风险评估", "status": "pending"},
    {"id": "report", "name": "评审报告", "status": "pending"},
]

# 产出物模板元数据
ARTIFACT_TEMPLATES_TEST_DESIGN = [
    {"stage_id": "clarify", "artifact_key": "test_design_requirements", "name": "需求澄清报告"},
    {"stage_id": "strategy", "artifact_key": "test_design_strategy", "name": "测试策略蓝图"},
    {"stage_id": "cases", "artifact_key": "test_design_cases", "name": "测试用例集"},
    {"stage_id": "delivery", "artifact_key": "test_design_final", "name": "交付文档"},
]

ARTIFACT_TEMPLATES_REQUIREMENT_REVIEW = [
    {"stage_id": "clarify", "artifact_key": "req_review_record", "name": "需求评审记录"},
    {"stage_id": "analysis", "artifact_key": "req_review_record", "name": "需求评审记录"},
    {"stage_id": "risk", "artifact_key": "req_review_risk", "name": "风险评估报告"},
    {"stage_id": "report", "artifact_key": "req_review_report", "name": "评审报告"},
]

def get_artifact_templates(workflow_type: str) -> List[Dict[str, str]]:
    """获取工作流对应的产出物模板元数据"""
    if workflow_type == "requirement_review":
        return ARTIFACT_TEMPLATES_REQUIREMENT_REVIEW
    return ARTIFACT_TEMPLATES_TEST_DESIGN


# ═══════════════════════════════════════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════════════════════════════════════

def get_default_plan(workflow_type: str) -> List[Dict[str, str]]:
    """获取工作流的默认计划"""
    if workflow_type == "requirement_review":
        return [dict(s) for s in DEFAULT_REQUIREMENT_REVIEW_PLAN]
    return [dict(s) for s in DEFAULT_TEST_DESIGN_PLAN]


def get_stage_index(plan: List[Dict], stage_id: str) -> int:
    """获取阶段在计划中的索引"""
    for i, stage in enumerate(plan):
        if stage.get("id") == stage_id:
            return i
    return 0


def update_plan_status(plan: List[Dict], current_stage_id: str) -> None:
    """更新计划中各阶段的状态"""
    current_idx = get_stage_index(plan, current_stage_id)
    for i, stage in enumerate(plan):
        if i < current_idx:
            stage["status"] = "completed"
        elif i == current_idx:
            stage["status"] = "active"
        else:
            stage["status"] = "pending"

def determine_stage(state: LisaState, workflow_type: str) -> str:
    """
    根据产出物确定当前阶段
    
    Args:
        state: 当前状态
        workflow_type: 工作流类型
    """
    artifacts = state.get("artifacts", {})
    
    if workflow_type == "requirement_review":
        # 需求评审流程: clarify -> analysis -> risk -> report
        if ArtifactKeys.REQ_REVIEW_REPORT in artifacts:
            return "report"  # 已完成，停留在最后阶段或进入结束
        elif ArtifactKeys.REQ_REVIEW_RISK in artifacts:
            return "report"
        elif ArtifactKeys.REQ_REVIEW_RECORD in artifacts:
            return "risk"
        else:
            return "clarify"
            
    else:  # 默认为 test_design
        # 测试设计流程: clarify -> strategy -> cases -> delivery
        if ArtifactKeys.TEST_DESIGN_FINAL in artifacts:
            return "delivery"
        elif ArtifactKeys.TEST_DESIGN_CASES in artifacts:
            return "delivery"
        elif ArtifactKeys.TEST_DESIGN_STRATEGY in artifacts:
            return "cases"
        elif ArtifactKeys.TEST_DESIGN_REQUIREMENTS in artifacts:
            return "strategy"
        else:
            return "clarify"


def get_artifact_template(key: str) -> str:
    """根据 Artifact Key 获取对应的 Markdown 模板"""
    if key == ArtifactKeys.TEST_DESIGN_REQUIREMENTS: return ARTIFACT_CLARIFY_REQUIREMENTS
    if key == ArtifactKeys.TEST_DESIGN_STRATEGY: return ARTIFACT_STRATEGY_BLUEPRINT
    if key == ArtifactKeys.TEST_DESIGN_CASES: return ARTIFACT_CASES_SET
    if key == ArtifactKeys.TEST_DESIGN_FINAL: return ARTIFACT_DELIVERY_FINAL
    if key == ArtifactKeys.REQ_REVIEW_RECORD: return ARTIFACT_REQ_REVIEW_RECORD
    return ""

def get_artifact_key_for_stage(stage: str, workflow_type: str) -> str | None:
    """获取阶段对应的产出物 Key"""
    if workflow_type == "requirement_review":
        stage_to_artifact = {
            "clarify": ArtifactKeys.REQ_REVIEW_RECORD,
            "analysis": ArtifactKeys.REQ_REVIEW_RECORD,
            "risk": ArtifactKeys.REQ_REVIEW_RISK,
            "report": ArtifactKeys.REQ_REVIEW_REPORT,
        }
    else:
        stage_to_artifact = {
            "clarify": ArtifactKeys.TEST_DESIGN_REQUIREMENTS,
            "strategy": ArtifactKeys.TEST_DESIGN_STRATEGY,
            "cases": ArtifactKeys.TEST_DESIGN_CASES,
            "delivery": ArtifactKeys.TEST_DESIGN_FINAL,
        }
    return stage_to_artifact.get(stage)


# ═══════════════════════════════════════════════════════════════════════════════
# 主节点
# ═══════════════════════════════════════════════════════════════════════════════

def workflow_execution_node(state: LisaState, llm: Any) -> LisaState:
    """
    通用工作流执行节点
    
    能够处理 test_design 和 requirement_review 两种工作流。
    使用 get_stream_writer() 实时推送进度和产出物更新。
    """
    # 获取 StreamWriter 用于实时推送进度
    writer = get_stream_writer()
    
    # 获取当前工作流类型，默认为 test_design
    workflow_type = state.get("current_workflow") or "test_design"
    logger.info(f"执行工作流: {workflow_type}")
    
    # 确定当前阶段 (优先使用 current_stage_id)
    current_stage = state.get("current_stage_id") or state.get("workflow_stage")
    if not current_stage:
        current_stage = determine_stage(state, workflow_type)
    
    logger.info(f"当前阶段: {current_stage}")
    
    # 获取或初始化计划
    plan = state.get("plan") or get_default_plan(workflow_type)
    update_plan_status(plan, current_stage)
    
    # ════════════════════════════════════════════════════════════
    # 📍 推送进度更新
    # ════════════════════════════════════════════════════════════
    writer({
        "type": "progress",
        "progress": {
            "stages": plan,
            "currentStageIndex": get_stage_index(plan, current_stage),
            "currentTask": f"正在处理 {current_stage} 阶段...",
            "artifact_templates": get_artifact_templates(workflow_type)
        }
    })
    logger.info(f"StreamWriter 推送进度: stage={current_stage}")
    
    # ════════════════════════════════════════════════════════════
    # 📍 自动初始化产出物模板
    # ════════════════════════════════════════════════════════════
    target_artifact_key = get_artifact_key_for_stage(current_stage, workflow_type)
    
    if target_artifact_key:
        current_artifacts = state.get("artifacts", {})
        if target_artifact_key not in current_artifacts:
            # 1. 获取模板
            template = get_artifact_template(target_artifact_key)
            if template:
                # 2. 推送初始化事件 (作为 Progress 事件)
                # 构造临时 artifacts 字典用于前端展示
                display_artifacts = current_artifacts.copy()
                display_artifacts[target_artifact_key] = template
                
                writer({
                    "type": "progress",
                    "progress": {
                        "stages": plan,
                        "currentStageIndex": get_stage_index(plan, current_stage),
                        "currentTask": f"正在处理 {current_stage} 阶段...",
                        "artifact_templates": get_artifact_templates(workflow_type),
                        "artifacts": display_artifacts
                    }
                })
                logger.info(f"StreamWriter 初始化模板: {target_artifact_key}")
    
    # 构建上下文
    artifacts = state.get("artifacts", {})
    artifacts_summary = get_artifacts_summary(artifacts)
    pending = state.get("pending_clarifications", [])
    consensus = state.get("consensus_items", [])
    
    # 构建进度计划上下文
    plan = state.get("plan", [])
    plan_context_lines = []
    for step in plan:
        step_id = step.get("id", "")
        step_name = step.get("name", "")
        marker = "→ " if step_id == current_stage else "  "
        plan_context_lines.append(f"{marker}{step_id}: {step_name}")
    plan_context = "\n".join(plan_context_lines) if plan_context_lines else "(无进度计划)"
    
    # 使用统一的 Prompt 构建函数
    system_prompt = build_workflow_prompt(
        workflow_type=workflow_type,
        stage=current_stage,
        artifacts_summary=artifacts_summary,
        pending_clarifications=", ".join(pending) if pending else "(无)",
        consensus_count=len(consensus),
        plan_context=plan_context,
    )
    
    # 构建消息列表
    messages = [SystemMessage(content=system_prompt)]
    for msg in state.get("messages", []):
        messages.append(msg)
    
    # 绑定工具
    llm_with_tools = llm.model.bind_tools([UpdateArtifact])
    
    # 最终汇总的消息内容
    final_content = ""
    
    # 累计的 Tool Args 字符串 (用于流式解析)
    accumulated_tool_args = {} # {tool_call_index: "args_string"}
    
    # [NEW] 记录已见过的 Tool Call Index -> ID 映射 (用于 Data Stream Protocol)
    tool_call_ids = {} # {index: tool_call_id}
    
    # 调用 LLM (改为 Stream 模式)
    try:
        # 使用同步流 (因为 Graph 节点目前是同步的)
        stream = llm_with_tools.stream(messages)
        
        # 收集 chunks 用于最终状态合成
        collected_chunks = []
        
        for chunk in stream:
            collected_chunks.append(chunk)
            
            # 1. 累加文本内容 (普通对话)
            if chunk.content:
                final_content += str(chunk.content)
            
            # 2. 处理 Tool Call Chunks (流式更新产出物)
            if chunk.tool_call_chunks:
                for tool_chunk in chunk.tool_call_chunks:
                    idx = tool_chunk["index"]
                    
                    # ════════════════════════════════════════════════════════
                    # Data Stream Protocol 支持 (Phase 2)
                    # ════════════════════════════════════════════════════════
                    if tool_chunk.get("name") == "UpdateArtifact":
                        # 1. Handle Start Event
                        if idx not in tool_call_ids:
                            # 尝试获取 ID，若无则生成临时 ID (通常首个 chunk 有 ID)
                            tc_id = tool_chunk.get("id") or f"call_{idx}"
                            tool_call_ids[idx] = tc_id
                            
                        # 2. Delta Event (Skipped for V2 simplified stream)
                        # pass

                    # ════════════════════════════════════════════════════════
                    # Legacy Partial JSON Parsing (Backward Compat)
                    # ════════════════════════════════════════════════════════
                    if idx not in accumulated_tool_args:
                        accumulated_tool_args[idx] = ""
                    
                    # 累加参数字符串
                    if tool_chunk.get("args"):
                        accumulated_tool_args[idx] += tool_chunk["args"]
                        
                        # 尝试从累加的字符串中提取 markdown_body
                        # 这是一个 "Best Effort" 的流式提取，不必等待 JSON 闭合
                        current_args_str = accumulated_tool_args[idx]
                        
                        # 查找 "markdown_body": " 之后的内容
                        # 提取 key (如果已出现)
                        key_match = re.search(r'"key":\s*"([^"]+)"', current_args_str)
                        current_key = key_match.group(1) if key_match else None
                        
                        # 提取 body (处理转义引号)
                        body_start_pattern = r'"markdown_body":\s*"'
                        body_match = re.search(body_start_pattern, current_args_str)
                        
                        if current_key and body_match:
                            start_pos = body_match.end()
                            raw_body = current_args_str[start_pos:]
                            
                            # 截断末尾可能的未闭合引号 (简单启发式)
                            if raw_body.endswith('"') and len(raw_body) > 1 and raw_body[-2] != '\\':
                                raw_body = raw_body[:-1]
                            
                            # 简易 Unescape (仅处理最常见的)
                            clean_body = raw_body.replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\')
                            
                            # 构造临时 artifacts 用于推送
                            stream_artifacts = dict(artifacts)
                            stream_artifacts[current_key] = clean_body
                            
                            writer({
                                "type": "progress",
                                "progress": {
                                    "stages": plan,
                                    "currentStageIndex": get_stage_index(plan, current_stage),
                                    "currentTask": f"正在生成文档...",
                                    "artifacts": stream_artifacts
                                }
                            })

        # 合并 chunks 构造最终响应
        if collected_chunks:
            # sum() 默认 start=0，会导致 0 + Chunk 报错
            # 我们需要手动累加或指定 start
            response = collected_chunks[0]
            for next_chunk in collected_chunks[1:]:
                response = response + next_chunk
        else:
            response = AIMessage(content="")

        response_content = str(response.content)
        
        # DEBUG LOGGING
        logger.warning(f"LLM Response Content Length: {len(response_content)}")
        if len(response_content) > 500:
            logger.warning(f"LLM Response tail (500 chars): {response_content[-500:]}")
        else:
            logger.warning(f"LLM Response full: {response_content}")
            
        new_artifacts = dict(artifacts)
        artifact_updated = False
        
        # 优先检查 Tool Calls
        if response.tool_calls:
            logger.info(f"检测到 Tool Calls: {len(response.tool_calls)}")
            for tool_call in response.tool_calls:
                if tool_call["name"] == "UpdateArtifact":
                    args = tool_call["args"]
                    key = args.get("key")
                    content = args.get("markdown_body")
                    
                    if key and content:
                        new_artifacts[key] = content
                        artifact_updated = True
                        logger.info(f"ToolCall 更新产出物: {key}")
                        
                        # 推送最终更新 (虽然流式已经推过了，但这里确保一致性)
                        writer({
                            "type": "progress",
                            "progress": {
                                "stages": plan,
                                "currentStageIndex": get_stage_index(plan, current_stage),
                                    "currentTask": f"正在处理 {current_stage} 阶段...",
                                "artifacts": new_artifacts
                            }
                        })
                        
                        # [NEW] 推送 Tool Result 事件 (Data Stream Protocol)
                        writer({
                            "type": "data_stream_event",
                            "event": stream_tool_result(
                                tool_call_id=tool_call["id"],
                                tool_name="UpdateArtifact",
                                result={"key": key, "status": "completed"}
                            )
                        })
        
        # 如果没有 Tool Call，且内容非空，则作为普通对话处理
        # 移除了 Regex Fallback，强制要求模型使用工具生成文档
        if not artifact_updated:
             logger.info("未检测到 ToolCall，作为普通回复处理")

        ai_message = AIMessage(content=response_content)
        
        # 更新消息历史
        new_messages = list(state.get("messages", []))
        new_messages.append(ai_message)
        
        # 返回更新后的状态
        return {
            **state,
            "messages": new_messages,
            "artifacts": new_artifacts,
            "workflow_stage": current_stage,
            "current_workflow": workflow_type,
        }
        
    except Exception as e:
        logger.error(f"测试设计工作流执行失败: {e}")
        error_message = AIMessage(content=f"抱歉，处理您的请求时遇到了问题：{str(e)}")
        new_messages = list(state.get("messages", []))
        new_messages.append(error_message)
        
        return {
            **state,
            "messages": new_messages,
        }
