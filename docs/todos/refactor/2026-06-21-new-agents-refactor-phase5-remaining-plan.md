# New Agents 智能体重构阶段 5 剩余路线计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` for serial implementation. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 校准 New Agents 全面重构剩余范围，确保后续不只在 backend 小切片内推进，而是覆盖 frontend、UI、persistence 和最终全链路验证。

**Architecture:** 继续保留单一 Agent Runtime、单一 typed SSE 主链路、单一共享 Zustand store 和共享 UI 基础设施。后续拆分只做模块边界和纯 helper 提取，不新增 Lisa/Alex 专属 runtime、transport、store、API/SSE path 或 rendering pipeline。

**Tech Stack:** Python 3.11, Flask, SQLAlchemy, pytest, TypeScript 5.x, React 19, Zustand, Vitest.

---

## 当前进度

- 已完成：目标模式第 1-7 轮。
- 当前状态：阶段 1/2 的契约和 registry 主线已完成；阶段 3/4 已开始模块边界重组，但目前主要覆盖 backend route 和 test assets。
- 剩余重点：`ArtifactPane.tsx`、`run_persistence.py`、frontend store/workflow adapter 收尾、最终全链路回归。

## 剩余轮次估算

按每轮一个可回滚 commit、每轮有 RED/GREEN/验证证据的口径，剩余预计 `4-6` 轮。

| 轮次 | 内容 | 目标边界 | 主要验证 | 是否必须 |
| --- | --- | --- | --- | --- |
| 第 8 轮 | `ArtifactPane.tsx` 第一批拆分 | 拆 PDF/export/Markdown projection 纯 helper，不改下载 UI 和文件格式 | `ArtifactPane.test.tsx` PDF/download tests、helper unit tests、frontend targeted Vitest | 是 |
| 第 9 轮 | `ArtifactPane.tsx` 第二批拆分 | 拆 diff/merge/automerge 纯 helper，不改编辑器和冲突处理用户行为 | `ArtifactPane.test.tsx` merge/diff/automerge tests、helper unit tests | 是 |
| 第 10 轮 | `run_persistence.py` 边界拆分 | 拆 snapshot/list/serialization 或 collaboration helper，不改 DB schema/API | `test_run_persistence.py`、agent endpoint tests | 是 |
| 第 11 轮 | frontend store/workflow adapter 收尾 | 检查 `store.ts`、`workflowRegistry.ts`、services 是否还有重复映射或过宽 helper | store、workflow config、services targeted tests | 视第 8/9 轮结果决定 |
| 第 12 轮 | 全链路回归与文档收束 | 汇总验证、补齐计划执行记录，判断是否需要 E2E/LLM judge | backend/frontend aggregate targeted suites、必要 E2E smoke | 是 |
| 可选第 13 轮 | UI 组件继续拆分 | 若 `ArtifactPane.tsx` 仍明显过大，再拆 review/history/collaboration 子组件 | ArtifactPane component tests、必要截图 | 可选 |

最短收束路线：第 8、9、10、12 轮。

完整收束路线：第 8、9、10、11、12 轮；如果 UI 文件仍过大，再进入可选第 13 轮。

## 为什么第 8 轮转向前端

`ArtifactPane.tsx` 当前约 6000 行，是 New Agents 前端最大模块，承担：

- Markdown rendering。
- Artifact comments、section locks、review panel。
- Markdown/Word/PDF download。
- PDF Mermaid/structured visual projection。
- Artifact edit/history/diff/merge/automerge。
- Visual diagnostics focus。

此前第 6/7 轮只覆盖 backend route 和 test assets parsing，虽然有价值，但不足以代表“全面重构”。因此第 8 轮必须转向前端，并先选择最容易验证的 PDF/export 纯 helper 区域。

## 第 8 轮：ArtifactPane PDF/export helper 拆分

### 目标

