# Repository Guidelines

## Project Structure & Module Organization

AI4SE is a modular monorepo with Docker Compose as the primary runtime. Core documentation lives in `docs/`; start with `docs/index.md`, then use focused references such as `docs/ARCHITECTURE.md`, `docs/api-contracts.md`, and `docs/TESTING.md`.

Main code areas:

- `tools/frontend/`: React portal frontend.
- `tools/intent-tester/`: Flask API, MidScene/Playwright proxy, UI, and tests.
- `tools/new-agents/`: React agent UI plus Flask/PydanticAI backend.
- `tools/shared/`: shared Python config and database utilities.
- `scripts/`: deployment, health, CI, and test helpers.
- `tests/`: root-level Python test entry point.

## High-Priority Architecture Principles

For `tools/new-agents`, all agents must share one common runtime, transport, state, and UI infrastructure. Different agents and workflows should be expressed through configuration: `tools/new-agents/workflow_manifest.json`, `agentId`, workflow definitions, stage prompts, artifact templates, backend contract requirements, and visualization contract requirements. Do not create agent-specific runtime branches, duplicate SSE/API paths, separate stores, or bespoke rendering pipelines for Lisa, Alex, or future agents unless the user explicitly approves a documented architecture change.

When adding or changing a workflow, keep the configuration surfaces synchronized: shared `workflow_manifest.json`, manifest-derived frontend `WORKFLOWS` / workflow slugs / agent workflow listings, backend `WORKFLOW_STAGES`, artifact contract headings, Mermaid visualization contract, prompt/template files, and tests that prove the workflow uses the shared `/api/agent/runs/stream` typed Agent Runtime. If behavior differs by workflow, encode the difference as data or prompt/template/contract configuration rather than branching infrastructure code. If the change affects workflow quality, update or run the relevant E2E LLM judge evidence.

## Build, Test, and Development Commands

- `./scripts/dev/deploy-dev.sh`: deploy the local Docker development stack.
- `./scripts/test/test-local.sh`: run the repository's local validation suite.
- `pytest`: run Python tests from the repository root.
- `flake8 --select=E9,F63,F7,F82 .`: run critical Python lint checks.
- `cd tools/frontend && npm run build`: build the main React frontend.
- `cd tools/new-agents/frontend && npm run test`: run Vitest tests for the New Agents UI.
- `cd tools/intent-tester && npm run test:proxy`: run Jest proxy tests.

## Coding Style & Naming Conventions

Use Python 3.11 and TypeScript 5.x patterns already present in the touched module. Python uses `snake_case`; React components use `PascalCase`; hooks and utilities use `camelCase`. Prefer strict contracts and explicit failures over compatibility shims or silent fallback behavior. Do not use hidden fallback paths, production mocks, fabricated data, or fake success responses to mask data or logic failures; invalid state must fail explicitly with a diagnosable error. Do not introduce `as any`, `@ts-ignore`, empty `catch` blocks, broad `except Exception`, or hardcoded secrets.

Run local formatters and linters: `black .`, `flake8 .`, `npm run lint`, or package TypeScript checks.

## Testing Guidelines

Follow TDD: write or update a failing test before changing behavior. Pytest discovers `test_*.py`, `Test*`, and `test_*`; markers include `unit`, `api`, `integration`, `e2e`, and `slow`.

For `tools/new-agents`, preserve layered coverage: backend contracts, runtime validation, typed SSE/API behavior, frontend stream parsing, and state updates. Real model smoke tests require explicit environment configuration.

In Codex goal mode, follow `docs/strategy/goal-mode-playbook.md` and the relevant plan rules for sub-agent dispatch, review, verification, and recording.

## Commit & Pull Request Guidelines

Recent history uses concise Chinese imperatives and Conventional Commit prefixes such as `fix(ci): ...`, `test: ...`, and `chore: ...`. Keep commits focused.

Pull requests should include the problem, solution, affected modules, verification commands, and screenshots for UI changes.

## Security & Configuration Tips

Store credentials in environment variables or approved configuration stores, never in source. When adding dependencies, update the relevant `requirements.txt` or `package.json` in the owning module.
