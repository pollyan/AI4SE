"""
Alex 智能体状态管理器

管理每个会话的工作流状态，处理 Tool 调用，生成前端 ProgressInfo。
采用内存存储，按 session_id 隔离状态。

状态结构:
- plan: 阶段计划列表
- current_stage_id: 当前活跃阶段
- current_task: 当前细粒度任务
- artifacts: 已生成的产出物内容
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from .templates import (
    get_template,
    get_template_by_stage,
    render_template_skeleton,
    update_section_content,
)

logger = logging.getLogger(__name__)


@dataclass
class AlexSessionState:
    """单个会话的状态"""
    
    # 阶段计划: [{"id": "clarify", "name": "需求澄清", "status": "active", "artifact_key": "...", "artifact_name": "..."}]
    plan: List[Dict[str, Any]] = field(default_factory=list)
    
    # 当前活跃阶段 ID
    current_stage_id: str = ""
    
    # 上一次的阶段 ID (用于检测阶段切换)
    _last_stage_id: str = ""
    
    # 当前细粒度任务描述 (如 "正在分析需求...", "正在生成用例...")
    current_task: str = ""
    
    # 产出物内容: {"test_design_requirements": "# 需求分析文档\n..."}
    artifacts: Dict[str, str] = field(default_factory=dict)


class AlexStateManager:
    """Alex 状态管理器"""
    
    def __init__(self):
        self._sessions: Dict[str, AlexSessionState] = {}
    
    def get_state(self, session_id: str) -> AlexSessionState:
        """获取或创建会话状态"""
        if session_id not in self._sessions:
            self._sessions[session_id] = AlexSessionState()
            logger.debug(f"创建新会话状态: {session_id}")
        return self._sessions[session_id]
    
    def clear_state(self, session_id: str) -> None:
        """清除会话状态"""
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.debug(f"清除会话状态: {session_id}")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Tool 处理函数
    # ═══════════════════════════════════════════════════════════════════════════
    
    def handle_update_progress(self, session_id: str, stages: List[Any], 
                                current_stage_id: str, current_task: str) -> None:
        """
        处理 update_progress Tool 调用
        
        全量更新工作流状态。当阶段切换时，自动初始化新阶段的产出物模板。
        """
        import json
        state = self.get_state(session_id)
        
        # 预处理: 如果 stages 是 JSON 字符串，尝试解析
        if isinstance(stages, str):
            try:
                parsed = json.loads(stages)
                if isinstance(parsed, list):
                    stages = parsed
                else:
                    logger.warning(f"stages 解析后不是列表: {type(parsed)}")
            except json.JSONDecodeError:
                logger.warning(f"stages 字符串无法解析为 JSON: {stages[:100]}...")
        
        # 验证并清洗 stages 数据
        valid_stages = []
        if isinstance(stages, list):
            for i, stage in enumerate(stages):
                if isinstance(stage, dict):
                    s_id = stage.get("id") or stage.get("stage_id")
                    s_name = stage.get("name") or stage.get("stage_name") or s_id
                    s_status = stage.get("status")
                    
                    if s_id:
                        valid_stages.append({
                            "id": str(s_id),
                            "name": str(s_name),
                            "status": str(s_status) if s_status else ("active" if i == 0 else "pending"),
                            "artifact_key": stage.get("artifact_key"),
                            "artifact_name": stage.get("artifact_name")
                        })
                    else:
                        logger.warning(f"Stage 缺少 id 字段: {stage}")
                        
                elif isinstance(stage, str) and stage.strip():
                    valid_stages.append({
                        "id": stage.strip(),
                        "name": stage.strip(),
                        "status": "active" if i == 0 else "pending"
                    })
                else:
                    logger.warning(f"忽略无效的 stage 数据类型: {type(stage)}")
        else:
            logger.warning(f"stages 参数格式错误 (期望 List, 实际 {type(stages)})")
        
        # 兜底策略
        if not valid_stages and state.plan:
            logger.warning("本次 update_progress 未解析出有效 stages，保留原有 plan，仅更新 task")
            state.current_stage_id = current_stage_id or state.current_stage_id
            state.current_task = current_task or state.current_task
            return

        # 更新状态
        if valid_stages:
            state.plan = valid_stages
            
        old_stage_id = state._last_stage_id
        state.current_stage_id = current_stage_id
        state.current_task = current_task
        
        # ─────────────────────────────────────────────────────────────────────────
        # 阶段切换检测：自动初始化产出物模板
        # ─────────────────────────────────────────────────────────────────────────
        if current_stage_id and current_stage_id != old_stage_id:
            self._initialize_stage_artifact(session_id, current_stage_id, state)
            state._last_stage_id = current_stage_id
        
        logger.info(
            f"update_progress 完成: {session_id}, "
            f"阶段数={len(state.plan)}, 当前阶段={state.current_stage_id}, 任务={state.current_task}"
        )

    def _initialize_stage_artifact(self, session_id: str, stage_id: str, state: AlexSessionState) -> None:
        """
        当进入新阶段时，自动初始化该阶段的产出物为模板骨架
        """
        # 从 plan 中找到该阶段的 artifact_key
        artifact_key = None
        for stage in state.plan:
            if stage["id"] == stage_id:
                artifact_key = stage.get("artifact_key")
                break
        
        if not artifact_key:
            # 尝试通过 stage_id 从模板定义中获取
            template_info = get_template_by_stage(stage_id)
            if template_info:
                artifact_key = template_info.get("artifact_key")
        
        if not artifact_key:
            logger.debug(f"阶段 {stage_id} 没有关联的产出物模板")
            return
        
        # 如果该产出物已经存在内容，不覆盖
        if artifact_key in state.artifacts and state.artifacts[artifact_key]:
            logger.debug(f"产出物 {artifact_key} 已存在内容，跳过初始化")
            return
        
        # 渲染模板骨架
        skeleton = render_template_skeleton(artifact_key)
        if skeleton:
            state.artifacts[artifact_key] = skeleton
            logger.info(f"自动初始化产出物模板: {artifact_key} (阶段: {stage_id})")
        else:
            logger.warning(f"未找到产出物模板定义: {artifact_key}")

    def handle_update_artifact(self, session_id: str, artifact_key: str, 
                                section_id: str, content: str) -> None:
        """
        处理 update_artifact Tool 调用
        
        按章节更新产出物内容（全量替换指定章节）。
        
        Args:
            session_id: 会话 ID
            artifact_key: 产出物唯一标识
            section_id: 要更新的章节 ID
            content: 该章节的完整内容
        """
        state = self.get_state(session_id)
        
        # 如果产出物不存在，先初始化模板
        if artifact_key not in state.artifacts:
            skeleton = render_template_skeleton(artifact_key)
            if skeleton:
                state.artifacts[artifact_key] = skeleton
            else:
                # 没有模板定义，直接存储内容
                state.artifacts[artifact_key] = content
                logger.info(f"update_artifact 完成 (无模板): {artifact_key}")
                return
        
        # 更新指定章节
        current_content = state.artifacts[artifact_key]
        updated_content = update_section_content(
            current_content, artifact_key, section_id, content
        )
        
        if updated_content:
            state.artifacts[artifact_key] = updated_content
            logger.info(f"update_artifact 完成: {artifact_key}.{section_id}")
        else:
            logger.warning(f"章节更新失败: {artifact_key}.{section_id}")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 生成前端 ProgressInfo
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_progress_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        生成前端 ProgressInfo 格式
        """
        state = self.get_state(session_id)
        
        if not state.plan:
            return None
        
        # 计算当前阶段索引
        current_index = 0
        for i, stage in enumerate(state.plan):
            if stage["id"] == state.current_stage_id:
                current_index = i
                break
        
        # 从 plan 中提取产出物模板信息
        artifact_templates = []
        generating_key = None
        
        for stage in state.plan:
            if stage.get("artifact_key"):
                tmpl = {
                    "stageId": stage["id"],
                    "artifactKey": stage["artifact_key"],
                    "name": stage.get("artifact_name") or stage["artifact_key"]
                }
                artifact_templates.append(tmpl)
                
                # 判断是否正在生成
                if stage["id"] == state.current_stage_id:
                    artifact_key = stage["artifact_key"]
                    # 检查是否还有 placeholder 内容 (表示未完成)
                    if artifact_key in state.artifacts:
                        content = state.artifacts[artifact_key]
                        if "*待" in content or "*暂无*" in content:
                            generating_key = artifact_key

        completed_keys = [
            k for k, v in state.artifacts.items() 
            if v and "*待" not in v and "*暂无*" not in v
        ]
        
        return {
            "stages": state.plan,
            "currentStageIndex": current_index,
            "currentTask": state.current_task or "处理中...",
            "artifactProgress": {
                "template": artifact_templates,
                "completed": completed_keys,
                "generating": generating_key
            },
            "artifacts": state.artifacts
        }
