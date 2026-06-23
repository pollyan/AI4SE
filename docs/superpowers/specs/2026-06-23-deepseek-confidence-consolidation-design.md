# DeepSeek 结构化输出信任闭环整合 Spec

## 背景

当前 `master` 已完成 DeepSeek V4 结构化产物数据的大部分垂直切片，但三个已经验证的信任闭环分支仍停留在独立 worktree:

- `codex/deepseek-readiness-gate`: DeepSeek V4 readiness gate，证明核心结构化输出链路、prompt 契约和 renderer registry 可被本地门禁覆盖。
- `codex/deepseek-artifact-data-persistence`: `artifact_data` 进入 `AgentTurnOutput`、typed SSE snapshot、run/artifact 持久化与迁移。
- `codex/deepseek-real-smoke-gate`: 真实 DeepSeek 冒烟门禁改为校验原始 `artifact_data`，并在缺少凭证/网络时明确 skip。

如果这些分支继续漂移，`docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md` 会持续把已完成能力当作未解设计问题，后续 DS 格式化输出工作也会反复踩到同一批运行时、持久化和验证缺口。

## 目标

本轮目标是把三个 DeepSeek 结构化输出信任能力合并到一个隔离整合分支，让后续 DeepSeek V4 格式化输出需求可以基于同一条已验证主线继续推进。

验收结果必须满足:

1. 新整合分支从 `master` 起步，红灯检查证明它一开始不包含三个目标分支。
2. 整合后，三个目标分支的关键能力都存在于当前 HEAD 历史或最终 diff 中。
3. `artifact_data` 继续走共享 Agent Runtime、typed SSE、workflow manifest、artifact contract、持久化 run/artifact 模型和共享 renderer registry。
4. 不新增 DeepSeek/Lisa/Alex 专属 API path、runtime、store 或 renderer 管线。
5. 本轮更新 DeepSeek todo，明确 readiness、persistence、real smoke gate 已整合，剩余真实联网 smoke 仍需要显式凭证、网络和额度。
6. 主工作区已有未提交改动保持不变。

## 非目标

- 不继续新增新的 workflow stage `artifact_data` schema。
- 不把 DeepSeek V4 Flash 升级为 strict JSON Schema provider。
- 不改前端视觉布局或用户交互。
- 不处理 New Agents enhancement diagnostic 的 E02/E04/E13/E14。

## 关键验收检查

- 红灯: `git merge-base --is-ancestor <target-branch> HEAD` 对三个目标分支均返回非 0。
- 绿灯: 整合后同样命令均返回 0，或通过等价 diff/commit 证明三个目标提交已进入整合分支。
- 后端最小扩展验证通过:
  - `test_deepseek_v4_readiness.py`
  - `test_artifact_data_renderers.py`
  - `test_run_persistence.py`
  - `test_stream_services.py`
  - `test_agent_endpoint.py`
  - `test_agent_runtime.py`
  - `test_agent_contracts.py`
  - `test_agent_real_smoke.py`
- `git diff --check` 通过。
- 主工作区 `git status --short` 仍只包含本轮开始时的 5 个既有脏文件。
