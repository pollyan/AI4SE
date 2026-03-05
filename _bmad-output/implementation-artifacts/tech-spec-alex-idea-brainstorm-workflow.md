---
title: 'Alex 创意头脑风暴工作流 (IDEA_BRAINSTORM)'
slug: 'alex-idea-brainstorm-workflow'
created: '2026-03-04'
status: 'completed'
stepsCompleted: [1, 2, 3, 4]
tech_stack: ['React', 'TypeScript', 'Zustand', 'Mermaid']
files_to_modify:
  - 'tools/new-agents/frontend/src/core/types.ts'
  - 'tools/new-agents/frontend/src/core/workflows.ts'
  - 'tools/new-agents/frontend/src/core/prompts/alexSystemPrompt.ts'
  - 'tools/new-agents/frontend/src/core/prompts/idea_brainstorm/*.ts'
  - 'tools/new-agents/frontend/src/core/prompts/systemPrompt.ts'
  - 'tools/new-agents/frontend/src/core/llm.ts'
  - 'tools/new-agents/frontend/src/core/config/agents.ts'
  - 'tools/new-agents/frontend/src/core/config/agentWorkflows.ts'
  - 'tools/new-agents/frontend/src/pages/Workspace.tsx'
  - 'tools/new-agents/frontend/src/components/WorkflowDropdown.tsx'
  - 'tools/new-agents/frontend/src/components/Header.tsx'
  - 'tools/new-agents/frontend/src/services/chatService.ts'
  - 'tools/new-agents/frontend/src/store.ts'
code_patterns:
  - 'WorkflowDef + stages 定义工作流阶段'
  - 'getSystemPrompt() 构建角色专属 System Prompt'
  - 'WORKFLOW_ID_MAP / WORKFLOW_SLUG_MAP 路由映射'
  - 'agentWorkflows.ts 配置 Agent → Workflow 关联'
test_patterns:
  - 'agents.test.ts Agent 配置测试'
  - 'workflows.test.ts 工作流配置测试'
  - 'onboarding.test.ts Onboarding 配置测试'
  - 'WorkflowDropdown.test.tsx 下拉组件测试'
---

# Tech-Spec: Alex 创意头脑风暴工作流 (IDEA_BRAINSTORM)

**Created:** 2026-03-04

## Overview

### Problem Statement

Alex 智能体目前处于 `coming_soon` 状态，没有任何可用的工作流。用户（产品经理/创业者/BA）有模糊的业务想法时，缺乏系统化思考和结构化输出的工具。需要实现 Alex 的首个工作流——创意头脑风暴，使其能引导用户将"脑中一闪而过的想法"转化为"可沟通、可验证的产品概念简报"。

### Solution

基于现有 Lisa 的架构模式（阶段式对话 + 结构化 Artifact），为 Alex 新增 `IDEA_BRAINSTORM` 工作流。包括 4 个阶段：定义问题域 (DEFINE) → 发散探索 (DIVERGE) → 收敛聚焦 (CONVERGE) → 概念输出 (CONCEPT)。需要扩展类型系统、新增 Alex 的 System Prompt、定义每个阶段的 Prompt 和 Artifact 模板，并将 Alex 从 `coming_soon` 切换为 `online`。

### Scope

**In Scope:**
1. 扩展 `WorkflowType` 类型 — 新增 `'IDEA_BRAINSTORM'`
2. 新增 `IDEA_BRAINSTORM` 的 `WorkflowDef`（4 个 Stage 定义 + Onboarding 配置）
3. 新建 Alex 专属的 System Prompt 构建逻辑（角色设定、变更标识、阶段推进协议）
4. 设计每个 Stage 的 Prompt（description）和 Artifact 模板（强调 Mermaid 图表 + 表格可视化）
5. 更新 `agentWorkflows.ts` — 新增 Alex 的工作流条目
6. 更新 `agents.ts` — Alex 状态从 `coming_soon` → `online`
7. 更新 `Workspace.tsx` 和 `WorkflowDropdown.tsx` 中的路由映射
8. 更新 `store.ts` — 适配多 Agent 的初始化逻辑（目前硬编码 Lisa 欢迎语）
9. 相关测试更新

