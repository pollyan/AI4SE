# 技术债与重构工作列表

> 更新日期: 2026-06-25

## 当前清理结论

- `docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md` 和 `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md` 保留为历史诊断记录，不再作为当前活动入口。
- `docs/todos/refactor/` 当前不保留未消化活跃候选；具体入口以 `docs/todos/refactor/README.md` 为准。
- `docs/plans/2026-06-25-new-agents-agent-framework-phase1-phase2.md` 已作为 New Agents 智能体框架深化阶段 1-2 的正式路线图；后续只按其中单个 Story 启动独立目标模式工作。
- `docs/todos/archive/` 中保留的“待办”“剩余”“未完成”属于历史过程记录，不作为当前活动 todo 直接进入实现。
- 本文件下方 `New Agents 智能体重构完成记录` 仅作为已完成重构路线的证据索引；其中历史优先级不再表示当前未完成事项。
- 后续新增技术债时，应在对应条目补充现象、影响、验证入口和收束状态；已完成条目保留验证证据，但不要再作为活动入口使用。

## 2026-06-18 CI 与部署可信度加固

**现象**: 代码库审查发现 CI/部署护栏存在几个可信度缺口：New Agents 前端 CI 只跑 Vitest 未跑类型检查，critical flake8 在 workflow 中被 `|| true` 吞掉，生产 `.env` 写入 secrets 依赖 `sed -i` 替换且对特殊字符较脆，`scripts/ci/deploy.sh local` 指向不存在的 `docker-compose.yml`，并且 `tools/new-agents/tsconfig.tsbuildinfo` 仍被 Git 追踪。

**修复记录**:

- 2026-06-18: 新增 `tests/test_ci_deploy_hardening.py`，用文本回归测试保护 CI 类型检查、critical flake8 hard gate、生产 `.env` 同步策略、本地 compose 文件和 `.tsbuildinfo` Git 索引卫生。
- 2026-06-18: `.github/workflows/deploy.yml` 的 New Agents frontend job 增加 `npm run lint`，并移除 critical flake8 的 `|| true`。
- 2026-06-18: 生产部署步骤改为通过 `appleboy/ssh-action` 的 `envs` 传递受管 secrets，并用 `.env.managed` 重建受管变量，保留非受管 `.env` 行，最终 `mv` 原子替换并 `chmod 600 .env`。
- 2026-06-18: `scripts/ci/deploy.sh local/dev/development` 改用仓库实际存在的 `docker-compose.dev.yml`。
- 2026-06-18: `tools/new-agents/tsconfig.tsbuildinfo` 已从 Git 索引移除；本地文件仍由 `.gitignore` 的 `*.tsbuildinfo` 规则忽略。
- RED 验证: `.venv/bin/python -m pytest tests/test_ci_deploy_hardening.py -q`，修复前 5 个用例失败。
- 验证: `.venv/bin/python -m pytest -o addopts='' tests/test_ci_deploy_hardening.py -q`，5 passed。
- 验证: `bash -n scripts/ci/deploy.sh`，通过。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run test`，26 files / 293 tests passed。
- 验证: `cd tools/new-agents/backend && /Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest -m "not slow" -q`，175 passed / 1 deselected。
- 验证: `.venv/bin/python -m flake8 tools/intent-tester/backend --count --select=E9,F63,F7,F82 --show-source --statistics`，0。
- 备注: `docker compose -f docker-compose.dev.yml config --services` 在本机执行时未返回输出并被中断，未作为本轮完成证据。

## 2026-06-17 New Agents 当前功能性问题

### P0: 工作流无法正确流转到下一环节

**现象**: 用户确认或触发进入下一阶段后，工作流没有稳定切换到目标阶段，表现为阶段状态、右侧产出物或后续生成上下文没有按预期进入下一环节。

**影响**: 多阶段工作流无法形成完整闭环。`TEST_DESIGN`、`REQ_REVIEW`、`INCIDENT_REVIEW`、`IDEA_BRAINSTORM`、`VALUE_DISCOVERY` 这类依赖阶段推进的智能体流程都会受影响。

**当前疑似风险点**:

- 前端在收到 `NEXT_STAGE` 决策后会设置 `pendingStageTransition` 并停止继续消费当前流；如果同一个最终 chunk 同时带有当前阶段 artifact 更新，可能不会先落盘当前阶段最终产物。
- 阶段确认后通过固定提示词 `请继续生成当前阶段产出物` 继续生成，但阶段切换、artifact 恢复和下一阶段上下文拼装之间缺少端到端验证。
- 当前测试更多覆盖字段分离和待确认状态，缺少浏览器级验证：从阶段 A 生成完成、用户确认进入阶段 B、阶段 B 产出物正确生成并保存的完整闭环。

**后续修复要求**:

- 先补一个失败用例覆盖完整阶段流转闭环，至少验证 `stageIndex`、`artifactContent`、`stageArtifacts` 和下一次 Agent 请求的 `stageId/systemPrompt` 一致。
- 修复时保证进入下一阶段前先保存当前阶段最终 artifact，再切换阶段。
- 补充手动或 Playwright 冒烟脚本，覆盖真实 UI 的阶段确认按钮和右侧 artifact 切换。

**修复记录**:

- 2026-06-17: 修复 `NEXT_STAGE` chunk 先停止流导致当前阶段最终 artifact 未保存的问题；后续阶段 prompt 改为注入前序阶段 artifact 上下文。
- 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/agentCore.test.ts src/services/__tests__/chatService.test.ts src/core/prompts/__tests__/buildSystemPrompt.test.ts src/__tests__/p0-fixes.test.ts`，54 passed。
- 验证: `cd tools/new-agents/frontend && npm test`，25 files / 181 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；当时仍有既有大 chunk warning，已在下方独立性能债中修复。
- 2026-06-18: 补充前端 Agent Runtime 请求体集成测试，不 mock `buildSystemPrompt`，直接捕获 `/new-agents/api/agent/runs/stream` fetch body，验证确认进入下一阶段后的 `TEST_DESIGN/STRATEGY` 请求包含 `stageId: "STRATEGY"`，且 `systemPrompt` 带入 `阶段 [CLARIFY] 核心成果` 与前序 artifact 关键内容。
- 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llmSystemPromptIntegration.test.ts`，1 passed。
- 2026-06-18: 本地 `.venv` 已安装根 `requirements.txt` 与 Playwright Chromium，浏览器级 New Agents E2E gate 已形成可执行路径。确定性命令 `NEW_AGENTS_E2E_LLM_JUDGE=0 .venv/bin/python -m pytest -o addopts='' tests/e2e/new_agents_browser -m e2e -q` 通过，2 passed / 2 skipped；可选 LLM judge 仍必须显式提供稳定外部模型环境。

### P0: 旧标签协议泄漏到左侧聊天

**现象**: 结构化 Agent Runtime 返回的 `chat` 字段如果包含 `<CHART>...</CHART>`、`<ARTIFACT>...</ARTIFACT>` 或 `<CHAT>...</CHAT>` 这类旧标签协议，前端会把它当作普通助手消息渲染在左侧聊天区。用户可见表现是左侧对话出现本应属于协议/产出物通道的标记和内容，例如 `<CHART>我已经在右侧生成了《需求分析文档》框架。</CHART>`。

**影响**: 左侧 chat 与右侧 artifact 的职责边界被破坏。用户会看到内部协议标记或产出物通道内容，误以为助手回复和右侧文档重复或串位。

**已确认根因**:

- 后端 `AgentTurnOutput.chat` 原先只拦截 Markdown 标题、表格、代码块和 Mermaid 片段，没有把 `<CHART>/<ARTIFACT>/<CHAT>` 旧标签协议列为非法输出。
- 前端 typed SSE 解析只校验 `chat` 是否为非空字符串，没有在协议边界拒绝旧标签污染。

**修复记录**:

- 2026-06-18: 后端契约新增旧标签协议校验，`chat` 字段一旦包含 `<CHART>`、`<ARTIFACT>` 或 `<CHAT>` 标签直接抛出契约错误，不剥离、不静默降级。
- 2026-06-18: 前端 typed SSE 解析同步拒绝旧标签协议，防止异常 payload 绕过后端后被渲染到左侧聊天。
- 2026-06-18: 结构化产出物契约 prompt 明确禁止 chat 包含 `<CHART>/<ARTIFACT>/<CHAT>` 旧标签协议。
- RED 验证: `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_contracts.py -q`，修复前 4 个旧标签用例失败。
- RED 验证: `cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/llm.test.ts -t "旧标签协议"`，修复前失败，`<CHART>...` 被作为 `chatResponse` 返回。
- 验证: `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_contracts.py -q`，62 passed。
- 验证: `cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/llm.test.ts -t "旧标签协议"`，1 passed。
- 验证: `./scripts/test/test-local.sh new-agents`，前端 26 files / 293 tests passed，后端 175 passed / 1 deselected。

### P1: 后续阶段产物会被误注入较早阶段 Prompt 上下文

**现象**: 当 `stageArtifacts` 中已经存在后续阶段产物时，用户回到较早阶段继续生成或从持久化状态恢复后，`buildSystemPrompt()` 会把后续阶段 artifact 也写入“前序阶段有效结论摘要”。

**影响**: Agent 在 `STRATEGY` 等中间阶段可能提前看到 `CASES`、`DELIVERY` 这类未来阶段内容，导致阶段边界被污染，生成结果不再只基于真实前序上下文。

**已确认根因**:

- 前端 Prompt 构造只排除了当前阶段 `stageId`，没有按当前 workflow 的 stage 顺序过滤 index 小于当前阶段的真实前序阶段。

**修复记录**:

- 2026-06-18: `buildSystemPrompt()` 改为从当前 workflow 的 `stages.slice(0, stageIndex)` 中选择前序阶段 artifact；未来阶段、当前阶段和未知阶段 artifact 不再注入“前序阶段有效结论摘要”。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/core/prompts/__tests__/buildSystemPrompt.test.ts -t "does not inject future stage artifacts"`，修复前失败，输出显示 `阶段 [CASES] 核心成果` 和 `未来阶段用例内容` 被注入 STRATEGY prompt。
- 验证: `cd tools/new-agents/frontend && npm test -- src/core/prompts/__tests__/buildSystemPrompt.test.ts -t "does not inject future stage artifacts"`，1 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/core/prompts/__tests__/buildSystemPrompt.test.ts`，14 passed。

### P1: 前序阶段 `<mark>` 高亮标签污染下一阶段 Prompt

**现象**: `buildSystemPrompt()` 会清理当前 artifact 中用于 UI 高亮的 `<mark>` 标签，但前序阶段上下文直接注入 `stageArtifacts[stage.id]`。如果前一阶段产物保存了 `<mark>登录链路</mark>`，下一阶段 Agent 会看到 UI 标记，而不是干净的业务内容。

**影响**: 阶段 B 的 prompt 被阶段 A 的渲染标记污染，模型可能学习或扩散 `<mark>` 包裹过的旧内容，削弱多阶段工作流的上下文质量。

**修复记录**:

- 2026-06-18: `buildSystemPrompt()` 抽出 `removeMarkTags(...)`，复用于当前 artifact 和前序阶段 artifact；前序上下文保留标签内文本，但不再包含 `<mark>` / `</mark>`。
- RED 验证: `cd tools/new-agents/frontend && npm run test -- src/core/prompts/__tests__/buildSystemPrompt.test.ts -t "removes mark tags from previous stage artifacts while preserving marked text"`，修复前失败，前序上下文仍包含 `已确认 <mark>登录链路</mark> 的核心边界`。
- 验证: `cd tools/new-agents/frontend && npm run test -- src/core/prompts/__tests__/buildSystemPrompt.test.ts -t "removes mark tags from previous stage artifacts while preserving marked text"`，1 passed。
- 验证: `cd tools/new-agents/frontend && npm run test -- src/core/prompts/__tests__/buildSystemPrompt.test.ts`，15 passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `git diff --check -- tools/new-agents/frontend/src/core/prompts/buildSystemPrompt.ts tools/new-agents/frontend/src/core/prompts/__tests__/buildSystemPrompt.test.ts docs/plans/tech-debt.md AGENTS.md docs/strategy/goal-mode-playbook.md`，通过。

### P1: Legacy 阶段切换会把来源产物复制到目标阶段

**现象**: 旧兼容 action `transitionToNextStage(initialStageId, initialArtifact)` 会先把 `initialArtifact` 保存回来源阶段，然后又把当前 `artifactContent` 写入 `stageArtifacts[nextStageId]`，并保持 `artifactContent` 不变。若当前内容是 `CLARIFY` 最终文档，切到 `STRATEGY` 后右侧仍显示并保存上一阶段内容。

**影响**: 即使主路径已经有确认门禁，旧入口仍可能污染下一阶段当前产物，造成“工作流已进入下一环节但产物仍停留在上一阶段”的功能性问题。

**修复记录**:

- 2026-06-18: `transitionToNextStage()` 只把 `initialArtifact` 保存回来源阶段，不再写入 `nextStageId`；进入下一阶段后，`artifactContent` 取目标阶段已有产物，没有则使用既有占位格式 `# 阶段名\n\n暂无产出物。`。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/__tests__/store.test.ts -t "should not reuse the source artifact as the next stage artifact during legacy transitions"`，修复前失败，`artifactContent` 仍等于 `# Clarify-only artifact...`。
- 验证: `cd tools/new-agents/frontend && npm test -- src/__tests__/store.test.ts -t "should not reuse the source artifact as the next stage artifact during legacy transitions"`，1 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/__tests__/store.test.ts`，17 passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `git diff --check -- tools/new-agents/frontend/src/store.ts tools/new-agents/frontend/src/__tests__/store.test.ts`，通过。
- 当前限制: `transitionToNextStage` 生产调用点当前只剩 store 实现和类型暴露，UI/service 层未发现直接调用；该修复保留旧 action 而非删除，降低兼容风险。

### P1: Legacy 阶段切换成功后派生状态残留

**现象**: 旧兼容 action `transitionToNextStage(...)` 成功推进阶段后，只更新 `stageIndex`、`stageArtifacts` 和 `artifactContent`，没有像 `setStageIndex()` 一样清理 `pendingStageTransition`、`artifactTruncated` 和 `isGenerating`。

**影响**: 旧入口推进到下一阶段后，聊天区仍可能保留上一轮确认卡片，右侧产物继续显示旧截断警告，发送入口也可能保持生成中状态，形成“阶段已切换但 UI 派生状态仍属于旧阶段”的错位。

**修复记录**:

- 2026-06-18: `transitionToNextStage(...)` 成功推进阶段时同步设置 `pendingStageTransition: null`、`artifactTruncated: false`、`isGenerating: false`，与手动阶段切换的派生状态清理语义保持一致。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/__tests__/store.test.ts -t "should clear derived workflow state when legacy next-stage transition advances"`，修复前失败，`pendingStageTransition` 仍为 `{ fromStageIndex: 0, toStageIndex: 1 }`。
- 验证: `cd tools/new-agents/frontend && npm test -- src/__tests__/store.test.ts -t "should clear derived workflow state when legacy next-stage transition advances"`，1 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/__tests__/store.test.ts`，19 passed。
- 验证: `git diff --check -- tools/new-agents/frontend/src/store.ts tools/new-agents/frontend/src/__tests__/store.test.ts`，通过。

### P1: 错误和停止控制反馈会污染下一轮 Runtime Prompt

**现象**: 流式错误反馈和用户停止反馈会作为 assistant 消息写入聊天历史；`buildRuntimePrompt()` 原先会把所有历史消息拼入下一次结构化 Agent Runtime prompt，导致 `**Error:** LLM_ERROR`、`*(已停止生成)*` 这类 UI 控制反馈被模型看到。

**影响**: 下一轮 Agent 可能把 UI 错误状态当成业务上下文，误判用户意图或复述内部错误信息，降低多轮对话的上下文质量。

**修复记录**:

- 2026-06-18: `buildRuntimePrompt()` 在拼接历史前过滤 assistant 角色且内容以 `**Error:**` 或 `*(已停止生成)*` 开头的控制反馈；普通用户消息和普通助手回复仍会进入 prompt。
- 2026-06-18: 继续补强中途追加控制反馈场景。过滤规则改为识别 assistant 消息任意行开头的 `**Error:**`、`*(已停止生成)*` 和 `⚠️ **模型额度或限流异常**`，避免“正在生成...”后追加的错误、停止或 quota 提示污染下一轮 prompt。
- RED 验证: `cd tools/new-agents/frontend && npm test -- --run src/core/__tests__/llm.test.ts -t "不应将错误或停止控制反馈注入到结构化 runtime prompt 中"`，修复前失败，prompt 中仍包含 `**Error:** LLM_ERROR`、`请求失败` 和 `*(已停止生成)*`。
- 验证: `cd tools/new-agents/frontend && npm test -- --run src/core/__tests__/llm.test.ts -t "不应将错误或停止控制反馈注入到结构化 runtime prompt 中"`，1 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- --run src/core/__tests__/llm.test.ts`，51 passed。
- RED 验证: `cd tools/new-agents/frontend && npm test -- --run src/core/__tests__/llm.test.ts -t "不应将错误或停止控制反馈注入"`，补强前失败，prompt 中仍包含 `流式中途失败`、`已停止生成` 和 `模型额度或限流异常`。
- 验证: `cd tools/new-agents/frontend && npm test -- --run src/core/__tests__/llm.test.ts -t "不应将错误或停止控制反馈注入"`，1 passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `git diff --check -- tools/new-agents/frontend/src/core/llm.ts tools/new-agents/frontend/src/core/__tests__/llm.test.ts`，通过。
- 当前限制: 过滤规则只覆盖当前 UI 已知的错误、停止和 quota 文案；未来如果新增控制反馈格式，需要补充同类回归测试。

### P1: Artifact 历史版本跨阶段混在当前阶段弹窗里

**现象**: `artifactHistory` 原先是全局列表，`ArtifactVersion` 没有 `stageId`，`ArtifactPane` 历史弹窗直接展示全量历史。用户在 `STRATEGY` 阶段打开历史版本时，也会看到 `CLARIFY` 阶段版本。

**影响**: 多阶段产物的版本边界不清晰，用户可能从当前阶段恢复或查看上一阶段文档，造成阶段产物混用。

**修复记录**:

- 2026-06-18: `ArtifactVersion` 增加 `stageId`，store 的 `addArtifactVersion(...)` 会为未显式传入 stageId 的新增版本补当前阶段 ID；`chatService` 保存运行产物历史时显式传入 run 开始时的 `runStageId`。
- 2026-06-18: persisted hydrate 会丢弃无 `stageId` 的旧 artifact history，不回退到全局展示；这是为了避免旧版本继续跨阶段污染当前阶段历史。
- 2026-06-18: `ArtifactPane` 按当前 workflow/stageIndex 计算当前阶段 ID，只展示当前阶段版本，默认选中当前阶段最新版本，版本号基于过滤后列表。
- RED 验证: `cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "only lists history versions for the current workflow stage"`，修复前失败，`CLARIFY version` 仍出现在 `STRATEGY` 阶段历史弹窗。
- RED 验证: `cd tools/new-agents/frontend && npm run test -- --run src/__tests__/store.test.ts -t "should stamp artifact versions with the current stage id"`，修复前失败，新增 artifact version 没有 `stageId: STRATEGY`。
- 验证: `cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "only lists history versions for the current workflow stage"`，1 passed。
- 验证: `cd tools/new-agents/frontend && npm run test -- --run src/__tests__/store.test.ts -t "should stamp artifact versions with the current stage id"`，1 passed。
- 验证: `cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx src/__tests__/store.test.ts src/services/__tests__/chatService.test.ts src/core/__tests__/agentCore.test.ts`，4 files / 85 tests passed。
- 验证: `cd tools/new-agents/frontend && npm test`，26 files / 278 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `git diff --check -- tools/new-agents/frontend/src/core/types.ts tools/new-agents/frontend/src/store.ts tools/new-agents/frontend/src/services/chatService.ts tools/new-agents/frontend/src/components/ArtifactPane.tsx tools/new-agents/frontend/src/__tests__/store.test.ts tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx tools/new-agents/frontend/src/services/__tests__/chatService.test.ts tools/new-agents/frontend/src/core/__tests__/agentCore.test.ts`，通过。
- 当前限制: 旧 persisted artifact history 如果没有 `stageId` 会被丢弃；这会牺牲旧历史可见性，但避免继续把无阶段归属的历史展示给任意阶段。

### P0: 默认 LLM 配置缺少可靠首次部署初始化路径

**现象**: 当前主 Agent 调用依赖后端 `llm_config.default`，但前端设置页只展示说明，后端只提供 `GET /api/config`。首次部署如果数据库里没有默认配置，用户会卡在“后端默认 LLM 未配置”，无法通过 UI 或现有维护脚本完成配置。

**影响**: 新环境无法直接启动 Agent Runtime。`/api/agent/runs/stream` 和 Mermaid 修复端点都会因为默认 LLM 配置缺失返回 503。

**已确认根因**:

- `scripts/migrate_llm_config_prod.sh` 导入 `init_db`，但 `tools/new-agents/backend/app.py` 原先没有定义该函数，脚本不可执行。
- Docker Compose 没有把 New Agents 默认 LLM 的 API Key、Base URL、模型名注入 `new-agents-backend`。
- `config_service.py` 只负责查询和公开脱敏 payload，没有从部署环境创建或更新 `llm_config.default` 的能力。

**修复记录**:

- 2026-06-17: 新增 `upsert_default_llm_config_from_env()`，支持通过 `NEW_AGENTS_DEFAULT_LLM_API_KEY`、`NEW_AGENTS_DEFAULT_LLM_BASE_URL`、`NEW_AGENTS_DEFAULT_LLM_MODEL`、`NEW_AGENTS_DEFAULT_LLM_DESCRIPTION` 创建/更新并启用 `llm_config.default`；API Key 仍只保存在后端数据库，不进入 `/api/config` 响应。
- 2026-06-17: 恢复 `init_db(app)` 支持入口，应用启动建表后会尝试环境变量初始化默认 LLM 配置；生产迁移脚本改为调用 `init_db(app)`。
- 2026-06-17: `docker-compose.dev.yml`、`docker-compose.dev-cn.yml`、`docker-compose.prod.yml` 已透传 `NEW_AGENTS_DEFAULT_LLM_*` 环境变量。
- 2026-06-17: 修正 Compose 变量落点，`NEW_AGENTS_DEFAULT_LLM_*` 从 `intent-tester` 移到实际读取配置的 `new-agents-backend` 服务。
- 2026-06-17: 修正默认 LLM 缺失错误文案，不再提示用户去已移除的前端个人 API Key 设置，改为提示维护后端默认 LLM 配置。
- 2026-06-17: 更新首次使用 onboarding 提示，明确可通过 `NEW_AGENTS_DEFAULT_LLM_API_KEY` 与 `NEW_AGENTS_DEFAULT_LLM_MODEL` 初始化后端默认配置。
- 2026-06-18: 修复 `Workspace` 默认 LLM 配置检查的异步竞态；如果旧 `/new-agents/api/config` 请求在用户已经开始对话后才返回，不再显示陈旧的“后端默认 LLM 未配置”遮罩。
- 2026-06-18: 收紧 `Workspace` 对 `/new-agents/api/config` 响应的契约判断，只有 `hasDefault === true` 才隐藏 onboarding；字符串 `"false"` 等畸形 truthy 值会按未配置处理。
- 测试: 已新增后端 pytest 用例覆盖环境变量创建、更新并重新启用、缺必填项不写入、`init_db(app)` 初始化配置。
- 测试: 已更新后端响应契约测试、Agent endpoint 测试和 route guard 测试，覆盖新的默认 LLM 缺失文案。
- 测试: 已更新 `Workspace` 页面测试，覆盖默认 LLM 缺失时 UI 展示环境变量配置入口。
- 测试: 已更新 `Workspace` 页面测试，覆盖配置检查挂起期间用户开始对话，旧请求返回 `hasDefault: false` 后不会重新显示 onboarding。
- 测试: 已更新 `Workspace` 页面测试，覆盖配置响应返回字符串等畸形 truthy `hasDefault` 值时仍显示默认 LLM 未配置 onboarding。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/pages/__tests__/Workspace.test.tsx -t "shows onboarding overlay when backend config response has malformed hasDefault"`，修复前失败输出显示页面没有渲染 `后端默认 LLM 未配置`。
- 验证: `cd tools/new-agents/frontend && npm test -- src/pages/__tests__/Workspace.test.tsx -t "shows onboarding overlay when backend config response has malformed hasDefault"`，1 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/pages/__tests__/Workspace.test.tsx`，5 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/pages/__tests__/Workspace.test.tsx src/components/__tests__/SettingsModal.test.tsx src/services/__tests__/chatService.test.ts`，3 files / 43 tests passed。
- 验证: `cd tools/new-agents/frontend && npm test`，25 files / 227 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；主入口 chunk 334.69 kB，large chunk warning 未回归。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/pages/__tests__/Workspace.test.tsx -t "does not show stale onboarding when config check resolves after chat starts"`，修复前失败输出显示页面仍渲染 `后端默认 LLM 未配置`。
- 验证: `cd tools/new-agents/frontend && npm test -- src/pages/__tests__/Workspace.test.tsx -t "does not show stale onboarding when config check resolves after chat starts"`，1 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/pages/__tests__/Workspace.test.tsx`，4 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/pages/__tests__/Workspace.test.tsx src/components/__tests__/ChatPane.test.tsx src/services/__tests__/chatService.test.ts src/__tests__/store.test.ts`，4 files / 52 tests passed。
- 验证: `cd tools/new-agents/frontend && npm test`，25 files / 226 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；主入口 chunk 334.68 kB，large chunk warning 未回归。
- 验证: `/Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m py_compile tools/new-agents/backend/config_service.py tools/new-agents/backend/app.py tools/new-agents/backend/tests/test_config_service.py tools/new-agents/backend/tests/test_api.py`，通过。
- 验证: `/Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m py_compile tools/new-agents/backend/api_responses.py tools/new-agents/backend/tests/test_api_responses.py tools/new-agents/backend/tests/test_agent_endpoint.py tools/new-agents/backend/tests/test_route_guards.py`，通过。
- 验证: `rg "请在设置中配置您自己的 API Key|自己的 API Key" tools/new-agents/backend tools/new-agents/frontend/src docs/plans/tech-debt.md`，无命中。
- 验证: `cd tools/new-agents/frontend && npm test -- src/pages/__tests__/Workspace.test.tsx`，3 passed。
- 验证: `cd tools/new-agents/frontend && npm test`，25 files / 186 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；当时仍有既有大 chunk warning，已在下方独立性能债中修复。
- 验证: `bash -n scripts/migrate_llm_config_prod.sh`，通过。
- 验证: `rg "NEW_AGENTS_DEFAULT_LLM" docker-compose.dev.yml docker-compose.dev-cn.yml docker-compose.prod.yml tools/new-agents/backend tools/new-agents/backend/tests scripts/migrate_llm_config_prod.sh`，三套 Compose、后端实现和测试均命中。
- 2026-06-18: 本地 `.venv` 已安装 `tools/new-agents/backend/requirements.txt`，New Agents 后端确定性 pytest gate 已打通。验证: `cd tools/new-agents/backend && /Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest -m "not slow" -q`，171 passed / 1 deselected。

### P1: 阶段确认后的内部续写提示污染聊天历史

**现象**: 用户在阶段确认卡片中确认进入下一阶段后，`handleConfirmStageTransition()` 通过 `handleSend('请继续生成当前阶段产出物')` 继续生成下一阶段内容。由于复用了普通用户发送路径，这条内部控制提示会以 `role: user` 写入 `chatHistory` 并显示在对话中。

**影响**: 用户会看到自己并未输入的内部提示词，后续 Agent Runtime prompt 也会把这条控制提示当作真实用户历史，污染多阶段工作流上下文。

**修复记录**:

- 2026-06-17: `handleSend()` 增加 `appendUserMessage` 选项，普通用户发送默认保持原行为；阶段确认续写调用 `appendUserMessage: false`，Agent Runtime 仍收到续写 prompt，但 UI 历史不再追加内部用户消息。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts -t "should confirm pending stage transition through the service and continue generation"`，修复前失败输出显示 `chatHistory` 中存在 `role: "user", content: "请继续生成当前阶段产出物"`。
- 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts -t "should confirm pending stage transition through the service and continue generation"`，1 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts`，15 passed。
- 验证: `cd tools/new-agents/frontend && npm test`，25 files / 201 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；主入口 chunk 保持 334.41 kB，large chunk warning 未回归。

### P1: 阶段确认内部续写后的重试会回退上一条真实用户输入

**现象**: 阶段确认续写已经不再追加内部 user 消息，但它生成的最后一条 assistant 消息仍和普通用户回合的 assistant 消息一样显示“重试”。用户点击该按钮时，`planRetryFromHistory()` 会向前找到上一条真实 user 消息，通常是上一阶段的原始需求输入，并把它恢复到输入框。

**影响**: 工作流已进入下一阶段后，重试会把用户带回上一阶段语义，容易重新提交旧阶段输入，污染当前阶段上下文；服务层直接调用 `handleRetry()` 时也会删除内部续写消息并回滚聊天历史。

**修复记录**:

- 2026-06-18: `Message` 增加可选 `retryable` 元数据；阶段确认内部续写通过 `appendUserMessage: false` 生成的 assistant 消息标记为 `retryable: false`，普通用户回合保持默认可重试语义。
- 2026-06-18: `ChatPane` 不再为 `retryable: false` 的最后一条 assistant 消息展示“重试”；`planRetryFromHistory()` 遇到最新 assistant 不可重试时直接返回 `null`，防止绕过 UI 的服务层调用误回退。
- 2026-06-18: 持久化聊天历史清洗保留布尔 `retryable` 字段，刷新后不可重试语义不丢失。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/agentCore.test.ts src/components/__tests__/ChatPane.test.tsx src/services/__tests__/chatService.test.ts src/__tests__/store.test.ts`，修复前 5 个用例失败，分别覆盖 retry plan、UI 按钮、内部续写标记、直接调用 `handleRetry()` 和 hydrate 元数据保留。
- 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/agentCore.test.ts src/components/__tests__/ChatPane.test.tsx src/services/__tests__/chatService.test.ts src/__tests__/store.test.ts`，4 files / 99 tests passed。

### P1: 过期阶段确认状态会把工作区回退到旧目标阶段

**现象**: `planStageTransitionConfirmation()` 原先只校验 pending transition 的目标阶段是否存在，不校验当前 `stageIndex` 是否仍等于 pending 的来源阶段。如果 pending 是从阶段 0 发起，但用户或其他状态变更已经让工作区处于阶段 2，再调用确认会把 `stageIndex` 回退到 pending 的旧目标阶段 1。

**影响**: 过期确认状态可能造成阶段回退、右侧产出物切换到错误阶段，并污染后续 Agent Runtime 的 `stageId/systemPrompt` 上下文。

**修复记录**:

- 2026-06-17: `planStageTransitionConfirmation()` 在确认前校验 `stageIndex === pendingTransition.fromStageIndex`；不匹配时只清除 pending transition，不推进阶段、不保存当前 artifact 到旧来源阶段。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/agentCore.test.ts -t "clears stale pending transition"`，修复前失败输出显示返回计划包含 `stageIndex: 1` 和目标阶段 artifact。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/__tests__/p0-fixes.test.ts -t "stale pending"`，修复前失败输出显示 `stageIndex` 从 2 回退到 1。
- 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/agentCore.test.ts -t "clears stale pending transition"`，1 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/__tests__/p0-fixes.test.ts -t "stale pending"`，1 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/agentCore.test.ts src/__tests__/p0-fixes.test.ts src/services/__tests__/chatService.test.ts`，3 files / 43 tests passed。
- 验证: `cd tools/new-agents/frontend && npm test`，25 files / 201 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；主入口 chunk 334.45 kB，large chunk warning 未回归。

