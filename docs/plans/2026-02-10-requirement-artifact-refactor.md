# Lisa Agent 需求澄清产出物重构实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 重构需求澄清阶段产出物结构，扩展为 7 段，统一初始化和对话后的渲染逻辑。

**Architecture:** 
- 扩展 `RequirementDoc` Pydantic 模型，新增 `out_of_scope` 和 `features` 字段
- 删除手写 `ARTIFACT_CLARIFY_REQUIREMENTS` 模板，改用动态生成（SSOT）
- `confirmed_items` 通过过滤 `assumptions` 实现，不新增字段

**Tech Stack:** Python (Pydantic, LangGraph), TypeScript (React, Vitest)

---

## 📊 执行依赖图 (Task Dependency Graph)

```
Phase 1 (后端模型)
    ├── 1.1 编写 FeatureItem 测试
    ├── 1.2 编写 RequirementDoc 新字段测试
    │         ↓ (测试先行)
    ├── 1.3 实现 FeatureItem
    ├── 1.4 更新 RequirementDoc
    │         ↓
    └── 1.5 验证现有测试
              ↓
Phase 2 (Markdown 渲染)     ←→     Phase 4 (前端类型) [可并行]
    ├── 2.1 编写 7段结构测试            ├── 4.1 添加 FeatureItem 接口
    ├── 2.2 编写 create_empty 测试      ├── 4.2 更新 RequirementDoc
    │         ↓                         └── 4.3 更新 fixture
    ├── 2.3 实现 7段渲染                       ↓
    ├── 2.4 实现 create_empty          Phase 5 (前端组件)
    └── 2.5 验证测试                        ├── 5.1 编写新段落测试
              ↓                              ├── 5.2 实现范围两列
Phase 3 (动态模板)                          ├── 5.3 实现 features 表格
    ├── 3.1 编写 generate_template 测试     ├── 5.4 实现已确认列表
    ├── 3.2 实现 generate_template          └── 5.5 验证测试
    ├── 3.3 更新 STAGE_CLARIFY_PROMPT             ↓
    ├── 3.4 更新 TEST_DESIGN_TEMPLATES      Phase 6 (集成验证)
    ├── 3.5 删除旧模板                          ├── 6.1 pytest
    └── 3.6 更新 prompt 测试                    ├── 6.2 npm test
                                                └── 6.3 lint
```

---

## 📁 涉及文件清单

| 文件 | 操作 | 变更内容 |
|------|------|----------|
| `backend/agents/lisa/artifact_models.py` | 修改 | 新增 FeatureItem，扩展 RequirementDoc |
| `backend/agents/lisa/utils/markdown_generator.py` | 修改 | 7段渲染 + create_empty_requirement_doc |
| `backend/agents/lisa/prompts/artifacts.py` | 修改 | 新增 generate_requirement_template，删除旧模板 |
| `backend/agents/lisa/prompts/workflows/test_design.py` | 修改 | STAGE_CLARIFY_PROMPT 使用动态模板 |
| `backend/agents/lisa/nodes/reasoning_node.py` | 修改 | TEST_DESIGN_TEMPLATES outline 改用动态生成 |
| `backend/tests/test_artifact_models.py` | 修改 | 新增 FeatureItem 和新字段测试 |
| `backend/tests/agents/lisa/utils/test_markdown_generator.py` | 修改 | 7段结构测试 |
| `backend/tests/test_prompts_artifacts.py` | 修改 | 更新为动态模板测试 |
| `frontend/src/types/artifact.ts` | 修改 | 新增 FeatureItem 接口，扩展 RequirementDoc |
| `frontend/src/components/artifact/StructuredRequirementView.tsx` | 修改 | 7段渲染 |
| `frontend/src/__tests__/components/ArtifactRenderer.test.tsx` | 修改 | 新段落测试 |

---

## 🔧 Phase 1: 后端模型扩展 (TDD)

### Task 1.1: 编写 FeatureItem 模型测试

