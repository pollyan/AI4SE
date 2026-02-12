---
stepsCompleted: ['step-01-init', 'step-02-discovery', 'step-03-success', 'step-04-journeys', 'step-05-domain', 'step-06-innovation', 'step-07-project-type', 'step-08-scoping', 'step-09-functional', 'step-10-nonfunctional', 'step-11-polish', 'step-12-complete']
inputDocuments:
  - docs/plans/2026-02-11-artifact-inline-diff-design.md
documentCounts:
  brief: 0
  research: 0
  brainstorming: 0
  projectDocs: 1
  projectContext: 0
workflowType: 'prd'
classification:
  projectType: web_app
  domain: scientific
  complexity: medium
  projectContext: brownfield
---

# 产品需求文档 - AI4SE

**作者:** Anhui
**日期:** 2026-02-11

## 成功标准 (Success Criteria)

### 用户成功 (User Success)

- **上下文无关审核**: 用户可以在不需要回忆以前版本或检查历史记录的情况下理解更改内容。
- **微观可见性**: 用户可以立即识别特定的单词/短语更改，而不仅仅是行级更新。
- **低认知负荷**: diff 可视化直观（红色/绿色），并且不会使阅读体验变得杂乱。

### 业务成功 (Business Success)

- **增强信任**: AI 修改的透明度建立了用户接受建议的信心。
- **加速验证**: 将用户审核 AI 生成需求的时间减少约 30%。

### 技术成功 (Technical Success)

- **零数据丢失**: 在多轮对话中准确跟踪 diff 状态。
- **瞬态正确性**: Diff 标记仅在当前审核周期持续存在，并在下次更新时自动清除。
- **性能**: 对渲染性能的影响可忽略不计。

### 可衡量的结果 (Measurable Outcomes)

- **审核速度**: 验证需求更新的时间减少。
- **拒绝率**: 用户因误解变更而拒绝有效 AI 建议的情况减少。

## 产品范围 (Product Scope)

### MVP - 最小可行产品

- **字段级 Inline Diff**: 删除使用红色删除线，插入使用绿色高亮。
- **范围覆盖**: 规则 (Rules)，特性 (Features)，假设 (Assumptions) 和范围 (Scope) 文本字段。
- **后端支持**: 在 Artifact 更新合并期间临时存储 `_prev` 值。
- **前端渲染**: 适用于所有文本字段的可重用 `DiffField` 组件。

### 增长特性 (Post-MVP)

- **Mermaid 图表 Diff**: 并排或视觉叠加显示图表 diff。
- **历史视图**: 需求演变的时间旅行调试。
- **粒度控制**: 用户能够接受/拒绝单个字段更​​改。

### 愿景 (Future)

- **智能理由**: AI 解释 *为什么* 进行了特定更改（例如，“为了一致性而调整”）。

## 用户旅程 (User Journeys)

### 旅程 1：审核 Lisa 的需求更新（核心路径）

1.  用户输入：“支持 SSO 登录”
2.  Lisa 更新结构化 artifact 并返回新版本
3.  用户在 artifact 面板中看到：规则描述显示 ~~必须登录~~ **必须通过 SSO 登录**（红删绿增）
4.  其他未更改的字段正常显示，没有任何标记
5.  用户一眼确认更改，继续对话；之前的 diff 标记自动清除

### 旅程 2：审核批量更新（多字段变更）

1.  Lisa 同时修改了 3 个特性的 `优先级` 和 2 个特性的 `描述`
2.  用户看到多个项目高亮显示（已修改），仅在更改的字段上显示红/绿 inline diff
3.  未更改的字段（例如 `名称`，`验收标准`）不显示任何视觉干扰
4.  用户快速批量确认：更改看起来正确，继续

### 旅程需求摘要

| 能力 | 来源 |
|---|---|
| `_prev` 旧值存储 | J1, J2 |
| `DiffField` 渲染组件 | J1, J2 |
| 瞬态 diff 自动清除 | J1 |
| 多字段/多项目同时 diff | J2 |
| 未更改字段零干扰 | J1, J2 |

## Web 应用特定需求 (Web App Specific Requirements)

### 项目类型概览

这是对现有基于 React 的单页应用 (SPA) 组件 (`StructuredRequirementView`) 的功能增强。

### 技术架构考量

- **组件架构**: 
  - 纯客户端渲染。
  - `DiffField` 组件应为无状态且可复用的。
  - `_prev` 数据通过 props 从父容器传递。
- **实时性**: 
  - Diff 功能不需要 WebSocket。
  - 更新由 AI 智能体的标准 HTTP 响应触发。

### 浏览器支持矩阵

- **目标**: 现代浏览器 (Chrome, Edge, Firefox, Safari - 最近 2 个版本)。
- **遗留支持**: 不需要。

### 可访问性与设计

