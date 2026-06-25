# New Agents 测试策略阶段产出物格式错误回归 Todo

状态：已完成当前版本复核
创建日期：2026-06-25
完成日期：2026-06-25
相关模块：`tools/new-agents/`

## 背景

本地部署后人工验证发现，测试用例生成流程第二阶段“测试策略制定”仍然反复生成格式错误的右侧产出物。此前 `docs/todos/archive/2026-06-24-new-agents-test-strategy-artifact-format-streaming-bug.md` 已收敛过 STRATEGY 阶段的结构化流式契约与前端 delta 覆盖，但本次手工验证说明问题没有彻底消除，至少还存在真实模型输出或渲染链路下的回归场景。

## 当前观察

- 复现场景：本地部署后进入 New Agents 测试用例生成流程，完成第一阶段需求澄清并进入第二阶段“测试策略制定”。
- 现象：右侧测试策略产出物依然反复出现格式错误。
- 影响：用户无法稳定获得正式可读的《测试策略蓝图》，后续用例编写阶段也可能继承错误格式或不完整策略输入。
- 重要上下文：此前修复偏向提示词契约和 typed SSE 流式解析；本次需要重新捕获真实运行时 payload，确认错误发生在模型输出、`artifact_data` 渲染、Markdown/Mermaid/ai4se-visual 合同，还是前端渲染层。

## 2026-06-25 相关处理记录

目标模式本轮优先处理了右侧产物真实流式渲染 P0，并确认 STRATEGY 当前主链路要求模型输出 `artifact_data`，后端 deterministic renderer 负责生成 Markdown、Mermaid `quadrantChart` / `block-beta` 和 `ai4se-visual` `risk-board`。

本轮新增的段落级 partial renderer 覆盖了 `TEST_DESIGN/STRATEGY` 的 `artifact_data` 流式增量，能减少“生成期间长期无右侧正式内容”的问题；但它没有替代真实失败 payload 复盘，也没有修改 STRATEGY prompt 或 Mermaid / risk-board 语法合同。因此本 todo 在当时保持活跃，后续必须用本地真实运行捕获的 SSE、最终 Markdown 或截图来定位格式错误首次出现层级，不能仅凭 deterministic streaming 修复归档。

同轮验证还发现一个相关质量证据：默认环境启用 `NEW_AGENTS_E2E_LLM_JUDGE=1` 时，`./scripts/test/test-local.sh all` 在 `test_lisa_final_artifact_passes_optional_llm_judge` 失败，Lisa mock 最终产物得分 83。外部 judge 指出第三方登录覆盖缺失、弱网支付场景未单独成例、安全审计日志验证不足，以及“先暂不进入策略阶段”后阶段引导略混乱。确定性 E2E 在 `NEW_AGENTS_E2E_LLM_JUDGE=0` 下通过，因此该问题更像 Lisa 测试设计产物质量 / judge fixture 缺口，而不是本轮 streaming 代码回归。后续处理本 todo 时应把该 judge failure 作为质量验收输入。

## 2026-06-25 真实部署复核记录

目标模式后续轮次已在本地 Docker 部署后的真实 `/new-agents/api/agent/runs/stream` 路径复核该问题，没有只依赖 mock E2E 或 synthetic unit tests。

### 部署与健康检查

- `./scripts/dev/deploy-dev.sh`：通过，脚本完成前端构建、后端镜像重建、Nginx 重启和部署后健康检查。
- New Agents URL：`http://localhost/new-agents`
- New Agents API health：`curl http://localhost/new-agents/api/health` 返回 `{"service":"new-agents-backend","status":"ok"}`。

### 真实 SSE 证据

1. CLARIFY -> STRATEGY 串联复核：
   - CLARIFY runId：`2c150676-7897-44bb-8412-32709651999b`
   - STRATEGY 使用同一 runId 请求第二阶段。
   - STRATEGY SSE 结果：HTTP 200，`text/event-stream`，无 `error` event。
   - STRATEGY `agent_delta`：67 个；final 前 artifact delta：9 个。
   - artifact 长度序列：`330 -> 843 -> 3243 -> 4028 -> 4807 -> 5823 -> 6060 -> 6183 -> 6183`。
   - final artifact 长度：6183；`stage_action` 请求进入 `CASES`。

2. 独立 STRATEGY 复核：
   - runId：`ec9abf49-702e-42cd-a2de-debfe15095fc`
   - SSE 结果：HTTP 200，`text/event-stream`，无 `error` event。
   - final 前 artifact delta：9 个。
   - artifact 长度序列：`197 -> 644 -> 2857 -> 3375 -> 4082 -> 4833 -> 5012 -> 5117 -> 5117`。
   - final artifact 长度：5117；`stage_action` 请求进入 `CASES`。

### 最终格式校验

对 run `2c150676-7897-44bb-8412-32709651999b` 的 `GET /new-agents/api/agent/runs/{runId}` snapshot 做结构校验：

