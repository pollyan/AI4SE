---
stepsCompleted: ['step-01-validate-prerequisites', 'step-02-design-epics', 'step-03-create-stories', 'step-04-final-validation']
inputDocuments: ['_bmad-output/planning-artifacts/prd.md', '_bmad-output/planning-artifacts/architecture.md']
status: 'complete'
completedAt: '2026-02-11'
---

# AI4SE - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for AI4SE, decomposing the requirements from the PRD, UX Design if it exists, and Architecture requirements into implementable stories.

## Requirements Inventory

### Functional Requirements

- FR1: [System] 能够识别并标记产出物列表中新增 (`added`)、修改 (`modified`) 和未变化 (`unchanged`) 的条目。
- FR2: [System] 能够在修改的条目中，精准识别出值发生变化的文本字段（如 `desc`, `priority`, `content`）。
- FR3: [System] 能够将变更字段的 **旧值 (Old Value)** 临时存储在产出物数据结构中。
- FR4: [System] 能够在下一轮对话更新时，自动清除上一轮产生的 diff 标记（瞬态特性）。
- FR5: [User] 能够以 **红色删除线** 样式看到被删除或修改前的文本内容。
- FR6: [User] 能够以 **绿色背景** 样式看到新增或修改后的文本内容。
- FR7: [User] 能够在同一个字段内同时看到旧值和新值（Inline Diff 模式）。
- FR8: [System] 能够确保未变化的字段保持原有样式，无任何干扰标记。
- FR9: [System] 能够支持对 `Rule` 类型数据的 `desc`, `source` 等字段进行 diff 展示。
- FR10: [System] 能够支持对 `Feature` 类型数据的 `name`, `desc`, `priority` 等字段进行 diff 展示。
- FR11: [System] 能够支持对 `Assumption` 和 `Scope` 类型数据的文本字段进行 diff 展示。
- FR12: [System] 能够忽略不支持 diff 的字段（如 Mermaid 图表），均按“当前值”渲染，不报错。
- FR13: [User] 在进行连续对话时，每次收到的产出物总是相对于上一版的增量 diff。
- FR14: [System] 能够处理多条目同时变更的场景，并正确渲染每一条的 diff。

### NonFunctional Requirements

- NFR1 (Rendering Latency): 对于少于 100 个条目的列表，Diff 渲染带来的额外延迟应 < 100ms（人眼无感）。
- NFR2 (Payload Overhead): 包含 `_prev` 的数据包大小增加不超过原始数据的 50%（基于仅差异字段存储的假设）。
- NFR3 (Component Reusability): `DiffField` 组件必须是无状态的纯展示组件，不包含任何业务逻辑，以便在不同类型的 Artifact 中复用。
- NFR4 (Data Isolation): `_prev` 字段不应被持久化存储到数据库，仅存在于前端渲染周期的内存/响应中（由后端逻辑保证）。
- NFR5 (Browser Compatibility): 在 Chrome, Edge, Safari, Firefox 的最近两个主版本中渲染一致。
- NFR6 (Graceful Degradation): 如果 `_prev` 数据缺失或格式错误，前端应自动降级为只显示当前值，不应崩溃（白屏）。

### Additional Requirements

- **Brownfield Integration**: Must integrate into existing `StructuredRequirementView.tsx` and `artifact_patch.py`.
- **Dependencies**: Install `fast-diff` for frontend diff calculation.
- **Naming Convention**: Strictly use `_prev` for old values in backend and `oldValue` props in frontend.
- **CSS Strategy**: Use global utility classes `.diff-inserted` and `.diff-deleted`.
- **Error Handling**: Frontend `DiffField` must trap errors from `fast-diff` and fallback to displaying current value.
- **Testing**: Backend tests in `test_artifact_patch.py`, Frontend tests in `DiffField.test.tsx`.
- **Markdown Handling**: Treat Markdown fields as plain strings for diffing (no syntax tree diff).

