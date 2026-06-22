# New Agents 质量诊断合流设计

## 背景

`docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md` 将 E03 "Artifact 质量诊断面板" 标为 P0。当前已有独立分支 `codex/artifact-quality-diagnostics` 完成该能力:

- 新增 `tools/new-agents/frontend/src/core/artifactQuality.ts`。
- 在共享 `ArtifactPane` 审阅面板展示 headings、visual、stage gate、专业字段和现有 visual diagnostic 的通过/失败/警告。
- 补充 `artifactQuality.test.ts` 和 `ArtifactPane.test.tsx`。
- 更新 enhancement todo 与 spec/plan。

但最新 DeepSeek 结构化输出主线已经推进到 `codex/deepseek-prompt-boundary-hardening`，包含 `artifact_data` persistence、readiness gate、real smoke gate 和 prompt 边界去格式化。若 E03 继续停留在旧 `master` 基线，会让两个 P0 主线继续漂移。

## 目标

本轮目标是把 Artifact 质量诊断面板合流到最新 DeepSeek 结构化输出基线，形成一条同时包含 DS 可靠输出链路和 E03 用户可见质量诊断的候选主线。

验收结果:

1. 新分支从 `codex/deepseek-prompt-boundary-hardening` 起步。
2. 红灯检查证明 `codex/artifact-quality-diagnostics` 的补丁尚未合入。
3. 合入后保留 E03 的共享前端诊断能力，不引入 agent-specific runtime、API、store 或 renderer。
4. DeepSeek prompt/readiness/runtime/renderer 回归继续通过。
5. `docs/todos/` 能反映 E03 已在最新 DS 基线上完成合流。

## 非目标

- 不新增 E02 缺失信息清单。
- 不新增 E04 Lisa 测试资产质量闭环。
- 不新增 Alex STORY_BREAKDOWN 或 PRD_REVIEW workflow。
- 不直接合入主工作区 `master`，因为主工作区存在既有未提交改动。
- 不运行真实 DeepSeek 联网 smoke。

## 整合策略

采用 `git cherry-pick a74cff03` 将 E03 实现合入当前分支。若发生冲突:

- `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md` 保留 E03 已消化记录，同时不覆盖主工作区既有脏文件。
- `ArtifactPane.tsx` 保留共享审阅面板结构，质量诊断作为审阅面板的一部分，不新增独立 agent UI。
- `types.ts` 与现有 `ArtifactVisualDiagnostic` 状态兼容。
- `workflow_manifest.json` 不作为本轮修改点。

## 验收条件

- `tools/new-agents/frontend/src/core/artifactQuality.ts` 存在并由测试覆盖。
- `ArtifactPane` 审阅面板显示质量诊断摘要和缺口列表。
- E03 相关测试通过:
  - `src/core/__tests__/artifactQuality.test.ts`
  - `src/components/__tests__/ArtifactPane.test.tsx`
- 最新 DS prompt 边界测试继续通过:
  - `src/core/prompts/__tests__/buildSystemPrompt.test.ts`
- 前端 TypeScript 检查通过。
- 后端 DeepSeek 回归通过:
  - `test_deepseek_v4_readiness.py`
  - `test_agent_runtime.py`
  - `test_artifact_data_renderers.py`
- `git diff --check` 通过。

## 风险

- E03 分支基于旧 `master`，合入最新 DS 分支时文档 todo 可能冲突。解决原则是保留两条进展，不回滚 DS 记录。
- ArtifactPane 是共享高流量组件；本轮必须运行组件测试和 TypeScript 检查。
- 质量诊断当前是前端派生状态，不持久化。后续 E08 工作流质量评分可以在此基础上继续深化。