**Files:**
- Modify: `tools/ai-agents/backend/tests/test_artifact_models.py`

**Step 1: 添加 FeatureItem 测试类**

```python
class TestFeatureItem:
    """功能项模型测试"""

    def test_feature_item_basic_creation(self):
        """测试基本创建"""
        from backend.agents.lisa.artifact_models import FeatureItem
        item = FeatureItem(
            id="F1",
            name="用户登录",
            desc="用户使用账号密码登录系统",
            acceptance=["能正常登录", "错误时显示提示"],
            priority="P0"
        )
        assert item.id == "F1"
        assert len(item.acceptance) == 2
        assert item.priority == "P0"

    def test_feature_item_acceptance_is_list(self):
        """验收标准必须是列表"""
        from backend.agents.lisa.artifact_models import FeatureItem
        item = FeatureItem(
            id="F1", name="功能", desc="描述",
            acceptance=["标准1", "标准2", "标准3"],
            priority="P1"
        )
        assert isinstance(item.acceptance, list)
        assert len(item.acceptance) == 3
```

**Step 2: 运行测试验证失败**

Run: `pytest tools/ai-agents/backend/tests/test_artifact_models.py::TestFeatureItem -v`
Expected: FAIL - `FeatureItem` 未定义

---

### Task 1.2: 编写 RequirementDoc 新字段测试

**Files:**
- Modify: `tools/ai-agents/backend/tests/test_artifact_models.py`

**Step 1: 添加新字段测试类**

```python
class TestRequirementDocNewFields:
    """RequirementDoc 新字段测试"""

    def test_out_of_scope_field(self):
        """测试 out_of_scope 字段"""
        from backend.agents.lisa.artifact_models import RequirementDoc
        doc = RequirementDoc(
            scope=["登录功能"],
            out_of_scope=["注册功能", "找回密码"],
            flow_mermaid="graph TD; A-->B",
        )
        assert len(doc.out_of_scope) == 2
        assert "注册功能" in doc.out_of_scope

    def test_out_of_scope_default_empty(self):
        """out_of_scope 默认为空列表"""
        from backend.agents.lisa.artifact_models import RequirementDoc
        doc = RequirementDoc(
            scope=["登录"],
            flow_mermaid="graph TD; A-->B",
        )
        assert doc.out_of_scope == []

    def test_features_field(self):
        """测试 features 字段"""
        from backend.agents.lisa.artifact_models import RequirementDoc, FeatureItem
        doc = RequirementDoc(
            scope=["登录"],
            flow_mermaid="graph TD; A-->B",
            features=[
                FeatureItem(
                    id="F1", name="登录", desc="描述",
                    acceptance=["标准1"], priority="P0"
                )
            ],
        )
        assert len(doc.features) == 1
        assert doc.features[0].name == "登录"

    def test_backward_compatibility(self):
        """向后兼容：不提供新字段也能创建"""
        from backend.agents.lisa.artifact_models import RequirementDoc
        doc = RequirementDoc(
            scope=["测试"],
            flow_mermaid="graph TD; A-->B",
            rules=[],
            assumptions=[],
        )
        assert doc.out_of_scope == []
        assert doc.features == []
```

**Step 2: 运行测试验证失败**

Run: `pytest tools/ai-agents/backend/tests/test_artifact_models.py::TestRequirementDocNewFields -v`
Expected: FAIL - 字段未定义

---

### Task 1.3: 实现 FeatureItem 模型

**Files:**
- Modify: `tools/ai-agents/backend/agents/lisa/artifact_models.py`

**Step 1: 在 RuleItem 之后添加 FeatureItem**

```python
class FeatureItem(BaseModel):
    """功能项"""
    
    id: str = Field(description="功能唯一标识，如 F1, F2")
    name: str = Field(description="功能名称")
    desc: str = Field(description="功能描述")
    acceptance: List[str] = Field(description="验收标准列表")
    priority: Priority = Field(description="优先级：P0/P1/P2/P3")
```

**Step 2: 运行测试验证通过**

