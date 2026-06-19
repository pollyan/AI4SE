# New Agents Artifact DOCX Mermaid SVG Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make DOCX export embed supported Mermaid flowchart/graph blocks as local SVG media while preserving readable text summaries.

**Architecture:** Keep export in the shared Artifact DOCX pipeline. Generate SVG locally from a conservative Mermaid flowchart/graph parser, add SVG media and relationships to the OOXML package, and keep unsupported Mermaid types on the current text projection path.

**Tech Stack:** React/Vite frontend, TypeScript, Vitest, hand-built stored ZIP DOCX package, Office Open XML relationships/drawing markup.

---

### Task 1: RED Test For DOCX SVG Media

**Files:**
- Modify: `tools/new-agents/frontend/src/core/__tests__/docxExport.test.ts`

- [ ] **Step 1: Write the failing test**

Add a test that builds a DOCX from a simple Mermaid flowchart and asserts:
- ZIP contains `word/_rels/document.xml.rels`.
- ZIP contains `word/media/mermaid-1.svg`.
- `[Content_Types].xml` declares SVG content.
- `word/document.xml` contains `w:drawing` and `r:embed="rId1"`.
- `word/media/mermaid-1.svg` contains escaped node labels, rectangles and lines.
- Raw Mermaid fence/source is not exposed in `document.xml`.

- [ ] **Step 2: Verify RED**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/docxExport.test.ts -t "embeds supported Mermaid flowcharts"
```

Expected: FAIL because the DOCX package has no document relationships, no media SVG, and no drawing reference.

### Task 2: Implement Minimal DOCX SVG Embedding

**Files:**
- Modify: `tools/new-agents/frontend/src/core/docxExport.ts`

- [ ] **Step 1: Add DOCX build context**

Introduce an internal `DocxBuildContext` with a `media` array. `markdownToWordParagraphs` and `projectMermaidToWordParagraphs` should receive this context so supported Mermaid blocks can register generated SVG media.

- [ ] **Step 2: Generate conservative flowchart SVG**

Implement a local flowchart/graph parser that accepts simple edge lines such as `A[用户入口] --> B[认证服务]` and emits an SVG with:
- escaped text labels;
- node rectangles;
- edge lines;
- no script, foreignObject, event attributes or raw model-provided SVG.

Unsupported Mermaid returns `null` and falls back to current text projection.

- [ ] **Step 3: Add OOXML relationship and drawing markup**

When an SVG is generated:
- add `word/media/mermaid-N.svg` to the package;
- add `word/_rels/document.xml.rels` with `Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"`;
- insert a `w:drawing` paragraph using the relationship id;
- keep `Mermaid 图表：flowchart` and node/edge summary paragraphs.

- [ ] **Step 4: Verify GREEN for focused test**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/docxExport.test.ts -t "embeds supported Mermaid flowcharts"
```

Expected: PASS.

### Task 3: Regression Coverage And Todo Record

**Files:**
- Modify: `tools/new-agents/frontend/src/core/__tests__/docxExport.test.ts`
- Modify: `docs/todos/new-agents-ux-professionalization.md`

- [ ] **Step 1: Keep existing DOCX projection tests green**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/docxExport.test.ts
```

Expected: all docx export tests pass.

- [ ] **Step 2: Run ArtifactPane export regression**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx
```

Expected: ArtifactPane download tests and PDF regressions still pass.

- [ ] **Step 3: Update todo progress**

Append a progress entry under Artifact 协作体验深化:
- slice name: `Artifact DOCX Mermaid SVG 图片级嵌入`
- user-visible result: DOCX embeds supported flowchart/graph Mermaid as SVG media.
- verification commands.
- remaining: PDF image-level embedding, more Mermaid types, repeated heading anchors.

### Task 4: Final Verification And Commit

**Files:**
- All files from previous tasks.

- [ ] **Step 1: Run quality gates**

Run:

```bash
cd tools/new-agents/frontend && npm run lint
cd tools/new-agents/frontend && npm run build
git diff --check
```

Expected: all commands exit 0.

- [ ] **Step 2: Commit focused slice**

Stage only this slice's files and commit:

```bash
git add docs/todos/new-agents-ux-professionalization.md docs/superpowers/specs/2026-06-20-new-agents-artifact-docx-mermaid-svg-design.md docs/superpowers/plans/2026-06-20-new-agents-artifact-docx-mermaid-svg.md tools/new-agents/frontend/src/core/docxExport.ts tools/new-agents/frontend/src/core/__tests__/docxExport.test.ts
git commit -m "feat(new-agents): 支持 DOCX 嵌入 Mermaid 图形"
```

Expected: one focused commit for this milestone.
