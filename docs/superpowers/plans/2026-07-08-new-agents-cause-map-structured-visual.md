# ROOT_CAUSE cause-map 结构化视觉 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 `INCIDENT_REVIEW/ROOT_CAUSE` 的 `cause-map` 从表格型 `ai4se-visual` 升级为节点 / 边复杂图，并通过后端、前端 parser、前端组件、导出层和契约同步测试保护。

**Architecture:** 后端继续从结构化 `artifact_data.why_chain` 确定性生成视觉数据，但 `cause-map` 改为 `nodes/edges`。前端 `parseStructuredVisual()` 支持矩阵视觉和节点边视觉两个 shape，`StructuredVisual` 复用同一组件按 shape 分流渲染。共享 Agent Runtime、typed SSE、store、ArtifactPane 和 Mermaid repair 路径不新增 workflow 专属分支。

**Tech Stack:** Python 3.11, pytest, TypeScript 5.x, React 19, Vitest, Testing Library.

---

### Task 1: 写 RED 测试

**Files:**
- Modify: `tools/new-agents/backend/tests/test_artifact_data_renderers.py`
- Modify: `tools/new-agents/backend/tests/test_agent_contracts.py`
- Modify: `tools/new-agents/frontend/src/core/__tests__/structuredVisuals.test.ts`
- Modify: `tools/new-agents/frontend/src/components/__tests__/StructuredVisual.test.tsx`
- Modify: `tools/new-agents/frontend/src/core/__tests__/artifactExport.test.ts`
- Modify: `tools/new-agents/frontend/src/core/__tests__/docxExport.test.ts`
- Modify: `tools/new-agents/frontend/src/core/prompts/incident_review/root_cause.ts`

- [x] **Step 1: 增加后端 ai4se-visual block 提取 helper**

在 `test_artifact_data_renderers.py` 顶部 imports 后添加：

```python
import json
```

在 `_extract_mermaid_block()` 后添加：

```python
def _extract_ai4se_visual_block(markdown: str, visual_type: str) -> dict:
    for chunk in markdown.split("```ai4se-visual\n")[1:]:
        block = chunk.split("\n```", 1)[0]
        visual = json.loads(block)
        if visual.get("type") == visual_type:
            return visual
    raise AssertionError(f"ai4se-visual block not found: {visual_type}")
```

- [x] **Step 2: 增加后端 ROOT_CAUSE cause-map 节点边测试**

在 `test_render_partial_incident_root_cause_artifact_data_builds_formal_incremental_markdown_and_patch()` 的 `assert '"type": "cause-map"' ...` 后加入：

```python
    cause_map = _extract_ai4se_visual_block(
        why_output.artifact_update.markdown,
        "cause-map",
    )
    assert "columns" not in cause_map
    assert "rows" not in cause_map
    assert [node["id"] for node in cause_map["nodes"]] == [
        item["level"]
        for item in VALID_INCIDENT_ROOT_CAUSE_ARTIFACT_DATA["why_chain"]
    ]
    assert cause_map["edges"] == [
        {"source": "现象", "target": "Why-1", "label": "继续追问"},
        {"source": "Why-1", "target": "Why-2", "label": "继续追问"},
        {"source": "Why-2", "target": "Why-3", "label": "继续追问"},
    ]
```

Expected RED: fails because current renderer still emits `columns/rows` and no `nodes/edges`.

- [x] **Step 3: 增加前端 parser 节点边测试**

在 `structuredVisuals.test.ts` 添加：

```typescript
    it('parses cause-map visual blocks as node-edge graphs', () => {
        const result = parseStructuredVisual(JSON.stringify({
            type: 'cause-map',
            title: '5-Why 根因链路图',
            nodes: [
                {
                    id: 'Why-1',
                    label: 'Why-1',
                    title: '直接原因',
                    description: '发布前缺少关键路径回归门禁',
                    category: '流程',
                    evidence: '发布记录与测试记录',
                    confidence: '高',
                    status: '已确认',
                },
                {
                    id: 'Why-2',
                    label: 'Why-2',
                    title: '深层原因',
                    description: '回归策略没有覆盖高风险链路',
                },
            ],
            edges: [
                { source: 'Why-1', target: 'Why-2', label: '继续追问' },
            ],
        }));

        expect(result.valid).toBe(true);
        if (result.valid === false) throw new Error(result.message);
        expect(result.visual.kind).toBe('node-edge');
        if (result.visual.kind !== 'node-edge') throw new Error('expected node-edge visual');
        expect(result.visual.nodes.map(node => node.id)).toEqual(['Why-1', 'Why-2']);
        expect(result.visual.edges[0]).toEqual({
            source: 'Why-1',
            target: 'Why-2',
            label: '继续追问',
        });
    });

    it('rejects cause-map edges that reference missing nodes', () => {
        const result = parseStructuredVisual(JSON.stringify({
            type: 'cause-map',
            nodes: [
                { id: 'Why-1', label: 'Why-1', title: '直接原因' },
            ],
            edges: [
                { source: 'Why-1', target: 'Why-404', label: '继续追问' },
            ],
        }));

        expect(result).toEqual({
            valid: false,
            message: 'cause-map edge 引用了不存在的节点：Why-1 -> Why-404。',
        });
    });
