# New Agents Observability Alert Actions Design

## Current State Gap Analysis

事实源快照：
- 已读取：`docs/todos/new-agents-ux-professionalization.md`、`tools/new-agents/frontend/src/components/Header.tsx`、`tools/new-agents/frontend/src/components/ChatPane.tsx`、`tools/new-agents/frontend/src/components/SettingsModal.tsx`、`tools/new-agents/frontend/src/core/observabilityAlerts.ts`、`tools/new-agents/frontend/src/components/__tests__/Header.test.tsx`。
- 子 Agent 事实源：Kant 建议本轮选择“运行统计供应商告警动作链”，因为它直接补模型配置与供应商治理中“从告警到操作”的缺口，冲突范围低；Bernoulli 建议 DOCX 更多 Mermaid 嵌入，作为下一候选。
- 当前主仓库仅有两个 unrelated intent-test-proxy zip 修改，本轮不触碰。

能力包聚合：

| 能力包 | 聚合的原始缺口 | 用户动作链 / 工程信任闭环 | 为什么不能再拆薄 | 验收证据 |
| --- | --- | --- | --- | --- |
| 运行统计供应商告警动作链 | 模型连接检测结果、provider 错误归因、高失败率告警与运行统计联动 | 用户打开运行统计 -> 看到模型/供应商异常告警 -> 直接打开设置或检测连接 -> 看到检测结果 | 只展示告警文字仍需要用户自己找设置入口；只抽 service 也没有用户价值 | Header 测试 + config service 测试 |
| DOCX 更多 Mermaid 图片嵌入 | Artifact 剩余导出增强 | 用户下载 DOCX -> 更多 Mermaid 类型显示真实图片 | 与模型治理无关，且上轮刚完成 Artifact 协作切片 | docxExport 测试 |

排序结论：
1. 选择运行统计供应商告警动作链。它补齐 P1 #6 的最后一段用户动作链，文件范围小，适合 worker 独立完成。
2. DOCX 更多 Mermaid 类型嵌入保留为下一候选。
3. Artifact 移动语义自动合并暂缓，因为 `ArtifactPane.tsx` 热点冲突和误合并风险更高。

## 用户故事

作为看到运行统计中“模型/供应商异常集中”的用户，我可以在同一个弹窗里直接打开模型设置或检测连接，快速判断问题是 API Key、额度、网络还是模型配置，而不是再去顶部更多菜单里寻找入口。

## 验收条件

1. Given 运行统计存在 `provider-issues` 告警
   When 用户打开运行统计
   Then 告警卡片显示 `打开模型设置` 和 `检测连接`。

2. Given 用户点击 `打开模型设置`
   Then 全局设置弹窗打开，运行统计弹窗仍不丢失当前上下文。

3. Given 用户点击 `检测连接`
   When `/new-agents/api/config/check` 返回成功
   Then 告警卡片显示后端成功 message 或默认成功文案。

4. Given 用户点击 `检测连接`
   When `/new-agents/api/config/check` 返回失败或网络异常
   Then 告警卡片显示后端 error/message 或默认失败文案。

5. Given 运行统计只有普通失败告警、阶段告警或供应商成功率告警
   Then 不显示模型设置/检测连接动作，避免无关告警堆按钮。

## 边界

- 不改后端 observability API。
- 不改 ChatPane / SettingsModal 现有 UI 行为；只可抽取共享检测 service，必要时 Header 先使用。
- 不新增 workflow-specific 模型配置分支。
- 不触碰 ArtifactPane、DOCX/PDF 导出和 intent-tester zip。

## 验证计划

- `cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/configService.test.ts src/components/__tests__/Header.test.tsx`
- `cd tools/new-agents/frontend && npm run lint`
- `cd tools/new-agents/frontend && npm run build`
- `git diff --check`
