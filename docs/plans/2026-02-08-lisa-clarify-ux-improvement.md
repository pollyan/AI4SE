# Lisa 澄清阶段 UX 改进实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 改进 Lisa 智能体在需求澄清阶段的用户体验，解决待澄清问题展示、产出物更新时机和增量渲染三个核心问题。

**Architecture:** 分三阶段实施：Phase 1 仅调整 Prompt 改进对话交互；Phase 2 修复产出物更新逻辑确保状态同步；Phase 3 实现前后端增量更新 + Diff 高亮渲染。

**Tech Stack:** Python (LangGraph/LangChain), TypeScript/React, Pydantic, Markdown 渲染

---

## 需求摘要

| # | 问题 | 期望行为 |
|---|------|----------|
| 1 | 待澄清问题只在产出物中，对话框没有 | 对话框中用摘要式展示 + 混合模式引导（列出所有 P0，主动追问第一个） |
| 2 | 用户回答后产出物不更新 | 有实质变化时立即更新；问题保留原位标记状态 + "已确认信息"新增记录 |
| 3 | 产出物渲染时先清空再显示 | 增量更新 + 行级高亮 + 侧边标记，高亮保持到下一轮对话开始 |

---

## Phase 1: 对话框中展示待澄清问题

**目标:** 让 Lisa 在对话中用摘要式展示待澄清问题，并用混合模式引导用户回答。

**改动范围:** 仅 Prompt 调整，无代码改动。

### Task 1.1: 更新 STAGE_CLARIFY_PROMPT 响应模板

**Files:**
- Modify: `tools/ai-agents/backend/agents/lisa/prompts/workflows/test_design.py:173-197`

**Step 1: 阅读现有 Prompt**

确认现有的场景 B 模板内容，理解当前结构。

**Step 2: 修改场景 B 模板**

将 `STAGE_CLARIFY_PROMPT` 中"响应模板"的"场景 B"替换为以下内容：

```python
**场景 B：用户上传了需求文档**

当用户上传文件时，分析完成后按以下格式回复：

1. 简要总结被测对象和范围（1-2 句话）
2. 摘要式说明问题数量："我发现了 X 个需要确认的问题，其中 Y 个是阻塞性的（P0）"
3. 列出所有 P0 问题（编号 + 问题描述）
4. 主动追问第一个 P0 问题，引导用户回答
5. 提示用户可以用 "Q1: xxx" 格式一次回答多个，或直接回答当前问题

**示例风格**（供参考，不必照搬）：
> "看完文档了，这是一个登录功能的测试需求。
>
> 我发现了 6 个需要确认的问题，其中 3 个是 P0 阻塞性的：
>
> - Q1: 登录失败锁定后，解锁机制是什么？自动还是人工？
> - Q2: 密码强度规则有哪些具体要求？
> - Q3: 是否需要支持"记住我"功能？
>
> 先说 Q1 吧——用户被锁定后，是等待一段时间自动解锁，还是需要联系管理员处理？"

**CRITICAL**: 
- 必须在对话中列出所有 P0 问题，不能只说"请查看右侧文档"
- 必须主动追问第一个问题，不能只是罗列等用户自己选
- 用户回答后，自然确认并追问下一个未解决的 P0 问题
```

**Step 3: 运行 lint 检查**

Run: `flake8 tools/ai-agents/backend/agents/lisa/prompts/workflows/test_design.py --select=E9,F63,F7,F82`
Expected: 无错误输出

**Step 4: 手动测试**

1. 启动开发环境: `./scripts/dev/deploy-dev.sh`
2. 访问 http://localhost/ai-agents
3. 选择 Lisa，发送"我想测试一个登录功能"
4. 验证 Lisa 的回复包含：摘要 + P0 问题列表 + 主动追问

**Step 5: Commit**

```bash
git add tools/ai-agents/backend/agents/lisa/prompts/workflows/test_design.py
git commit -m "feat(lisa): 改进 clarify 阶段对话交互，摘要式展示 P0 问题并主动引导"
```

---

## Phase 2: 确保用户回答后产出物更新