```

Expected RED: fails because parser requires `columns/rows` for every visual type.

- [x] **Step 4: 增加前端组件非表格渲染测试**

在 `StructuredVisual.test.tsx` 添加：

```typescript
    it('renders cause-map node-edge JSON as a graph view instead of a table', () => {
        render(
            <StructuredVisual
                source={JSON.stringify({
                    type: 'cause-map',
                    title: '5-Why 根因链路图',
                    nodes: [
                        {
                            id: 'Why-1',
                            label: 'Why-1',
                            title: '直接原因',
                            description: '发布前缺少关键路径回归门禁',
                            category: '流程',
                            evidence: '发布记录与测试记录',
                            confidence: '高',
                            status: '已确认',
                        },
                        {
                            id: 'Why-2',
                            label: 'Why-2',
                            title: '深层原因',
                            description: '回归策略没有覆盖高风险链路',
                        },
                    ],
                    edges: [
                        { source: 'Why-1', target: 'Why-2', label: '继续追问' },
                    ],
                })}
            />
        );

        expect(screen.queryByRole('table')).toBeNull();
        expect(screen.getByRole('group', { name: '5-Why 根因链路图' })).toBeTruthy();
        expect(screen.getByText('Why-1')).toBeTruthy();
        expect(screen.getByText('发布前缺少关键路径回归门禁')).toBeTruthy();
        expect(screen.getByText('继续追问')).toBeTruthy();
        expect(screen.getByText('Why-1 -> Why-2')).toBeTruthy();
    });
```

Expected RED: fails because current component renders all valid visuals as a table.

- [x] **Step 5: 增加 prompt template 协议测试**

在 `structuredVisuals.test.ts` 添加文件读取 imports：

```typescript
import { ROOT_CAUSE_TEMPLATE } from '../../prompts/incident_review/root_cause';
```

添加测试：

```typescript
    it('keeps ROOT_CAUSE cause-map template on the node-edge protocol', () => {
        expect(ROOT_CAUSE_TEMPLATE).toContain('"type": "cause-map"');
        expect(ROOT_CAUSE_TEMPLATE).toContain('"nodes"');
        expect(ROOT_CAUSE_TEMPLATE).toContain('"edges"');
        expect(ROOT_CAUSE_TEMPLATE).not.toContain('"columns": ["层级", "问题", "回答"');
    });
```

Expected RED: fails because current template still uses `columns/rows`.

- [x] **Step 6: 增加导出层和后端 contract RED 测试**

在 `artifactExport.test.ts` 和 `docxExport.test.ts` 增加 `cause-map` node-edge fence，断言导出的 PDF / DOCX 可读文本包含标题、节点说明和 `source -> target` 连接，不泄漏原始 JSON。

在 `test_agent_contracts.py` 增加合法 `cause-map` node-edge 最小 fixture，并增加缺失节点引用拒绝测试。

- [x] **Step 7: 运行 RED**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_incident_root_cause_artifact_data_builds_formal_incremental_markdown_and_patch -q
cd tools/new-agents/frontend && npm run test -- src/core/__tests__/structuredVisuals.test.ts src/components/__tests__/StructuredVisual.test.tsx -t "cause-map|ROOT_CAUSE"
```

Expected: backend and frontend selected tests fail for the reasons above.

### Task 2: 实现前端 node-edge visual parser 和 renderer

**Files:**
- Modify: `tools/new-agents/frontend/src/core/structuredVisuals.ts`
- Modify: `tools/new-agents/frontend/src/components/StructuredVisual.tsx`
- Modify: `tools/new-agents/frontend/src/core/artifactExport.ts`
- Modify: `tools/new-agents/frontend/src/core/docxExport.ts`

- [x] **Step 1: 扩展 structured visual 类型**

在 `structuredVisuals.ts` 中把现有 `StructuredVisual` 改为矩阵和节点边 union：