### P1: 畸形阶段确认状态可跳过或倒退阶段

**现象**: `planStageTransitionConfirmation()` 原先只校验 pending transition 的来源阶段等于当前阶段、目标阶段存在，但不校验目标是否为来源阶段的紧邻下一阶段。如果持久化状态、旧事件处理器或外部调用写入 `{ fromStageIndex: 0, toStageIndex: 2 }` 或 `{ fromStageIndex: 1, toStageIndex: 0 }`，确认后会跳过阶段或倒退阶段。

**影响**: 阶段确认卡片可能破坏多阶段工作流顺序，导致 `stageIndex`、右侧产物和下一轮 Agent Runtime `stageId/systemPrompt` 上下文不一致。

**修复记录**:

- 2026-06-18: `planStageTransitionConfirmation()` 增加相邻性校验，只允许 `toStageIndex === fromStageIndex + 1`；非相邻 pending transition 只清除 pending，不推进阶段、不保存产物。
- 测试: 已更新 `agentCore.test.ts`，覆盖跳过阶段和倒退阶段两个畸形 pending transition。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/agentCore.test.ts -t "target is not the immediate next stage"`，修复前失败输出显示返回计划包含 `stageIndex: 2` 和目标阶段占位产物。
- 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/agentCore.test.ts -t "target is not the immediate next stage"`，1 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/agentCore.test.ts`，17 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/agentCore.test.ts src/__tests__/store.test.ts src/services/__tests__/chatService.test.ts src/__tests__/p0-fixes.test.ts`，4 files / 87 tests passed。
- 验证: `cd tools/new-agents/frontend && npm test`，26 files / 269 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；主入口 chunk 336.59 kB，large chunk warning 未回归。

### P1: 过期阶段确认被清除后仍触发内部续写

**现象**: 状态层修复过期 pending transition 后，`confirmStageTransition()` 会在来源阶段不匹配时只清除 pending 而不推进阶段。但 `handleConfirmStageTransition()` 仍会继续调用 `handleSend('请继续生成当前阶段产出物', ...)`，导致没有实际进入目标阶段也会发起一次内部 Agent Runtime 请求。

**影响**: 用户确认一个已经过期的阶段卡片时，工作区虽然不会回退，但仍可能在当前阶段生成无关回复或覆盖当前 artifact；同时会产生一次不必要的模型调用。

**修复记录**:

- 2026-06-17: `handleConfirmStageTransition()` 在确认前记录 pending 的目标阶段，确认后重新读取 store；只有当前 `stageIndex` 确实进入目标阶段时才触发内部续写，否则直接返回。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts -t "should not continue generation when confirming a stale stage transition"`，修复前失败输出显示 `generateResponseStream` 被调用一次，参数包含 `请继续生成当前阶段产出物`。
- 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts -t "should not continue generation when confirming a stale stage transition"`，1 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts`，17 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/agentCore.test.ts src/__tests__/p0-fixes.test.ts src/services/__tests__/chatService.test.ts`，3 files / 45 tests passed。
- 验证: `cd tools/new-agents/frontend && npm test`，25 files / 204 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；主入口 chunk 334.45 kB，large chunk warning 未回归。

### P1: 阶段确认内部续写误消费用户草稿附件

**现象**: 阶段确认后，`handleConfirmStageTransition()` 复用 `handleSend(STAGE_CONTINUATION_PROMPT, ...)` 触发下一阶段续写。即使不再追加内部 user 消息，`handleSend()` 仍会读取当前 `pendingAttachments`，把用户为下一条真实输入准备的草稿附件传给内部续写请求，并清空附件列表。

**影响**: 内部续写 prompt 会携带无关附件污染 Agent Runtime 上下文；用户刚选好的草稿附件也会从输入区消失，造成数据丢失感。

**修复记录**:

- 2026-06-17: `handleSend()` 增加 `useDraftAttachments` 选项。普通用户发送默认继续消费并清空草稿附件；阶段确认内部续写使用 `useDraftAttachments: false`，不读取也不清空用户草稿附件。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts -t "should not send or clear draft attachments"`，修复前失败输出显示 `generateResponseStream` 收到了 `draft.md` 附件。
- 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts -t "should not send or clear draft attachments"`，1 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts`，16 passed。
- 验证: `cd tools/new-agents/frontend && npm test`，25 files / 203 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；主入口 chunk 334.45 kB，large chunk warning 未回归。

### P1: `PROXY_API_KEY` 认证与浏览器主链路不匹配

**现象**: 后端在设置 `PROXY_API_KEY` 时要求 `/api/agent/runs/stream` 和 `/api/utils/mermaid/repair` 的 POST 请求携带 `X-API-Key`。当前 React 前端调用 `/new-agents/api/agent/runs/stream` 和 `/new-agents/api/utils/mermaid/repair` 时只发送 `Content-Type`，Nginx 也没有注入 `X-API-Key`。

**影响**: 一旦部署环境设置 `PROXY_API_KEY`，主 Agent 对话和 Mermaid 修复都会返回 401，用户侧表现为智能体不可用。

**修复记录**:

- 2026-06-17: 采用“后端端口不对外暴露 + Nginx 注入内部网关标记”的方案。浏览器仍只访问 `/new-agents/api/...`，不接触 `PROXY_API_KEY`。
- 2026-06-17: `nginx/nginx.conf` 在 `/new-agents/api/` 代理块注入 `X-AI4SE-Gateway: new-agents`。
- 2026-06-17: 后端认证层接受正确 `X-API-Key` 或可信内部网关标记；错误网关标记、无 Key 直连请求仍返回 401。
- 2026-06-17: `docker-compose.dev.yml`、`docker-compose.dev-cn.yml` 移除 `new-agents-backend` 的宿主机 `5002:5002` 映射；生产环境原本未暴露该端口。
- 2026-06-17: `PROXY_API_KEY` 只注入 `new-agents-backend`，未进入前端源码或前端容器。
- 测试: 新增后端 pytest 用例覆盖网关注入头放行、Mermaid 修复端点放行、错误网关标记不绕过认证。
- 验证: `/Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m py_compile tools/new-agents/backend/app.py tools/new-agents/backend/tests/test_api_auth.py`，通过。
- 验证: `rg "X-AI4SE-Gateway|PROXY_API_KEY|NEW_AGENTS_DEFAULT_LLM" nginx/nginx.conf docker-compose.dev.yml docker-compose.dev-cn.yml docker-compose.prod.yml tools/new-agents/backend/app.py tools/new-agents/backend/tests/test_api_auth.py tools/new-agents/frontend/src`，前端源码无 `PROXY_API_KEY` 命中。
- 验证: `docker compose -f docker-compose.dev.yml config --services`、`docker compose -f docker-compose.dev-cn.yml config --services`、`docker compose -f docker-compose.prod.yml config --services`，三套 Compose 均可渲染；dev/dev-cn 仅有既有 `version` obsolete warning。
- 验证: `docker compose -f docker-compose.dev.yml config new-agents-backend`、`docker compose -f docker-compose.dev-cn.yml config new-agents-backend`、`docker compose -f docker-compose.prod.yml config new-agents-backend`，`new-agents-backend` 包含 `NEW_AGENTS_DEFAULT_LLM_*` 和 `PROXY_API_KEY`，且无宿主机端口映射。
- 当前限制: 本机后端 pytest 运行器仍不可用；本机无 `nginx` 命令且 Docker API 权限不足，未执行 `nginx -t`。

### P1: 非法 workflow/stage 请求进入 Agent Runtime 流式通道

**现象**: `/api/agent/runs/stream` 只校验 `workflowId` 和 `stageId` 非空，不校验它们是否存在或是否归属于同一个工作流。明显非法的 `workflowId=UNKNOWN_WORKFLOW` 或 `TEST_DESIGN/REPORT` 会通过请求解析，后续才在 runtime 或产物契约构建中暴露。

**影响**: 非法请求可能先构建 PydanticAI runtime，甚至在没有产物契约 prompt 的情况下调用模型；调用方也会收到 200 SSE typed error，而不是明确的 HTTP 400 请求错误。

**修复记录**:

- 2026-06-17: `parse_agent_run_stream_request()` 复用后端 `WORKFLOW_STAGES` 契约，前置拒绝未知 workflow 和 workflow/stage 错配请求。
- 2026-06-17: 解析时同步归一化 `workflowId` / `stageId` 前后空白，避免校验使用 strip 后返回对象仍携带空格并在 runtime 再次失败。
- 2026-06-17: 认证测试中的 Agent Runtime 请求体改为合法 `TEST_DESIGN/CLARIFY`，避免认证测试用 400 掩盖“不是 401”的测试意图。
- 测试: 新增 request schema 测试覆盖未知 workflow、workflow/stage 错配和 ID 空白归一化；新增 API 层测试覆盖错配请求返回 400 且不构建 runtime。
- 验证: `PYTHONPATH=tools/new-agents/backend /Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -c "..."`，合法 `TEST_DESIGN/CLARIFY` 通过，带空白 ID 归一化为规范值，未知 workflow 和错配 stage 均被 `RequestValidationError` 拒绝。
- 验证: `/Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m py_compile tools/new-agents/backend/request_schemas.py tools/new-agents/backend/tests/test_request_schemas.py tools/new-agents/backend/tests/test_agent_endpoint.py tools/new-agents/backend/tests/test_api_auth.py`，通过。
- 验证: `rg -n '"workflowId": "workflow"|"stageId": "stage"' tools/new-agents/backend/tests/test_api_auth.py tools/new-agents/backend/tests/test_agent_endpoint.py tools/new-agents/backend/tests/test_request_schemas.py`，无命中。
- 当前限制: bundled Python 缺少 `pytest`，本机后端 pytest 仍未实际执行。

### P1: 非对象 JSON 请求体会绕过请求校验并触发 500

**现象**: `/api/agent/runs/stream` 和 `/api/utils/mermaid/repair` 的 parser 假设 `request.get_json()` 一定返回 dict。请求体如果是非空 JSON 数组或字符串，代码会继续调用 `data.get(...)`，抛出 `AttributeError`。

**影响**: 明显非法的客户端请求不会在请求边界返回 HTTP 400，而是冒泡成服务端 500。用户侧会看到不可诊断的智能体或 Mermaid 修复失败，服务端日志也会混入非业务异常。

**修复记录**:

- 2026-06-18: 新增 `_ensure_request_object(...)`，两个 parser 在读取字段前统一区分空请求体、非对象 JSON 和合法对象；非对象 JSON 统一抛出 `RequestValidationError("请求体必须是 JSON 对象")`。
- 2026-06-18: `test_request_schemas.py` 增加 Agent Runtime 与 Mermaid 修复两个 parser 的非对象 JSON 回归测试。
- RED 验证: `PYTHONPATH=tools/new-agents/backend /Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 - <<'PY' ...`，修复前非空 list/string 请求体分别触发 `AttributeError: 'list' object has no attribute 'get'` 和 `AttributeError: 'str' object has no attribute 'get'`。
- 验证: `PYTHONPATH=tools/new-agents/backend /Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 - <<'PY' ...`，非对象 JSON 均被 `RequestValidationError("请求体必须是 JSON 对象")` 拒绝，输出 `non-object JSON rejected`。
- 验证: `PYTHONPATH=tools/new-agents/backend /Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 - <<'PY' ...`，合法 Agent Runtime 请求、workflow/stage 归一化、未知 workflow、workflow/stage 错配、合法 Mermaid repair、负数/布尔 blockIndex 边界均符合预期，输出 `request schema boundary checks passed`。
- 验证: `/Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m py_compile tools/new-agents/backend/request_schemas.py tools/new-agents/backend/tests/test_request_schemas.py`，通过。
- 当前限制: 项目 `.venv` 不存在，bundled Python 没有安装 `pytest`，系统 `python3 -m pytest --version` 在本机卡住后已中断；本轮未实际执行后端 pytest。

### P1: JSON 解析错误绕过 API JSON error envelope

**现象**: `/api/agent/runs/stream` 和 `/api/utils/mermaid/repair` 直接调用 `request.get_json()`。空 body、畸形 JSON 或错误 `Content-Type` 会先由 Flask/Werkzeug 抛出 `BadRequest` / `UnsupportedMediaType`，不会进入已有的 `RequestValidationError` 分支。`app.py` 又把 `<500` HTTPException 原样交回 Flask，调用方可能收到默认 HTML 错误页，而不是项目 API 约定的 `{"error": ...}` JSON envelope。

**影响**: 前端和外部调用方不能稳定按 JSON 错误响应解析请求边界失败。智能体主链路和 Mermaid 修复链路在明显非法请求下会表现为不可诊断的 HTTP 错误，而不是明确的 400 JSON 错误。

**修复记录**:

- 2026-06-18: 新增 `read_json_request_body(...)`，在调用 schema parser 前统一处理 HTTP JSON 读取边界：空 raw body 返回 `None` 交给 parser 输出 `请求体为空`；Werkzeug 400 映射为 `RequestValidationError("请求体不是合法 JSON")`；Werkzeug 415 映射为 `RequestValidationError("请求体必须是 JSON 对象")`。
- 2026-06-18: `agent_runs_stream()` 与 `mermaid_repair()` 改为通过 `read_json_request_body(request.get_data(cache=True), request.get_json)` 读取请求体，因此空 body、畸形 JSON 和错误 content-type 都会进入统一的 JSON error envelope。
- 测试: 已更新 `test_request_schemas.py`，覆盖空 raw body、畸形 JSON 400 和非 JSON content-type 415 的 helper 边界；已更新 Agent Runtime 与 Mermaid repair 端点测试，覆盖空 JSON body 和 malformed JSON body 返回稳定 JSON 400。
- RED 验证: `PYTHONPATH=tools/new-agents/backend /Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 - <<'PY' ...`，修复前失败为 `ImportError: cannot import name 'read_json_request_body'`。
- 验证: `PYTHONPATH=tools/new-agents/backend /Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 - <<'PY' ...`，空 body、畸形 JSON 和非 JSON content-type 均被映射为预期 `RequestValidationError`，输出 `json request boundary checks passed`。
- 验证: `PYTHONPATH=tools/new-agents/backend /Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 - <<'PY' ...`，合法 Agent Runtime、合法 Mermaid repair、空 body、畸形 JSON、非 JSON content-type 和非对象 JSON 均符合预期，输出 `request JSON boundary integration checks passed`。
- 验证: `/Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m py_compile tools/new-agents/backend/request_schemas.py tools/new-agents/backend/routes.py tools/new-agents/backend/tests/test_request_schemas.py tools/new-agents/backend/tests/test_agent_endpoint.py tools/new-agents/backend/tests/test_mermaid_repair_endpoint.py`，通过。
- 当前限制: bundled Python 缺少 `pytest` 和 Flask；系统 `python3 -m pytest --version` 与最小 Flask app 导入脚本在本机卡住后已中断，因此本轮未实际执行后端 pytest / Flask test client。
- 2026-06-18: 收束 JSON 读取异常职责边界，`request_schemas.py` 不再使用 `except Exception` 宽泛捕获；`read_json_request_body(...)` 只负责空 body 与委托 JSON reader，routes 层只捕获 Werkzeug `HTTPException` 并通过 `map_json_request_error(...)` 映射 400/415。
- 测试: 已更新 `test_request_schemas.py`，覆盖 JSON reader 异常会留给 HTTP 层、400/415 映射函数返回 `RequestValidationError`、其他 HTTP 错误不被误映射；已更新 `test_backend_layering.py`，机械约束低层 helper 不出现 `except Exception`。
- RED 验证: `/Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 - <<'PY' ...` 源码检查修复前失败，输出 `AssertionError: request_schemas.py still catches broad Exception`。
- 验证: `PYTHONPATH=tools/new-agents/backend /Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 - <<'PY' ...`，输出 `request schema json boundary checks passed`。
- 验证: `/Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 - <<'PY' ...`，输出 `backend broad exception source check passed`。
- 验证: `/Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m py_compile tools/new-agents/backend/request_schemas.py tools/new-agents/backend/routes.py tools/new-agents/backend/tests/test_request_schemas.py tools/new-agents/backend/tests/test_backend_layering.py`，通过。

### P1: 顶部“导出报告”按钮无动作

**现象**: `Header.tsx` 中“导出报告”按钮没有绑定 `onClick`，用户点击后不会下载当前产出物。右侧 `ArtifactPane` 的下载按钮可用，但顶部主操作入口不可用。

**影响**: 用户在完成多阶段智能体工作流后，无法通过顶部主按钮导出报告，容易误判导出能力失效。

**修复记录**:

- 2026-06-17: 为顶部“导出报告”按钮绑定当前 `artifactContent` 的 Markdown 下载逻辑，文件名为 `<workflow>_report.md`。
- 测试: 新增 `Header` 组件测试，覆盖点击顶部导出按钮会创建 Markdown Blob、触发 anchor click 并释放 object URL。
- 验证: `cd tools/new-agents/frontend && npm test -- src/components/__tests__/Header.test.tsx`，4 passed。
- 验证: `cd tools/new-agents/frontend && npm test`，25 files / 182 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；当时仍有既有大 chunk warning，已在下方独立性能债中修复。

### P1: 右侧产出物下载文件名硬编码为 Lisa

**现象**: 顶部“导出报告”按钮已按 workflow 使用 `<workflow>_report.md`，但右侧 `ArtifactPane` 下载按钮仍固定设置 `a.download = 'lisa_artifact.md'`。在 `REQ_REVIEW`、`INCIDENT_REVIEW` 或 Alex 工作流中，下载文件名仍带 Lisa 品牌残留。

**影响**: 多智能体/多工作流导出的文件名与当前上下文不匹配，用户本地归档时容易混淆产出物来源；也会让已完成的顶部导出修复和右侧下载入口表现不一致。

**修复记录**:

- 2026-06-18: `ArtifactPane` 下载逻辑读取当前 `workflow`，文件名改为 `<workflow>_artifact.md`，与顶部 `<workflow>_report.md` 命名风格保持一致。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/components/__tests__/ArtifactPane.test.tsx`，修复前新增用例失败，实际文件名为 `lisa_artifact.md` 而不是 `req_review_artifact.md`。
- 验证: `cd tools/new-agents/frontend && npm test -- src/components/__tests__/ArtifactPane.test.tsx`，6 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/components/__tests__/ArtifactPane.test.tsx src/components/__tests__/Header.test.tsx`，2 files / 10 tests passed。
- 验证: `cd tools/new-agents/frontend && npm test`，26 files / 258 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；主入口 chunk 336.20 kB，large chunk warning 未回归。
- 验证: `git diff --check`，通过。

### P1: 复制按钮未处理 Clipboard API 失败

**现象**: `ChatPane.handleCopy()` 直接 `await navigator.clipboard.writeText(...)`。当浏览器 Clipboard API 因权限、安全上下文或系统策略拒绝时，组件不会显示失败反馈，测试环境也会捕获未处理 promise rejection。

**影响**: 用户点击“复制”后没有明确反馈，可能误以为内容已复制；未处理 rejection 还会污染前端错误监控和自动化测试输出。

**修复记录**:

- 2026-06-18: `handleCopy()` 增加失败分支。成功时继续设置 `copiedId` 并显示 `已复制到剪贴板`；失败时清除 copied 状态并显示 `复制失败` toast，仍复用 2 秒后清理 toast 的逻辑。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/components/__tests__/ChatPane.test.tsx`，修复前新增用例失败，找不到 `复制失败`，且 Vitest 捕获 `permission denied` unhandled rejection。
- 验证: `cd tools/new-agents/frontend && npm test -- src/components/__tests__/ChatPane.test.tsx`，12 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/components/__tests__/ChatPane.test.tsx src/services/__tests__/chatService.test.ts src/__tests__/testHygiene.test.ts`，3 files / 59 tests passed。
- 验证: `cd tools/new-agents/frontend && npm test`，26 files / 259 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；主入口 chunk 336.20 kB，large chunk warning 未回归。
- 验证: `git diff --check`，通过。

### P1: 连续复制消息时旧反馈定时器会提前清除新反馈

**现象**: `ChatPane.handleCopy()` 每次复制都会启动一个 2 秒后清理 `copiedId` 和 toast 的 `setTimeout`，但没有取消上一轮定时器。用户快速复制第一条和第二条消息时，第一条的旧定时器会提前清掉第二条的“已复制”状态和 toast。

**影响**: 用户刚复制第二条消息后，按钮可能很快从“已复制”退回“复制”，底部反馈也提前消失，容易误判第二次复制没有成功。

**修复记录**:

- 2026-06-18: `ChatPane` 使用 `copyFeedbackTimeoutRef` 保存当前复制反馈定时器；新的复制动作会先清理上一轮定时器，再启动自己的 2 秒清理窗口；组件卸载时也会清理未完成定时器。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/components/__tests__/ChatPane.test.tsx -t "keeps the latest copy feedback"`，修复前失败输出显示第一条旧 timer 触发后找不到 `已复制到剪贴板`。
- 验证: `cd tools/new-agents/frontend && npm test -- src/components/__tests__/ChatPane.test.tsx -t "keeps the latest copy feedback"`，1 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/components/__tests__/ChatPane.test.tsx`，13 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/components/__tests__/ChatPane.test.tsx src/services/__tests__/chatService.test.ts src/__tests__/testHygiene.test.ts`，3 files / 60 tests passed。
- 验证: `cd tools/new-agents/frontend && npm test`，26 files / 261 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；主入口 chunk 336.20 kB，large chunk warning 未回归。
- 验证: `git diff --check`，通过。

### P1: 图片/PDF 附件被当作 UTF-8 文本注入 prompt

**现象**: `llm.ts` 在构造结构化 Agent Runtime prompt 时，对所有附件调用 base64 → UTF-8 解码。图片、PDF 等二进制附件会变成乱码或把二进制片段塞进 prompt。

**影响**: 模型上下文被无意义内容污染，严重时会影响智能体理解用户输入；同时当前后端协议并不支持真正的文件对象解析，前端把二进制硬塞进 prompt 也不会得到可靠文件理解能力。

**修复记录**:

- 2026-06-17: 新增附件 MIME 判断。`text/*`、JSON、XML、YAML 以及常见文本扩展名继续按 UTF-8 解码；图片、PDF 等非文本附件只注入文件名、MIME 类型和“非文本附件未注入原始二进制内容”的明确提示。
- 测试: 新增 `llm.ts` 单测，覆盖图片/PDF 不再把二进制内容写入 prompt，同时仍保留附件元数据。
- 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts`，24 passed。
- 验证: `cd tools/new-agents/frontend && npm test`，25 files / 183 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；当时仍有既有大 chunk warning，已在下方独立性能债中修复。

### P1: 上传未知 MIME 附件时会误标为 text/plain

**现象**: `handleFileChange()` 在浏览器未提供 `file.type` 时把附件 `mimeType` 默认写成 `text/plain`。如果用户上传的是 `.png`、`.pdf` 等二进制文件，但浏览器或系统没有识别 MIME，后续 prompt 构建会优先按 `text/plain` 判断为文本附件，绕过非文本附件保护。

**影响**: 已修复的“图片/PDF 附件不注入原始二进制内容”边界会被上传入口的错误默认值破坏。未知 MIME 的二进制附件可能再次被 base64 解码并写入 Agent Runtime prompt，造成乱码、上下文污染和模型误判。

**修复记录**:

- 2026-06-18: 上传入口默认 MIME 从 `text/plain` 改为 `application/octet-stream`。真实文本文件仍可通过浏览器提供的 `text/*` MIME 或文件扩展名在 prompt 构建阶段识别；未知二进制文件不会被乐观标记为文本。
- 测试: 已更新 `chatService` hook 测试，覆盖上传 `file.type === ''` 的 `screen.png` 时，pending attachment 的 `mimeType` 为 `application/octet-stream`。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts -t "should not default unknown uploaded file types"`，修复前失败输出显示 `mimeType` 实际为 `text/plain`。
- 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts -t "should not default unknown uploaded file types"`，1 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts src/core/__tests__/llm.test.ts`，2 files / 82 tests passed。
- 验证: `cd tools/new-agents/frontend && npm test`，25 files / 244 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；主入口 chunk 336.11 kB，large chunk warning 未回归。

### P1: 附件缺少 MIME 类型时 prompt 构建崩溃

**现象**: `llm.ts` 的 `isTextAttachment()` 直接调用 `attachment.mimeType.toLowerCase()`。如果历史会话、外部导入或测试夹具里的附件对象缺少 `mimeType`，结构化 Agent Runtime prompt 构建会在发起请求前抛 `TypeError`。

**影响**: 用户带着旧附件历史继续对话或重试时，主 Agent 调用可能直接失败；即使附件文件名是 `.md`、`.txt` 等可识别文本，也无法退回到扩展名判断。

**修复记录**:

- 2026-06-18: `isTextAttachment()` 在 MIME 缺失时使用空字符串继续判断，并保留后续文件扩展名兜底；prompt 展示仍使用 `类型: unknown`，不会伪造 MIME 类型。
- 测试: 已更新 `llm.ts` 消息构建测试，覆盖缺少 `mimeType` 的 `.md` 历史附件仍按文本附件解码注入 prompt。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts -t "附件缺少 mimeType"`，修复前失败输出为 `TypeError: Cannot read properties of undefined (reading 'toLowerCase')`。
- 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts -t "附件缺少 mimeType"`，1 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts`，42 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts src/services/__tests__/chatService.test.ts`，2 files / 74 tests passed。
- 验证: `cd tools/new-agents/frontend && npm test`，25 files / 228 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；主入口 chunk 334.69 kB，large chunk warning 未回归。

### P1: 文本附件 base64 损坏时 prompt 构建崩溃

**现象**: `llm.ts` 的 `decodeBase64Text()` 直接调用 `atob(base64)`。如果历史会话、持久化状态或外部导入数据里存在损坏的文本附件 base64，结构化 Agent Runtime prompt 构建会在发起请求前抛 `InvalidCharacterError`。

**影响**: 用户继续分析旧附件或重试旧消息时，主 Agent 请求会被本地解码异常阻断；用户只能看到请求失败，无法从 prompt 或 UI 判断是哪一个附件内容损坏。

**修复记录**:

- 2026-06-18: `decodeBase64Text()` 捕获 base64 解码失败并返回 `null`；文本附件无法解码时仍保留附件名与 MIME 类型，并在 prompt 中写入“文本附件内容无法解码”的明确占位，不再阻断 Agent 请求。
- 测试: 已更新 `llm.ts` 消息构建测试，覆盖损坏 base64 的文本附件仍能发起结构化 Agent Runtime 请求。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts -t "文本附件 base64 损坏"`，修复前失败输出为 `InvalidCharacterError: Invalid character`。
- 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts -t "文本附件 base64 损坏"`，1 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts`，43 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts src/services/__tests__/chatService.test.ts`，2 files / 75 tests passed。
- 验证: `cd tools/new-agents/frontend && npm test`，25 files / 229 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；主入口 chunk 334.69 kB，large chunk warning 未回归。

### P1: 附件缺少文件名时 prompt 构建崩溃

**现象**: `llm.ts` 的 `isTextAttachment()` 在 MIME 类型无法判断文本类型时，会继续调用 `attachment.name.toLowerCase()`。如果历史会话、持久化状态或外部导入数据里的附件对象缺少 `name`，结构化 Agent Runtime prompt 构建会在发起请求前抛 `TypeError`。

**影响**: 用户继续分析旧附件或重试旧消息时，主 Agent 请求可能被本地附件格式化异常阻断；缺失文件名的附件也没有稳定占位，无法在 prompt 中定位问题附件。

**修复记录**:

- 2026-06-18: `isTextAttachment()` 在文件名缺失时使用空字符串做扩展名判断；`formatAttachmentForPrompt()` 对缺失文件名显示 `未命名附件`，保留 MIME 类型或 `unknown`，不再阻断 Agent 请求。
- 测试: 已更新 `llm.ts` 消息构建测试，覆盖缺少文件名的历史附件仍能发起结构化 Agent Runtime 请求，并在 prompt 中显示稳定占位。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts -t "附件缺少文件名"`，修复前失败输出为 `TypeError: Cannot read properties of undefined (reading 'toLowerCase')`。
- 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts -t "附件缺少文件名"`，1 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts`，44 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts src/services/__tests__/chatService.test.ts`，2 files / 76 tests passed。
- 验证: `cd tools/new-agents/frontend && npm test`，25 files / 230 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；主入口 chunk 334.69 kB，large chunk warning 未回归。
- 说明: 曾并行运行全量 `npm test`、`npm run lint`、`npm run build` 时进程被系统以 137 结束；顺序重跑三项均通过，判断为本地并行资源竞争而非功能失败。

### P1: 文本附件缺少内容时误报为 base64 损坏

**现象**: `llm.ts` 在格式化文本附件时，只区分“成功解码”和“无法解码”。如果历史会话、持久化状态或外部导入数据里的文本附件缺少 `data` 字段，prompt 中会显示“文本附件内容无法解码”，无法区分内容缺失和内容损坏。

**影响**: Agent Runtime 请求不会被阻断，但用户和模型都会收到不准确的附件诊断；后续排查时难以判断是上传内容损坏，还是持久化/导入过程丢失了附件内容字段。

**修复记录**:

- 2026-06-18: `formatAttachmentForPrompt()` 在文本附件 `data` 不是字符串时返回“文本附件内容缺失”占位；只有字符串存在但 base64 解码失败时才返回“文本附件内容无法解码”。
- 测试: 已更新 `llm.ts` 消息构建测试，覆盖文本附件缺少 `data` 字段时仍能发起结构化 Agent Runtime 请求，并在 prompt 中给出准确缺失诊断。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts -t "文本附件缺少 data"`，修复前失败输出显示 prompt 包含“文本附件内容无法解码”，而不是期望的“文本附件内容缺失”。
- 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts -t "文本附件缺少 data"`，1 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts`，45 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts src/services/__tests__/chatService.test.ts`，2 files / 77 tests passed。
- 验证: `cd tools/new-agents/frontend && npm test`，25 files / 231 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；主入口 chunk 334.69 kB，large chunk warning 未回归。

### P1: 附件数组包含无效记录时 prompt 构建崩溃

**现象**: `llm.ts` 的 `formatAttachmentForPrompt()` 假设附件数组中的每一项都是对象，并直接读取 `attachment.name`。如果历史会话、持久化状态或外部导入数据中的 `attachments` 数组含有 `null` 等无效记录，结构化 Agent Runtime prompt 构建会在发起请求前抛 `TypeError`。

**影响**: 单个坏附件记录会阻断整轮 Agent 请求，用户无法继续分析其余上下文；同时 prompt 中也没有可诊断占位说明持久化附件记录本身损坏。

**修复记录**:

- 2026-06-18: `formatAttachmentForPrompt()` 增加运行时记录校验；非对象或 `null` 附件记录会转为 `[附件: 无效附件记录]`、`类型: unknown` 和“附件记录无效”占位，不再阻断 Agent 请求。
- 测试: 已更新 `llm.ts` 消息构建测试，覆盖附件数组包含 `null` 记录时仍能发起结构化 Agent Runtime 请求。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts -t "附件数组包含空记录"`，修复前失败输出为 `TypeError: Cannot read properties of null (reading 'name')`。
- 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts -t "附件数组包含空记录"`，1 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts`，46 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts src/services/__tests__/chatService.test.ts`，2 files / 78 tests passed。
- 验证: `cd tools/new-agents/frontend && npm test`，25 files / 232 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；主入口 chunk 334.69 kB，large chunk warning 未回归。

### P1: 历史消息附件去重遇到无效记录时 prompt 构建崩溃

**现象**: `llm.ts` 的 `areSameAttachments()` 会比较历史最后一条用户消息与当前请求附件，用于避免把当前用户消息重复拼进 Agent Runtime prompt。该比较逻辑直接读取 `attachment.name`、`mimeType` 和 `data`。如果历史消息和当前请求的附件数组都包含同一个 `null` 等无效记录，前面的附件格式化已经能兜底，但去重比较仍会在发起请求前抛 `TypeError`。

**影响**: 用户从持久化历史继续同一条带坏附件记录的请求时，结构化 prompt 不仅无法去重，还会直接阻断 Agent 请求；这会让刚修复的无效附件占位能力在历史去重路径上失效。

**修复记录**:

- 2026-06-18: `areSameAttachments()` 复用附件记录运行时校验；只有两侧都是对象记录时才比较 `name`、`mimeType` 和 `data`，否则退回严格相等判断，不再读取 `null` 或非对象字段。
- 测试: 已更新 `llm.ts` 消息构建测试，覆盖历史最后一条用户消息与当前请求都包含 `null` 附件记录时，当前用户消息仍会被去重且 prompt 中保留无效附件占位。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts -t "历史消息和当前消息都包含空附件记录"`，修复前失败输出为 `TypeError: Cannot read properties of null (reading 'name')`。
- 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts -t "历史消息和当前消息都包含空附件记录"`，1 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts`，47 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts src/services/__tests__/chatService.test.ts`，2 files / 79 tests passed。
- 验证: `cd tools/new-agents/frontend && npm test`，25 files / 233 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；主入口 chunk 334.69 kB，large chunk warning 未回归。

### P1: 历史附件字段不是数组时 prompt 构建崩溃

**现象**: `llm.ts` 的 `buildContentWithAttachments()` 和 `areSameAttachments()` 假设 `attachments` 字段一定是数组。历史会话、localStorage 持久化迁移或外部导入如果把 `attachments` 写成对象等非数组容器，结构化 Agent Runtime prompt 构建会在 `.map()` 入口抛 `TypeError`。

**影响**: 用户继续打开旧会话或导入异常历史时，单个附件容器格式错误会阻断整轮 Agent 请求；如果这条消息正好是当前用户消息，还会让去重逻辑无法执行，造成 prompt 构建链路在进入后端前失败。

**修复记录**:

- 2026-06-18: 新增 `normalizeAttachmentList()`，在 prompt 构建和附件去重入口统一处理附件列表容器。`undefined` / `null` 视为空列表；数组按原逻辑逐项格式化；非数组容器转为 `[附件: 无效附件列表]` 和“附件列表格式无效”占位，并在去重比较时退回严格相等判断。
- 测试: 已更新 `llm.ts` 消息构建测试，覆盖历史最后一条用户消息与当前请求都携带同一个非数组附件容器时，当前用户消息仍会被去重且 prompt 中保留无效附件列表占位。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts -t "历史消息和当前消息都包含非数组附件容器"`，修复前失败输出为 `TypeError: attachments.map is not a function`。
- 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts -t "历史消息和当前消息都包含非数组附件容器"`，1 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts`，48 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts src/services/__tests__/chatService.test.ts`，2 files / 80 tests passed。
- 验证: `cd tools/new-agents/frontend && npm test`，25 files / 234 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；主入口 chunk 334.69 kB，large chunk warning 未回归。

### P1: 历史附件字段不是数组时 ChatPane 渲染崩溃

**现象**: `ChatPane.tsx` 渲染历史消息附件时使用 `msg.attachments.length > 0` 和 `msg.attachments.map(...)`。如果持久化历史里的 `attachments` 是 `{ length: 1 }` 等非数组容器，会通过 length 判断后在 `.map()` 处抛 `TypeError`。

**影响**: 即使 Agent Runtime prompt 构建已能处理脏附件容器，用户打开工作区或恢复旧会话时仍可能在 React 渲染层白屏，无法看到历史消息或继续对话。

**修复记录**:

- 2026-06-18: `ChatPane` 新增渲染附件归一化，只渲染真实数组附件；历史消息和 pending 附件的 `.length` / `.map` 均只作用于归一化后的数组。
- 测试: 已更新 `ChatPane` 组件测试，覆盖持久化历史消息的 `attachments` 为非数组容器时仍能渲染消息正文。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/components/__tests__/ChatPane.test.tsx -t "renders messages when persisted attachments is a non-array value"`，修复前失败输出为 `TypeError: msg.attachments.map is not a function`。
- 验证: `cd tools/new-agents/frontend && npm test -- src/components/__tests__/ChatPane.test.tsx -t "renders messages when persisted attachments is a non-array value"`，1 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/components/__tests__/ChatPane.test.tsx src/core/__tests__/agentCore.test.ts src/services/__tests__/chatService.test.ts`，3 files / 59 tests passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts src/components/__tests__/ChatPane.test.tsx src/core/__tests__/agentCore.test.ts src/services/__tests__/chatService.test.ts`，4 files / 107 tests passed。
- 验证: `cd tools/new-agents/frontend && npm test`，25 files / 236 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；主入口 chunk 334.72 kB，large chunk warning 未回归。

### P1: 重试链路会把非数组历史附件写入 pendingAttachments

**现象**: `planRetryFromHistory()` 原先返回 `lastUserMessage.attachments || []`。如果最后一条用户历史消息的 `attachments` 是 `{ length: 1 }` 等非数组容器，点击 assistant 消息“重试”后会把脏值写入 `pendingAttachments`。随后输入区渲染或下一次发送可能在 `.map()` / 展开操作处崩溃。

**影响**: 用户恢复旧会话后点击重试，可能在尚未发起 Agent Runtime 请求前就让 UI 或发送链路崩溃；同时脏附件容器会从历史状态传播到当前草稿状态。

**修复记录**:

- 2026-06-18: `planRetryFromHistory()` 在生成 retry plan 时只保留真实数组附件；非数组历史附件归一化为空数组，避免污染 `pendingAttachments`。
- 测试: 已更新 `agentCore` 单测，覆盖从持久化历史规划重试时丢弃非数组附件容器。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/agentCore.test.ts -t "drops non-array attachments"`，修复前失败输出显示 `retryAttachments` 为 `{ length: 1 }`。
- 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/agentCore.test.ts -t "drops non-array attachments"`，1 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/components/__tests__/ChatPane.test.tsx src/core/__tests__/agentCore.test.ts src/services/__tests__/chatService.test.ts`，3 files / 59 tests passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts src/components/__tests__/ChatPane.test.tsx src/core/__tests__/agentCore.test.ts src/services/__tests__/chatService.test.ts`，4 files / 107 tests passed。
- 验证: `cd tools/new-agents/frontend && npm test`，25 files / 236 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；主入口 chunk 334.72 kB，large chunk warning 未回归。

### P1: 持久化恢复时未清洗历史附件字段

**现象**: `store.ts` 的 Zustand `persist` 配置原先直接保存和恢复 `chatHistory`。如果 localStorage、旧 key 迁移或外部导入状态中存在非数组 `attachments`，脏值会在 hydrate 时进入全局 store，再由 ChatPane、retry、prompt 构建等多个消费点分别兜底。

**影响**: 数据边界缺少统一治理会让每个下游消费点都必须重复防御同一类脏状态；一旦新增消费点遗漏检查，旧会话恢复仍可能导致 UI 崩溃、重试崩溃或 Agent 请求前失败。

**修复记录**:

- 2026-06-18: 新增 `sanitizeChatHistory()`，在 `persist.partialize` 和 `persist.merge` 两个边界统一清洗 `chatHistory`。恢复时只保留结构合法的消息，非数组 `attachments` 字段会被删除；保存时同样避免把非数组附件容器写回 localStorage。
- 测试: 已更新 store 单测，覆盖从 localStorage rehydrate 含非数组 `attachments` 的历史消息时，消息正文保留且 `attachments` 被清除。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/__tests__/store.test.ts -t "should drop non-array attachments"`，修复前失败输出显示 `attachments` 仍为 `{ length: 1 }`。
- 验证: `cd tools/new-agents/frontend && npm test -- src/__tests__/store.test.ts -t "should drop non-array attachments"`，1 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/__tests__/store.test.ts`，7 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/__tests__/store.test.ts src/components/__tests__/ChatPane.test.tsx src/core/__tests__/agentCore.test.ts src/services/__tests__/chatService.test.ts src/core/__tests__/llm.test.ts`，5 files / 114 tests passed。
- 验证: `cd tools/new-agents/frontend && npm test`，25 files / 237 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；主入口 chunk 335.14 kB，large chunk warning 未回归。
- 2026-06-18: `sanitizeChatHistory()` 进一步增加附件数组元素级清洗，只保留 `name`、`data`、`mimeType` 均为字符串的附件；数组中的 `null`、缺字段或字段类型错误记录会被丢弃。
- 2026-06-18: `ChatPane` 的渲染附件归一化同步增加元素级过滤，避免外部导入或测试夹具绕过 store hydration 时因 `attachments: [null]` 触发渲染崩溃。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/__tests__/store.test.ts -t "malformed attachment entries"`，修复前失败输出显示 `attachments` 仍包含 `null`、缺 `data` 和 `name: 123` 的记录。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/components/__tests__/ChatPane.test.tsx -t "malformed entries"`，修复前失败输出为 `TypeError: Cannot read properties of null (reading 'name')`。
- 验证: `cd tools/new-agents/frontend && npm test -- src/__tests__/store.test.ts -t "malformed attachment entries"`，1 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/components/__tests__/ChatPane.test.tsx -t "malformed entries"`，1 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/__tests__/store.test.ts src/components/__tests__/ChatPane.test.tsx src/core/__tests__/agentCore.test.ts src/core/__tests__/llm.test.ts`，4 files / 96 tests passed。
- 验证: `cd tools/new-agents/frontend && npm test`，26 files / 268 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；主入口 chunk 336.52 kB，large chunk warning 未回归。

### P1: 持久化恢复时未校验工作流与阶段状态

**现象**: `store.ts` 的 Zustand `persist.merge` 原先只清洗 `chatHistory`，其余持久化字段会直接合并进全局 store。如果 localStorage、旧 key 迁移或外部导入状态写入未知 `workflow`、越界 `stageIndex` 或非对象 `stageArtifacts`，后续 `clearHistory()`、`setStageIndex()`、`setArtifactContent()` 等路径会读取 `WORKFLOWS[state.workflow].stages[...]` 并崩溃。

**影响**: 一个脏持久化状态就能污染整个工作区身份和阶段上下文。用户打开旧会话后可能白屏、无法清空历史，或在错误 workflow/stage 下发起 Agent Runtime 请求。

**修复记录**:

- 2026-06-18: 新增持久化工作区状态归一化。未知 `workflow` 回退到 `TEST_DESIGN`；非法或越界 `stageIndex` 回退到 `0`；非法 `stageArtifacts` 重建当前工作流首阶段欢迎产物；`artifactHistory` 也只保留结构合法版本。`persist.merge` 改为白名单合并归一化后的字段，不再信任任意持久化对象。
- 测试: 已更新 store 单测，覆盖 rehydrate 未知工作流和合法工作流越界阶段索引两个场景，确认恢复后 `workflow`、`stageIndex`、`artifactContent` 和 `stageArtifacts` 都回到可用状态。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/__tests__/store.test.ts -t "hydrating an unknown workflow|out-of-range persisted stage"`，修复前第一个用例显示 `workflow` 仍为 `UNKNOWN_WORKFLOW`，第二个用例在 `clearHistory()` 中因未知 workflow 崩溃。
- 验证: `cd tools/new-agents/frontend && npm test -- src/__tests__/store.test.ts -t "hydrating an unknown workflow|out-of-range persisted stage"`，2 passed / 7 skipped。
- 验证: `cd tools/new-agents/frontend && npm test -- src/__tests__/store.test.ts`，9 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/__tests__/store.test.ts src/components/__tests__/ChatPane.test.tsx src/core/__tests__/agentCore.test.ts src/services/__tests__/chatService.test.ts src/core/__tests__/llm.test.ts`，5 files / 117 tests passed。
- 验证: `cd tools/new-agents/frontend && npm test`，25 files / 240 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；主入口 chunk 336.11 kB，large chunk warning 未回归。

### P1: 持久化恢复时丢失有效当前产物内容

**现象**: `persist.merge` 在清洗 `stageArtifacts` 为空对象或非法值时，会先补当前工作流首阶段欢迎页。即使持久化状态里还有合法的 `artifactContent`，恢复后的右侧工作区也会显示欢迎页，并把当前阶段 `stageArtifacts[currentStageId]` 写成欢迎页。

**影响**: 旧版本 localStorage、外部导入或局部损坏状态只要丢失 `stageArtifacts`，就可能让用户已经生成的当前阶段产物在恢复时被欢迎页覆盖。用户会误以为产物丢失，后续 prompt 也会基于欢迎页而不是真实当前产物构建上下文。

**修复记录**:

- 2026-06-18: 将 `stageArtifacts` 清洗和默认欢迎页填充分离。只有原始 `workflow` 与 `stageIndex` 都合法、当前阶段缺少有效 `stageArtifacts`、且持久化 `artifactContent` 是非空字符串时，才用 `artifactContent` 恢复当前阶段产物；未知 workflow 或越界 stage 仍回退到安全欢迎页。
- 测试: 已更新 store 单测，覆盖合法 workflow/stage 下 `stageArtifacts` 为空但 `artifactContent` 有效时，rehydrate 后 `artifactContent` 与 `stageArtifacts.CLARIFY` 均保留该产物。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/__tests__/store.test.ts -t "should restore current artifact content"`，修复前失败输出显示恢复结果为 `# 欢迎使用 Lisa AI 专家...`，不是持久化产物。
- 验证: `cd tools/new-agents/frontend && npm test -- src/__tests__/store.test.ts -t "should restore current artifact content"`，1 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/__tests__/store.test.ts`，10 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/__tests__/store.test.ts src/services/__tests__/chatService.test.ts src/core/__tests__/agentCore.test.ts src/core/__tests__/llm.test.ts`，4 files / 113 tests passed。
- 验证: `cd tools/new-agents/frontend && npm test`，25 files / 247 tests passed。
- 2026-06-18: 修复当前阶段 `stageArtifacts[currentStageId]` 旧缓存覆盖最新 `artifactContent` 的恢复顺序问题。合法 workflow/stage 下，非空持久化 `artifactContent` 现在优先作为当前阶段产物，并同步写回当前阶段 `stageArtifacts[currentStageId]`。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/__tests__/store.test.ts -t "prefer persisted current artifact"`，修复前失败输出显示恢复结果为 `# 旧需求分析`，不是 `# 最新需求分析`。
- 验证: `cd tools/new-agents/frontend && npm test -- src/__tests__/store.test.ts -t "prefer persisted current artifact"`，1 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/__tests__/store.test.ts`，16 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/__tests__/store.test.ts src/components/__tests__/ChatPane.test.tsx src/core/__tests__/agentCore.test.ts src/core/__tests__/llm.test.ts`，4 files / 96 tests passed。
- 验证: `cd tools/new-agents/frontend && npm test`，26 files / 268 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；主入口 chunk 336.52 kB，large chunk warning 未回归。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；主入口 chunk 336.13 kB，large chunk warning 未回归。

### P1: Mermaid 修复请求允许非法 blockIndex 进入 LLM prompt

**现象**: `/api/utils/mermaid/repair` 的请求 schema 只声明 `blockIndex: int | None`，`blockIndex=-1` 会被 parser 接受并进入 Mermaid 修复提示词。由于 Python 中 `bool` 是 `int` 的子类，`blockIndex=true` 也会被解析为 `1`。

**影响**: 前端传入异常代码块索引时，后端不能在请求边界给出明确 400 错误，而是把无意义索引带入 LLM 修复上下文，增加错误定位成本。

**修复记录**:

- 2026-06-17: `parse_mermaid_repair_request()` 增加显式 `blockIndex` 校验，只允许 `None` 或非负整数；布尔值和字符串等非整数统一返回 `blockIndex 必须为整数`，负数返回 `blockIndex 不能为负数`。
- 测试: 新增 request schema 测试覆盖负数和布尔 `blockIndex`；新增 Mermaid 修复端点测试覆盖负数索引在调用 repair service 前返回 400。
- RED 验证: parser 直接调用在修复前输出 `AssertionError: negative blockIndex was accepted`；布尔边界修复前输出 `AssertionError: boolean blockIndex was accepted`。
- 验证: `PYTHONPATH=tools/new-agents/backend /Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 - <<'PY' ...`，覆盖负数、布尔、字符串和合法 `0`，输出 `mermaid repair blockIndex validation passed`。
- 验证: `/Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m py_compile tools/new-agents/backend/request_schemas.py tools/new-agents/backend/tests/test_request_schemas.py tools/new-agents/backend/tests/test_mermaid_repair_endpoint.py`，通过。
- 当前限制: bundled Python 没有安装 `pytest`，本轮未实际执行后端 pytest；端点级直接脚本也因当前环境缺少 `flask` 无法运行。

### P1: Mermaid repair 上游 LLM 异常未映射为端点级错误

**现象**: `/api/utils/mermaid/repair` 的 route 只捕获 `MermaidRepairError`。但 `repair_mermaid_code()` 内部会调用 `llm_client.stream_chat_completion_content()`，该函数可能抛出 `LlmClientError`、`AuthenticationError`、`RateLimitError` 或 `APIError`。这些异常原先会穿透 service 和 route，最终落到全局 500。

**影响**: Mermaid 自动修复是用户看到图表渲染失败后的补救链路；默认 LLM 鉴权失败、限流、网关不可达或流式 chunk 畸形时，前端只能看到泛化服务端错误，无法判断是“修复模型调用失败”还是后端业务 bug。

**修复记录**:

- 2026-06-18: `repair_mermaid_code()` 显式捕获 `LlmClientError`、`AuthenticationError`、`RateLimitError` 和 `APIError`，并包装为 `MermaidRepairError` 保留原始 message 与 `__cause__`。现有 route 的 `MermaidRepairError -> 502 JSON` 路径因此可统一返回可诊断错误。
- 测试: 已更新 `test_mermaid_repair_service.py`，覆盖 `stream_chat_completion_content()` 抛出 `LlmClientError("OpenAI unavailable")` 时，service 抛出 `MermaidRepairError("OpenAI unavailable")` 且保留原异常 cause。
- RED 验证: `PYTHONPATH=tools/new-agents/backend /Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 - <<'PY' ...`，修复前 `LlmClientError: OpenAI unavailable` 直接穿透 `repair_mermaid_code()`。
- 验证: `PYTHONPATH=tools/new-agents/backend /Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 - <<'PY' ...`，`LlmClientError` 被映射为 `MermaidRepairError`，输出 `mermaid LLM error mapping passed`。
- 验证: `PYTHONPATH=tools/new-agents/backend /Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 - <<'PY' ...`，Mermaid repair 成功清洗、空响应校验失败和 LLM 错误包装三条路径均符合预期，输出 `mermaid repair service boundary checks passed`。
- 验证: `/Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m py_compile tools/new-agents/backend/mermaid_repair_service.py tools/new-agents/backend/tests/test_mermaid_repair_service.py tools/new-agents/backend/routes.py tools/new-agents/backend/tests/test_mermaid_repair_endpoint.py`，通过。
- 当前限制: bundled Python 缺少 `pytest`、Flask 和 openai；本轮直接脚本通过注入最小 fake `openai` 模块验证 service 逻辑，未实际执行后端 pytest / Flask test client。

### P1: 前端生产源码残留 console 诊断输出

**现象**: `store.ts` 的 localStorage 迁移失败路径和 `mermaidRetryService.ts` 的 Mermaid 修复失败路径会直接调用 `console.error(...)`。现有 hygiene 测试只覆盖非 smoke 测试文件，没有约束生产源码。

**影响**: 预期内的浏览器 storage 不可用、Mermaid 修复端点 5xx 等失败会在用户控制台留下实现细节和噪声；自动化测试也无法防止后续生产代码继续引入 `console.log/error/warn`。

**修复记录**:

- 2026-06-18: `testHygiene.test.ts` 新增生产前端源码扫描，排除 `__tests__` 和 `.test.ts(x)` 后禁止 `console.log`、`console.error`、`console.warn`。
- 2026-06-18: `mermaidRetryService.ts` 的预期失败路径仍返回 `null`，不再直接写 stderr；`store.ts` 的 legacy storage 迁移仅吞掉浏览器 `DOMException`，非预期错误继续抛出。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/__tests__/testHygiene.test.ts`，修复前失败，offenders 为 `src/services/mermaidRetryService.ts:58` 和 `src/store.ts:172`。
- 验证: `cd tools/new-agents/frontend && npm test -- src/__tests__/testHygiene.test.ts src/services/__tests__/mermaidRetryService.test.ts src/__tests__/store.test.ts`，3 files / 20 tests passed。
- 验证: `cd tools/new-agents/frontend && npm test`，26 files / 252 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；主入口 chunk 336.18 kB，large chunk warning 未回归。
- 验证: `cd tools/new-agents/frontend && rg -n "console\\.(log|error|warn)" src --glob '!**/*.test.ts' --glob '!**/*.test.tsx' --glob '!**/__tests__/**'`，无命中。

### P1: 当前用户消息在 Agent Runtime prompt 中重复注入

**现象**: `handleSend` 会先把当前用户消息追加到 `chatHistory`，随后 `generateResponseStream` 又从 store 读取 `chatHistory` 并额外追加同一个 `userMessage`。首轮请求会变成 `[用户]\nhello\n\n[用户]\nhello` 这类重复 prompt；带附件时同一份附件也可能重复进入模型上下文。

**影响**: 后端结构化 Agent Runtime 收到的输入被重复污染，模型可能误判用户强调了同一需求两次；附件场景会浪费上下文窗口，并放大附件摘要或二进制占位文本对模型判断的干扰。

**修复记录**:

- 2026-06-17: `buildRuntimePrompt` 在拼接历史前识别并移除末尾那条与当前发送内容、附件完全一致的 user turn，只保留真正的历史上下文，再追加当前输入。
- 测试: 新增 `llm.ts` 单测，模拟聊天服务已把当前用户消息写入 store 后再调用 `generateResponseStream`，断言发给 `/new-agents/api/agent/runs/stream` 的 `prompt` 只包含一次当前输入。
- 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts`，25 passed。
- 验证: `cd tools/new-agents/frontend && npm test`，25 files / 189 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；主入口 chunk 保持 334.41 kB，large chunk warning 未回归。

### P1: Agent Runtime SSE 最后一个无换行事件被丢弃

**现象**: 前端 `generateResponseStreamViaAgentRuntime()` 读取 SSE 时只处理 `buffer.split('\n')` 产生的完整行；如果服务端关闭流时最后一个 `data: ...` 事件没有尾随换行，该事件会留在 buffer 中，reader `done` 后直接退出。

**影响**: 在代理、网关或流式实现没有补尾随换行时，最后一个 `agent_turn` 或 `error` 事件可能被静默丢弃。用户侧表现为没有回复、没有错误提示，且不容易从前端状态判断原因。

**修复记录**:

- 2026-06-17: SSE 读取循环在 reader `done` 后 flush `TextDecoder` 并处理剩余 buffer；普通行处理与尾部 buffer 处理复用同一逻辑，`[DONE]` 仍会停止后续消费。
- 测试: 新增 `llm.ts` 单测，构造没有尾随换行的单个 `agent_turn` SSE 事件，覆盖最后事件不再被丢弃。
- 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts`，26 passed。
- 验证: `cd tools/new-agents/frontend && npm test`，25 files / 190 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；主入口 chunk 保持 334.41 kB，large chunk warning 未回归。

### P1: SSE `data:` 冒号后无空格时 typed event 被静默忽略

**现象**: 前端 Agent Runtime SSE adapter 原先只识别 `line.startsWith('data: ')`。SSE 规范允许 `data:<payload>` 这种冒号后不带空格的字段行；如果后端实现或中间代理输出无空格格式，前端会把合法 data 行当作非 data 行跳过。

**影响**: 合法的 `agent_turn` 或 `[DONE]` 事件可能被静默忽略，用户侧表现为空回复或流状态异常，开发侧也看不到明确协议错误。

**修复记录**:

- 2026-06-17: SSE 行解析改为识别 `data:` 前缀，并对冒号后的可选空格做归一化；注释行、`event:` 等非 data 行仍保持忽略。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts -t "应接受冒号后不带空格的 SSE data 行"`，修复前失败，结果数组为空。
- 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts -t "应接受冒号后不带空格的 SSE data 行"`，1 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts`，38 passed。
- 验证: `cd tools/new-agents/frontend && npm test`，25 files / 202 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；主入口 chunk 334.45 kB，large chunk warning 未回归。

### P1: Agent Runtime SSE adapter 不支持标准多行 data 事件

**现象**: SSE 规范允许同一个 event 包含多条 `data:` 字段，并在空行处把这些 data 行用换行拼接成一个事件 payload。前端 Agent Runtime adapter 原先把每一条 `data:` 行都当作完整 JSON 事件解析；当代理或后端按标准格式把一个 JSON event 拆成多行 `data:` 时，第一行就会触发 `结构化智能体 SSE 数据格式错误`。

**影响**: 合法 SSE 流可能被误判为协议损坏，用户侧看到结构化智能体错误；这也让前端无法兼容更标准的 SSE encoder 或中间层重写后的事件格式。

**修复记录**:

- 2026-06-18: `generateResponseStreamViaAgentRuntime()` 改为按 SSE event 聚合 `data:` 行，在空行或流结束时 flush payload；同一 event 的多条 data 行用 `\n` 拼接后再解析。
- 2026-06-18: 为兼容既有后端/测试中的连续单行 `data:` 事件，当前一条 pending payload 已是完整 JSON 或下一条是 `[DONE]` 时，会先 flush 前一条，再处理新 data 行。
- 测试: 已更新 `llm.test.ts`，覆盖一个 `agent_turn` JSON 被拆成 4 条 `data:` 行并以空行结束时，前端仍能解析为正常 stream chunk。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts -t "多行 data"`，修复前失败为 `结构化智能体 SSE 数据格式错误`。
- 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts -t "多行 data"`，1 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts`，50 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts src/services/__tests__/chatService.test.ts`，2 files / 88 tests passed。
- 验证: `cd tools/new-agents/frontend && npm test`，25 files / 248 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；主入口 chunk 336.13 kB，large chunk warning 未回归。

### P1: Agent Runtime 200 响应缺少 stream body 时错误不可诊断

**现象**: 前端 `generateResponseStreamViaAgentRuntime()` 对 `response.body` 使用非空断言并直接调用 `getReader()`。当浏览器、代理或测试环境返回 `200 OK` 但没有流式 body 时，会抛出 `Cannot read properties of null (reading 'getReader')` 这类低层 TypeError。

**影响**: 用户侧只看到不可理解的错误文本，无法判断是后端没有返回 SSE stream、网关吞掉 body，还是前端协议处理失败。

**修复记录**:

- 2026-06-17: 在读取 SSE 前显式检查 `response.body`，缺失时抛出 `结构化智能体响应缺少流式内容`。
- 测试: 新增 `llm.ts` 单测覆盖 `ok: true` 但 `body: null` 的响应，要求返回明确错误。
- 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts`，27 passed。
- 验证: `cd tools/new-agents/frontend && npm test`，25 files / 191 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；主入口 chunk 保持 334.41 kB，large chunk warning 未回归。

### P1: Agent Runtime 非 200 错误字段为对象时错误不可诊断

**现象**: 前端 `generateResponseStreamViaAgentRuntime()` 在处理非 200 响应时直接使用 `err.error || '结构化智能体请求失败'` 构造 `Error`。如果后端或网关返回 `{ error: { code, message } }` 这类结构化错误，用户侧会看到 `[object Object]`，而不是具体错误文案。

**影响**: 默认 LLM 缺失、认证失败、网关错误或后端结构化错误经过非字符串 `error` 包装时，会丢失可诊断 message，用户和开发者难以判断真实失败原因。

**修复记录**:

- 2026-06-18: 新增 `getHttpErrorMessage()`，非 200 响应会稳定提取字符串 `error`、对象型 `error.message`、对象型 `error.error` 或顶层 `message`；其他畸形 JSON 和非 JSON 响应统一回退到 `结构化智能体请求失败`。
- 测试: 已更新 `llm.ts` 单测，覆盖后端非 200 响应的 `error` 字段为 `{ code, message }` 时，前端抛出对象内 `message`。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts -t "错误字段为对象"`，修复前失败输出为 `[object Object]`，不是期望的 `后端默认 LLM 未配置`。
- 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts -t "错误字段为对象"`，1 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts`，49 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts src/services/__tests__/chatService.test.ts`，2 files / 81 tests passed。
- 验证: `cd tools/new-agents/frontend && npm test`，25 files / 238 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；主入口 chunk 335.14 kB，large chunk warning 未回归。

### P1: 畸形 typed SSE event 会变成 TypeError 或空错误

**现象**: 前端 `parseAgentRuntimeEvent()` 原先只做 `JSON.parse` 并把结果断言为 `AgentRuntimeEvent`。如果服务端或代理返回 `{"type":"agent_turn"}` 这类缺少 `output` 的事件，会在后续读取 `artifact_update` 时抛 TypeError；如果 `{"type":"error","code":"LLM_ERROR"}` 缺少 `message`，会抛出空错误；如果 `{"type":"error","message":"failed"}` 缺少后端契约必填的 `code`，前端会把它当成合法错误并丢失错误分类。即使 `output` 存在，缺少 `chat` 或 `artifact_update` 也会继续穿透到下游并变成 `trim` / `type` 读取异常；`chat` 为空白时还会渲染空助手消息。畸形 `stage_action` 会因为 truthy 被直接映射为 `NEXT_STAGE`。即便 `stage_action` 形状合法，只要 `target_stage_id` 不是当前工作流下一阶段，前端也不应触发阶段流转。`artifact_update.type="none"` 携带 markdown 会被静默忽略，`replace` 携带空 markdown 则可能把右侧产物清空。

**影响**: Agent Runtime 协议问题无法被定位为 SSE event 格式错误，用户侧和开发侧都只能看到低层异常或空错误文本。

**修复记录**:

- 2026-06-17: `parseAgentRuntimeEvent()` 在 JSON 解析后增加运行时 shape 校验，未知事件类型、缺失 `agent_turn.output`、缺失或空 `error.message` 都统一抛出 `结构化智能体 SSE 事件格式错误`。
- 2026-06-17: 继续补齐 `agent_turn.output` 内部字段校验，缺少 `chat`、`chat` 为空白、缺少 `artifact_update`、`artifact_update.type` 非法、`replace` 缺少 `markdown` 也统一走协议格式错误。
- 2026-06-17: 补齐 `artifact_update` 语义校验，`replace` 必须携带非空 markdown，`none` 不能携带非空 markdown，保持与后端 Pydantic 契约一致。
- 2026-06-17: 补齐 `stage_action` 校验，只允许 `null` 或合法的 `request_next_stage + target_stage_id`；缺目标阶段或非法动作类型不再触发 `NEXT_STAGE`。
- 2026-06-17: Agent Runtime adapter 根据当前 workflow/stageIndex 计算期望下一阶段，`stage_action.target_stage_id` 不匹配时抛出 `结构化智能体 SSE 阶段动作目标错误`，避免前端接受不连续跳转。
- 2026-06-18: `error` typed SSE event 现在要求同时包含非空 `code` 和非空 `message`，与后端 `ErrorEvent` 契约保持一致。
- 2026-06-18: 前端抛出 typed SSE error 时保留后端错误分类，错误文本从单独的 `message` 改为 `${code}: ${message}`，例如 `CONTRACT_VALIDATION_FAILED: missing heading`。
- 2026-06-18: 后端 `ErrorEvent` schema 增加空白校验，拒绝 whitespace-only `code` 和 `message`，避免后端继续编码前端会拒绝的畸形 error event。
- 测试: 新增 `llm.ts` 单测覆盖 `agent_turn` 缺 `output`、`error` 缺 `message`、`output` 缺 `chat`、`chat` 为空白、`output` 缺 `artifact_update`、`artifact_update.type="none"` 却包含 markdown、`artifact_update.type="replace"` 但 markdown 为空、`stage_action` 缺 `target_stage_id`、`stage_action.type` 非法、`target_stage_id` 不是下一阶段等畸形 typed event。
- 测试: 已更新后端 `test_sse_encoder.py`，覆盖 `ErrorEvent` 拒绝空白 `code` 和空白 `message`。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts -t "SSE error 事件缺少 code 时应抛出明确协议错误"`，修复前失败输出显示收到的是 `failed`，而不是 `结构化智能体 SSE 事件格式错误`。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts -t "应在 SSE error 抛错中保留后端错误分类 code"`，修复前失败输出显示收到的是 `missing heading`，而不是 `CONTRACT_VALIDATION_FAILED: missing heading`。
- RED 验证: `/Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 - <<'PY' ...`，修复前输出 `AssertionError: blank code was accepted`。
- 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts -t "SSE error 事件缺少 code 时应抛出明确协议错误"`，1 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts -t "应在 SSE error 抛错中保留后端错误分类 code"`，1 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts -t "应在 SSE 流中遇到 error 字段时抛出错误"`，1 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts`，53 passed。
- 验证: `/Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 - <<'PY' ...`，修复后空白 `code` / `message` 均抛出 `ValidationError`，错误分别包含 `error code cannot be blank` 与 `error message cannot be blank`。
- 验证: `/Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 - <<'PY' ...`，合法 `ErrorEvent(code="LLM_ERROR", message="OpenAI API unreachable")` 仍可编码为 typed SSE JSON。
- 验证: `/Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m py_compile tools/new-agents/backend/sse_schemas.py tools/new-agents/backend/sse_encoder.py tools/new-agents/backend/tests/test_sse_encoder.py tools/new-agents/backend/stream_services.py`，通过。
- 验证: `env PYTHONPATH=tools/new-agents/backend /Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -c "..."`，刷新确认空白 `code` / `message` 被拒绝，合法 `ErrorEvent` 仍可 dump 为 `{'type': 'error', 'code': 'LLM_ERROR', 'message': 'OpenAI API unreachable'}`。
- 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts src/services/__tests__/chatService.test.ts`，2 files / 73 tests passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts`，41 passed。
- 验证: `cd tools/new-agents/frontend && npm test`，25 files / 225 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；主入口 chunk 334.58 kB，large chunk warning 未回归。
- 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts`，37 passed。
- 验证: `cd tools/new-agents/frontend && npm test`，25 files / 201 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；主入口 chunk 保持 334.41 kB，large chunk warning 未回归。

### P1: 后端结构化输出契约允许空白 chat

**现象**: 后端 `AgentTurnOutput.chat` 原先只使用 `Field(min_length=1)` 校验，`"   "` 这类只含空白字符的值会通过 Pydantic 模型。前端 typed SSE adapter 已经把空白 `chat` 识别为协议错误，但这意味着坏模型输出会先经过后端 runtime 和 SSE 成功事件，错误边界过晚。

**影响**: PydanticAI 结构化输出重试和后端 `SCHEMA_VALIDATION_FAILED` 错误映射无法在源头接住空白回复；用户侧可能看到前端协议错误，而不是明确的后端模型输出契约失败。

**修复记录**:

- 2026-06-17: `AgentTurnOutput` 增加 `chat` 字段级校验，拒绝只含空白字符的模型回复，并保留原始非空文本。
- 测试: 新增后端契约测试覆盖 `AgentTurnOutput` 拒绝空白 `chat`；新增 runtime 测试覆盖 PydanticAI 返回 dict 形态坏输出时，在 `PydanticAgentRuntime.run_turn(...)` 返回前被拒绝。
- RED 验证: `PYTHONPATH=tools/new-agents/backend /Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 - <<'PY' ...`，修复前输出 `AssertionError: blank chat was accepted`。
- 验证: `PYTHONPATH=tools/new-agents/backend /Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 - <<'PY' ...`，契约直接调用输出 `agent contract rejected blank chat`。
- 验证: `PYTHONPATH=tools/new-agents/backend /Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 - <<'PY' ...`，runtime 直接调用输出 `runtime rejected blank chat`。
- 验证: `/Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m py_compile tools/new-agents/backend/agent_contracts.py tools/new-agents/backend/agent_runtime.py tools/new-agents/backend/tests/test_agent_contracts.py tools/new-agents/backend/tests/test_agent_runtime.py`，通过。
- 当前限制: bundled Python 没有安装 `pytest`，`/Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m pytest --version` 返回 `No module named pytest`，因此本轮未执行后端 pytest。

### P1: 后端结构化 stage_action 目标阶段允许空白字符串

**现象**: 后端 `StageAction.target_stage_id` 原先只使用 `Field(min_length=1)` 校验，`"   "` 这类只含空白字符的值会通过 Pydantic 模型。后续 `validate_agent_turn()` 才会把它当成非法阶段处理，而不是在 typed output schema 边界拒绝。

**影响**: 上游模型输出畸形 `stage_action` 时，错误归类不准确，后端结构化输出契约与前端 typed SSE 协议边界不一致；用户侧可能看到阶段契约错误，而不是明确的结构化输出格式错误。

**修复记录**:

- 2026-06-18: `StageAction.target_stage_id` 增加字段级空白校验，拒绝 whitespace-only 目标阶段，并保留合法阶段 ID 的现有行为。
- 测试: 新增后端契约测试覆盖 `AgentTurnOutput` 拒绝空白 `stage_action.target_stage_id`。
- RED 验证: `/Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 - <<'PY' ...`，修复前输出 `AssertionError: blank target_stage_id was accepted`。
- 验证: `/Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 - <<'PY' ...`，修复后抛出 `ValidationError` 且包含 `target_stage_id cannot be blank`。
- 验证: `/Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 - <<'PY' ...`，合法 `target_stage_id="STRATEGY"` 仍可通过模型校验。
- 验证: `/Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m py_compile tools/new-agents/backend/agent_contracts.py tools/new-agents/backend/tests/test_agent_contracts.py tools/new-agents/backend/agent_runtime.py tools/new-agents/backend/stream_services.py`，通过。
- 当前限制: bundled Python 没有安装 `pytest`，本轮未执行后端 pytest。

### P1: 后端结构化输出契约静默丢弃未知字段

**现象**: `ArtifactUpdate`、`StageAction`、`AgentTurnOutput` 原先没有设置 Pydantic `extra="forbid"`。Pydantic 默认会忽略额外字段，因此模型输出中的 `unexpected_top_level`、`unexpected_nested` 这类 schema 漂移字段会被静默丢弃，再以看似合法的 typed SSE 成功事件进入前端。

**影响**: 结构化输出契约无法识别模型输出漂移。后端看似已经使用 PydanticAI 和 Pydantic schema，但未知字段不会触发重试或 `SCHEMA_VALIDATION_FAILED`，削弱“非法输出不会进入渲染链路”的 P0 目标。

**修复记录**:

- 2026-06-18: `ArtifactUpdate`、`StageAction`、`AgentTurnOutput` 均增加 `ConfigDict(extra="forbid")`，结构化输出中的未知顶层字段、artifact_update 嵌套未知字段、stage_action 嵌套未知字段都会在 Pydantic 边界被拒绝。
- 测试: 已更新 `test_agent_contracts.py`，覆盖 `AgentTurnOutput` 拒绝未知顶层字段、未知 artifact_update 字段和未知 stage_action 字段。
- RED 验证: `env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tools/new-agents/backend /Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -c "..."`，修复前失败输出显示 `unexpected_top_level was accepted and dumped as ...`。
- 验证: `env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tools/new-agents/backend /Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -c "..."`，修复后输出 `rejected unexpected_top_level`、`rejected unexpected_nested`、`rejected unexpected_stage_field`。
- 验证: `env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tools/new-agents/backend /Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -c "..."`，合法 `TEST_DESIGN/CLARIFY` 完整产物仍可通过 `AgentTurnOutput` 与 `validate_agent_turn(...)`。
- 验证: `env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tools/new-agents/backend /Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -c "..."`，JSON 字符串形态的合法 `artifact_update` 仍可解析。
- 验证: `/Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m py_compile tools/new-agents/backend/agent_contracts.py tools/new-agents/backend/tests/test_agent_contracts.py tools/new-agents/backend/agent_runtime.py tools/new-agents/backend/stream_services.py tools/new-agents/backend/sse_schemas.py`，通过。
- 当前限制: bundled Python 没有安装 `pytest`，`/Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m pytest --version` 返回 `No module named pytest`，因此本轮未执行后端 pytest；使用直接契约脚本和 `py_compile` 替代验证。

### P1: PydanticAI 缺依赖时 typed SSE 错误分支不可达

**现象**: `stream_services.py` 原先在模块顶层导入 `pydantic_ai.exceptions`。当运行环境缺少 `pydantic_ai` 时，模块导入阶段就会抛 `ModuleNotFoundError`，因此 `stream_agent_run_events(...)` 中设计好的 `AGENT_RUNTIME_UNAVAILABLE` typed SSE error 分支根本无法执行。

**影响**: 后端依赖缺失时，调用方可能看到应用启动或模块导入失败，而不是结构化 Agent Runtime 的 typed error event。这个边界削弱了“依赖缺失显式错误、不静默失败”的运行时契约。

**修复记录**:

- 2026-06-18: `stream_services.py` 移除对 `pydantic_ai` 的直接导入，只捕获本地 `AgentRuntimeSchemaError` / `AgentRuntimeModelError` / `AgentRuntimeDependencyError`。
- 2026-06-18: `agent_runtime.py` 受控加载 PydanticAI 具体异常类型；运行时将 PydanticAI schema 重试失败映射为 `AgentRuntimeSchemaError`，将模型供应商错误映射为 `AgentRuntimeModelError`，缺少 runtime 依赖仍通过 `AgentRuntimeDependencyError` 报告。
- 2026-06-18: `stream_agent_run_events(...)` 收尾补强 service 边界。即使 direct service 调用绕过 route 层，也会先复用 `parse_agent_run_stream_request(...)` 校验 workflow/stage 契约，非法请求返回 `REQUEST_VALIDATION_FAILED`，且不会创建 runtime 或调用 LLM。
- 2026-06-18: `stream_agent_run_events(...)` 同步捕获 `agent_runtime.PYDANTIC_AI_SCHEMA_ERRORS` 中的原始 schema 异常，避免替代 runtime 或未包装调用路径把 `UnexpectedModelBehavior` 等异常裸露给 SSE 调用方。
- 测试: 已更新 `test_backend_layering.py`，机械约束 `stream_services.py` 不再出现 `from pydantic_ai` 或 `import pydantic_ai`。
- 测试: 已更新 `test_stream_services.py`，stream service 层改为验证本地 runtime 错误类型到 typed SSE error 的映射。
- 测试: 已更新 `test_stream_services.py`，覆盖原始 PydanticAI schema 异常映射为 `SCHEMA_VALIDATION_FAILED`，以及非法 workflow/stage 在 runtime 创建前返回 `REQUEST_VALIDATION_FAILED`。
- 测试: 已更新 `test_agent_runtime.py`，通过 fake schema/model exception 集合验证 `PydanticAgentRuntime.run_turn(...)` 会转换为本地 runtime 错误。
- RED 验证: `env PYTHONDONTWRITEBYTECODE=1 /Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -c "..."` 源码检查，修复前因 `stream_services.py` 包含 `from pydantic_ai` 触发 `AssertionError`。
- RED 验证: `env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tools/new-agents/backend /Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -c "..."`，fake `openai` 后导入 `stream_services`，修复前输出 `ModuleNotFoundError No module named 'pydantic_ai'`。
- 验证: `env PYTHONDONTWRITEBYTECODE=1 /Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -c "..."`，源码检查输出 `stream_services has no direct pydantic_ai import`。
- 验证: `env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tools/new-agents/backend /Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -c "..."`，fake `openai` 后 `import stream_services` 输出 `imported stream_services`。
- 验证: `env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tools/new-agents/backend /Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -c "..."`，缺 `pydantic_ai` 时 `stream_agent_run_events(...)` 输出 typed error `{'type': 'error', 'code': 'AGENT_RUNTIME_UNAVAILABLE', ...}`。
- 验证: `env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tools/new-agents/backend /Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -c "..."`，fake schema/model exception 分别映射为 `AgentRuntimeSchemaError` 和 `AgentRuntimeModelError`。
- 验证: `PYTHONPATH=tools/new-agents/backend /Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 - <<'PY' ...`，fake `openai` 后原始 schema 异常映射为 `SCHEMA_VALIDATION_FAILED`，输出 `raw schema error mapped`。
- 验证: `PYTHONPATH=tools/new-agents/backend /Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 - <<'PY' ...`，fake `openai` 后非法 workflow 和合法 workflow / 不匹配 stage 均在 runtime 创建前返回 `REQUEST_VALIDATION_FAILED`，输出 `stream service boundary checks passed`。
- 验证: `/Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m py_compile tools/new-agents/backend/stream_services.py tools/new-agents/backend/agent_runtime.py tools/new-agents/backend/tests/test_backend_layering.py tools/new-agents/backend/tests/test_stream_services.py tools/new-agents/backend/tests/test_agent_runtime.py`，通过。
- 验证: `git diff --check`，通过。
- 当前限制: bundled Python 没有安装 `pytest`，本轮未执行后端 pytest；同时 bundled Python 缺少 `openai`，直接导入 `stream_services` 的替代验证使用 fake `openai` 隔离 PydanticAI 缺依赖边界。

### P1: 后端 SSE envelope schema 静默丢弃未知字段

**现象**: `AgentTurnEvent` 和 `ErrorEvent` 原先没有设置 Pydantic `extra="forbid"`。因此 `{"type":"error","code":"LLM_ERROR","message":"failed","error":"legacy"}` 或 `agent_turn` 顶层 `legacy` 字段会被接受并静默丢弃。

**影响**: 后端 typed SSE envelope 的协议漂移无法在 schema 边界暴露；虽然内部 `AgentTurnOutput` 已 forbid extra，但 SSE 顶层仍可能吞掉旧字段或误拼字段，削弱前后端 typed event 契约。

**修复记录**:

- 2026-06-18: `AgentTurnEvent` 和 `ErrorEvent` 增加 `ConfigDict(extra="forbid")`，未知顶层字段会在 Pydantic 边界拒绝。
- 测试: 已更新 `test_sse_encoder.py`，覆盖 `ErrorEvent` 和 `AgentTurnEvent` 拒绝未知顶层字段。
- RED 验证: `env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tools/new-agents/backend /Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -c "..."`，修复前失败输出为 `AssertionError: unknown SSE envelope fields were accepted`。
- 验证: `env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tools/new-agents/backend /Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -c "..."`，修复后输出 `unknown SSE envelope fields rejected`。
- 验证: `/Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m py_compile tools/new-agents/backend/sse_schemas.py tools/new-agents/backend/tests/test_sse_encoder.py`，通过。
- 验证: `git diff --check -- tools/new-agents/backend/sse_schemas.py tools/new-agents/backend/tests/test_sse_encoder.py`，通过。
- 当前限制: bundled Python 没有安装 `pytest`，`/Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m pytest --version` 返回 `No module named pytest`，因此本轮未执行后端 pytest。

### P2: 子智能体分发规则缺少 commit 与输出边界

**现象**: 目标模式 playbook 已鼓励使用子智能体，但 `superpowers:subagent-driven-development` 技能示例包含 worker commit 步骤；仓库规则又要求未经用户明确要求不要 commit。playbook 也缺少统一子智能体返回状态、共享记录文件保护和无子智能体能力时的降级说明。

**影响**: 持续修技术债时，worker 可能误提交、越界修改共享文档，或用不统一的摘要替代可验收证据。主 Agent 后续集成和验证成本会上升，也更容易丢失 explorer 发现的候选。

**修复记录**:

- 2026-06-18: `docs/strategy/goal-mode-playbook.md` 明确满足默认触发点时应分发子智能体，跳过时必须记录原因；同时声明 AI4SE 仓库规则覆盖技能示例中的自动 commit 行为，worker 不得创建 commit，除非用户本轮明确要求提交。
- 2026-06-18: `docs/strategy/goal-mode-playbook.md` 增加共享文件保护和无子智能体能力时的降级规则。
- 2026-06-18: 旧技术债专项规则曾增加 worker 不创建 commit 的专项约束，并要求子智能体统一返回 `status: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED`、读取/修改文件、验证结果和残余风险。
- 2026-06-25: 技术债专项规则已退役；子智能体调度、worker commit 边界、统一返回状态和验收规则统一收敛到 `docs/strategy/goal-mode-subagents.md`。
- 2026-06-18: `AGENTS.md` 增加 Codex goal mode 下子智能体分发、审查、验证和记录规则的交叉引用。
- 验证: `rg -n "worker 不得创建 commit|统一状态|Codex goal mode|满足下列默认触发点|不得同时修改 worker" AGENTS.md docs/strategy/goal-mode-playbook.md docs/strategy/goal-mode-subagents.md`，命中新增规则。
- 验证: `git diff --check -- AGENTS.md docs/strategy/goal-mode-playbook.md docs/strategy/goal-mode-subagents.md`，通过。

### P1: Artifact 模板标题校验会误接受正文或代码块中的标题文本

**现象**: 后端 `validate_artifact_template()` 原先只用 `heading in markdown` 判断必需标题是否存在。模型只要在普通段落或 fenced code block 中列出 `# 需求分析文档`、`## 1. 被测系统与边界` 等字符串，即使没有生成真实 Markdown 标题结构，也会通过后端契约校验。

**影响**: 结构化 Agent Runtime 可能把“描述模板”或“代码块里的模板示例”当成合格产物放行，导致前端右侧 Artifact 看起来像一段说明而不是可交付文档；PydanticAI 输出契约的应用级校验也因此失真。

**修复记录**:

- 2026-06-18: `validate_artifact_template()` 改为先移除 fenced code block，再提取真实 Markdown heading 行。以 `#` 开头的必需项必须作为真实 heading 行出现；非 `#` 开头的契约词仍在去除代码块后的正文中查找，避免误伤 `60 秒电梯演讲` 等非标题要求。
- 2026-06-18: `build_artifact_contract_prompt()` 同步说明标题必须是真实 Markdown 标题行，不能只放在正文描述或代码块中。
- 测试: 已更新 `test_agent_contracts.py`，覆盖 `TEST_DESIGN/CLARIFY` 的必需标题只出现在 fenced code block 时必须抛出 `ContractValidationError`。
- RED 验证: `PYTHONPATH=tools/new-agents/backend /Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 - <<'PY' ...`，修复前输出 `AssertionError: headings inside code block were accepted`。
- 验证: `PYTHONPATH=tools/new-agents/backend /Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 - <<'PY' ...`，代码块标题被拒绝、所有完整阶段模板仍通过、契约 prompt 包含真实标题行要求，输出 `artifact heading boundary checks passed`。
- 验证: `/Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m py_compile tools/new-agents/backend/agent_contracts.py tools/new-agents/backend/tests/test_agent_contracts.py tools/new-agents/backend/agent_runtime.py tools/new-agents/backend/stream_services.py`，通过。
- 当前限制: bundled Python 没有安装 `pytest`，本轮未执行后端 pytest。

### P1: VALUE_DISCOVERY/BLUEPRINT 缺少 H1 需求蓝图标题仍会通过契约校验

**现象**: `VALUE_DISCOVERY/BLUEPRINT` 的必需项原先把 `需求蓝图` 配成普通正文关键词。`validate_artifact_template()` 对非 `#` 开头条目只检查关键词是否出现在去除代码块后的正文中，因此模型只要在普通段落中写到“需求蓝图”，即使完全没有 `# [产品名称] 需求蓝图` 这类真实 H1 标题，也会通过后端结构化产出物契约。

**影响**: 价值发现最终阶段可能放行没有顶层标题的“需求蓝图”文档，前端 Artifact 看起来像章节片段而不是完整需求蓝图；也削弱了“后端应用级契约保证 Artifact 最低结构完整”的目标。

**修复记录**:

- 2026-06-18: 后端新增 `REQUIRED_ARTIFACT_H1_KEYWORDS`，对 `VALUE_DISCOVERY/BLUEPRINT` 要求真实 H1 标题行包含 `需求蓝图`；保留原有非标题正文关键词逻辑，避免误伤 `60 秒电梯演讲`、痛点优先级等正文要求。
- 2026-06-18: `build_artifact_contract_prompt()` 同步输出 H1 关键词要求，明确 BLUEPRINT 阶段必须生成包含 `需求蓝图` 的真实 H1 标题。
- 2026-06-18: `test_agent_contracts.py` 增加 `test_validate_agent_turn_rejects_blueprint_without_h1_heading`，覆盖正文提到“需求蓝图”但缺少 H1 时必须抛出 `ContractValidationError`；完整模板测试同步使用 `# 产品需求蓝图` 验证动态产品名 H1 可通过。
- RED 验证: `PYTHONPATH=tools/new-agents/backend /Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -c "..."`，修复前输出 `AssertionError: blueprint without H1 was accepted`。
- RED 验证: `PYTHONPATH=tools/new-agents/backend /Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -c "..."`，修复前输出 `AssertionError: BLUEPRINT contract prompt does not mention H1 标题`。
- 验证: `PYTHONPATH=tools/new-agents/backend /Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -c "..."`，无 H1 的 BLUEPRINT 被拒绝，输出 `blueprint without H1 rejected`。
- 验证: `PYTHONPATH=tools/new-agents/backend /Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -c "..."`，契约 prompt 包含 `H1 标题` 和 `需求蓝图`，输出 `blueprint prompt mentions H1`。
- 验证: `PYTHONPATH=tools/new-agents/backend /Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -c "..."`，所有 `REQUIRED_ARTIFACT_HEADINGS` 完整模板仍通过，输出 `all complete artifact templates accepted`。
- 验证: `/Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m py_compile tools/new-agents/backend/agent_contracts.py tools/new-agents/backend/tests/test_agent_contracts.py tools/new-agents/backend/agent_runtime.py tools/new-agents/backend/stream_services.py`，通过。
- 当前限制: bundled Python 仍没有安装 `pytest`，`/Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m pytest --version` 返回 `No module named pytest`，因此本轮未执行后端 pytest。

### P1: 后端 chat/artifact 分离校验误杀普通 graph 文本

**现象**: `AgentTurnOutput.validate_chat_artifact_separation()` 为了防止模型把完整 Artifact Markdown 放进 `chat`，会扫描 `sequenceDiagram`、`flowchart`、`graph` 等 Mermaid 关键词。但原先 `flowchart\s+` / `graph\s+` 没有锚定行首，导致普通短说明里出现 `dependency graph` 这类英文词组时也被拒绝。

**影响**: 模型返回“已更新右侧文档，dependency graph 已补充到产出物中。”这类合法短说明时，即使 `artifact_update.markdown` 合法，后端也会抛出 `chat must not contain artifact markdown`。用户看到的是结构化输出失败，而不是正常的产物更新。

**修复记录**:

- 2026-06-18: `sequenceDiagram`、`flowchart`、`graph` 的 chat 分离校验改为只匹配行首 Mermaid 片段；普通正文中的 `dependency graph` 不再触发 artifact markdown 误判。
- 2026-06-18: `test_agent_contracts.py` 增加 `test_agent_turn_output_allows_ordinary_graph_wording_in_chat`，覆盖 artifact 更新时 chat 可包含普通 `dependency graph` 短语；同步增加行首 `graph TD`、`flowchart LR`、`sequenceDiagram` 仍必须拒绝的参数化测试，避免过度放宽。
- RED 验证: `PYTHONPATH=tools/new-agents/backend /Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -c "..."`，修复前失败并抛出 `chat must not contain artifact markdown`。
- 验证: `PYTHONPATH=tools/new-agents/backend /Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -c "..."`，普通 `dependency graph` 短句被接受，输出 `ordinary graph wording accepted`。
- 验证: `PYTHONPATH=tools/new-agents/backend /Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -c "..."`，普通 `dependency graph` / `flowchart` / `sequenceDiagram` 短句被接受，行首 `graph TD` / `flowchart LR` / `sequenceDiagram` Mermaid 片段仍被拒绝，输出 `mermaid chat boundaries ok`。
- 验证: `/Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m py_compile tools/new-agents/backend/agent_contracts.py tools/new-agents/backend/tests/test_agent_contracts.py`，通过。
- 当前限制: bundled Python 仍没有安装 `pytest`，本轮用直接脚本验证契约行为，未执行后端 pytest。

### P1: URL 中 agentId 与 workflow 归属不一致时工作区状态错位

**现象**: `Workspace` 只根据 `workflowId` 设置当前 workflow，不校验 URL 中的 `agentId`。例如 `/workspace/lisa/idea-brainstorm` 会进入 Alex 的创意头脑风暴 workflow，但 Header 仍按 URL 中的 Lisa 计算返回路径和头像信息。

**影响**: 深链、手工输入 URL 或历史链接可能进入 agent 与 workflow 不一致的工作区，导致返回路径、页面上下文和后续导航错乱。

**修复记录**:

- 2026-06-17: `Workspace` 现在校验 `workflowId` 对应 workflow 的 owning `agentId`；如果 URL agent 不一致，会 `replace` 到规范 URL，例如 `/workspace/lisa/idea-brainstorm` 自动替换为 `/workspace/alex/idea-brainstorm`。
- 2026-06-17: 未知 workflow slug 会替换回首页，避免进入无效工作区状态。
- 测试: 新增 `Workspace` 页面测试，覆盖 workflow slug 归属 agent 与 URL agent 不一致时自动重定向。
- 验证: `cd tools/new-agents/frontend && npm test -- src/pages/__tests__/Workspace.test.tsx`，3 passed。
- 验证: `cd tools/new-agents/frontend && npm test`，25 files / 184 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；当时仍有既有大 chunk warning，已在下方独立性能债中修复。

### P1: ChatPane 顶部标题未跟随当前工作流

**现象**: `ChatPane` 已经根据当前 `workflow` 和 owning agent 显示副标题，例如 `Alex 创新顾问 正在为您服务`，但顶部主标题硬编码为 `智能需求分析`。切到 `价值发现`、`创意头脑风暴`、`故障复盘` 等非测试设计工作流后，聊天区主标题仍显示错误上下文。

**影响**: 多工作流入口下，用户会看到当前 Agent 和输入 placeholder 已切换，但聊天区主标题仍指向需求分析，削弱工作流上下文一致性。

**修复记录**:

- 2026-06-18: `ChatPane` 顶部主标题改为 `WORKFLOWS[workflow].name`，与当前工作流保持一致；欢迎区原有工作流标题保持不变。
- 测试: 已更新 `ChatPane.test.tsx`，覆盖 `VALUE_DISCOVERY` 且已有聊天历史时，顶部 heading 显示 `价值发现`，不再显示 `智能需求分析`。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/components/__tests__/ChatPane.test.tsx -t "active workflow name"`，修复前失败输出显示唯一 heading 为 `智能需求分析`。
- 验证: `cd tools/new-agents/frontend && npm test -- src/components/__tests__/ChatPane.test.tsx -t "active workflow name"`，1 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/components/__tests__/ChatPane.test.tsx`，15 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/agentCore.test.ts src/components/__tests__/ChatPane.test.tsx src/__tests__/store.test.ts src/services/__tests__/chatService.test.ts`，4 files / 89 tests passed。
- 验证: `cd tools/new-agents/frontend && npm test`，26 files / 270 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；主入口 chunk 336.59 kB，large chunk warning 未回归。

### P1: 推荐问题发送会保留旧输入草稿并误用草稿附件

**现象**: ChatPane 欢迎区的 starter prompt 直接调用 `handleSend(prompt)`。`chatService` 会发送覆盖输入的推荐问题，但只在普通输入发送时清空 `input`，因此用户原来输入框里的未发送草稿会继续留在输入框中。同时覆盖发送默认使用 `pendingAttachments`，如果用户已经选择了附件，点击推荐问题会把草稿附件附加到推荐问题上并清空附件列表。

**影响**: 用户点击推荐问题后可能误以为输入框中的旧草稿已经发送，随后再次发送会产生重复或上下文错乱；草稿附件也可能被错误地发送到推荐问题请求中，破坏用户预期和 Agent 上下文。

**修复记录**:

- 2026-06-18: `handleSend()` 对会追加用户消息的 override send 同样清空输入草稿，保留 `appendUserMessage:false` 的阶段续写不清空用户草稿。
- 2026-06-18: ChatPane starter prompt 调用改为 `handleSend(prompt, { useDraftAttachments: false })`，推荐问题不再消费待上传草稿附件。
- 测试: 已更新 `chatService.test.ts`，覆盖 override starter prompt 发送后清空旧输入草稿。
- 测试: 已更新 `ChatPane.test.tsx`，覆盖 starter prompt 按钮调用 `handleSend` 时传入 `useDraftAttachments:false`。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts -t "override starter prompt"`，修复前失败输出为 `expected '用户尚未发送的草稿' to be ''`。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/components/__tests__/ChatPane.test.tsx -t "starter prompts"`，修复前失败显示 `handleSend` 只收到 prompt，未收到 `{ useDraftAttachments: false }`。
- 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts -t "override starter prompt"`，1 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/components/__tests__/ChatPane.test.tsx -t "starter prompts"`，1 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts src/components/__tests__/ChatPane.test.tsx`，2 files / 58 tests passed。
- 验证: `cd tools/new-agents/frontend && npm test`，26 files / 272 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；主入口 chunk 336.59 kB，large chunk warning 未回归。
- 验证: `git diff --check`，通过。

### P1: 首个响应 chunk 前停止生成没有用户反馈

**现象**: 用户点击“停止生成”后，如果模型还没有返回首个 chunk，`chatService` 的 abort 分支不会追加 assistant 消息，最终对话里只留下用户消息，看起来像请求悄悄消失。

**影响**: 用户无法判断停止操作是否生效，尤其是在后端 Agent Runtime 首包较慢时体验明显。

**修复记录**:

- 2026-06-17: `chatService` 在收到 `Aborted by user` 且尚未创建 assistant chunk 时，会新增一条 `*(已停止生成)*` assistant 消息；中途停止仍保持原有追加提示行为。
- 2026-06-17: 同步识别真实浏览器 `fetch` abort 抛出的 `DOMException` / `AbortError`，避免首包前停止被错误渲染为 `**Error:** Something went wrong.`。
- 测试: 新增 `useChatService` hook 测试，模拟首包前 abort 与 DOM `AbortError`，覆盖停止后 `isGenerating=false`、对话中出现停止提示且不渲染 `**Error:**`。
- 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts`，15 passed。
- 验证: `cd tools/new-agents/frontend && npm test`，25 files / 186 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；当时仍有既有大 chunk warning，已在下方独立性能债中修复。

### P1: 中途停止后部分产物未标记截断且会保存为正常版本

**现象**: 流式生成已经写入过 artifact update 后，如果用户停止生成，`chatService` 的 abort 分支只会追加 `*(已停止生成)*`，不会把当前产物标记为截断；`finally` 仍会把本轮最后一次 artifact update 写入 `artifactHistory`。

**影响**: 右侧产物实际可能只是被用户中止的部分内容，但 UI 不显示截断警告，版本历史也会把它当成正常完整版本。后续用户回看版本或继续生成时，容易误判该产物已经完整。

**修复记录**:

- 2026-06-18: `handleSend()` 在 abort 分支识别本轮已经写入过 artifact 时同步设置 `artifactTruncated: true`；版本历史保存分支新增 `!wasRunAborted` 条件，用户停止后的部分产物不再进入正常 artifact history。
- 测试: 已更新 `chatService` hook 测试，覆盖先收到 artifact update、随后 abort 的中途停止场景，确认右侧保留部分产物、截断标记为 true，并且 artifact history 不新增正常版本。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts -t "partially updated artifact"`，修复前失败输出显示 `artifactTruncated` 仍为 `false`。
- 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts -t "partially updated artifact"`，1 passed / 37 skipped。
- 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts`，38 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts src/components/__tests__/ArtifactPane.test.tsx src/__tests__/store.test.ts src/core/__tests__/agentCore.test.ts src/__tests__/p0-fixes.test.ts src/core/__tests__/llm.test.ts`，6 files / 129 tests passed。
- 验证: `cd tools/new-agents/frontend && npm test`，25 files / 246 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；主入口 chunk 336.11 kB，large chunk warning 未回归。

### P1: 非中止流式错误后部分产物会保存为正常版本

**现象**: 流式生成已经写入过 artifact update 后，如果随后发生非 abort 错误，例如 Agent Runtime 连接中断、协议错误或模型调用异常，`chatService` 会在聊天中追加错误信息，但不会把当前产物标记为截断；`finally` 还会把本轮最后一次 artifact update 写入 `artifactHistory`，作为正常版本保存。

**影响**: 右侧产物可能只是失败流中的部分内容，但 UI 不显示截断警告，版本历史也会把它当成完整结果。用户后续导出、回看版本或继续生成时，容易误用未完成产物。

**修复记录**:

- 2026-06-18: `handleSend()` 增加普通失败标记；非 abort 错误发生且本轮已经写入 artifact 时，同步设置 `artifactTruncated: true`，并阻止该部分产物进入正常 artifact history。中止生成路径继续使用既有 `wasRunAborted` 语义。
- 测试: 已更新 `chatService` hook 测试，覆盖先收到 artifact update、随后抛出普通错误时，聊天保留错误信息、右侧保留部分产物、截断标记为 true，且 artifact history 不新增正常版本。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts -t "stream errors after an artifact update"`，修复前失败输出显示 `artifactTruncated` 为 `false`。
- 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts -t "stream errors after an artifact update"`，1 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts`，43 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts src/__tests__/store.test.ts src/core/__tests__/agentCore.test.ts src/components/__tests__/ArtifactPane.test.tsx`，4 files / 82 tests passed。
- 验证: `cd tools/new-agents/frontend && npm test`，26 files / 273 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；主入口 chunk 336.59 kB，large chunk warning 未回归。
- 验证: `git diff --check`，通过。

**后续候选记录**:

- 只读 explorer 曾发现: 旧兼容 action `transitionToNextStage(...)` 成功推进阶段时仍未清理 `pendingStageTransition`、`artifactTruncated` 和 `isGenerating` 等派生状态；该候选已在 2026-06-18 修复，见上方“Legacy 阶段切换成功后派生状态残留”。
- 只读 explorer 曾发现: `stream_services.py` 顶层导入 `pydantic_ai.exceptions`，当前 bundled Python 缺少 `pydantic_ai` 时，设计中的 `AGENT_RUNTIME_UNAVAILABLE` typed SSE error 分支可能在模块导入前就不可达；该候选已在 2026-06-18 修复，见上方“PydanticAI 缺依赖时 typed SSE 错误分支不可达”。
- 只读 explorer 曾发现: `ArtifactUpdate`、`StageAction`、`AgentTurnOutput` 未设置 `extra="forbid"`，Pydantic 默认会静默丢弃未知字段；该候选已在 2026-06-18 修复，见上方“后端结构化输出契约静默丢弃未知字段”。
- 只读 explorer 曾发现: 前序阶段 artifact 的 `<mark>` UI 高亮标签会污染下一阶段 prompt；该候选已在 2026-06-18 修复，见上方“前序阶段 `<mark>` 高亮标签污染下一阶段 Prompt”。
- 只读 explorer 曾发现: legacy `transitionToNextStage()` 仍会把来源阶段 artifact 写入目标阶段 `stageArtifacts[nextStageId]`，导致目标阶段显示/保存上一阶段内容；该候选已在 2026-06-18 修复，见上方“Legacy 阶段切换会把来源产物复制到目标阶段”。
- 只读 explorer 曾发现: 流式错误或停止反馈会作为助手历史注入下一轮 Agent prompt；该候选已在 2026-06-18 修复，见上方“错误和停止控制反馈会污染下一轮 Runtime Prompt”。
- 只读 explorer 曾发现: artifact history 仍是全局列表，跨阶段混在当前阶段历史弹窗中；该候选已在 2026-06-18 修复，见上方“Artifact 历史版本跨阶段混在当前阶段弹窗里”。
- 只读 explorer 曾发现: Agent Runtime artifact 预校验路径仍会把 `mermaid-js` 当 Mermaid；该候选已在 2026-06-18 修复，见下方“Mermaid fence 语言识别过宽导致误渲染和误替换”。
- 只读 explorer 曾发现: typed SSE error 的 `code` 被前端丢弃，用户侧只剩 `message`；该候选已在 2026-06-18 修复，见上方“畸形 typed SSE event 会变成 TypeError 或空错误”。
- 只读 explorer 曾发现: 后端 SSE envelope schema 未设置 `extra="forbid"`；该候选已在 2026-06-18 修复，见上方“后端 SSE envelope schema 静默丢弃未知字段”。
- 只读 explorer 曾发现: 阶段确认后的内部续写没有可重试上下文，Retry 可能退回上一条真实用户消息；该候选已在 2026-06-18 修复，见上方“阶段确认内部续写后的重试会回退上一条真实用户输入”。

### P1: 清空或切换工作区时不会立即取消旧 Agent 请求

**现象**: 用户在 Agent Runtime 首包返回前点击新会话、切换工作流或手动切换阶段时，`clearHistory()`、`setWorkflow()`、`setStageIndex()` 只会把 `isGenerating` 复位为 `false`，不会立即调用当前请求的 `AbortController.abort()`。旧流要等到下一次 chunk 到达后才会被 stale guard 发现并取消。

**影响**: UI 已允许用户开始新请求，但旧后端 LLM run 仍可能继续占用额度、连接和并发；如果模型首包很慢，用户也没有显式入口取消这个已经离开当前工作区上下文的旧请求。

**修复记录**:

- 2026-06-18: `useChatService()` 增加 store 订阅。当外部工作区动作把 `isGenerating` 从 `true` 复位为 `false`，且当前 hook 仍持有 active `AbortController` 时，立即 abort 当前请求；正常完成路径会先清空 controller ref，不会误触发取消。
- 测试: 已更新 `chatService` hook 测试，覆盖清空历史、切换工作流、手动切换阶段三种外部重置动作都会立即把当前请求的 `AbortSignal` 标记为 aborted。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts -t "abort an in-flight request immediately"`，修复前失败输出显示清空历史后 `capturedSignal.aborted` 仍为 `false`。
- 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts -t "abort an in-flight request immediately"`，3 passed / 33 skipped。
- 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts`，36 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts src/components/__tests__/ChatPane.test.tsx src/__tests__/store.test.ts src/core/__tests__/agentCore.test.ts src/__tests__/p0-fixes.test.ts`，5 files / 85 tests passed。
- 验证: `cd tools/new-agents/frontend && npm test`，25 files / 244 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；主入口 chunk 336.11 kB，large chunk warning 未回归。

### P1: 切换工作流后截断警告状态残留

**现象**: Agent Runtime 返回 `artifactTruncated` 后，右侧产出物面板会显示截断警告。`clearHistory()` 已重置该状态，但 `setWorkflow()` 只清空对话、阶段和产出物，没有重置 `artifactTruncated`。用户从一个发生过截断的工作流切换到另一个工作流后，新工作流的欢迎产出物仍可能显示旧的截断警告。

**影响**: 用户会误以为新工作流当前产出物已经被截断，造成状态误导；后续 prompt 也可能在没有真实截断的上下文中携带错误的“已截断”提示。

**修复记录**:

- 2026-06-17: `setWorkflow()` 在重置 workflow、stage、chat history、artifact history、artifact content 和 pending transition 时同步重置 `artifactTruncated: false`。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/__tests__/store.test.ts`，修复前失败输出显示切换到 `REQ_REVIEW` 后 `artifactTruncated` 仍为 `true`。
- 验证: `cd tools/new-agents/frontend && npm test -- src/__tests__/store.test.ts`，3 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/__tests__/p0-fixes.test.ts src/__tests__/store.test.ts src/components/__tests__/ArtifactPane.test.tsx`，3 files / 20 tests passed。
- 验证: `cd tools/new-agents/frontend && npm test`，25 files / 204 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；主入口 chunk 334.47 kB，large chunk warning 未回归。

### P1: 手动切换阶段后截断警告状态残留

**现象**: 用户在同一个工作流内手动切换阶段时，`setStageIndex()` 会保存当前阶段 artifact 并加载目标阶段 artifact，但不会重置全局 `artifactTruncated`。如果上一阶段生成曾被标记为截断，切到另一个阶段后右侧产出物仍会显示旧截断警告。

**影响**: 阶段间浏览会出现错误的产出物完整性提示；用户可能误判目标阶段产物不完整，后续 Agent prompt 也可能在错误的截断状态下构建。

**修复记录**:

- 2026-06-17: `setStageIndex()` 在切换阶段并加载目标阶段 artifact 时同步重置 `artifactTruncated: false`。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/__tests__/store.test.ts`，修复前失败输出显示手动切到阶段 1 后 `artifactTruncated` 仍为 `true`。
- 验证: `cd tools/new-agents/frontend && npm test -- src/__tests__/store.test.ts`，4 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/__tests__/p0-fixes.test.ts src/__tests__/store.test.ts src/components/__tests__/ArtifactPane.test.tsx`，3 files / 21 tests passed。
- 验证: `cd tools/new-agents/frontend && npm test`，25 files / 205 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；主入口 chunk 334.49 kB，large chunk warning 未回归。

### P1: 手动切换阶段后旧阶段确认卡片残留

**现象**: 当前阶段生成 `NEXT_STAGE` 后会设置 `pendingStageTransition` 并在聊天区展示“确认进入下一阶段”卡片。用户如果没有点确认，而是通过顶部阶段条手动切到其他阶段，`setStageIndex()` 原先不会清除 pending transition，旧确认卡片会继续显示。

**影响**: 用户会在非来源阶段看到旧阶段的确认入口，容易误以为当前阶段仍需要进入旧目标阶段。虽然服务层已有 stale pending 防护，不会真正回退并续写，但 UI 仍会误导工作流状态。

**修复记录**:

- 2026-06-17: `setStageIndex()` 在用户手动切换阶段时同步清除 `pendingStageTransition`，让旧阶段确认卡片立即失效。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/__tests__/store.test.ts`，修复前失败输出显示手动切到阶段 2 后 `pendingStageTransition` 仍为 `{ fromStageIndex: 0, toStageIndex: 1 }`。
- 验证: `cd tools/new-agents/frontend && npm test -- src/__tests__/store.test.ts`，5 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/__tests__/p0-fixes.test.ts src/core/__tests__/agentCore.test.ts src/services/__tests__/chatService.test.ts src/components/__tests__/ChatPane.test.tsx src/__tests__/store.test.ts`，5 files / 60 tests passed。
- 验证: `cd tools/new-agents/frontend && npm test`，25 files / 206 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；主入口 chunk 334.52 kB，large chunk warning 未回归。

### P1: 用户继续发新消息后旧阶段确认卡片残留

**现象**: 当前阶段生成 `NEXT_STAGE` 后会设置 `pendingStageTransition`。用户如果不点击“暂不进入/确认进入”，而是直接继续补充信息并发送新消息，旧 pending transition 不会被清除；新一轮普通回复完成后，聊天区仍显示上一轮“确认进入下一阶段”卡片。

**影响**: 用户会在新的对话上下文下继续看到旧阶段推进建议，容易基于过期建议进入下一阶段；这会让工作流状态和用户刚补充的上下文发生错位。

**修复记录**:

- 2026-06-18: `handleSend()` 在真实用户消息轮次开始时清理旧 `pendingStageTransition`；阶段确认内部续写使用 `appendUserMessage: false`，不受该清理影响。本轮 Agent 如果再次返回 `NEXT_STAGE`，仍会设置新的 pending transition。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts -t "should clear a previous pending stage transition"`，修复前失败输出显示 `pendingStageTransition` 仍为 `{ fromStageIndex: 0, toStageIndex: 1 }`。
- 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts -t "should clear a previous pending stage transition"`，1 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts`，40 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts src/components/__tests__/ChatPane.test.tsx src/__tests__/store.test.ts src/core/__tests__/agentCore.test.ts`，4 files / 81 tests passed。
- 验证: `cd tools/new-agents/frontend && npm test`，26 files / 261 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；主入口 chunk 336.20 kB，large chunk warning 未回归。
- 验证: `git diff --check`，通过。

### P1: 生成中切换工作流后旧流写入新工作区

**现象**: `handleSend()` 原先在每个流式 chunk 到达时重新读取当前 store 的 `workflow` 和 `stageIndex`，再决定 artifact 写入目标。用户如果在旧请求首个 chunk 到达前切换到另一个 workflow，旧请求返回后会按新 workflow 的当前阶段追加 assistant 消息并写入 artifact。

**影响**: 旧智能体请求可能污染新工作流的对话和右侧产出物，表现为切换到需求评审后却看到测试设计旧请求的回复或文档内容。

**修复记录**:

- 2026-06-17: `handleSend()` 在发送时绑定本次请求的 `workflow`、`stageIndex`、workflow 定义和当前 stageId；后续 chunk 到达时如果 store 已不在同一个 workflow/stage，立即 abort 并丢弃该 chunk，不追加 assistant 消息、不写 artifact。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts -t "should ignore stale stream chunks after switching workflows during generation"`，修复前失败输出显示切换到 `REQ_REVIEW` 后仍追加了 `旧请求回复` assistant 消息。
- 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts -t "should ignore stale stream chunks after switching workflows during generation"`，1 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts`，18 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/__tests__/p0-fixes.test.ts src/core/__tests__/agentCore.test.ts src/services/__tests__/chatService.test.ts src/components/__tests__/ChatPane.test.tsx src/components/__tests__/WorkflowDropdown.test.tsx src/pages/__tests__/Workspace.test.tsx`，6 files / 66 tests passed。
- 验证: `cd tools/new-agents/frontend && npm test`，25 files / 207 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；主入口 chunk 334.52 kB，large chunk warning 未回归。

### P1: 生成中清空历史后旧流写回工作区

**现象**: 用户发送消息后，`handleSend()` 会追加本轮 user message 并等待 Agent Runtime 流式返回。如果用户在首个 chunk 到达前清空历史，workflow/stage 仍可能保持不变；上一条“workflow/stage 绑定”保护无法识别这次 reset，旧流返回后仍会追加 assistant 消息并覆盖欢迎产出物。

**影响**: 用户执行清空后仍看到旧请求回复或旧 artifact 写回，清空操作失去可信度，也可能把旧上下文重新带回后续智能体对话。

**修复记录**:

- 2026-06-17: 普通用户发送时记录本轮 user message id；后续 chunk 到达时如果该 user message 已不在 `chatHistory` 中，说明工作区已被清空或回滚，立即 abort 并丢弃旧 chunk。阶段确认内部续写不追加 user message，仍依赖 workflow/stage 绑定保护。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts -t "should ignore stale stream chunks after clearing history during generation"`，修复前失败输出显示清空后仍追加了 `清空后的旧回复` assistant 消息。
- 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts -t "should ignore stale stream chunks after clearing history during generation"`，1 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts`，19 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/__tests__/p0-fixes.test.ts src/__tests__/store.test.ts src/core/__tests__/agentCore.test.ts src/services/__tests__/chatService.test.ts src/components/__tests__/ChatPane.test.tsx src/components/__tests__/WorkflowDropdown.test.tsx src/pages/__tests__/Workspace.test.tsx`，7 files / 72 tests passed。
- 验证: `cd tools/new-agents/frontend && npm test`，25 files / 208 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；主入口 chunk 334.52 kB，large chunk warning 未回归。

### P1: 首包前清空历史再停止会重新写入停止提示

**现象**: 用户发送消息后、Agent Runtime 首个 chunk 返回前，如果先清空历史再点击停止生成，`handleSend()` 的 abort 分支仍会向已经清空的 `chatHistory` 追加 `*(已停止生成)*` assistant 消息。

**影响**: 用户已经执行清空后仍看到旧请求产生的停止反馈，会让清空操作看起来没有彻底生效；后续对话也会把这条旧请求反馈当成当前会话历史。

**修复记录**:

- 2026-06-17: `handleSend()` 的 abort 反馈复用本轮请求有效性校验；如果当前 workflow/stage 已变化，或普通用户发送对应的 user message 已不在 `chatHistory` 中，则不再追加首包前停止提示。正常首包前手动停止仍保留 `*(已停止生成)*` 用户反馈。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts -t "should not add stopped feedback after clearing history before the first chunk"`，修复前失败输出显示清空后仍追加了 `*(已停止生成)*` assistant 消息。
- 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts -t "should not add stopped feedback after clearing history before the first chunk"`，1 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts`，20 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/__tests__/p0-fixes.test.ts src/__tests__/store.test.ts src/core/__tests__/agentCore.test.ts src/services/__tests__/chatService.test.ts src/components/__tests__/ChatPane.test.tsx src/components/__tests__/WorkflowDropdown.test.tsx src/pages/__tests__/Workspace.test.tsx`，7 files / 73 tests passed。
- 验证: `cd tools/new-agents/frontend && npm test`，25 files / 209 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；主入口 chunk 334.52 kB，large chunk warning 未回归。

### P1: 清空历史后旧流错误会写回空会话

**现象**: 用户发送消息后、Agent Runtime 首个 chunk 返回前清空历史，如果旧请求随后抛出网络、协议或模型错误，`handleSend()` 的非 abort 错误分支仍会向已经清空的 `chatHistory` 追加 `**Error:** ...` assistant 消息。

**影响**: 清空操作后仍会出现旧请求错误反馈，用户会误以为当前新会话发生了错误；旧错误消息也可能进入下一轮 Agent Runtime 历史上下文。

**修复记录**:

- 2026-06-17: `handleSend()` 的错误反馈统一前置本轮请求有效性校验；如果当前 workflow/stage 已变化，或普通用户发送对应的 user message 已不在 `chatHistory` 中，则 abort 与非 abort 错误都不再写回聊天区。当前有效请求的正常错误提示、额度提示和首包前停止提示保持原行为。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts -t "should not add stale error feedback after clearing history before the first chunk"`，修复前失败输出显示清空后仍追加了 `**Error:** LLM_ERROR_AFTER_CLEAR` assistant 消息。
- 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts -t "should not add stale error feedback after clearing history before the first chunk"`，1 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts`，21 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/__tests__/p0-fixes.test.ts src/__tests__/store.test.ts src/core/__tests__/agentCore.test.ts src/services/__tests__/chatService.test.ts src/components/__tests__/ChatPane.test.tsx src/components/__tests__/WorkflowDropdown.test.tsx src/pages/__tests__/Workspace.test.tsx`，7 files / 74 tests passed。
- 验证: `cd tools/new-agents/frontend && npm test`，25 files / 210 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；主入口 chunk 334.52 kB，large chunk warning 未回归。

### P1: 生成中手动切阶段后版本历史保存错误阶段内容

**现象**: `handleSend()` 在本轮流式生成中只用 `didUpdateArtifact` 记录是否曾经写过 artifact，但 `finally` 保存版本历史时重新读取当前全局 `artifactContent`。如果用户在流结束前手动切到另一个阶段，当前 `artifactContent` 会变成目标阶段内容或占位文档，版本历史会保存错误阶段的内容。

**影响**: Artifact 版本历史可能出现与本轮生成无关的阶段占位文档，例如需求分析生成过程中切到策略阶段后，历史记录保存成 `# 策略制定\n\n暂无产出物。`。这会污染用户后续回溯和导出判断。

**修复记录**:

- 2026-06-17: `handleSend()` 在每次真实 artifact 更新时记录 `latestRunArtifactContent`；`finally` 保存版本历史时使用本轮最后一次 artifact 更新内容，而不是当前 UI 展示的全局 `artifactContent`。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts -t "should save artifact history for the run artifact when manually switching stages before stream ends"`，修复前失败输出显示版本历史保存成 `# 策略制定\n\n暂无产出物。`。
- 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts -t "should save artifact history for the run artifact when manually switching stages before stream ends"`，1 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts`，22 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/__tests__/p0-fixes.test.ts src/__tests__/store.test.ts src/core/__tests__/agentCore.test.ts src/services/__tests__/chatService.test.ts src/components/__tests__/ChatPane.test.tsx src/components/__tests__/WorkflowDropdown.test.tsx src/pages/__tests__/Workspace.test.tsx`，7 files / 75 tests passed。
- 验证: `cd tools/new-agents/frontend && npm test`，25 files / 211 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；主入口 chunk 334.52 kB，large chunk warning 未回归。

### P1: 手动切阶段触发 abort 后半成品被保存为正常历史版本

**现象**: 流式生成已经写入当前阶段 artifact 后，如果用户手动切换阶段，`setStageIndex()` 会让旧请求 abort。旧流随后抛出 `Aborted by user` 时，`handleSend()` 的 catch 分支会因为本轮 stage 已不再 active 而提前 return，导致 `wasRunAborted` 没有置为 `true`；`finally` 仍会把本轮半成品写入 `artifactHistory`，作为正常版本保存。

**影响**: 用户手动离开阶段本应中止旧请求，但右侧历史版本可能残留一份被中止的半成品文档。后续回看或导出版本时，半成品会被误认为一次完整生成结果。

**修复记录**:

- 2026-06-18: `handleSend()` 在 abort/error catch 分支中先根据错误类型设置 `wasRunAborted` 或 `didRunFail`，再判断本轮是否仍 active；inactive 的旧流仍不写回聊天区或截断 UI，但 `finally` 能正确跳过正常 artifact history 保存。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts -t "should not save an aborted partial artifact"`，修复前失败输出显示 `artifactHistory` 被写入 `# 需求分析文档\n半成品`。
- 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts -t "should not save an aborted partial artifact"`，1 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts -t "manually switching stages|partially updated artifact|stream errors after an artifact update|save artifact history for the run artifact"`，6 passed。

### P1: 清空历史后旧 artifact 版本写回空版本历史

**现象**: 旧请求已经写入过 artifact 后，如果用户在流结束前清空历史，聊天区和右侧产物会被重置，但 `handleSend()` 的 `finally` 仍会因为 `didUpdateArtifact=true` 把旧 artifact 保存到新的 `artifactHistory`。

**影响**: 用户清空历史后，版本历史仍残留旧请求产物；后续查看版本或导出时会看到已经清空过的旧内容，削弱清空操作的可信度。

**修复记录**:

- 2026-06-17: 将请求有效性判断拆分为严格的 `isRunStillActive()` 和用于版本历史的 `isRunHistoryStillActive()`；chunk/catch 仍要求 workflow/stage 均匹配，版本历史允许同 workflow 内手动切阶段后保存本轮 artifact，但在本轮 user message 已被清空或 workflow 已切换时不再写入旧版本。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts -t "should not save a stale artifact version after clearing history before stream ends"`，修复前失败输出显示 `artifactHistory` 被写入 `# 需求分析文档\n清空前旧产物`。
- 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts -t "should not save a stale artifact version after clearing history before stream ends"`，1 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts -t "should (save artifact history for the run artifact when manually switching stages before stream ends|not save a stale artifact version after clearing history before stream ends)"`，2 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts`，23 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/__tests__/p0-fixes.test.ts src/__tests__/store.test.ts src/core/__tests__/agentCore.test.ts src/services/__tests__/chatService.test.ts src/components/__tests__/ChatPane.test.tsx src/components/__tests__/WorkflowDropdown.test.tsx src/pages/__tests__/Workspace.test.tsx`，7 files / 76 tests passed。
- 验证: `cd tools/new-agents/frontend && npm test`，25 files / 212 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；主入口 chunk 334.52 kB，large chunk warning 未回归。

### P1: 清空历史后阶段确认内部续写 artifact 写回空版本历史

**现象**: 阶段确认内部续写使用 `appendUserMessage:false`，不会追加内部 user 消息。旧请求普通路径依赖 user message id 判断当前运行是否仍属于现有会话，但内部续写没有这个历史锚点。如果内部续写已经写入 artifact，随后用户清空历史，旧流即使不再写回聊天区，`finally` 仍可能在正常结束时把旧 artifact 写入新的空 `artifactHistory`。

**影响**: 用户清空历史后仍可能在版本历史中看到上一轮阶段确认续写产生的旧策略/后续阶段产物；这和普通用户请求的清空语义不一致，也会污染后续版本回看。

**修复记录**:

- 2026-06-18: `handleSend()` 为每轮生成记录首个 assistant message id；普通用户请求继续使用 user message id 作为 history guard，`appendUserMessage:false` 的内部续写则使用 assistant message id 作为 history guard。清空历史后该锚点消失，旧内部续写不会再保存 artifact history。
- 2026-06-18: 在消费每个 stream chunk 前增加本轮 `AbortSignal` 检查；如果清空历史等外部 reset 已经 abort 旧内部续写，即使用户随后又切回相同阶段，旧流首包也不会重新写回聊天区、artifact 或版本历史。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts -t "stale internal continuation artifact"`，修复前失败输出显示 `artifactHistory` 被写入 `# 测试策略蓝图\n内部续写半成品`。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts -t "ignore an internal continuation chunk"`，修复前失败输出显示清空历史并切回同阶段后，旧内部续写重新写入 assistant 消息。
- 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts -t "ignore an internal continuation chunk|stale internal continuation artifact|should not save an aborted partial artifact"`，3 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts -t "save artifact history for the run artifact|not save a stale artifact version after clearing history|manually switching stages|partially updated artifact|stream errors after an artifact update"`，7 passed。

### P1: 同一渲染周期重复发送会启动并发 Agent 请求

**现象**: `handleSend()` 入口只检查 hook 闭包里的 `isGenerating`。用户双击发送按钮或同一渲染周期内连续触发发送时，第一次调用虽然已经同步把 store 的 `isGenerating` 设为 `true`，第二次调用仍可能读取旧闭包值 `false`，从而再次追加 user message 并启动第二条 Agent Runtime 请求。

**影响**: 同一用户输入可能触发重复模型调用、重复聊天消息和并发 artifact 写入；后返回的请求还可能覆盖先返回请求的产物，造成工作区状态不可预测。

**修复记录**:

- 2026-06-17: `handleSend()` 入口改为读取 `useStore.getState().isGenerating` 作为实时生成状态保护，避免同一渲染周期内第二次调用绕过旧闭包值。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts -t "should ignore duplicate sends triggered before the hook rerenders"`，修复前失败输出显示 `generateResponseStream` 被调用 2 次。
- 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts -t "should ignore duplicate sends triggered before the hook rerenders"`，1 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts`，24 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/__tests__/p0-fixes.test.ts src/__tests__/store.test.ts src/core/__tests__/agentCore.test.ts src/services/__tests__/chatService.test.ts src/components/__tests__/ChatPane.test.tsx src/components/__tests__/WorkflowDropdown.test.tsx src/pages/__tests__/Workspace.test.tsx`，7 files / 77 tests passed。
- 验证: `cd tools/new-agents/frontend && npm test`，25 files / 213 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；主入口 chunk 334.52 kB，large chunk warning 未回归。

### P1: 生成中旧重试 handler 仍可回滚聊天历史

**现象**: `handleRetry()` 入口依赖 hook 闭包里的 `isGenerating` 和 `chatHistory.length`。如果 UI 已经触发新的生成并把 store 中的 `isGenerating` 设为 `true`，但旧 render 的 retry handler 仍被调用，它会读取旧闭包值继续执行重试，回滚当前聊天历史并恢复旧输入。

**影响**: 生成中状态本应禁止重试，但 stale handler 仍可能撤销对话，破坏正在进行的 Agent Runtime 请求上下文；旧流后续返回时还会进入 stale/abort 分支，造成用户看到的聊天历史与真实请求状态不一致。

**修复记录**:

- 2026-06-18: `handleRetry()` 入口改为读取 `useStore.getState()` 的实时 `isGenerating` 和实时 `chatHistory.length`，与 `handleSend()` 的实时生成状态保护保持一致。
- 2026-06-18: `chatService.test.ts` 增加回归测试，模拟旧 render 的 retry handler 在 store 已经进入生成中后被调用，要求不回滚历史、不恢复输入。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts -t "should ignore retry when generation starts before the hook rerenders"`，修复前失败输出显示 `chatHistory` 被回滚为空数组。
- 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts -t "should ignore retry when generation starts before the hook rerenders"`，1 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts`，31 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts src/components/__tests__/ChatPane.test.tsx src/__tests__/p0-fixes.test.ts src/__tests__/store.test.ts src/core/__tests__/agentCore.test.ts`，5 files / 75 tests passed。
- 验证: `cd tools/new-agents/frontend && npm test`，25 files / 223 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；主入口 chunk 334.58 kB，large chunk warning 未回归。

### P1: 生成中旧阶段确认 handler 仍可推进阶段

**现象**: `handleConfirmStageTransition()` 虽然会从 store 读取实时 `pendingStageTransition`，但生成中保护仍依赖 hook 闭包里的 `isGenerating`。如果 UI 已进入新的生成中状态，而旧 render 的阶段确认 handler 在 rerender 前被调用，它会继续确认 pending transition。

**影响**: 阶段会被推进到目标阶段，`pendingStageTransition` 被清除；随后内部 `handleSend()` 又会因为实时 `isGenerating=true` 被拦截，导致工作流状态已经进入下一阶段，但下一阶段续写没有发生，形成“阶段已切、内容未续”的错位。

**修复记录**:

- 2026-06-18: `handleConfirmStageTransition()` 改为使用同一次 `useStore.getState()` 中的实时 `state.isGenerating` 做入口保护，并移除对闭包 `isGenerating` 的依赖。
- 2026-06-18: `chatService.test.ts` 增加回归测试，模拟旧 render 的阶段确认 handler 在 store 已经进入生成中后被调用，要求不推进阶段、不清除 pending transition、不触发内部续写。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts -t "should not confirm a stage transition when generation starts before the hook rerenders"`，修复前失败输出显示 `stageIndex` 从 `0` 变为 `1`。
- 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts -t "should not confirm a stage transition when generation starts before the hook rerenders"`，1 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts`，32 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts src/components/__tests__/ChatPane.test.tsx src/__tests__/p0-fixes.test.ts src/__tests__/store.test.ts src/core/__tests__/agentCore.test.ts`，5 files / 76 tests passed。
- 验证: `cd tools/new-agents/frontend && npm test`，25 files / 224 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；主入口 chunk 334.58 kB，large chunk warning 未回归。

### P1: 新会话清空后生成状态残留并阻塞后续请求

**现象**: 用户在 Agent Runtime 请求仍挂起时点击“新会话/清空历史”，`clearHistory()` 会重置聊天、产物和阶段，但不会重置 `isGenerating`。工作区看起来已经清空，发送入口却仍处于生成中，无法立即开始新请求。若强行恢复可发送，旧请求还可能通过共享 `abortControllerRef.current` 和 `finally` 干扰后续新请求。

**影响**: 新会话操作不能让工作区立即恢复可用；用户可能需要等待旧模型请求结束。旧请求结束时还可能中止新请求或把新请求的生成状态提前置为 false。

**修复记录**:

- 2026-06-17: `clearHistory()` 同步重置 `isGenerating: false`，让新会话立即恢复可发送。
- 2026-06-17: `handleSend()` 为每轮请求捕获独立 `runAbortController`；旧请求 stale 时只 abort 自己，`finally` 也只在当前 ref 仍指向本轮 controller 时清理 controller 和 `isGenerating`，避免旧请求干扰新请求。
- 2026-06-17: `chatService` 的消息和版本 ID 改为单调唯一 ID，避免同一毫秒内清空后新请求的 user message 与旧请求 user message ID 碰撞，导致旧请求误判仍有效。
- 2026-06-17: `handleStop()` 不再提前清空 controller ref，停止后的 `isGenerating=false` 仍由本轮请求 `finally` 负责落盘。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts -t "should allow a new request after clearing history while the previous stream is still pending"`，修复前失败输出显示清空后 `isGenerating` 仍为 `true`。
- 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts -t "should allow a new request after clearing history while the previous stream is still pending"`，1 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/__tests__/store.test.ts src/services/__tests__/chatService.test.ts`，2 files / 30 tests passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/__tests__/p0-fixes.test.ts src/__tests__/store.test.ts src/core/__tests__/agentCore.test.ts src/services/__tests__/chatService.test.ts src/components/__tests__/ChatPane.test.tsx src/components/__tests__/WorkflowDropdown.test.tsx src/pages/__tests__/Workspace.test.tsx`，7 files / 78 tests passed。
- 验证: `cd tools/new-agents/frontend && npm test`，25 files / 214 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；主入口 chunk 334.53 kB，large chunk warning 未回归。

### P1: 生成中切换工作流后生成状态残留并阻塞新工作流

**现象**: 用户在旧工作流 Agent Runtime 请求仍挂起时切换到另一个 workflow，`setWorkflow()` 会重置聊天、阶段和 artifact，但不会重置 `isGenerating`。新工作流界面已经显示出来，但发送入口仍处于生成中，直到旧请求返回才恢复。

**影响**: 工作流切换不能立即让新工作流可用；用户可能被旧工作流请求阻塞。旧请求如果随后返回，也需要继续依赖 stale 保护防止污染新工作流。

**修复记录**:

- 2026-06-18: `setWorkflow()` 同步重置 `isGenerating: false`，与 `clearHistory()` 的新会话语义保持一致。
- 2026-06-18: `store.test.ts` 增加切换工作流会清除生成状态的断言。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts -t "should allow a new request after switching workflows while the previous stream is still pending"`，修复前失败输出显示切换到 `REQ_REVIEW` 后 `isGenerating` 仍为 `true`。
- 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts -t "should allow a new request after switching workflows while the previous stream is still pending"`，1 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/__tests__/store.test.ts src/services/__tests__/chatService.test.ts`，2 files / 31 tests passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/__tests__/p0-fixes.test.ts src/__tests__/store.test.ts src/core/__tests__/agentCore.test.ts src/services/__tests__/chatService.test.ts src/components/__tests__/ChatPane.test.tsx src/components/__tests__/WorkflowDropdown.test.tsx src/pages/__tests__/Workspace.test.tsx`，7 files / 79 tests passed。
- 验证: `cd tools/new-agents/frontend && npm test`，25 files / 215 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；主入口 chunk 334.55 kB，large chunk warning 未回归。

### P1: 生成中手动切换阶段后生成状态残留并阻塞新阶段

**现象**: 用户在某阶段 Agent Runtime 请求仍挂起时手动切到另一个阶段，`setStageIndex()` 会切换右侧 artifact、清除截断标记和 pending transition，但不会重置 `isGenerating`。目标阶段界面已经显示出来，发送入口仍处于生成中，直到旧阶段请求返回才恢复。

**影响**: 用户无法在目标阶段立即继续生成；旧阶段请求会阻塞新阶段工作流操作。旧阶段请求返回时还需要继续依赖 stale 保护防止污染目标阶段。

**修复记录**:

- 2026-06-18: `setStageIndex()` 同步重置 `isGenerating: false`，与 `clearHistory()` 和 `setWorkflow()` 的重置语义保持一致。
- 2026-06-18: `store.test.ts` 增加手动切换阶段会清除生成状态的断言。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts -t "should allow a new request after manually switching stages while the previous stream is still pending"`，修复前失败输出显示切到阶段 1 后 `isGenerating` 仍为 `true`。
- 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts -t "should allow a new request after manually switching stages while the previous stream is still pending"`，1 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/__tests__/store.test.ts src/services/__tests__/chatService.test.ts`，2 files / 32 tests passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/__tests__/p0-fixes.test.ts src/__tests__/store.test.ts src/core/__tests__/agentCore.test.ts src/services/__tests__/chatService.test.ts src/components/__tests__/ChatPane.test.tsx src/components/__tests__/WorkflowDropdown.test.tsx src/pages/__tests__/Workspace.test.tsx`，7 files / 80 tests passed。
- 验证: `cd tools/new-agents/frontend && npm test`，25 files / 216 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；主入口 chunk 334.56 kB，large chunk warning 未回归。

### P1: 阶段确认进入下一阶段后截断警告状态残留

**现象**: Agent Runtime 标记当前阶段 artifact 被截断后，用户通过阶段确认卡片进入下一阶段，`confirmStageTransition()` 会更新 `stageIndex`、保存当前阶段 artifact 并加载目标阶段 artifact，但不会重置 `artifactTruncated`。目标阶段的空产物或已有产物会继续显示上一阶段的截断警告。

**影响**: 阶段确认后的新阶段会出现错误的产物完整性提示，用户可能误以为目标阶段产出已经被截断；该状态也和手动切换阶段、切换工作流、清空历史的重置语义不一致。

**修复记录**:

- 2026-06-18: `planStageTransitionConfirmation()` 在有效确认进入目标阶段时返回 `artifactTruncated: false`，让 `confirmStageTransition()` 的状态 patch 同步清理旧阶段截断标记。
- 2026-06-18: `store.test.ts` 增加确认阶段流转会清除截断状态的断言，`agentCore.test.ts` 同步 plan 层返回契约。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/__tests__/store.test.ts -t "should clear artifact truncation state when confirming a stage transition"`，修复前失败输出显示 `artifactTruncated` 仍为 `true`。
- 验证: `cd tools/new-agents/frontend && npm test -- src/__tests__/store.test.ts -t "should clear artifact truncation state when confirming a stage transition"`，1 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/__tests__/store.test.ts src/core/__tests__/agentCore.test.ts src/services/__tests__/chatService.test.ts`，3 files / 48 tests passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/__tests__/p0-fixes.test.ts src/__tests__/store.test.ts src/core/__tests__/agentCore.test.ts src/services/__tests__/chatService.test.ts src/components/__tests__/ChatPane.test.tsx src/components/__tests__/WorkflowDropdown.test.tsx src/pages/__tests__/Workspace.test.tsx`，7 files / 81 tests passed。
- 验证: `cd tools/new-agents/frontend && npm test`，25 files / 217 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；主入口 chunk 334.58 kB，large chunk warning 未回归。

### P1: 结构化 Agent Runtime 截断 warning 未驱动前端截断提示

**现象**: 前端 `chatService` 和 Artifact 面板已有 `artifactTruncated` 状态与截断警告 UI，但主链路的 typed Agent Runtime adapter 只消费 `chat`、`artifact_update` 和 `stage_action`，没有把后端 `warnings` 中的截断语义映射到 stream chunk 的 `artifactTruncated`。因此结构化运行时即使返回 `warnings: ["artifact_truncated"]`，右侧产出物面板也不会显示截断警告。

**影响**: 截断状态清理逻辑已经覆盖切换工作流、切换阶段、确认阶段和重试，但真实 typed runtime 主链路缺少设置入口，用户无法从 UI 得知本轮产出物可能不完整。

**修复记录**:

- 2026-06-18: `core/llm.ts` 新增 `hasArtifactTruncationWarning(...)`，将 `warnings` 中的 `artifact_truncated`、`truncated`、`截断`、`不完整` 映射为合成 stream chunk 的 `artifactTruncated: true`；未命中时不输出该可选字段，保持原有 chunk 形状。
- 2026-06-18: `llm.test.ts` 增加 typed Agent Runtime warning 映射回归测试，覆盖 `warnings: ["artifact_truncated"]` 会在前端 stream chunk 上产生 `artifactTruncated: true`。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts -t "warnings 包含 artifact_truncated"`，修复前失败输出显示实际 chunk 缺少 `artifactTruncated: true`。
- 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts -t "warnings 包含 artifact_truncated"`，1 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts`，39 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts src/services/__tests__/chatService.test.ts src/components/__tests__/ArtifactPane.test.tsx src/__tests__/p0-fixes.test.ts src/__tests__/store.test.ts src/core/__tests__/agentCore.test.ts`，6 files / 106 tests passed。
- 验证: `cd tools/new-agents/frontend && npm test`，25 files / 220 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；主入口 chunk 334.58 kB，large chunk warning 未回归。

### P1: 截断 warning 与 artifact 更新同 chunk 时会被清除

**现象**: typed Agent Runtime adapter 已能把 `warnings: ["artifact_truncated"]` 映射成 stream chunk 的 `artifactTruncated: true`。但 `chatService` 处理同一个 chunk 时，会先根据 `decision.artifactTruncated` 设置 `artifactTruncated: true`，随后只要存在 `decision.artifactUpdate` 就无条件 `setArtifactTruncated(false)`。因此“带截断 warning 的 artifact 更新”最终仍不会在右侧产物面板显示截断警告。

**影响**: 主链路已经收到后端不完整产物信号，artifact 内容也会写入右侧面板，但 UI 最终状态会误报为完整产物，用户无法获知需要检查文档完整性。

**修复记录**:

- 2026-06-18: `chatService` 的 artifact 更新分支改为仅在当前决策没有截断 warning 时清理旧 `artifactTruncated`；如果本轮 artifact 更新本身被标记为截断，则保留 `artifactTruncated: true`。
- 2026-06-18: `chatService.test.ts` 增加 hook 回归测试，覆盖同一个 stream chunk 同时包含 `hasArtifactUpdate: true` 和 `artifactTruncated: true` 时，最终 store 仍保留截断警告状态。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts -t "should keep truncation warning when an artifact update is marked truncated"`，修复前失败输出显示 `artifactContent` 已更新但 `artifactTruncated` 为 `false`。
- 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts -t "should keep truncation warning when an artifact update is marked truncated"`，1 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts`，30 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts src/services/__tests__/chatService.test.ts src/components/__tests__/ArtifactPane.test.tsx src/__tests__/p0-fixes.test.ts src/__tests__/store.test.ts src/core/__tests__/agentCore.test.ts`，6 files / 107 tests passed。
- 验证: `cd tools/new-agents/frontend && npm test`，25 files / 221 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；主入口 chunk 334.58 kB，large chunk warning 未回归。

### P1: 结构化 Agent Runtime warnings 字段缺少运行时协议校验

**现象**: 前端 `parseAgentRuntimeEvent()` 会校验 `chat`、`artifact_update` 和 `stage_action`，但没有校验 `warnings` 是否为字符串数组。畸形 SSE 事件例如 `warnings: "artifact_truncated"` 会通过协议解析，随后在 `hasArtifactTruncationWarning()` 中调用 `.some(...)` 才抛出 `warnings.some is not a function`。

**影响**: 后端或中间层返回畸形 `warnings` 时，用户侧看到的是实现细节型运行时错误，而不是统一的“结构化智能体 SSE 事件格式错误”。这会削弱 typed runtime 协议边界，也让后续错误定位偏离真正的契约问题。

**修复记录**:

- 2026-06-18: `parseAgentRuntimeEvent()` 增加 `warnings` 运行时校验；允许省略或字符串数组，拒绝非数组和数组内非字符串元素，并统一抛出 `结构化智能体 SSE 事件格式错误`。
- 2026-06-18: `llm.test.ts` 增加 malformed warnings 回归测试，覆盖 `warnings` 为字符串时必须在 SSE 解析阶段失败。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts -t "warnings 不是字符串数组"`，修复前失败输出为 `warnings.some is not a function`，不是期望的协议错误。
- 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts -t "warnings 不是字符串数组"`，1 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts`，40 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts src/services/__tests__/chatService.test.ts src/components/__tests__/ArtifactPane.test.tsx src/__tests__/p0-fixes.test.ts src/__tests__/store.test.ts src/core/__tests__/agentCore.test.ts`，6 files / 108 tests passed。
- 验证: `cd tools/new-agents/frontend && npm test`，25 files / 222 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；主入口 chunk 334.58 kB，large chunk warning 未回归。

### P1: 重试后旧阶段确认和截断警告状态残留

**现象**: 用户点击最后一条 assistant 消息的“重试”后，`handleRetry()` 会回滚到最后一条 user 消息之前，并把用户输入和附件恢复到输入区。但如果被重试的 assistant 结果曾触发 `pendingStageTransition` 或 `artifactTruncated`，这两个派生状态不会被清理，聊天区仍可能显示旧的“确认进入下一阶段”卡片，右侧产物面板也可能继续显示旧截断警告。

**影响**: 重试语义变成“撤销回复但保留回复产生的工作流状态”，会误导用户继续确认一个已被撤销的阶段流转，或误判重试前的截断警告仍适用于当前待重试输入。

**修复记录**:

- 2026-06-18: `handleRetry()` 在成功计算 retry plan 并回滚消息后，同步调用 `clearPendingStageTransition()` 和 `setArtifactTruncated(false)`，只清理被重试 assistant 结果产生的派生 UI 状态，不改变输入/附件恢复逻辑。
- 2026-06-18: `chatService.test.ts` 增加两个 hook 回归测试，分别覆盖重试清理阶段确认状态和重试清理截断警告状态。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts -t "should clear (pending stage transition|artifact truncation warning) when retrying"`，修复前两个用例失败，分别显示 `pendingStageTransition` 仍为 `{ fromStageIndex: 0, toStageIndex: 1 }`、`artifactTruncated` 仍为 `true`。
- 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts -t "should clear (pending stage transition|artifact truncation warning) when retrying"`，2 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts`，29 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/__tests__/p0-fixes.test.ts src/__tests__/store.test.ts src/core/__tests__/agentCore.test.ts src/services/__tests__/chatService.test.ts src/components/__tests__/ChatPane.test.tsx src/components/__tests__/WorkflowDropdown.test.tsx src/pages/__tests__/Workspace.test.tsx`，7 files / 83 tests passed。
- 验证: `cd tools/new-agents/frontend && npm test`，25 files / 219 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；主入口 chunk 334.58 kB，large chunk warning 未回归。

### P1: 重试后旧产物状态残留在工作区

**现象**: 用户点击最后一条 assistant 消息的“重试”后，`handleRetry()` 会删除被重试的聊天消息并恢复输入，但不会回滚该 assistant 回复写入的 `artifactContent`、`stageArtifacts` 和 `artifactHistory`。聊天区看起来已经撤销旧回复，右侧产物仍保留旧回复生成的内容。

**影响**: 下一轮重试请求会在已删除回答产生的右侧产物上下文中继续执行，形成“聊天已撤销、产物未撤销”的脏状态链；用户也会误以为旧产物仍是当前有效结果。

**修复记录**:

- 2026-06-18: `useChatService()` 在每轮生成的首个 assistant 消息创建时记录发送前的产物快照；`handleRetry()` 删除该轮消息时，如果被删除消息有关联快照，会同步恢复 `artifactContent`、`stageArtifacts` 和 `artifactHistory`。快照保存在 hook 内存 ref 中，不写入持久化聊天历史，避免扩大 localStorage 体积。
- 测试: 已更新 `chatService` hook 测试，覆盖一次生成写入 `# Bad artifact` 并保存 artifact version 后，点击 retry 会清空该轮聊天、恢复发送前产物、恢复当前阶段 artifact，并移除该轮 artifact history。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts -t "roll back artifact state"`，修复前失败输出显示 retry 后 `artifactContent` 仍为 `# Bad artifact`。
- 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts -t "roll back artifact state"`，1 passed / 36 skipped。
- 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts`，37 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts src/components/__tests__/ChatPane.test.tsx src/__tests__/store.test.ts src/core/__tests__/agentCore.test.ts src/__tests__/p0-fixes.test.ts src/core/__tests__/llm.test.ts`，6 files / 135 tests passed。
- 验证: `cd tools/new-agents/frontend && npm test`，25 files / 245 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；主入口 chunk 336.11 kB，large chunk warning 未回归。
- 2026-06-18: 修复页面刷新或 hook 重新挂载后的重试回滚缺口；当内存快照不存在、但当前 artifact 与最新持久化 artifact version 一致时，`handleRetry()` 会从 `artifactHistory` 回退到上一版，并同步当前阶段 `stageArtifacts`。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts -t "roll back persisted artifact state"`，修复前失败输出显示 retry 后 `artifactContent` 仍为 `# Bad artifact`。
- 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts -t "roll back persisted artifact state"`，1 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts`，39 passed。
- 2026-06-18: 补强持久化回滚的阶段边界。当 hook 重新挂载后只能从全局 `artifactHistory` 回滚时，如果上一版内容已属于其他阶段，则不再把它写入当前阶段；当前阶段改为恢复到该阶段模板，并移除本轮坏版本历史。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts -t "should not roll back the current stage"`，修复前失败输出显示 `STRATEGY` 当前产物被回滚成 `# 需求分析文档\n需求澄清最终版`。
- 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts -t "should not roll back the current stage"`，1 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts -t "roll back"`，3 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts`，41 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts src/components/__tests__/ChatPane.test.tsx src/__tests__/store.test.ts src/core/__tests__/agentCore.test.ts src/core/__tests__/llm.test.ts`，5 files / 132 tests passed。
- 验证: `cd tools/new-agents/frontend && npm test`，26 files / 262 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；主入口 chunk 336.20 kB，large chunk warning 未回归。
- 验证: `git diff --check`，通过。
- 2026-06-18: 继续补强刷新后重试的首个产物回滚。如果重挂载后 `artifactHistory` 只有当前坏版本，没有上一版可回退，`handleRetry()` 现在会移除该版本并把当前阶段恢复到基线内容：首阶段恢复工作流欢迎文案，后续阶段恢复阶段模板，避免“聊天已撤销但右侧首个坏产物仍残留”。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts -t "first persisted artifact"`，修复前失败输出显示 `artifactContent` 仍为 `# Bad first artifact`。
- 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts -t "first persisted artifact"`，1 passed。
- 2026-06-18: 代码审查后将持久化回滚的阶段归属判断从内容相等启发式改为 `ArtifactVersion.stageId`。最新版本必须属于当前阶段才参与本次回滚；上一版只有在 `stageId` 仍等于当前阶段时才回滚到上一版，否则恢复当前阶段基线，避免把其他阶段历史版本写回当前阶段。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts -t "artifact version stage ids"`，修复前失败输出显示 `STRATEGY` 被回滚成 `# 需求分析文档\n旧澄清历史版本`。
- 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts -t "first persisted artifact|artifact version stage ids"`，2 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts -t "roll back"`，5 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/services/__tests__/chatService.test.ts`，50 passed。
- 验证: `cd tools/new-agents/frontend && npm test`，26 files / 291 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；主入口 chunk 336.99 kB，Mermaid runtime 498.23 kB lazy chunk。
- 验证: `git diff --check -- AGENTS.md docs/strategy/goal-mode-playbook.md docs/plans/tech-debt.md tools/new-agents/frontend/src/services/chatService.ts tools/new-agents/frontend/src/services/__tests__/chatService.test.ts`，通过。
- 2026-06-18: 收尾修复 `artifactTruncated` 刷新后丢失的问题。store 持久化白名单加入 `artifactTruncated`，hydrate 时仅在存在有效当前 artifact 内容且 persisted 标记为 `true` 时恢复截断状态，避免刷新后把不完整产物展示成正常产物。
- RED 验证: `cd tools/new-agents/frontend && npm test -- --run src/__tests__/store.test.ts -t "should persist and restore artifact truncation state"`，修复前失败，`artifactTruncated` 从 persisted `true` 恢复为 `false`。
- 验证: `cd tools/new-agents/frontend && npm test -- --run src/__tests__/store.test.ts -t "should persist and restore artifact truncation state"`，1 passed。
- 只读 explorer 后续候选记录: “中途错误/停止与 quota 反馈会污染下一轮 prompt” 已在上方“错误和停止控制反馈会污染下一轮 Runtime Prompt”补强修复；“artifact 截断警告刷新后丢失”已在本节收尾修复。

### P1: 阶段导航 action 越界会让工作区崩溃

**现象**: `store.ts` 的 `setStageIndex(index)` 和旧兼容 action `transitionToNextStage(...)` 直接读取 `WORKFLOWS[state.workflow].stages[index].id`。当调用方传入越界阶段索引，或当前已经处于最终阶段仍调用“进入下一阶段”时，store 会抛出 `Cannot read properties of undefined (reading 'id')`。

**影响**: 当前顶部阶段条只会传入合法 index，但 URL 同步、旧事件处理器、测试工具或未来入口如果带入无效阶段，会直接打崩工作区状态层。该问题和持久化恢复防御不一致：恢复路径已经会 clamp 阶段索引，运行期 action 仍信任调用方。

**修复记录**:

- 2026-06-18: `setStageIndex()` 在保存当前阶段和读取目标阶段前校验当前/目标 stage 存在；非法 index 直接 no-op，不改变 `stageIndex`、`artifactContent` 或 `stageArtifacts`。
- 2026-06-18: `transitionToNextStage(...)` 在目标下一阶段不存在时 no-op，避免最终阶段继续推进时崩溃。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/__tests__/store.test.ts`，修复前新增两个用例失败，均抛 `Cannot read properties of undefined (reading 'id')`。
- 验证: `cd tools/new-agents/frontend && npm test -- src/__tests__/store.test.ts`，12 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/__tests__/store.test.ts src/core/__tests__/agentCore.test.ts src/services/__tests__/chatService.test.ts src/__tests__/p0-fixes.test.ts`，4 files / 80 tests passed。
- 验证: `cd tools/new-agents/frontend && npm test`，26 files / 254 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；主入口 chunk 336.20 kB，large chunk warning 未回归。
- 验证: `git diff --check`，通过。

### P1: 运行期 stage artifact 更新可写入非当前工作流阶段

**现象**: `store.ts` 的 `setStageArtifact(stageId, content)` 直接把任意 `stageId` 写入 `stageArtifacts`。持久化恢复路径已经会按当前 workflow 清洗 stage id，但运行期 action 没有同样的边界保护，调用方传入 `REPORT` 或未知阶段时，会污染当前 `TEST_DESIGN` 工作区的 `stageArtifacts`。

**影响**: 脏阶段产物可能被后续 prompt 构造、版本回滚或 UI 切换路径读取，造成跨工作流上下文污染。即使当前主链路通常由 `reduceAgentStreamChunk()` 传入当前阶段 id，状态层 action 仍应与 hydrate 清洗策略保持一致。

**修复记录**:

- 2026-06-18: `setStageArtifact()` 增加当前 workflow stage id 白名单；非当前 workflow 阶段或未知阶段直接 no-op，不改变 `stageArtifacts`。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/__tests__/store.test.ts -t "should ignore stage artifact updates"`，修复前失败输出显示 `stageArtifacts.REPORT` 被写入 `# Cross-workflow artifact`。
- 验证: `cd tools/new-agents/frontend && npm test -- src/__tests__/store.test.ts -t "should ignore stage artifact updates"`，1 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/__tests__/store.test.ts`，13 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/__tests__/store.test.ts src/services/__tests__/chatService.test.ts src/core/__tests__/agentCore.test.ts`，3 files / 70 tests passed。
- 验证: `cd tools/new-agents/frontend && npm test`，26 files / 263 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；主入口 chunk 336.26 kB，large chunk warning 未回归。
- 验证: `git diff --check`，通过。
- 2026-06-18: 同步收紧旧兼容 action `transitionToNextStage(initialStageId, initialArtifact)`；来源阶段必须等于当前 workflow 当前阶段 id，否则 no-op，避免 stale handler 或跨工作流调用推进阶段并写入错误来源产物。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/__tests__/store.test.ts -t "source stage outside"`，修复前失败输出显示传入 `REPORT` 后 `stageIndex` 从 0 变成 1。
- 验证: `cd tools/new-agents/frontend && npm test -- src/__tests__/store.test.ts -t "source stage outside"`，1 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/__tests__/store.test.ts`，14 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/__tests__/store.test.ts src/core/__tests__/agentCore.test.ts src/services/__tests__/chatService.test.ts src/__tests__/p0-fixes.test.ts`，4 files / 84 tests passed。
- 验证: `cd tools/new-agents/frontend && npm test`，26 files / 264 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；主入口 chunk 336.32 kB，large chunk warning 未回归。
- 验证: `git diff --check`，通过。

### P1: 历史版本只读预览仍暴露 Mermaid 修复动作

**现象**: `ArtifactPane` 历史版本弹窗标注“版本预览（只读）”，但历史预览复用了当前产出物的 `markdownComponents`。该 renderer 固定传入 `onMermaidRetry`，所以历史版本中的 Mermaid 图表也会显示“重新生成图表”这类修复动作。

**影响**: 只读历史版本仍可能触发修复请求，并且修复逻辑会基于当前 `artifactContent` 替换 Mermaid block，而不是历史版本内容；用户可能以为正在修复历史版本，实际修改当前工作区产物。

**修复记录**:

- 2026-06-18: `ArtifactPane` 将 Markdown components 构造拆为可编辑和只读两套。当前产物预览继续传入 `handleMermaidRetry`；历史版本只读预览不传 `onMermaidRetry`。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/components/__tests__/ArtifactPane.test.tsx`，修复前新增用例失败，历史只读预览中仍出现 `重新生成图表` 按钮。
- 验证: `cd tools/new-agents/frontend && npm test -- src/components/__tests__/ArtifactPane.test.tsx`，5 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/components/__tests__/ArtifactPane.test.tsx src/components/__tests__/markdownCodeRenderer.test.tsx src/components/__tests__/Mermaid.test.tsx src/core/__tests__/markdownUtils.test.ts`，4 files / 21 tests passed。
- 验证: `cd tools/new-agents/frontend && npm test`，26 files / 257 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；主入口 chunk 336.20 kB，large chunk warning 未回归。
- 验证: `git diff --check`，通过。

### P1: Mermaid 手动重新生成失败后卡在 loading

**现象**: `Mermaid` 组件在错误降级 UI 中点击“重新生成图表”后，会先把 `renderState` 设置为 `loading`。如果父级 `onRetry(...)` Promise reject，例如修复端点不可用、动态 import 失败或替换逻辑异常，`handleManualRetry()` 会提前中断，组件不会恢复到错误降级 UI。

**影响**: 用户会一直看到“正在绘制流程图...”，无法继续点击重新生成或打开 Live Editor，也看不到修复失败原因。

**修复记录**:

- 2026-06-18: `handleManualRetry()` 捕获 `onRetry(...)` reject，写回失败 message 并恢复 `error` 状态；`onRetry` 返回 `false` 和返回 `true` 但父组件未替换内容的既有回落语义保持不变。
- 测试: 已更新 `Mermaid.test.tsx`，覆盖手动重新生成 reject 后不再停留在 loading，并展示重试失败原因。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/components/__tests__/Mermaid.test.tsx -t "returns to degraded UI"`，修复前失败输出显示页面仍渲染 `正在绘制流程图...`，且 Vitest 捕获未处理的 `repair endpoint unavailable` rejection。
- 验证: `cd tools/new-agents/frontend && npm test -- src/components/__tests__/Mermaid.test.tsx -t "returns to degraded UI"`，1 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/components/__tests__/Mermaid.test.tsx`，7 passed。
- 验证: `cd tools/new-agents/frontend && npm test`，26 files / 265 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；主入口 chunk 336.32 kB，large chunk warning 未回归。

### P1: Mermaid fence 语言识别过宽导致误渲染和误替换

**现象**: `markdownCodeRenderer.tsx` 用 `/language-(\w+)/` 提取代码块语言时，会把 `language-mermaid-js` 截断识别为 `mermaid` 并渲染为 Mermaid 图表；`replaceMermaidBlockAtIndex(...)` 的 `/```mermaid.*?\n/` 也会把 ```mermaid-js 计入可修复的 Mermaid block。

**影响**: 非标准或普通代码块可能被误当作 Mermaid 渲染并暴露“重新生成图表”操作；修复第 N 个 Mermaid 图表时，前面的 `mermaid-js` 代码块会污染 block index，导致替换错误代码块。

**修复记录**:

- 2026-06-18: 代码块语言提取改为读取完整 `language-*` token，`language-mermaid-js` 保持为 `mermaid-js`，不再触发 Mermaid 渲染。
- 2026-06-18: `replaceMermaidBlockAtIndex(...)` 的 fence 正则收紧为只接受开 fence 语言精确为 `mermaid`，后面只能接空白参数或行尾，不再匹配 `mermaid-js`。
- 2026-06-18: Agent Runtime artifact 预校验路径 `extractMermaidBlocks(...)` 同步收紧 fence 正则，只校验语言精确为 `mermaid` 的代码块，`mermaid-js` 普通代码块不再进入 `mermaid.parse(...)`。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/components/__tests__/markdownCodeRenderer.test.tsx src/core/__tests__/markdownUtils.test.ts`，修复前两个新增用例失败：`language-mermaid-js` 被渲染成 Mermaid，且第一个 `mermaid-js` fence 被替换。
- RED 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts -t "不应把 mermaid-js 代码块当作 Mermaid 校验"`，修复前失败，`mermaid-js` 被送入 `mermaid.parse(...)` 并抛出 `Artifact Mermaid parse failed`。
- 验证: `cd tools/new-agents/frontend && npm test -- src/components/__tests__/markdownCodeRenderer.test.tsx src/core/__tests__/markdownUtils.test.ts`，2 files / 10 tests passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts -t "不应把 mermaid-js 代码块当作 Mermaid 校验"`，1 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts -t "typed artifact 包含坏 Mermaid"`，1 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts`，52 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/components/__tests__/markdownCodeRenderer.test.tsx src/core/__tests__/markdownUtils.test.ts src/components/__tests__/ChatPane.test.tsx src/components/__tests__/ArtifactPane.test.tsx src/components/__tests__/Mermaid.test.tsx`，5 files / 31 tests passed。
- 验证: `cd tools/new-agents/frontend && npm test`，26 files / 256 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed；主入口 chunk 336.20 kB，large chunk warning 未回归。
- 验证: `git diff --check`，通过。

### P1: Mermaid 与工作区面板静态导入导致首屏主包过大

**现象**: New Agents 前端构建时 Vite 持续提示 chunk 超过 500 kB。此前主入口 `index-*.js` 约 1,207 kB，首屏会同步加载 Mermaid runtime、ChatPane、ArtifactPane 及其 Markdown 渲染链路。

**影响**: 首屏加载和交互准备时间被非首屏必需模块拖慢；用户只进入工作区页面时，也会提前下载 Mermaid 渲染器和右侧产物面板相关依赖。

**已确认根因**:

- `core/llm.ts` 顶层静态导入 `mermaid`，导致校验工具链进入主入口。
- `components/Mermaid.tsx` 顶层静态导入 `mermaid`，导致 Markdown/Mermaid 渲染 runtime 进入主入口。
- `Workspace.tsx` 顶层静态导入 `ChatPane` 与 `ArtifactPane`，导致聊天面板、产物面板和 Markdown 渲染链路在进入工作区时一次性加载。

**修复记录**:

- 2026-06-17: `core/llm.ts` 改为仅在存在 Mermaid 代码块并需要校验时动态加载 Mermaid runtime。
- 2026-06-17: `components/Mermaid.tsx` 改为动态加载并初始化 Mermaid runtime，保留类型导入，不再把运行时代码静态打进主入口。
- 2026-06-17: `Workspace.tsx` 改为 `React.lazy` 加载 `ChatPane` 和 `ArtifactPane`，工作区主入口先渲染稳定布局，再按需加载重面板。
- 测试: 新增前端 hygiene 测试，禁止 `core/llm.ts`、`Mermaid.tsx` 静态导入 Mermaid runtime，并禁止 `Workspace.tsx` 静态导入重面板组件。
- 验证: `cd tools/new-agents/frontend && npm test -- src/__tests__/testHygiene.test.ts`，7 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/components/__tests__/Mermaid.test.tsx`，6 passed。
- 验证: `cd tools/new-agents/frontend && npm test -- src/pages/__tests__/Workspace.test.tsx`，3 passed。
- 验证: `cd tools/new-agents/frontend && npm test`，25 files / 188 tests passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 验证: `cd tools/new-agents/frontend && npm run build`，Vite build passed，large chunk warning 消失；主入口 chunk 降到 334.41 kB，Mermaid runtime 独立为 498.23 kB lazy chunk。

## New Agents 智能体重构完成记录

### 已完成 P0: 引入 PydanticAI 约束智能体输出结构

**目标**: 解决当前大模型输出不稳定导致前端解析、Artifact 渲染、Mermaid 渲染失败的问题。

重构前 `new-agents` 依赖 `<CHAT>`、`<ARTIFACT>`、`<ACTION>` 文本标签和正则解析 LLM 输出。这个方案适合 Demo，但长期维护风险较高：标签缺失、半截输出、`NO_UPDATE` 混入正文、Markdown/Mermaid 格式错误都会直接影响渲染稳定性；当前主链路已迁移为后端统一智能体运行时和 PydanticAI 结构化输出校验。

重构方向:

- 在 `tools/new-agents/backend` 增加 PydanticAI Agent Runtime 试点。
- 用 Pydantic 模型定义单轮智能体输出契约，例如 `chat`、`artifact_update`、`stage_action`、`warnings`。
- 后端负责把模型输出校验为结构化对象；校验失败时明确返回错误或触发有限重试，不再把不可信文本直接交给前端解析。
- 前端消费 typed SSE event，而不是解析 `<ARTIFACT>` 标签。
- 在结构化输出之后继续执行应用级校验：Markdown 安全处理、Mermaid parse 校验、Artifact 模板章节完整性校验、阶段动作合法性校验。

建议先做最小试点:

- 仅迁移 `TEST_DESIGN` 工作流的 `CLARIFY` 阶段。
- 新增实验端点 `/api/agent/runs/stream`，完成迁移后删除旧 `/api/chat/stream` 对照端点。
- 前端新增 adapter 接入新协议，暂不重写 UI。
- TDD 覆盖模型输出缺字段、非法阶段跳转、坏 Mermaid、空 Artifact、流式中断等失败场景。

完成标准:

- 不再依赖正则从 LLM 自由文本中提取核心协议字段。
- 非法输出不会进入 Artifact 渲染链路。
- `TEST_DESIGN/CLARIFY` 阶段在新协议下可完成对话、Artifact 更新和进入下一阶段确认。

当前进展:

- 2026-06-05 已完成后端最小垂直切片:
  - 新增 `agent_contracts.py`，用 Pydantic 模型约束 `chat`、`artifact_update`、`stage_action`、`warnings`。
  - 新增 `agent_runtime.py`，用 PydanticAI Agent Runtime 输出 `AgentTurnOutput`，并在返回前执行阶段动作合法性校验。
  - 新增实验端点 `/api/agent/runs/stream`，返回 typed SSE event: `agent_turn`；后续迁移完成后已删除 `/api/chat/stream` 对照端点。
  - `tools/new-agents/backend/requirements.txt` 改为 `pydantic-ai-slim[openai]==1.104.0` 与 `openai>=2.29.0,<3`，避免引入全量 provider extras，并匹配本地 Docker 构建使用的 PyPI 镜像可解析版本。
- 2026-06-05 已完成前端 typed SSE adapter 最小切片:
  - `TEST_DESIGN`、`REQ_REVIEW`、`INCIDENT_REVIEW`、`IDEA_BRAINSTORM`、`VALUE_DISCOVERY` 在系统代理模式下改为调用 `/new-agents/api/agent/runs/stream`。
  - 前端将 `agent_turn` typed event 映射为现有 `chatService` 可消费的 `chatResponse`、`newArtifact`、`action`、`hasArtifactUpdate` chunk。
  - 结构化 runtime 请求会把历史对话、附件和当前用户消息合成为 `prompt` 发送，避免迁移后丢失上下文。
  - 用户自配 API Key 前端直连旧路径已删除；主 Agent 调用统一走后端结构化 Agent Runtime。
- 2026-06-05 已完成 `TEST_DESIGN/CLARIFY` Markdown 模板最低结构校验:
  - 后端在 PydanticAI 输出结构化之后继续校验 Artifact 必备标题。
  - 缺少《需求分析文档》顶层标题或 4 个关键二级章节时抛出 `ContractValidationError`，不会进入 SSE 成功事件和前端渲染链路。
- 2026-06-05 已扩展 `TEST_DESIGN` 全阶段 Markdown 模板最低结构校验:
  - `STRATEGY` 阶段校验《测试策略蓝图》的质量目标、风险分析、风险矩阵、风险明细、技术选型、分层策略、测试点拓扑等关键标题。
  - `CASES` 阶段校验《测试用例集》的用例统计、用例清单、测试点覆盖追溯等关键标题。
  - `DELIVERY` 阶段校验《测试设计文档》的文档信息、需求分析、测试策略、测试用例、验收标准等关键标题。
- 2026-06-05 已扩展 `REQ_REVIEW` 全阶段 Markdown 模板最低结构校验:
  - `REVIEW` 阶段校验《需求评审问题清单》的评审概要、问题统计等关键标题。
  - `REPORT` 阶段校验《需求评审报告》的评审结论、判定标准、评审信息、问题统计、待确认问题清单、P0/P1/P2 分组和评审意见签署等关键标题。
- 2026-06-05 已扩展 `INCIDENT_REVIEW` 全阶段 Markdown 模板最低结构校验:
  - `TIMELINE` 阶段校验《故障复盘报告》的事件概要、事件时间线、事实摘要、参与人员、待补充信息等关键标题。
  - `ROOT_CAUSE` 阶段校验根因分析、5-Why 分析链、原因鱼骨图、根因结论等关键标题。
  - `IMPROVEMENT` 阶段校验报告信息、事件还原、根因分析、改进措施、防复发检查清单、经验教训、签署确认等关键标题。
- 2026-06-05 已扩展 `IDEA_BRAINSTORM` 全阶段 Markdown 模板最低结构校验:
  - `DEFINE` 阶段校验问题假设、目标用户画像、问题域全景、问题-用户-场景匹配、约束边界、反向验证等关键标题。
  - `DIVERGE` 阶段校验发散全景图、创意卡片库等关键标题。
  - `CONVERGE` 阶段校验决策矩阵、ICE 评估表、整合演进路径等关键标题。
  - `CONCEPT` 阶段校验定位声明、Lean Canvas、MVP 功能分布、增长漏斗、风险分析、下一步行动等关键标题。
- 2026-06-05 已扩展 `VALUE_DISCOVERY` 全阶段 Markdown 模板最低结构校验:
  - `ELEVATOR` 阶段校验价值定位分析、电梯演讲、用户概览、价值主张、商业可行性等关键标题。
  - `PERSONA` 阶段校验主要用户画像、基础特征、行为特征、需求动机、核心痛点、用户优先级排序等关键标题。
  - `JOURNEY` 阶段校验用户旅程地图、阶段分析、痛点优先级、核心机会点、产品切入策略等关键标题。
  - `BLUEPRINT` 阶段校验需求蓝图、产品概述、目标用户、核心需求、核心流程、成功指标、MVP 范围、风险评估等关键标题。
- 2026-06-05 已完成 typed Artifact Mermaid parse 校验:
  - 前端 typed event adapter 在接收 `artifact_update.type=replace` 后提取 Markdown 中的 ```mermaid 代码块。
  - 每个 Mermaid 图表进入 Store 和 Artifact 渲染链路前先执行 `mermaid.parse(...)`。
  - Mermaid parse 失败时直接抛出 `Artifact Mermaid parse failed`，不产出 artifact 更新 chunk。
- 2026-06-05 已新增真实 LLM/PydanticAI 冒烟测试入口:
  - 新增 `tests/test_agent_real_smoke.py`，标记为 `slow`，默认不会因缺少真实配置而失败。
  - 只有显式提供 `NEW_AGENTS_SMOKE_API_KEY`、`NEW_AGENTS_SMOKE_BASE_URL`、`NEW_AGENTS_SMOKE_MODEL` 时才会调用真实模型。
  - 冒烟测试会通过 `build_pydantic_agent_runtime(...)` 真实调用 PydanticAI，并验证 `TEST_DESIGN/CLARIFY` 输出能通过结构化契约与 Artifact 标题校验。
  - 当前已用 DeepSeek OpenAI-compatible endpoint 和 `deepseek-v4-flash` 执行真实模型调用，验证结构化输出、Pydantic 契约和 Artifact 标题校验可同时通过。
- 2026-06-05 已完成 DeepSeek V4 真实 smoke 兼容:
  - 首次真实调用在网络放开后返回 DeepSeek 400: `Thinking mode does not support this tool_choice`，说明 PydanticAI 结构化输出的 tool choice 与 DeepSeek V4 默认 thinking 模式不兼容。
  - 依据 DeepSeek 官方 Thinking Mode 文档和官方 Oh My Pi 集成说明，DeepSeek V4 thinking 默认开启，且 thinking 模式下不支持 `tool_choice`。
  - `agent_runtime.py` 新增 `build_model_settings(...)`，对 `deepseek-v4-*` 模型显式传入 `extra_body={"thinking": {"type": "disabled"}}`，不影响其他 OpenAI-compatible 模型默认行为。
  - `tests/test_agent_runtime.py` 新增 DeepSeek V4 settings 单元测试，防止后续移除该兼容设置。
  - `tests/test_agent_real_smoke.py` 收紧真实 smoke 提示词，要求模型逐字输出当前 Artifact 模板校验所需标题，避免真实模型自由改写标题导致误判。
- 2026-06-05 已删除主 Agent 对话的旧 `/api/chat/stream` 文本代理兜底:
  - `core/llm.ts` 在系统代理模式下只调用 `/new-agents/api/agent/runs/stream`，不再在阶段索引异常或工作流未接入时回退到文本代理。
  - 阶段索引非法时直接抛出 `当前工作流阶段不存在: <workflow>/<stageIndex>`，让状态错误及早暴露。
  - `/api/chat/stream` 当时仅作为 Mermaid 修复等通用文本工具的临时路径保留，不再作为主 Agent 产出协议路径。
  - `docs/architecture.md`、`docs/integration-architecture.md`、`docs/component-inventory.md` 已同步改为 typed Agent Runtime 主链路描述。
- 2026-06-05 已将 Mermaid 修复迁移到 typed utility endpoint:
  - 新增 `POST /api/utils/mermaid/repair`，由后端读取默认 LLM 配置、构造 Mermaid 修复提示词、调用 LLM 并返回 typed JSON: `{"repairedCode": "..."}`。
  - 新增 `MermaidRepairRequest` / `parse_mermaid_repair_request(...)`，显式校验 `brokenCode`、`errorMessage`、`blockIndex`。
  - 新增 `mermaid_repair_service.py` 和 `prompts/mermaid_repair.py`，把 Mermaid 修复提示词从前端迁到后端 prompt 模块。
  - `mermaidRetryService.ts` 不再依赖 `collectLlmResponse`、OpenAI 类型或 `/new-agents/api/chat/stream`，只调用 `/new-agents/api/utils/mermaid/repair`。
  - 删除前端无引用的 `core/utils/llmClient.ts` 和对应测试，并在 `testHygiene.test.ts` 中机械禁止前端源码继续调用 `/new-agents/api/chat/stream`。
  - 历史 P2 中对 `llmClient` 的类型清理成果已被本轮删除无引用文件取代，前端不再保留该通用文本代理客户端。
  - `docs/api-contracts.md`、`docs/architecture.md`、`docs/integration-architecture.md`、`docs/component-inventory.md` 已同步更新新 utility endpoint 与旧 chat stream 的边界。
- 2026-06-05 已删除后端 `/api/chat/stream` 遗留端点:
  - 删除 `routes.py` 中的 `/api/chat/stream` route，并从 API Key 中间件保护路径移除该旧路径。
  - 删除 `ChatStreamRequest`、`parse_chat_stream_request(...)`、`ChatDeltaEvent`、`stream_chat_events(...)` 及旧端点专属测试。
  - `llm_client.py` 继续保留为 Mermaid 修复工具的底层 LLM 文本调用服务，不再暴露为通用聊天代理 API。
  - `docs/api-contracts.md`、`docs/architecture.md`、`docs/ARCHITECTURE.md`、`docs/project-parts.json` 已移除旧端点的当前契约描述。
- 2026-06-05 已删除前端用户 API Key 直连旧协议:
  - `core/llm.ts` 不再导入 OpenAI SDK，不再构造浏览器端 OpenAI client，也不再通过 `parseLlmStreamChunk(...)` 解析 `<CHAT>/<ARTIFACT>/<ACTION>` 标签。
  - 删除 `core/utils/llmParser.ts`、对应单元测试和旧标签解析集成用例。
  - 删除旧的前端 LLM judge smoke 套件与前端 `openai` 依赖；当前真实模型冒烟入口统一保留在后端 `tests/test_agent_real_smoke.py`。
  - `SettingsModal` 改为说明 LLM 由后端默认配置统一管理，前端不再保存个人 API Key、Base URL 或模型名称。
  - `Workspace` 后端缺省配置 onboarding 改为提示维护后端 `llm_config`，不再引导用户在浏览器中配置 API Key。
- 2026-06-05 已收束入口文档中的旧技术栈与测试结构描述:
  - `docs/index.md` 不再把 `new-agents-frontend` 描述为浏览器端 OpenAI SDK 链路，改为 typed Agent Runtime SSE。
  - `docs/architecture.md` 与 `docs/ARCHITECTURE.md` 的服务拓扑表已标明后端使用 OpenAI SDK + PydanticAI。
  - `docs/TESTING.md` 的 New Agents 后端测试目录已从单一 `test_api.py` 更新为当前分层测试结构。
  - `docs/project-overview.md` 与 `docs/source-tree-analysis.md` 不再描述前端直连/双模式、`llmParser` 或前端 OpenAI SDK。
  - 旧技术债专项规则当时已改为当前事实: 旧 `/api/chat/stream` 已删除，后续不得恢复旧文本代理端点或旧标签协议作为兼容层；该专项规则已于 2026-06-25 退役，目标模式规则统一收敛到 `docs/strategy/`。
  - `docs/integration-architecture.md`、`docs/project-parts.json`、`docs/project-scan-report.json` 和架构文档标题不再把 New Agents 后端命名为旧式 LLM 代理后端，统一为结构化 Agent Runtime 后端。
- 验证证据:
  - `cd tools/new-agents/backend && python3 -m pytest tests/test_request_schemas.py tests/test_mermaid_repair_service.py tests/test_mermaid_repair_endpoint.py tests/test_routes_blueprint.py`: 22 passed。
  - `cd tools/new-agents/backend && python3 -m pytest tests/test_request_schemas.py tests/test_mermaid_repair_service.py tests/test_mermaid_repair_endpoint.py tests/test_routes_blueprint.py tests/test_api_auth.py`: 29 passed。
  - `cd tools/new-agents/frontend && npm test -- src/services/__tests__/mermaidRetryService.test.ts`: 先红，证明前端仍在走旧 `collectLlmResponse`。
  - `cd tools/new-agents/frontend && npm test -- src/__tests__/testHygiene.test.ts`: 先红，指向 `src/core/utils/llmClient.ts` 和其测试中的 `/new-agents/api/chat/stream`。
  - `cd tools/new-agents/frontend && npm test -- src/__tests__/testHygiene.test.ts src/services/__tests__/mermaidRetryService.test.ts`: 6 passed。
  - `cd tools/new-agents/frontend && npm test`: 190 passed。
  - `cd tools/new-agents/frontend && npm run lint`: 通过。
  - `cd tools/new-agents/backend && python3 -m pytest`: 135 passed, 1 skipped。
  - `flake8 --select=E9,F63,F7,F82 .`: 通过。
  - `cd tools/new-agents/backend && python3 -m pytest tests/test_routes_blueprint.py tests/test_request_schemas.py tests/test_sse_encoder.py tests/test_sse_response.py tests/test_stream_services.py tests/test_api.py tests/test_api_auth.py tests/test_mermaid_repair_endpoint.py tests/test_mermaid_repair_service.py tests/test_agent_endpoint.py`: 35 passed。
  - `cd tools/new-agents/backend && python3 -m pytest`: 78 passed, 1 skipped。
  - `cd tools/new-agents/frontend && npm test`: 190 passed。
  - `cd tools/new-agents/frontend && npm run lint`: 通过。
  - `flake8 --select=E9,F63,F7,F82 .`: 通过。
  - `rg '/api/chat/stream|/new-agents/api/chat/stream|chat/stream|ChatStreamRequest|parse_chat_stream_request|stream_chat_events|ChatDeltaEvent|chat_delta' tools/new-agents/backend tools/new-agents/frontend/src docs/api-contracts.md docs/architecture.md docs/ARCHITECTURE.md docs/integration-architecture.md docs/component-inventory.md docs/project-parts.json -g '!**/__pycache__/**'`: 只剩防回归测试断言命中，生产代码、前端源码和当前契约文档无旧端点残留。
  - `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts -t "isUserConfigured=true 且 apiKey 非空"`: 先红，证明旧代码仍进入浏览器 OpenAI SDK 分支。
  - `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts src/__tests__/p0-fixes.test.ts`: 37 passed。
  - `cd tools/new-agents/frontend && npm test -- src/__tests__/testHygiene.test.ts src/core/__tests__/llm.test.ts src/__tests__/p0-fixes.test.ts`: 42 passed。
  - `cd tools/new-agents/frontend && npm test`: 173 passed。
  - `cd tools/new-agents/frontend && npm run lint`: 通过。
  - `cd tools/new-agents/backend && python3 -m pytest`: 78 passed, 1 skipped。
  - `flake8 --select=E9,F63,F7,F82 .`: 通过。
  - `cd tools/new-agents/frontend && npm ls openai`: 依赖树为空，前端 package/lock 不再依赖 OpenAI SDK。
  - `rg 'from ['"'"'\"'"'"']openai['"'"'\"'"'"']|new OpenAI|OpenAI SDK|前端直连|直连模式|用户 API Key 前端|llmParser|parseLlmStreamChunk|detectArtifactTruncation|/new-agents/api/chat/stream|/api/chat/stream|ChatStreamRequest|ChatDeltaEvent|stream_chat_events|parse_chat_stream_request' tools/new-agents/frontend/src tools/new-agents/frontend/package.json tools/new-agents/frontend/package-lock.json docs/architecture.md docs/ARCHITECTURE.md docs/integration-architecture.md docs/component-inventory.md docs/api-contracts.md docs/project-parts.json`: 只剩防回归测试规则和后端当前 OpenAI SDK 说明，前端主链路无旧直连/旧协议残留。
  - `rg 'React 19 \+ Zustand \+ OpenAI SDK|Flask \+ SQLAlchemy \+ OpenAI \+ Gunicorn|Flask \+ OpenAI \+ Gunicorn|└── test_api\.py|/api/chat/stream|/new-agents/api/chat/stream' docs/index.md docs/TESTING.md docs/architecture.md docs/ARCHITECTURE.md docs/api-contracts.md docs/integration-architecture.md docs/component-inventory.md docs/project-parts.json`: 无输出，入口文档无旧前端 SDK、旧后端技术栈、旧测试布局或旧 chat stream 当前契约残留。
  - `rg '双模式|前端直连|后端代理 SSE|llmParser|先保留现有' docs/project-overview.md docs/source-tree-analysis.md docs/strategy`: 无输出，非归档概览/源码树/目标规则无旧双模式和旧端点保留指令残留；旧 `/api/chat/stream` 只在目标规则中以“已删除、不得恢复”的约束形式出现。
  - `rg 'LLM 代理|SSE 流式代理|双模式|前端直连|OpenAI SDK 6|OpenAI Python/JS SDK|llmParser|所有路由集中|app\.py.*路由' docs -g '!docs/plans/archive/**' -g '!docs/plans/completed/**' -g '!docs/plans/2026-03-07-new-agents-refactor.md' -g '!docs/plans/tech-debt.md'`: 无输出，非归档当前文档无旧 New Agents 代理命名和旧前端直连结构描述残留。
  - `python3 -m json.tool docs/project-parts.json` 与 `python3 -m json.tool docs/project-scan-report.json`: 通过，结构化元数据仍为合法 JSON。
  - `cd tools/new-agents/backend && python3 -m pytest tests/test_agent_real_smoke.py -q`: 1 skipped，原因是当前环境缺少真实模型环境变量。
  - `cd tools/new-agents/backend && python3 -m pytest tests/test_agent_runtime.py -q`: 4 passed。
  - `cd tools/new-agents/backend && python3 -m pytest tests/test_agent_runtime.py tests/test_agent_endpoint.py tests/test_stream_services.py -q`: 7 passed。
  - `cd tools/new-agents/backend && NEW_AGENTS_SMOKE_API_KEY=... NEW_AGENTS_SMOKE_BASE_URL=https://api.deepseek.com NEW_AGENTS_SMOKE_MODEL=deepseek-v4-flash python3 -m pytest tests/test_agent_real_smoke.py -q`: 1 passed。
  - `cd tools/new-agents/backend && python3 -m pytest`: 80 passed, 1 skipped。
  - `cd tools/new-agents/frontend && npm test`: 173 passed。
  - `cd tools/new-agents/frontend && npm run lint`: 通过。
  - `flake8 --select=E9,F63,F7,F82 .`: 通过。
  - `git diff --check`: 通过。
  - `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts -t "阶段索引非法"`: 先红，证明旧代码会回退 chat stream 并产出 `legacy`。
  - `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts`: 31 passed。
  - `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts src/core/utils/__tests__/llmClient.test.ts src/services/__tests__/mermaidRetryService.test.ts`: 41 passed。
  - `cd tools/new-agents/frontend && npm test`: 197 passed。
  - `cd tools/new-agents/frontend && npm run lint`: 通过。
  - `rg 'generateResponseStreamViaProxy|parseChatProxyEvent|ChatProxyEvent|/new-agents/api/chat/stream|解析 <CHAT>|<ACTION>NEXT_STAGE|主 Agent 对话走|agent/runs/stream' tools/new-agents/frontend/src/core/llm.ts docs/integration-architecture.md docs/architecture.md docs/component-inventory.md`: `core/llm.ts` 只保留 `/new-agents/api/agent/runs/stream`；后续已删除通用文本代理端点及对应当前文档描述。
  - `cd tools/new-agents/backend && pytest`: 90 passed, 1 skipped。
  - `cd tools/new-agents/backend && pytest tests/test_agent_real_smoke.py -q`: 1 skipped，原因是缺少真实模型环境变量。
  - `python3 -c "from agent_runtime import build_pydantic_agent_runtime; ..."`: runtime builder 可实例化。
  - `flake8 --select=E9,F63,F7,F82 .`: 通过。
  - `cd tools/new-agents/frontend && npm test`: 188 passed。
  - `cd tools/new-agents/frontend && npm run lint`: 通过。
- 收束状态:
  - P0 当前明确范围已完成: 主链路不再依赖旧标签解析，非法输出不会进入 Artifact 渲染链路，`TEST_DESIGN/CLARIFY` 真实模型 smoke 已通过。

### 已决策 P1: 暂缓引入 LangGraph，保留轻量阶段工作流

**决策**: 当前不把 LangGraph 作为第一阶段重构主线。

原因:

- 当前智能体核心是轻量、阶段式、人工确认推进的工作流，不是复杂图编排。
- LangGraph 的 node、edge、conditional edge、checkpoint 等概念会引入额外框架成本。
- 当前最痛的问题是输出结构不稳定和渲染失败，PydanticAI + 应用级校验可以先缓解大部分问题。
- 过早引入图运行时会把问题从“输出契约不稳”扩大成“运行时迁移 + 状态模型迁移 + UI 事件迁移”。

保留后续评估条件:

- 如果后续出现跨阶段回跳、并行子任务、长任务恢复、复杂人工审批、可回放执行历史等需求，再评估 LangGraph。
- 如果 Deep Agents 作为长任务能力接入，由于其底层依赖 LangGraph，可在特定新工作流内局部使用，而不是重写全部 Lisa/Alex 主链路。

### 已完成 P1: 抽出 Agent Core 纯逻辑层

**目标**: 把当前散落在 Store、Hook、组件里的业务状态机集中到可测试的纯逻辑模块。

范围:

- 阶段切换规则。
- Artifact 更新策略。
- 版本历史生成。
- pending stage transition 处理。
- LLM 输出事件到 UI 状态的 reducer。

完成标准:

- `chatService` 不再直接判断核心业务规则，只负责调用 runtime 和派发事件。
- `ChatPane` 不再负责构造业务提示词或推进阶段，只负责交互展示。
- 核心规则有单元测试覆盖。

当前进展:

- 2026-06-05 已完成第一块纯逻辑抽离:
  - 新增 `tools/new-agents/frontend/src/core/agentCore.ts`。
  - 将流式 chunk 的业务决策抽为 `reduceAgentStreamChunk(...)`，包括普通 Artifact 写入、`NEXT_STAGE` pending transition、停止继续消费未确认新阶段 Artifact、Artifact 截断标记。
  - `chatService` 不再直接判断这些规则，只执行 reducer 返回的决策。
  - 新增 `src/core/__tests__/agentCore.test.ts` 覆盖纯逻辑。
- 2026-06-05 已完成 retry 回滚逻辑抽离:
  - 新增 `planRetryFromHistory(...)`，从聊天历史中找到最后一条用户消息，计算需要回滚的消息数量，并返回待恢复的输入和附件。
  - `chatService.handleRetry` 不再手写倒序查找和回滚计算，只执行 Agent Core 返回的 retry plan。
- 2026-06-05 已完成 Artifact 版本写入决策抽离:
  - 新增 `planArtifactVersionUpdate(...)`，将“空内容不写、欢迎页不写、最后版本重复不写、真实新内容才写”的判断集中到 Agent Core。
  - `chatService` 只负责读取 Store、调用决策函数，并在需要写入时补充 `id` 和 `timestamp`。
- 2026-06-05 已完成阶段确认推进逻辑抽离:
  - 新增 `planStageTransitionConfirmation(...)`，将 pending transition 校验、当前阶段 Artifact 保存、目标阶段 Artifact 恢复/默认内容生成集中到 Agent Core。
  - `store.confirmStageTransition` 不再直接实现阶段推进业务规则，只负责调用 Agent Core 并提交状态变更。
- 2026-06-05 已完成 ChatPane 阶段确认动作下沉:
  - `useChatService` 新增 `handleConfirmStageTransition(...)`，统一执行确认阶段和继续生成。
  - `ChatPane` 不再直接调用 Store 推进阶段，也不再硬编码继续生成提示词，只负责渲染确认卡片并触发服务层 handler。
  - 顺手将 `ChatPane.test.tsx` 中相关 hook mock 从 `(useChatService as any)` 改为 `vi.mocked(useChatService)`。
- 验证证据:
  - `cd tools/new-agents/frontend && npm test -- src/core/__tests__/agentCore.test.ts src/__tests__/store.test.ts src/__tests__/p0-fixes.test.ts src/services/__tests__/chatService.test.ts src/components/__tests__/ChatPane.test.tsx`: 54 passed。
  - `cd tools/new-agents/frontend && npm test`: 175 passed。
  - `cd tools/new-agents/frontend && npm run lint`: 通过。
- 收束状态:
  - P1 Agent Core 当前明确范围已完成，无本优先级内待处理的本地技术债切片。

### 已完成 P2: 收敛 Prompt 职责

**目标**: Prompt 只描述任务目标、判断标准和上下文，不继续承担字符级输出协议和渲染格式修复职责。

范围:

- 从 `buildSystemPrompt` 中移除 `<CHAT>/<ARTIFACT>/<ACTION>` 标签协议说明。
- 将 Artifact 结构要求迁移到 Pydantic 模型、模板渲染器和校验器。
- 将 Mermaid 约束迁移到应用级校验和修复链路。

当前进展:

- 2026-06-05 已完成第一块标签协议清理:
  - `buildSystemPrompt` 不再要求模型输出 `<CHAT>`、`<ARTIFACT>`、`<ACTION>`、`NO_UPDATE` 等字符级协议。
  - 阶段推进规则改为语义约束：阶段完成时询问用户确认；用户确认后表达可以推进；具体阶段切换由结构化事件/应用状态机处理。
  - 保留工作流、当前阶段、阶段目标、当前 Artifact 上下文，避免把任务目标一起删掉。
  - 新增 `buildSystemPrompt` 单元测试约束旧标签协议不得回流到 prompt 中。
- 2026-06-05 已完成 Mermaid 全局修复提示清理:
  - `buildSystemPrompt` 不再包含 Mermaid 渲染崩溃、HTML 换行、特殊字符包裹、围栏格式、`${FENCE}` 等渲染修复细节。
  - Mermaid 稳定性继续由应用层承担：typed Artifact adapter 在进入 Store 前执行 `mermaid.parse(...)`，组件层继续使用 sanitizer、降级渲染和 `mermaidRetryService`。
  - 保留各阶段模板中的业务图表示例，本切片不扩大到模板体系重写。
- 2026-06-05 已完成 `TEST_DESIGN` 模板强约束清理:
  - 前端结构化 Agent Runtime 从 `TEST_DESIGN/CLARIFY` 扩展到 `TEST_DESIGN` 全阶段，和后端 `REQUIRED_ARTIFACT_HEADINGS` 的全阶段契约对齐。
  - `buildSystemPrompt` 不再为 `TEST_DESIGN` 注入 `currentStage.template` 的“唯一合法格式”“禁止增删章节标题”等强模板段落。
- 2026-06-05 已完成 `REQ_REVIEW` 模板强约束清理:
  - 前端结构化 Agent Runtime 扩展到 `REQ_REVIEW` 全阶段，和后端 `REQUIRED_ARTIFACT_HEADINGS` 的需求评审契约对齐。
  - `buildSystemPrompt` 不再为 `REQ_REVIEW` 注入 `currentStage.template` 的“唯一合法格式”“禁止增删章节标题”等强模板段落。
- 2026-06-05 已完成 `INCIDENT_REVIEW` 模板强约束清理:
  - 前端结构化 Agent Runtime 扩展到 `INCIDENT_REVIEW` 全阶段，和后端 `REQUIRED_ARTIFACT_HEADINGS` 的故障复盘契约对齐。
  - `buildSystemPrompt` 不再为 `INCIDENT_REVIEW` 注入 `currentStage.template` 的“唯一合法格式”“禁止增删章节标题”等强模板段落。
- 2026-06-05 已完成 `IDEA_BRAINSTORM` 模板强约束清理:
  - 前端结构化 Agent Runtime 扩展到 `IDEA_BRAINSTORM` 全阶段，和后端 `REQUIRED_ARTIFACT_HEADINGS` 的创意工作流契约对齐。
  - `buildSystemPrompt` 不再为 `IDEA_BRAINSTORM` 注入 `currentStage.template` 的“唯一合法格式”“禁止增删章节标题”等强模板段落。
- 2026-06-05 已完成 `VALUE_DISCOVERY` 模板强约束清理:
  - 前端结构化 Agent Runtime 扩展到 `VALUE_DISCOVERY` 全阶段，和后端 `REQUIRED_ARTIFACT_HEADINGS` 的价值发现契约对齐。
  - `buildSystemPrompt` 不再为 `VALUE_DISCOVERY` 注入 `currentStage.template` 的“唯一合法格式”“禁止增删章节标题”等强模板段落。
  - 迁移完成后，所有已定义工作流都走 typed Agent Runtime；用户自配 API Key 前端直连旧路径已在 P0 收束中删除。
- 验证证据:
  - `cd tools/new-agents/frontend && npm test -- src/core/prompts/__tests__/buildSystemPrompt.test.ts`: 6 passed。
  - `cd tools/new-agents/frontend && npm test -- src/core/prompts/__tests__/buildSystemPrompt.test.ts src/core/__tests__/llm.test.ts src/__tests__/p0-fixes.test.ts`: 50 passed。
  - `cd tools/new-agents/frontend && npm test -- src/core/prompts/__tests__/buildSystemPrompt.test.ts src/core/__tests__/llm.test.ts src/components/__tests__/Mermaid.test.tsx src/services/__tests__/mermaidRetryService.test.ts src/core/__tests__/mermaid.test.ts src/core/__tests__/mermaidSanitizer.test.ts`: 51 passed。
  - `cd tools/new-agents/frontend && npm test -- src/core/prompts/__tests__/buildSystemPrompt.test.ts src/core/__tests__/llm.test.ts src/__tests__/p0-fixes.test.ts src/services/__tests__/chatService.test.ts`: 61 passed。
  - `cd tools/new-agents/backend && pytest tests/test_agent_contracts.py tests/test_agent_endpoint.py tests/test_agent_runtime.py`: 25 passed。
  - `cd tools/new-agents/frontend && npm test -- src/core/__tests__/llm.test.ts src/core/prompts/__tests__/buildSystemPrompt.test.ts`: 42 passed。
  - `cd tools/new-agents/frontend && npm test`: 188 passed。
  - `cd tools/new-agents/backend && pytest`: 90 passed, 1 skipped。
  - `cd tools/new-agents/frontend && npm run lint`: 通过。
  - `flake8 --select=E9,F63,F7,F82 .`: 通过。
- 收束状态:
  - P2 Prompt 职责收敛当前明确范围已完成，无本小节内待处理的本地技术债切片。

### 已完成 P2: 清理前端类型与渲染债务

范围:

- 消除源码中的 `as any`、`@ts-ignore`、不必要的宽泛 `catch`。
- 统一 Markdown/Mermaid 渲染组件，避免 ChatPane 与 ArtifactPane 各自维护补丁逻辑。
- 清理测试中的诊断 stdout 和 React `act(...)` 警告。

当前进展:

- 2026-06-05 已完成测试 stdout 与 `act(...)` 警告清理第一块:
  - 新增 `src/__tests__/testHygiene.test.ts`，约束非 smoke 测试文件不得遗留 `console.log` 诊断输出。
  - `pages/__tests__/Workspace.test.tsx` 显式等待后端配置检查完成，并断言不会产生 React `act(...)` 警告。
- 2026-06-05 已完成测试 stderr 清理第一块:
  - `src/__tests__/testHygiene.test.ts` 扩展为同时约束非 smoke 测试文件不得遗留直接 `console.error` 诊断输出。
  - `core/__tests__/mermaid.test.ts` 删除 Mermaid parse 失败时的直接 stderr 输出，失败仍通过断言暴露。
  - `services/__tests__/mermaidRetryService.test.ts` 对预期失败路径显式 spy `console.error` 并断言日志行为，避免全量测试输出 stderr。
- 2026-06-05 已完成 Mermaid 组件类型逃逸清理第一块:
  - `src/__tests__/testHygiene.test.ts` 新增 Mermaid 渲染切片类型卫生约束，禁止 `Mermaid.tsx` 和 `Mermaid.test.tsx` 使用 `as any`、`@ts-ignore`、`@ts-expect-error`。
  - `components/Mermaid.tsx` 改用 Mermaid 官方导出的 `MermaidConfig`，移除 `suppressErrorRendering` 上的 `@ts-ignore`，并删除 `catch (...: any)`。
  - `components/__tests__/Mermaid.test.tsx` 删除已过期的 store mock，改用 Mermaid 官方 `ParseResult`、`RenderResult` 类型构造 mock 返回值。
- 2026-06-05 已完成 `llmClient` 类型逃逸清理第一块:
  - `src/__tests__/testHygiene.test.ts` 将类型卫生约束扩展到 `core/utils/llmClient.ts` 和 `core/utils/__tests__/llmClient.test.ts`，同时禁止受控文件中的 `catch (...: any)`。
  - `core/utils/__tests__/llmClient.test.ts` 新增完整 `ChatState` 测试工厂，移除 store mock 返回值上的 `as any`。
  - `core/utils/__tests__/llmClient.test.ts` 改用标准 `Response` 和 `ReadableStream<Uint8Array>` 构造 fetch mock，移除 SSE/错误响应 mock 上的 `as any`。
  - `core/utils/llmClient.ts` 将两个 `catch (e: any)` 改为 `unknown` 处理路径，并用显式错误消息提取函数保留原有 abort 透传和错误包装语义。
- 2026-06-05 已完成前端剩余类型逃逸清理:
  - `src/__tests__/testHygiene.test.ts` 将类型卫生约束扩展到 `services/chatService.ts` 和当时仍存在的 `core/__tests__/smoke/llmJudge.ts`。
  - `services/chatService.ts` 将 `catch (error: any)` 改为 `unknown` 处理路径，并保留中断停止、配额提示和普通错误展示语义。
  - `core/__tests__/smoke/llmJudge.ts` 当时将 `catch (error: any)` 改为 `unknown` 处理路径；该旧 LLM judge smoke 后续已整体删除。
  - 当前 `tools/new-agents/frontend/src` 中除 `testHygiene.test.ts` 自身的规则文本外，已无 `as any`、`@ts-ignore`、`@ts-expect-error`、`catch (...: any)` 残留。
- 2026-06-05 已删除前端旧 LLM judge smoke 套件:
  - 删除 `core/__tests__/smoke/llmJudge.ts` 和 `workflow.smoke.test.ts`，不再保留要求 `<CHAT>/<ARTIFACT>/<ACTION>` 标签的旧端到端判卷脚本。
  - `package.json` 删除 `test:smoke` 旧脚本，普通 `npm test` 不再需要排除旧 smoke 目录。
  - Mermaid 模板语法 smoke `core/__tests__/smoke/mermaid.smoke.test.ts` 保留并纳入普通测试。
- 2026-06-05 已完成 Mermaid retry 替换逻辑统一第一块:
  - `core/utils/markdownUtils.ts` 新增 `replaceMermaidBlockAtIndex(...)`，集中处理按索引替换第 N 个 Mermaid 代码块、目标不存在和替换内容无变化等逻辑。
  - `components/ArtifactPane.tsx` 和 `components/ChatPane.tsx` 不再各自维护 `matchAll(...)`、字符串下标拼接和 Mermaid fence 重建逻辑，统一调用该纯函数。
  - `core/__tests__/markdownUtils.test.ts` 新增覆盖多个 Mermaid block、目标不存在、替换内容无变化三个场景的单元测试。
  - 当前 Mermaid retry 的代码块定位正则只保留在 `markdownUtils.ts` 的单一事实来源中。
- 2026-06-05 已完成 ReactMarkdown Mermaid code renderer 统一第一块:
  - 新增 `components/markdownCodeRenderer.tsx`，集中处理 `language-mermaid` 识别、`${FENCE}` 还原、尾随换行清理、Mermaid block index 分配和 `<Mermaid />` 渲染。
  - `components/ArtifactPane.tsx` 和 `components/ChatPane.tsx` 改为通过 `createMarkdownCodeRenderer(...)` 复用 Mermaid code 分支，普通代码块和 inline code 样式继续由各自组件传入。
  - 新增 `components/__tests__/markdownCodeRenderer.test.tsx`，覆盖 Mermaid 代码块规范化与普通代码块委托渲染。
- 2026-06-05 已删除历史 Mermaid 诊断测试:
  - `src/__tests__/testHygiene.test.ts` 新增约束，禁止非 smoke 测试套件继续保留 `diag`/`diagnostic` 命名的临时诊断测试文件。
  - 删除 `components/__tests__/mermaid-diag.test.tsx`；其原本验证的 Mermaid 内容传递与规范化行为，已由 `components/__tests__/markdownCodeRenderer.test.tsx` 作为正式 shared renderer 行为测试覆盖。
- 2026-06-05 已完成 ReactMarkdown component props 类型收敛第一块:
  - `src/__tests__/testHygiene.test.ts` 将 `ArtifactPane.tsx`、`ChatPane.tsx`、`markdownCodeRenderer.tsx` 和 shared renderer 测试纳入类型卫生约束，并禁止受控文件继续出现 `}: any)` 形式的 ReactMarkdown props 宽泛类型。
  - `components/ArtifactPane.tsx` 和 `components/ChatPane.tsx` 改用 `react-markdown` 本地导出的 `Components` 类型为 component map 提供上下文类型。
  - 本轮未使用 Context7，因为当前环境没有 Context7 工具；类型依据来自本地 `node_modules/react-markdown/index.d.ts`。
- 2026-06-05 已完成 `llm.test.ts` OpenAI mock 类型收敛:
  - `src/__tests__/testHygiene.test.ts` 将 `core/__tests__/llm.test.ts` 纳入类型卫生约束，并禁止受控文件继续出现裸 `: any` 类型逃逸。
  - `core/__tests__/llm.test.ts` 为 OpenAI 构造参数、mock client、stream chunk、store override 建立显式测试类型。
  - OpenAI mock 构造函数不再使用 `this: any` / `args: any`，`collectStream(...)` 和 `resetStore(...)` 不再依赖宽泛 `any`。
- 验证证据:
  - `cd tools/new-agents/frontend && npm test -- src/__tests__/testHygiene.test.ts src/core/__tests__/llm.test.ts`: 33 passed。
  - `cd tools/new-agents/frontend && npm test -- src/__tests__/testHygiene.test.ts src/components/__tests__/markdownCodeRenderer.test.tsx`: 5 passed。
  - `cd tools/new-agents/frontend && npm test -- src/__tests__/testHygiene.test.ts src/components/__tests__/ArtifactPane.test.tsx src/components/__tests__/ChatPane.test.tsx src/components/__tests__/markdownCodeRenderer.test.tsx`: 19 passed。
  - `cd tools/new-agents/frontend && npm test -- src/__tests__/testHygiene.test.ts src/core/__tests__/mermaid.test.ts src/services/__tests__/mermaidRetryService.test.ts`: 7 passed。
  - `cd tools/new-agents/frontend && npm test -- src/__tests__/testHygiene.test.ts src/components/__tests__/Mermaid.test.tsx`: 8 passed。
  - `cd tools/new-agents/frontend && npm test -- src/__tests__/testHygiene.test.ts src/core/utils/__tests__/llmClient.test.ts`: 8 passed。
  - `cd tools/new-agents/frontend && npm test -- src/__tests__/testHygiene.test.ts src/services/__tests__/chatService.test.ts`: 9 passed。
  - `cd tools/new-agents/frontend && npm test -- src/core/__tests__/markdownUtils.test.ts src/components/__tests__/ArtifactPane.test.tsx src/components/__tests__/ChatPane.test.tsx`: 20 passed。
  - `cd tools/new-agents/frontend && npm test -- src/components/__tests__/markdownCodeRenderer.test.tsx src/components/__tests__/ArtifactPane.test.tsx src/components/__tests__/ChatPane.test.tsx`: 16 passed。
  - `cd tools/new-agents/frontend && npm test`: 195 passed。
  - `cd tools/new-agents/frontend && npm run lint`: 通过。
  - `rg "as any|@ts-ignore|@ts-expect-error|catch \\([^)]*: any|\\}: any\\)|:\\s*any\\b" tools/new-agents/frontend/src --glob '!**/testHygiene.test.ts'`: 无输出。
  - `rg "as any|@ts-ignore|@ts-expect-error|catch \\([^)]*: any" tools/new-agents/frontend/src -n --glob '!tools/new-agents/frontend/src/__tests__/testHygiene.test.ts' --glob '!src/__tests__/testHygiene.test.ts' --glob '!testHygiene.test.ts'`: 无输出。
  - `rg "as any|@ts-ignore|@ts-expect-error|catch \\([^)]*: any|\\}: any\\)" tools/new-agents/frontend/src/components/ArtifactPane.tsx tools/new-agents/frontend/src/components/ChatPane.tsx tools/new-agents/frontend/src/components/markdownCodeRenderer.tsx tools/new-agents/frontend/src/components/__tests__/markdownCodeRenderer.test.tsx -n`: 无输出。
  - `rg 'matchAll\\(|newBlock|replaceMermaidBlockAtIndex' tools/new-agents/frontend/src/components tools/new-agents/frontend/src/core/utils tools/new-agents/frontend/src/core/__tests__/markdownUtils.test.ts -n`: `matchAll(...)` 仅位于 `core/utils/markdownUtils.ts`，两个组件只引用 `replaceMermaidBlockAtIndex(...)`。
  - `rg 'language-\\(\\\\w\\+\\)|FENCE|createMarkdownCodeRenderer|<Mermaid' tools/new-agents/frontend/src/components -n`: 生产组件中的 Mermaid code 分支集中在 `components/markdownCodeRenderer.tsx`，`ArtifactPane.tsx` 与 `ChatPane.tsx` 只调用 `createMarkdownCodeRenderer(...)`。
  - `rg --files tools/new-agents/frontend/src | rg '(^|[-_.])diag([-_.]|$)|diagnostic'`: 无输出。
