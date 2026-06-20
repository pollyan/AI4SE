# New Agents Artifact 冲突处理收尾能力包 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` when the task can be split across independent files. 当前环境已达到子智能体线程上限，本轮由主 Agent 串行实现；如后续释放线程，优先把 review / verification 分发给子智能体。

**Goal:** 让 Artifact 保存冲突形成完整用户能力包：安全非重叠改动可自动合并；危险场景不误合并；用户能看到可读原因、继续手工处理并重试保存；审计和状态恢复可验证。

**Architecture:** 继续扩展 `ArtifactPane.tsx` 现有三方冲突处理链路。合并逻辑只在 base/server/draft 三方 Markdown sections 形态一致、普通段落唯一、顺序可证明、插入侧纯插入、改写侧单段改写时返回结果。不可自动合并原因只作为 UI 辅助说明，不改变服务端 API、typed runtime、store 结构或 agent/workflow 分支。

**Tech Stack:** React 19、TypeScript、Vitest、Zustand store、现有 ArtifactPane 冲突 UI。

---

### Task 1: RED 测试覆盖完整用户功能包

**Files:**
- Modify: `tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`

- [x] **Step 1: 新增正向测试：Draft 插入 + Server 改写**

测试名：`auto-merges same-section paragraph insertion with a non-overlapping server paragraph rewrite`。

期望当前失败：保存冲突后找不到 `自动合并非重叠变更`。

- [x] **Step 2: 新增正向测试：Server 插入 + Draft 改写**

测试名：`auto-merges same-section server paragraph insertion with a draft paragraph rewrite`。

期望当前失败：保存冲突后找不到 `自动合并非重叠变更`。

- [x] **Step 3: 新增危险场景拒绝测试**

测试名：`does not auto-merge same-section paragraph insertion when the rewrite side changes multiple paragraphs`。

期望当前失败：现有宽松插入合并可能错误显示自动合并入口。

- [x] **Step 4: 新增自动合并不可用原因测试**

新增测试名：`shows an auto-merge unavailable reason for unsafe paragraph insertion conflicts`。

断言：
- 冲突卡片不显示 `自动合并非重叠变更`。
- 显示 `自动合并暂不可用`。
- 显示 `双方改动涉及同一章节的多处段落，已保留你的草稿，请手工确认后重试保存。`
- textarea 仍保留用户草稿，用户可以继续编辑。

- [x] **Step 5: 已运行 RED**

已运行：

```bash
cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "same-section paragraph insertion"
```

结果：FAIL，符合预期；正例找不到自动合并入口，危险场景暴露现有宽松合并误判。

### Task 2: 实现安全自动合并和危险场景拦截

**Files:**
- Modify: `tools/new-agents/frontend/src/components/ArtifactPane.tsx`

- [x] **Step 1: 新增插入 change 类型**

新增 `ParagraphInsertChange`，记录插入 block 及其挂载的 base index。

- [x] **Step 2: 新增 `parsePureParagraphInsertChange`**

实现逻辑：
- target 必须比 base 长，且 trailing blank count 相同。
- base 段落 key 必须按原顺序全部出现在 target。
- target 中不属于 base 的 block 是插入块。
- 插入块数量必须大于 0；base block 顺序不能变化；target 中 base block 不能被改写。
- 如果插入块 key 与 base 或其他插入块重复，返回 null。

- [x] **Step 3: 新增合并行构造 helper**

新增 `buildMergedSameSectionParagraphInsertRewriteLines(...)`：
- parse base / insert / rewrite section。
- insert side 走 `parsePureParagraphInsertChange`。
- rewrite side 走 `parsePureParagraphRewriteChange`，且只能改写一个旧段落。
- 按 base 顺序构造 merged blocks：每个 base block 先应用 rewrite，再追加挂在该 base index 后的 inserted blocks。
- 插入在章节开头时 `afterBaseIndex = -1`，先追加开头插入块。
- 返回 `buildParagraphSectionLines(...)`。