```typescript
export interface MatrixStructuredVisual {
    kind: 'matrix';
    type: StructuredVisualType;
    title?: string;
    columns: string[];
    rows: Array<{
        cells: string[];
    }>;
}

export interface NodeEdgeStructuredVisualNode {
    id: string;
    label: string;
    title: string;
    description?: string;
    category?: string;
    evidence?: string;
    confidence?: string;
    status?: string;
}

export interface NodeEdgeStructuredVisualEdge {
    source: string;
    target: string;
    label?: string;
}

export interface NodeEdgeStructuredVisual {
    kind: 'node-edge';
    type: Extract<StructuredVisualType, 'cause-map'>;
    title?: string;
    nodes: NodeEdgeStructuredVisualNode[];
    edges: NodeEdgeStructuredVisualEdge[];
}

export type StructuredVisual = MatrixStructuredVisual | NodeEdgeStructuredVisual;
```

- [x] **Step 2: 增加 node-edge 校验 helper**

在 `structuredVisuals.ts` 中加入：

```typescript
function optionalNonEmptyString(value: unknown): string | undefined {
    return typeof value === 'string' && value.trim().length > 0 ? value.trim() : undefined;
}

function requiredNonEmptyString(value: unknown): string | null {
    return typeof value === 'string' && value.trim().length > 0 ? value.trim() : null;
}
```

新增 `parseNodeEdgeVisual(parsed, visualType, title)`，校验 non-empty `nodes`、唯一 `id`、每条 edge 的 `source/target` 引用已存在节点；错误信息使用 RED 测试中的中文。

- [x] **Step 3: 在 parser 中让 cause-map 优先走 node-edge**

在 `parseStructuredVisual()` 取得 `visualType` 和 `title` 后加入：

```typescript
    if (visualType === 'cause-map') {
        return parseNodeEdgeVisual(parsed, visualType, title);
    }
```

矩阵类路径保持现状，但返回对象补上 `kind: 'matrix'`。

- [x] **Step 4: 增加 graph renderer 分支**

在 `StructuredVisual.tsx` 中，如果 `visual.kind === 'node-edge'`，渲染：

```tsx
<div role="group" aria-label={title} className="...">
  <div>ai4se-visual · {visual.type}</div>
  {visual.nodes.map(...)}
  {visual.edges.map(...)}
</div>
```

节点展示 `label`、`title`、`description`、`category`、`evidence`、`confidence`、`status`。边展示 `source -> target` 和可选 `label`。矩阵类继续走现有 table。

- [x] **Step 5: 同步 PDF / DOCX 导出投影**

在 `artifactExport.ts` 和 `docxExport.ts` 中按 `visual.kind` 分流。矩阵类视觉继续导出表格；`node-edge` 视觉导出标题、节点列表和连接列表的可读文本，并避免访问 `visual.columns` / `visual.rows`。

### Task 3: 后端 ROOT_CAUSE renderer 输出 nodes/edges

**Files:**
- Modify: `tools/new-agents/backend/artifact_data_renderers.py`

- [x] **Step 1: 修改 `_render_incident_why_chain()` 的 visual**

把当前 `visual = {"type": "cause-map", "columns": ..., "rows": ...}` 替换为：

```python
    visual = {
        "type": "cause-map",
        "title": "5-Why 根因链路图",
        "nodes": [
            {
                "id": item.level,
                "label": item.level,
                "title": item.answer,
                "description": item.question,
                "category": item.cause_type,
                "evidence": item.evidence,
                "confidence": item.confidence,
                "status": item.verification_status,
            }
            for item in items
        ],
        "edges": [
            {
                "source": previous.level,
                "target": current.level,
                "label": "继续追问",
            }
            for previous, current in zip(items, items[1:])
        ],
    }
```

Markdown 表格保留，保证正文可读；`ai4se-visual` block 改为复杂图协议。

### Task 4: 同步 ROOT_CAUSE prompt template

**Files:**
- Modify: `tools/new-agents/frontend/src/core/prompts/incident_review/root_cause.ts`
- Modify: `tools/new-agents/backend/agent_contracts.py`
- Modify: `tools/new-agents/backend/tests/test_workflow_contract_sync.py`

- [x] **Step 1: 修改 `ROOT_CAUSE_TEMPLATE` 中 cause-map 示例**

把 `columns/rows` 示例替换为 `nodes/edges` 示例：

```json
{
  "type": "cause-map",
  "title": "5-Why 根因链路图",
  "nodes": [
    {
      "id": "Why-1",
      "label": "Why-1",
      "title": "直接原因",
      "description": "为什么会出现这个现象？",
      "category": "技术 / 流程 / 人员 / 环境 / 度量 / 管理",
      "evidence": "发布记录与测试记录",
      "confidence": "高",
      "status": "已确认"
    },
    {
      "id": "Why-2",
      "label": "Why-2",
      "title": "深层原因",
      "description": "为什么直接原因未被提前拦截？",
      "category": "流程",
      "evidence": "评审记录与测试记录",
      "confidence": "中",
      "status": "待验证"
    }
  ],
  "edges": [
    {
      "source": "Why-1",
      "target": "Why-2",
      "label": "继续追问"
    }
  ]
}
```

