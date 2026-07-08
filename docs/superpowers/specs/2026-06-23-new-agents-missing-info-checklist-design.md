# New Agents 阶段缺失信息清单设计

## 背景

当前 `codex/new-agents-missing-info-checklist` 基于 `codex/new-agents-quality-diagnostics-consolidation`。该基线已经完成 DeepSeek V4 `artifact_data` 信任闭环和 E03 Artifact 质量诊断面板，`ArtifactPane` 可以展示 headings、visual、stage gate、专业字段和 visual diagnostic 的通过/失败/警告。

E02 剩余缺口是用户恢复链路：当当前阶段产物不完整时，用户不只需要看到“哪里失败”，还需要知道缺失项是否阻断继续推进，以及下一步应该补充信息、重试生成还是定位可视化问题。该提示需要同时出现在 chat 和 artifact 两侧，避免用户只看左侧对话或右侧产物时漏掉恢复动作。

## 用户故事

作为 New Agents 用户，当我查看某阶段生成的不完整 artifact 时，我可以在 chat 和 artifact 两侧同时看到缺失信息、阻断性和下一步补救建议，从而知道该补充什么、是否能继续推进当前 workflow。

## 设计

采用前端共享诊断层扩展，不新增后端 API、SSE 事件、store 分支或 agent/workflow 专属 renderer。

- 在 `tools/new-agents/frontend/src/core/artifactQuality.ts` 中把现有 `ArtifactQualityItem` 聚合成 `MissingInfoItem`。
- `MissingInfoItem` 包含稳定 `id`、`title`、`blocking`、`severity`、`reason`、`nextAction` 和可选 `actionDiagnosticId`。
- `blocking=true` 用于 contract fail、visual fail 和 visual diagnostic fail；`blocking=false` 用于 stage gate warning 等可继续但需确认的问题。
- `ArtifactPane` 的审阅面板新增“缺失信息清单”，展示阻断/提醒、原因、下一步，并保留 visual diagnostic 定位动作。
- `ChatPane` 基于当前 workflow/stage、artifactContent 和当前阶段 visual diagnostics 计算同一缺失清单；当存在缺失项且非生成中时，在消息流顶部显示轻量提示，列出优先级最高的若干项和下一步。

## 非目标

- 不引入质量评分或趋势分析；E08/E09 后续处理。
- 不自动修复全文、不自动改写 artifact。
- 不改变 DeepSeek 后端 renderer、typed SSE、run persistence 或 artifact contract。
- 不新增 Lisa、Alex、DeepSeek 专属 runtime/API/store/renderer。

## 验收条件

1. 给定当前阶段 artifact 缺少 contract 标题、字段或 visual，`buildArtifactQualitySummary()` 返回缺失信息清单，标明阻断、原因和下一步。
2. 给定 stage gate 章节存在但没有 checkbox 决策项，缺失信息清单返回非阻断提醒和确认下一步。
3. 给定当前阶段有 visual diagnostic，缺失信息清单保留定位 action id，并提示用户定位问题位置。
4. 用户打开 ArtifactPane 审阅面板时，可以看到“缺失信息清单”、阻断/提醒标签、下一步文案。
5. 用户查看 ChatPane 时，如果当前阶段 artifact 不完整，可以看到“当前阶段缺失信息”、阻断性和下一步；其他阶段的 visual diagnostic 不应污染当前提示。

## 验证计划

- 先补 `artifactQuality.test.ts` 的 RED 测试，验证缺失清单数据结构。
- 再补 `ArtifactPane.test.tsx` 的 RED 测试，验证 artifact 审阅面板展示缺失清单。
- 再补 `ChatPane.test.tsx` 的 RED 测试，验证 chat 区同步展示缺失清单。
- 实现后运行上述 Vitest 聚焦测试、`npm run lint` 和 `git diff --check`。