**目标:** 修复用户回答问题后产出物不更新的问题，确保问题状态正确同步。

**改动范围:** Prompt 强化 + 可能的代码修复。

### Task 2.1: 强化 should_update_artifact 判断逻辑

**Files:**
- Modify: `tools/ai-agents/backend/agents/lisa/prompts/workflows/test_design.py:74-87`

**Step 1: 阅读现有 should_update_artifact 指导**

确认 `WORKFLOW_TEST_DESIGN_SYSTEM` 中关于 `should_update_artifact` 的现有指导。

**Step 2: 强化更新触发条件**

在 "产出物更新原则" 部分添加更明确的触发规则：

```python
## 产出物更新原则 (Universal Artifact Update Principles)

1. **增量丰富 (Incremental Enrichment)**:
    - 随着对话进展，不断丰富产出物内容。
    - 每次认为有实质性进展时，应触发更新。

2. **拒绝口头空谈 (No "Thought-Only" Confirmations)**:
    - 任何属于文档范畴的信息（需求、风险、用例），必须触发 `should_update_artifact=True`。

3. **问题回答即更新 (Answer = Update)**:
    - **CRITICAL**: 当用户回答了任何待澄清问题时，**必须**设置 `should_update_artifact=True`
    - 需要更新的内容：
      a. 将对应问题的 status 从 "pending" 改为 "confirmed"
      b. 在 assumptions 中添加 note 记录用户的回答
    - 即使用户只回答了一个问题，也必须触发更新

4. **保持已有内容 (Preserve Existing Content)**:
    - 更新产出物时，必须保留所有未变更的内容
    - 只修改/添加与本轮对话相关的部分
```

**Step 3: 运行 lint 检查**

Run: `flake8 tools/ai-agents/backend/agents/lisa/prompts/workflows/test_design.py --select=E9,F63,F7,F82`
Expected: 无错误输出

**Step 4: Commit**

```bash
git add tools/ai-agents/backend/agents/lisa/prompts/workflows/test_design.py
git commit -m "feat(lisa): 强化产出物更新触发条件，确保问题回答后立即同步"
```

### Task 2.2: 修复 'str' object has no attribute 'get' 错误

**Files:**
- Modify: `tools/ai-agents/backend/agents/lisa/utils/markdown_generator.py`
- Test: `tools/ai-agents/backend/tests/test_markdown_generator.py` (新建)

**Step 1: 编写失败测试**

创建测试文件 `tools/ai-agents/backend/tests/test_markdown_generator.py`:

```python
import pytest
from backend.agents.lisa.utils.markdown_generator import convert_to_markdown, convert_requirement_doc


class TestConvertRequirementDoc:
    """测试 RequirementDoc 转 Markdown"""

    def test_handles_string_assumptions(self):
        """当 assumptions 是字符串列表时应正确处理"""
        content = {
            "scope": ["登录功能"],
            "flow_mermaid": "graph TD\n  A-->B",
            "assumptions": ["问题1", "问题2"]  # 字符串列表，非对象列表
        }
        result = convert_requirement_doc(content)
        assert "问题1" in result
        assert "问题2" in result

    def test_handles_dict_assumptions(self):
        """当 assumptions 是对象列表时应正确处理"""
        content = {
            "scope": ["登录功能"],
            "flow_mermaid": "graph TD\n  A-->B",
            "assumptions": [
                {"id": "Q1", "question": "问题1", "priority": "P0", "status": "pending"},
                {"id": "Q2", "question": "问题2", "priority": "P1", "status": "confirmed", "note": "答案"}
            ]
        }
        result = convert_requirement_doc(content)
        assert "Q1" in result
        assert "问题1" in result
        assert "P0" in result or "阻塞" in result

    def test_handles_empty_assumptions(self):
        """空 assumptions 应返回 (无)"""
        content = {
            "scope": ["登录功能"],
            "flow_mermaid": "graph TD\n  A-->B",
            "assumptions": []
        }
        result = convert_requirement_doc(content)
        assert "(无)" in result

    def test_handles_mixed_content(self):
        """混合内容时不应崩溃"""
        content = {
            "scope": "登录功能",  # 字符串而非列表
            "flow_mermaid": "graph TD\n  A-->B",
            "rules": "规则描述",  # 字符串而非列表
            "assumptions": [{"id": "Q1", "question": "问题", "status": "pending"}]
        }
        # 不应抛出异常
        result = convert_requirement_doc(content)
        assert isinstance(result, str)
```

