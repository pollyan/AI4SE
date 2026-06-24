# 目标模式 CI 等价验证附录

本文承载目标模式中的常用验证命令、CI 等价映射、远端 CI 失败复盘和提交前验证表。主执行入口见 `docs/strategy/goal-mode-playbook.md`。

## 1. 常用验证矩阵

按本轮影响范围选择验证命令。测试分层、覆盖口径和真实模型 smoke 规则以 `docs/TESTING.md` 为准；本节只提供目标模式常用命令索引。不要声称未运行的测试已通过。

| 影响范围 | 推荐验证 |
| --- | --- |
| 全仓 Python 语法风险 | `flake8 --select=E9,F63,F7,F82 .` |
| 全仓本地验证 | `./scripts/test/test-local.sh all`（无参数默认等价于 `all`） |
| Docker 开发栈 | `./scripts/dev/deploy-dev.sh`，必要时配合健康检查 |
| New Agents 后端 | `cd tools/new-agents/backend && python3 -m pytest -m "not slow" -q` |
| New Agents 后端语法兜底 | `python3 -m py_compile <changed-python-files>` |
| New Agents 前端 | `cd tools/new-agents/frontend && npm test` |
| New Agents 前端类型 / lint | `cd tools/new-agents/frontend && npm run lint` |
| New Agents 前端构建 | `cd tools/new-agents/frontend && npm run build` |
| New Agents 浏览器工作流 | `python3 -m pytest -o addopts='' tests/e2e/new_agents_browser -m e2e -q` |
| Intent Tester proxy | `cd tools/intent-tester && npm run test:proxy` |
| 统一门户 | `cd tools/frontend && npm run build` |
| Compose 配置 | `docker compose -f docker-compose.dev.yml config --services`，按需检查 `dev-cn` / `prod` |
| 纯文档 / playbook / todo | 文档核对清单和 `git diff --check` |

真实模型 smoke、LLM judge 或外部服务验证只在用户明确要求或相关事实源规定、且环境变量 / 网络 / 额度齐备时运行。缺少条件时要明确说明，不能把 mock 或确定性测试说成真实外部验证。

## 2. CI 等价本地验证

提交或 push 前必须先判断本轮改动会触发哪些 CI 检查，并在本地运行最接近的等价命令。目标不是把所有测试机械跑一遍，而是避免“本地未跑对应验证、提交后才发现 CI 失败”。

每轮进入 commit / push 前，必须先做一次 CI 映射：

1. 查看当前 diff 的文件范围，判断影响模块、语言栈、生成产物、部署脚本和共享契约。
2. 对照仓库 CI workflow、`scripts/test/*`、package scripts 和本文验证矩阵，列出远端可能运行的 job 或等价风险面。
3. 为每个相关 job 选择一个本地等价命令；如果本地没有等价命令，必须写明缺口原因。
4. 先运行本地等价命令，再允许完成型用户故事 commit；完成型代码用户故事默认还必须运行 `./scripts/test/test-local.sh all`。如果用户要求 push，再在 push 前复核这些命令仍覆盖当前 HEAD。

本地验证选择规则：

- 改 Python 后端、共享脚本或测试工具：至少运行对应 `pytest` 聚焦用例和 `python3 -m py_compile` / 关键 lint；触及共享运行时或跨模块契约时扩大到相关测试目录。
- 改 TypeScript / React 前端：至少运行 owning package 的 test、lint 或 build 中与 CI 最接近的一组；如果依赖缺失，先说明缺失，不要把未运行验证包装成通过。
- 改 API、SSE、artifact contract、workflow manifest、持久化模型或主用户路径：必须覆盖后端契约测试、前端解析 / 状态测试和必要的浏览器或 E2E 验收，除非当前环境明确缺少依赖或外部权限。
- 纯文档 / playbook / todo 更新：运行文档核对清单、`git diff --check`，并确认链接 / 路径 / 规则不与事实源冲突；通常不需要代码测试。
- 改生成产物、zip、镜像配置或部署脚本：必须运行对应生成、校验或健康检查命令；不能只提交生成文件而不验证生成来源。

