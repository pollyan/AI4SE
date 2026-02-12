---
stepsCompleted: ['step-01-init', 'step-02-context', 'step-03-starter', 'step-04-decisions', 'step-05-patterns', 'step-06-structure', 'step-07-validation', 'step-08-complete']
inputDocuments: ['_bmad-output/planning-artifacts/prd.md']
workflowType: 'architecture'
lastStep: 8
status: 'complete'
completedAt: '2026-02-11'
project_name: 'AI4SE'
user_name: 'Anhui'
date: '2026-02-11'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## 项目上下文分析 (Project Context Analysis)

### 需求概览 (Requirements Overview)

**功能需求 (Functional Requirements):**
- **核心能力**: 在后端合并过程中追踪旧值 (`_prev`) 并暴露给前端。
- **可视化**: 在文本字段内渲染删除（红色删除线）和插入（绿色高亮）。
- **范围**: 支持 Rules, Features, Assumptions, Scope 中的嵌套字段。
- **交互**: 瞬态 Diff，下一次更新时自动清除。
- **总计 FRs**: 14 条明确的功能需求，定义了“Diff 契约”。

**非功能需求 (Non-Functional Requirements):**
- **性能**: 对于典型产出物（<100条目），渲染延迟不可感知 (<100ms)。
- **架构**: `DiffField` 必须是无状态且可复用的。`_prev` 数据是临时的（不持久化）。
- **兼容性**: 现代浏览器，若 Diff 数据格式错误需优雅降级。

**规模与复杂度 (Scale & Complexity):**
- **主要领域**: Web 应用 (React SPA) + Python 后端。
- **复杂度**: 低-中 (功能增强)。
- **预计架构组件**:
  - 后端: 1 个核心逻辑模块 (`artifact_patch.py`)。
  - 前端: 1 个新 UI 组件 (`DiffField`) + 1 个父容器更新 (`StructuredRequirementView`)。

### 技术约束与依赖 (Technical Constraints & Dependencies)

- **现有系统约束 (Brownfield)**: 必须集成到现有的组件结构 (`StructuredRequirementView`) 中。
- **数据传输**: `_prev` 数据必须通过标准的 HTTP JSON 响应传输。
- **无状态性**: 不为 Diff 历史创建新的数据库表；状态仅在响应中存在。

### 识别的横切关注点 (Cross-Cutting Concerns)

- **数据完整性**: 确保 `_merge_lists` 逻辑在处理嵌套更新时不会丢失数据。
- **UI 一致性**: Diff 样式绝不能破坏现有的网格布局或可读性。
### 识别的横切关注点 (Cross-Cutting Concerns)

- **数据完整性**: 确保 `_merge_lists` 逻辑在处理嵌套更新时不会丢失数据。
- **UI 一致性**: Diff 样式绝不能破坏现有的网格布局或可读性。
- **错误处理**: 前端必须健壮地处理缺失或格式错误的 `_prev` 结构。

## 基础架构评估与选型 (Starter Template / Foundation Evaluation)

### 主要技术栈确认 (Primary Technology Domain)

- **基础**: **Brownfield (现有项目)** Web 应用 (React + Python)。
- **目标**: 增量开发功能增强，无需全新脚手架。
- **策略**: 复用现有项目的基础设施 (Webpack/Vite, CSS, API 层)。

### 关键依赖库选择 (Key Dependencies)

**Diff 算法库决策:**

为了实现 **User Success** 中的“微观可见性” (FR2/FR7)，前端必须计算 `current` 与 `old_value` 之间的字符/单词级差异。

- **推荐**: `diff-match-patch` (Google) 或 `fast-diff`。
- **MVP 建议**: 优先使用 `fast-diff` (轻量, 高性能)，若无法满足复杂需求则回退到 `diff-match-patch`。

**CSS 样式方案:**

- **决策**: 严格遵循项目现有的 CSS 规范。如果是 Tailwind 则用 Tailwind；如果是 CSS Modules 则用 CSS Modules。不引入新的样式预处理器。

### 数据流与状态管理

- **状态**: 使用局部组件状态 (`React.useState`) 或直接由 Props 驱动 (`Pure Component`)。
- **通信**: 沿用现有的 HTTP API 响应结构，通过 payload 携带 `_prev` 数据。不需要引入新的状态管理库 (如 Redux)。

### 架构决定摘要

- **不创建新项目 repo**: 代码直接合并入现有仓库。
- **引入依赖**: 仅引入必要的 Diff 计算库 (`npm install fast-diff`)。
- **零配置变更**: 不修改现有的构建流程或 CI/CD 管道。

## 核心架构决策 (Core Architectural Decisions)

### 决策优先级分析 (Decision Priority Analysis)

