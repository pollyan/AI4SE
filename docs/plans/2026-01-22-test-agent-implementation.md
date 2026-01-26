# 测试专家 Agent 重构 - 实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 重构 Lisa 测试专家 Agent，实现 Chat-and-Show 交互模式，支持四阶段工作流和结构化 Artifact 输出。

**Architecture:** 采用 Backend-First 策略。先定义 Pydantic 数据契约，再重构 Prompt 植入专家人设，最后开发前端 Artifact 渲染器。后端使用 ID 锚定 + Patch 模式确保增量更新一致性。

**Tech Stack:** Python 3.11+ / Pydantic / LangGraph / Flask / React 19 / TypeScript / assistant-ui / Mermaid

**Design Doc:** `docs/plans/2026-01-22-test-agent-redesign.md`

---

## Phase 1: 数据契约定义 (Foundation)

### Task 1.1: 创建 Artifact Schema (Backend Pydantic)

**Files:**
- Create: `tools/ai-agents/backend/agents/lisa/artifact_models.py`
- Test: `tools/ai-agents/backend/tests/test_artifact_models.py`

**Step 1: Write the failing test**

```python
# tools/ai-agents/backend/tests/test_artifact_models.py
"""测试 Artifact 数据模型的序列化和验证"""
import pytest
from backend.agents.lisa.artifact_models import (
    ArtifactPhase,
    RuleItem,
    AssumptionItem,
    RequirementDoc,
    TestNode,
    TestDesignDoc,
    TestStep,
    TestCaseItem,
    TestCaseDoc,
    AgentArtifact,
)


class TestRequirementDoc:
    """Phase 1: 需求文档模型测试"""

    def test_requirement_doc_basic_creation(self):
        """测试基本创建"""
        doc = RequirementDoc(
            scope=["登录页面", "POST /api/login"],
            flow_mermaid="graph LR; A-->B",
            rules=[
                RuleItem(id="R1", desc="密码不能为空", source="user")
            ],
            assumptions=[
                AssumptionItem(id="Q1", question="是否支持第三方登录?", status="pending")
            ],
        )
        assert doc.scope == ["登录页面", "POST /api/login"]
        assert len(doc.rules) == 1
        assert doc.rules[0].source == "user"

    def test_assumption_status_validation(self):
        """测试假设状态枚举验证"""
        item = AssumptionItem(id="Q1", question="问题", status="assumed")
        assert item.status == "assumed"


class TestTestDesignDoc:
    """Phase 2: 测试设计文档模型测试"""

    def test_test_node_tree_structure(self):
        """测试树形结构"""
        child = TestNode(
            id="TP-001",
            label="密码为空校验",
            type="point",
            method="等价类",
            priority="P0",
        )
        parent = TestNode(
            id="GRP-001",
            label="登录表单校验",
            type="group",
            children=[child],
        )
        assert parent.children[0].id == "TP-001"
        assert parent.children[0].method == "等价类"

    def test_design_doc_with_strategy(self):
        """测试完整设计文档"""
        doc = TestDesignDoc(
            strategy_markdown="## 测试策略\n- 边界值分析\n- 安全测试",
            test_points=TestNode(
                id="ROOT",
                label="登录模块",
                type="group",
                children=[],
            ),
        )
        assert "边界值" in doc.strategy_markdown


class TestTestCaseDoc:
    """Phase 3: 测试用例文档模型测试"""

    def test_case_with_steps(self):
        """测试用例步骤"""
        case = TestCaseItem(
            id="TC-001",
            title="验证有效登录",
            precondition="用户已注册",
            steps=[
                TestStep(action="访问登录页", expect="页面加载"),
                TestStep(action="输入账密", expect="输入成功"),
            ],
            tags=["Smoke", "P0"],
        )
        assert len(case.steps) == 2
        assert case.steps[0].action == "访问登录页"


class TestAgentArtifact:
    """通用 Artifact 信封测试"""

    def test_artifact_phase_enum(self):
        """测试阶段枚举"""
        artifact = AgentArtifact(
            phase="requirement",
            version="1.0",
            content=RequirementDoc(
                scope=["test"],
                flow_mermaid="",
                rules=[],
                assumptions=[],
            ),
        )
        assert artifact.phase == "requirement"

    def test_artifact_json_serialization(self):
        """测试 JSON 序列化"""
        doc = RequirementDoc(
            scope=["test"],
            flow_mermaid="graph LR; A-->B",
            rules=[RuleItem(id="R1", desc="规则1", source="default")],
            assumptions=[],
        )
        artifact = AgentArtifact(phase="requirement", version="1.0", content=doc)
        json_str = artifact.model_dump_json()
        assert '"phase":"requirement"' in json_str
        assert '"source":"default"' in json_str
```

