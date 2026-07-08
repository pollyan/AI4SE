---
stepsCompleted: [1, 2, 3, 4]
inputDocuments: []
session_topic: 'Lisa 智能体新工作流痛点挖掘'
session_goals: '为一线测试人员和 QA Lead 挖掘全链路测试痛点，设计可落地的专家指导型工作流'
selected_approach: 'ai-recommended'
techniques_used:
  - 'Reverse Brainstorming (逆向风暴法)'
  - 'Role Playing (角色代入法)'
  - 'Constraint Mapping (约束映射法)'
ideas_generated:
  - 'INCIDENT_REVIEW: 线上故障复盘引导'
  - 'BUG_TRIAGE: 疑难 Bug 排查引导'
  - 'CHANGE_IMPACT: 变更影响面分析'
  - 'TEST_REPORT: 测试总结报告生成 (Tier 2)'
  - 'BUG_REPORT: 缺陷报告重组 (Tier 2)'
  - 'SCOPE_CUTDOWN: 测试范围裁剪 (Tier 2)'
context_file: ''
---

# Brainstorming Session Results

**Facilitator:** Anhui
**Date:** 2026-03-04

---

## Session Overview

**Topic:** Lisa 智能体新工作流痛点挖掘
**Goals:** 为一线测试人员和 QA Lead 挖掘全链路测试痛点，设计可落地的专家指导型工作流

### Context Guidance

_本次头脑风暴基于 Lisa 智能体现有架构（纯 LLM 对话 + Artifact 产出物模式），聚焦测试全生命周期（测前/测中/测后）的痛点挖掘。_

### Session Setup

- **目标受众**: 一线测试人员 + 测试团队负责人 (QA Lead)
- **技术约束**: 纯对话 + Artifact 模式，不调用外部系统
- **痛点范围**: 测试全生命周期
- **优先级导向**: 以用户最痛为主

---

## Technique Selection

**Approach:** AI-Recommended Techniques
**Analysis Context:** 测试痛点挖掘 with focus on 全链路覆盖 + 最高痛感优先

**Recommended Techniques:**

- **Reverse Brainstorming (逆向风暴法):** 通过"如何让 QA 崩溃"的反向视角暴露深层痛点
- **Role Playing (角色代入法):** 从一线 QA 和 QA Lead 两个视角排序痛点优先级
- **Constraint Mapping (约束映射法):** 用技术约束筛选哪些痛点能在纯对话模式中"降维打击"

**AI Rationale:** 传统提问"测试有什么痛点"只能得到表层答案，逆向思维能打破盲区；双角色代入确保兼顾一线和管理层；约束映射确保方案可落地。

---

## Technique Execution

### Phase 1: Reverse Brainstorming — "如何让一线 QA 彻底崩溃？"

共产出 **24 个痛点场景**：

#### 测试前（计划与准备）— 3 个

1. 给他一份写了 200 页但没有验收标准的 PRD
2. 每次需求变更都不通知测试
3. 给他一个涉及 15 个微服务的全新系统，没有架构图

#### 测试中（执行与调试）— 7 个

4. 手动造 50 组边界值测试数据，每组 30 个字段
5. 只在特定数据组合下才能复现的 Bug，报错信息是"Unknown Error"
6. 测试环境每天宕机两次
7. UI 自动化脚本跑失败了，截图显示页面看起来完全正常
8. 面对一份 80 个接口的 Swagger 文档不知道从何测起
9. 数据库验证时不会写 SQL
10. 并发/性能场景完全不知道怎么下手

#### 测试后（报告与复盘）— 3 个

11. 手动从 5 个系统拼凑数据写测试报告
12. 质量度量和效能汇报说不清
13. 线上故障复盘变成甩锅大会

#### 跨团队协作 — 4 个

14. 变更影响分析全靠人肉猜测
15. 测试排期永远被压缩，"砍哪些用例"没有方法论
16. 技术方案评审时测试人员像个透明人
17. 偶现 Bug 复现不了但不敢关

#### 专业成长 — 3 个

18. Bug 报告总是被开发驳回，信息不够充分
19. 想从手工测试转型但不知道该学什么
20. 探索性测试不知道怎么做才不是"随便点点"

_(注: 编号在会话中为 1-24，此处按类别重新归类)_

### Phase 2: Role Playing — 双视角痛点排序

#### 一线 QA 视角 Top 5

| 排序 | 痛点 | 痛苦指数 |
|------|------|---------|
| 🥇 | 疑难 Bug 排查毫无头绪 | ⭐⭐⭐⭐⭐ |
| 🥈 | 变更影响分析全靠猜 | ⭐⭐⭐⭐⭐ |
| 🥉 | Bug 报告总是被驳回 | ⭐⭐⭐⭐ |
| 4 | 偶现 Bug 不知道怎么追踪 | ⭐⭐⭐⭐ |
| 5 | 测试数据设计耗时且不系统 | ⭐⭐⭐⭐ |

#### QA Lead 视角 Top 5

| 排序 | 痛点 | 痛苦指数 |
|------|------|---------|
| 🥇 | 测试总结报告不知道怎么写 | ⭐⭐⭐⭐⭐ |
| 🥈 | 被压缩排期时不知道该砍什么 | ⭐⭐⭐⭐⭐ |
| 🥉 | 线上故障复盘不系统 | ⭐⭐⭐⭐⭐ |
| 4 | 质量度量和效能汇报说不清 | ⭐⭐⭐⭐ |
| 5 | 测试覆盖率和版本风险说不清 | ⭐⭐⭐⭐ |