**关键决策 (阻碍实现):**
- **D1. 数据结构**: 采用 **扁平化 Diff Map** (`_prev: { field: old_val }`) 存储旧值。
- **D2. API 注入点**: 后端 `artifact_patch.py` 的列表合并逻辑 (`_merge_lists`) 负责生成 `_prev`。
- **D3. 前端 Diff 策略**: 使用 `fast-diff` 库计算并渲染字符级差异。

**重要决策 (塑造架构):**
- **D4. Markdown 处理**: MVP 阶段将 Markdown 视为 **纯字符串** 进行 Diff (允许 Markdown 符号被划掉/高亮)，不进行语法树 Diff。

**推迟决策 (Post-MVP):**
- **D5. Block Diff**: 大段文本变更的回退机制暂不实现。
- **D6. 历史存储**: `_prev` 不持久化到数据库。

### 数据架构 (Data Architecture)

- **Schema**:
  ```json
  {
    "id": "item-123",
    "content": "New content",
    "_diff": "modified",
    "_prev": {
      "content": "Old content"
    }
  }
  ```
- **Rationale**: 扁平化 Map 简单且足以覆盖 MVP 需求，避免过度复杂化 Schema。
- **Impact**: 后端 `_merge_lists` 函数必须正确生成此结构。

### API 与通信模式 (API & Communication Patterns)

- **Protocol**: 标准 HTTP JSON Response。
- **Payload**: 在现有的 Artifact List 响应中直接嵌入 `_prev` 字段。
- **Version**: 无需 API 版本变更（向后兼容的字段增加）。

### 前端架构 (Frontend Architecture)

- **Component**: `DiffField` (Stateless Functional Component)。
- **Props**: `{ value: string, oldValue?: string, type?: 'text' }`。
- **Security**: 渲染 Diff 后的 HTML 时，需确保证内容被视作纯文本（避免注入），或仅对受信任的 Markdown 渲染器输出结果进行 Diff (但在 MVP 中直接 Diff 原始 Markdown 字符串更安全)。

### 决策影响分析 (Decision Impact Analysis)

**实现顺序:**
1.  后端逻辑 (`artifact_patch.py`)：实现 `_prev` 注入。
2.  前端组件 (`DiffField`)：实现基于 `fast-diff` 的渲染。
3.  父组件集成 (`StructuredRequirementView`)：传递 `_prev` 数据。

**跨组件依赖:**
- 前端强依赖后端正确返回 `_prev` 字段，否则无法显示 Inline Diff（只能回退到只显示新值）。

## 实现模式与一致性规则 (Implementation Patterns & Consistency Rules)

### 命名模式 (Naming Patterns)

- **后端 Key (Backend Key)**:
  - 必须使用 **`_prev`** (下划线前缀表示内部/元数据)。
  - **禁止**使用 `previous`, `oldValues`, `old_value` 等变体。
  - 数据结构: `_prev: { [field_name]: "old string value" }`

- **CSS 类名 (CSS Classes)**:
  - 必须使用语义化的全局工具类：
    - 删除: `.diff-deleted` (避免使用 `red-strike`)
    - 新增: `.diff-inserted` (避免使用 `green-bg`)
  - 定义位置: 全局通用 CSS 文件 (`index.css` 或 `global.css`)。

### 数据处理模式 (Data Processing Patterns)

- **后端写入策略 (Write Logic)**:
  - **按需写入**: 仅当 `new_val != old_val` 且 `old_val` 存在时，才写入 `_prev`。
  - **完整性**: 如果 ID 匹配但字段未变更，不要生成 `_prev` 条目。

- **前端渲染策略 (Render Logic)**:
  - **惰性计算**: 使用 `useMemo` 计算 diff 结果，避免每次重渲染都执行 `fast-diff`。
  - **组合模式**: 所有需要 Diff 的文本字段 **必须** 使用 `<DiffField />` 组件包裹，禁止在父组件内手动拼接 HTML。

### 错误处理模式 (Error Handling Patterns)

- **前端防御性编程**:
  - 如果 `_prev` 不是对象 -> 忽略，只显示当前值。
  - 如果 `fast-diff` 抛出异常 -> `try-catch` 捕获，降级只显示当前值，**绝不崩溃**。
  - 如果 `oldValue` 为空 -> 视为 `added` (整段高亮 `.diff-inserted`，而不做 inline diff)。

### 强制执行指南 (Enforcement Guidelines)

- **API 契约**: 后端返回的 JSON 必须通过 schema 验证（至少在测试中验证 `_prev` 结构）。
- **代码审查**: 检查所有新 `DiffField` 的使用是否传入了正确的 `oldValue`。

## 项目结构与边界 (Project Structure & Boundaries)

