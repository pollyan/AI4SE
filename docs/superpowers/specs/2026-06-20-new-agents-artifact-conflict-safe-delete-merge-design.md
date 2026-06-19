# Artifact 冲突安全删除自动合并设计

## Current State Gap Analysis

事实源快照：
- 已读取：`AGENTS.md`、`docs/strategy/goal-mode-playbook.md`、`docs/index.md`、`docs/todos/new-agents-ux-professionalization.md`、`tools/new-agents/frontend/src/components/ArtifactPane.tsx`、`tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`。
- 当前工作区：主目录不是 linked worktree；只剩 `dist/intent-test-proxy.zip` 与 `tools/intent-tester/frontend/static/intent-test-proxy.zip` 两个未提交遗留文件。本轮主 Agent 只做调度和文档集成，代码实现交给 worker 的独立工作区。

能力包聚合：

| 能力包 | 聚合的原始缺口 | 用户动作链 / 工程信任闭环 | 为什么不能再拆薄 | 验收证据 |
| --- | --- | --- | --- | --- |
| 安全三方自动合并扩展 | todo 第 30 块剩余“更完整三方 merge 的删除/改写/移动语义” | 用户保存人工编辑遇到版本冲突 -> 系统识别服务端只插入、草稿只删除旧行 -> 用户点击自动合并 -> 草稿同时保留服务端新增并应用用户删除 -> 活动轨迹可追溯 | 只做按钮或只做 helper 都不能形成用户可见闭环；必须覆盖入口、合并结果、审计轨迹和保守降级 | ArtifactPane RED/GREEN 测试、相关组件测试 |
| 复杂 Mermaid/SVG 高保真导出 | todo 第 28 块剩余复杂 Mermaid/SVG 高保真嵌入 | 用户导出 PDF -> 复杂图形更接近原图 | 需要图形解析/渲染策略，风险高于当前协作主链路 | PDF 导出单测和视觉结构检查 |

候选 gap：

| 候选 | 来源 | 目标态 | 当前能力 | 缺口 | 价值 | 风险/复杂度 | 可测试性 | 去向 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 安全删除自动合并 | Artifact 协作剩余项 | 自动合并可覆盖“服务端插入 + 用户删除旧行”的安全场景 | 只支持双方均为插入的自动合并 | 用户删除旧结论时仍要手工处理冲突 | 直接减少人工编辑冲突成本，增强“编辑会影响后续工作流”的可信度 | 中等；必须避免误合并改写/移动 | 组件测试可构造冲突并断言草稿和 audit event | 本轮 |
| 复杂 Mermaid/SVG 高保真 PDF | 可视化导出剩余项 | PDF 中复杂 Mermaid 更接近浏览器渲染 | 仅支持简单 flowchart 矢量投影，其他类型摘要降级 | 高复杂图仍不够专业 | 提升交付美观度 | 高；涉及布局/解析或渲染依赖 | 需要更复杂 PDF 内容验证 | 下一轮候选 |

排序结论：
1. 选择“安全删除自动合并”，因为它延续当前 Artifact 协作主线，用户可感知动作链完整，且可以用保守算法把风险控制在可验证范围内。
2. Mermaid/SVG 高保真导出暂缓，因为当前已有简单 flowchart 投影和语义摘要兜底，下一步需要单独设计图形渲染边界。

切片厚度门禁：
- 入口：现有保存冲突卡片中的 `自动合并非重叠变更`。
- 动作：用户点击自动合并。
- 系统处理：基于旧版、服务端版本、用户草稿做保守三方合并。
- 可见结果：编辑草稿更新为合并结果。
- 状态承接：用户仍需点击 `保存修改` 走现有服务端冲突检测。
- 失败反馈：不满足安全条件时不显示自动合并入口，保留现有对比/刷新/逐行/块级处理。
- 证据：新增组件测试先失败后通过；相关 ArtifactPane 测试通过。

## 用户故事

作为在右侧人工校准产出物的用户，我希望当服务端在我编辑期间补充了新内容，而我只是删除了旧版中某些不再需要的行时，系统能帮我自动合并两边的非冲突变更。这样我不需要逐行处理冲突，也不用担心丢掉服务端的新产出。

## 目标行为

- 当 `artifactContent` 是编辑开始前的旧版、`conflictArtifact.content` 是服务端当前版本、`editDraft` 是用户草稿时，系统尝试构造合并草稿。
- 安全合并只覆盖以下条件：
  - 服务端版本相对旧版没有删除或改写旧行，只允许插入新行。
  - 用户草稿相对旧版允许删除旧行，也允许插入补充行。
  - 用户草稿保留下来的旧行仍按旧版顺序出现，不能移动。
- 合并结果应以旧版顺序为骨架：
  - 对被用户删除的旧行，不再输出。
  - 对用户保留的旧行，输出前合并同一锚点处的服务端插入和用户插入，去重并保持服务端插入优先。
  - 旧版末尾后的插入同样合并。
- 如果合并结果没有引入任何用户侧变化，或者结果与服务端版本完全相同，不显示自动合并入口。
- 如果出现服务端删除/改写、用户移动旧行、锚点无法匹配等不安全情况，不显示自动合并入口。

## 范围

进入本轮：
- 更新 ArtifactPane 自动合并 helper，使其支持安全删除场景。
- 新增一个冲突组件测试，覆盖“服务端插入 + 用户删除旧行 + 用户插入补充”的合并结果和 audit event。
- 更新 todo 进展记录。

不进入本轮：
- 不实现复杂改写/移动语义自动合并。
- 不修改服务端 API 或 artifact snapshot 结构。
- 不改变现有逐行/块级手工合并能力。
- 不处理 PDF Mermaid/SVG 高保真导出。

## 风险与约束

- 自动合并宁可不出现，也不能误合并。无法证明旧行顺序和锚点关系时必须返回 `null`。
- `ArtifactPane.tsx` 已经较大，本轮不做文件拆分，避免扩大集成风险。
- worker 只能修改 ArtifactPane 相关测试和实现文件；主 Agent 统一更新 todo 和执行最终验证。

## 验收条件

1. Given 旧版包含 `背景 / 旧风险 / 共同内容`，服务端当前版本只新增 `服务端补充`，用户草稿删除 `旧风险` 并新增 `用户补充`；When 用户点击 `自动合并非重叠变更`；Then 编辑草稿同时保留服务端补充、用户补充和共同内容，并移除旧风险。
2. 自动合并操作记录 `artifact_auto_merge_applied` 活动轨迹。
3. 既有插入-only 自动合并测试继续通过。
4. 不满足安全条件的冲突仍依赖现有手工对比/刷新/逐行/块级处理，本轮不扩大自动合并入口。

## 验证计划

- RED：`npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "auto-merges server insertions with draft deletions"`
- GREEN：同一命令通过。
- 回归：`npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx`
- 主 Agent 集成后再运行 `git diff --check`。

## Self-Review

- Placeholder scan: 无 TBD/TODO 或待补范围。
- Scope check: 单一 Artifact 冲突动作链，未混入 PDF 或服务端 API。
- Ambiguity check: 安全条件明确为“服务端只插入、用户保留旧行顺序且可删除旧行”。
