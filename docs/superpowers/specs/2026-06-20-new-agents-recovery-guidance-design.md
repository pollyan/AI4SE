# New Agents 失败恢复引导补齐设计

## Current State Gap Analysis

事实源快照：
- 已读取：`AGENTS.md`、`docs/strategy/goal-mode-playbook.md`、`docs/index.md`、`docs/todos/new-agents-ux-professionalization.md`。
- 已读取代码：`tools/new-agents/frontend/src/services/chatService.ts`、`tools/new-agents/frontend/src/components/ChatPane.tsx`、`tools/new-agents/frontend/src/core/agentCore.ts`、`tools/new-agents/frontend/src/core/llm.ts`、`tools/new-agents/frontend/src/components/Mermaid.tsx`、`tools/new-agents/frontend/src/components/ArtifactPane.tsx`。
- 已读取测试：`tools/new-agents/frontend/src/services/__tests__/chatService.test.ts`、`tools/new-agents/frontend/src/components/__tests__/ChatPane.test.tsx`、`tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`。
- 子智能体只读审计：结构化失败恢复、模型治理、Artifact 协作/导出三个方向均已完成候选审计。
- 工作树隔离：主工作区不是 linked worktree，且有两个无关 zip 脏文件；本轮在 `.worktrees/codex-new-agents-recovery-guidance` 分支 `codex/new-agents-recovery-guidance` 中执行。

能力包聚合：

| 能力包 | 聚合的原始缺口 | 用户动作链 / 工程信任闭环 | 为什么不能再拆薄 | 验收证据 |
| --- | --- | --- | --- | --- |
| 失败恢复引导补齐 | P0.2 连续失败补充信息、Artifact Mermaid 预校验失败归类、失败时阻断阶段确认 | 用户触发生成 -> 模型产物契约或 Mermaid 预校验失败 -> 左侧出现恢复卡 -> 连续失败时引导补充信息而非盲目重试 -> 阶段确认隐藏 -> 右侧产物保持不变 | 只改错误文案无法证明重试/阶段确认行为；只改 ChatPane 无法证明 llm/chatService 的 Mermaid 预校验错误能进入恢复卡 | `chatService.test.ts`、`ChatPane.test.tsx` |
| 模型治理闭环 | P1.6 供应商失败卡片到设置/检测/运行统计联动 | 用户遇到供应商失败 -> 进入设置检测 -> 运行统计看到 provider/错误类型 | 横跨后端 observability、设置弹窗、Header 统计和 provider error 分类，适合单独中等切片 | Header/Settings/backend observability tests |
| Artifact 语义三方合并 | P1.7 更完整 merge 改写/移动语义 | 用户编辑产物遇到 409 -> 系统识别安全改写/移动 -> 自动合并或明确降级人工 | 属于 Artifact 协作 P1 主线，需纯函数 merge core + ArtifactPane 接线；不应混入 P0 恢复链路 | 新 `artifactThreeWayMerge.test.ts` + ArtifactPane tests |

候选 gap：

| 候选 | 来源 | 目标态 | 当前能力 | 缺口 | 价值 | 风险/复杂度 | 可测试性 | 去向 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 失败恢复引导补齐 | todo P0.2 / explorer 审计 | 结构化、retry exhaustion、Artifact Mermaid 预校验失败都进入恢复卡；连续失败出现补充信息引导；失败时不显示阶段确认 | 已有单次结构化失败恢复卡和重试；供应商失败恢复卡；右侧 Mermaid 块可手动修复 | 连续失败只是文案，没有独立动作；`Artifact Mermaid parse failed` 仍落普通 `**Error:**`；阶段确认保护依赖错误是否已被格式化 | 直接影响主链路可恢复性和用户信任 | 中等，主要在前端服务和 ChatPane | 聚焦 Vitest | 本轮 |
| 模型治理联动 | todo P1.6 / explorer 审计 | 失败卡片、设置检测和运行统计互相打通 | 设置、检测、统计、友好 provider card 均存在 | 检测不入统计，失败卡片没有设置/检测入口，错误码不细 | 提升诊断效率 | 中高，跨前后端 | 前后端测试 | 下一轮候选 |
| Artifact 语义三方合并 | todo P1.7 / explorer 审计 | 安全改写/移动自动合并，冲突明确降级 | 已有行/块合并和部分自动合并 | 移动、改写+插入、重复锚点语义不成 core 契约 | 协作价值高 | 中等，需从组件抽 core | 纯函数 + UI tests | 下一轮候选 |