若无法运行 CI 等价验证，必须在收尾说明中写明具体命令、失败或未运行原因、是否会导致提交 / push 暂缓，以及需要用户提供什么条件。不得在已知关键验证缺失或失败时默认 push；除非用户明确要求带风险推进，并且收尾说明记录风险。

## 3. 收尾 CI 等价表

提交到 GitHub 前的收尾说明必须包含一个简短 CI 等价表：

| 远端 CI / 风险面 | 本地等价命令 | 结果 | 未覆盖原因 |
| --- | --- | --- | --- |
| <job 或风险面> | `<command>` | <通过 / 失败 / 未运行> | <无或具体原因> |

每轮收尾前必须明确回答“本地为什么能或不能挡住对应 CI 失败”。默认按以下口径记录：

- 已跑的本地命令分别覆盖哪些远端 CI job 或风险面。
- 哪些远端 CI job 没有本地等价运行，原因是什么，例如依赖缺失、网络 / 凭证不足、耗时过高、只影响文档，或当前改动不会触发该 job。
- 如果只运行了聚焦测试，说明为什么聚焦范围足够，哪些共享路径没有被触及。
- 如果改动触及共享 runtime、SSE/API、artifact contract、持久化模型、workflow manifest、前端主路径、生成产物或部署脚本，不得只跑单个局部测试；必须扩大到最接近 CI 的组合验证，或明确暂缓 commit / push。
- 如果本地验证失败、未运行关键验证或无法判断 CI 等价性，默认不得 push；是否允许 commit 取决于该 commit 是否只是保存未完成工作。完成型用户故事 commit 必须等关键验证通过或由用户明确接受风险。若全仓本地验证脚本未能让严重 lint、测试、构建或 E2E 失败反映为非零退出，必须修正脚本或额外运行对应命令并记录原因。

## 4. 远端 CI 失败复盘

如果远端 CI 失败，下一轮排查必须先比较“远端失败 job”和“本地本轮实际运行命令”的差异，判断是本地漏跑、环境差异、依赖版本、外部服务、并发时序还是真实回归。不能直接猜测修复，也不能把远端 CI 当作首次验证渠道。

远端 CI 失败复盘必须形成下一轮输入，而不是临时口头解释。复盘时至少记录：

1. 失败 job、失败命令、失败日志中的首个真实错误和对应 commit。
2. 本地提交前实际运行过的命令，以及缺失的本地等价命令。
3. 根因分类：漏跑本地验证、环境差异、依赖版本差异、外部服务 / 凭证、测试时序、生成产物未同步、真实代码回归或 CI 配置问题。
4. 修复策略：补本地可复现测试、更新验证矩阵、修代码、修文档记录、修 CI 配置，或补充无法本地复现的原因。
5. 是否需要更新 `docs/todos/`、本手册或相关测试说明，避免同类 CI 失败再次只在远端暴露。

远端 CI 失败后的下一轮默认用户故事不是继续做新功能，而是先完成一个“CI 失败复现与防复发闭环”，除非用户明确改判优先级。这个闭环至少要做到：

- 在 CGA 中把远端失败作为当前事实源，列出失败 job、本地漏跑或本地无法复现的原因。
- 如果属于本地漏跑，补充本地等价命令到本文、`docs/TESTING.md`、相关 todo 或 package scripts 中的合适位置。
- 如果属于环境差异，记录差异条件、为什么本地不能完全覆盖，以及后续如何用 smoke、health check 或 CI job 缩小差距。
- 如果属于真实回归，先补失败测试或复现脚本，再修代码；不能只按日志猜测改动。
- 修复后必须运行能覆盖该失败 job 的本地命令，并在收尾说明中明确“这次为什么能挡住同类 CI 失败”。