### FR Coverage Map

FR1 (Diff Tracking): Epic 1
FR2 (Field Identification): Epic 1
FR3 (Old Value Storage): Epic 1
FR4 (Transient Diff): Epic 1 (Story 1.3)
FR5 (Deleted Style): Epic 1
FR6 (Inserted Style): Epic 1
FR7 (Inline Diff): Epic 1 (Story 1.1)
FR8 (Unchanged Style): Epic 1
FR9 (Rule Structure): Epic 1 (Story 1.2)
FR10 (Feature Structure): Epic 1 (Story 1.2)
FR11 (Assumption/Scope Structure): Epic 1 (Story 1.2)
FR12 (Ignore Unsupported): Epic 1 (Story 1.2)
FR13 (Incremental Diff): Epic 1
FR14 (Batch Diff): Epic 1

NFRs: Performance and Compatibility addressed in Story 1.1 (Fast-Diff integration).

## Epic List

### Epic 1: Complete Inline Diff Implementation (End-to-End)
Goal: Implement the complete field-level inline diff capability, starting with a vertical slice on a single field (`desc`) using `fast-diff` (Story 1.1), then expanding coverage to all artifact structures (Story 1.2), and finally ensuring proper transient state management (Story 1.3).
**FRs covered:** FR1-FR14 (All Functional Requirements)

<!-- Repeat for each epic in epics_list (N = 1, 2, 3...) -->

## Epic 1: Complete Inline Diff Implementation (End-to-End)

Goal: Implement the complete field-level inline diff capability, starting with a vertical slice on a single field (`desc`) using `fast-diff` (Story 1.1), then expanding coverage to all artifact structures (Story 1.2), and finally ensuring proper transient state management (Story 1.3).

### Story 1.1: End-to-End Inline Diff Pilot (Single Field)

As a Product Owner reviewing AI updates,
I want to see character-level inline diffs (red strikethrough/green highlight) for the `desc` field of Rules,
So that I can precisely identify minor wording changes without reading the old and new text separately.

**Acceptance Criteria:**

**Given** an existing Rule with `desc: "User must login."`
**When** the AI updates the rule to `desc: "User must login via SSO."`
**Then** the backend response includes `_prev: { desc: "User must login." }` for that rule
**And** the Frontend `StructuredRequirementView` renders the `desc` field as: `User must login <ins>via SSO</ins>.` (using `fast-diff` logic)
**And** unchanged parts of the text have no styling
**And** `fast-diff` is installed as a project dependency

### Story 1.2: Expand Diff Coverage to All Artifact Types

As a Product Owner,
I want inline diff support for all text fields across Features, Assumptions, and Scoping sections,
So that I have a consistent review experience regardless of which part of the document changed.

**Acceptance Criteria:**

**Given** a complex artifact containing Features (`name`, `priority`), Assumptions (`content`), and Scope (`in_scope`, `out_scope`)
**When** the AI updates multiple fields across these types simultaneously
**Then** the backend correctly generates `_prev` values for all modified text fields within nested structures
**And** the Frontend renders `DiffField` components for all corresponding UI elements
**And** unsupported fields (like Mermaid diagrams) fallback to showing only the new value without crashing
**And** `added` items (newly created entries) are highlighted with a green background (`.diff-inserted` block style)

### Story 1.3: Transient State Management & Cleanup

As a User,
I want diff markings to disappear after I proceed to the next round of conversation,
So that the interface remains clean and I don't see stale changes from previous turns.

**Acceptance Criteria:**

**Given** a rule with visible inline diffs from Turn 1
**When** I send a new message and the AI returns a response where that rule is *unchanged* from Turn 1
**Then** the backend does NOT include a `_prev` field for that rule
**And** the Frontend updates to show only the current text with no red/green markings
**And** if a field was previously `added` (green block), it reverts to normal styling in the next turn if unchanged