**Step 2: 运行测试验证失败**

Run: `pytest tools/ai-agents/backend/tests/test_markdown_generator.py -v`
Expected: 部分测试可能失败（取决于现有实现的健壮性）

**Step 3: 修复 markdown_generator.py**

检查 `convert_requirement_doc` 函数中所有 `.get()` 调用，添加类型检查：

```python
def convert_requirement_doc(content: Dict[str, Any]) -> str:
    """
    将 RequirementDoc 结构转换为符合 ARTIFACT_CLARIFY_REQUIREMENTS 模板的 Markdown
    兼容 strict schema (objects) 和 simplified schema (strings)
    """
    md = ["# 需求分析文档\n"]
    
    # ... 现有代码 ...
    
    # 5 & 6. 待澄清问题 & 已确认信息 (Assumptions)
    assumptions = content.get("assumptions", [])
    pending = []
    confirmed = []
    
    if isinstance(assumptions, list) and assumptions:
        for a in assumptions:
            if isinstance(a, dict):
                # Schema: AssumptionItem(id, question, status, note)
                if a.get('status') == 'confirmed':
                    confirmed.append(a)
                else:
                    pending.append(a)
            elif isinstance(a, str):
                # Fallback: 字符串直接作为 pending 问题
                pending.append({'id': '-', 'question': a, 'priority': 'P1', 'status': 'pending'})
            # 其他类型忽略
    
    # ... 后续渲染代码 ...
```

**Step 4: 运行测试验证通过**

Run: `pytest tools/ai-agents/backend/tests/test_markdown_generator.py -v`
Expected: 全部 PASS

**Step 5: 运行完整测试套件**

Run: `pytest tools/ai-agents/backend/tests/ -v --tb=short`
Expected: 无新增失败

**Step 6: Commit**

```bash
git add tools/ai-agents/backend/agents/lisa/utils/markdown_generator.py
git add tools/ai-agents/backend/tests/test_markdown_generator.py
git commit -m "fix(lisa): 修复 markdown_generator 处理字符串类型 assumptions 时的崩溃"
```

### Task 2.3: 验证产出物更新流程端到端

**Files:**
- 无新增文件，仅手动测试

**Step 1: 启动开发环境**

Run: `./scripts/dev/deploy-dev.sh`

**Step 2: 端到端测试场景**

1. 访问 http://localhost/ai-agents
2. 选择 Lisa，发送"我想测试一个登录功能"
3. Lisa 应返回 P0 问题列表
4. 回复"Q1: 失败5次锁定，24小时后自动解锁"
5. **验证**:
   - Lisa 的回复应确认收到答案并追问下一个问题
   - 右侧产出物应更新，Q1 状态变为"已确认"
   - "已确认信息"章节应出现 Q1 的答案

**Step 3: 记录测试结果**

如果仍有问题，记录具体现象以便后续修复。

---

## Phase 3: 增量更新 + Diff 高亮

**目标:** 实现产出物增量更新，避免清空闪烁，并用行级高亮 + 侧边标记展示变更。

**改动范围:** 后端 artifact_node 改为 patch 模式 + 前端 Diff 渲染。

### Task 3.1: 设计增量更新数据结构

**Files:**
- Create: `tools/ai-agents/backend/agents/lisa/artifact_patch.py` (已存在，需检查/扩展)
- Modify: `tools/ai-agents/backend/agents/lisa/schemas.py`

**Step 1: 阅读现有 artifact_patch.py**

检查是否已有 patch 相关逻辑。

**Step 2: 定义 Patch 操作类型**

在 `schemas.py` 中添加：