**Step 2: Run test to verify it fails**

Run: `pytest tools/ai-agents/backend/tests/test_artifact_models.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'backend.agents.lisa.artifact_models'"

**Step 3: Write minimal implementation**

```python
# tools/ai-agents/backend/agents/lisa/artifact_models.py
"""
Lisa Agent Artifact 数据模型

定义四阶段工作流的结构化产出物 Schema。
用于前后端契约、LLM 输出校验和增量 Diff。
"""
from typing import List, Optional, Literal, Union
from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════════════════
# 通用类型定义
# ═══════════════════════════════════════════════════════════════════════════════

ArtifactPhase = Literal["requirement", "design", "cases", "delivery"]
Priority = Literal["P0", "P1", "P2", "P3"]
NodeType = Literal["group", "point"]
AssumptionStatus = Literal["pending", "assumed", "confirmed"]
RuleSource = Literal["user", "default"]


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 1: 需求澄清 (Requirement)
# ═══════════════════════════════════════════════════════════════════════════════

class RuleItem(BaseModel):
    """业务规则项"""
    id: str = Field(description="规则唯一标识，如 R1, R2")
    desc: str = Field(description="规则描述")
    source: RuleSource = Field(description="来源：user=用户提供, default=系统默认")


class AssumptionItem(BaseModel):
    """待确认/假设项"""
    id: str = Field(description="问题唯一标识，如 Q1, Q2")
    question: str = Field(description="问题描述")
    status: AssumptionStatus = Field(description="状态：pending/assumed/confirmed")
    note: Optional[str] = Field(default=None, description="备注或假设值")


class RequirementDoc(BaseModel):
    """Phase 1 产出物：需求分析文档"""
    scope: List[str] = Field(description="被测对象范围列表")
    flow_mermaid: str = Field(description="业务流程 Mermaid 代码")
    rules: List[RuleItem] = Field(default_factory=list, description="核心规则列表")
    assumptions: List[AssumptionItem] = Field(default_factory=list, description="待确认/假设列表")
    nfr_markdown: Optional[str] = Field(default=None, description="非功能需求 Markdown")


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 2: 策略与设计 (Design)
# ═══════════════════════════════════════════════════════════════════════════════

class TestNode(BaseModel):
    """测试点树节点"""
    id: str = Field(description="节点唯一标识，如 GRP-001, TP-001")
    label: str = Field(description="节点标签/名称")
    type: NodeType = Field(description="节点类型：group=分组, point=测试点")
    method: Optional[str] = Field(default=None, description="测试方法论标签，如 边界值、等价类")
    priority: Optional[Priority] = Field(default=None, description="优先级")
    is_new: Optional[bool] = Field(default=None, description="是否为新增节点（用于 Diff 高亮）")
    children: Optional[List["TestNode"]] = Field(default=None, description="子节点列表")


class TestDesignDoc(BaseModel):
    """Phase 2 产出物：测试策略与设计"""
    strategy_markdown: str = Field(description="测试策略 Markdown 文档")
    test_points: TestNode = Field(description="测试点树根节点")


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 3: 用例生成 (Cases)
# ═══════════════════════════════════════════════════════════════════════════════

class TestStep(BaseModel):
    """测试步骤"""
    action: str = Field(description="操作描述")
    expect: str = Field(description="预期结果")


class TestCaseItem(BaseModel):
    """单个测试用例"""
    id: str = Field(description="用例 ID，对应 TestNode ID")
    title: str = Field(description="用例标题")
    precondition: Optional[str] = Field(default=None, description="前置条件")
    steps: List[TestStep] = Field(default_factory=list, description="执行步骤列表")
    tags: List[str] = Field(default_factory=list, description="标签，如 Smoke, Regression")
    script: Optional[str] = Field(default=None, description="自动化脚本片段")