Run: `pytest tools/ai-agents/backend/tests/test_artifact_models.py::TestFeatureItem -v`
Expected: PASS

---

### Task 1.4: 更新 RequirementDoc 模型

**Files:**
- Modify: `tools/ai-agents/backend/agents/lisa/artifact_models.py`

**Step 1: 在 RequirementDoc 中添加新字段**

```python
class RequirementDoc(BaseModel):
    """Phase 1 产出物：需求分析文档"""

    scope: List[str] = Field(description="测试范围列表")
    out_of_scope: List[str] = Field(
        default_factory=list, description="范围外内容列表"
    )
    scope_mermaid: Optional[str] = Field(
        default=None, description="需求全景图 Mermaid Mindmap 代码"
    )
    features: List[FeatureItem] = Field(
        default_factory=list, description="功能详细规格列表"
    )
    flow_mermaid: str = Field(description="业务流程 Mermaid 代码")
    rules: List[RuleItem] = Field(default_factory=list, description="核心规则列表")
    assumptions: List[AssumptionItem] = Field(
        default_factory=list, description="待确认/假设列表"
    )
    nfr_markdown: Optional[str] = Field(
        default=None, description="非功能需求 Markdown"
    )
```

**Step 2: 运行测试验证通过**

Run: `pytest tools/ai-agents/backend/tests/test_artifact_models.py::TestRequirementDocNewFields -v`
Expected: PASS

---

### Task 1.5: 验证现有测试不回归

**Step 1: 运行所有模型测试**

Run: `pytest tools/ai-agents/backend/tests/test_artifact_models.py -v`
Expected: ALL PASS

**Step 2: Commit**

```bash
git add tools/ai-agents/backend/agents/lisa/artifact_models.py tools/ai-agents/backend/tests/test_artifact_models.py
git commit -m "feat(lisa): add FeatureItem model and extend RequirementDoc with out_of_scope and features fields"
```

---

## 🔧 Phase 2: Markdown 渲染逻辑 (TDD)

### Task 2.1: 编写 7 段结构测试

**Files:**
- Modify: `tools/ai-agents/backend/tests/agents/lisa/utils/test_markdown_generator.py`

**Step 1: 添加 7 段结构测试**

```python
class TestConvertRequirementDoc7Sections:
    """测试 7 段结构渲染"""

    def test_section_1_scope_with_out_of_scope(self):
        """第1段：测试范围包含范围内和范围外"""
        content = {
            "scope": ["登录功能", "注销功能"],
            "out_of_scope": ["注册功能"],
            "flow_mermaid": "",
        }
        result = convert_to_markdown(content, "requirement")
        assert "## 1. 测试范围" in result
        assert "### 范围内" in result
        assert "### 范围外" in result
        assert "登录功能" in result
        assert "注册功能" in result

    def test_section_2_features_table(self):
        """第2段：功能详细规格表格"""
        content = {
            "scope": ["测试"],
            "flow_mermaid": "",
            "features": [
                {
                    "id": "F1",
                    "name": "登录",
                    "desc": "用户登录",
                    "acceptance": ["能登录", "有提示"],
                    "priority": "P0",
                }
            ],
        }
        result = convert_to_markdown(content, "requirement")
        assert "## 2. 功能详细规格" in result
        assert "| F1 |" in result
        assert "登录" in result
        assert "能登录" in result

    def test_section_3_rules_table(self):
        """第3段：核心业务规则"""
        content = {
            "scope": ["测试"],
            "flow_mermaid": "",
            "rules": [{"id": "R1", "desc": "密码不能为空", "source": "user"}],
        }
        result = convert_to_markdown(content, "requirement")
        assert "## 3. 核心业务规则" in result
        assert "R1" in result

    def test_section_7_confirmed_from_assumptions(self):
        """第7段：已确认信息从 assumptions 过滤"""
        content = {
            "scope": ["测试"],
            "flow_mermaid": "",
            "assumptions": [
                {"id": "Q1", "question": "问题1", "status": "pending", "priority": "P0"},
                {"id": "Q2", "question": "问题2", "status": "confirmed", "note": "答案"},
            ],
        }
        result = convert_to_markdown(content, "requirement")
        assert "## 6. 待澄清问题" in result
        assert "## 7. 已确认信息" in result
        # Q2 应该在已确认信息段落
        section_7 = result.split("## 7.")[1] if "## 7." in result else ""
        assert "Q2" in section_7
        assert "答案" in section_7

    def test_all_7_sections_present(self):
        """验证所有7段都存在"""
        content = {
            "scope": ["测试"],
            "out_of_scope": [],
            "features": [],
            "flow_mermaid": "graph TD; A-->B",
            "rules": [],
            "assumptions": [],
            "nfr_markdown": "性能要求",
        }
        result = convert_to_markdown(content, "requirement")
        assert "## 1. 测试范围" in result
        assert "## 2. 功能详细规格" in result
        assert "## 3. 核心业务规则" in result
        assert "## 4. 业务流程图" in result
        assert "## 5. 非功能需求" in result
        assert "## 6. 待澄清问题" in result
        assert "## 7. 已确认信息" in result
```