### Phase 3: Constraint Mapping — 可行性筛选

筛选维度: 需不需要外部系统？核心瓶颈是不是思维/方法论？Artifact 产出价值如何？

| 痛点 | 需要外部系统？ | 核心是方法论？ | Artifact 价值 | 可行性 |
|------|--------------|-------------|-------------|--------|
| 疑难 Bug 排查 | ❌ | ✅ | 🔥 排障决策树 | ✅ 高 |
| 变更影响分析 | ⚠️ 用户可粘贴 diff | ✅ | 🔥 影响拓扑图 | ✅ 中高 |
| Bug 报告重组 | ❌ | ✅ | 🔥 专业缺陷报告 | ✅ 极高 |
| 测试总结报告 | ⚠️ 需数据 | ✅ | 🔥 报告模板 | ✅ 高 |
| 排期裁剪 | ❌ | ✅ | 🔥 风险矩阵 | ✅ 极高 |
| 故障复盘 | ❌ | ✅ | 🔥 复盘报告 | ✅ 极高 |

---

## Selected Ideas

### ✅ Tier 1: 用户选定的 3 个工作流

#### 1. 🥇 线上故障复盘引导 (`INCIDENT_REVIEW`)

- **用户画像**: QA Lead / 一线 QA 需要做线上事故复盘
- **阶段设计**: 事件还原 (TIMELINE) → 根因分析 (ROOT_CAUSE) → 改进报告 (IMPROVEMENT)
- **核心亮点**: Mermaid timeline 时间线 + mindmap 鱼骨图 + 5-Why 分析链 + 改进行动清单
- **震撼点**: 把"甩锅大会"变成专业的质量改进闭环

#### 2. 🥈 疑难 Bug 排查引导 (`BUG_TRIAGE`)

- **用户画像**: 一线 QA 面对一个诡异 Bug，不知道从哪下手
- **阶段设计**: 现象采集 (COLLECT) → 根因推理 (HYPOTHESIZE) → 排查行动清单 (ACTION_PLAN)
- **核心亮点**: Mermaid flowchart 排查决策树 + 假设概率排序 + 分步排查方案
- **震撼点**: 把"两天盲猜"变成"30 分钟定向排查"

#### 3. 🥉 变更影响面分析 (`CHANGE_IMPACT`)

- **用户画像**: 一线 QA / QA Lead 需要分析变更影响范围
- **阶段设计**: 变更采集 (COLLECT_CHANGES) → 影响面推导 (IMPACT_ANALYSIS) → 回归策略 (REGRESSION_PLAN)
- **核心亮点**: Mermaid flowchart 影响拓扑图 + quadrantChart 风险热力图 + 四级回归清单
- **震撼点**: 把"拍脑袋回归"变成"精准回归"

### 📦 Tier 2: 备选工作流（未来迭代）

- 测试总结报告生成 (`TEST_REPORT`) — 依赖大量数据粘贴，UX 门槛较高
- 缺陷报告重组 (`BUG_REPORT`) — 场景较轻量，可能不需要完整工作流
- 测试范围裁剪 (`SCOPE_CUTDOWN`) — 与 TEST_DESIGN STRATEGY 阶段有重叠

---

## Key Decisions Made

| 决策点 | 确认结果 | 阶段 |
|--------|---------|------|
| Mermaid 兼容性 | v11.12.3 支持 timeline/mindmap/pie/quadrantChart | 技术调研 |
| 产出物继承 | 方案 A：最后阶段整合全部内容 | Stage 设计 |
| 对话引导风格 | 风格 B：渐进式对话引导 | Stage 设计 |
| 鱼骨图分类 | 固定六大类（人员/流程/技术/环境/工具/管理） | Stage 设计 |

---

## Open Items & Enhancement Requirements

> 以下是评审阶段提出的关键增强要求，待下一步需求细化时深入设计：

1. **融入专业敏捷教练技巧** — 引入经典复盘方法论，对话中展现方法论来源，提升专业度感知
2. **阶段门禁标准 (Stage Gate)** — 每个 Stage 定义 Must-Have 信息清单，未满足时不放行
3. **专业度感知设计** — Lisa 在每个阶段开头介绍即将使用的方法论

---

## Next Actions

| 序号 | 行动 | 优先级 |
|------|------|--------|
| 1 | 细化 INCIDENT_REVIEW 需求：融入敏捷教练技巧 + 门禁标准 | 🔴 Next |
| 2 | 编写 INCIDENT_REVIEW Implementation Plan | 🟡 |
| 3 | 编码实施 INCIDENT_REVIEW | 🟡 |
| 4 | 细化 BUG_TRIAGE 需求和设计 | 🔵 Later |
| 5 | 细化 CHANGE_IMPACT 需求和设计 | 🔵 Later |

---

## Related Artifacts

- [lisa_new_workflows_design.md](file:///Users/anhui/.gemini/antigravity/brain/327acae5-1ca7-4946-9778-0948ebde927d/lisa_new_workflows_design.md) — 三个工作流初版设计方案
- [incident_review_stage_design.md](file:///Users/anhui/.gemini/antigravity/brain/327acae5-1ca7-4946-9778-0948ebde927d/incident_review_stage_design.md) — INCIDENT_REVIEW System Prompt 草稿