class TestCaseDoc(BaseModel):
    """Phase 3 产出物：测试用例集"""
    cases: List[TestCaseItem] = Field(default_factory=list, description="用例列表")
    stats: Optional[dict] = Field(default=None, description="统计信息，如 total, p0_count")


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 4: 交付 (Delivery) - 组装前三阶段内容
# ═══════════════════════════════════════════════════════════════════════════════

class DeliveryDoc(BaseModel):
    """Phase 4 产出物：最终交付文档"""
    title: str = Field(description="文档标题")
    version: str = Field(description="版本号")
    requirement: RequirementDoc = Field(description="需求文档")
    design: TestDesignDoc = Field(description="设计文档")
    cases: TestCaseDoc = Field(description="用例文档")
    summary_markdown: Optional[str] = Field(default=None, description="概览摘要 Markdown")


# ═══════════════════════════════════════════════════════════════════════════════
# 通用 Artifact 信封
# ═══════════════════════════════════════════════════════════════════════════════

class AgentArtifact(BaseModel):
    """Agent 产出物通用信封"""
    phase: ArtifactPhase = Field(description="当前阶段")
    version: str = Field(description="版本号")
    content: Union[RequirementDoc, TestDesignDoc, TestCaseDoc, DeliveryDoc] = Field(
        description="阶段对应的内容"
    )


# 支持 TestNode 的自引用
TestNode.model_rebuild()
```

**Step 4: Run test to verify it passes**

Run: `pytest tools/ai-agents/backend/tests/test_artifact_models.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add tools/ai-agents/backend/agents/lisa/artifact_models.py tools/ai-agents/backend/tests/test_artifact_models.py
git commit -m "feat(lisa): add artifact data models for 4-phase workflow"
```

---

### Task 1.2: 创建 TypeScript 类型定义 (Frontend)

**Files:**
- Create: `tools/ai-agents/frontend/src/types/artifact.ts`

**Step 1: Create types directory**

Run: `mkdir -p tools/ai-agents/frontend/src/types`

**Step 2: Write TypeScript interfaces**

```typescript
// tools/ai-agents/frontend/src/types/artifact.ts
/**
 * Lisa Agent Artifact 数据类型定义
 * 
 * 与后端 artifact_models.py 保持同步
 */

// ═══════════════════════════════════════════════════════════════════════════════
// 通用类型
// ═══════════════════════════════════════════════════════════════════════════════

export type ArtifactPhase = 'requirement' | 'design' | 'cases' | 'delivery';
export type Priority = 'P0' | 'P1' | 'P2' | 'P3';
export type NodeType = 'group' | 'point';
export type AssumptionStatus = 'pending' | 'assumed' | 'confirmed';
export type RuleSource = 'user' | 'default';

// ═══════════════════════════════════════════════════════════════════════════════
// Phase 1: 需求澄清
// ═══════════════════════════════════════════════════════════════════════════════

export interface RuleItem {
  id: string;
  desc: string;
  source: RuleSource;
}

export interface AssumptionItem {
  id: string;
  question: string;
  status: AssumptionStatus;
  note?: string;
}

