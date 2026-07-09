# Goal Mode Milestone Ledger

> 状态: 历史事实源
> 更新日期: 2026-07-09
> 用途: 记录目标模式已验证 milestone 和历史集成证据；恢复目标模式时不得从旧 integration branch 或 E 编号直接恢复实现。

## 当前结论

- DeepSeek V4 结构化产物数据改造: 本地确定性完成并已主线化；真实 DeepSeek V4 Flash smoke 仍需显式凭证、网络和额度。
- New Agents 增强诊断: E01、E02、E03、E04、E05、E06、E07、E08、E09、E10、E11、E12、E13、E14 均已作为历史能力包收口。
- 当前功能能力包已清空；后续不再围绕旧 integration branch、旧 E 编号或旧 protected worktree 记录继续执行。
- 恢复目标模式时，应从当前代码、测试、文档、git 状态、新失败证据和用户最新目标重新做 CGA。

## integrated_in_goal_final_branch

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
| E10 专业方法库配置 | E10 | `d63f9a9d` | `codex/professional-method-library` | professional methods registry + prompt injection tests |
| E11 Prompt/template 版本管理 | E11 | `c4edd4b4` | `codex/prompt-template-versioning` | prompt version/sample registry + sync tests |
| E05 章节级重生成 / 定向修订闭环 | E05 | `fdcc3887` | `codex/artifact-section-regeneration` | artifactSections/chatService/ArtifactPane tests |
| E12 Workflow schema dry-run/scaffold | E12 | `43cfe0bc` | `codex/workflow-dry-run-gate` | workflow dry-run validation tests |
| E02 阶段缺失信息清单 | E02 | `0ab900f2` | `codex/new-agents-missing-info-checklist` | ChatPane/ArtifactPane/artifactQuality tests |
| E01 Workflow 入口 preview | E01 | `8072a866` | historical branch evidence | WorkflowSelect/workflows tests |

## remaining_active

无。功能能力包已清空；恢复目标模式时应先从当前代码、测试、文档和 git 状态做 CGA，确认是否只剩最终集成风险或 CI/验证回归。

## final_integration_status

- 历史 integration branch: `codex/goal-final-integration`。
- 当前状态: 本账本只保留历史集成证据，不再声明仍有待合回分支或待删除分支。
- 若未来发现主线验证或远端 CI 回归，应按当前 `docs/strategy/goal-mode-playbook.md` 重新进入 CGA，而不是沿旧 integration branch 规则继续。

## protected_main_worktree_changes

历史记录中的受保护主工作区改动已不作为当前事实源。恢复目标模式时必须重新运行 `git status -sb` 和必要的 diff 归属检查，以当前工作区为准。

## recovery_rules

- 目标模式恢复时可以读本账本了解历史能力包，但必须以当前代码、测试、文档和 git 状态为准。
- 不要从 `integrated_in_goal_final_branch` 中的 E 编号重新启动功能实现，除非 CGA 证明当前主线仍存在回归、缺失验证或用户重新定义范围。
- 选择下一轮工作时，默认从新用户目标、当前失败证据、远端 CI 失败复盘或当前 `docs/todos/` 中仍未完成的 P0/P1 开始；不要重新启动已完成的历史能力包。
- 如果远端 CI 或真实 DeepSeek smoke 暴露失败，优先按目标模式 playbook 的 CI 失败复盘规则处理。
