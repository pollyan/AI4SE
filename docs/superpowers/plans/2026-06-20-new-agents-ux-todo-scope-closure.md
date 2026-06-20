# New Agents UX Todo Scope Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 收敛 `docs/todos/new-agents-ux-professionalization.md` 的当前活动范围，让后续目标模式不会被历史“剩余”记录误导为薄切片实现任务。

**Architecture:** 本轮是文档型工程信任闭环，不修改 New Agents 运行时代码。通过在 todo 顶部增加当前状态索引、暂不推进项和后续 CGA 选题规则，保留历史进展记录，同时给后续目标模式一个稳定入口。

**Tech Stack:** Markdown 文档、ripgrep 文档验收、Git diff whitespace check。

---

### Task 1: 文档活动状态索引

**Files:**
- Modify: `docs/todos/new-agents-ux-professionalization.md`
- Create: `docs/superpowers/specs/2026-06-20-new-agents-ux-todo-scope-closure-design.md`
- Create: `docs/superpowers/plans/2026-06-20-new-agents-ux-todo-scope-closure.md`

- [ ] **Step 1: Run RED documentation check**

Run:

```bash
rg -n "当前活动状态|当前明确不推进|后续 CGA 选题规则|历史进展记录说明" docs/todos/new-agents-ux-professionalization.md
```

Expected: no matches, exit code 1. This proves the todo currently lacks a stable activity-state index.

- [ ] **Step 2: Add current activity status section**

Insert after `## 使用规则` a section named `## 当前活动状态（2026-06-20）` with a table covering:

```markdown
| 能力包 | 当前状态 | 证据 | 后续处理 |
| --- | --- | --- | --- |
| 工作区顶部操作收敛 | 阶段完成 | 第一块和第二块 CGA 已完成 Header 与 Artifact 工具条收敛 | 仅在出现新的用户混乱证据时重启 |
| 结构化输出失败与重试体验 | 阶段完成 | 失败恢复卡片、连续失败补充信息、可视化诊断定位已完成 | 仅在出现新的失败恢复断点时重启 |
| 全流程专业产出物与可视化增强 | 阶段完成 | 首阶段、后续关键阶段、E2E 和 LLM judge 证据已补齐 | 高保真导出不再作为当前活动项 |
| Mermaid 可靠性与结构化可视化扩展 | 阶段完成 | 结构化可视化类型、生产渲染缓存、策略 Mermaid sanitizer 已完成 | 仅按生产事故或新稳定性证据重启 |
| 左侧对话自然表达与重点可扫描 | 阶段完成 | 自然顾问式对话契约已完成 | 不引入固定 chat schema |
| 模型配置与供应商治理融入体验 | 阶段完成 | 供应商失败卡片、运行统计、告警动作、首次配置自检已完成 | 仅按新的供应商治理主路径缺口重启 |
| Artifact 协作体验深化 | 当前阶段完成 | 受控编辑、保存冲突、审阅面板、批注锚点、块级处理、安全边界已完成 | 仅在出现完整且可证明安全的用户冲突场景时重启 |
```

- [ ] **Step 3: Add non-goals and CGA restart rules**

Add sections:

```markdown
## 当前明确不推进

- 高保真 PDF 图片级导出继续深化。
- 恢复中心。
- 分享/权限。
- 多人实时协同。
- 与 intent-tester 自动打通。

## 后续 CGA 选题规则

- 历史进展记录中的“剩余”是当时的过程记录，不自动等同于当前活动待办。
- 后续目标模式必须以上方当前活动状态、用户最新决策和当前代码证据为准。
- 不能从单个旧“剩余”、单个导出格式、单个 Mermaid 语法变体或单个三方 merge 算法分支直接进入 milestone。
- 只有当新证据能聚合成完整用户功能厚切片，或独立工程信任闭环时，才进入 spec、plan 和 TDD。
```

- [ ] **Step 4: Add history note before priority sections**

Insert a short note before `## P0 高优先级`:

```markdown
## 历史进展记录说明

以下 P0/P1/P2 条目保留完整过程记录。较早记录里的“剩余”可能已被后续 CGA、产品决策或当前活动状态覆盖；后续选题以本文件顶部的当前活动状态为准。
```

- [ ] **Step 5: Run GREEN checks**

Run:

```bash
rg -n "当前活动状态|当前明确不推进|后续 CGA 选题规则|历史进展记录说明" docs/todos/new-agents-ux-professionalization.md
```

Expected: all four section names are present.

Run:

```bash
rg -n "高保真|恢复中心|分享/权限|intent-tester|更复杂三方 merge" docs/todos/new-agents-ux-professionalization.md
```

Expected: output includes the current non-goal and restart-rule language.

- [ ] **Step 6: Run quality checks**

Run:

```bash
rg -n "T[B]D|implement[ ]later|填[入]|稍后[实]现" docs/todos/new-agents-ux-professionalization.md docs/superpowers/specs/2026-06-20-new-agents-ux-todo-scope-closure-design.md docs/superpowers/plans/2026-06-20-new-agents-ux-todo-scope-closure.md
git diff --check
```

Expected: placeholder scan has no matches; diff check exits 0.

- [ ] **Step 7: Commit**

Run:

```bash
git add docs/todos/new-agents-ux-professionalization.md docs/superpowers/specs/2026-06-20-new-agents-ux-todo-scope-closure-design.md docs/superpowers/plans/2026-06-20-new-agents-ux-todo-scope-closure.md
git commit -m "docs(new-agents): 收敛 UX todo 活动范围"
```

Expected: one focused documentation commit.
