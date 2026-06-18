# New Agents Config Unification Design

## Goal

Reduce duplicated frontend workflow configuration for `tools/new-agents` without changing runtime behavior, UI copy, routing, prompts, templates, backend validation, or SSE behavior.

## Scope

This change is limited to online workflow metadata in the New Agents frontend:

- `WORKFLOWS` remains the runtime source for online workflow identity, stages, prompts, templates, onboarding, and agent ownership.
- Online workflow cards are derived from `WORKFLOWS` instead of manually repeating `id`, `agentId`, and `link`.
- Workflow slug mappings are derived from workflow definitions instead of maintained as a second hardcoded table.
- Planned or development cards that do not have runtime workflow definitions remain as separate non-runtime listing configuration.
- Backend contract data in `agent_contracts.py` remains unchanged and continues to be guarded by the existing frontend/backend sync tests.

## Current Duplication

The same online workflow facts currently appear in several frontend places:

- `core/workflows.ts` owns runtime workflow definitions and `agentId`.
- `core/types.ts` owns `WORKFLOW_SLUGS` and `SLUG_TO_WORKFLOW`.
- `core/config/agentWorkflows.ts` repeats online listing card ids, agent ids, links, names, descriptions, and icons.
- `core/llm.ts` repeats the structured-runtime workflow list.

The backend also owns validation stages and artifact headings. That duplication is intentional contract enforcement for now and is already covered by `test_workflow_contract_sync.py`.

## Recommended Architecture

Add `slug` and `listing` metadata to each online `WorkflowDef`. The `listing` fields preserve the exact current card copy and icons.

Derive these runtime-facing values from `WORKFLOWS`:

- `WORKFLOW_SLUGS`
- `SLUG_TO_WORKFLOW`
- online `AgentWorkflowConfig` rows
- workspace links in the form `/workspace/${agentId}/${slug}`
- structured runtime eligibility in `llm.ts`

Keep a separate `NON_RUNTIME_AGENT_WORKFLOWS` list for dev/plan cards such as `log-diagnostics`, `auto-assert`, `story-breakdown`, and `competitive-analysis`.

## Non-Behavior Requirements

The implementation must preserve:

- All existing workflow slugs.
- All existing workspace links.
- All existing workflow card names, descriptions, icons, statuses, and status labels.
- All existing `WORKFLOWS[*].name`, `description`, stages, prompts, templates, and onboarding values.
- All backend stage validation and artifact heading validation.
- All current stream behavior and API paths.

## Testing Strategy

Use TDD:

1. Add tests proving every online card is generated from `WORKFLOWS` metadata.
2. Add tests proving slug maps are derived from workflow definitions and remain reversible.
3. Add tests proving online card count matches runtime workflow count while non-runtime dev/plan cards remain available.
4. Verify existing workflow config tests still preserve current user-facing values.
5. Run the focused frontend test file, then the broader frontend config/prompt tests and TypeScript check.

## Out of Scope

- Introducing a shared JSON manifest for both Python and TypeScript.
- Generating code.
- Changing prompts, artifact templates, stage definitions, or backend schemas.
- Changing the left chat or right artifact streaming implementation.
