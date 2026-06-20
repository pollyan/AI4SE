# New Agents UX Todo 活动范围收敛设计

## 用户故事

作为持续推进 AI4SE 目标模式的执行者，当我读取 `docs/todos/new-agents-ux-professionalization.md` 准备选择下一轮 New Agents UI/UX milestone 时，我希望能直接看到哪些能力包已经阶段完成、哪些能力用户已决定暂不推进、哪些只有在新证据出现时才允许重启，从而避免把历史进展里的“剩余”记录误判为当前活动 P0/P1 待办。

## 场景

1. 目标模式启动后按 playbook 扫描 New Agents UX todo。
2. 文件顶部先呈现当前活动状态，而不是要求执行者从 700 多行历史进展中推断。
3. 执行者看到高保真导出、恢复中心、分享/权限、多人实时协同、intent-tester 自动打通等用户已暂缓项，不再把它们作为当前目标继续实现。
4. 执行者看到 Artifact 更复杂三方 merge 只能在出现完整、可证明安全的用户冲突场景时重启，不能按单算法分支拆薄。
5. 执行者看到早期进展记录中的“剩余”属于历史过程，后续 CGA 必须以上方活动状态和用户最新决策为准。

## 范围

- 修改 `docs/todos/new-agents-ux-professionalization.md`，增加当前活动状态、明确不推进项、后续 CGA 选题规则和历史记录说明。
- 保留历史进展记录，不删除已完成过程证据。
- 新增本轮 implementation plan。

## 非目标

- 不修改 New Agents 前端、后端、测试或运行时行为。
- 不重启高保真 PDF 图片级导出、恢复中心、分享/权限、多人实时协同、intent-tester 自动打通。
- 不新增 Artifact 三方 merge 算法分支。
- 不把已阶段完成的模型治理、可视化、结构化重试、Header 收敛重新拆成实现任务。

## 验收条件

1. `docs/todos/new-agents-ux-professionalization.md` 顶部有当前活动状态索引，覆盖 P0/P1 主能力包。
2. 文件明确说明当前不推进项：高保真 PDF 图片级导出深化、恢复中心、分享/权限、多人实时协同、与 intent-tester 自动打通。
3. 文件明确说明早期进展记录里的“剩余”是历史记录，后续选题以上方当前活动状态和最新产品决策为准。
4. 文件明确说明后续 CGA 不能从单个旧“剩余”或单算法分支直接进入 milestone，必须重新聚合成完整用户功能厚切片。
5. 文档验证命令能证明关键段落存在，且 `git diff --check` 通过。

## 风险

- 风险：过度改写历史记录会丢失已完成过程证据。
  - 处理：只在顶部增加当前状态和解释，不删除历史进展。
- 风险：把所有项目都标成完成会掩盖未来真实缺口。
  - 处理：使用“阶段完成”“当前不推进”“按新证据重启”区分状态。
- 风险：文档收敛被误解为目标已经全部完成。
  - 处理：不调用目标完成状态；只完成本轮工程信任闭环。

## 验证计划

1. RED：运行 `rg -n "当前活动状态|当前明确不推进|后续 CGA 选题规则|历史进展记录说明" docs/todos/new-agents-ux-professionalization.md`，确认当前缺少这些稳定索引。
2. GREEN：更新文档后重新运行同一 `rg`，确认关键索引存在。
3. 范围验证：运行 `rg -n "高保真|恢复中心|分享/权限|intent-tester|更复杂三方 merge" docs/todos/new-agents-ux-professionalization.md`，确认暂缓项和重启条件表达清楚。
4. 质量验证：运行 `rg -n "T[B]D|implement[ ]later|填[入]|稍后[实]现" docs/todos/new-agents-ux-professionalization.md docs/superpowers/specs/2026-06-20-new-agents-ux-todo-scope-closure-design.md docs/superpowers/plans/2026-06-20-new-agents-ux-todo-scope-closure.md`，确认没有占位符。
5. 运行 `git diff --check`。
