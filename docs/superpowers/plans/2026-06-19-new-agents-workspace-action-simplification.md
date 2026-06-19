# New Agents 工作区操作降噪计划

## 范围

本计划对应 `docs/todos/new-agents-ux-professionalization.md` 的 P0「工作区顶部操作收敛」中可前端独立交付的第一块：Header 操作分层、Header 导出入口移除、ArtifactPane 生成态假进度条移除。

## 步骤

1. 补充 Header 测试：
   - 一级区保留新会话、历史会话、更多操作。
   - Header 不再出现导出报告。
   - 更多菜单可触发上下文摘要、运行统计、TEST_DESIGN 测试资产。

2. 补充 ArtifactPane 测试：
   - 生成态仍显示构建文案和加载动画。
   - 生成态不再包含装饰性横向进度条。

3. 实现 Header：
   - 删除 Header 导出实现和导出按钮。
   - 新增更多菜单状态和入口。
   - 将上下文摘要、运行统计、测试资产、设置移入更多菜单。

4. 实现 ArtifactPane：
   - 删除横向假进度条。
   - 保留已有生成文案和柱状 pulse 动画。

5. 验证：
   - 运行 Header 与 ArtifactPane 聚焦测试。
   - 运行 `git diff --check`。
   - 更新 todo 文件记录本切片进展与验证命令。