**Out of Scope:**
- Alex 的其他工作流（PRD_CREATION, STORY_BREAKDOWN, COMPETITIVE_ANALYSIS）
- Alex ↔ Lisa 的产出物自动流转/导入功能
- 后端 API 变更（当前是纯前端直连 LLM）
- UI/UX 大改版（复用现有的 ChatPane + ArtifactPane 布局）

## Context for Development

### Design Preferences

- **可视化优先**：Artifact 模板中尽量使用 Mermaid 图表和结构化表格来增强表现力
- **已验证可用的 Mermaid 图表类型**：`quadrantChart`, `block-beta`, `pie`, `timeline`, `mindmap`, `flowchart`, `journey`
- **Mermaid 约束**：需注意 sanitizer 的限制（HTML 标签、特殊字符、timeline 冒号等）

### UX 交互设计原则（用户焦点小组成果）

| 原则 | 说明 | 影响阶段 |
|------|------|----------|
| **AI 主动填写，用户确认修正** | Artifact 应由 AI 根据对话自动生成草稿，用户来纠正，而非给空模板让用户填写 | ALL |
| **对话式引导，渐进式追问** | Prompt 不使用学术术语，用简单问句引导 | ALL |
| **术语用户友好化** | 全部使用中文友好表述加emoji标签 | ALL |
| **AI 先抛种子，用户反应后深挖** | 发散阶段 AI 主动提供方向供用户选择 | DIVERGE |
| **对话式间接评分** | 收敛阶段通过对话提问间接获取评分，AI 转化为数字 | CONVERGE |
| **自动整合，不要求重新组织** | 最终产出物由 AI 自动汇总前 3 阶段精华 | CONCEPT |

### Artifact 可视化设计规格（SCAMPER 分析成果）

#### 阶段 1: DEFINE — 问题域分析文档

**核心可视化**: `mindmap` 思维导图 + 类 Lean Canvas 结构化表格

**Artifact 模板结构**:
- 电梯演讲（30 字以内核心描述）
- 🎯 目标用户画像表格（角色/痛点/期望/场景）
- Mermaid `mindmap`：以核心问题为根节点，分支展示用户群、痛点、机会点
- 类 Lean Canvas 表格：问题/方案假设/目标用户/独特价值/约束条件
- 🚧 约束与边界（bullet points + emoji 标签精简）

**设计原则**:
- 用结构化表格取代纯文字叙述
- 文档结构与后续 PRD_CREATION 输入格式保持兼容
- 增加反向验证段（假设想法失败会是因为什么？）
- UX: AI 通过对话式追问获取信息后主动填写 Canvas 草稿，用户确认修正
- Prompt: 必须包含“验证问题真实性”的追问（你怎么知道这个问题真实存在？有什么证据？）

#### 阶段 2: DIVERGE — 创意发散探索

**核心可视化**: `mindmap` 创意发散图 + 创意卡片分组表格

**Artifact 模板结构**:
- Mermaid `mindmap`：以核心问题为中心，分支展示各创意方向
- 按创意技术分组的创意卡片表格（技术名称/创意名称/描述/目标用户/差异化点）
- 每个创意以 "How Might We..." 问句格式引出
- 状态标注：✅ Active / 💤 Parked / ❌ Killed

**设计原则**:
- **严格不评判**：发散阶段只收集、不评分（评分留给 CONVERGE）
- Prompt 应引导逆向风暴（最差方案是什么？然后翻转）
- 创意技术混合使用：SCAMPER、类比联想、逆向风暴等
- UX: AI 先主动抛出 3-5 个方向种子，用户选择感兴趣的方向后再深入展开
- UX: 逐个方向讨论，每讨论完一个再推进下一个，避免信息过载
- Prompt: 种子方向必须基于阶段 1 的问题域分析结合行业常见解决模式生成，不能凭空编造
- Prompt: AI 根据问题类型自动选取 1-2 种最适合的创意技术，而非全部上

