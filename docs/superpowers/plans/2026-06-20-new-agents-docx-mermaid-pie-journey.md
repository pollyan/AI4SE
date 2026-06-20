# New Agents DOCX Mermaid Pie/Journey Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Embed Mermaid `pie` and `journey` diagrams as safe local SVG media in exported DOCX packages.

**Architecture:** Extend the existing `tools/new-agents/frontend/src/core/docxExport.ts` Mermaid projection pipeline. Keep `flowchart/graph`, `timeline`, and `mindmap` behavior intact, add local parsers and SVG projectors for `pie` and `journey`, register generated SVG through the existing DOCX media relationship mechanism, and retain text paragraphs for searchability and fallback.

**Tech Stack:** TypeScript, Vitest, DOCX OOXML ZIP generation.

---

## Commit Boundary

This slice should produce one focused commit after main-thread verification:

```bash
git add docs/todos/new-agents-ux-professionalization.md \
  docs/superpowers/plans/2026-06-20-new-agents-docx-mermaid-pie-journey.md \
  docs/superpowers/specs/2026-06-20-new-agents-docx-mermaid-pie-journey-design.md \
  tools/new-agents/frontend/src/core/docxExport.ts \
  tools/new-agents/frontend/src/core/__tests__/docxExport.test.ts
git commit -m "feat(new-agents): 补齐 DOCX Mermaid 饼图旅程图嵌入"
```

The worker must not commit or push. The main agent will review, verify, commit, merge to `master`, and push.

### Task 1: RED Tests For Pie And Journey SVG Media

**Files:**
- Modify: `tools/new-agents/frontend/src/core/__tests__/docxExport.test.ts`

- [x] **Step 1: Add pie test**

Add a test named `embeds supported Mermaid pies as SVG media in DOCX packages`.

Test input:

```ts
const blob = buildDocxPackage([
    '# 优先级分布',
    '',
    '```mermaid',
    'pie title 评审问题优先级分布',
    '"高优先级" : 5',
    '"中优先级" : 3',
    '"低优先级 <script>alert("x")</script>" : 2',
    '```',
].join('\n'));
```

Assert:
- `word/media/mermaid-1.svg` exists.
- `word/_rels/document.xml.rels` contains `Target="media/mermaid-1.svg"`.
- `word/document.xml` contains `<w:drawing>` and `Mermaid 图表：pie`.
- `word/document.xml` contains semantic text `评审问题优先级分布`, `高优先级：5`, `中优先级：3`.
- `word/document.xml` does not contain ```` ```mermaid ```` or `pie title 评审问题优先级分布`.
- SVG contains `<svg`, title, labels and values.
- SVG escapes the script label and does not contain raw `<script>`, `<foreignObject`, or `onload=`.

- [x] **Step 2: Add journey test**

Add a test named `embeds supported Mermaid journeys as SVG media in DOCX packages`.

Test input:

```ts
const blob = buildDocxPackage([
    '# 用户旅程',
    '',
    '```mermaid',
    'journey',
    'title 登录体验旅程',
    'section 发现问题',
    '收到告警: 3: 值班员',
    '确认影响范围 <script>alert("x")</script>: 4: SRE',
    'section 恢复服务',
    '回滚配置: 5: 发布负责人',
    '```',
].join('\n'));
```

Assert:
- `word/media/mermaid-1.svg` exists.
- `word/document.xml` contains `<w:drawing>` and `Mermaid 图表：journey`.
- `word/document.xml` contains semantic text `登录体验旅程`, `发现问题`, `收到告警：3（值班员）`, `恢复服务`.
- `word/document.xml` does not contain ```` ```mermaid ```` or `title 登录体验旅程` or `section 发现问题`.
- SVG contains title, sections, task labels, scores and actors.
- SVG escapes the script task label and does not contain raw `<script>`, `<foreignObject`, or `onload=`.

- [x] **Step 3: Verify RED**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/docxExport.test.ts -t "embeds supported Mermaid"
```

Expected: FAIL for the new pie/journey tests because current DOCX projection registers SVG media only for flowchart/graph, timeline and mindmap.

### Task 2: Implement Pie And Journey DOCX Projectors

**Files:**
- Modify: `tools/new-agents/frontend/src/core/docxExport.ts`

- [x] **Step 1: Add local types**

Add narrow local types near the existing Mermaid DOCX types:

```ts
type MermaidPieSlice = {
    label: string;
    value: number;
    valueText: string;
};

