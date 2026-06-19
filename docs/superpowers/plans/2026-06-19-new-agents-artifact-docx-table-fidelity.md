# New Agents Artifact DOCX 表格高保真导出 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 Artifact Word 导出的 Markdown 表格成为真实 OOXML 表格，并为 DOCX 包增加基础 styles part。

**Architecture:** 继续使用现有无依赖 DOCX ZIP builder，不引入第三方包。Markdown 解析仍在 `docxExport.ts` 内完成，但表格分支输出 `w:tbl`，包结构新增 `word/styles.xml` 并在 content types 中声明。

**Tech Stack:** TypeScript、Vitest、Office Open XML、stored ZIP builder。

---

### Task 1: 写失败测试

**Files:**
- Modify: `tools/new-agents/frontend/src/core/__tests__/docxExport.test.ts`

- [ ] **Step 1: 增加 OOXML 表格和 styles entry 断言**

在现有 `builds a real DOCX package...` 测试中加入这些断言：

```ts
expect(Object.keys(entries)).toEqual(expect.arrayContaining([
    '[Content_Types].xml',
    '_rels/.rels',
    'word/document.xml',
    'word/styles.xml',
]));
expect(entries['[Content_Types].xml']).toContain('styles+xml');

const documentXml = entries['word/document.xml'];
expect(documentXml).toContain('<w:tbl>');
expect(documentXml).toContain('<w:tr>');
expect(documentXml).toContain('<w:tc>');
expect(documentXml).toContain('模块');
expect(documentXml).toContain('状态');
expect(documentXml).toContain('登录');
expect(documentXml).not.toContain('模块 | 状态');

const stylesXml = entries['word/styles.xml'];
expect(stylesXml).toContain('<w:styles');
expect(stylesXml).toContain('Heading1');
expect(stylesXml).toContain('TableGrid');
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/docxExport.test.ts
```

Expected: FAIL，缺少 `word/styles.xml` 或 `w:tbl`。

### Task 2: 实现最小 DOCX 表格输出

**Files:**
- Modify: `tools/new-agents/frontend/src/core/docxExport.ts`

- [ ] **Step 1: 新增表格 cell/row/table XML helper**

实现 `tableCell`、`tableRow`、`table`，所有单元格文本继续用 `xmlEscape`。

- [ ] **Step 2: 修改 Markdown 表格分支**

把当前表格分支从 `paragraph(splitTableRow(line).join(' | '))` 改为收集 header 和 body rows 后输出单个 `table(rows)`。

- [ ] **Step 3: 新增 styles.xml 和 content type**

新增 `buildStylesXml()`，并在 `buildDocxPackage` files 中加入 `{ fileName: 'word/styles.xml', content: buildStylesXml() }`。`buildContentTypesXml()` 增加 `/word/styles.xml` override。

- [ ] **Step 4: 运行测试确认通过**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/docxExport.test.ts
```

Expected: PASS。

### Task 3: 回归验证和文档记录

**Files:**
- Modify: `docs/todos/new-agents-ux-professionalization.md`

- [ ] **Step 1: 扩大前端相关测试**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/docxExport.test.ts src/components/__tests__/ArtifactPane.test.tsx
```

Expected: PASS。

- [ ] **Step 2: 运行 lint、build、diff check**

Run:

```bash
cd tools/new-agents/frontend && npm run lint
cd tools/new-agents/frontend && npm run build
git diff --check
```

Expected: PASS。

- [ ] **Step 3: 更新 todo**

在 P1.7 进展记录中追加第十五块 CGA，说明 DOCX 表格和 styles part 已完成，剩余仍包括复杂编号、页眉页脚、Mermaid/结构化可视化图形嵌入和 PDF 图形化导出。