**Step 2: 运行测试验证失败**

Run: `pytest tools/ai-agents/backend/tests/agents/lisa/utils/test_markdown_generator.py::TestConvertRequirementDoc7Sections -v`
Expected: FAIL - 新段落结构未实现

---

### Task 2.2: 编写 create_empty_requirement_doc 测试

**Files:**
- Modify: `tools/ai-agents/backend/tests/agents/lisa/utils/test_markdown_generator.py`

**Step 1: 添加 create_empty 测试**

```python
class TestCreateEmptyRequirementDoc:
    """测试空文档创建"""

    def test_returns_requirement_doc(self):
        """返回 RequirementDoc 实例"""
        from backend.agents.lisa.utils.markdown_generator import create_empty_requirement_doc
        from backend.agents.lisa.artifact_models import RequirementDoc
        doc = create_empty_requirement_doc()
        assert isinstance(doc, RequirementDoc)

    def test_all_lists_empty(self):
        """所有列表字段为空"""
        from backend.agents.lisa.utils.markdown_generator import create_empty_requirement_doc
        doc = create_empty_requirement_doc()
        assert doc.scope == []
        assert doc.out_of_scope == []
        assert doc.features == []
        assert doc.rules == []
        assert doc.assumptions == []

    def test_converts_to_markdown(self):
        """能正确转换为 Markdown"""
        from backend.agents.lisa.utils.markdown_generator import create_empty_requirement_doc, convert_to_markdown
        doc = create_empty_requirement_doc()
        result = convert_to_markdown(doc.model_dump(), "requirement")
        assert "## 1. 测试范围" in result
```

**Step 2: 运行测试验证失败**

Run: `pytest tools/ai-agents/backend/tests/agents/lisa/utils/test_markdown_generator.py::TestCreateEmptyRequirementDoc -v`
Expected: FAIL - 函数未定义

---

### Task 2.3: 实现 7 段渲染逻辑

**Files:**
- Modify: `tools/ai-agents/backend/agents/lisa/utils/markdown_generator.py`

**Step 1: 重写 convert_requirement_doc 函数**

完整代码见 Plan Agent 输出中的 `convert_requirement_doc` 实现。

**Step 2: 运行测试验证通过**

Run: `pytest tools/ai-agents/backend/tests/agents/lisa/utils/test_markdown_generator.py::TestConvertRequirementDoc7Sections -v`
Expected: PASS

---

### Task 2.4: 实现 create_empty_requirement_doc

**Files:**
- Modify: `tools/ai-agents/backend/agents/lisa/utils/markdown_generator.py`

**Step 1: 添加函数**

```python
from ..artifact_models import RequirementDoc

def create_empty_requirement_doc() -> RequirementDoc:
    """创建空的 RequirementDoc 结构，用于初始化模板"""
    return RequirementDoc(
        scope=[],
        out_of_scope=[],
        scope_mermaid=None,
        features=[],
        flow_mermaid="",
        rules=[],
        assumptions=[],
        nfr_markdown=None,
    )
```

