# DeepSeek V4 Real Smoke Gate Design

## Milestone

DeepSeek V4 `artifact_data` 真实 smoke gate 对齐。

## 用户故事

作为 AI4SE 维护者，当我准备验证真实 DeepSeek V4 Flash 兼容性时，我可以运行一个可选 slow smoke。这个 smoke 不再要求模型直接输出完整 Markdown，而是验证真实模型通过 JSON object 返回 `artifact_data`，再由后端 renderer 和 artifact contract 生成最终 Markdown。

## 范围

- 改造 `tools/new-agents/backend/tests/test_agent_real_smoke.py`，将旧的“直接 Markdown artifact”真实 smoke 更新为 “DeepSeek raw JSON/artifact_data renderer” smoke。
- 保留默认无凭证时 skip 的行为，避免本地测试默认访问网络。
- 继续兼容通用 `NEW_AGENTS_SMOKE_*` 环境变量，同时支持更语义化的 `DEEPSEEK_V4_SMOKE_*` 覆盖。
- smoke 使用 `PydanticAgentRuntime` 的 raw streaming config，确保命中 `response_format={"type":"json_object"}` 和 DeepSeek thinking disabled 的 runtime 路径。
- smoke 断言最终 `AgentTurnOutput` 通过 renderer 后含 CLARIFY 必需标题和 Mermaid；chat 不含 Markdown 文档正文；不请求下一阶段。
- 新增本地单元测试覆盖 env 解析、缺 env skip、prompt/contract 不再要求模型输出 Markdown。
- 更新 DeepSeek todo，说明真实 smoke gate 已可选化并对齐 `artifact_data`；真实网络执行仍不作为默认本地门禁。

## 非目标

- 不在本轮调用真实 DeepSeek 网络。
- 不新增供应商专属 runtime、API、store 或 renderer。
- 不改变正常 `/api/agent/runs/stream` 路径。
- 不修改前端。

## 验收条件

1. 无 smoke env 时，真实 smoke 显式 skip 并说明所需 env。
2. `test_agent_real_smoke.py` 不再要求模型输出 `artifact_update.markdown`，而要求模型返回 `artifact_data`。
3. smoke 运行路径使用 raw JSON streaming runtime，并仍由现有 renderer/contract 输出 Markdown artifact。
4. 相关 runtime/smoke 测试通过。
5. DeepSeek todo 记录该策略，避免后续误用旧 Markdown smoke。

## 风险

- 真实 smoke 依赖供应商网络、凭证和额度，本轮只提供可选门禁与本地可验证的测试结构。
- DeepSeek 输出质量仍可能受真实模型版本影响；失败时应暴露 schema/contract 错误，而不是伪造成功。
