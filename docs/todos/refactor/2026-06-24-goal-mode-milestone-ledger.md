# Goal Mode Milestone Ledger

> 状态: 活动事实源
> 更新日期: 2026-06-24
> 用途: 记录目标模式已验证 milestone、待最终合回提交、剩余能力包和最终集成条件。

## 当前结论

- DeepSeek V4 结构化产物数据改造: 本地确定性完成，待最终合回。
- New Agents 增强诊断: E01、E02、E03、E04、E05、E06、E07、E08、E09、E12、E13、E14 已有提交证据，待最终合回或主线复核。
- 当前仍作为后续能力包候选: E10 专业方法库配置、E11 Prompt/template 版本管理。
- 最终 merge/push/删分支: 仅在所有活跃能力包完成、主线脏文件处理完、integration branch 验证通过后执行。

## completed_pending_merge

| Capability | Todo | Commit | Branch | Evidence |
| --- | --- | --- | --- | --- |
| DeepSeek V4 格式化输出 readiness gate | DeepSeek V4 structured artifact data | `50f444f7` | `codex/deepseek-v4-format-output-readiness` | runtime readiness, renderer contract |
| E09 运行统计产品化诊断建议 | E09 | `9739fc27` | `codex/runtime-observability-actions-current` | observability API/service/Header tests |
| E03/E08 Artifact 与工作流质量治理 | E03/E08 | `dfa2b1b6` | `codex/workflow-quality-governance-current` | workflowQuality + ArtifactPane tests |
| E06 Run 历史中心增强 | E06 | `c265ae4a` | `codex/run-history-reuse-goal-current` | backend persistence/API + Header/service tests |
| E07 Workflow handoff 上下文强化 | E07 | `32bffcbc` | `codex/workflow-handoff-context-goal-mainline` | handoff backend/frontend tests |
| E04 Lisa 测试资产质量闭环 | E04 | `eb957d55` | `codex/lisa-test-asset-quality-loop-goal-mainline` | test asset backend/frontend tests |
| E13 Alex 用户故事拆解 workflow | E13 | `1782001b` | `codex/alex-story-breakdown-goal-current` | workflow manifest/runtime/contract/prompt tests |
| E14 Alex PRD 质量评审 workflow | E14 | `f088cf91` | `codex/alex-prd-review-goal-mainline` | workflow manifest/runtime/contract/prompt tests |
| E05 章节级重生成 / 定向修订闭环 | E05 | `fdcc3887` | `codex/artifact-section-regeneration` | artifactSections/chatService/ArtifactPane tests |
| E12 Workflow schema dry-run/scaffold | E12 | `43cfe0bc` | `codex/workflow-dry-run-gate` | workflow dry-run validation tests |
| E02 阶段缺失信息清单 | E02 | `0ab900f2` | `codex/new-agents-missing-info-checklist` | ChatPane/ArtifactPane/artifactQuality tests |
| E01 Workflow 入口 preview | E01 | `8072a866` | historical branch evidence | WorkflowSelect/workflows tests |

## remaining_active

| Capability | Todo | Why Still Active | Suggested Next Validation |
| --- | --- | --- | --- |
| 专业方法库配置 | E10 | 尚未找到完成提交；当前方法仍散落在 prompt/template 中，缺统一配置注入与方法元数据。 | manifest/prompt registry tests, workflow prompt regression tests |
| Prompt/template 版本管理 | E11 | 尚未找到完成提交；每个 stage 的 prompt/template version 和回归样例仍未形成统一治理面。 | prompt registry/version tests, dry-run integration |

## final_integration_pending

- 当前账本只证明存在已验证的独立 milestone commit，不证明这些 commits 已在 `master` 可用。
- 最终合回前应创建 integration branch，按依赖和冲突风险逐项 cherry-pick 或手工移植 `completed_pending_merge` 中的 commits。
- 每合入一个跨 runtime / workflow manifest / frontend 主路径的 commit，都应运行对应聚焦验证；全部合入后运行 New Agents 后端 contract/runtime/API、前端 lint/test 和 `git diff --check`。
- 用户要求的删除当前分支、merge 回主干并 push GitHub，只能在 `remaining_active` 清空、integration branch 验证通过、主工作区受保护改动已处理后执行。

## protected_main_worktree_changes

当前 `master` 工作区仍有以下未提交改动。本账本不覆盖、不回滚、不格式化这些文件:

- `dist/intent-test-proxy.zip`
- `docs/plans/tech-debt.md`
- `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md`
- `docs/todos/refactor/README.md`
- `tools/intent-tester/frontend/static/intent-test-proxy.zip`

## recovery_rules

- 目标模式恢复时先读本账本，再读具体 todo。
- 不要从 `completed_pending_merge` 中的 E 编号重新启动功能实现，除非 CGA 证明主线集成后仍存在回归、缺失验证或用户重新定义范围。
- 选择下一个功能能力包时，默认从 `remaining_active` 中的 E10、E11 或最终集成前置闭环开始。
- 如果远端 CI、真实 DeepSeek smoke 或 integration branch 暴露失败，优先按目标模式 playbook 的 CI 失败复盘规则处理。