- 收束状态:
  - P2 前端类型与渲染债务当前明确范围已完成，无本小节内待处理的本地技术债切片。

### 已完成 P3: 后端 LLM Gateway 分层

原范围:

- 从 `app.py` 拆出 routes、services、schemas、llm_client、sse_encoder。
- 早期阶段曾统一 `/api/chat/stream` 与新 Agent Runtime 的 SSE 事件格式；主链路迁移完成后，旧 `/api/chat/stream` 已删除。
- 修复前后端 `content` / `response` 字段不一致的契约缺口，并通过 typed `agent_turn/error` 事件收束。

当前进展:

- 2026-06-05 已完成 SSE schema/encoder 第一块:
  - 新增 `tools/new-agents/backend/sse_schemas.py`，定义 `chat_delta`、`agent_turn`、`error` 三类 typed SSE event。
  - 新增 `tools/new-agents/backend/sse_encoder.py`，集中处理 `data: ...\n\n` 与 `[DONE]` 编码，`/api/chat/stream` 和 `/api/agent/runs/stream` 不再各自手写 JSON SSE 拼接。
  - `/api/chat/stream` 普通增量从裸 `{"content": ...}` 收敛为 `{"type": "chat_delta", "content": ...}`。
  - 两个流式端点的错误事件统一为 `{"type": "error", "code": "...", "message": "..."}`，不再输出裸 `error` 字段。
  - 前端 `core/utils/llmClient.ts` 和 `core/llm.ts` 的代理流解析统一消费 `chat_delta/content` 与 `error/message`，删除旧 `response` 字段消费。
  - `docs/api-contracts.md` 已同步更新 New Agents Backend typed SSE 契约，并补充 `/api/agent/runs/stream`。
