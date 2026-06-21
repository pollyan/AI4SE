import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from run_collaboration_state import (
    audit_event_snapshot,
    build_collaboration_state_models,
    comment_snapshot,
    section_lock_snapshot,
)


def test_build_collaboration_state_models_preserves_api_snapshot_shape():
    state = build_collaboration_state_models(
        run_id="run-1",
        workflow_id="TEST_DESIGN",
        current_stage_id="CLARIFY",
        patch={
            "comments": [
                {
                    "id": "comment-1",
                    "stageId": "CLARIFY",
                    "content": "这里需要业务确认登录边界。",
                    "artifactExcerpt": "登录边界",
                    "anchorText": "登录边界",
                    "createdAt": 1710000000000,
                    "status": "resolved",
                    "resolvedAt": 1710000000300,
                    "replies": [
                        {
                            "id": "reply-1",
                            "content": "已补充登录异常边界。",
                            "createdAt": 1710000000200,
                        }
                    ],
                }
            ],
            "sectionLocks": [
                {
                    "id": "lock-1",
                    "stageId": "CLARIFY",
                    "heading": "## 业务规则",
                    "sectionAnchor": "h2:业务规则:1",
                    "content": "## 业务规则\n\n已确认登录规则。",
                    "createdAt": 1710000000100,
                }
            ],
        },
        created_at_ms=1710000000999,
    )

    assert [comment_snapshot(comment) for comment in state.comments] == [
        {
            "id": "comment-1",
            "stageId": "CLARIFY",
            "content": "这里需要业务确认登录边界。",
            "artifactExcerpt": "登录边界",
            "anchorText": "登录边界",
            "createdAt": 1710000000000,
            "status": "resolved",
            "resolvedAt": 1710000000300,
            "replies": [
                {
                    "id": "reply-1",
                    "content": "已补充登录异常边界。",
                    "createdAt": 1710000000200,
                }
            ],
        }
    ]
    assert [section_lock_snapshot(lock) for lock in state.section_locks] == [
        {
            "id": "lock-1",
            "stageId": "CLARIFY",
            "heading": "## 业务规则",
            "sectionAnchor": "h2:业务规则:1",
            "content": "## 业务规则\n\n已确认登录规则。",
            "createdAt": 1710000000100,
        }
    ]
    assert audit_event_snapshot(state.audit_event) == {
        "stageId": "CLARIFY",
        "eventType": "collaboration_updated",
        "summary": "更新了 CLARIFY 阶段协作状态：1 条批注，1 个章节锁",
        "createdAt": 1710000000999,
    }


def test_build_collaboration_state_models_rejects_stage_outside_workflow():
    with pytest.raises(
        ValueError,
        match="workflowId 与 stageId 不匹配: TEST_DESIGN/REPORT",
    ):
        build_collaboration_state_models(
            run_id="run-1",
            workflow_id="TEST_DESIGN",
            current_stage_id="CLARIFY",
            patch={
                "comments": [
                    {
                        "id": "comment-1",
                        "stageId": "REPORT",
                        "content": "跨工作流批注",
                        "artifactExcerpt": "摘要",
                        "createdAt": 1710000000000,
                    }
                ],
                "sectionLocks": [],
            },
            created_at_ms=1710000000999,
        )
