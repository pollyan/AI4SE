# New Agents Observability Provider Issues Plan

## Goal

Make model/provider failures visible in the existing runtime statistics view instead of leaving users to interpret raw error codes.

## Steps

1. Add failing backend tests for provider issue classification in `/api/agent/observability`.
2. Add failing frontend parser, alert, and Header modal tests for provider issue fields.
3. Implement backend classification and summary fields.
4. Implement frontend types, parser, alerts, and badges.
5. Update the UX professionalization todo progress.
6. Run focused backend/frontend tests, lint/build, and `git diff --check`.
7. Commit, fast-forward merge to `master`, and push.

## Verification

- `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_endpoint.py::test_agent_observability_endpoint_groups_provider_issue_codes`
- `cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/observabilityService.test.ts src/core/__tests__/observabilityAlerts.test.ts src/components/__tests__/Header.test.tsx`
- `cd tools/new-agents/frontend && npm run lint`
- `cd tools/new-agents/frontend && npm run build`
- `git diff --check`