- 2026-06-05 已完成 `llm_client` service 抽离第一块:
  - 新增 `tools/new-agents/backend/llm_client.py`，集中创建 OpenAI client、调用 `chat.completions.create(...)` 并提取非空 delta content。
  - `/api/chat/stream` route 不再直接导入或创建 `OpenAI` client，只负责请求校验、配置读取、调用 service、SSE 编码和错误事件映射。
  - 后端 API/错误处理/聊天历史测试的 OpenAI mock 目标从 `app.OpenAI` 迁移到 `llm_client.OpenAI`。
  - `docs/TESTING.md` 已同步更新 new-agents-backend 的 OpenAI Client mock 入口。
- 2026-06-05 已完成 request schemas / validation helper 抽离第一块:
  - 新增 `tools/new-agents/backend/request_schemas.py`，用 Pydantic 模型定义 `ChatStreamRequest` 和 `AgentRunStreamRequest`。
  - 新增 `RequestValidationError`、`parse_chat_stream_request(...)`、`parse_agent_run_stream_request(...)`，集中保留现有中文错误文案。
  - `/api/chat/stream` route 不再内联读取 `messages`、`model`、`temperature` 字段。
  - `/api/agent/runs/stream` route 不再内联读取和逐项校验 `prompt`、`systemPrompt`、`workflowId`、`stageId`。
