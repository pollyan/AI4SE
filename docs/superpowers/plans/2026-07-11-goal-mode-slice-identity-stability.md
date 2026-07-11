# Goal Mode 厚切片身份稳定性 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让已经确认且仍有效的厚切片在 Goal Mode 全流程中保持身份、顺序、验收与交付边界稳定，禁止用 A/B、phase、batch 等内部标签伪装拆薄。

**Architecture:** 在唯一规则入口 `goal-mode-playbook.md` 增加厚切片身份基线、执行不变量、合法改界路线和状态转换检查；当前 QS-03 计划只保留内部实现步骤（非切片）语义。QS-01 至 QS-08 的业务边界和执行顺序不变。

**Tech Stack:** Markdown、shell 文档一致性检查、Git diff。

## Global Constraints

- 本计划内所有步骤都是同一 Playbook 治理修复的内部文档步骤，不是子切片或独立交付。
- 不改变 QS-01 至 QS-08 的 ID、名称、范围和顺序。
- 不触碰当前 QS-03 业务代码和测试的未提交改动。
- 只形成一个覆盖完整治理修复的聚焦 commit；不按内部步骤提交。

---

### 内部实现步骤 1（非切片）：补强唯一 Playbook 规则入口

**Files:**
- Modify: `docs/strategy/goal-mode-playbook.md`

**Interfaces:**
- Consumes: 第 3.3 节七项厚切片门禁、第 2 节状态机、第 6.2 节 commit 规则。
- Produces: 厚切片身份基线、内部步骤禁用语义、合法改界路线和状态转换稳定性检查。

- [x] 在第 3 节增加“厚切片身份稳定性门禁”，明确身份基线和顺序基线。
- [x] 明确禁止 A/B/C、小数编号、phase、batch、wave、checkpoint、task 等内部标签成为切片、进度、验收、commit、push 或交付单位。
- [x] 明确真正改界只能回到 `ASSESS`，生成具备七项门禁的同级厚切片并记录替代关系。
- [x] 把稳定性检查接入 `MILESTONE`、`PLAN`、`DELIVER` 与进度说明的离开门禁。

### 内部实现步骤 2（非切片）：校准当前 QS-03 计划

**Files:**
- Modify: `docs/superpowers/specs/2026-07-11-qs03-intent-durable-execution-design.md`
- Modify: `docs/superpowers/plans/2026-07-11-qs03-intent-durable-execution.md`

**Interfaces:**
- Consumes: 新的厚切片身份稳定性门禁。
- Produces: 只有一个 QS-03 身份和交付边界的 implementation plan。

- [x] 把实施标题改为“内部实现步骤 N（非切片）”，把最终交付明确为 QS-03 唯一整片交付边界。
- [x] 在 QS-03 中文 spec 固定“厚切片身份基线”，让 plan 链接 spec 与 owning todo 的唯一基线位置。
- [x] 确认不存在 `4A/4B/4C`、`QS-03A/QS-03B` 或内部独立提交指令。
- [x] 保留完整 QS-03 的单一验收、复审、commit 与 push 边界。

### 内部实现步骤 3（非切片）：一致性验证与单一交付

**Files:**
- Verify: `docs/strategy/goal-mode-playbook.md`
- Verify: `docs/superpowers/specs/2026-07-11-goal-mode-slice-identity-stability-design.md`
- Verify: `docs/superpowers/plans/2026-07-11-goal-mode-slice-identity-stability.md`
- Verify: `docs/superpowers/plans/2026-07-11-qs03-intent-durable-execution.md`

**Interfaces:**
- Consumes: 完整文档 diff。
- Produces: 可审计的一致性证据和一个治理修复 commit。

- [x] 运行关键词检查，确认 Playbook 包含身份基线、伪装子切片禁令、合法改界路线和状态转换检查。
- [x] 运行 QS-03 计划扫描，确认无 A/B 子切片，且内部步骤均标记“非切片”。
- [x] 运行 `git diff --check`；纯文档变更不运行代码测试并记录原因。
- [x] 精确暂存本治理修复的文档并复核 staged ownership；随后按本计划的单一交付边界形成聚焦 commit。
