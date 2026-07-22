# QG-023：New Agents 双层 E2E 收口设计

- 日期：2026-07-22
- 状态：已获用户确认，立即实施
- Owning todo：[QG-023](../../todos/refactor/2026-07-22-new-agents-two-tier-e2e-consolidation.md)
- 前置事实：[QG-021 固定全量 pre-push](2026-07-21-fixed-full-pre-push-quality-gate-design.md)

## 厚切片身份基线

开发者或 CI 从固定 New Agents E2E 入口触发质量验证；系统用两道职责明确的门禁证明可见流式、阶段流转、持久化和真实发布质量；失败返回可定位的确定性或真实模型证据；最终结果可由固定全量 pre-push 绑定到当前 `HEAD`。本切片不以删除文件为目标，而以消除“第三套 E2E 的错误分层”同时保留全部独有风险覆盖为目标。

## 当前事实、评估与决定

当前有三处相关执行集合：

| 集合 | 当前职责 | 独有价值 | 问题 |
| --- | --- | --- | --- |
| `tests/e2e/new_agents_browser/` | 真实 Vite/Chromium + controlled typed SSE | 精确观察 chat/artifact 分帧、artifact-first、retry、全 workflow handoff/Story packet 和元信息尾注 | 不是服务端真实链路，不能证明 Flask/SQLite 持久化 |
| `test_live_stack.py` | 同文件混合真实 React/Vite/Flask/SQLite/Chromium tracer 与 observer/安全 helper | 两个 tracer 证明本仓库全链路；其余 16 个用例证明 observer、SSE 诊断及启动日志脱敏 | 只有两个用例是真正的 live-stack E2E，其他被错误计入第三套 E2E |
| `test_real_agent_workflows.py` | production-shaped 部署 + headless Chromium + DeepSeek | 7 workflow、25 stage、18 transition 的真实发布事实 | 不能稳定注入坏事件，也不适合取代确定性故障测试 |

候选比较：

1. **只保留真实 Release E2E**：拒绝。它不能确定地触发 artifact-first、SSE 损坏、retry 或渲染重写，也无法以低成本定位浏览器/协议回归。
2. **保持三套独立 E2E**：拒绝。live-stack 文件中绝大多数不是端到端主旅程，门禁和报告把契约测试误列为另一层 E2E。
3. **两层 E2E，observer/helper 下沉到契约层**：采用。确定性功能 E2E 覆盖受控时序和一条真实服务链路；真实 Release E2E 覆盖真实模型和部署发布事实。

## 方案与组件边界

### 1. 确定性功能 E2E（evidence level 3）

canonical suite 名称为 `new-agents-deterministic-e2e`。它运行两个互补 adapter，但作为一个质量门报告；runner 固定把二者置于不同 pytest 子进程，避免同步 Playwright 生命周期相互嵌套：

- `tests/e2e/new_agents_browser/` 保留全部 7 workflow 的无头 Chromium 流式、阶段、handoff、Story packet 和 metadata footer 检查。其 controlled typed SSE 只控制外部 Agent Runtime 响应，不替换被验收的前端流式状态与渲染。
- 新的 `test_deterministic_live_stack.py` 只保留一条两阶段 `TEST_DESIGN: CLARIFY → STRATEGY` tracer。它在同一真实 LiveStack 中同时检查 forged config 不能授权、`runId` 复用、chat 先于 artifact、至少两个 artifact delta、snapshot/version、服务端恢复、`agent_turn` 完成与第二阶段新 chat 后才出现 artifact。

不能把 browser workflow runner 与 real workflow runner 强行抽象成单一“大接口”：两者的 external seam 和证据模型不同。仅在 gate registry 上收口，在断言语义上保持相同的用户可见不变量。

### 2. 确定性契约层（evidence level 2）

以下现有用例从 `test_live_stack.py` 移到 `test_live_stack_contracts.py`，在 `new-agents-real-contracts` suite 内执行：启动失败日志/traceback 脱敏、DOM observer 的 retry/metadata/source watermark/rewrite 行为，以及 stream observer 的安全字段、错误投影、heading 插入和 malformed SSE 行为。

这些用例继续使用真实 Playwright DOM 和 production observer script；它们不是服务端到浏览器主旅程，故不再承担 E2E suite 身份。迁移不得改变断言或放宽 secret redaction。

### 3. 真实模型 Release E2E（evidence level 4）

`new-agents-deployed-real-release` 保持不变：production-shaped Compose 栈、headless Chromium、已配置 DeepSeek、7/7 workflow、25/25 stage、18 次合法 transition。它继续是 push 前固定门禁的最终真实发布证据，缺凭证、零收集、超时、波动或清理失败均不可降级为 PASS。

## 数据流和失败行为

确定性 gate 先跑，任一 UI 时序/服务端持久化/契约坏路径失败即阻止后续昂贵 release；release 只在部署成功后消费来自受保护环境的真实模型配置。suite journal 仍记录 collected、executed、非 PASS 与 current `HEAD`，不得记录 secret、原始浏览器 storage 或 provider 原始日志。

`test-local.sh e2e` 和 CI deterministic job 必须先调用 required contracts，再调用同一个确定性 E2E 边界（browser suite + 单一 live tracer）；不同 pytest session 分开运行以避免 Playwright event-loop 生命周期交叉。contracts 的 evidence level 是 2，不能被报告为第三条 E2E。测试文档必须明确“两个门禁”而非把目录数误写成门禁数。

## 测试设计与验收

1. RED：更新 `tests/test_pre_push_gate.py`，要求固定 registry 不再出现独立 `new-agents-live-stack` 与 `new-agents-browser-e2e`，而有唯一 `new-agents-deterministic-e2e`，且命令同时覆盖 browser 与新的两阶段 tracer。
2. RED：为新 live-tracer 文件建立两阶段旅程断言；先让它在目标路径不存在时失败，再移植并合并既有两条 live-stack journey。
3. GREEN：把其他 16 个 observer/helper 用例逐字迁到契约文件；确定性 contracts suite 收集它们，E2E gate 只收集新 tracer 与 browser workflow。
4. 同步 `scripts/test/pre_push.py`、`scripts/test/test-local.sh`、`.github/workflows/deploy.yml`、`docs/TESTING.md` 及 generated suite ownership 视图；为 registry、CI 命令和本地脚本添加漂移测试。
5. 验证先跑受影响 pytest、browser E2E、new two-stage live tracer、registry/CI contract；最后从当前最终 `HEAD` 运行 `./scripts/test/pre-push.sh`。不以局部绿色替代最终全量门禁。

## 非目标

- 不加入产出物 LLM judge/评分；该项仍按用户要求在本轮结束后另行设计。
- 不减少真实 Release E2E 的 workflow/stage/transition 覆盖。
- 不做 screenshot 或像素比较。
- 不顺手删改单元/API/前端 Vitest；它们的进一步精简需要独立的覆盖归属审计。