- 2026-06-05 已完成 routes / Blueprint 抽离第一块:
  - 新增 `tools/new-agents/backend/routes.py`，定义 `api_bp = Blueprint("new_agents_api", ..., url_prefix="/api")`。
  - `health`、`config`、`chat/stream`、`agent/runs/stream` 四个 API route 已迁移到 `routes.py`。
  - `tools/new-agents/backend/app.py` 不再定义具体 `@app.route(...)`，只保留应用工厂、CORS/DB 初始化、请求 hooks、全局错误处理和 `app.register_blueprint(api_bp)`。
  - Agent endpoint 测试的 PydanticAI runtime mock 目标从 `app.build_pydantic_agent_runtime` 迁移到 `routes.build_pydantic_agent_runtime`。
- 2026-06-05 已完成 stream services 编排抽离第一块:
  - 新增 `tools/new-agents/backend/stream_services.py`，集中编排 chat stream 和 agent runtime 两条 typed event 流。
  - `stream_chat_events(...)` 负责调用 `llm_client.stream_chat_completion_content(...)`，并将 OpenAI 认证、限流、API 和非预期异常映射为 `ErrorEvent`。
  - `stream_agent_run_events(...)` 负责调用 PydanticAI runtime，并将契约校验、schema 校验、依赖缺失和 LLM 异常映射为 `ErrorEvent`。
  - `routes.py` 不再直接导入 `OpenAI` 异常、PydanticAI runtime builder 或具体 `ChatDeltaEvent` / `AgentTurnEvent` / `ErrorEvent`，只负责请求解析、配置读取、调用 service、SSE 编码和 HTTP Response。
  - Agent endpoint 测试的 PydanticAI runtime mock 目标从 `routes.build_pydantic_agent_runtime` 迁移到 `stream_services.build_pydantic_agent_runtime`。