```python
from typing import Literal, List, Optional
from pydantic import BaseModel, Field


class ArtifactPatchOp(BaseModel):
    """单个产出物 Patch 操作"""
    
    op: Literal["update_field", "update_item", "add_item", "remove_item"] = Field(
        description="操作类型"
    )
    path: str = Field(
        description="JSON Path 风格的字段路径，如 'assumptions[0].status'"
    )
    value: Optional[Any] = Field(
        default=None,
        description="新值（update/add 操作需要）"
    )


class ArtifactPatch(BaseModel):
    """产出物增量更新请求"""
    
    key: str = Field(description="产出物 key")
    operations: List[ArtifactPatchOp] = Field(description="Patch 操作列表")
```

**Step 3: 运行 lint 检查**

Run: `flake8 tools/ai-agents/backend/agents/lisa/schemas.py --select=E9,F63,F7,F82`
Expected: 无错误

**Step 4: Commit**

```bash
git add tools/ai-agents/backend/agents/lisa/schemas.py
git commit -m "feat(lisa): 添加 ArtifactPatch 增量更新数据结构定义"
```

### Task 3.2: 实现后端 Patch 应用逻辑

**Files:**
- Modify: `tools/ai-agents/backend/agents/lisa/artifact_patch.py`
- Test: `tools/ai-agents/backend/tests/test_artifact_patch.py` (新建)

**Step 1: 编写失败测试**

```python
import pytest
from backend.agents.lisa.artifact_patch import apply_patch


class TestApplyPatch:
    """测试 Patch 应用逻辑"""

    def test_update_simple_field(self):
        """更新简单字段"""
        doc = {"title": "旧标题", "scope": ["功能1"]}
        patch = {
            "op": "update_field",
            "path": "title",
            "value": "新标题"
        }
        result = apply_patch(doc, [patch])
        assert result["title"] == "新标题"
        assert result["scope"] == ["功能1"]  # 未变

    def test_update_array_item_field(self):
        """更新数组元素的字段"""
        doc = {
            "assumptions": [
                {"id": "Q1", "status": "pending"},
                {"id": "Q2", "status": "pending"}
            ]
        }
        patch = {
            "op": "update_item",
            "path": "assumptions[0].status",
            "value": "confirmed"
        }
        result = apply_patch(doc, [patch])
        assert result["assumptions"][0]["status"] == "confirmed"
        assert result["assumptions"][1]["status"] == "pending"  # 未变

    def test_add_item_to_array(self):
        """向数组添加元素"""
        doc = {"assumptions": [{"id": "Q1"}]}
        patch = {
            "op": "add_item",
            "path": "assumptions",
            "value": {"id": "Q2", "status": "pending"}
        }
        result = apply_patch(doc, [patch])
        assert len(result["assumptions"]) == 2
        assert result["assumptions"][1]["id"] == "Q2"
```

**Step 2: 运行测试验证失败**

Run: `pytest tools/ai-agents/backend/tests/test_artifact_patch.py -v`
Expected: FAIL (函数未实现)

**Step 3: 实现 apply_patch 函数**

在 `artifact_patch.py` 中实现：

```python
import re
from typing import Dict, Any, List
from copy import deepcopy


def apply_patch(doc: Dict[str, Any], patches: List[Dict]) -> Dict[str, Any]:
    """
    应用 Patch 操作到文档
    
    Args:
        doc: 原始文档
        patches: Patch 操作列表
        
    Returns:
        更新后的文档（深拷贝，不修改原文档）
    """
    result = deepcopy(doc)
    
    for patch in patches:
        op = patch.get("op")
        path = patch.get("path", "")
        value = patch.get("value")
        
        if op == "update_field":
            _set_value_at_path(result, path, value)
        elif op == "update_item":
            _set_value_at_path(result, path, value)
        elif op == "add_item":
            arr = _get_value_at_path(result, path)
            if isinstance(arr, list):
                arr.append(value)
        elif op == "remove_item":
            # 实现略
            pass
            
    return result


def _parse_path(path: str) -> List[str]:
    """解析路径为段列表，如 'assumptions[0].status' -> ['assumptions', '0', 'status']"""
    # 将 [n] 转换为 .n
    normalized = re.sub(r'\[(\d+)\]', r'.\1', path)
    return [p for p in normalized.split('.') if p]


def _get_value_at_path(doc: Dict, path: str) -> Any:
    """获取路径对应的值"""
    segments = _parse_path(path)
    current = doc
    for seg in segments:
        if seg.isdigit():
            current = current[int(seg)]
        else:
            current = current.get(seg)
        if current is None:
            return None
    return current


def _set_value_at_path(doc: Dict, path: str, value: Any) -> None:
    """设置路径对应的值"""
    segments = _parse_path(path)
    current = doc
    for seg in segments[:-1]:
        if seg.isdigit():
            current = current[int(seg)]
        else:
            if seg not in current:
                current[seg] = {}
            current = current[seg]
    
    last_seg = segments[-1]
    if last_seg.isdigit():
        current[int(last_seg)] = value
    else:
        current[last_seg] = value
```