- [x] **Step 2: 同步后端 artifact contract 和 prompt sync 测试**

在 `agent_contracts.py` 中让 `cause-map` 走节点 / 边 structured visual 校验，保留其他视觉类型的 `columns/rows` 矩阵校验。同步 `test_workflow_contract_sync.py`，使模板同步测试对 `cause-map` 要求 `nodes/edges`，对其他 visual type 继续要求 `columns/rows`。

### Task 5: GREEN 和回归

**Files:**
- Modify: `docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md`
- Modify: this plan

- [x] **Step 1: Run GREEN selected tests**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_incident_root_cause_artifact_data_builds_formal_incremental_markdown_and_patch -q
cd tools/new-agents/frontend && npm run test -- src/core/__tests__/structuredVisuals.test.ts src/components/__tests__/StructuredVisual.test.tsx -t "cause-map|ROOT_CAUSE"
```

Expected: selected tests pass.

- [x] **Step 2: Run focused backend regression**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_incident_root_cause_artifact_data_builds_formal_incremental_markdown_and_patch tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_incident_root_cause_artifact_data_is_deterministic_and_contract_valid tools/new-agents/backend/tests/test_agent_runtime.py::test_parse_agent_turn_output_text_renders_incident_root_cause_artifact_data tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_incident_root_cause_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_contracts.py -q
```

Expected: all selected backend tests pass.

- [x] **Step 3: Run focused frontend regression**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- src/core/__tests__/structuredVisuals.test.ts src/components/__tests__/StructuredVisual.test.tsx src/components/__tests__/ArtifactPane.test.tsx src/core/__tests__/artifactExport.test.ts src/core/__tests__/docxExport.test.ts
```

Expected: selected frontend tests pass or only existing unrelated warnings appear without failures.

- [x] **Step 4: Run New Agents regression**

Run:

```bash
./scripts/test/test-local.sh new-agents
```

Expected: New Agents frontend and backend suites pass.

- [x] **Step 5: Update todo execution record**

Add a new record to `docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md` for `ROOT_CAUSE cause-map 结构化视觉纵切`. Include RED/GREEN, focused regressions, New Agents regression and residual risk that only `cause-map` has migrated to node-edge shape.

### Task 6: 全量验证、提交和推送

**Files:**
- Modify: this plan

- [x] **Step 1: Run full local validation**

Run:

```bash
./scripts/test/test-local.sh all
```

If default sandbox fails on browser or port permissions, rerun with approved non-sandbox execution and record both results.

- [x] **Step 2: Run diff checks**

Run:

```bash
rg -n "T[B]D|TO[ ]?DO|待[ ]?补|未[ ]?决|place[ ]?holder" docs/superpowers/specs/2026-07-08-new-agents-cause-map-structured-visual-design.md docs/superpowers/plans/2026-07-08-new-agents-cause-map-structured-visual.md docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md
git diff --check -- tools/new-agents/backend/artifact_data_renderers.py tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/agent_contracts.py tools/new-agents/backend/tests/test_agent_contracts.py tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/frontend/src/core/structuredVisuals.ts tools/new-agents/frontend/src/core/__tests__/structuredVisuals.test.ts tools/new-agents/frontend/src/components/StructuredVisual.tsx tools/new-agents/frontend/src/components/__tests__/StructuredVisual.test.tsx tools/new-agents/frontend/src/core/prompts/incident_review/root_cause.ts tools/new-agents/frontend/src/core/artifactExport.ts tools/new-agents/frontend/src/core/__tests__/artifactExport.test.ts tools/new-agents/frontend/src/core/docxExport.ts tools/new-agents/frontend/src/core/__tests__/docxExport.test.ts docs/superpowers/specs/2026-07-08-new-agents-cause-map-structured-visual-design.md docs/superpowers/plans/2026-07-08-new-agents-cause-map-structured-visual.md docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md
```

Stage only this slice and run:

```bash
git diff --cached --check
git diff --cached --name-only
```

- [ ] **Step 3: Commit and push**

Commit message:

```bash
git commit -m "feat(new-agents): 支持根因链路结构化视觉"
git push
```

After push, verify:

```bash
git rev-parse HEAD
git rev-parse @{u}
```

Expected: both SHAs match.