排序结论：
1. 选择“失败恢复引导补齐”，因为它是 P0，直接补齐用户截图里提到的“提示让重试但缺少手段/引导”的主链路缺口。
2. 模型治理联动暂缓为下一轮候选，因为它是 P1，且跨后端统计、Header、Settings，边界更大。
3. Artifact 语义三方合并暂缓为下一轮候选，因为它也是 P1，适合独立 worktree worker 处理。

切片准入判断：
- 用户可感知动作链：用户生成当前阶段 -> 模型输出结构或 Mermaid 失败 -> 左侧恢复卡说明右侧产物未变 -> 用户可选择重试或补充信息后再试 -> 阶段确认不会误导进入下一阶段。
- 相邻缺口合并：合并结构化失败、retry exhaustion、Artifact Mermaid 预校验失败和连续失败补充信息，不把单个文案或按钮拆成独立切片。
- Superpowers 成本合理性：该切片跨 service、ChatPane 和阶段确认行为，值得完整 CGA/spec/plan/TDD。
- 过薄风险检查：不是单按钮；完成后改变失败归类、恢复操作和阶段推进保护。
- 能力增量句：完成后，用户现在可以在连续结构化/Mermaid 失败时明确选择补充信息后再试，而不会带着无效产物进入下一阶段。

切片厚度门禁：
- 入口：New Agents Workspace 左侧对话和右侧 artifact 生成。
- 动作：用户触发生成或 retry，遇到结构化/Mermaid 预校验失败。
- 处理：chatService 将错误归类为恢复型失败；ChatPane 根据失败上下文展示重试或补充信息操作；阶段确认被隐藏。
- 可见结果：恢复卡、右侧产物保持不变、连续失败补充信息引导。
- 状态承接：补充信息写入输入框并聚焦，由用户编辑后发送；失败消息留在 chat history 作为上下文外控制反馈。
- 失败反馈：无法归类的普通错误仍以普通错误展示；恢复型错误明确提示原因和下一步。
- 证据：RED/GREEN 的 `chatService.test.ts` 与 `ChatPane.test.tsx`。
- 结论：通过。

## 用户故事

作为 New Agents 用户，当当前阶段生成连续失败，或模型生成了无法通过 Mermaid / artifact 契约校验的产物时，我希望系统明确告诉我右侧产物没有被污染，并提供“重试”与“补充信息后再试”的清晰路径，避免我被阶段确认按钮误导继续推进。

## 目标行为

- `Artifact Mermaid parse failed` 和同类 artifact 可视化预校验失败要进入 `结构化输出生成失败` 恢复消息，而不是普通 `**Error:**`。
- 连续结构化恢复失败时，ChatPane 恢复卡显示 `补充信息后再试` 操作。
- 点击 `补充信息后再试` 不直接发送请求；它把输入框填入可编辑的补充提示，并聚焦输入框。
- 最新 assistant 消息为恢复型失败时，阶段确认卡片不显示。
- 单次失败仍保留 `重试本阶段生成`。

## 范围

进入本轮：
- `chatService` 恢复型错误归类。
- `ChatPane` 连续失败识别与补充信息操作。
- 聚焦测试。
- todo 进展记录。

不进入本轮：
- 不实现 ArtifactPane 运行时 Mermaid 渲染失败向 ChatPane 主动广播。
- 不实现 `ai4se-visual` 预览错误的跨栏提示。
- 不做模型设置/运行统计联动。
- 不做 Artifact 三方 merge 改写/移动语义。

## 验收条件

1. Given `generateResponseStream` 抛出 `Artifact Mermaid parse failed`
   When 用户发送消息
   Then chat history 中出现 `结构化输出生成失败`，不出现普通 `**Error:**`，artifact 保持不变。
2. Given 最新两次 assistant 消息都是结构化输出失败
   When ChatPane 渲染最新恢复卡
   Then 用户能看到 `补充信息后再试`，点击后输入框出现补充信息提示且不会立即发送。
3. Given 存在 pending stage transition 且最新消息是恢复型失败
   When ChatPane 渲染
   Then 阶段确认卡片不出现。

## 风险

- 失败次数基于 chat history 文本识别，未来若改为结构化 message meta 需要迁移。
- 本轮不处理右侧 Mermaid runtime 渲染失败的跨栏提示，因为那需要 ArtifactPane 与 ChatPane 的共享状态事件，适合后续小切片。

## 验证计划

- `cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/chatService.test.ts src/components/__tests__/ChatPane.test.tsx`
- `cd tools/new-agents/frontend && npm run build`
- `git diff --check`
