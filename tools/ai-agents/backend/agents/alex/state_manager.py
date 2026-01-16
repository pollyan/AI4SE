"""
Alex 智能体状态管理器

管理每个会话的工作流状态，处理 Tool 调用，生成前端 ProgressInfo。
采用内存存储，按 session_id 隔离状态。

状态结构:
- plan: 阶段计划列表
- current_stage_id: 当前活跃阶段
- artifact_templates: 产出物模板列表
- artifacts: 已生成的产出物内容
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


@dataclass
class AlexSessionState:
    """单个会话的状态"""
    
    # 阶段计划: [{"id": "clarify", "name": "需求澄清", "status": "active"}]
    plan: List[Dict[str, str]] = field(default_factory=list)
    
    # 当前活跃阶段 ID
    current_stage_id: str = ""
    
    # 当前细粒度任务描述 (如 "正在分析需求...", "正在生成用例...")
    current_task: str = ""
    
    # 产出物模板: [{"stage_id": "clarify", "artifact_key": "req_doc", "name": "需求分析文档"}]
    artifact_templates: List[Dict[str, str]] = field(default_factory=list)
    
    # 产出物内容: {"req_doc": "# 需求分析文档\n..."}
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
    
    def handle_set_plan(self, session_id: str, stages: List[Dict[str, Any]]) -> None:
        """
        处理 set_plan Tool 调用
        
        设置工作流计划和产出物模板，第一个阶段自动设为 active。
        
        Args:
            session_id: 会话 ID
            stages: 阶段列表，每个阶段包含 id, name, artifact_key?, artifact_name?
        """
        state = self.get_state(session_id)
        
        # 重置状态
        state.plan = []
        state.artifact_templates = []
        state.plan = []
        state.artifact_templates = []
        state.current_stage_id = ""
        state.current_task = ""
        
        if not stages:
            logger.warning(f"set_plan 收到空的 stages 列表: {session_id}")
            return
        
        for i, stage in enumerate(stages):
            stage_id = stage.get("id", "")
            stage_name = stage.get("name", "")
            
            if not stage_id or not stage_name:
                logger.warning(f"跳过无效阶段: {stage}")
                continue
            
            # 添加阶段（第一个为 active，其余为 pending）
            status = "active" if i == 0 else "pending"
            state.plan.append({
                "id": stage_id,
                "name": stage_name,
                "status": status
            })
            
            # 添加产出物模板（如果有）
            artifact_key = stage.get("artifact_key")
            artifact_name = stage.get("artifact_name")
            if artifact_key:
                state.artifact_templates.append({
                    "stage_id": stage_id,
                    "artifact_key": artifact_key,
                    "name": artifact_name or artifact_key
                })
        
        # 设置当前阶段
        if state.plan:
            state.current_stage_id = state.plan[0]["id"]
        
        logger.info(
            f"set_plan 完成: {session_id}, "
            f"{len(state.plan)} 个阶段, "
            f"{len(state.artifact_templates)} 个产出物模板"
        )
    
    def handle_update_stage(self, session_id: str, stage_id: str, status: str) -> None:
        """
        处理 update_stage Tool 调用
        
        更新阶段状态。如果设为 completed，自动激活下一个阶段。
        
        Args:
            session_id: 会话 ID
            stage_id: 阶段 ID
            status: 新状态 ('active' 或 'completed')
        """
        state = self.get_state(session_id)
        
        if not state.plan:
            logger.warning(f"update_stage 失败，plan 为空: {session_id}")
            return
        
        # 查找阶段并更新
        stage_index = -1
        for i, stage in enumerate(state.plan):
            if stage["id"] == stage_id:
                stage["status"] = status
                stage_index = i
                
                if status == "active":
                    state.current_stage_id = stage_id
                break
        
        if stage_index == -1:
            logger.warning(f"update_stage 失败，未找到阶段: {stage_id}")
            return
        
        # 如果设为 completed，自动激活下一个阶段
        if status == "completed" and stage_index + 1 < len(state.plan):
            next_stage = state.plan[stage_index + 1]
            next_stage["status"] = "active"
            state.current_stage_id = next_stage["id"]
            logger.debug(f"自动激活下一阶段: {next_stage['id']}")
        
        logger.info(f"update_stage 完成: {session_id}, {stage_id} -> {status}")
    
    def handle_save_artifact(self, session_id: str, key: str, content: str) -> None:
        """
        处理 save_artifact Tool 调用
        
        保存产出物内容。
        
        Args:
            session_id: 会话 ID
            key: 产出物键（需与 artifact_templates 中的 artifact_key 匹配）
            content: 产出物内容（Markdown 格式）
        """
        state = self.get_state(session_id)
        
        if not key:
            logger.warning(f"save_artifact 失败，key 为空: {session_id}")
            return
        
        state.artifacts[key] = content or ""
        
        logger.info(
            f"save_artifact 完成: {session_id}, "
            f"key={key}, 内容长度={len(content or '')} 字符"
        )
    
    def handle_update_task(self, session_id: str, task_name: str) -> None:
        """
        处理 update_task Tool 调用
        
        更新当前细粒度任务描述。
        
        Args:
            session_id: 会话 ID
            task_name: 任务名称
        """
        state = self.get_state(session_id)
        
        if not task_name:
            return
            
        state.current_task = task_name
        logger.info(f"update_task 完成: {session_id}, task='{task_name}'")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 生成前端 ProgressInfo
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_progress_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        生成前端 ProgressInfo 格式
        
        Args:
            session_id: 会话 ID
            
        Returns:
            ProgressInfo 字典，如果 plan 为空则返回 None
            格式: {
                "stages": [{id, name, status}],
                "currentStageIndex": int,
                "currentTask": str,
                "artifactProgress": {
                    "template": [{stageId, artifactKey, name}],
                    "completed": [artifact_key],
                    "generating": artifact_key | null
                },
                "artifacts": {key: content}
            }
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
        
        # 构建 currentTask
        current_task = "处理中..."
        if state.current_task:
            # 优先使用细粒度任务描述
            current_task = state.current_task
        elif 0 <= current_index < len(state.plan):
            # 回退到默认的阶段描述
            stage_name = state.plan[current_index]["name"]
            current_task = f"正在{stage_name}..."
        
        # 构建 artifactProgress
        completed_keys = list(state.artifacts.keys())
        
        # 正在生成的产出物 = 当前阶段的模板中未完成的
        generating_key = None
        for tmpl in state.artifact_templates:
            if tmpl["stage_id"] == state.current_stage_id:
                if tmpl["artifact_key"] not in state.artifacts:
                    generating_key = tmpl["artifact_key"]
                    break
        
        return {
            "stages": state.plan,
            "currentStageIndex": current_index,
            "currentTask": current_task,
            "artifactProgress": {
                "template": [
                    {
                        "stageId": t["stage_id"],
                        "artifactKey": t["artifact_key"],
                        "name": t["name"]
                    }
                    for t in state.artifact_templates
                ],
                "completed": completed_keys,
                "generating": generating_key
            },
            "artifacts": state.artifacts
        }