**Step 2: 运行测试验证通过**

Run: `pytest tools/ai-agents/backend/tests/agents/lisa/utils/test_markdown_generator.py::TestCreateEmptyRequirementDoc -v`
Expected: PASS

---

### Task 2.5: 验证所有渲染测试

**Step 1: 运行所有 markdown_generator 测试**

Run: `pytest tools/ai-agents/backend/tests/agents/lisa/utils/test_markdown_generator.py -v`
Expected: ALL PASS

**Step 2: Commit**

```bash
git add tools/ai-agents/backend/agents/lisa/utils/markdown_generator.py tools/ai-agents/backend/tests/agents/lisa/utils/test_markdown_generator.py
git commit -m "feat(lisa): implement 7-section markdown rendering and create_empty_requirement_doc"
```

---

## 🔧 Phase 3: 动态模板生成 (TDD)

### Task 3.1: 编写 generate_requirement_template 测试

**Files:**
- Modify: `tools/ai-agents/backend/tests/test_prompts_artifacts.py`

**Step 1: 替换旧测试为新测试**

```python
from backend.agents.lisa.prompts.artifacts import (
    generate_requirement_template,
    get_artifact_json_schemas,
)


class TestGenerateRequirementTemplate:
    """测试动态模板生成"""

    def test_returns_string(self):
        """返回字符串"""
        result = generate_requirement_template()
        assert isinstance(result, str)

    def test_contains_all_7_sections(self):
        """包含所有7个段落标题"""
        result = generate_requirement_template()
        assert "## 1. 测试范围" in result
        assert "## 2. 功能详细规格" in result
        assert "## 3. 核心业务规则" in result
        assert "## 4. 业务流程图" in result
        assert "## 5. 非功能需求" in result
        assert "## 6. 待澄清问题" in result
        assert "## 7. 已确认信息" in result

    def test_schema_sync_with_model(self):
        """Schema 与模型同步"""
        schemas = get_artifact_json_schemas()
        req_schema = schemas["requirement"]
        props = req_schema.get("properties", {})
        assert "out_of_scope" in props
        assert "features" in props
```

**Step 2: 运行测试验证失败**

Run: `pytest tools/ai-agents/backend/tests/test_prompts_artifacts.py::TestGenerateRequirementTemplate -v`
Expected: FAIL - 函数未定义

---

### Task 3.2: 实现 generate_requirement_template

**Files:**
- Modify: `tools/ai-agents/backend/agents/lisa/prompts/artifacts.py`

**Step 1: 添加函数**

```python
def generate_requirement_template() -> str:
    """
    动态生成需求分析文档模板
    
    从 Pydantic 模型生成，保持 SSOT 原则
    """
    from ..utils.markdown_generator import create_empty_requirement_doc, convert_to_markdown
    
    example_doc = create_empty_requirement_doc()
    template_md = convert_to_markdown(example_doc.model_dump(), "requirement")
    
    return f"""
# 需求分析文档

> 文档结构说明：本文档包含 7 个核心段落，按以下顺序组织。

{template_md}

---
> 提示：使用 `UpdateStructuredArtifact` 工具更新时，请确保 content 字段符合 RequirementDoc JSON Schema。
"""
```

**Step 2: 运行测试验证通过**

Run: `pytest tools/ai-agents/backend/tests/test_prompts_artifacts.py::TestGenerateRequirementTemplate -v`
Expected: PASS

---

### Task 3.3-3.4: 更新 Prompt 和 Templates

**Files:**
- Modify: `tools/ai-agents/backend/agents/lisa/prompts/workflows/test_design.py`
- Modify: `tools/ai-agents/backend/agents/lisa/nodes/reasoning_node.py`

详细代码见 Plan Agent 输出。

---

### Task 3.5: 删除旧模板