type MermaidJourneyTask = {
    section: string;
    label: string;
    scoreText: string;
    actor: string | null;
};
```

- [x] **Step 2: Add pie parser/projector**

Implement `parseMermaidPieProjection(source: string): MermaidDocxProjection | null`.

Rules:
- Only handle first line beginning with `pie`.
- Support inline `pie title ...` and later `title ...`.
- Read slice rows like `"高优先级" : 5`.
- Strip wrapping quotes from labels.
- Require at least one positive numeric slice.
- Generate a white-background SVG with title, circle outline, separator lines and legend rows.
- Use `xmlEscape` for every text value.
- Limit displayed slices to a small bounded count, for example 8, matching PDF behavior.

- [x] **Step 3: Add journey parser/projector**

Implement `parseMermaidJourneyProjection(source: string): MermaidDocxProjection | null`.

Rules:
- Only handle first line `journey`.
- Read optional `title ...`.
- Read `section ...` markers.
- Read task rows like `收到告警: 3: 值班员`.
- Preserve task label, score text and optional actor.
- Require at least one task.
- Generate a white-background SVG with title, section labels, a journey baseline and task cards.
- Use `xmlEscape` for every text value.
- Limit sections/tasks to bounded counts matching PDF behavior, for example 6 sections and 8 tasks.

- [x] **Step 4: Register projections**

Update:

```ts
const parseMermaidDocxProjection = (source: string): MermaidDocxProjection | null => (
    parseMermaidFlowchartProjection(source)
    || parseMermaidTimelineProjection(source)
    || parseMermaidMindmapProjection(source)
);
```

to include:

```ts
    || parseMermaidPieProjection(source)
    || parseMermaidJourneyProjection(source)
```

- [x] **Step 5: Add semantic text projection helpers**

Add semantic helpers used by `projectMermaidSemanticLine`:

```ts
const projectMermaidPieLine = (line: string): string | null => { ... };
const projectMermaidJourneyLine = (line: string): string | null => { ... };
```

Expected text forms:
- `pie title 评审问题优先级分布` -> `评审问题优先级分布`
- `"高优先级" : 5` -> `高优先级：5`
- `title 登录体验旅程` -> `登录体验旅程`
- `section 发现问题` -> `发现问题`
- `收到告警: 3: 值班员` -> `收到告警：3（值班员）`

Do not expose source control lines such as `pie title ...`, `title ...`, or `section ...` in `document.xml`.

- [x] **Step 6: Verify GREEN**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/docxExport.test.ts
```

Expected: PASS.

### Task 3: Todo Record And Quality Gates

**Files:**
- Modify: `docs/todos/new-agents-ux-professionalization.md`
- Add: `docs/superpowers/specs/2026-06-20-new-agents-docx-mermaid-pie-journey-design.md`
- Add: `docs/superpowers/plans/2026-06-20-new-agents-docx-mermaid-pie-journey.md`

- [x] **Step 1: Update todo progress**

Append under Artifact 协作体验深化:

```markdown
- 2026-06-20：完成第四十一块 CGA「Artifact DOCX Mermaid Pie/Journey SVG 嵌入」。
  - Word/DOCX 导出现在会对 Mermaid `pie` 和 `journey` 生成本地 SVG media part，并写入 `word/_rels/document.xml.rels` 与 `w:drawing` 引用，让优先级分布和用户旅程在 Word 中呈现为图形。
  - DOCX 仍保留 `Mermaid 图表：pie` / `Mermaid 图表：journey` 与清洗后的标题、分类、数值、阶段、任务、评分和角色语义文本，保证导出物可搜索、可复制，不暴露 fenced source。
  - SVG 继续由前端本地保守投影生成，文本经过 XML 转义，不把模型输出的任意 SVG/HTML 原样写入 DOCX；实现复用共享 DOCX 导出路径，不新增 Lisa/Alex 或 workflow 专属分支。
  - 验证：先运行 `npm run test -- --run src/core/__tests__/docxExport.test.ts -t "embeds supported Mermaid"` 观察到新增 pie/journey 用例因缺少 `word/media/mermaid-1.svg` 失败；实现后运行 `npm run test -- --run src/core/__tests__/docxExport.test.ts`、`npm run lint`、`npm run build`、`git diff --check`。
  - 剩余：PDF Mermaid 图片级嵌入、移动语义自动合并、完整三方 merge 的更复杂冲突解析仍可作为后续增强切片。
```

- [x] **Step 2: Run final gates**

Run:

```bash
cd tools/new-agents/frontend && npm run lint
cd tools/new-agents/frontend && npm run build
git diff --check
```

- [x] **Step 3: Leave uncommitted for main-thread review**

Do not commit. Report:
- Files changed.
- RED command and failure summary.
- GREEN/final verification commands.
- Residual risks.
