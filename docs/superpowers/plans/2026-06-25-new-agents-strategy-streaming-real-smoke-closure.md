# New Agents STRATEGY 真实部署复核与归档 Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:verification-before-completion before claiming completion. This plan is evidence and documentation only; do not modify runtime code.

**Goal:** 用本地部署后的真实 SSE 路径复核 TEST_DESIGN / STRATEGY 阶段，关闭右侧产物流式渲染残余 smoke 和测试策略格式回归两个活跃 todo。

**Architecture:** 继续使用共享 `/new-agents/api/agent/runs/stream` typed Agent Runtime、Nginx gateway、run persistence 和现有 artifact renderer；不新增脚本、不新增 workflow 专属 runtime/API/store/renderer。

---

## Tasks

- [x] **Step 1: 部署当前主工作区**

Run:

```bash
./scripts/dev/deploy-dev.sh
```

Expected: Docker dev stack starts, health check passes, New Agents available at `http://localhost/new-agents`.

- [x] **Step 2: 捕获 CLARIFY -> STRATEGY 真实 SSE**

用临时 Python 脚本请求 `http://localhost/new-agents/api/agent/runs/stream`：

- 先请求 `TEST_DESIGN/CLARIFY` 创建 run。
- 再带同一 `runId` 请求 `TEST_DESIGN/STRATEGY`。
- 记录 event 时间、`agent_delta` 数量、final 前 artifact delta 数量和 Markdown 长度。

- [x] **Step 3: 校验 STRATEGY snapshot 最终格式**

请求 `GET http://localhost/new-agents/api/agent/runs/{runId}`，校验：

- 必需标题齐全。
- Mermaid fenced block 至少 2 个。
- `quadrantChart` 和 `block-beta` 存在。
- `ai4se-visual` `risk-board` 是合法 JSON，含非空 `columns` / `rows`。
- 不包含“下一步计划”章节。

- [x] **Step 4: 独立 STRATEGY 再跑一轮**

不依赖前一轮 run，直接请求 `TEST_DESIGN/STRATEGY`，再次验证 final 前 artifact delta 递增和最终格式。

- [x] **Step 5: 归档 todo 并提交**

移动两个活跃 todo 到 `docs/todos/archive/`，补充真实 runId、验证结果和残余风险；更新 `docs/todos/refactor/README.md`。

Run:

```bash
git diff --check
```

只 stage 本轮文档归档文件，不 stage 部署或测试生成物。
