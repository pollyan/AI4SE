# New Agents Artifact DOCX 包级导出设计

## Current State Gap Analysis

事实源快照：
- 已读取：`AGENTS.md`、`docs/strategy/goal-mode-playbook.md`、`docs/todos/new-agents-ux-professionalization.md`、`tools/new-agents/frontend/package.json`、`tools/new-agents/frontend/src/components/ArtifactPane.tsx`、`tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`。
- 当前工作区已有大量目标模式累计改动，继续在当前工作区推进；本切片限定写入 DOCX 导出 util、对应测试、ArtifactPane 接入和 todo/spec/plan。

能力包聚合：

| 能力包 | 聚合的原始缺口 | 用户动作链 / 工程信任闭环 | 为什么不能再拆薄 | 验收证据 |
| --- | --- | --- | --- | --- |
| 真正 DOCX 导出 | Artifact 协作体验里的“真正富文本 DOCX 导出”；当前只是 `.doc` HTML | 用户点击下载 -> Word -> 得到 `.docx` 包 -> Word/WPS 可识别标题、列表、表格、代码和文本 | 只改扩展名没有价值，必须生成 OOXML zip 包并覆盖内容安全 | util 单测 + ArtifactPane 下载测试 |
| 高保真 DOCX 样式 | 表格边框、标题样式、代码样式、中文字体、页眉页脚 | 下载 -> 打开后接近正式交付物模板 | 需要完整 styles.xml、numbering.xml 和复杂 Markdown AST，本轮过大 | 更广 OOXML 结构测试 |
| 导出服务端渲染 | 后端生成 docx，前端只下载 | 用户下载 -> 后端生成稳定文档 | 需要新 API、权限和文件流契约，不适合当前前端切片 | API/集成测试 |

排序结论：
1. 选择“真正 DOCX 导出”，因为它直接兑现 todo 中未完成项，并能显著提升交付专业感。
2. 高保真样式和服务端渲染暂缓；本轮先保证用户拿到标准 `.docx` 包，而不是 HTML 容器。

切片厚度门禁：
- 入口：ArtifactPane 下载菜单里的 `Word`。
- 动作：用户点击导出。
- 处理：前端把 Markdown 转为 WordprocessingML，再打包成最小 OOXML `.docx` zip。
- 可见结果：下载文件名为 `.docx`，MIME 为 OOXML，包内含 `[Content_Types].xml`、`_rels/.rels`、`word/document.xml`。
- 状态承接：不改变 artifact 内容、history 或服务端状态。
- 失败反馈：构建过程为同步纯函数；测试覆盖包结构和内容转义。
- 证据：新增 `docxExport` 单测，更新 ArtifactPane Word 下载测试，运行 lint/build。

## 用户故事

作为正在交付 New Agents 产出物的用户，我可以从右侧 ArtifactPane 下载真正的 `.docx` 文件，而不是 HTML 伪装的 `.doc`，从而更容易发给客户、在 Word/WPS 中继续编辑，并体现专业交付感。

## 验收条件

1. Given artifact 包含标题、段落、加粗、列表、表格和代码块
   When 生成 DOCX 包
   Then 输出为 ZIP/OOXML 包，包含标准 DOCX 必要文件和 `word/document.xml`。

2. Given artifact 包含 `<script>` 等 HTML 字符
   When 生成 DOCX 包
   Then `word/document.xml` 中只保留转义后的文本，不出现可执行 HTML 标签。

3. Given 用户在 ArtifactPane 点击 `Word`
   When 浏览器触发下载
   Then 文件名为 `<workflow>_artifact.docx`，Blob 类型为 `application/vnd.openxmlformats-officedocument.wordprocessingml.document`。

## 非目标

- 不引入新依赖。
- 不实现完整 Markdown AST。
- 不实现复杂 Word 样式、页眉页脚、图片、Mermaid 图形渲染。
- 不新增后端导出 API。