#### 阶段 3: CONVERGE — 收敛聚焦

**核心可视化**: `quadrantChart` 象限图 + ICE 评分表格

**Artifact 模板结构**:
- Mermaid `quadrantChart`（影响力 × 可行性）定位每个创意
- ICE 评分表格：创意/影响力(1-5)/信心(1-5)/实施难度(1-5)/总分
- Mermaid `flowchart`：展示创意合并路径（互补创意如何组合为更强方案）
- Kill Your Darlings 环节：创意 > 3 个时强制收敛到 Top 3；创意 ≤ 3 个时跳过此环节

**设计原则**:
- 象限图 + 评分表双管齐下，让决策有理有据
- AI 模拟不同用户画像对创意的偏好
- 明确标注入选/淘汰理由
- UX: 通过对话式提问间接获取评分，AI 先给初始评分建议，用户修正
- Prompt: 创意合并触发条件——当两个创意的目标用户相同且痛点互补时，建议合并

#### 阶段 4: CONCEPT — 产品概念简报

**核心可视化**: One-Pager 概念画布表格 + `pie` MVP 功能分布图 + `flowchart` 用户旅程

**Artifact 模板结构**:
- 电梯演讲（开头 30 字核心定位）
- One-Pager 概念画布表格：问题/方案/目标用户/独特价值/竞品对比/成功指标
- Mermaid `pie`：MVP 功能分布（核心功能 / 增值功能 / 未来规划）
- Mermaid `flowchart`：核心用户旅程（用户从进入到获得价值的关键路径）
- 风险反思段（为什么这个产品可能失败？）
- 下一步行动清单

**设计原则**:
- 只保留 What 和 Why，不涉及 How（技术方案留给后续工作流）
- 产出物结构与 Lisa REQ_REVIEW 的输入格式兼容
- 产品概念一览表应该是一份可以直接拿去跟团队沟通的文档
- UX: AI 自动整合前 3 阶段精华生成最终产出物，用户不需要手动拼接
- UX: 电梯演讲由 AI 基于全流程对话自动生成
- Prompt: 电梯演讲公式模板——「为 [目标用户] 解决 [核心问题]，我们提供 [解决方案]，不同于 [现有方案]，我们的独特优势是 [差异化]」
- 技术决策: CONCEPT 阶段需要前 3 阶段的 Artifact 注入到 System Prompt 中（详见 Technical Decisions）

#### 可视化汇总

| 阶段 | 核心可视化 | Mermaid 图表类型 |
|------|-----------|----------------|
| DEFINE | 问题域思维导图 + Lean Canvas 表格 | `mindmap` + 表格 |
| DIVERGE | 创意发散思维导图 + 创意卡片分组表 | `mindmap` + 表格 |
| CONVERGE | 影响力×可行性象限图 + ICE 评分表 | `quadrantChart` + `flowchart` + 表格 |
| CONCEPT | 概念画布表格 + MVP 饼图 + 用户旅程 | `pie` + `flowchart` + 表格 |

### Codebase Patterns

**架构模式**:
- 工作流定义在 `workflows.ts` 中，使用 `WorkflowDef` 接口，每个阶段包含 `id`, `name`, `description`
- System Prompt 在 `systemPrompt.ts` 中构建，当前硬编码为 Lisa 角色
- Store (`store.ts`) 用 Zustand + persist 管理状态，存储 key 为 `lisa-storage`
- 路由模式: `/workspace/:agentId/:workflowId`
- LLM 调用在 `llm.ts` 中，通过 `getSystemPrompt()` 获取 system instruction
- 响应解析在 `llmParser.ts` 中，解析 `<CHAT>`, `<ARTIFACT>`, `<ACTION>` 三个标签
- 阶段切换在 `chatService.ts` 中处理，检测 `NEXT_STAGE` action 后调用 `setStageIndex()`

