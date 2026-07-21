# QG-021 固定 Pre-push Suite 所有权

本文件由 `scripts/test/pre_push.py:fixed_suites()` 渲染；修改门禁时必须更新 registry，并由同步测试阻止此视图漂移。

| Suite | 保护的不变量 | 证据层 | 外部边界 | Canonical owner | 耗时 | 处置 |
| --- | --- | ---: | --- | --- | --- | --- |
| `docs-links` | document links resolve | 1 | none | `scripts/test/pre_push.py` | 短 | KEEP |
| `intent-tester-critical-lint` | critical Python syntax and name errors fail | 1 | none | `scripts/test/pre_push.py` | 短 | KEEP |
| `intent-tester-api` | Intent API contract and CI coverage threshold | 1 | provider mocks only | `scripts/test/pre_push.py` | 短 | MERGE |
| `intent-proxy` | Intent proxy protocol | 1 | Playwright adapter replacement | `scripts/test/pre_push.py` | 短 | KEEP |
| `common-frontend-lint` | common frontend type and lint safety | 1 | none | `scripts/test/pre_push.py` | 短 | KEEP |
| `common-frontend-build` | common frontend production build | 1 | none | `scripts/test/pre_push.py` | 短 | MOVE |
| `new-agents-frontend-lint` | New Agents frontend type safety | 1 | none | `scripts/test/pre_push.py` | 短 | MOVE |
| `new-agents-frontend-test` | frontend stream parsing and state behavior | 1 | controlled browser and API seams | `scripts/test/pre_push.py` | 短 | MERGE |
| `new-agents-frontend-build` | New Agents production frontend build | 1 | none | `scripts/test/pre_push.py` | 短 | MOVE |
| `new-agents-backend` | backend contracts, persistence and typed SSE | 1 | provider mocks only | `scripts/test/pre_push.py` | 短 | MERGE |
| `new-agents-runner-contracts` | real-model runner scope and secret boundary | 2 | none | `scripts/test/pre_push.py` | 中 | KEEP |
| `verification-outcomes` | zero collection and non-PASS outcome closure | 2 | none | `scripts/test/pre_push.py` | 中 | KEEP |
| `ci-deploy-hardening` | CI and deployment configuration contracts | 2 | none | `scripts/test/pre_push.py` | 中 | KEEP |
| `new-agents-real-contracts` | real-model evidence, stream and persistence assertions | 2 | none | `scripts/test/pre_push.py` | 中 | KEEP |
| `new-agents-live-stack` | real frontend/backend/SSE/browser deterministic boundary | 3 | deterministic provider seam | `scripts/test/pre_push.py` | 长 | MERGE |
| `new-agents-browser-e2e` | browser-visible stream order and artifact rendering | 3 | controlled Agent Runtime seam | `scripts/test/pre_push.py` | 长 | KEEP |
| `new-agents-deployed-real-release` | deployed real-model release covers every manifest workflow, stage and transition | 4 | isolated production Compose and real configured provider | `scripts/test/pre_push.py` | 很长 | MOVE |
| `new-agents-real-nightly-stage-probes` | independent per-stage real-model diagnostic coverage | 4 | GitHub scheduled runner and real configured provider | `.github/workflows/deploy.yml` | 很长 | KEEP |
