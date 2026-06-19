# New Agents Artifact PDF Mermaid Journey Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Draw Mermaid `journey` diagrams as lightweight journey maps in Artifact PDF exports.

**Architecture:** Extend the existing shared Artifact PDF projection in `ArtifactPane.tsx`. Keep the no-dependency PDF string generator, preserve searchable journey text, and add journey diagram metadata consumed by the existing Mermaid drawing phase.

**Tech Stack:** React, TypeScript, Vitest, existing no-dependency PDF generator.

---

### Task 1: RED Test For Journey PDF Drawing

**Files:**
- Modify: `tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`

- [ ] **Step 1: Write the failing test**

Add a test near the existing Mermaid PDF vector tests:

```ts
it('draws Mermaid journeys as vector journey map shapes in exported PDF content streams', async () => {
    const createdAnchors: HTMLAnchorElement[] = [];
    const click = vi.fn();
    const createObjectURL = vi
        .spyOn(URL, 'createObjectURL')
        .mockReturnValue('blob:artifact-mermaid-journey-pdf');
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
        workflow: 'VALUE_DISCOVERY',
        artifactContent: [
            '# 用户旅程分析',
            '',
            '```mermaid',
            'journey',
            '    title 核心用户旅程',
            '    section 问题认知',
            '        意识到问题存在: 3: 用户',
            '    section 寻找方案',
            '        搜索解决方案: 2: 用户',
            '        对比不同选择: 2: 用户',
            '```',
        ].join('\n'),
    });

    render(<ArtifactPane />);
    fireEvent.click(screen.getByTitle('下载'));
    fireEvent.click(screen.getByRole('button', { name: 'PDF' }));

    const blob = createObjectURL.mock.calls[0][0] as Blob;
    const content = await blob.text();
    const rectangleCount = content.match(/ re S/g)?.length ?? 0;
    expect(createdAnchors[0].download).toBe('value_discovery_artifact.pdf');
    expect(content).toContain(toUtf16BeHex('Mermaid 图表：journey'));
    expect(content).toContain(toUtf16BeHex('核心用户旅程'));
    expect(content).toContain(toUtf16BeHex('问题认知'));
    expect(content).toContain(toUtf16BeHex('意识到问题存在：3（用户）'));
    expect(content).toContain(toUtf16BeHex('寻找方案'));
    expect(content).toContain(toUtf16BeHex('搜索解决方案：2（用户）'));
    expect(content).not.toContain(toUtf16BeHex('title 核心用户旅程'));
    expect(content).not.toContain(toUtf16BeHex('section 问题认知'));
    expect(content).not.toContain(toUtf16BeHex('意识到问题存在: 3: 用户'));
    expect(content).toContain('0.18 0.55 0.95 RG');
    expect(rectangleCount).toBeGreaterThanOrEqual(4);
    expect(content).toContain(' m ');
    expect(content).toContain(' l S');
    expect(click).toHaveBeenCalledTimes(1);
});
```

- [ ] **Step 2: Verify RED**

Run:

```bash
cd tools/new-agents/frontend
npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "draws Mermaid journeys"
```

Expected: fail because `journey` is currently text-only and not parsed into drawing metadata.

### Task 2: Journey Projection And Drawing

**Files:**
- Modify: `tools/new-agents/frontend/src/components/ArtifactPane.tsx`

- [ ] **Step 1: Implement minimal parser**

Add a `PdfMermaidJourneyDiagram` shape with `title`, `sections`, and `tasks`.

Parse:

- first line `journey`
- optional `title ...`
- `section ...`
- task lines matching `task: score: actor`
- labels by stripping inline Markdown
- scores as original text and numeric value when finite

- [ ] **Step 2: Merge into existing dispatcher**

Update the Mermaid diagram union and `parseMermaidDiagramForPdf` to include journey while preserving flowchart, timeline, mindmap and pie behavior.

- [ ] **Step 3: Project clean PDF text**

Update `projectMermaidToPdfLines` for `journey`:

```ts
return [
  'Mermaid 图表：journey',
  ...(parsedDiagram.title ? [parsedDiagram.title] : []),
  ...parsedDiagram.sections,
  ...parsedDiagram.tasks.map(task => `${task.label}：${task.scoreText}${task.actor ? `（${task.actor}）` : ''}`),
];
```

- [ ] **Step 4: Draw journey commands**

Update `buildPdfMermaidDrawingCommands`:

- flowchart/timeline/mindmap/pie branches remain unchanged.
- journey branch draws a baseline, section boxes and task cards.
- cap tasks to a small count to avoid overrun.

- [ ] **Step 5: Verify GREEN**

Run:

```bash
cd tools/new-agents/frontend
npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "draws Mermaid journeys"
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

Append a progress entry documenting Journey PDF projection and verification.

- [ ] **Step 3: Check whitespace**

```bash
git diff --check
```

- [ ] **Step 4: Commit**

```bash
git add docs/todos/new-agents-ux-professionalization.md docs/superpowers/specs/2026-06-20-new-agents-artifact-pdf-mermaid-journey-design.md docs/superpowers/plans/2026-06-20-new-agents-artifact-pdf-mermaid-journey.md tools/new-agents/frontend/src/components/ArtifactPane.tsx tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx
git commit -m "feat(new-agents): 增强 PDF 用户旅程导出"
```