### 项目目录结构映射 (Directory Structure Mapping)

我们将**仅改动**以下核心文件，以保持增量开发的轻量化：

**后端 (Python) - 核心逻辑:**
- **File**: `tools/ai-agents/backend/agents/lisa/artifact_patch.py`
  - **Change**: 修改 `_merge_lists` 函数，注入 `_prev` 生成逻辑。
- **Test**: `tools/ai-agents/backend/tests/test_artifact_patch.py` (新增测试用例)。

**前端 (React) - UI 组件:**
- **Directory**: `tools/ai-agents/frontend/src/components/common/`
  - **New File**: `DiffField.tsx` (通用 Diff 字段组件)。
- **Directory**: `tools/ai-agents/frontend/src/components/artifact/`
  - **Modify File**: `StructuredRequirementView.tsx` (集成 `DiffField`)。
- **Styles**: `tools/ai-agents/frontend/src/index.css` (添加全局 Diff 样式)。

**测试 (Tests):**
- **Frontend Test**: `tools/ai-agents/frontend/src/components/common/__tests__/DiffField.test.tsx`

### 架构边界定义 (Architectural Boundaries)

**1. API 边界 (Diff 数据生成):**
- **Boundary**: `_merge_lists` 函数的返回值。
- **Contract**: 此函数是 `_prev` 数据的唯一合法来源。所有的 Diff 计算逻辑都封装在此，不泄漏到上层调用者。

**2. 组件边界 (Diff 数据消费):**
- **Boundary**: `<DiffField />` 组件接口。
- **Props**: `{ value, oldValue }`。
- **Isolation**: 组件内部处理 `fast-diff` 的所有细节。父组件 (`StructuredRequirementView`) 只负责透传数据，不知道如何计算 diff。

**3. 样式边界 (Global vs Local):**
- **Global**: `.diff-inserted` 和 `.diff-deleted` 定义在全局 CSS 中，供全站通用。
- **Local**: `DiffField` 组件内部布局相关的样式可局部化。

### 需求到结构的映射 (Requirements Mapping)

- **FR1 (变更标记)** -> `artifact_patch.py` (`_diff` field)
- **FR3 (旧值存储)** -> `artifact_patch.py` (`_prev` field)
- **FR5/6 (红删绿增)** -> `index.css` (.diff-*)
- **FR7 (Inline Diff)** -> `DiffField.tsx` (fast-diff logic)
- **FR7 (Inline Diff)** -> `DiffField.tsx` (fast-diff logic)
- **FR9-11 (结构覆盖)** -> `StructuredRequirementView.tsx` (在各个字段处调用 DiffField)

## 架构验证结果 (Architecture Validation Results)

### 一致性验证 (Coherence Validation) ✅

- **决策兼容性**: 扁平化数据结构 (`_prev`) 与前端 `DiffField` 的 props 设计完美匹配。
- **模式一致性**: 明确了 `StructuredRequirementView` 集成 `DiffField`，路径映射清晰。
- **技术栈对齐**: 复用 React + Python，引入 `fast-diff`，无冲突。

### 需求覆盖验证 (Requirements Coverage Validation) ✅

- **FR 覆盖**: FR1 (diff mark), FR2 (field diff), FR3 (_prev store), FR4 (transient) 都有对应的后端/前端逻辑支持。
- **User Journeys**: 支持 J1 (单条) 和 J2 (批量) 更新。
- **NFR 覆盖**: 性能（惰性计算）、复用性（通用组件）、兼容性（防御性编程）已考虑。

### 差距分析与缓解 (Gap Analysis Results)

- **Gap 1 (Testing)**: 我们定义了单元测试位置，但没有详细说明 **Diff 的测试用例数据**。需要开发者自行构造复杂的嵌套更新场景。
- **Gap 2 (CSS)**: 全局 CSS 文件路径不仅是 `index.css`，还可能是 `globals.css` 或 `App.css`，需要开发者根据实际项目确认。

### 架构就绪度评估 (Architecture Readiness Assessment)

- **总体状态**: 准备好进行实施 (READY FOR IMPLEMENTATION)
- **信心水平**: 高 (High)

### 实施交接指南 (Implementation Handoff)

**AI Agent 指南:**
1.  **Strict**: 严格遵守 `_prev` 命名约定，不要创造新的字段名。
2.  **Defensive**: 前端必须对空值 (`null/undefined`) 和格式错误进行防御性处理。
3.  **Scoped**: 仅修改指定的文件 (`artifact_patch.py`, `StructuredRequirementView.tsx`)，不要触碰无关模块。

**首个实施优先级:**
- 安装前端依赖: `npm install fast-diff` (或者 yarn add fast-diff)