**Step 4: 运行测试验证通过**

Run: `pytest tools/ai-agents/backend/tests/test_artifact_patch.py -v`
Expected: 全部 PASS

**Step 5: Commit**

```bash
git add tools/ai-agents/backend/agents/lisa/artifact_patch.py
git add tools/ai-agents/backend/tests/test_artifact_patch.py
git commit -m "feat(lisa): 实现产出物增量 Patch 应用逻辑"
```

### Task 3.3: 前端 Diff 高亮组件

**Files:**
- Create: `tools/ai-agents/frontend/components/DiffHighlight.tsx`
- Modify: `tools/ai-agents/frontend/components/ArtifactPanel.tsx`
- Test: `tools/ai-agents/frontend/tests/DiffHighlight.test.tsx`

**Step 1: 设计 Diff 高亮组件接口**

```typescript
interface DiffHighlightProps {
  content: string;           // 当前 Markdown 内容
  previousContent?: string;  // 上一版本内容（用于计算 diff）
  showDiff: boolean;         // 是否显示 diff 高亮
}
```

**Step 2: 编写失败测试**

创建 `tools/ai-agents/frontend/tests/DiffHighlight.test.tsx`:

```typescript
import { render, screen } from '@testing-library/react';
import { DiffHighlight } from '../components/DiffHighlight';

describe('DiffHighlight', () => {
  it('renders content without diff when showDiff is false', () => {
    render(
      <DiffHighlight 
        content="# 标题\n\n内容" 
        showDiff={false} 
      />
    );
    expect(screen.getByText('标题')).toBeInTheDocument();
    // 不应有高亮样式
  });

  it('highlights changed lines when showDiff is true', () => {
    render(
      <DiffHighlight 
        content="# 标题\n\n新内容" 
        previousContent="# 标题\n\n旧内容"
        showDiff={true} 
      />
    );
    // 新内容行应有高亮
    const newLine = screen.getByText('新内容');
    expect(newLine.closest('.diff-added')).toBeInTheDocument();
  });

  it('shows side marker for changed lines', () => {
    render(
      <DiffHighlight 
        content="# 标题\n\n新内容" 
        previousContent="# 标题\n\n旧内容"
        showDiff={true} 
      />
    );
    // 应有侧边标记
    expect(document.querySelector('.diff-marker')).toBeInTheDocument();
  });
});
```

**Step 3: 运行测试验证失败**

Run: `cd tools/ai-agents/frontend && npm run test -- --run DiffHighlight`
Expected: FAIL (组件未创建)

**Step 4: 实现 DiffHighlight 组件**

创建 `tools/ai-agents/frontend/components/DiffHighlight.tsx`:

