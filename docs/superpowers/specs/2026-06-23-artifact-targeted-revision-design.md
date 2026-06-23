# Artifact 定向修订闭环设计

## 背景

当前 New Agents 已经具备共享 Agent Runtime、typed SSE、Artifact 版本历史、手工编辑、章节锁定、审阅诊断和 workflow 质量治理。用户可以审阅和保护产出物，但当只想改写某个章节时，只能通过自然语言要求模型重写全文，或者手工编辑。这会带来三个风险：

- 模型可能改动非目标章节，尤其是已经确认但未锁定的章节。
- 锁定章节虽然已有生成保护，但缺少用户可见的“定向修订”入口。
- 修订失败或模型返回结构不完整时，需要明确不污染当前 artifact、stage artifact 和历史版本。

本轮将 `E05 章节级重生成` 上调为一个更完整的用户工作流：Artifact 定向修订闭环。

## 用户目标

用户在 Artifact 审阅过程中，可以针对当前阶段 artifact 的某个 Markdown 章节发起定向修订。系统通过现有共享 `/api/agent/runs/stream` typed SSE 运行时请求模型生成完整 artifact，但前端只接受目标章节的更新，并继续保护锁定章节、保留非目标章节、写入版本历史。

## 范围

本轮包含：

1. 在 Artifact 章节管理界面提供“重生成章节”动作。
2. 发起定向修订时携带当前 workflow、stage、目标章节、原始 artifact、锁定章节和修订约束。
3. 复用现有 `useChatService`、`generateResponseStream` 和 `reduceAgentStreamChunk`；不新增 API path、runtime、store 或 renderer。
4. 对模型返回的完整 artifact 做客户端合并：只提取目标章节内容写回当前 artifact。
5. 继续强制保留当前阶段锁定章节。
6. 目标章节被锁定、目标章节缺失、模型返回缺少目标章节时明确失败，且不更新 artifact。
7. 成功后更新 `artifactContent`、`stageArtifacts` 和 `artifactHistory`，沿用现有版本历史与 retry/rollback 机制。
8. 覆盖纯函数、service hook 和 ArtifactPane UI 的最小 TDD 验收。

本轮不包含：

- 新增后端 runtime、agent-specific API 或 workflow-specific store。
- 多章节批量重写、章节重排、章节删除或重命名合并。
- 真实 LLM smoke；真实 DeepSeek V4 验证仍受凭证、网络和额度约束。
- 跨 run 质量趋势、LLM judge evidence 或 workflow schema scaffold。

## 行为契约

### 成功路径

给定当前 artifact 包含多个 Markdown 标题章节，且当前阶段存在一个锁定章节：

1. 用户选择一个未锁定目标章节并点击重生成。
2. 系统向共享 typed SSE runtime 发送定向修订 prompt。
3. 模型返回完整 artifact。
4. 前端只从返回 artifact 中提取目标章节内容。
5. 前端将目标章节内容合并回原 artifact。
6. 所有锁定章节以锁定快照内容为准。
7. 非目标章节保持原样。
8. 当前 `artifactContent`、当前 `stageArtifacts[stageId]` 和最新历史版本一致。

### 阻断路径

- 目标章节已锁定：不调用模型，显示可诊断提示。
- 当前 artifact 找不到目标章节：不调用模型，显示可诊断提示。
- 模型返回 artifact 找不到目标章节：不写入 artifact，保留当前状态，并在 chat 中显示错误。
- 流式运行失败：沿用现有错误提示和回滚策略，不追加成功版本。

## UI 约束

- 入口放在现有“章节锁定”侧栏中，避免新建孤立工具面板。
- 每个章节保持紧凑操作：锁定/解锁和重生成并列。
- 锁定章节的重生成按钮禁用，并通过 `title`/提示说明需要先解锁。
- 生成中禁用重生成动作，避免并发污染当前 artifact。

## 架构约束

- 定向修订是共享 Agent Runtime 的一种调用方式，不是新的后端端点。
- 章节识别、目标章节合并和锁定章节保护应抽到共享 frontend core helper，避免 `ArtifactPane` 和 `chatService` 继续各自维护不一致的 Markdown section 解析逻辑。
- 锁定匹配优先使用 `sectionAnchor`，否则回退到 heading。
- 如果模型改变了非目标章节，客户端合并必须丢弃这些变化。

## 验收

1. 纯函数测试证明目标章节合并只改目标章节，锁定章节强制保留。
2. 纯函数测试证明锁定目标章节和缺失目标章节会失败。
3. `useChatService` 测试证明章节重生成使用共享 stream，并在成功时更新 artifact/stage/history。
4. `useChatService` 测试证明模型返回缺少目标章节时 artifact/stage/history 不变。
5. `ArtifactPane` 测试证明用户可从章节侧栏触发未锁定章节重生成，锁定章节按钮禁用且不会调用 stream。
6. `docs/todos/` 记录本轮消化 E05，并保留下一轮候选。