export interface RequirementDoc {
  scope: string[];
  flow_mermaid: string;
  rules: RuleItem[];
  assumptions: AssumptionItem[];
  nfr_markdown?: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// Phase 2: 策略与设计
// ═══════════════════════════════════════════════════════════════════════════════

export interface TestNode {
  id: string;
  label: string;
  type: NodeType;
  method?: string;
  priority?: Priority;
  is_new?: boolean;
  children?: TestNode[];
}

export interface TestDesignDoc {
  strategy_markdown: string;
  test_points: TestNode;
}

// ═══════════════════════════════════════════════════════════════════════════════
// Phase 3: 用例生成
// ═══════════════════════════════════════════════════════════════════════════════

export interface TestStep {
  action: string;
  expect: string;
}

export interface TestCaseItem {
  id: string;
  title: string;
  precondition?: string;
  steps: TestStep[];
  tags: string[];
  script?: string;
}

export interface TestCaseDoc {
  cases: TestCaseItem[];
  stats?: {
    total: number;
    p0_count?: number;
    auto_ready?: number;
  };
}

// ═══════════════════════════════════════════════════════════════════════════════
// Phase 4: 交付
// ═══════════════════════════════════════════════════════════════════════════════

export interface DeliveryDoc {
  title: string;
  version: string;
  requirement: RequirementDoc;
  design: TestDesignDoc;
  cases: TestCaseDoc;
  summary_markdown?: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// 通用 Artifact 信封
// ═══════════════════════════════════════════════════════════════════════════════

export interface AgentArtifact {
  phase: ArtifactPhase;
  version: string;
  content: RequirementDoc | TestDesignDoc | TestCaseDoc | DeliveryDoc;
}

// 类型守卫函数
export function isRequirementDoc(content: AgentArtifact['content']): content is RequirementDoc {
  return 'scope' in content && 'rules' in content;
}

export function isTestDesignDoc(content: AgentArtifact['content']): content is TestDesignDoc {
  return 'strategy_markdown' in content && 'test_points' in content;
}

export function isTestCaseDoc(content: AgentArtifact['content']): content is TestCaseDoc {
  return 'cases' in content && Array.isArray((content as TestCaseDoc).cases);
}

export function isDeliveryDoc(content: AgentArtifact['content']): content is DeliveryDoc {
  return 'requirement' in content && 'design' in content && 'cases' in content;
}
```

**Step 3: Verify TypeScript compiles**

Run: `cd tools/ai-agents/frontend && npx tsc --noEmit src/types/artifact.ts`
Expected: No errors

**Step 4: Commit**

```bash
git add tools/ai-agents/frontend/src/types/artifact.ts
git commit -m "feat(frontend): add TypeScript artifact type definitions"
```

---

## Phase 2: 后端逻辑重构 (Backend Logic)

### Task 2.1: 重构 System Prompt - 植入专家人设

**Files:**
- Modify: `tools/ai-agents/backend/agents/lisa/prompts/shared.py`
- Modify: `tools/ai-agents/backend/agents/lisa/prompts/workflows/test_design.py`

**Step 1: 阅读现有 shared.py 并理解结构**

Run: `cat tools/ai-agents/backend/agents/lisa/prompts/shared.py`

**Step 2: 更新 LISA_IDENTITY 和 LISA_STYLE**

在 `shared.py` 中找到 `LISA_IDENTITY` 和 `LISA_STYLE`，更新为专家顾问人设：

```python
# 更新后的内容（需要根据实际文件结构调整）
LISA_IDENTITY = """
你是 Lisa Song，一位资深测试架构师和质量工程顾问。你拥有 15 年以上的软件测试经验，
精通 ISTQB 方法论，曾主导过多个大型系统的测试体系建设。

**你的核心能力**：
- 需求分析与风险识别
- 测试策略设计（等价类、边界值、判定表、状态迁移、正交实验等）
- 测试用例设计与评审
- 自动化测试架构

**你的工作风格**：
- **专家建议者**：你主动提出专业建议，而非被动等待指令
- **结构化思维**：你的产出物总是清晰、结构化、可追溯
- **风险导向**：你优先关注高风险区域，确保测试投资回报最大化
"""

LISA_STYLE = """
**交互风格**：
1. **对话简洁**：左侧对话只输出导航、摘要和关键提示，详细内容在右侧 Artifact 展示
2. **专家姿态**：主动提出策略建议，而非询问用户"您想用什么方法"
3. **DRY 原则**：不在对话中重复 Artifact 中已有的内容
4. **进度感知**：明确告知用户当前阶段和下一步计划
"""
```

**Step 3: 更新阶段 Prompt (test_design.py)**

修改 `STAGE_CLARIFY_PROMPT`、`STAGE_STRATEGY_PROMPT` 等，植入 Chat-and-Show 左右分工原则。

**Step 4: 运行现有测试确保无回归**

Run: `pytest tools/ai-agents/backend/tests/ -v -k "prompt or lisa"`

**Step 5: Commit**

```bash
git add tools/ai-agents/backend/agents/lisa/prompts/
git commit -m "refactor(lisa): update prompts with expert persona and chat-and-show style"
```

---

### Task 2.2: 实现结构化 Artifact 输出节点

**Files:**
- Modify: `tools/ai-agents/backend/agents/lisa/nodes/artifact_node.py`
- Modify: `tools/ai-agents/backend/agents/lisa/schemas.py`
- Test: `tools/ai-agents/backend/tests/test_artifact_node.py`

**Step 1: 更新 schemas.py 添加结构化输出 Schema**

```python
# 在 schemas.py 中添加
from .artifact_models import RequirementDoc, TestDesignDoc, TestCaseDoc

class StructuredArtifactOutput(BaseModel):
    """结构化 Artifact 输出"""
    artifact_type: Literal["requirement", "design", "cases"] = Field(
        description="产出物类型"
    )
    content: Union[RequirementDoc, TestDesignDoc, TestCaseDoc] = Field(
        description="结构化内容"
    )
```

**Step 2: 修改 artifact_node.py 使用结构化输出**

（具体代码需要根据现有 artifact_node.py 的实现来调整）

**Step 3: 更新测试**

Run: `pytest tools/ai-agents/backend/tests/test_artifact_node.py -v`

**Step 4: Commit**

```bash
git add tools/ai-agents/backend/agents/lisa/nodes/artifact_node.py tools/ai-agents/backend/agents/lisa/schemas.py
git commit -m "feat(lisa): implement structured artifact output for all phases"
```

---

### Task 2.3: 实现 Patch 模式支持

**Files:**
- Create: `tools/ai-agents/backend/agents/lisa/artifact_patch.py`
- Test: `tools/ai-agents/backend/tests/test_artifact_patch.py`

**Step 1: Write the failing test**

```python
# tools/ai-agents/backend/tests/test_artifact_patch.py
"""测试 Artifact Patch 逻辑"""
import pytest
from backend.agents.lisa.artifact_patch import apply_patch, PatchOperation
from backend.agents.lisa.artifact_models import TestNode, TestDesignDoc


class TestPatchOperations:
    """测试 Patch 操作"""