- 2026-06-05 已完成默认 LLM 配置 service 抽离第一块:
  - 新增 `tools/new-agents/backend/config_service.py`，集中查询 active default `LlmConfig`。
  - 新增 `build_default_llm_config_payload(...)`，统一构造 `/api/config` 公开响应，并继续保证不暴露 `api_key`。
  - `routes.py` 不再直接导入 `LlmConfig` 或调用 `LlmConfig.query`，只通过 `get_active_default_llm_config(...)` 获取配置。
- 2026-06-05 已完成 SSE Response helper 抽离第一块:
  - 新增 `tools/new-agents/backend/sse_response.py`，集中构造 `text/event-stream` Flask `Response`。
  - `build_sse_response(...)` 负责遍历 typed `SseEvent`、调用 `encode_sse_event(...)`、自动追加 `[DONE]`，并统一设置 `Cache-Control: no-cache` 与 `X-Accel-Buffering: no`。
  - `routes.py` 不再直接导入 `Response`，也不再重复书写 `mimetype="text/event-stream"` 或 SSE headers。
- 2026-06-05 已完成路由错误响应与默认配置 guard 抽离第一块:
  - 新增 `tools/new-agents/backend/api_responses.py`，集中构造 JSON error 响应，并把默认 LLM 配置缺失的 503 中文错误契约收敛为单一事实来源。
  - 新增 `tools/new-agents/backend/route_guards.py`，集中处理两个流式端点共享的 active default `LlmConfig` 读取与缺失响应。
  - `routes.py` 不再重复手写 `jsonify({"error": ...})` 或默认 LLM 配置缺失文案，两个流式端点只调用 `require_default_llm_config(...)`。
  - `/api/config` 的异常处理从宽泛 `Exception` 收窄为 `SQLAlchemyError`，非数据库类未知异常继续交给 Flask 全局错误处理及早暴露。