```typescript
import React, { useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import { diffLines } from 'diff';

interface DiffHighlightProps {
  content: string;
  previousContent?: string;
  showDiff: boolean;
}

export const DiffHighlight: React.FC<DiffHighlightProps> = ({
  content,
  previousContent,
  showDiff
}) => {
  const diffResult = useMemo(() => {
    if (!showDiff || !previousContent) {
      return null;
    }
    return diffLines(previousContent, content);
  }, [content, previousContent, showDiff]);

  if (!showDiff || !diffResult) {
    return <ReactMarkdown>{content}</ReactMarkdown>;
  }

  // 渲染带高亮的内容
  return (
    <div className="diff-container">
      {diffResult.map((part, index) => {
        if (part.removed) {
          return null; // 不显示删除的内容
        }
        
        const className = part.added ? 'diff-added' : '';
        const lines = part.value.split('\n');
        
        return (
          <div key={index} className={`diff-block ${className}`}>
            {part.added && <div className="diff-marker" />}
            <ReactMarkdown>{part.value}</ReactMarkdown>
          </div>
        );
      })}
    </div>
  );
};
```

**Step 5: 添加 CSS 样式**

在相关 CSS 文件中添加：

```css
.diff-container {
  position: relative;
}

.diff-block {
  position: relative;
}

.diff-added {
  background-color: rgba(46, 160, 67, 0.15);
}

.diff-marker {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  background-color: #2ea043;
}
```

**Step 6: 运行测试验证通过**

Run: `cd tools/ai-agents/frontend && npm run test -- --run DiffHighlight`
Expected: 全部 PASS

**Step 7: Commit**

```bash
git add tools/ai-agents/frontend/components/DiffHighlight.tsx
git add tools/ai-agents/frontend/tests/DiffHighlight.test.tsx
git commit -m "feat(frontend): 添加 Diff 高亮组件，支持行级高亮和侧边标记"
```

### Task 3.4: 集成 Diff 高亮到 ArtifactPanel

**Files:**
- Modify: `tools/ai-agents/frontend/components/ArtifactPanel.tsx`
- Modify: `tools/ai-agents/frontend/CompactApp.tsx`

**Step 1: 修改 ArtifactPanel 接收 diff 相关 props**

```typescript
interface ArtifactPanelProps {
  // ... 现有 props
  previousContent?: string;  // 新增：上一版本内容
  showDiff?: boolean;        // 新增：是否显示 diff
}
```

**Step 2: 在 ArtifactPanel 中使用 DiffHighlight**

替换现有的 Markdown 渲染为 DiffHighlight 组件。

**Step 3: 修改 CompactApp 管理 previousContent 状态**

- 在每次产出物更新时，保存旧内容到 `previousContent`
- 在用户发送新消息时，清空 `showDiff` 状态

**Step 4: 运行构建检查**

Run: `cd tools/ai-agents/frontend && npm run build`
Expected: 无错误

**Step 5: 手动测试**

1. 启动开发环境
2. 与 Lisa 对话，观察产出物更新时的高亮效果
3. 发送新消息，验证高亮被清除

**Step 6: Commit**

```bash
git add tools/ai-agents/frontend/components/ArtifactPanel.tsx
git add tools/ai-agents/frontend/CompactApp.tsx
git commit -m "feat(frontend): 集成 Diff 高亮到产出物面板，用户新对话时清除高亮"
```

---

## 验收标准

### Phase 1 完成标准
- [ ] Lisa 在对话中用摘要式展示 P0 问题数量
- [ ] Lisa 列出所有 P0 问题并主动追问第一个
- [ ] 用户可以直接回答当前问题，也可以用 "Q1: xxx" 格式批量回答

### Phase 2 完成标准
- [ ] 用户回答问题后，产出物立即更新
- [ ] 问题状态从"待确认"变为"已确认"
- [ ] "已确认信息"章节新增对应记录
- [ ] 不再出现 `'str' object has no attribute 'get'` 错误

### Phase 3 完成标准
- [ ] 产出物更新时不再清空闪烁，而是增量更新
- [ ] 变更行有浅绿色背景高亮
- [ ] 变更行左侧有绿色竖条标记
- [ ] 高亮保持到用户发送下一条消息时自动清除

---

## 风险与备注

1. **Phase 3 工作量较大**：增量更新涉及前后端改动，可能需要拆分为更小的子任务
2. **LLM 行为不确定性**：Prompt 调整后 LLM 的响应可能仍有偏差，需要多轮测试调优
3. **Diff 库选型**：前端使用 `diff` 库进行行级比较，如果性能不佳可考虑其他方案