    def test_add_node(self):
        """测试添加节点"""
        root = TestNode(id="ROOT", label="Root", type="group", children=[])
        patch = PatchOperation(
            op="add",
            parent_id="ROOT",
            node=TestNode(id="TP-001", label="新测试点", type="point", method="边界值"),
        )
        result = apply_patch(root, [patch])
        assert len(result.children) == 1
        assert result.children[0].id == "TP-001"

    def test_modify_node(self):
        """测试修改节点"""
        root = TestNode(
            id="ROOT",
            label="Root",
            type="group",
            children=[TestNode(id="TP-001", label="旧名称", type="point")],
        )
        patch = PatchOperation(
            op="modify",
            target_id="TP-001",
            field="label",
            value="新名称",
        )
        result = apply_patch(root, [patch])
        assert result.children[0].label == "新名称"

    def test_delete_node(self):
        """测试删除节点"""
        root = TestNode(
            id="ROOT",
            label="Root",
            type="group",
            children=[
                TestNode(id="TP-001", label="保留", type="point"),
                TestNode(id="TP-002", label="删除", type="point"),
            ],
        )
        patch = PatchOperation(op="delete", target_id="TP-002")
        result = apply_patch(root, [patch])
        assert len(result.children) == 1
        assert result.children[0].id == "TP-001"
```

**Step 2: Run test to verify it fails**

Run: `pytest tools/ai-agents/backend/tests/test_artifact_patch.py -v`

**Step 3: Write implementation**

```python
# tools/ai-agents/backend/agents/lisa/artifact_patch.py
"""
Artifact Patch 操作实现

支持对 TestNode 树进行增量修改，确保 ID 锚定和一致性。
"""
from typing import List, Optional, Literal, Any
from pydantic import BaseModel, Field
from .artifact_models import TestNode


class PatchOperation(BaseModel):
    """Patch 操作定义"""
    op: Literal["add", "modify", "delete"] = Field(description="操作类型")
    parent_id: Optional[str] = Field(default=None, description="父节点 ID (add 时必填)")
    target_id: Optional[str] = Field(default=None, description="目标节点 ID (modify/delete)")
    node: Optional[TestNode] = Field(default=None, description="新节点 (add 时必填)")
    field: Optional[str] = Field(default=None, description="要修改的字段 (modify)")
    value: Optional[Any] = Field(default=None, description="新值 (modify)")


def find_node(root: TestNode, node_id: str) -> Optional[TestNode]:
    """递归查找节点"""
    if root.id == node_id:
        return root
    if root.children:
        for child in root.children:
            found = find_node(child, node_id)
            if found:
                return found
    return None


def apply_patch(root: TestNode, patches: List[PatchOperation]) -> TestNode:
    """
    应用 Patch 操作列表到树结构
    
    Args:
        root: 树根节点
        patches: Patch 操作列表
    
    Returns:
        更新后的树根节点（深拷贝）
    """
    # 深拷贝避免修改原对象
    result = root.model_copy(deep=True)
    
