# New Agents 策略 Mermaid 语法兼容计划

## Goal

把未合并旧分支中的 Mermaid 策略图兼容修复按当前主干重新落地，降低测试策略阶段 Mermaid 预校验失败概率。

## Architecture

继续使用共享 `tools/new-agents/frontend/src/core/utils/mermaidSanitizer.ts`，并在 `llm.ts` 的 artifact Mermaid 预校验路径接入 sanitizer。测试策略 prompt/template 只做保守格式约束和示例修正。

## Tasks

- [x] 做 CGA，确认主干 clean、旧分支未合并且不能直接 merge。
- [x] 写 RED 测试：
  - `mermaidSanitizer.test.ts` 覆盖 `quadrantChart` 单行标签和 `block-beta` 分组语法。
  - `llm.test.ts` 覆盖结构化 artifact Mermaid 预校验使用 sanitized diagram。
  - `mermaid.test.ts` 覆盖 `TEST_DESIGN/STRATEGY` 模板中的 `block-beta` 示例可解析。
- [x] 运行 RED，确认 4 个测试按预期失败。
- [x] 实现最小修复：
  - 扩展 `sanitizeMermaidCode`。
  - `validateMermaidBlocks` 调用 sanitizer 后再 parse。
  - 修正 `TEST_DESIGN/STRATEGY` prompt/template。
- [x] 运行定向 GREEN。
- [x] 运行扩展验证。
- [x] 提交到切片分支；待主分支快进合并并推送。

## Verification Commands

```bash
cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/mermaidSanitizer.test.ts src/core/__tests__/llm.test.ts src/core/__tests__/mermaid.test.ts
cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/mermaidSanitizer.test.ts src/core/__tests__/mermaid.test.ts src/core/__tests__/llm.test.ts src/components/__tests__/Mermaid.test.tsx
cd tools/new-agents/frontend && npm run lint
cd tools/new-agents/frontend && npm run build
git diff --check
```