**Files:**
- Modify: `tools/ai-agents/backend/agents/lisa/prompts/artifacts.py`

**Step 1: 删除 ARTIFACT_CLARIFY_REQUIREMENTS 变量定义**

---

### Task 3.6: 更新相关测试

**Files:**
- Modify: `tools/ai-agents/backend/tests/test_prompts_artifacts.py`

**Step 1: 删除引用旧模板的测试**

**Step 2: 运行所有测试验证**

Run: `pytest tools/ai-agents/backend/tests/test_prompts_artifacts.py -v`
Expected: ALL PASS

**Step 3: Commit**

```bash
git add tools/ai-agents/backend/agents/lisa/prompts/ tools/ai-agents/backend/agents/lisa/nodes/reasoning_node.py tools/ai-agents/backend/tests/test_prompts_artifacts.py
git commit -m "feat(lisa): replace static template with dynamic generate_requirement_template"
```

---

## 🔧 Phase 4: 前端类型同步

### Task 4.1-4.2: 更新 TypeScript 类型

**Files:**
- Modify: `tools/ai-agents/frontend/src/types/artifact.ts`

**Step 1: 添加 FeatureItem 接口**

```typescript
export interface FeatureItem {
  id: string;
  name: string;
  desc: string;
  acceptance: string[];
  priority: Priority;
}
```

**Step 2: 更新 RequirementDoc 接口**

```typescript
export interface RequirementDoc {
  scope: string[];
  out_of_scope?: string[];
  scope_mermaid?: string | null;
  features?: FeatureItem[];
  flow_mermaid: string;
  rules: RuleItem[];
  assumptions: AssumptionItem[];
  nfr_markdown?: string | null;
}
```

**Step 3: Commit**

```bash
git add tools/ai-agents/frontend/src/types/artifact.ts
git commit -m "feat(frontend): add FeatureItem interface and extend RequirementDoc type"
```

---

## 🔧 Phase 5: 前端组件渲染

### Task 5.1-5.4: 更新 StructuredRequirementView

**Files:**
- Modify: `tools/ai-agents/frontend/src/components/artifact/StructuredRequirementView.tsx`

详细代码见 Plan Agent 输出。

**Step 1: 运行前端测试**

Run: `cd tools/ai-agents/frontend && npm run test`
Expected: ALL PASS

**Step 2: Commit**

```bash
git add tools/ai-agents/frontend/src/components/artifact/
git commit -m "feat(frontend): implement 7-section rendering in StructuredRequirementView"
```

---

## 🔧 Phase 6: 集成验证

### Task 6.1: 全量后端测试

Run: `pytest tools/ai-agents/backend/tests/ -v`
Expected: ALL PASS

### Task 6.2: 前端测试

Run: `cd tools/ai-agents/frontend && npm run test`
Expected: ALL PASS

### Task 6.3: Lint 检查

Run: `flake8 tools/ai-agents/backend/agents/lisa/ --select=E9,F63,F7,F82`
Expected: No errors

Run: `cd tools/ai-agents/frontend && npm run lint`
Expected: No errors

### Task 6.4: 部署验证

Run: `./scripts/dev/deploy-dev.sh`
Expected: 健康检查通过

---

## ⏱️ 估算工作量

| Phase | 任务数 | 预估时间 |
|-------|--------|----------|
| Phase 1: 后端模型 | 5 | 30 min |
| Phase 2: Markdown 渲染 | 5 | 45 min |
| Phase 3: 动态模板 | 6 | 30 min |
| Phase 4: 前端类型 | 3 | 15 min |
| Phase 5: 前端组件 | 5 | 45 min |
| Phase 6: 集成验证 | 4 | 15 min |
| **总计** | **28** | **~3 小时** |

---

## ✅ 完成标准 (Definition of Done)

- [ ] 所有新测试通过 (`pytest` + `npm run test`)
- [ ] 所有现有测试通过 (无回归)
- [ ] Lint 无错误
- [ ] 产出物内容全部使用中文
- [ ] Docker 部署健康检查通过
