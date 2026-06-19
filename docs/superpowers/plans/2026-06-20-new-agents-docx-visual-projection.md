# New Agents DOCX Visual Projection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Word/DOCX export project Mermaid and `ai4se-visual` blocks into professional, readable document content instead of raw fenced code or JSON.

**Architecture:** Keep the existing shared `buildDocxPackage(content)` entry point. Extend the Markdown-to-OOXML conversion in `docxExport.ts` so fenced blocks can dispatch by language: Mermaid becomes semantic paragraphs, `ai4se-visual` becomes a titled table or error paragraph, and all other languages remain code paragraphs.

**Tech Stack:** TypeScript, Vitest, existing no-dependency stored-ZIP DOCX builder, existing `parseStructuredVisual`.

---

### Task 1: Add RED coverage for DOCX visual projection

**Files:**
- Modify: `tools/new-agents/frontend/src/core/__tests__/docxExport.test.ts`

- [ ] **Step 1: Write failing tests**

Add tests that build a DOCX from Markdown containing:
- a Mermaid `flowchart` fenced block;
- a valid `ai4se-visual` `risk-board` block;
- an invalid `ai4se-visual` block.

The assertions must inspect `word/document.xml` through the existing `readStoredZipEntries` helper:

```ts
expect(documentXml).toContain('Mermaid 图表：flowchart');
expect(documentXml).toContain('用户入口');
expect(documentXml).toContain('认证服务');
expect(documentXml).not.toContain('```mermaid');
expect(documentXml).toContain('结构化可视化：核心风险矩阵');
expect(documentXml).toContain('<w:tbl>');
expect(documentXml).toContain('风险');
expect(documentXml).toContain('登录失败');
expect(documentXml).not.toContain('```ai4se-visual');
expect(documentXml).not.toContain('&quot;type&quot;');
expect(documentXml).toContain('结构化可视化错误：结构化可视化必须是合法 JSON。');
```

- [ ] **Step 2: Run RED**

Run:

```bash
cd tools/new-agents/frontend
npm run test -- --run src/core/__tests__/docxExport.test.ts
```

Expected: fail because Mermaid is still code text and `ai4se-visual` is still raw JSON/code text.

### Task 2: Implement shared DOCX fenced visual projection

**Files:**
- Modify: `tools/new-agents/frontend/src/core/docxExport.ts`

- [ ] **Step 1: Import shared parser**

Add:

```ts
import { parseStructuredVisual } from './structuredVisuals';
```

- [ ] **Step 2: Add fence language helper**

Add a helper near existing Markdown helpers:

```ts
const getFenceLanguage = (line: string): string => (
    line.trim().replace(/^```/, '').trim().split(/\s+/)[0] || ''
);
```

- [ ] **Step 3: Add Mermaid projection helper**

Add a helper that emits semantic paragraphs:

```ts
const projectMermaidToWordParagraphs = (source: string): string[] => {
    const mermaidLines = source.split(/\r?\n/).map(line => line.trim()).filter(Boolean);
    const firstLine = mermaidLines[0] || 'diagram';
    const diagramType = firstLine.split(/\s+/)[0] || 'diagram';
    return [
        paragraph(`Mermaid 图表：${diagramType}`),
        ...mermaidLines.slice(1).map(line => paragraph(stripInlineMarkdown(line))),
    ];
};
```

- [ ] **Step 4: Add structured visual projection helper**

Add a helper that emits a title and real OOXML table:

```ts
const projectStructuredVisualToWordParagraphs = (source: string): string[] => {
    const result = parseStructuredVisual(source);
    if (result.valid === false) {
        return [paragraph(`结构化可视化错误：${result.message}`)];
    }

    const { visual } = result;
    return [
        paragraph(`结构化可视化：${visual.title || visual.type}`),
        table([
            visual.columns,
            ...visual.rows.map(row => row.cells),
        ]),
    ];
};
```

- [ ] **Step 5: Dispatch fenced blocks by language**

Update the `isFenceStart(trimmedLine)` branch in `markdownToWordParagraphs`:

```ts
const fenceLanguage = getFenceLanguage(trimmedLine);
index += 1;
const codeLines: string[] = [];
while (index < lines.length && !isFenceStart(lines[index])) {
    codeLines.push(lines[index]);
    index += 1;
}
if (index < lines.length) index += 1;
const codeSource = codeLines.join('\n');
if (fenceLanguage === 'mermaid') {
    paragraphs.push(...projectMermaidToWordParagraphs(codeSource));
    continue;
}
if (fenceLanguage === 'ai4se-visual') {
    paragraphs.push(...projectStructuredVisualToWordParagraphs(codeSource));
    continue;
}
codeLines.forEach(codeLine => paragraphs.push(codeParagraph(codeLine)));
continue;
```

- [ ] **Step 6: Run GREEN**

Run:

```bash
cd tools/new-agents/frontend
npm run test -- --run src/core/__tests__/docxExport.test.ts
```

Expected: pass.

### Task 3: Run regression and update todo

**Files:**
- Modify: `docs/todos/new-agents-ux-professionalization.md`

- [ ] **Step 1: Run regression**

Run:

```bash
cd tools/new-agents/frontend
npm run test -- --run src/core/__tests__/docxExport.test.ts src/components/__tests__/ArtifactPane.test.tsx
npm run lint
npm run build
```

Expected: all pass.

- [ ] **Step 2: Update todo progress**

Add a progress record under Artifact 协作体验深化:

```md
- 2026-06-20：完成第三十二块 CGA「Artifact DOCX 可视化语义投影」。
  - Word/DOCX 导出现在会识别 Mermaid fenced block，并输出图表类型和关键语义行，不再把 Mermaid 当普通代码块暴露。
  - Word/DOCX 导出现在会识别合法 `ai4se-visual`，复用共享 parser 输出结构化可视化标题和真实 Word 表格。
  - 非法 `ai4se-visual` 会输出结构化可视化错误摘要，下载仍保持成功。
  - 验证：...
```

- [ ] **Step 3: Final checks and commit**

Run:

```bash
git diff --check
git status --short
git add ...
git commit -m "feat(new-agents): 优化 DOCX 可视化导出"
```