- 2026-06-05 已完成 P3 后端分层收束审计:
  - 新增 `tools/new-agents/backend/tests/test_backend_layering.py`，用架构测试机械约束 `app.py`、`routes.py`、`stream_services.py`、`llm_client.py`、`request_schemas.py`、`config_service.py`、`sse_encoder.py` 的职责边界。
  - `routes.py` 不再直接调用 `get_active_default_llm_config(...)`，`/api/config` 改为通过 `get_default_llm_config_payload(...)` 读取公开配置 payload。
  - `llm_client.py` 新增 `LlmClientError` 和 `extract_delta_content(...)`，显式包装 OpenAI 基类错误并校验流式 chunk 结构。
  - `stream_services.py` 不再保留宽泛 `except Exception`，普通聊天流只捕获明确的 OpenAI 错误与 `LlmClientError`。
  - 畸形 LLM 响应不再依赖路由层或 stream service 的任意异常兜底；缺少 choices、非字符串 delta content 会转为 `STREAM_ERROR`，空 choices / 空 delta / 空 content 作为无内容 chunk 忽略。
- 验证证据:
  - `cd tools/new-agents/backend && python3 -m pytest tests/test_backend_layering.py tests/test_llm_client.py tests/test_stream_services.py tests/test_api.py::test_chat_stream_openai_error`: 10 passed。
  - `cd tools/new-agents/backend && python3 -m pytest tests/test_config_service.py tests/test_backend_layering.py tests/test_routes_blueprint.py tests/test_api.py::test_get_config_no_default tests/test_api.py::test_get_config_with_default tests/test_api.py::test_chat_stream_success tests/test_agent_endpoint.py::test_agent_runs_stream_returns_typed_sse_event`: 17 passed。
  - `cd tools/new-agents/backend && python3 -m pytest tests/test_api_responses.py tests/test_route_guards.py tests/test_routes_blueprint.py`: 9 passed。
  - `cd tools/new-agents/backend && python3 -m pytest tests/test_api.py::test_get_config_no_default tests/test_api.py::test_get_config_with_default tests/test_api.py::test_chat_stream_empty_body tests/test_api.py::test_chat_stream_missing_config tests/test_api.py::test_chat_stream_success tests/test_agent_endpoint.py::test_agent_runs_stream_rejects_missing_prompt tests/test_agent_endpoint.py::test_agent_runs_stream_returns_typed_sse_event tests/test_error_handling.py`: 40 passed。
  - `cd tools/new-agents/backend && python3 -m pytest tests/test_sse_response.py tests/test_routes_blueprint.py`: 5 passed。
  - `cd tools/new-agents/backend && python3 -m pytest tests/test_api.py::test_chat_stream_success tests/test_api.py::test_chat_stream_openai_error tests/test_agent_endpoint.py::test_agent_runs_stream_returns_typed_sse_event tests/test_sse_encoder.py tests/test_stream_services.py`: 9 passed。
  - `cd tools/new-agents/backend && python3 -m pytest tests/test_config_service.py tests/test_api.py::test_get_config_no_default tests/test_api.py::test_get_config_with_default tests/test_api.py::test_chat_stream_missing_config tests/test_api.py::test_chat_stream_success tests/test_agent_endpoint.py::test_agent_runs_stream_returns_typed_sse_event`: 8 passed。
  - `cd tools/new-agents/backend && python3 -m pytest tests/test_stream_services.py tests/test_api.py::test_chat_stream_success tests/test_api.py::test_chat_stream_openai_error tests/test_agent_endpoint.py::test_agent_runs_stream_returns_typed_sse_event`: 6 passed。
  - `cd tools/new-agents/backend && python3 -m pytest tests/test_routes_blueprint.py tests/test_api.py::test_health_endpoint tests/test_api.py::test_get_config_with_default tests/test_api.py::test_chat_stream_success tests/test_agent_endpoint.py::test_agent_runs_stream_returns_typed_sse_event`: 7 passed。
  - `cd tools/new-agents/backend && python3 -m pytest tests/test_sse_encoder.py tests/test_api.py::test_chat_stream_success tests/test_api.py::test_chat_stream_openai_error tests/test_agent_endpoint.py::test_agent_runs_stream_returns_typed_sse_event`: 6 passed。
  - `cd tools/new-agents/backend && python3 -m pytest tests/test_llm_client.py tests/test_api.py::test_chat_stream_success tests/test_chat_history.py::TestMultiTurnChatHistory::test_single_turn_chat tests/test_chat_history.py::TestSessionStateManagement::test_model_override`: 5 passed。
  - `cd tools/new-agents/backend && python3 -m pytest tests/test_request_schemas.py tests/test_api.py::test_chat_stream_empty_body tests/test_api.py::test_chat_stream_success tests/test_agent_endpoint.py::test_agent_runs_stream_rejects_missing_prompt tests/test_agent_endpoint.py::test_agent_runs_stream_returns_typed_sse_event tests/test_chat_history.py::TestMessageFormatValidation::test_empty_messages_array`: 13 passed。
  - `cd tools/new-agents/backend && python3 -m pytest`: 93 passed, 1 skipped。
  - `cd tools/new-agents/backend && python3 -m pytest`: 95 passed, 1 skipped。
  - `cd tools/new-agents/backend && python3 -m pytest`: 103 passed, 1 skipped。
  - `cd tools/new-agents/backend && python3 -m pytest`: 106 passed, 1 skipped。
  - `cd tools/new-agents/backend && python3 -m pytest`: 109 passed, 1 skipped。
  - `cd tools/new-agents/backend && python3 -m pytest`: 112 passed, 1 skipped。
  - `cd tools/new-agents/backend && python3 -m pytest`: 114 passed, 1 skipped。
  - `cd tools/new-agents/backend && python3 -m pytest`: 119 passed, 1 skipped。
  - `cd tools/new-agents/backend && python3 -m pytest`: 125 passed, 1 skipped。
  - `cd tools/new-agents/frontend && npm test -- src/core/utils/__tests__/llmClient.test.ts src/core/__tests__/llm.test.ts`: 37 passed。
  - `cd tools/new-agents/frontend && npm test`: 196 passed。
  - `cd tools/new-agents/frontend && npm run lint`: 通过。
  - `flake8 --select=E9,F63,F7,F82 .`: 通过。
  - `rg '@app\\.route|OpenAI|chat\\.completions\\.create|build_pydantic_agent_runtime|ChatDeltaEvent|AgentTurnEvent|ErrorEvent|Response\\(|text/event-stream|jsonify\\(\\{\"error\"|except Exception|LlmConfig\\.query|get_active_default_llm_config|LlmClientError' tools/new-agents/backend/app.py tools/new-agents/backend/routes.py tools/new-agents/backend/stream_services.py tools/new-agents/backend/llm_client.py tools/new-agents/backend/config_service.py tools/new-agents/backend/tests/test_backend_layering.py -g '*.py'`: `app.py` 只保留应用工厂/全局 hook，`routes.py` 无 SDK、运行时、SSE、默认配置底层查询和宽泛异常残留；SDK 调用集中在 `llm_client.py`，运行时事件编排集中在 `stream_services.py`，默认配置查询集中在 `config_service.py`。
  - `rg 'jsonify\(\{\"error\"|系统未配置默认 LLM|require_default_llm_config|default_llm_config_missing_response|except Exception' tools/new-agents/backend/routes.py tools/new-agents/backend/api_responses.py tools/new-agents/backend/route_guards.py tools/new-agents/backend/tests -g '*.py'`: `routes.py` 无手写 JSON error、无默认 LLM 缺失文案、无宽泛 `except Exception`，默认配置 guard 和缺失响应集中在 helper。
  - `rg 'Response\\(|text/event-stream|X-Accel-Buffering|Cache-Control|build_sse_response' tools/new-agents/backend/routes.py tools/new-agents/backend/sse_response.py tools/new-agents/backend/tests -g '*.py'`: 生产 SSE Response 包装只保留在 `sse_response.py`，`routes.py` 只调用 `build_sse_response(...)`。
  - `rg 'LlmConfig\\.query|from models import LlmConfig|get_active_default_llm_config|build_default_llm_config_payload|hasDefault|api_key' tools/new-agents/backend/routes.py tools/new-agents/backend/config_service.py tools/new-agents/backend/tests -g '*.py'`: `LlmConfig.query` 只保留在 `config_service.py` 和模型/测试内，`routes.py` 无直接查询依赖。
  - `rg 'build_pydantic_agent_runtime|stream_chat_completion_content|AuthenticationError|RateLimitError|APIError|ContractValidationError|ValidationError|AgentRuntimeDependencyError|ErrorEvent|ChatDeltaEvent|AgentTurnEvent' tools/new-agents/backend/routes.py tools/new-agents/backend/stream_services.py tools/new-agents/backend/tests -g '*.py'`: 运行时编排和错误事件映射集中在 `stream_services.py`，`routes.py` 只保留 `RequestValidationError` 处理。
  - `rg '@app\\.route|@api_bp\\.route|register_blueprint|Blueprint|build_pydantic_agent_runtime|@patch\\("app\\.build_pydantic_agent_runtime"' tools/new-agents/backend/app.py tools/new-agents/backend/routes.py tools/new-agents/backend/tests -g '*.py'`: 具体 API route 只在 `routes.py`，`app.py` 仅注册 `api_bp`。
  - `rg 'data\\.get|prompt =|system_prompt =|workflow_id =|stage_id =|messages =|model_override =|temperature =|prompt 不能为空|systemPrompt 不能为空|workflowId 不能为空|stageId 不能为空|messages 不能为空' tools/new-agents/backend/app.py tools/new-agents/backend/request_schemas.py`: 请求字段读取和错误文案已集中到 `request_schemas.py`，`app.py` 无内联字段校验残留。
  - `rg 'data: \{\"error\"|data: \{\"content\"|\"response\"' tools/new-agents/backend tools/new-agents/frontend/src docs/api-contracts.md -g '!**/__pycache__/**'`: 除测试中显式断言不包含 `response` 外，无旧 SSE 契约残留。
  - `rg 'from openai import OpenAI|OpenAI\(|chat\.completions\.create|@patch\(['"'"'\"'"'"']app\.OpenAI' tools/new-agents/backend -g '*.py'`: OpenAI SDK 直接调用仅保留在 `llm_client.py` 和对应测试中，`app.py` 无直接 OpenAI client 耦合。
- 收束状态:
  - P3 后端 LLM Gateway 分层当前明确范围已完成；旧 `/api/chat/stream` 文本代理路径已删除。
  - 当前跨优先级剩余事项只保留 P0 真实 LLM 冒烟验证，依赖外部真实模型环境变量。
