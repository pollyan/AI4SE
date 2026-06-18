# 2026-06-06 New Agents 测试策略审计

## 背景

本次审计由一个真实缺陷触发：右侧 artifact 正常更新，但左侧 chat 同时展示了一份完整 artifact 文档。根因是旧测试只验证了 artifact 能写入右侧，没有验证 `chat` 与 `artifact_update.markdown` 的字段职责分离。

## 策略更新

- `AGENTS.md` 已新增 New Agents 测试契约，要求修改智能体链路时按职责层补测试。
- `docs/TESTING.md` 已新增 New Agents 测试职责分层、覆盖率口径和策略符合性审计清单。

## 当前场景覆盖状态

本次审计中的“覆盖率”按场景覆盖率计算：正向场景、异常场景、边界场景、跨字段不变量、跨层不变量和供应商兼容。工具行覆盖率只作为辅助指标。

| 场景维度 | 当前状态 | 证据 | 缺口/后续动作 |
|----------|----------|------|----------------|
| 正向场景 | 基本覆盖 | 后端 `test_agent_endpoint.py`、`test_stream_services.py`；前端 `llm.test.ts` 覆盖 typed `agent_turn`、多工作流首阶段、artifact 写入；契约层已覆盖所有阶段合法完整 artifact 模板 | 仍缺少浏览器级端到端正向样例 |
| 异常场景 | 已补关键链路，仍需扩展 | 请求字段缺失、默认配置缺失、PydanticAI retries 失败、契约失败、供应商 HTTP/API/Auth/RateLimit 错误、SSE error、坏 Mermaid、坏 SSE JSON 已覆盖 | 数据库异常在 agent endpoint 维度还可补 API 场景 |
| 边界场景 | 部分覆盖 | 最后阶段禁止推进、非法阶段、空 artifact、无用户消息 retry、空/欢迎 artifact 版本写入已覆盖 | 还缺 warnings 透传、空 chat、空 body、空白字段在 endpoint 层的组合检查 |
| 跨字段不变量 | 已覆盖核心事故 | `chat` 不承载 artifact；`artifact_update.markdown` 承载完整 Markdown；`NEXT_STAGE` 不直接写未确认下一阶段产物 | 后续新增字段时必须同步补该字段与现有字段的串位测试 |
| 跨层不变量 | 已覆盖关键路径 | API 测试解析 SSE JSON；前端 LLM 层拆分 chat、最终 chunk 才写 artifact；状态层只写 `chatResponse` / `newArtifact`；后端契约阶段 ID 与前端 workflow 配置保持同步 | 缺少浏览器级手动/Playwright 脚本来验证真实 UI 左右栏行为 |
| 供应商兼容 | 有可选冒烟 | DeepSeek V4 model settings/retries 单测；真实模型 smoke 依赖 `NEW_AGENTS_SMOKE_*` | smoke 不进普通门禁；发布前需要显式运行 |

## 当前测试职责覆盖状态

| 层次 | 当前状态 | 证据 |
|------|----------|------|
| 后端契约层 | 已覆盖关键不变量 | `test_agent_contracts.py` 覆盖 chat/artifact 分离、artifact 必需更新、必需标题、阶段推进、JSON 字符串嵌套对象 |
| 后端运行时层 | 已覆盖运行时契约入口 | `test_agent_runtime.py` 覆盖 PydanticAI 输出转项目契约、工作流规则拒绝、DeepSeek V4 模型设置 |
| 后端 API/SSE 层 | 已覆盖 typed SSE 和字段解析 | `test_stream_services.py`、`test_agent_endpoint.py`、`test_sse_encoder.py` 覆盖成功/错误事件、缺默认配置、prompt 契约注入、SSE JSON 字段断言 |
| 前端 LLM 流解析层 | 已覆盖主要流式行为 | `llm.test.ts` 覆盖 typed SSE、旧 endpoint 禁用、渐进 chunk、最终 artifact 更新、Mermaid 拦截、SSE error、坏 SSE JSON 报错 |
| 前端状态编排层 | 已覆盖左右栏写入边界 | `chatService.test.ts`、`agentCore.test.ts` 覆盖 assistant 只写 chatResponse、artifact 只写 newArtifact、NEXT_STAGE 待确认 |
| 真实模型冒烟层 | 已覆盖但不进普通门禁 | `test_agent_real_smoke.py` 覆盖真实模型输出合法 artifact 和干净 chat，依赖 `NEW_AGENTS_SMOKE_*` |
| 旧协议清理 | 已覆盖 | `testHygiene.test.ts` 禁止旧 `/api/chat/stream` 和 `<CHAT>/<ARTIFACT>` 协议回流 |

## 已运行验证

- 后端常规门禁：`cd tools/new-agents/backend && python3 -m pytest -m "not slow" -q`
  - 结果：`90 passed, 1 deselected`
- 前端全量：`cd tools/new-agents/frontend && npm test`
  - 结果：`175 passed`
- 前端类型检查：`cd tools/new-agents/frontend && npm run lint`
  - 结果：通过
- Python 关键 lint：`flake8 --select=E9,F63,F7,F82 .`
  - 结果：通过
- Diff 空白检查：`git diff --check`
  - 结果：通过

## 工具覆盖率现状

当前不能声称工具覆盖率满足要求，原因如下：

1. 后端 `pytest-cov` 在本地环境挂住：
   - `cd tools/new-agents/backend && python3 -m pytest --cov=. --cov-report=term-missing -q`
   - `cd tools/new-agents/backend && python3 -m pytest -m "not slow" --cov=<关键模块> --cov-report=term-missing -q`
   - 两者均超过合理等待时间无输出，已手动结束进程。
2. 前端 Vitest coverage 缺依赖：
   - `cd tools/new-agents/frontend && npm test -- --coverage`
   - 失败原因：缺少 `@vitest/coverage-v8`。

## 结论

当前 New Agents 的场景覆盖率已经比事故发生前明显更完整：核心不变量已落到契约层、API/SSE 层和前端状态层，不再只依赖 happy path。

但测试保护还不能视为完成，后续应按优先级继续补：

1. 增加浏览器级手动/Playwright 验证脚本，覆盖真实 UI 中左侧流式文本与右侧 artifact 同步更新。
2. 补齐 agent endpoint 的数据库异常 API 场景。
3. 修复后端 `pytest-cov` 在 new-agents 下挂住的问题，明确工具覆盖率命令和阈值。
4. 为 `tools/new-agents/frontend` 增加 Vitest coverage provider，并设定前端工具覆盖率报告命令。