**Lisa 硬编码依赖清单（需改造为多 Agent 支持）**:

| 文件 | 硬编码内容 | 改造方案 |
|------|-----------|----------|
| `systemPrompt.ts:18` | "你叫 Lisa，是一名资深测试架构师" | 新建 `alexSystemPrompt.ts`，封装为工厂函数按 agent 选择 |
| `store.ts:20,23,39,41,101,106` | Lisa 欢迎语多处重复 | 抽取为函数 `getWelcomeMessage(workflow)` |
| `store.ts:111` | 存储 key `lisa-storage` | 改为 `agent-workspace-storage`（通用） |
| `chatService.ts:136` | Lisa 欢迎语比对 | 改用 `getWelcomeMessage()` |
| `Workspace.tsx:9-13` | `WORKFLOW_ID_MAP` 只有 Lisa 3 个 | 添加 Alex 的映射 |
| `WorkflowDropdown.tsx:8-12` | `WORKFLOW_SLUG_MAP` 只有 Lisa 3 个 | 添加 Alex 的映射 |
| `WorkflowDropdown.tsx:71` | "硬编码 Lisa AI 专家" | 根据当前 agentId 动态显示 |
| `WorkflowDropdown.tsx:92` | "选择不同的测试专家流水线" | 改为通用描述 |
| `WorkflowDropdown.tsx:133-135` | 硬编码 3 个工作流描述 | 改用 `WorkflowDef` 中的数据 |
| `Header.tsx:38` | `navigate('/workflows/lisa')` | 改为动态 `navigate(\`/workflows/${agentId}\`)` |
| `Header.tsx:96` | Lisa 头像 picsum URL | 根据 agentId 动态切换 |

### Files to Modify/Create

| 文件 | 操作 | 说明 |
| ---- | ---- | ------- |
| `core/types.ts:21` | 修改 | 扩展 `WorkflowType` 加入 `'IDEA_BRAINSTORM'` |
| `core/workflows.ts` | 修改 | 新增 `IDEA_BRAINSTORM` 的 `WorkflowDef`（4 个 Stage + Onboarding） |
| `core/prompts/alexSystemPrompt.ts` | 新建 | Alex 专属 System Prompt 构建逻辑 |
| `core/prompts/systemPrompt.ts` | 修改 | 重构为工厂函数，根据 workflow 类型选择 Lisa 或 Alex 的 prompt |
| `core/config/agents.ts:25` | 修改 | Alex status `coming_soon` → `online` |
| `core/config/agentWorkflows.ts` | 修改 | 新增 Alex 的工作流条目 |
| `pages/Workspace.tsx:9-13` | 修改 | `WORKFLOW_ID_MAP` 加入 `'idea-brainstorm': 'IDEA_BRAINSTORM'` |
| `components/WorkflowDropdown.tsx` | 修改 | `WORKFLOW_SLUG_MAP` + 去除硬编码 Lisa 文本 |
| `components/Header.tsx` | 修改 | 去除 Lisa 硬编码，动态展示 Agent 信息 |
| `store.ts` | 修改 | 抽取欢迎语函数、更新存储 key |
| `services/chatService.ts:136` | 修改 | 改用通用欢迎语函数 |
| `core/__tests__/onboarding.test.ts` | 修改 | 新增工作流会自动纳入检测 |
| `core/config/__tests__/agents.test.ts` | 修改 | Alex 状态断言从 `coming_soon` 改为 `online` |
| `core/config/__tests__/workflows.test.ts` | 修改 | Alex 工作流断言从空数组改为非空 |

### Technical Decisions