    for patch in patches:
        if patch.op == "add":
            parent = find_node(result, patch.parent_id)
            if parent:
                if parent.children is None:
                    parent.children = []
                parent.children.append(patch.node.model_copy(deep=True))
        
        elif patch.op == "modify":
            target = find_node(result, patch.target_id)
            if target and patch.field:
                setattr(target, patch.field, patch.value)
        
        elif patch.op == "delete":
            # 需要找到父节点并从 children 中移除
            _delete_node_recursive(result, patch.target_id)
    
    return result


def _delete_node_recursive(node: TestNode, target_id: str) -> bool:
    """递归删除节点"""
    if node.children:
        for i, child in enumerate(node.children):
            if child.id == target_id:
                node.children.pop(i)
                return True
            if _delete_node_recursive(child, target_id):
                return True
    return False
```

**Step 4: Run test to verify it passes**

Run: `pytest tools/ai-agents/backend/tests/test_artifact_patch.py -v`

**Step 5: Commit**

```bash
git add tools/ai-agents/backend/agents/lisa/artifact_patch.py tools/ai-agents/backend/tests/test_artifact_patch.py
git commit -m "feat(lisa): implement artifact patch operations for incremental updates"
```

---

## Phase 3: 前端组件开发 (Frontend)

### Task 3.1: 创建 ArtifactRenderer 基础组件

**Files:**
- Create: `tools/ai-agents/frontend/src/components/artifact/ArtifactRenderer.tsx`
- Test: `tools/ai-agents/frontend/src/__tests__/components/ArtifactRenderer.test.tsx`

（详细步骤类似上述模式，包含测试、实现、验证、提交）

### Task 3.2: 实现 RequirementView (Markdown + Mermaid)

**Files:**
- Create: `tools/ai-agents/frontend/src/components/artifact/RequirementView.tsx`

### Task 3.3: 实现 DesignView (Strategy + MindMap)

**Files:**
- Create: `tools/ai-agents/frontend/src/components/artifact/DesignView.tsx`

### Task 3.4: 实现 CaseView (Table)

**Files:**
- Create: `tools/ai-agents/frontend/src/components/artifact/CaseView.tsx`

---

## Phase 4: 集成验证 (Integration)

### Task 4.1: 端到端流程测试

**Steps:**
1. 启动后端服务
2. 启动前端开发服务器
3. 手动测试完整流程：需求输入 -> 策略生成 -> 用例生成 -> 导出

### Task 4.2: 编写集成测试

**Files:**
- Create: `tools/ai-agents/backend/tests/test_workflow_integration.py`

---

## 任务清单总览

| # | Task | Priority | Status |
|---|------|----------|--------|
| 1.1 | Backend Pydantic Models | High | Pending |
| 1.2 | Frontend TypeScript Types | High | Pending |
| 2.1 | Refactor System Prompt | High | Pending |
| 2.2 | Structured Artifact Output | Medium | Pending |
| 2.3 | Patch Mode Implementation | Medium | Pending |
| 3.1 | ArtifactRenderer Component | Medium | Pending |
| 3.2 | RequirementView | Medium | Pending |
| 3.3 | DesignView | Medium | Pending |
| 3.4 | CaseView | Medium | Pending |
| 4.1 | E2E Manual Test | High | Pending |
| 4.2 | Integration Test | Medium | Pending |

---

## 备注

- **TDD 原则**：每个任务都遵循 红-绿-重构 循环
- **频繁提交**：每个 Task 完成后立即 commit
- **增量验证**：每完成一个 Phase 就进行手动验收