- **视觉编码**: 
  - MVP 依赖颜色 (红/绿) + 文本装饰 (删除线)。
  - MVP 不需要额外的图标。
- **响应式设计**:
  - 必须在标准桌面分辨率下保持布局完整性。
  - Inline diff 应优雅换行，不破坏网格布局。

### 性能目标

- **渲染性能**: 
  - 对于少于 100 个条目的 artifact，实现即时渲染。
  - MVP 不需要虚拟化 (假设典型的 artifact 大小 < 50 个条目)。

## 项目范围界定与分阶段开发 (Project Scoping & Phased Development)

### MVP 策略与理念

**MVP 方法:** 最小可行体验 (MVE) - 专注于增加变更感知，而不破坏现有的阅读流。
**资源需求:** 1 名全栈工程师 (后端 + 前端)。

### MVP 功能集 (第一阶段)

**支持的核心用户旅程:**
- 审核单个需求更新 (旅程 1)
- 审核批量更新 (旅程 2)

**必须具备的能力:**
- 列表合并期间的后端 `_prev` 跟踪
- 前端 `DiffField` 组件
- 红/绿 视觉编码

### Post-MVP 功能

**第二阶段 (增长):**
- Mermaid 图表可视化 Diff
- 历史时间旅行
- 针对大量文本更改的 "块级 Diff (Block Diff)" 回退

**第三阶段 (扩展):**
- AI 生成变更理由
- 细粒度的接受/拒绝控制

### 风险缓解策略

**技术风险:** 
- **复杂的合并逻辑**: 针对 `_merge_lists` 的单元测试，覆盖嵌套/部分更新。

**市场风险 (可用性):** 
- **视觉杂乱**: 如果文本更改超过 50%，inline diff 可能难以阅读。
- **缓解措施**: 监控反馈；未来考虑增加 "查看原始内容" 切换。

**资源风险:** 
- 低风险，现有组件的高复用性。

## 功能需求 (Functional Requirements)

### 变更追踪能力 (Diff Tracking)

- **FR1**: [System] 能够识别并标记产出物列表中新增 (`added`)、修改 (`modified`) 和未变化 (`unchanged`) 的条目。
- **FR2**: [System] 能够在修改的条目中，精准识别出值发生变化的文本字段（如 `desc`, `priority`, `content`）。
- **FR3**: [System] 能够将变更字段的 **旧值 (Old Value)** 临时存储在产出物数据结构中。
- **FR4**: [System] 能够在下一轮对话更新时，自动清除上一轮产生的 diff 标记（瞬态特性）。

### 变更可视化能力 (Diff Visualization)

- **FR5**: [User] 能够以 **红色删除线** 样式看到被删除或修改前的文本内容。
- **FR6**: [User] 能够以 **绿色背景** 样式看到新增或修改后的文本内容。
- **FR7**: [User] 能够在同一个字段内同时看到旧值和新值（Inline Diff 模式）。
- **FR8**: [System] 能够确保未变化的字段保持原有样式，无任何干扰标记。

### 结构化覆盖能力 (Structural Coverage)

- **FR9**: [System] 能够支持对 `Rule` 类型数据的 `desc`, `source` 等字段进行 diff 展示。
- **FR10**: [System] 能够支持对 `Feature` 类型数据的 `name`, `desc`, `priority` 等字段进行 diff 展示。
- **FR11**: [System] 能够支持对 `Assumption` 和 `Scope` 类型数据的文本字段进行 diff 展示。
- **FR12**: [System] 能够忽略不支持 diff 的字段（如 Mermaid 图表），均按“当前值”渲染，不报错。

### 交互与状态能力 (Interaction)

- **FR13**: [User] 在进行连续对话时，每次收到的产出物总是相对于上一版的增量 diff。
- **FR14**: [System] 能够处理多条目同时变更的场景，并正确渲染每一条的 diff。

## 非功能需求 (Non-Functional Requirements)

### 性能 (Performance)

- **NFR1 (渲染延迟)**: 对于少于 100 个条目的列表，Diff 渲染带来的额外延迟应 < 100ms（人眼无感）。
- **NFR2 (传输开销)**: 包含 `_prev` 的数据包大小增加不超过原始数据的 50%（基于仅差异字段存储的假设）。

### 可维护性 (Maintainability)

- **NFR3 (组件复用)**: `DiffField` 组件必须是无状态的纯展示组件，不包含任何业务逻辑，以便在不同类型的 Artifact 中复用。
- **NFR4 (数据隔离)**: `_prev` 字段不应被持久化存储到数据库，仅存在于前端渲染周期的内存/响应中（由后端逻辑保证）。

### 兼容性 (Compatibility)

- **NFR5 (浏览器)**: 在 Chrome, Edge, Safari, Firefox 的最近两个主版本中渲染一致。
- **NFR6 (降级)**: 如果 `_prev` 数据缺失或格式错误，前端应自动降级为只显示当前值，不应崩溃（白屏）。