1. **跨阶段 Artifact 注入方案与 Token 限制（🔴 关键决策点）**:
   - 当前 `getSystemPrompt(workflow, stageIndex, currentArtifact)` 只传入当前阶段 Artifact
   - `llm.ts:73` 调用时传入的是 `state.artifactContent`（仅当前阶段）
   - **方案**: 为 Alex 的 `getAlexSystemPrompt()` 新增 `stageArtifacts` 参数，仅在 CONCEPT 阶段将前 3 阶段的 Artifact 注入 System Prompt 中
   - **Token 截断策略**: 为防止前序产出物内容过长导致 Token 溢出，注入前对每个阶段的内容进行截断（保留前 1500 字符或摘要核心表格）。
   - **影响范围**: 需修改 `llm.ts` 的调用方式，传入 `state.stageArtifacts`

2. **System Prompt 工厂模式**:
   - 不修改 Lisa 现有 `getSystemPrompt()` 的签名，避免破坏现有功能
   - 新建 `alexSystemPrompt.ts`，封装 `getAlexSystemPrompt(workflow, stageIndex, currentArtifact, stageArtifacts)`
   - 修改 `llm.ts` 中的调用逻辑：根据当前 workflow 类型选择调用哪个 prompt 函数

3. **WorkflowDef 新增 `agentId` 字段与 Map 统一化**:
   - 在 `WorkflowDef` 接口中新增 `agentId: string` 字段
   - 向前兼容：检查并更新 Lisa 现有的所有工作流声明，增加 `agentId: 'lisa'`
   - 将分散的 `WORKFLOW_ID_MAP` 和 `WORKFLOW_SLUG_MAP` 考虑做提取封装或直接从 `WORKFLOWS` 推导

4. **Store 硬编码清理 + 迁移兼容**:
   - 欢迎语抽取为 `getWelcomeMessage(workflow)` 函数（Alex 欢迎语为："你好！我是 Alex，你的产品创新顾问。告诉我你的初步想法，我们一起把它变成可实现的产品概念！"）
   - 存储 key 从 `lisa-storage` 改为 `agent-workspace-storage`
   - **迁移兼容**: 在 Zustand persist 的 `onRehydrateStorage` 回调或初始化钩子中读取旧 key 数据再合并，避免数据静默丢失（针对正在使用 Lisa 功能的用户）

5. **LLM 响应解析与竞态修复**:
   - 解析协议通用，Alex 复用 `llmParser.ts`
   - `chatService.ts:136` 修改欢迎语硬编码判定的同时，加入当前 workflow 和 agentId 的校验，防止 UI 面板渲染时出现旧 Agent 数据残留的竞态陷阱

## Implementation Plan

### Tasks

> 按依赖顺序排列，最底层先改，逐步向上。共 10 个任务。

- [x] **Task 0: 制定 Alex 角色人设 Brief**
  - Action: 明确 Alex 人设基调："你叫 Alex，是一名资深业务需求分析师和产品创新顾问。沟通风格：友好引导、善于追问、用简单通俗语言、鼓励用户思考。"并将此基调落地到新建的 prompt 文件注释中。

- [x] **Task 1: 扩展类型系统**
  - File: `core/types.ts`
  - Action:
    - `WorkflowType` 的联合类型中新增 `'IDEA_BRAINSTORM'`
    - `WorkflowDef` 新增 `agentId: string` 和 `welcomeMessage?: string`
  - Notes: 这是所有后续任务的基础，让路由、UI 都基于数据驱动。

- [x] **Task 2a: 定义 IDEA_BRAINSTORM 工作流 — DEFINE + DIVERGE 阶段及补充现有 AgentId**
  - File: `core/workflows.ts` + `core/prompts/idea_brainstorm/define.ts` + `diverge.ts`
  - Action: 
    - 补充 Lisa 各工作流 `agentId: 'lisa'` 避免 TS 报错。
    - DEFINE Prompt 骨架："作为 Alex... 主动抛出问题，你打算为谁解决什么烦恼？如果失败会怎样？随后生成 mindmap 和 Lean Canvas..."
    - DIVERGE Prompt 骨架："不加评判，抛出 3-5 个具体的种子方向，引导采用 SCAMPER 等方法进行创新，产出创意卡片..."

