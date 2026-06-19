# New Agents 失败恢复引导补齐 Implementation Plan

> **For agentic workers:** 本计划按 `superpowers:subagent-driven-development` 执行。Worker 只允许修改本计划列出的前端测试/源码文件，不提交、不推送。

**Goal:** 补齐 P0 失败恢复体验：Artifact Mermaid 预校验失败进入恢复卡；连续恢复失败时给用户“补充信息后再试”的操作；失败时阶段确认不误导推进。

**Architecture:** 继续复用现有 ChatPane / chatService / Agent Runtime typed SSE。只改前端恢复归类与 UI 行为，不新增 workflow-specific 或 agent-specific 分支。

**Working tree:** `/Users/anhui/Documents/myProgram/AI4SE/.worktrees/codex-new-agents-recovery-guidance`

---

## File Structure

- Modify: `tools/new-agents/frontend/src/services/chatService.ts`
  - Add artifact validation / Mermaid parse failure to structured recovery formatter.
- Modify: `tools/new-agents/frontend/src/services/__tests__/chatService.test.ts`
  - Add RED test for `Artifact Mermaid parse failed` recovery card behavior.
- Modify: `tools/new-agents/frontend/src/components/ChatPane.tsx`
  - Detect repeated structured recovery failures.
  - Add `补充信息后再试` action on repeated failure cards.
- Modify: `tools/new-agents/frontend/src/components/__tests__/ChatPane.test.tsx`
  - Add RED test for repeated failures showing complement-info action.
  - Keep existing stage confirmation hidden behavior green.
- Modify: `docs/todos/new-agents-ux-professionalization.md`
  - Record this slice after verification.

## Task 1: chatService Recovery Classification RED/GREEN

- [x] Add regression test: `Artifact Mermaid parse failed` should produce `结构化输出生成失败`, preserve artifact, and avoid raw `**Error:**`.
- [x] Implement minimal recovery classification in `chatService.ts`.
- [x] Run focused test after dependency setup: `cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/chatService.test.ts -t "artifact Mermaid validation"`.
- [ ] RED observation note: worker attempted this before implementation verification, but the isolated worktree had an empty `node_modules` and failed with `vitest: command not found`; do not treat RED evidence as proven for this item.

## Task 2: ChatPane Repeated Failure Guidance RED/GREEN

- [x] Add regression test: two assistant structured failure messages render `补充信息后再试`.
- [x] Test click behavior: it sets an editable clarification prompt in textarea and does not call retry/send.
- [x] Implement minimal ChatPane logic using existing `setInput`.
- [x] Add guard that a single structured failure does not show the supplement action.
- [x] Run focused ChatPane test after dependency setup: `cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/ChatPane.test.tsx -t "supplement guidance"`.
- [ ] RED observation note: worker attempted this before implementation verification, but the isolated worktree had an empty `node_modules` and failed with `vitest: command not found`; do not treat RED evidence as proven for this item.

## Task 3: Regression Verification And Todo

- [x] Run `cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/chatService.test.ts src/components/__tests__/ChatPane.test.tsx`.
- [x] Run `cd tools/new-agents/frontend && npm run build`.
- [x] Run `git diff --check`.
- [x] Update `docs/todos/new-agents-ux-professionalization.md`.

## Worker Constraints

- Work only inside `/Users/anhui/Documents/myProgram/AI4SE/.worktrees/codex-new-agents-recovery-guidance`.
- Do not modify files outside the File Structure list unless tests reveal a direct type dependency; report first if that happens.
- Do not commit or push.
- Do not touch main worktree zip files.
- You are not alone in the codebase; do not revert or overwrite unrelated changes.
