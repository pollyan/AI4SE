# DeepSeek V4 真实 Smoke Gate 与证据闭环设计

## 自问自答头脑风暴

**Q1: 这个能力包的真实用户意图是什么？**

A: New Agents 维护者需要确认 DeepSeek V4 Flash 在真实供应商链路下仍能走通当前生产契约：模型只输出 `artifact_data`，后端确定性 renderer 生成 Markdown/Mermaid/`ai4se-visual`，再由 artifact contract 和 typed runtime 接住。当前本地 readiness 已覆盖 deterministic 链路，但真实 smoke 测试仍验证旧的 `artifact_update.markdown` 直接输出形态，证据语义已经落后。

**Q2: 完成后用户多完成了什么？**

A: 维护者可以继续使用 `./scripts/test/test-local.sh smoke` 或直接运行 `tools/new-agents/backend/tests/test_agent_real_smoke.py`。无凭证时得到明确 skip；有凭证、网络和额度时，真实 DeepSeek smoke 会验证 JSON object mode、thinking disabled、`artifact_data` 输出、renderer、artifact contract 和 chat/artifact 分离，而不是验证旧 Markdown 输出协议。

**Q3: 哪些相邻小缺口必须合并？**

A: 必须同时合并 smoke prompt、运行入口、环境变量 skip 行为、DeepSeek provider 设置断言、`artifact_data` renderer/contract 断言、测试策略说明和 DeepSeek todo 状态记录。只改 prompt 或只改文档都会留下证据断层。

**Q4: 哪些内容必须排除？**

A: 不在本轮新增供应商凭证、不联网安装依赖、不把真实 DeepSeek 调用纳入默认 CI、不新增 DeepSeek 专属 runtime/API/store/renderer、不用 mock 结果声称真实 smoke 通过。真实外部调用只在用户显式提供 `NEW_AGENTS_SMOKE_*` 环境变量和网络/额度时运行。

**Q5: 有哪些实现路径？**

A: 路径一是只改 `test_agent_real_smoke.py` 的 prompt，让真实模型直接按 `artifact_data` 返回，再断言 renderer 输出。优点是最小，缺点是缺少 deterministic gate 证明 smoke 请求参数和 skip 语义。路径二是新增独立 smoke runner 脚本，pytest 只包一层。优点是 CLI 语义清晰，缺点是新增入口和维护面。路径三是在现有 pytest smoke 内补 deterministic tests 和真实测试：mock `stream_chat_completion_content` 证明请求参数与 renderer 路径，真实测试继续按 env gate 运行。推荐路径三，因为它复用现有入口、最小化架构变化，并让无凭证环境也能验证 smoke gate 本身没有漂移。

**Q6: 推荐路径的主要风险是什么？**

A: 第一，真实模型可能仍输出不合格 `artifact_data`，这应作为 smoke 失败暴露，而不是被 mock 掩盖。第二，现有 `build_partial_agent_delta()` 只从 `markdown` 字段抽取 partial artifact，对 `artifact_data` streaming 不产生右侧增量；这不影响最终 smoke gate，本轮不扩大到 streaming UX。第三，环境缺少前端依赖导致 `npm run lint` 无法运行；本轮只改后端 smoke 和文档，前端 CI 门禁不适用。

**Q7: TDD 验收证据是什么？**

A: 先写失败测试，证明现有 smoke system prompt 仍要求 `artifact_update` / `markdown` 而不是 `artifact_data`。再写 deterministic mock streaming 测试，证明 smoke runtime 使用 DeepSeek JSON object mode、thinking disabled，最终 `artifact_data` 会被 renderer 转成 contract-valid CLARIFY artifact。最后运行真实 smoke 测试，在无 env 时应 skip 且说明缺少变量；有 env 时才执行真实调用。

**Q8: 无法验证真实外部调用时怎么处理？**

A: 收尾说明必须把真实 DeepSeek 调用列入“未运行验证及原因”，不能说真实 smoke 已通过。todo 中也要记录 gate 已与当前结构化链路对齐，但真实外部证据仍取决于凭证、网络和额度。

## Spec

### 用户故事

作为 New Agents 维护者，当我准备验证 DeepSeek V4 Flash 的结构化输出兼容性时，我希望真实 smoke gate 验证当前 `artifact_data -> deterministic renderer -> artifact contract` 链路，并在缺少外部条件时明确跳过，从而避免用旧 Markdown 输出协议或 mock 结果误判真实供应商状态。

### 范围

本轮进入范围：

