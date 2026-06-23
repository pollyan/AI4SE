# Alex PRD 质量评审与补全 Workflow 实施计划

## Milestone

把 Alex `PRD_REVIEW` 做成共享 Agent Runtime 上的在线 workflow，覆盖 manifest、前端入口、prompt/template、后端 contract、artifact_data renderer 和最小验证。

## 工作步骤

1. 补 RED 测试
   - 前端 workflow 配置测试断言 `PRD_REVIEW` 为 Alex 在线 workflow，slug 为 `prd-review`，4 个阶段 prompt/template 均存在。
   - 后端 workflow contract sync 测试新增 `PRD_REVIEW` prompt file 映射。
   - 后端 runtime/renderer 测试断言 `PRD_REVIEW` artifact_data 能被解析、渲染并通过 contract。

2. 同步 workflow 配置
   - 在 `tools/new-agents/workflow_manifest.json` 新增 `PRD_REVIEW`。
   - 在 `tools/new-agents/frontend/src/core/types.ts` 扩展 `WorkflowType`。
   - 在 `tools/new-agents/frontend/src/core/workflows.ts` 注册 4 个 prompt/template module。
   - 新增 `frontend/src/core/prompts/prd_review/*.ts`。

3. 同步后端 contract
   - 在 `agent_contracts.py` 增加 `PRD_REVIEW` stages、required headings、structured visuals。
   - 在 `test_workflow_contract_sync.py` 增加 prompt file 映射。

4. 实现 artifact_data 确定性渲染
   - 在 `artifact_data_renderers.py` 增加 PRD Review Pydantic schema、校验器、Markdown renderer。
   - 在 `agent_runtime.py` 增加 PRD_REVIEW artifact_data instruction、readiness stages 和 dispatch。
   - 确保 instruction 明确禁止完整 Markdown、Mermaid fenced block 和 ai4se-visual 直出。

5. 更新 todo 状态
   - 在 active todo 中记录本轮已把 Alex PRD 质量评审与补全作为完整 workflow 切片落地。
   - 保留其他 New Agents 增强项为后续候选。

6. 验证与提交
   - 运行 PRD_REVIEW 相关 frontend Vitest。
   - 运行 backend contract/runtime/renderer/deepseek readiness 最小 pytest。
   - 运行 `git diff --check`。
   - 验证通过后形成聚焦 commit。

## 回滚边界

本切片全部通过共享 manifest 和共享 renderer 接入。若验证失败，回滚新增 `PRD_REVIEW` manifest、prompt、contract、renderer 和测试文件即可，不影响现有 Lisa/Alex workflow。
