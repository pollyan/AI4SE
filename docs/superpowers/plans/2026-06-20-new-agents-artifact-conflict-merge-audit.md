# New Agents Artifact Conflict Merge Audit Plan

## Steps

1. 写 RED 测试：采纳冲突草稿行后，历史面板活动轨迹显示合并摘要。
2. Store 增加本地 `addArtifactAuditEvent` action，并测试事件归属当前 workflow stage。
3. ArtifactPane 在采纳/丢弃冲突草稿行时记录合并轨迹事件。
4. 运行目标组件和 store 测试，确认 RED 转 GREEN。
5. 运行 lint、build、diff check。
6. 更新 `docs/todos/new-agents-ux-professionalization.md` 进展记录。
