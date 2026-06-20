# New Agents Artifact 冲突处理收尾能力包设计

## Current State Gap Analysis

事实源快照：
- 已读取：`AGENTS.md`、`docs/strategy/goal-mode-playbook.md`、`docs/todos/new-agents-ux-professionalization.md`、`tools/new-agents/frontend/src/components/ArtifactPane.tsx`、`tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`。
- 按需未展开：后端 artifact update API，本轮不改服务端契约；导出能力，本轮用户已明确不继续深做。

能力包聚合：

| 能力包 | 聚合的原始缺口 | 用户动作链 / 工程信任闭环 | 为什么不能再拆薄 | 验收证据 |
| --- | --- | --- | --- | --- |
| Artifact 冲突处理收尾能力包 | 编辑后保存遇到服务端新版本；同章节安全插入 / 改写可自动合并；不安全场景需要明确拒绝；用户需要继续手工处理和重试保存 | 用户编辑 Artifact -> 保存 -> 系统检测冲突 -> 安全场景自动合并或危险场景解释原因 -> 用户继续编辑 / 保存 -> 审计记录可追踪 | 只做一个 merge 分支会让用户仍然不知道哪些冲突不能自动处理；只做提示不补安全合并则主路径仍卡住 | ArtifactPane 组件测试、审计事件断言、全量组件回归、lint/build |
| 模型配置与供应商治理 | 默认供应商缺失、模型可见性、失败恢复动作 | 用户配置模型 -> 工作流使用 -> 出错时可诊断和恢复 | 与 Artifact 编辑冲突不是同一用户动作链，本轮合并会扩大风险面 | 后端配置测试、前端设置页测试 |

排序结论：
1. 选择 Artifact 冲突处理收尾能力包，因为它直接承接用户已在生产路径中使用的 Artifact 编辑能力，且当前已有未完成 RED 测试暴露安全合并和危险拦截缺口。
2. 模型配置与供应商治理暂不选，保留在 todo 中作为后续中优先级能力包。

切片准入判断：
- 用户功能包边界：本轮交付“Artifact 冲突处理收尾能力包”；并入同章节段落插入 / 改写安全自动合并、危险多段改写拦截、可读冲突原因、手工承接、审计和恢复验证；不并入复杂三方语义 merge、多人实时协同和导出增强。
- 用户可感知动作链：Artifact 编辑入口 -> 用户修改并保存 -> 遇到版本冲突 -> 系统给出自动合并或明确拒绝原因 -> 用户继续编辑 / 保存 -> 审计轨迹记录。
- 相邻缺口合并：把单个“插入 + 改写”算法场景上升为冲突处理闭环，不再只按 helper 分支推进。
- Superpowers 成本合理性：该能力包触达用户保存主路径、冲突提示、审计证据和回归测试，值得完整 CGA/spec/plan/TDD/验证。
- 过薄风险检查：不是单 parser / 单 helper；即使内部仍按多个 RED/GREEN 测试递进，验收边界以用户完成冲突处理为准。
- 能力增量句：完成后，用户现在可以在 Artifact 保存冲突中获得更可靠的自动合并和明确的手工处理承接，而不是卡在模糊冲突状态。

切片厚度门禁：
- 入口：Artifact 预览右上角编辑按钮和保存修改按钮。
- 动作：用户编辑 Artifact 后保存。
- 处理：系统基于 base/server/draft 三方内容判断是否可安全自动合并。
- 可见结果：安全场景显示 `自动合并非重叠变更`；危险场景显示明确的自动合并不可用原因和手工处理提示。
- 状态承接：自动合并写回编辑草稿并记录 `artifact_auto_merge_applied`；危险场景保留用户草稿和服务端版本，允许用户继续编辑后重试保存。
- 失败反馈：不安全场景不显示误导性自动合并入口，显示可读原因。
- 证据：RED/GREEN 组件测试、审计断言、ArtifactPane 全量测试、lint、build、`git diff --check`。
- 结论：通过。

## 用户故事

作为正在校准右侧产出物的用户，我可能在编辑 Artifact 时遇到 Agent 或服务端已经生成了新版本。当我保存发生版本冲突时，我希望系统能在可证明安全的情况下自动合并双方非重叠改动；如果不能自动合并，也要明确告诉我原因，并保留我的草稿，让我可以手工处理后重试保存。

## 范围

- 支持同一章节内普通段落的双向安全自动合并：
  - Server 改写一个旧段落，Draft 插入新普通段落。
  - Server 插入新普通段落，Draft 改写一个旧段落。
- 阻止不安全自动合并：
  - 插入侧还移动或重排旧段落。
  - 插入内容重复或旧段落无法唯一定位。
  - 改写侧同时改写多个旧段落。
  - 涉及列表、表格、fenced code / Mermaid / `ai4se-visual` 的结构化块。
- 在不安全场景下提供可读的不可自动合并原因，保留用户草稿、服务端版本和手工处理路径。
- 自动合并结果继续写回当前编辑草稿，沿用现有 `artifact_auto_merge_applied` 审计轨迹。
- 继续复用现有 ArtifactPane 冲突处理 UI、保存流程、typed runtime 和共享 store，不新增 agent-specific 或 workflow-specific 分支。

## 非目标

- 不实现复杂三方语义 merge 或逐词 merge。
- 不处理跨章节双方同时改写同一语义内容。
- 不新增多人实时协同、权限、分享和恢复中心。
- 不改变服务端 artifact update API。
- 不扩大 PDF/DOCX 或高保真可视化导出能力。

## 验收条件

1. 当 Server 改写同章节一个普通段落、Draft 插入同章节一个新普通段落时，冲突卡片显示 `自动合并非重叠变更`。
2. 点击自动合并后，textarea 草稿同时包含 Server 改写和 Draft 插入段落。
3. 反向场景（Server 插入、Draft 改写）也能自动合并。
4. 合并轨迹记录 `artifact_auto_merge_applied`，summary 为 `合并轨迹：自动合并服务端与草稿的同章节非重叠段落插入与改写`。
5. 如果插入侧还移动 / 重排段落、插入内容重复、或改写侧改写多个段落，则不显示自动合并入口。
6. 当自动合并不可用时，冲突提示显示可读原因，用户仍能看到并编辑当前草稿，之后可以再次保存。

## 风险

- 误把段落移动识别为插入，导致顺序错误。需要用 base 段落 key 的相对顺序校验拒绝。
- 重复段落会破坏唯一匹配。需要拒绝 base 或 target 中普通段落 key 不唯一的情况。
- 列表、表格、fenced block 被当作普通段落会误合并。继续复用 `parseSafeSectionParagraphBlocks` 的结构化块保护。
- 不可自动合并原因如果过细，会让 UI 变成技术错误列表；文案应保持用户可理解，避免暴露内部算法细节。

## 验证计划

- RED：在 `ArtifactPane.test.tsx` 新增同章节插入+改写正反例、不安全多段改写拒绝例、自动合并不可用原因例，先确认当前行为失败。
- GREEN：实现保守段落插入+改写合并 helper，补充不可自动合并原因推导，并接入现有冲突 UI。
- 聚焦验证：运行 `npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "paragraph insertion|auto-merge unavailable"`。
- 回归验证：运行段落/结构化块相关测试、`ArtifactPane` 全量测试、`npm run lint`、`npm run build`、`git diff --check`。
