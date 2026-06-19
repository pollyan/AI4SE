# New Agents Provider Recovery Actions Plan

## Goal

Turn provider failure guidance in ChatPane from passive text into actionable recovery controls.

## Steps

1. Add failing ChatPane tests for provider failure settings entry and connection check.
2. Add ChatPane actions that open SettingsModal and call `/new-agents/api/config/check`.
3. Render connection check status in the provider failure card.
4. Run focused frontend tests, lint/build as needed, and `git diff --check`.
5. Update the UX professionalization todo to mark this provider recovery slice complete and keep statistics linkage as remaining work.
6. Commit, merge back to `master`, and push.

## Verification

- `cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/ChatPane.test.tsx src/components/__tests__/SettingsModal.test.tsx`
- `cd tools/new-agents/frontend && npm run lint`
- `cd tools/new-agents/frontend && npm run build`
- `git diff --check`
