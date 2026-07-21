# 固定全量 Pre-push 门禁与生产发布安全待办

- 状态：`ACTIVE`
- 创建日期：2026-07-21
- 完成情况：0/2
- 当前入口：`QG-021`
- 唯一范围：固定全量 pre-push 质量保障、测试分层去重、真实本地部署 E2E，以及随后处理已确认的生产发布事务风险
- 事实审计：[`本地提交 / 推送前验证审计`](../test_requirements/2026-07-21-pre-push-local-validation-audit.md)

## 用户决定

2026-07-21 用户明确要求：每次 push 到 GitHub 前运行固定全量测试，不依据 diff、路径或 Agent 影响分析缩减范围。效率优化必须通过合理分层、合并重复门禁、删除无效或低效率测试完成。除高效率的单元/API/模块/契约测试外，主干功能优先由真实环境、尽量少 mock 的无头 E2E 保障；不追求截图或像素级回归。

用户同时确认把本轮审计发现的三个生产发布阻断风险写入待办，但先完成本地 pre-push 验证闭环，再按顺序处理发布事务。未来启动目标模式时必须按 `QG-021 → QG-022` 执行，不得跳过、并行交付或从旧归档恢复其他候选。

## 待办总览

| ID | 优先级 | 能力包 | 状态 | 独立验收目标 |
|---|---|---|---|---|
| `QG-021` | P1 | 固定全量 pre-push 质量门禁与测试去重 | `IN_PROGRESS` | 任意 push 前由一个固定入口完成全仓确定性门禁、production-shaped 本地部署和部署栈真实 DeepSeek 7-workflow E2E；不按 diff 选测且无重复/污染 |
| `QG-022` | P0 | 可信生产发布事务与完整 readiness | `TODO` | 备份/回滚身份可信、构建失败不先停服、健康检查覆盖真实 New Agents 前端和主干链路；失败可安全恢复且并发发布受控 |

## QG-021 — 固定全量 Pre-push 质量门禁与测试去重

### 用户问题

按 diff 选择测试依赖 Agent 或人的影响分析，恰好会遗漏未知耦合和认知盲区；bug 又常来自这种遗漏。当前多个 runner、低层测试、mock-browser、LiveStack 和真实模型矩阵存在重叠，但不能用缩小执行范围解决效率问题。

### 目标状态

- 每次 push 到 GitHub 前运行相同的固定全量范围，文档或小改动也不跳过。
- 开发过程中继续使用聚焦测试做 TDD；只有 pre-push 承担全量交付判断。
- 一个 canonical runner 按便宜到昂贵执行全仓技术门禁、确定性跨层、production-shaped 本地部署和部署栈真实模型 E2E。
- 测试按不变量确定主要责任层；重复、无效和低效率测试通过 KEEP/MOVE/MERGE/DELETE 迁移去重，不能降低覆盖。
- 真实 E2E 使用无头 Chromium、真实 Docker/Nginx/Gunicorn/PostgreSQL、真实 frontend/backend/SSE/persistence 和真实 DeepSeek；不以截图或像素差异为门禁。

### 验收规则

- 唯一 pre-push 命令不接受 diff/path scope，不提供静默跳过或低层替代高层的兼容路径。
- 全仓单元/API/模块/契约、lint/typecheck/build、root gate、浏览器与真实模型门禁均有唯一调用位置和机械可查的覆盖归属。
- 真实 Release 在已部署本地栈上覆盖 7/7 workflow、25/25 stage、格式、流式、阶段推进、持久化与刷新恢复。
- 缺工具、Docker、浏览器、凭证、测试零收集、模型波动、超时、清理失败或工作区污染均非 PASS，并阻止 push。
- 运行证据绑定当前 `HEAD`；测试后任何事实变化使证据失效。
- 正式设计见 [`QG-021 spec`](../superpowers/specs/2026-07-21-fixed-full-pre-push-quality-gate-design.md)。

### 非目标

- 不在本项引入产出物 LLM judge/评分；该话题后续独立设计。
- 不在本项修复生产发布事务；只建立可暴露部署风险的本地验证边界。

## QG-022 — 可信生产发布事务与完整 Readiness

### 顺序与边界

只有 `QG-021` 完成并提交后才能进入本项。本项必须在自己的 Goal Mode `ASSESS/DESIGN/PLAN` 中重新读取生产事实并形成独立 spec；以下三项是已确认风险和验收底线，不是预先批准的实现方案。

### 阻断风险 1：备份与回滚身份不可信

当前 GitHub workflow 先用 `rsync --delete` 覆盖 live 目录，部署脚本随后才从 live 创建 backup。该 backup 可能已经是新版本；回滚也没有机械证明恢复了上一版本镜像、代码和运行身份。

验收底线：部署前冻结并记录旧 release identity；新版本失败时能恢复并核验旧代码、镜像、配置引用和服务状态，不用“命令执行成功”代替真实恢复证据。

### 阻断风险 2：先停服务再构建

当前生产脚本在 Docker build 前执行 Compose down 和广泛容器/网络清理。构建、拉取依赖、初始化或启动失败会造成不必要停机，且部分失败发生在 rollback 分支之前。

验收底线：新 release 在不影响当前服务时完成构建和预检，再执行受控切换；构建失败不触碰当前服务，并发部署不能互相删除临时目录、容器或网络。

### 阻断风险 3：健康检查遗漏真实 New Agents 主链路

当前 health 容器和页面清单没有完整覆盖 New Agents frontend；`/new-agents/api/health` 只证明 backend 浅存活，Nginx `/health` 又是固定 `200`，不能证明真实上游、SSE、数据库或页面工作流可用。

验收底线：readiness 覆盖所有目标容器、New Agents 页面、真实 Nginx upstream、关键 API/SSE、数据库读写和恢复；负向 mutation 能证明任一关键上游损坏都会使发布失败并触发可信恢复。

### 共同验收规则

- 发布事务绑定 immutable release/SHA，不在 live 目录上原地覆盖后再猜测版本。
- 构建、预检、切换、readiness、失败恢复和并发互斥都有自动化证据。
- docs/test-only 变更是否发布由未来设计明确裁决；在此之前不得用 path skip 破坏 required checks。
- 部署文档、workflow、脚本和实际生产行为保持一致，不保留虚假回滚或浅健康声明。

## 执行与归档规则

- 目标模式从 `QG-021` 开始；完成后更新本文件证据和下一入口，再进入 `QG-022`。
- 每个能力包以完整厚切片形成独立 spec、plan、验证、审查、commit 和交付，不把内部测试迁移批次记为额外进度。
- 两项全部终结后才归档本文件。历史归档中的 QG、QS、E 编号或旧 checkbox 不得自动恢复。
- 活动待办只保留本文件；三个发布风险属于 `QG-022`，不得再复制成多个竞争 backlog。