- [x] **Step 4: 新增 auto merge result helper**

新增 `buildAutoMergedSameSectionParagraphInsertRewriteResult(baseContent, serverContent, draftContent)`：
- parse 三方 markdown sections。
- section shape 必须一致。
- 找到唯一一个双方都改动的 section。
- 尝试 `server=insert,draft=rewrite` 和 `draft=insert,server=rewrite` 两个方向。
- 其他 section 必须等于 base。
- 返回 summary `同章节非重叠段落插入与改写`。

- [x] **Step 5: 新增不可自动合并原因 helper**

新增保守的 `buildAutoMergeUnavailableReason(...)` 或等价逻辑：
- 仅在已经发生 artifact conflict 且没有任何 auto merge result 时显示。
- 对“同一章节段落插入 + 多段改写 / 重排 / 重复”返回用户可读原因。
- 不覆盖其他现有冲突说明，不把内部 parser 细节暴露给用户。

- [x] **Step 6: 接入 auto merge 链和 UI**

- 在 `sameSectionParagraphDeleteRewriteMerge` 之后、结构化块 reorder helper 之前接入 `sameSectionParagraphInsertRewriteMerge`。
- 在冲突卡片中为无自动合并场景显示 `自动合并暂不可用` 和原因。
- 确认 textarea 草稿不被覆盖，用户可继续手工处理后重试保存。

### Task 3: GREEN 与回归

**Files:**
- Modify: `docs/todos/new-agents-ux-professionalization.md`
- Modify: `docs/superpowers/plans/2026-06-20-new-agents-artifact-conflict-resolution-completion.md`

- [x] **Step 1: 聚焦 GREEN**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "paragraph insertion|auto-merge unavailable"
```

Expected: PASS。

Result: PASS，4 tests passed。

- [x] **Step 2: 相关回归**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "same-section paragraph|paragraph movement|section rewrites|table row|list item|fenced block line reordering|auto-merge unavailable"
cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx
cd tools/new-agents/frontend && npm run lint
cd tools/new-agents/frontend && npm run build
git diff --check
```

Result:
- `npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "paragraph insertion|auto-merge unavailable|paragraph is split"` PASS，5 tests passed。
- `npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "same-section paragraph|paragraph movement|section rewrites|table row|list item|fenced block line reordering|auto-merge unavailable"` PASS，44 tests passed。
- `npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx` PASS，131 tests passed。
- `npm run lint` PASS。
- `npm run build` PASS。
- `git diff --check` PASS。

- [x] **Step 3: 更新 todo 进展**

在 `docs/todos/new-agents-ux-professionalization.md` 的 Artifact 协作体验深化条目追加本轮完成项：
- Artifact 冲突处理收尾能力包已完成：安全自动合并、危险拦截、不可用原因、手工承接、审计/恢复验证。
- 剩余候选：更复杂的三方语义 merge 暂不做；导出增强已按用户决策标记完成到当前程度。

- [ ] **Step 4: 提交与推送**

Commit boundary: 一个用户可感知 Artifact 冲突处理能力包。

```bash
git add docs/todos/new-agents-ux-professionalization.md \
  docs/superpowers/specs/2026-06-20-new-agents-artifact-conflict-resolution-completion-design.md \
  docs/superpowers/plans/2026-06-20-new-agents-artifact-conflict-resolution-completion.md \
  tools/new-agents/frontend/src/components/ArtifactPane.tsx \
  tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx
git commit -m "feat(new-agents): 完善 Artifact 冲突处理闭环"
git push origin codex/new-agents-paragraph-insert-rewrite-merge
```

## Self Review

- Spec coverage: 用户故事、安全自动合并、危险拒绝、不可用原因、手工承接、审计轨迹、验证命令均有任务覆盖。
- Placeholder scan: 无 `TODO`、`TBD` 或“稍后实现”占位。
- Commit boundary: 一个用户可感知 Artifact 冲突处理能力包，而不是单个算法分支。
