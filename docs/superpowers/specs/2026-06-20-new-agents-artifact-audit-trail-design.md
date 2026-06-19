# New Agents Artifact Audit Trail Design

## Current State Gap Analysis

Artifact 已支持人工保存、历史版本、批注、章节锁、回复、解决状态和服务端同步。但这些协作动作目前只改变最终状态，用户恢复历史 run 后只能看到“现在有什么”，看不到“最近发生了什么”。这会降低多人审阅、客户演示和问题追溯时的可信度。

候选能力包：

- 轻量服务端审阅轨迹：记录人工产物保存和协作状态更新，并随 run snapshot 返回，前端在历史面板展示最近活动。
- 完整审计日志：记录具体字段 diff、操作者身份、权限和 IP；当前系统没有完整身份体系，暂不展开。
- Artifact 三方 merge 轨迹：需要更复杂的合并语义，适合后续独立切片。

本轮选择轻量服务端审阅轨迹。

## User Story

作为 Lisa/Alex 工作区用户，当我恢复或审阅一个历史 run 时，我可以在 Artifact 历史面板看到最近的产物保存、批注/章节锁协作更新记录，从而理解这个产出物为何变成当前状态。

## Scope

- 后端新增 `AgentArtifactAuditEvent`，绑定 run 与 stage。
- `POST /api/agent/runs/<run_id>/artifacts` 成功保存人工产物时记录 `artifact_saved`。
- `PUT /api/agent/runs/<run_id>/artifact-collaboration` 成功替换协作状态时记录 `collaboration_updated`。
- `get_run_snapshot` 返回 `artifactAuditEvents`。
- 前端 snapshot service、store 和 ArtifactPane 历史面板支持展示当前阶段最近活动。
- 不新增 workflow-specific 或 agent-specific 审计分支。

## Non-Goals

- 不做权限、操作者身份、IP、设备信息。
- 不做逐字段 diff 或完整三方 merge 日志。
- 不为单个批注动作新增独立 endpoint。
- 不把审阅轨迹送入模型上下文。

## Acceptance

1. 人工保存 artifact 成功后，服务端 snapshot 返回 `artifact_saved` 活动。
2. 批注/章节锁协作状态同步成功后，服务端 snapshot 返回 `collaboration_updated` 活动。
3. 前端恢复 run snapshot 后，Artifact 历史面板能展示当前阶段的活动轨迹。
4. 切换阶段时只展示当前阶段活动。
5. 现有 artifact 保存、协作同步、历史版本、批注、章节锁测试不退化。

## Verification

- `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_run_persistence.py tools/new-agents/backend/tests/test_agent_endpoint.py`
- `npm run test -- --run src/services/__tests__/runSnapshotService.test.ts src/__tests__/store.test.ts src/components/__tests__/ArtifactPane.test.tsx`
- `npm run lint`
- `npm run build`
- `git diff --check`
