# QS-03 Intent Tester 真实执行与持久化闭环设计

## 厚切片身份基线

- **ID / 名称**：`QS-03 — Intent Tester 真实执行与持久化闭环`。
- **完整用户任务**：用户从 Intent 页面创建一次真实执行后，可以围绕同一个 durable execution ID 观察进度、停止、重试，并在服务重启后恢复和解释终态。
- **纳入边界**：Flask durable record、production Node proxy、canonical ID、lifecycle callback、页面状态承接、scoped stop、same-ID retry/recovery、real HTTP 组合证据和可复现下载 package。
- **排除边界**：真实付费 AI provider、Intent 认证/XSS/CSP（`QS-04`）、跨服务发布与回滚事务（`QS-05`）、New Agents runtime。
- **七项门禁**：入口是 Intent execution page；动作是创建、查看、停止、重试或恢复一次执行；处理是 Flask 创建 durable authority 并驱动 Node 及幂等 callback；可见结果是同一 ID 的进度与显式终态；状态承接是 DB、页面对账和重启恢复；失败反馈是可诊断的 pending/running/failed/stopped 与同 ID 恢复路径；证据是 API、production Node、real HTTP restart/stop/retry 和 clean-room package smoke。
- **依赖 / 验收 / 交付**：依赖已完成的 `QS-01`；只有上述用户链和全部验证门禁共同闭合后，才形成一个 `QS-03` 聚焦 commit 和交付。页面、retry、real HTTP 与 package 都是内部实现步骤，不是子切片。

本设计执行时，用户确认的顺序以 [已归档的 AI Coding 测试质量改进待办](../../todos/archive/2026-07-10-ai-coding-test-quality-improvement.md#厚切片序列) 为历史顺序基线；该旧序列已于 2026-07-16 由用户取消，不再是当前执行入口。

## 目标与边界

用户从 Intent 页面发起一次执行后，Flask 先创建唯一 `execution_id` 和 durable `pending` 记录；同一 ID 传给 production Node proxy，Node 的 started/result callback 只更新该记录。停止、失败和恢复均有可解释终态。本切片不调用付费模型、不处理认证/XSS/CSP（QS-04），也不做部署事务（QS-05）。

## 当前事实与问题

`backend/api/executions.py` 仅创建 `pending` 记录；`browser-automation/midscene_server.js` 的 `/api/execute-testcase` 再生成另一 ID，导致 Flask 历史与真实代理执行脱节。Node 已有 callback 字段和 stop endpoint，但 Flask 端缺少受控、幂等的 lifecycle callback contract，现有 proxy HTTP 测试还以简化 HTTP server 取代 production app。

## 方案比较与裁决

1. **Flask 轮询 Node 内存状态**：改动小，但重启丢失状态，且无法证明 callback 契约。拒绝。
2. **Node 为权威，Flask 镜像**：会把页面历史绑定到 proxy 内存和启动时序。拒绝。
3. **Flask 为 durable authority，Node 接收 canonical ID 并回调**：ID、终态和重放边界统一，Node 仍是 production 执行端。采用。

## 架构与状态机

Flask API 创建 execution 后调用一个可注入的 proxy client；proxy 收到 `executionId` 后不再生成 ID。回调使用受限的 started/result schema：`pending -> running -> success|failed|stopped`。相同 started/result 重放是 no-op；终态不会被旧 callback 覆盖；未知 ID、非法状态转移和 payload 错误返回显式 4xx。stop 先请求 Node 的 scoped `/api/stop-execution/:id`，成功后 Flask 持久化 `stopped`；proxy 不可达时保留可诊断的未停止状态，不伪造成功。

## 组合验证

Python real-HTTP test 启动真实 Flask 与一个协议等价的本地 Node fixture，验证一次创建只产生一个 ID，并覆盖 duplicate callback、失败 callback、scoped stop 和 restart 后从数据库读取状态。Node Jest test 直接加载 production `midscene_server.js` 的 app/export seam，验证 caller-supplied ID 被保留、缺失 ID 拒绝、停止不影响其他 execution。下载包 smoke 在干净临时目录解压并启动 package health endpoint。

## 失败与非目标

callback 网络失败会留下 `pending/running` 和诊断，不把它标为 success；执行器失败必须回调 `failed`。本切片使用 fake Playwright/AI adapter，因而不证明真实供应商质量；该边界记录为 QS-06。
