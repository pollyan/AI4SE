# Artifact Word 兼容导出设计

## 背景

`docs/todos/new-agents-evolution.md` #11 要求 Word / PDF / Markdown 多格式导出。当前 ArtifactPane 只有 Markdown 下载按钮，用户如果要把产出物发给非技术协作者，还需要手工复制到文档工具。

## 用户故事

作为 New Agents 用户，我希望在右侧产出物中选择导出格式，除了现有 Markdown 外，还能下载一个 Word 可打开的 `.doc` 文件，从而把当前 artifact 快速交给不使用 Markdown 的协作者审阅。

## 范围

进入本轮：

- 将 ArtifactPane 下载按钮改为导出菜单。
- 保留现有 Markdown 导出行为和文件名。
- 新增 Word 兼容 `.doc` 导出，内容为一个简单 HTML 文档，包含当前 Markdown 文本的安全转义版本。
- 补充组件测试覆盖 `.doc` 文件名、MIME type 和内容。

不进入本轮：

- 不引入 docx/pdf 生成依赖。
- 不做 Markdown 到富文本的完整语义渲染。
- 不做 PDF 导出。
- 不改变 Header 的“导出报告”按钮。

## 验收条件

1. 点击下载按钮后用户可以选择 Markdown 或 Word。
2. Markdown 选项保持原有 `${workflow}_artifact.md` 下载。
3. Word 选项生成 `${workflow}_artifact.doc`，MIME type 为 `application/msword`。
4. Word 导出内容包含转义后的当前 artifact 文本，不执行 HTML。
5. 相关 ArtifactPane 测试、TypeScript 检查和 `git diff --check` 通过。
