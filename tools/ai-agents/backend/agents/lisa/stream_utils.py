from typing import List, Dict, Any, Callable, Iterator, Optional
from backend.agents.shared.data_stream import stream_text_delta
from .schemas import UpdateArtifact, ReasoningResponse

def get_stage_index(plan: List[Dict], stage_id: str) -> int:
    """获取阶段在计划中的索引 (Internal Helper)"""
    for i, stage in enumerate(plan):
        if stage.get("id") == stage_id:
            return i
    return 0

def process_reasoning_stream(
    stream_iterator,
    writer,
    plan: list,
    current_stage: str,
    base_artifacts: Optional[Dict[str, Any]] = None
) -> ReasoningResponse:
    """
    处理 ReasoningNode 的流式响应。
    只处理 thought 和 progress_step，不处理 artifact 更新。
    """
    current_artifacts = dict(base_artifacts) if base_artifacts else {}
    stage_index = next((i for i, s in enumerate(plan) if s["id"] == current_stage), 0)
    
    # Extract artifact_templates ONCE at the start, before the loop
    # This prevents the template from being lost after the first pop in the loop
    saved_templates = current_artifacts.pop("artifact_templates", [])
    
    final_thought = ""
    final_progress_step = None
    final_should_update_artifact = False
    
    # 状态追踪
    last_thought_len = 0
    last_sent_progress_step = None
    
    for chunk in stream_iterator:
        # 1. 处理 thought 增量
        if chunk.thought:
            current_thought = chunk.thought
            if len(current_thought) > last_thought_len:
                delta = current_thought[last_thought_len:]
                writer({
                    "type": "text_delta_chunk",
                    "delta": delta
                })
                last_thought_len = len(current_thought)
            final_thought = current_thought
            
        # 2. 处理 progress_step 更新
        if chunk.progress_step:
            current_step = chunk.progress_step
            # Use saved_templates which was extracted once before the loop
            # current_artifacts no longer contains artifact_templates (it was popped)
            
            # Construct standardized artifactProgress payload
            # This matches the structure in backend/agents/shared/progress.py:get_progress_info
            
            # 1. Convert templates to frontend metadata format (exclude 'outline')
            template_list = []
            for tmpl in saved_templates:
                template_list.append({
                    "stageId": tmpl.get("stage") or tmpl.get("stage_id"),
                    "artifactKey": tmpl.get("key") or tmpl.get("artifact_key"),
                    "name": tmpl.get("name"),
                })
                
            # 2. Identify completed artifacts
            completed_keys = list(current_artifacts.keys())
            
            writer({
                "type": "progress",
                "progress": {
                    "stages": plan,
                    "currentStageIndex": stage_index,
                    "currentTask": current_step,
                    # Replace raw artifact_templates with structured artifactProgress
                    "artifactProgress": {
                        "template": template_list,
                        "completed": completed_keys,
                        "generating": None # Reasoning phase doesn't generate artifacts
                    },
                    "artifacts": current_artifacts
                }
            })
            last_sent_progress_step = current_step
            final_progress_step = current_step
            
        # 3. 处理 should_update_artifact
        if hasattr(chunk, 'should_update_artifact'):
            # 注意: LangChain stream 可能会返回 partial chunks. 
            # bool 类型通常在最后确定，或者我们会收到 True.
            # 这里我们只记录最新值
            if chunk.should_update_artifact is not None:
                final_should_update_artifact = chunk.should_update_artifact

    return ReasoningResponse(
        thought=final_thought,
        progress_step=final_progress_step,
        should_update_artifact=final_should_update_artifact
    )
