# New Agents STRATEGY 产物格式与流式真实复核设计

## User Story

作为目标模式执行 Agent，我需要用本地部署后的真实 `/new-agents/api/agent/runs/stream` 路径复核 TEST_DESIGN / STRATEGY 阶段，确认当前版本的右侧产物既能段落级增量出现，也能生成格式稳定的《测试策略蓝图》，从而关闭剩余两个活跃 todo 或留下可审计阻塞。

## Current State Gap Analysis

- `docs/todos/refactor/2026-06-25-new-agents-artifact-streaming-deep-diagnosis.md` 已完成确定性修复，但缺少本地真实模型 smoke。
- `docs/todos/refactor/2026-06-25-new-agents-test-strategy-artifact-format-regression.md` 要求不能在没有真实 payload 的情况下猜测修复；需要捕获真实 SSE、最终 Markdown 和格式校验证据。
- 仓库没有已提交的部署后真实 SSE 捕获脚本；已有 `test_agent_real_smoke.py` 只覆盖 runtime，不覆盖 Nginx / HTTP / SSE / run persistence 路径。
- 当前可执行路径是先部署本地 Docker 栈，再用临时脚本请求 `http://localhost/new-agents/api/agent/runs/stream`，记录 `run_started`、`agent_delta`、`agent_turn`、`[DONE]` 的时间、artifact 长度和错误事件。

## Acceptance Criteria

- 本地 `./scripts/dev/deploy-dev.sh` 成功，`scripts/health/health_check.sh local` 通过。
- TEST_DESIGN / STRATEGY 真实 SSE 返回 HTTP 200 和 `text/event-stream`，事件中没有 `error`。
- `agent_turn` 之前至少出现多个 `agent_delta.output.artifact_update.type=replace`，且 Markdown 长度有多个递增值。
- 最终 STRATEGY Markdown 包含测试策略蓝图必需章节、2 个 Mermaid 代码块和合法 `ai4se-visual` `risk-board` JSON。
- 若无法满足以上条件，应保留 todo 为活跃或记录阻塞，而不是归档。

## Evidence Scope

本轮只做部署后真实 smoke 与文档归档，不改后端 runtime、前端 parser、prompt、renderer 或测试代码。
