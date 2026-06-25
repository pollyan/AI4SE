# New Agents 右侧可视化诊断重复提示 UX 修复记录

状态：已完成
创建日期：2026-06-25
完成日期：2026-06-25
相关模块：`tools/new-agents/frontend`
用户反馈来源：本地 UI 截图，Lisa / 产物诊断对话区

## 背景

用户在 Lisa 产物诊断界面看到左侧对话区仍展示一张较大的提示卡：

- 标题：`右侧产物有可视化需要处理`
- 正文：`图表或结构化可视化未能稳定渲染，右侧产物已保留诊断入口。`
- 操作：`查看诊断详情`、`查看问题位置`

用户反馈：这类错误信息上方已经有了，没有必要在左侧再次重复显示。当前卡片会占用对话区空间，且和已有错误信息形成重复提醒。

## 完成内容

- 移除 `ChatPane` 对 `artifactVisualDiagnostics` 的订阅和左侧大块可视化诊断提示卡。
- 保留右侧 `ArtifactPane` 的 visual diagnostic 记录、诊断显示、定位锚点和 focus 高亮能力。
- 更新 `ChatPane` 测试：当前阶段存在 visual diagnostic 时，左侧不显示 `右侧产物有可视化需要处理`、`查看诊断详情` 或 `查看问题位置`。

## 验收结果

- 当右侧产物已经有可视化诊断入口时，左侧对话区不再显示重复大卡片。
- 用户仍可以从右侧产物查看诊断详情并定位问题块。
- 未改变 Agent Runtime SSE、artifact visual diagnostics store、错误折叠详情、阶段推进或重试逻辑。

## 验证

- `cd tools/new-agents/frontend && npm run test -- src/components/__tests__/ChatPane.test.tsx`：通过，33 tests。
- `cd tools/new-agents/frontend && npm run test -- src/components/__tests__/ArtifactPane.test.tsx -t "diagnostic"`：通过，5 tests。
- `cd tools/new-agents/frontend && npm run lint`：通过。

## 非目标

- 不改变后端错误 code taxonomy。
- 不隐藏右侧产物中的真实可视化错误。
- 不伪造可视化渲染成功。
- 不为 Lisa 单独创建专属错误展示逻辑。
