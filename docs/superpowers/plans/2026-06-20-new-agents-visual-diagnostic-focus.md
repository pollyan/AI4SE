# New Agents Visual Diagnostic Focus Plan

## Goal

Let users jump from the left-side visual diagnostic notice to the failing right-side Mermaid or structured visual block.

## Steps

1. Add failing store, ChatPane, and ArtifactPane tests for visual diagnostic focus.
2. Add focus state and action to the shared store.
3. Add a ChatPane `查看问题位置` action.
4. Add diagnostic anchors and scroll/highlight handling in ArtifactPane.
5. Update the UX professionalization todo progress.
6. Run focused frontend tests, lint/build, and `git diff --check`.
7. Commit, fast-forward merge to `master`, and push.

## Verification

- `cd tools/new-agents/frontend && npm run test -- --run src/__tests__/store.test.ts src/components/__tests__/ChatPane.test.tsx src/components/__tests__/ArtifactPane.test.tsx src/components/__tests__/markdownCodeRenderer.test.tsx`
- `cd tools/new-agents/frontend && npm run lint`
- `cd tools/new-agents/frontend && npm run build`
- `git diff --check`
