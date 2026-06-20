# New Agents Artifact 审阅面板处理闭环设计

## 用户故事

作为正在校准 Lisa / Alex 产出物的用户，当我打开 `更多产物操作 -> 审阅` 时，我希望不只是看到未解决批注、失效锚点、锁定章节、最近轨迹和最近版本，还能直接处理或跳到正确的处理区域，从而把审阅面板从只读摘要升级为可操作的审阅中心。

## Current State Gap Analysis 摘要

| 能力包 | 当前能力 | 缺口 | 本轮结论 |
| --- | --- | --- | --- |
| Artifact 审阅面板处理闭环 | 已有只读审阅面板、批注状态、锚点定位/重绑、章节锁、历史版本和活动轨迹 | 审阅面板只能看，不能直接处理或进入对应面板 | 本轮实现 |
| 更复杂三方 merge 解析 | 已覆盖章节、段落、列表、表格、fenced block 等大量安全自动合并场景 | 剩余场景边界不清，容易变成单算法分支 | 下一轮需重新聚合成完整冲突场景 |
| Todo 范围收敛 | 已有产品决策记录 | 历史进展中仍有散落“剩余”描述 | 随本轮同步记录，不单独作为 milestone |

## 范围

本轮进入范围：

- 审阅面板中的未解决批注提供处理入口：
  - 可直接 `标记已解决`。
  - 可定位仍有效的正文锚点。
  - 锚点失效时可提示用户进入批注面板完成重新绑定。
- 审阅面板中的锁定章节提供入口，直接打开章节锁定面板。
- 审阅面板中的最近版本提供入口，直接切换到历史版本视图。
- 这些动作复用现有 store、批注、锁定章节、历史版本和 ArtifactPane 状态，不新增 agent-specific 或 workflow-specific 分支。
- 更新 `docs/todos/new-agents-ux-professionalization.md`，记录本轮完成情况和后续候选。

本轮不进入范围：

- 不做多人实时协同、分享权限或恢复中心。
- 不重启高保真 PDF 图片级导出。
- 不新增新的三方 merge 自动合并算法分支。
- 不引入独立的 Artifact 审阅后端 API；继续复用现有 run collaboration snapshot。

## 场景

1. Given 当前阶段有未解决批注，When 用户打开审阅面板并点击处理按钮，Then 该批注可以直接标记为已解决，并从待处理列表中消失。
2. Given 当前阶段有带有效 `anchorText` 的批注，When 用户在审阅面板点击定位，Then 右侧产出物切回预览并高亮对应正文。
3. Given 当前阶段有锚点失效的批注，When 用户在审阅面板选择处理，Then 系统打开批注面板，让用户使用现有 `重新绑定选区` 流程，并保留无选区时的可读错误。
4. Given 当前阶段有锁定章节，When 用户在审阅面板点击管理锁定章节，Then 系统打开章节锁定面板，并关闭审阅面板避免浮层叠加。
5. Given 当前阶段有历史版本，When 用户在审阅面板点击查看版本，Then 系统切换到历史版本视图，让用户继续查看 diff / 恢复。

## 验收条件

1. 审阅面板的未解决批注可以在面板内标记已解决，状态更新后不再显示为待处理项。
2. 审阅面板的有效锚点批注可以定位正文，复用现有高亮行为。
3. 审阅面板的失效锚点批注可以打开批注面板承接重新绑定，且无有效选区时仍显示现有错误提示。
4. 审阅面板的锁定章节入口可以打开章节锁定面板。
5. 审阅面板的最近版本入口可以进入历史版本视图。
6. 所有实现继续复用共享 ArtifactPane/store，不新增 Lisa/Alex 或 workflow 专属状态。

## 风险

- `ArtifactPane.tsx` 已较大，本轮应避免重构无关区域，只在审阅面板和少量复用函数边界内修改。
- 审阅面板内直接处理批注会改变持久化协作状态，必须复用现有 `setArtifactCommentStatus` 和同步逻辑。
- 多浮层状态容易重叠，本轮必须在打开批注/章节锁定/历史视图时关闭审阅面板。
- 锚点重新绑定依赖浏览器选区，组件测试应覆盖无选区错误路径，避免误写空锚点。

## 验证计划

- RED：`npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "artifact review panel"`，新增断言先失败。
- GREEN：同一聚焦命令通过。
- 回归：`npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx`。
- 状态相关回归：`npm run test -- --run src/__tests__/store.test.ts -t "artifact comment"`。
- 扩大验证：`npm run lint`、`npm run build`、必要时 `npm run test`、`git diff --check`。

