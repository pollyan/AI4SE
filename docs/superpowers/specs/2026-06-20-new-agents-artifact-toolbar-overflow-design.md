# New Agents Artifact 工具条收敛设计

## 背景

Header 已完成一级操作降噪，但右侧 ArtifactPane 仍把预览、代码、历史、编辑、批注、章节锁定、下载作为等权重图标排列。用户在右侧阅读产物时，协作和导出入口与阅读/编辑模式混在一起，容易误判当前最重要动作。

## 用户故事

作为 Lisa / Alex 工作流用户，当我查看右侧产出物时，我希望顶部工具条只突出当前阅读、历史和编辑这些高频动作；批注、章节锁定和导出仍然可发现，但不占据同等视觉权重。

## 方案

- 一级保留：`预览`、`代码`、`历史版本`、`编辑产出物`。
- 新增 Artifact 上下文菜单 `更多产物操作`，收纳：
  - `批注`
  - `章节锁定`
  - `下载 Markdown`
  - `下载 Word`
  - `下载 PDF`
- 菜单行为复用现有状态，不新增后端 API 或 store 字段。
- 打开批注或章节锁定时关闭菜单，并保持二者互斥。
- 下载仍调用现有 `handleDownload`，只改变入口位置。
- 保留现有 icon-only 风格，但给 `更多产物操作` 提供清晰 `title` 和 `aria-label`，提高可访问性。

## 非目标

- 不改变批注、章节锁定、下载、历史、编辑的业务逻辑。
- 不引入新的 Artifact 协作 schema。
- 不改 Header。
- 不做移动端专属布局重构。

## 验收条件

1. ArtifactPane 顶部一级按钮不再直接展示 `批注`、`章节锁定`、`下载`。
2. 点击 `更多产物操作` 后可看到 `批注`、`章节锁定`、`下载 Markdown`、`下载 Word`、`下载 PDF`。
3. 从菜单打开批注或章节锁定后，现有侧边面板行为保持不变。
4. 从菜单下载 Markdown/Word/PDF 后，现有导出内容测试继续通过。
5. 现有历史、编辑、预览、代码入口继续可用。

## 验证计划

- RED：`npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "artifact toolbar"`
- GREEN：同命令通过。
- 回归：`npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx`
- 静态检查：`npm run lint`
- 构建：`npm run build`
- 空白检查：`git diff --check`
