# New Agents Artifact DOCX 包级导出实施计划

## 范围

实现前端最小 OOXML `.docx` 导出，替换当前 Word-compatible HTML `.doc` 导出。

## TDD 步骤

1. RED：新增 `src/core/__tests__/docxExport.test.ts`，断言 `buildDocxPackage` 生成 ZIP 头、包含 `[Content_Types].xml`、`_rels/.rels`、`word/document.xml`，并能从无压缩 ZIP 中读回 document XML。
2. RED：在同一测试中断言 Markdown 标题、列表、表格、代码块和转义文本进入 `word/document.xml`，且不出现 `<script>`。
3. RED：更新 ArtifactPane Word 下载测试，期望 `.docx` 文件名和 OOXML MIME。
4. GREEN：实现 `src/core/docxExport.ts`，包含轻量 Markdown 到 WordprocessingML 投影、XML 转义、CRC32 和无压缩 ZIP 打包。
5. GREEN：ArtifactPane 复用 `buildDocxPackage`，将 Word 下载 Blob 改为 `.docx`。
6. REFACTOR：删除 ArtifactPane 内不再使用的 HTML Word 导出 helper，减少组件负担。
7. 验证：运行 `npm run test -- --run src/core/__tests__/docxExport.test.ts src/components/__tests__/ArtifactPane.test.tsx`、`npm run lint`、`npm run build`、`git diff --check`。

## 风险控制

- 无新增依赖，避免网络安装和包体变化。
- ZIP 使用 store 模式，便于单测直接验证内容。
- 只影响 Word 下载路径，不改变 artifact state、history、服务端 run snapshot 或 PDF/Markdown 下载。
