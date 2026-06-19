# New Agents Artifact PDF Mermaid Mindmap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Draw Mermaid `mindmap` diagrams as lightweight tree diagrams in Artifact PDF exports.

**Architecture:** Extend the existing shared Artifact PDF projection in `ArtifactPane.tsx`. Keep the no-dependency PDF string generator, preserve searchable node text, and add mindmap diagram metadata consumed by the existing Mermaid drawing phase.

**Tech Stack:** React, TypeScript, Vitest, existing no-dependency PDF generator.

---

### Task 1: RED Test For Mindmap PDF Drawing

**Files:**
- Modify: `tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`

- [ ] **Step 1: Write the failing test**

Add a test near the existing Mermaid PDF vector tests:

```ts
it('draws Mermaid mindmaps as vector tree shapes in exported PDF content streams', async () => {
    const createdAnchors: HTMLAnchorElement[] = [];
    const click = vi.fn();
    const createObjectURL = vi
        .spyOn(URL, 'createObjectURL')
        .mockReturnValue('blob:artifact-mermaid-mindmap-pdf');
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
        workflow: 'IDEA_BRAINSTORM',
        artifactContent: [
            '# 问题树',
            '',
            '```mermaid',
            'mindmap',
            '  root((宠物照护问题))',
            '    用户痛点',
            '      临时出行无人照看',
            '      陌生服务缺少信任',
            '    机会方向',
            '      邻里互助',
            '```',
        ].join('\n'),
    });

    render(<ArtifactPane />);
    fireEvent.click(screen.getByTitle('下载'));
    fireEvent.click(screen.getByRole('button', { name: 'PDF' }));

    const blob = createObjectURL.mock.calls[0][0] as Blob;
    const content = await blob.text();
    const rectangleCount = content.match(/ re S/g)?.length ?? 0;
    expect(createdAnchors[0].download).toBe('idea_brainstorm_artifact.pdf');
    expect(content).toContain(toUtf16BeHex('Mermaid 图表：mindmap'));
    expect(content).toContain(toUtf16BeHex('宠物照护问题'));
    expect(content).toContain(toUtf16BeHex('用户痛点'));
    expect(content).toContain(toUtf16BeHex('临时出行无人照看'));
    expect(content).not.toContain(toUtf16BeHex('root((宠物照护问题))'));
    expect(content).toContain('0.18 0.55 0.95 RG');
    expect(rectangleCount).toBeGreaterThanOrEqual(5);
    expect(content).toContain(' m ');
    expect(content).toContain(' l S');
    expect(click).toHaveBeenCalledTimes(1);
});
```

- [ ] **Step 2: Verify RED**

Run:

```bash
cd tools/new-agents/frontend
npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "draws Mermaid mindmaps"
```

Expected: fail because `mindmap` is currently text-only and not parsed into drawing metadata.

### Task 2: Mindmap Projection And Drawing

**Files:**
- Modify: `tools/new-agents/frontend/src/components/ArtifactPane.tsx`

- [ ] **Step 1: Implement minimal parser**

Add a `PdfMermaidMindmapDiagram` shape with nodes containing `id`, `label`, `depth`, and optional `parentId`.

Parse:

- first line `mindmap`
- indentation depth by leading spaces after trimming blank lines
- labels by removing Mermaid wrappers such as `root((...))`, `((...))`, `[...]`, and `(...)`

- [ ] **Step 2: Merge into existing dispatcher**

Update the Mermaid diagram union and `parseMermaidDiagramForPdf` to include mindmap while preserving flowchart and timeline behavior.

- [ ] **Step 3: Draw tree commands**

Update `buildPdfMermaidDrawingCommands`:

- flowchart branch remains unchanged.
- timeline branch remains unchanged.
- mindmap branch lays out depth columns left to right and sibling rows top to bottom.
- draw one rectangle per visible node and one line per parent-child edge.
- cap nodes to a small count to avoid overrun.

- [ ] **Step 4: Verify GREEN**

Run:

```bash
cd tools/new-agents/frontend
npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "draws Mermaid mindmaps"
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

Append a progress entry documenting Mindmap PDF projection and verification.

- [ ] **Step 3: Check whitespace**

```bash
git diff --check
```

- [ ] **Step 4: Commit**

```bash
git add docs/todos/new-agents-ux-professionalization.md docs/superpowers/specs/2026-06-20-new-agents-artifact-pdf-mermaid-mindmap-design.md docs/superpowers/plans/2026-06-20-new-agents-artifact-pdf-mermaid-mindmap.md tools/new-agents/frontend/src/components/ArtifactPane.tsx tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx
git commit -m "feat(new-agents): 增强 PDF 思维导图导出"
```
