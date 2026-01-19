from typing import List, Dict, Any, Callable, Iterator, Optional
from backend.agents.shared.data_stream import stream_text_delta
from .schemas import WorkflowResponse, UpdateArtifact

def get_stage_index(plan: List[Dict], stage_id: str) -> int:
    """获取阶段在计划中的索引 (Internal Helper)"""
    for i, stage in enumerate(plan):
        if stage.get("id") == stage_id:
            return i
    return 0

def process_workflow_stream(
    stream_iterator: Iterator[WorkflowResponse],
    writer: Callable[[Dict[str, Any]], None],
    plan: List[Dict[str, Any]],
    current_stage: str,
    base_artifacts: Dict[str, str]
) -> WorkflowResponse:
    """
    处理 WorkflowResponse 流，负责 Diff 计算和事件推送。
    """
    final_thought = ""
    final_progress_step = None
    final_update_artifact: Optional[UpdateArtifact] = None
    
    # 状态追踪 (用于 Diff)
    last_thought_len = 0
    last_artifact_body_len = 0
    # 追踪上一次发送的 progress_step，避免重复发送
    last_sent_progress_step = None
    
    # 当前 artifacts 状态 (用于增量推送)
    current_artifacts = dict(base_artifacts)
    stage_index = get_stage_index(plan, current_stage)
    
    for chunk in stream_iterator:
        # ---------------------------------------------------------
        # 1. 处理 thought 增量 (对话)
        # ---------------------------------------------------------
        if chunk.thought:
            current_thought = chunk.thought
            if len(current_thought) > last_thought_len:
                delta = current_thought[last_thought_len:]
                # 使用 text-delta 事件推送到 Data Stream Protocol
                writer({
                    "type": "text_delta_chunk",
                    "delta": delta
                })
                last_thought_len = len(current_thought)
            final_thought = current_thought
            
        # ---------------------------------------------------------
        # 2. 处理 progress_step 更新 (状态)
        # ---------------------------------------------------------
        if chunk.progress_step:
            current_step = chunk.progress_step
            final_progress_step = current_step
            
            # 如果步骤描述发生变化，推送进度更新
            if current_step != last_sent_progress_step:
                writer({
                    "type": "progress",
                    "progress": {
                        "stages": plan,
                        "currentStageIndex": stage_index,
                        "currentTask": current_step,
                        "artifacts": current_artifacts
                    }
                })
                last_sent_progress_step = current_step

        # ---------------------------------------------------------
        # 3. 处理 artifact 更新 (行动)
        # ---------------------------------------------------------
        if chunk.update_artifact:
            final_update_artifact = chunk.update_artifact
            
            # 只有当内容变长时才推送 (避免频繁空更新)
            current_body = chunk.update_artifact.markdown_body
            current_key = chunk.update_artifact.key
            
            if current_body and len(current_body) > last_artifact_body_len:
                # 更新本地 artifacts 副本
                current_artifacts[current_key] = current_body
                
                writer({
                    "type": "progress",
                    "progress": {
                        "stages": plan,
                        "currentStageIndex": stage_index,
                        "currentTask": last_sent_progress_step or f"正在生成 {current_key}...",
                        "artifacts": current_artifacts
                    }
                })
                last_artifact_body_len = len(current_body)

    # 构造最终响应对象
    return WorkflowResponse(
        thought=final_thought,
        progress_step=final_progress_step,
        update_artifact=final_update_artifact
    )
