# New Agents DOCX Mermaid More Types Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Embed Mermaid `timeline` and `mindmap` diagrams as safe local SVG media in exported DOCX packages.

**Architecture:** Extend the existing `docxExport.ts` Mermaid projection pipeline. Keep `flowchart/graph` behavior intact, add local parsers and SVG projectors for `timeline` and `mindmap`, register generated SVG through the existing DOCX media relationship mechanism, and retain text paragraphs for searchability and fallback.

**Tech Stack:** TypeScript, Vitest, DOCX OOXML ZIP generation.

---

### Task 1: RED Tests For Timeline And Mindmap SVG Media

**Files:**
- Modify: `tools/new-agents/frontend/src/core/__tests__/docxExport.test.ts`

- [x] **Step 1: Add timeline test**

Add a test named `embeds supported Mermaid timelines as SVG media in DOCX packages`.

Test input:

```ts
const blob = buildDocxPackage([
  '# 故障时间线',
  '',
  '```mermaid',
  'timeline',
  'title 登录故障复盘',
  'section 发现',
  '09:00 : 监控告警触发',
  '09:05 : 值班确认影响范围',
  'section 恢复',
  '09:20 : 回滚配置',
  '```',
].join('\n'));
```

Assert:
- `word/media/mermaid-1.svg` exists.
- `word/_rels/document.xml.rels` contains `Target="media/mermaid-1.svg"`.
- `word/document.xml` contains `<w:drawing>` and `Mermaid 图表：timeline`.
- SVG contains `登录故障复盘`, `发现`, `监控告警触发`, `恢复`, `回滚配置`.
- SVG does not contain `<script>`, `<foreignObject`, or `onload=`.

- [x] **Step 2: Add mindmap test**

Add a test named `embeds supported Mermaid mindmaps as SVG media in DOCX packages`.

Test input:

```ts
const blob = buildDocxPackage([
  '# 问题树',
  '',
  '```mermaid',
  'mindmap',
  '  root((登录体验问题))',
  '    认证链路',
  '      第三方回调超时',
  '    安全策略',
  '      风控误杀 <script>alert("x")</script>',
  '```',
].join('\n'));
```

Assert:
- `word/media/mermaid-1.svg` exists.
- `word/document.xml` contains `<w:drawing>` and `Mermaid 图表：mindmap`.
- SVG contains `登录体验问题`, `认证链路`, `第三方回调超时`, `安全策略`.
- SVG escapes the script text and does not contain raw `<script>` / `<foreignObject` / `onload=`.

- [x] **Step 3: Verify RED**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/docxExport.test.ts -t "embeds supported Mermaid"
```

Expected: FAIL for the new timeline/mindmap tests because only flowchart/graph currently register SVG media.

### Task 2: Implement Timeline And Mindmap Projectors

**Files:**
- Modify: `tools/new-agents/frontend/src/core/docxExport.ts`

- [x] **Step 1: Add projection union**

Refactor `MermaidFlowchartProjection` to a generic local projection type:

```ts
type MermaidDocxProjection = {
  diagramType: string;
  svg: string;
};
```

Keep `parseMermaidFlowchartProjection` returning `MermaidDocxProjection | null`.

- [x] **Step 2: Add timeline parser/projector**

Implement `parseMermaidTimelineProjection(source: string): MermaidDocxProjection | null`.

Rules:
- Only handle first line `timeline`.
- Read optional `title ...`.
- Read `section ...` markers.
- Read event rows like `09:00 : 监控告警触发`.
- Require at least one event.
- Generate a white-background SVG with a horizontal line, section labels, event cards, and escaped text.

- [x] **Step 3: Add mindmap parser/projector**

Implement `parseMermaidMindmapProjection(source: string): MermaidDocxProjection | null`.

Rules:
- Only handle first line `mindmap`.
- Preserve indentation-based hierarchy.
- Clean common wrappers: `root((...))`, `[...]`, `(...)`.
- Require at least one node.
- Generate a white-background SVG with root and child node boxes plus connecting lines, escaped text.

- [x] **Step 4: Register first supported projection**

Add helper:

```ts
const parseMermaidDocxProjection = (source: string): MermaidDocxProjection | null => (
  parseMermaidFlowchartProjection(source)
  || parseMermaidTimelineProjection(source)
  || parseMermaidMindmapProjection(source)
);
```

Update `projectMermaidToWordParagraphs` to use the helper instead of only `parseMermaidFlowchartProjection`.

- [x] **Step 5: Verify GREEN**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/docxExport.test.ts
```

Expected: PASS.

### Task 3: Todo And Quality Gates

**Files:**
- Modify: `docs/todos/new-agents-ux-professionalization.md`
- Add: `docs/superpowers/specs/2026-06-20-new-agents-docx-mermaid-more-types-design.md`
- Add: `docs/superpowers/plans/2026-06-20-new-agents-docx-mermaid-more-types.md`

- [x] **Step 1: Update todo progress**

Append under Artifact 协作体验深化:
- slice name: `Artifact DOCX Mermaid Timeline/Mindmap SVG 嵌入`
- result: DOCX now embeds timeline and mindmap Mermaid as local SVG media.
- verification commands.
- remaining: DOCX pie/journey, PDF image-level embedding, movement semantic auto-merge.

- [x] **Step 2: Run final gates**

Run:

```bash
cd tools/new-agents/frontend && npm run lint
cd tools/new-agents/frontend && npm run build
git diff --check
```

- [ ] **Step 3: Commit after main-thread verification**

Commit:

```bash
git add docs/todos/new-agents-ux-professionalization.md docs/superpowers/plans/2026-06-20-new-agents-docx-mermaid-more-types.md docs/superpowers/specs/2026-06-20-new-agents-docx-mermaid-more-types-design.md tools/new-agents/frontend/src/core/docxExport.ts tools/new-agents/frontend/src/core/__tests__/docxExport.test.ts
git commit -m "feat(new-agents): 扩展 DOCX Mermaid 图形嵌入"
```

提交前由主线程重新审查 diff 并运行完整验证，确认后再合并回主工作区并推送。