- [x] **Task 2b: 定义 IDEA_BRAINSTORM 工作流 — CONVERGE + CONCEPT 阶段 + Onboarding**
  - File: `core/workflows.ts` + `converge.ts` + `concept.ts`
  - Action: 
    - CONVERGE Prompt 骨架："对每个点询问用户的影响/信心预估并换算为 1-5 分，＞3 个选项时执行 Kill Your Darlings，生成 quadrantChart 象限图..."
    - CONCEPT Prompt 骨架："基于你获取的前序 Artifact（限制取最新精华摘要），应用「为[目标用户]解决[问题]，我们提供[方案]」的公式生成电梯演讲，绘制功能 pie 图与流程图。"
    - `onboarding` 配置: 默认 welcomeMessage ("你好！我是 Alex，你的产品创新顾问...") 和 starterPrompts。

- [x] **Task 3: 创建 Alex System Prompt**
  - File: `core/prompts/alexSystemPrompt.ts`（新建）
  - Action: 创建 `getAlexSystemPrompt(workflow, stageIndex, currentArtifact, stageArtifacts)` 函数
  - Notes: 在 CONCEPT 阶段运用 Token 截断策略注入前 3 阶段的内容。

- [x] **Task 4: 重构 LLM 调用层，支持多 Agent Prompt 选择**
  - File: `core/llm.ts`
  - Action: 通过 `WORKFLOWS[workflow].agentId` 判断并分发调用目标 SystemPrompt 生成器。传入截断/处理后的 `state.stageArtifacts`。

- [x] **Task 5: Store 适配与数据迁移**
  - File: `store.ts` + `services/chatService.ts`
  - Action:
    - 实现 `getWelcomeMessage(workflow)`。
    - 存储 key 改为 `agent-workspace-storage`，在 `onRehydrateStorage` （或类似加载钩子）中读取 `lisa-storage` 数据实现无缝回填。
    - 修复 `chatService.ts:136` 竞态（比对 `getWelcomeMessage()` 且校验当前 workflow 状态）。

- [x] **Task 6a: 配置变更与路由映射**
  - File: `core/config/agents.ts` + `core/config/agentWorkflows.ts` + `pages/Workspace.tsx`
  - Action: Alex status 设为 `online`，录入工作流，统一注册路由 ID 映射。

- [x] **Task 6b: UI 组件多 Agent 改造**
  - File: `components/WorkflowDropdown.tsx` + `components/Header.tsx`
  - Action:
    - 如果 Header 无 `agentId`，添加 `useParams<{agentId: string}>()`。
    - `WorkflowDropdown.tsx` 根据 `useParams()` 下的 `agentId` 动态过滤展示对应 Agent 的流水线选项。

- [x] **Task 7: 测试与 Sanitize 更新**
  - File: `config/__tests__/*.test.ts` + `core/utils/mermaidSanitizer.ts`
  - Action:
    - 新增所有工作流必须存在 `agentId` 字段的测试断言。
    - 验证并为 `quadrantChart` 的特殊字符渲染添加必要的 sanitize 检查。
  - Notes: 运行 `npm test` 保证全部通过。

### Acceptance Criteria

**Happy Path (✅ 可自动化):**

- [ ] AC 1: Given Alex 智能体已上线，when 用户在首页选择 Alex，then 显示工作流选择页面，且 "创意头脑风暴" 工作流状态为 online 并可点击
- [ ] AC 2: Given 用户进入 Alex 的创意头脑风暴工作流，when 页面加载完成，then 显示 4 个阶段标签（问题域分析/创意发散/收敛聚焦/概念输出）+ Alex 的欢迎语和引导话术

**Happy Path (🔸 Smoke Test / LLM Judge):**

