# 智能体交互设计与架构方案：测试专家 Agent 重构

**日期**: 2026-01-22
**状态**: Draft
**目标**: 重构 Lisa 测试专家 Agent 的工作流，从线性的"问答机器"升级为具备专业方法论、支持复杂交互的"专家顾问"。

---

## 1. 核心交互理念

### 1.1 模式：Chat-and-Show (专家模式)
- **左侧 (Chat)**: **导航与建议**。负责引导流程、解释意图、提供专家建议、通知变更。**严禁输出大段长文或表格**。
- **右侧 (Artifact)**: **Single Source of Truth**。负责展示结构化的全量信息、文档、图表。支持 **Diff 高亮** 增量更新。

### 1.2 左右分工原则 (DRY)
- **Chat**: "基于安全优先策略，我为您设计了 24 个测试点（见右侧）。重点关注高亮的 SQL 注入场景。"
- **Artifact**: (完整展示 24 个点的树状结构，其中安全节点高亮)

---

## 2. 四阶段工作流 (The 4 Phases)

### Phase 1: 需求澄清 (Requirement Analysis)
*目标：明确被测对象范围、业务流程与规则。*

*   **交互逻辑**: 引导式访谈 (Consultative Interview)。
*   **右侧展现**: `Markdown` 文档 (Scope - Flow - Rules)。
*   **关键特性**:
    *   **待确认清单 (Pending List)**: 明确列出模糊点。支持用户**挂起**（导出问题去线下确认）或**局部推进**（基于假设继续）。
    *   **冷启动 (Cold Start)**: 用户输入极少时，自动填充**行业标准模板**并标记为 `[默认]`。

### Phase 2: 策略与设计 (Test Strategy & Design)
*目标：确定测试方法论，拆解功能测试点。*

*   **交互逻辑**: **专家建议模式 (Advisor Mode)**。
    *   Agent 主动分析需求 -> 抛出《推荐测试策略》（如：建议采用边界值+安全测试）-> 用户 Accept/Reject。
*   **右侧展现**: **上下结构**。
    *   上：**策略卡片** (Markdown) - 测试层级、重点风险、专项测试类型。
    *   下：**测试点思维导图** (Tree/MindMap) - 显式标记方法论标签 (如 `[边界值]`, `[正交]`) 和优先级。
*   **增量更新**: 使用 Diff 高亮显示因策略调整而新增/删除的测试点。

### Phase 3: 用例具体化 (Test Case Instantiation)
*目标：生成可执行的详细步骤与预期结果。*

*   **交互逻辑**: 层级化预览与微调。
*   **右侧展现**: **树形表格 (Tree Table)**。
    *   展开测试点可见具体的 Steps, Expected Result, Pre-conditions。
*   **特性**: 支持对单个用例的微调（改文字）。

### Phase 4: 交付与归档 (Delivery)
*目标：组装完整交付件，结束任务。*

*   **交互逻辑**: 预览与导出。
*   **右侧展现**: **完整测试设计说明书** (Requirement + Strategy + Points + Cases)。
*   **出口动作**:
    *   `下载 PDF/Word` (汇报用)
    *   `生成 MidScene 脚本` (自动化测试用)
    *   `同步至测试管理平台` (Jira/PingCode)

---

## 3. 关键机制设计

### 3.1 非线性跳转与热修补 (Hot-Patching)
*   **场景**: 用户在 Phase 3 突然想起 Phase 1 的需求遗漏。
*   **逻辑**: 基于**意图识别**。
    1.  捕获变更意图 ("加个手机号验证")。
    2.  **自动回溯**: 更新 Phase 1 状态。
    3.  **级联更新 (Ripple Effect)**: 自动重新生成/标记 Phase 2 和 Phase 3 中受影响的部分。
    4.  **视图跳转**: 暂时切回 Phase 2 视图展示变更影响，请求用户确认。

### 3.2 一致性控制 (Consistency Control)
为了解决 LLM 生成不稳定的问题，确保 Diff 准确：
*   **ID 锚定**: 强制 LLM 维护稳定的 Node ID (如 `TP-101`)，严禁重排现有 ID。
*   **Patch 模式**: 优先让 LLM 输出 **操作指令 (Actions)** 而非全量 JSON。
    *   Example: `[{"op": "add", "parent": "root", "node": {...}}]`
    *   后端负责 Apply Patch，保证未变动部分字节级一致。

---

## 4. 数据结构 (Artifact Schema Draft)

为了支持通用的 `ArtifactRenderer` 组件，采用类型化数据结构。

```typescript
// 通用信封
interface AgentArtifact {
  phase: 'requirement' | 'design' | 'cases' | 'delivery';
  version: string;
  content: RequirementDoc | TestDesignDoc | TestCaseDoc | DeliveryDoc;
}

// Phase 1: 需求
interface RequirementDoc {
  scope: string[]; // Markdown list
  flow_mermaid: string;
  rules: Array<{ id: string; desc: string; source: 'user' | 'default' }>;
  assumptions: Array<{ id: string; question: string; status: 'pending' | 'assumed' }>;
}

// Phase 2: 设计
interface TestDesignDoc {
  strategy: {
    levels: string[]; // ['Unit', 'Integration']
    focus: string[]; // ['Security', 'Boundary']
  };
  test_points: TestNode; // Tree structure
}

interface TestNode {
  id: string;
  label: string;
  type: 'group' | 'point';
  method?: string; // 'Boundary', 'Equivalence'
  priority?: 'P0' | 'P1';
  is_new?: boolean; // For Diff UI
  children?: TestNode[];
}

// Phase 3: 用例
interface TestCaseDoc {
  cases: Array<{
    id: string; // Refers to TestNode ID
    steps: Array<{ action: string; expect: string }>;
    script?: string; // Automation snippet
  }>;
}

## 6. 补充说明 (MVP Scope)

### 6.1 错误恢复策略 (Robustness)
鉴于 LLM 输出的不稳定性，必须建立多层防护：
1.  **自动重试 (Auto-Retry)**: 后端检测到 JSON 解析错误或 Schema 校验失败时，自动重试 (Max Retries = 3)。
2.  **降级机制 (Fallback)**: 如果 Patch 指令执行失败（如找不到 Parent ID），自动降级为请求 LLM 进行**全量重新生成**，确保 UI 不崩溃。

### 6.2 支持的测试方法论 (Methodology Full-Set)
Agent 将根据需求特征动态选择以下方法论（不限于）：
*   **黑盒测试**: 等价类划分 (Equivalence), 边界值分析 (Boundary), 判定表 (Decision Table), 状态迁移 (State Transition), 正交实验 (Orthogonal Array), 错误推测 (Error Guessing).
*   **场景测试**: 用例场景法 (Use Case Testing), 流程分析法.
*   **非功能**: 负载测试策略, 安全性测试策略 (OWASP Top 10), 兼容性测试策略.

### 6.3 范围约束
*   **无持久化**: 本版本为 Demo 性质，刷新即重置，不支持历史回溯或多任务切换。
*   **Single Head**: 始终展示最新状态，不支持撤销/重做 (Undo/Redo)。

```

## 5. 实施路线图

1.  **Contract Definition**: 确立前后端 JSON Schema。
2.  **Prompt Engineering**: 重写 System Prompt，植入专家人设和四阶段状态机。
3.  **Frontend**: 开发 `ArtifactRenderer` (Markdown, Mermaid, TreeView, Diff)。
4.  **Backend**: 实现 Patch 逻辑和状态回溯机制。