- 必需标题齐全：H1、策略摘要、质量目标、FMEA、风险矩阵、风险明细、测试技术选型、测试分层、测试点拓扑、资源取舍、阶段门禁。
- fenced code block：3 个。
- Mermaid：2 个，包含 `quadrantChart` 和 `block-beta`。
- `ai4se-visual`：1 个，类型为 `risk-board`，JSON 合法，`columns` / `rows` 非空。
- 未包含“下一步计划”章节。

结论：当前部署版本下，TEST_DESIGN / STRATEGY 没有复现“反复格式错误”，且真实 SSE 与 persisted snapshot 都满足当前合同。因此本 todo 以“当前版本真实 smoke 通过”归档。

### 残余风险

- 本轮没有拿到用户最初观察到的失败产物截图、原始 SSE 或后端 raw JSON，因此不能反推出当时的具体坏 payload。
- 子智能体只读审计指出潜在薄弱点仍存在：Mermaid label 转义只覆盖双引号、final 与 delta 前端校验强度不同、真实模型若输出特殊字符或中途截断仍可能暴露局部格式问题。
- 如果该问题复发，应新建 todo 并附带原始 SSE、最终 Markdown、截图和 provider/model/base_url；不要仅用“格式错误”描述恢复实施。

## 目标能力包

定位并修复 TEST_DESIGN / STRATEGY 阶段产出物格式错误的真实根因，确保本地部署真实运行时第二阶段可以稳定生成正式、可渲染、通过合同校验的测试策略蓝图。

该能力包必须继续复用共享 Agent Runtime、typed SSE、workflow manifest、artifact contract、持久化 run/artifact 模型和共享 UI 渲染基础设施；不允许为 Lisa、测试设计、DeepSeek 或某个模型新增专属 runtime、API path、store 或 renderer。

## 建议排查方向

1. 重新捕获本地部署下 TEST_DESIGN / STRATEGY 的完整 typed SSE 流，包括 `agent_delta`、最终 `agent_turn`、`warnings` 和后端日志。
2. 对比模型原始输出、后端解析后的 `artifact_data`、后端渲染出的 Markdown、前端收到的 Markdown、前端最终渲染结果，定位格式错误首次出现的位置。
3. 检查 STRATEGY `artifact_data` schema 是否仍允许不稳定字段进入渲染层，例如空 Mermaid 节点、非法 quadrant 坐标、risk-board 数值类型不一致、阶段门禁或表格字段缺失。
4. 检查 `render_test_design_strategy_markdown(...)` 生成的 Mermaid quadrantChart、block-beta 和 ai4se-visual risk-board 是否能用真实样例通过前端 Mermaid 预校验和结构化可视化解析。
5. 检查当前提示词是否仍在某处要求模型手写 Markdown/Mermaid/risk-board，导致与 `artifact_data` 结构化契约冲突。
6. 如错误只在特定模型或 provider 出现，记录 model/base_url/capability 设置，但修复仍应走共享 capability 或 contract，不新增模型专属 UI 分支。

## 验收标准

- 本地部署真实运行时 TEST_DESIGN / STRATEGY 阶段不再反复产生格式错误。
- 最终《测试策略蓝图》包含稳定 H1、策略摘要、质量目标、FMEA 风险矩阵、风险明细、测试技术选型、测试分层、测试点拓扑、资源取舍和阶段门禁。
- Mermaid quadrantChart / block-beta 可以通过前端预校验，不出现破碎代码块或无法解析图表。
- ai4se-visual risk-board 是合法 JSON，字段和值类型可被共享结构化可视化组件渲染。
- 后端测试覆盖真实失败样例或最小等价样例，证明 `artifact_data -> Markdown -> 前端解析` 链路稳定。
- 修复不得绕过 artifact contract，不得把右侧产物降级成纯文本、裸 JSON 或隐藏错误。

## 建议测试

- 后端 renderer 回归测试：使用本地复现捕获的 STRATEGY `artifact_data` 或最小失败样例，验证渲染 Markdown 含合法 Mermaid 与 risk-board。
- 后端 runtime 测试：STRATEGY raw JSON streaming 输出在最终前后都能生成可渲染 artifact。
- 前端 parser/renderer 测试：真实失败样例 Markdown 能通过 Mermaid sanitizer / `StructuredVisual` 解析，或在非法时给出明确错误而不是展示破碎产物。
- 部署后 smoke：在本地 `http://localhost/new-agents` 真实跑一次测试用例生成到第二阶段，记录最终产物截图或 SSE/日志证据。

## 非目标

- 不重新设计所有 TEST_DESIGN 阶段。
- 不新增专属 renderer 或专属 API。
- 不把模型错误静默隐藏为“生成成功”。
- 不在没有真实失败样例的情况下只做提示词微调后归档。

## 复发时必须补充的证据

- 具体测试输入。
- 失败产物截图或 Markdown 原文。
- 后端日志中的 raw JSON / `artifact_data` / 渲染后 Markdown。
- 使用的 provider、model、base_url 和 capability 设置。