- [ ] AC 3: Given 用户在 DEFINE 阶段输入模糊想法，when AI 回复，then `<ARTIFACT>` 中包含 mindmap 思维导图和 Lean Canvas 表格的 Markdown 内容
- [ ] AC 4: Given 用户在 DIVERGE 阶段与 AI 对话，when AI 生成创意方向，then `<ARTIFACT>` 中包含创意卡片表格和 mindmap，且不包含评分或排序
- [ ] AC 5: Given 用户在 CONVERGE 阶段确认创意评估，when AI 生成收敛结果，then `<ARTIFACT>` 中包含 quadrantChart 象限图和 ICE 评分表格
- [ ] AC 6: Given 用户从第 3 阶段确认进入 CONCEPT 阶段，when AI 生成产品概念简报，then `<ARTIFACT>` 中包含电梯演讲、概念画布表格、pie 功能分布图和 flowchart 用户旅程
- [ ] AC 7: Given 用户在每个阶段完成后，when 用户确认进入下一阶段，then AI 输出 `<ACTION>NEXT_STAGE</ACTION>` 且系统自动切换阶段

**多 Agent 适配 (✅ 可自动化):**

- [ ] AC 8: Given 用户在 Alex 工作空间，when 点击 Header 返回按钮，then 导航到 `/workflows/alex`（而非 `/workflows/lisa`）
- [ ] AC 9: Given 用户在 Alex 工作空间，when 打开工作流下拉菜单，then 仅显示 Alex 的工作流（不显示 Lisa 的测试设计等）
- [ ] AC 10: Given 用户在 Alex 工作空间开始新会话，when 点击"新会话"按钮，then Artifact 面板重置为 Alex 的欢迎语（而非 Lisa 的）

**边界与回归 (✅ 可自动化):**

- [ ] AC 11: Given Lisa 的所有工作流未被修改，when 用户使用 Lisa 的测试设计/需求评审/故障复盘工作流，then 行为与改动前完全一致（回归无破坏）
- [ ] AC 12: Given CONCEPT 是最后一个阶段，when 用户在 CONCEPT 阶段确认完成，then AI 不输出 `<ACTION>NEXT_STAGE</ACTION>`（🔸 Smoke Test）
- [ ] AC 13: Given 所有单元测试，when 执行 `npm test`，then 全部通过（包括新增和修改的测试用例）
- [ ] AC 14: Given 用户从 Alex 工作流切换到 Lisa 工作流，when store 重新初始化，then Lisa 的欢迎语和 Artifact 正确加载（不会残留 Alex 的数据）

## Additional Context

### Dependencies

- 无外部新依赖，复用现有 tech stack (React, TypeScript, Zustand, Mermaid, Vitest)

### Testing Strategy

**现有测试模式**:
- `vitest` 框架，使用 `describe/it/expect`
- 配置测试: `agents.test.ts` / `workflows.test.ts` 验证配置数据正确性
- Onboarding 测试: `onboarding.test.ts` 自动遍历所有工作流验证配置
- Smoke 测试: `workflow.smoke.test.ts` 使用真实 LLM + LLM Judge 验证完整工作流

**需要新增/修改的测试**:
- 修改 `agents.test.ts`: Alex 状态断言从 `coming_soon` → `online`
- 修改 `workflows.test.ts`: Alex 工作流从空数组→非空 + IDEA_BRAINSTORM 结构验证
- 现有 `onboarding.test.ts` 会自动覚察新工作流（遍历所有 keys）
- 可选: Alex 工作流的 smoke 测试（待上线后追加）

### Notes

- 头脑风暴阶段设计已确定：DEFINE → DIVERGE → CONVERGE → CONCEPT
- 参考 BMAD 框架中 brainstorming + create-product-brief 的方法论
- Alex-Lisa 协同：Alex 的产出物（产品概念简报）可作为 Lisa 需求评审的输入
- “创意头脑风暴”是 Alex 的第一个工作流，架构改造需考虑后续工作流（PRD_CREATION 等）的可扩展性
- INCIDENT_REVIEW 工作流的 Prompt 已抽取到独立文件（`prompts/incident_review/`），Alex 的 Prompt 也应采用类似模式

## Review Notes
- Adversarial review completed
- Findings: 6 total, 5 fixed, 1 skipped
- Resolution approach: auto-fix