- 更新 `tools/new-agents/backend/tests/test_agent_real_smoke.py`，让真实 smoke 以 `TEST_DESIGN/CLARIFY` 的 `artifact_data` schema 为验证对象。
- 为 smoke gate 增加 deterministic 测试，mock raw streaming 输出 contract-valid `artifact_data`，断言 DeepSeek 请求参数、system prompt、renderer 输出和 chat/artifact 分离。
- 保留 `NEW_AGENTS_SMOKE_API_KEY`、`NEW_AGENTS_SMOKE_BASE_URL`、`NEW_AGENTS_SMOKE_MODEL` 环境变量 gate。
- 更新 `docs/TESTING.md` 和 DeepSeek todo，说明真实 smoke 的当前语义、外部条件和未运行口径。

本轮不进入范围：

- 不新增真实凭证管理。
- 不联网安装依赖或调用真实 DeepSeek，除非环境已显式提供 smoke env。
- 不新增 DeepSeek 专属 runtime、API path、store 或 renderer。
- 不改变默认 `scripts/test/test-local.sh` 的普通测试门禁；真实 smoke 仍只在 `smoke` 参数下运行。
- 不把 deterministic mock 测试称为真实 DeepSeek 验证。

### 设计

`test_agent_real_smoke.py` 继续作为真实模型 smoke 的唯一 pytest 入口。文件内拆出三个清晰责任：

1. 环境变量读取：缺少任一 `NEW_AGENTS_SMOKE_*` 变量时 skip，并列出缺失变量。
2. smoke prompt：system prompt 明确要求 JSON object 中包含 `chat`、`artifact_data`、`stage_action`、`warnings`，禁止模型输出完整 Markdown、Mermaid、表格或 `artifact_update.markdown`。
3. smoke 断言：无论 deterministic mock 还是真实调用，最终都必须返回 contract-valid `AgentTurnOutput`，其 artifact 来自 CLARIFY renderer，chat 不含 artifact Markdown 结构，`stage_action` 为 `None` 或符合当前阶段规则。

deterministic 测试通过 monkeypatch `agent_runtime.stream_chat_completion_content` 代替外部网络，返回合法 CLARIFY `artifact_data` JSON。测试断言实际请求参数包含 `response_format={"type":"json_object"}`、`extra_body={"thinking":{"type":"disabled"}}`，system prompt 包含 `artifact_data` 且不包含要求模型输出 `artifact_update.markdown` 的旧协议。

真实测试继续使用 `build_pydantic_agent_runtime()`，因为该 builder 已经为 DeepSeek V4 配置 raw streaming、JSON object mode、thinking disabled 和 artifact_data instruction。真实调用结果必须通过 `validate_agent_turn()` 隐式验证，并显式断言必需标题、Mermaid flowchart 和 chat/artifact 分离。

### 错误处理

- 缺少 env：pytest skip，输出缺失变量名。
- OpenAI SDK / provider 错误：测试失败，暴露真实供应商问题。
- JSON decode / schema / renderer / artifact contract 失败：测试失败，沿用 `FormattedOutputDiagnosticError` 或 runtime schema/model error。
- 模型把完整 artifact Markdown 放入 `chat`：测试失败。

### 验收条件

1. 无 env 时，真实 smoke 测试明确 skip，不声明真实 DeepSeek 通过。
2. deterministic smoke gate 测试能证明 DeepSeek 请求参数、system prompt 和 `artifact_data` renderer 路径正确。
3. 真实 env 存在时，smoke 断言 CLARIFY artifact 包含 `# 需求分析文档`、必需章节和 Mermaid flowchart，且 `chat` 不含 Markdown artifact 结构。
4. 文档和 todo 说明真实 smoke 的语义已经从旧 Markdown 输出协议更新为 `artifact_data` 结构化链路。

### 验证计划

- `cd tools/new-agents/backend && python3 -m pytest tests/test_agent_real_smoke.py -q`
- `cd tools/new-agents/backend && python3 -m pytest tests/test_deepseek_v4_readiness.py -q`
- `python3 -m py_compile tools/new-agents/backend/tests/test_agent_real_smoke.py`
- `git diff --check`

真实 DeepSeek 外部调用只有在 `NEW_AGENTS_SMOKE_*` 环境变量、网络和额度齐备时运行；否则记录为未运行外部验证。

### 自审

- 不含未解释占位符。
- 范围只覆盖真实 smoke gate 与证据记录，不引入新 runtime 或 UI。
- 验收条件区分 deterministic gate、skip 和真实外部验证。
