# New Agents Artifact PDF Mermaid Timeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Draw Mermaid `timeline` diagrams as lightweight vector timelines in Artifact PDF exports.

**Architecture:** Extend the existing shared Artifact PDF projection in `ArtifactPane.tsx`. Keep the current no-dependency PDF generator, preserve searchable text lines, and add timeline diagram metadata consumed by the existing content stream drawing phase.

**Tech Stack:** React, TypeScript, Vitest, existing no-dependency PDF string generator.

---

### Task 1: RED Test For Timeline PDF Drawing

**Files:**
- Modify: `tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`

- [ ] **Step 1: Write the failing test**

Add a test near the existing Mermaid PDF vector test:

```ts
it('draws Mermaid timelines as vector timeline shapes in exported PDF content streams', async () => {
    const createdAnchors: HTMLAnchorElement[] = [];
    const click = vi.fn();
    const createObjectURL = vi
        .spyOn(URL, 'createObjectURL')
        .mockReturnValue('blob:artifact-mermaid-timeline-pdf');
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
        workflow: 'INCIDENT_REVIEW',
        artifactContent: [
            '# 事件还原',
            '',
            '```mermaid',
            'timeline',
            '    title 登录事故时间线',
            '    section 发现',
            '      09点10分 : 监控触发告警',
            '      09点18分 : 值班确认影响范围',
            '    section 恢复',
            '      09点42分 : 回滚异常发布',
            '```',
        ].join('\n'),
    });

    render(<ArtifactPane />);
    fireEvent.click(screen.getByTitle('下载'));
    fireEvent.click(screen.getByRole('button', { name: 'PDF' }));

    const blob = createObjectURL.mock.calls[0][0] as Blob;
    const content = await blob.text();
    const rectangleCount = content.match(/ re S/g)?.length ?? 0;
    expect(createdAnchors[0].download).toBe('incident_review_artifact.pdf');
    expect(content).toContain(toUtf16BeHex('Mermaid 图表：timeline'));
    expect(content).toContain(toUtf16BeHex('登录事故时间线'));
    expect(content).toContain(toUtf16BeHex('发现'));
    expect(content).toContain(toUtf16BeHex('09点10分：监控触发告警'));
    expect(content).toContain('0.18 0.55 0.95 RG');
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
npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "draws Mermaid timelines"
```

Expected: fail because `timeline` is not parsed into Mermaid drawing metadata yet.

### Task 2: Timeline Projection And Drawing

**Files:**
- Modify: `tools/new-agents/frontend/src/components/ArtifactPane.tsx`

- [ ] **Step 1: Implement minimal parser**

Add timeline metadata shape beside existing Mermaid PDF types. Parse:

- first line `timeline`
- optional `title ...`
- `section ...`
- event lines in the form `time : description`

Normalize event text to `time：description` for searchable PDF lines.

- [ ] **Step 2: Merge into existing projection**

Update `PdfMermaidDiagram` to support `kind: 'flowchart' | 'timeline'`, keep existing flowchart behavior unchanged, and add timeline diagrams to `projectMarkdownToPdfDocument`.

- [ ] **Step 3: Draw timeline vector commands**

Update `buildPdfMermaidDrawingCommands`:

- flowchart diagrams use existing node/edge drawing.
- timeline diagrams draw a horizontal baseline, tick marks, connector lines, and event rectangles.
- cap drawn events to a small count to avoid overrun, matching current lightweight export approach.

- [ ] **Step 4: Verify GREEN**

Run:

```bash
cd tools/new-agents/frontend
npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "draws Mermaid timelines"
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

Add a progress entry under Artifact collaboration / export progress documenting the timeline PDF projection and verification.

- [ ] **Step 3: Check whitespace**

```bash
git diff --check
```

- [ ] **Step 4: Commit**

```bash
git add docs/todos/new-agents-ux-professionalization.md docs/superpowers/specs/2026-06-20-new-agents-artifact-pdf-mermaid-timeline-design.md docs/superpowers/plans/2026-06-20-new-agents-artifact-pdf-mermaid-timeline.md tools/new-agents/frontend/src/components/ArtifactPane.tsx tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx
git commit -m "feat(new-agents): 增强 PDF 时间线图导出"
```
