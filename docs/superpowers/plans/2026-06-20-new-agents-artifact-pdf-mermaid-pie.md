# New Agents Artifact PDF Mermaid Pie Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Draw Mermaid `pie` diagrams as lightweight distribution diagrams in Artifact PDF exports.

**Architecture:** Extend the existing shared Artifact PDF projection in `ArtifactPane.tsx`. Keep the no-dependency PDF string generator, preserve searchable title/category text, and add pie diagram metadata consumed by the existing Mermaid drawing phase.

**Tech Stack:** React, TypeScript, Vitest, existing no-dependency PDF generator.

---

### Task 1: RED Test For Pie PDF Drawing

**Files:**
- Modify: `tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`

- [ ] **Step 1: Write the failing test**

Add a test near the existing Mermaid PDF vector tests:

```ts
it('draws Mermaid pie charts as vector distribution shapes in exported PDF content streams', async () => {
    const createdAnchors: HTMLAnchorElement[] = [];
    const click = vi.fn();
    const createObjectURL = vi
        .spyOn(URL, 'createObjectURL')
        .mockReturnValue('blob:artifact-mermaid-pie-pdf');
    vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});
    vi.spyOn(document, 'createElement').mockImplementation((tagName, options) => {
        const element = originalCreateElement(tagName, options);
        if (tagName.toLowerCase() === 'a') {
            Object.defineProperty(element, 'click', {
                configurable: true,
                value: click,
            });
            createdAnchors.push(element as HTMLAnchorElement);
        }
        return element;
    });
    useStore.setState({
        workflow: 'REQ_REVIEW',
        artifactContent: [
            '# 评审报告',
            '',
            '```mermaid',
            'pie title 评审问题优先级分布',
            '    "P0 (阻塞)" : 2',
            '    "P1 (重要)" : 3',
            '    "P2 (建议)" : 5',
            '```',
        ].join('\n'),
    });

    render(<ArtifactPane />);
    fireEvent.click(screen.getByTitle('下载'));
    fireEvent.click(screen.getByRole('button', { name: 'PDF' }));

    const blob = createObjectURL.mock.calls[0][0] as Blob;
    const content = await blob.text();
    const rectangleCount = content.match(/ re S/g)?.length ?? 0;
    expect(createdAnchors[0].download).toBe('req_review_artifact.pdf');
    expect(content).toContain(toUtf16BeHex('Mermaid 图表：pie'));
    expect(content).toContain(toUtf16BeHex('评审问题优先级分布'));
    expect(content).toContain(toUtf16BeHex('P0 (阻塞)：2'));
    expect(content).toContain(toUtf16BeHex('P1 (重要)：3'));
    expect(content).toContain(toUtf16BeHex('P2 (建议)：5'));
    expect(content).not.toContain(toUtf16BeHex('pie title 评审问题优先级分布'));
    expect(content).not.toContain(toUtf16BeHex('"P0 (阻塞)" : 2'));
    expect(content).toContain('0.18 0.55 0.95 RG');
    expect(content).toContain(' c ');
    expect(rectangleCount).toBeGreaterThanOrEqual(3);
    expect(content).toContain(' m ');
    expect(content).toContain(' l S');
    expect(click).toHaveBeenCalledTimes(1);
});
```

- [ ] **Step 2: Verify RED**

Run:

```bash
cd tools/new-agents/frontend
npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "draws Mermaid pie"
```

Expected: fail because `pie` is currently text-only and not parsed into drawing metadata.

### Task 2: Pie Projection And Drawing

**Files:**
- Modify: `tools/new-agents/frontend/src/components/ArtifactPane.tsx`

- [ ] **Step 1: Implement minimal parser**

Add a `PdfMermaidPieDiagram` shape with `title` and `slices`.

Parse:

- first line starts with `pie`
- optional title from `pie title ...`
- slice lines matching `"label" : value` or `label : value`
- labels by removing surrounding quotes and inline Markdown
- values as finite positive numbers

- [ ] **Step 2: Merge into existing dispatcher**

Update the Mermaid diagram union and `parseMermaidDiagramForPdf` to include pie while preserving flowchart, timeline and mindmap behavior.

- [ ] **Step 3: Project clean PDF text**

Update `projectMermaidToPdfLines` for `pie`:

```ts
return [
  'Mermaid 图表：pie',
  ...(parsedDiagram.title ? [parsedDiagram.title] : []),
  ...parsedDiagram.slices.map(slice => `${slice.label}：${slice.value}`),
];
```

- [ ] **Step 4: Draw distribution commands**

Update `buildPdfMermaidDrawingCommands`:

- flowchart branch remains unchanged.
- timeline branch remains unchanged.
- mindmap branch remains unchanged.
- pie branch draws a circle approximation with cubic Bezier segments, radial separator lines, and one small legend rectangle per slice.
- cap slices to a small count to avoid overrun.

- [ ] **Step 5: Verify GREEN**

Run:

```bash
cd tools/new-agents/frontend
npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "draws Mermaid pie"
```

Expected: pass.

### Task 3: Regression, Docs, Commit

**Files:**
- Modify: `docs/todos/new-agents-ux-professionalization.md`

- [ ] **Step 1: Run focused regression**

```bash
cd tools/new-agents/frontend
npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx
npm run lint
npm run build
```

- [ ] **Step 2: Update todo progress**

Append a progress entry documenting Pie PDF projection and verification.

- [ ] **Step 3: Check whitespace**

```bash
git diff --check
```

- [ ] **Step 4: Commit**

```bash
git add docs/todos/new-agents-ux-professionalization.md docs/superpowers/specs/2026-06-20-new-agents-artifact-pdf-mermaid-pie-design.md docs/superpowers/plans/2026-06-20-new-agents-artifact-pdf-mermaid-pie.md tools/new-agents/frontend/src/components/ArtifactPane.tsx tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx
git commit -m "feat(new-agents): 增强 PDF 饼图导出"
```