从 `tools/new-agents/frontend/src/components/ArtifactPane.tsx` 中拆出 PDF/export 相关纯逻辑到新模块，保持下载菜单、文件名、Markdown/DOCX/PDF 输出语义不变。

### 文件范围

- Create: `tools/new-agents/frontend/src/core/artifactExport.ts`
- Create: `tools/new-agents/frontend/src/core/__tests__/artifactExport.test.ts`
- Modify: `tools/new-agents/frontend/src/components/ArtifactPane.tsx`
- Run: `tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`

### 候选迁移内容

- `toUtf16BeHex`
- `stripInlineMarkdown`
- `formatPdfTableRows`
- Mermaid PDF parse/project helpers
- structured visual table projection helpers
- `projectMarkdownToPdfDocument`
- `buildPdfTableDrawingCommands`
- `buildPdfMermaidDrawingCommands`
- `buildPdfContentStream`
- `buildPlainTextPdf`

不在第 8 轮迁移：

- DOM selection/comment helper。
- Artifact edit/history/diff/merge/automerge。
- React state、toolbar menu、modal/panel UI。
- `downloadBlob` 和 `handleDownload` 可以暂留在组件中，只调用导出的 pure builder。

### TDD 任务

- [ ] **Step 1: RED helper tests**

  新增 `artifactExport.test.ts`，锁定：

  - PDF 以 `%PDF-1.4` 开头。
  - 中文内容以 UTF-16BE hex 出现在 PDF。
  - Mermaid timeline/mindmap/pie/journey 关键文本会被投影到 PDF。
  - structured visual table 关键文本会被投影到 PDF。

- [ ] **Step 2: create `artifactExport.ts`**

  移入 pure helper。模块不得 import React、Zustand、DOM API、services 或 component。

- [ ] **Step 3: wire `ArtifactPane.tsx`**

  组件继续处理 UI、Blob、anchor click 和 filename；PDF 内容由 `buildPlainTextPdf` 生成。

- [ ] **Step 4: remove duplicate helpers**

  删除组件中已迁移 helper 和 type，避免两套 PDF projection 逻辑并存。

- [ ] **Step 5: run verification**

  ```bash
  cd tools/new-agents/frontend
  npm run test -- --run src/core/__tests__/artifactExport.test.ts src/components/__tests__/ArtifactPane.test.tsx
  git diff --check
  ```

## 第 9 轮：ArtifactPane diff/merge helper 拆分

第 9 轮只在第 8 轮通过后启动。目标是把 diff/merge/automerge 纯逻辑拆到 `core/artifactMerge.ts` 或相近模块，不改编辑器 UI 和冲突处理行为。

## 第 10 轮：run_persistence 边界拆分

第 10 轮回到 backend，目标是在已有前端大模块拆分后处理 `run_persistence.py`。优先拆 snapshot/list/serialization helper 或 collaboration helper，不改数据库 schema、不改 API response shape。

## 第 11 轮：frontend store/workflow adapter 收尾

第 11 轮视第 8/9 轮结果决定是否执行。重点检查 registry adapter、store helper、services 是否仍存在重复 workflow/stage 映射或过宽职责。

## 第 12 轮：全链路回归与文档收束

最后一轮必须做 completion audit：

- 检查阶段 1-5 文档执行记录。
- 跑 backend contract/runtime/persistence/test assets targeted suites。
- 跑 frontend workflow/parser/store/services/ArtifactPane targeted suites。
- 如 prompt/artifact quality 或用户可见 workflow 行为被改动，再跑 Lisa/Alex 浏览器 E2E 或 LLM judge。
- 明确记录没有新增 agent-specific runtime、transport、store、SSE/API path 或 bespoke rendering pipeline。

## 每轮 Summary 要求

每轮完成后必须向用户报告：

- 总体轮次和剩余估算。
- 本轮目标。
- 本轮改动。
- 验证命令和结果。
- Commit。
- 下轮建议。
- 风险或阻塞。
