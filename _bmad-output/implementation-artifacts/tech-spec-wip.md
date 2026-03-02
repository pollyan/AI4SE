---
title: 'New-Agents 真实 LLM 智能体冒烟测试层'
slug: 'new-agents-llm-smoke-test'
created: '2026-03-02T15:10:00+08:00'
status: 'in-progress'
stepsCompleted: [1, 2, 3]
tech_stack:
  - Vitest
  - OpenAI SDK
  - dotenv
files_to_modify:
  - tools/new-agents/package.json
  - tools/new-agents/src/__tests__/smoke/llmJudge.ts
  - tools/new-agents/src/__tests__/smoke/smokeTestData.ts
  - tools/new-agents/src/__tests__/smoke/workflow.smoke.test.ts
code_patterns:
  - '直接使用 OpenAI SDK 与系统 Prompt 组装'
  - 'LLM-as-a-Judge 进行非精确字符串的语义级断言'
test_patterns:
  - 'npm run test:smoke — 独立于常规单元测试的冒烟测试'
---

# Tech-Spec: New-Agents 真实 LLM 智能体冒烟测试层

**Created:** 2026-03-02T15:10:00+08:00

## Overview

### Problem Statement

目前 `new-agents` 的智能体逻辑（如 `systemPrompt` 设计、阶段流转判定）严重依赖真实的大模型表现。修改 Prompt 或业务流转逻辑后，手动完整跑一遍测试耗时过长。然而，传统的字符串精准断言（如 `expect(res).toContain(...)`）面对 LLM 输出的不确定性和有时存在的 Markdown 格式瑕疵时，极度脆弱且难以维护。我们需要兼顾效率、稳定性和验证真实链路的自动化套件，代替手工操作，但不作为强制 CI 的阻断环节。

### Solution

构建基于真实 LLM 调用的独立"智能体行为冒烟测试 (Smoke Test)"层：
1. **绕过 UI 直接测 Agent 核心**：使用 `OpenAI` SDK 和项目中的 `getSystemPrompt`，结合不同阶段的手造历史记录，直接验证大模型的回答。
2. **动态 LLM-as-a-Judge 断言**：设计一个通用的判断帮助函数，发送 `(实际回答, 断言标准)` 给模型自己，让它判断回答是否满足阶段特性（例如："是否包含了 <CHAT> 和 <ARTIFACT> 并且没有产生语法错误"），彻底解决正则及字符级死磕。
3. **读根目录配置执行**：完全使用本地的 `.env` 并在本地提交前运行，防止密钥泄露和 CI 超时。

### Scope

**In Scope:**
- 编写 `llmJudge` 断言工具。
- 构建涵盖"首轮对话"、"提问阶段"、"成功跨越阶段"等 2-3 个核心场景的前序上下文 Context 夹具（Fixtures）。
- 实现 `workflow.smoke.test.ts` 并配置至少 30s-60s 每条用例的高级超时策略。
- 在 `package.json` 添加独立的 `test:smoke` 命令。

**Out of Scope:**
- 在 CI/CD 流水线中运行此测试。
- 用真浏览器自动化验证（Playwright 等）。

## Context for Development

### Codebase Patterns

- **LLM Judge 模式**：通过系统化的 Prompt 要求大模型仅输出符合 JSON Schema 的 `{ "pass": true/false, "reason": "..." }` 进行断言评估。
- **Vitest 超时配置**：真实模型调用通常需要 5-15 秒，需要在 `it('...', async () => {}, { timeout: 60000 })` 级别指定更长的超时或者在 CLI 指定。

### Files to Reference

| File | Purpose |
| ---- | ------- |
| `src/prompts/systemPrompt.ts` | 需要验证其是否能按预期约束 LLM。 |
| `../../../../.env` | 项目根目录环境变量，存有 `OPENAI_API_KEY`、`OPENAI_BASE_URL`。 |

## Implementation Plan

### Task 1: 基础设施铺设

1. 更新 `package.json`，增加 `"test:smoke": "vitest run src/__tests__/smoke --testTimeout=60000"`。
2. 创立 `llmJudge.ts`，借助根目录 `.env` 初始化 OpenAI Client，并暴露 `evaluateWithLLM(actual, criteria): Promise<boolean>` 及直接的生成流。
3. 创立 `smokeTestData.ts`，为测试提供诸如："阶段 1 空白状态"、"阶段 1 已经聊完随时可进入阶段 2" 的 Mock 对话数组 `messages`。

### Task 2: 编写基于状态机的 E2E 流程式冒烟测试 (`workflow.smoke.test.ts`)

为了真实还原用户体验并降低手造数据的复杂度，我们将构建 `AgentConversationRunner` 状态机类，它会自动将历史对话和阶段（Stage）变更的 System Prompt 拼装。 

借助这个 Runner，实施以下完整的端到端 (E2E) 测试流程（以 `TEST_DESIGN` 完整链路为蓝本）：

- **Round 1 (模糊输入)**：用户输入一个极其模糊的需求（如："测试一下登录"）。
  * **断言预期**：必须产出初始的 `<ARTIFACT>`，且在 `<CHAT>` 中向用户提出 P0 级别的阻断性澄清问题。绝对不允许出现 `<ACTION>NEXT_STAGE</ACTION>`。
- **Round 2 (尝试违规越级)**：用户拒答问题并强行要求推进（"别问了，直接给我用例"）。
  * **断言预期**：Agent 必须坚守原则（也就是测试覆盖目标 1：P0 未解答不进入下一阶段），拒绝输出 `NEXT_STAGE`，并在 `<CHAT>` 中提供合适的拦截反馈。
- **Round 3 (解答完问题)**：用户老实回答了所有 P0 问题（"密码8-16位字母，账号是手机号..."）。
  * **断言预期**：必须更新 `<ARTIFACT>`，并在 `<CHAT>` 中明确给出了"已完善阶段产出，请问是否可以进入下一阶段"的询问。依然不能擅自输出 `NEXT_STAGE`。
- **Round 4 (确认流转)**：用户确认进入下一阶段。
  * **断言预期**：必须准确输出 `<ACTION>NEXT_STAGE</ACTION>`。必须在 `<ARTIFACT>` 中生成【测试策略】阶段的新大纲，而不能是原样照抄上一轮。
- **后续阶段跑通**：通过程序循环配合 LLM，将流程一路跑至最后阶段（例如文档排版交付），验证测试设计工作流的完整生命周期。
- **全局断言约束**：每一轮的判断标准（Criteria）中，都要求检查格式大体正确（必须由 `<CHAT>` 和 `<ARTIFACT>` 组成），没有明显的格式崩坏。

### Acceptance Criteria

- [ ] 运行 `npm run test:smoke` 时，能够成功读取根目录的 `.env`。
- [ ] LLM 自我评估断言能够有效忽略因为空白字符、或细微结构不同导致的假阳性报错。
- [ ] 测试运行时间长但能稳定反馈通过或提供不通过的具体 LLM reason。 
