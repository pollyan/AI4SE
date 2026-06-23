# Workflow Scaffold Codegen 设计

## 背景

New Agents 已有 `workflow_manifest.json`、前端 prompt/template、后端 `WORKFLOW_STAGES`、artifact contract、artifact_data renderer/readiness 和 handoff 的同步 dry-run。当前 dry-run 能发现漏配，但新增 workflow 仍要维护者手工复制多处骨架，容易在进入业务 contract 设计前就产生命名、文件、prompt export 或 manifest 结构错误。

本轮交付 E12 剩余的 workflow scaffold/codegen 工程信任闭环：从一个受校验的 JSON spec 预览或生成最小 workflow 骨架，并把后续完整上线需要补齐的 backend contract、renderer/readiness 等缺口交给现有 dry-run 显式报告。

## 自问自答式头脑风暴

问：真实用户意图是什么？
答：维护者新增或试验 New Agents workflow 时，需要先得到一致、不会覆盖现有文件的共享 workflow 骨架，再继续补齐业务 contract，而不是在多个配置面手工复制后等待 CI 才暴露漏配。

问：完成后用户多完成了什么？
答：用户可以准备一个 JSON spec，运行 preview 查看将生成的 manifest/prompt 骨架和后续 dry-run 命令；确认后用 write 模式写入文件。非法 spec、重复 stage/template、已有 workflow 或已有 prompt 文件都会明确失败。

问：哪些相邻小缺口应合并？
答：spec 校验、manifest workflow block 生成、prompt skeleton 生成、preview 输出、write 防覆盖、CLI 错误码、dry-run 后续命令提示、pytest 和 todo 记录必须一起交付。只做其中任意一项都会退化为薄切片。

问：哪些内容必须排除？
答：不自动上线真实业务 workflow；不生成完整 `agent_contracts.py`、artifact_data renderer/readiness 或前端 `workflows.ts` 映射；不新增 agent 专属 runtime、API path、store 或 renderer；不调用 LLM。scaffold 的职责是生成共享骨架和显式暴露剩余缺口，不伪造完整能力。

问：可行路径有哪些？
答：
1. 扩展 `new_agents_workflow_dry_run.py` 增加 scaffold 子命令。入口少，但 dry-run 和 codegen 职责混杂。
2. 新增 `new_agents_workflow_scaffold.py`，独立完成 spec 校验、preview/write 和 dry-run 后续提示。边界清晰，测试简单。
3. 做完整多文件 codegen，一次生成 manifest、prompt、backend contract、renderer/readiness 和前端映射。看似省事，但会生成大量业务占位，容易造成假完整。

推荐路径：选择 2。它形成完整 scaffold/codegen 闭环，又保留现有 dry-run 作为权威同步门禁，符合“显式失败，不伪造成功”的仓库原则。

问：主要风险是什么？
答：manifest 写入可能造成格式重排；prompt export 命名可能不符合 dry-run 规则；用户可能误以为 scaffold 后即可上线。设计上通过临时仓库测试写入、固定 `*_PROMPT` / `*_TEMPLATE` export、CLI 明确 next dry-run 命令和“业务 contract 仍需补齐”来控制风险。

问：TDD 验收证据是什么？
答：先新增 scaffold preview/write/conflict/invalid/CLI 测试并观察 RED，再实现脚本；最后运行 scaffold 测试、当前 dry-run、Python 语法检查和 diff 检查。

## 用户故事

作为 New Agents 平台维护者，当我要新增共享 workflow 时，我可以用一个 JSON scaffold spec 预览或生成一致的 workflow 骨架，并用 dry-run 继续定位未补齐的 contract/readiness 缺口，从而降低漏配、覆盖和 CI 失败风险。

## 输入格式

脚手架读取 JSON 文件：

```json
{
  "workflowId": "SUPPORT_TRIAGE",
  "agentId": "lisa",
  "slug": "support-triage",
  "name": "支持工单分诊",
  "description": "帮助支持团队结构化分诊支持工单",
  "welcomeMessage": "你好，我会帮助你完成支持工单分诊。",
  "starterPrompts": ["请帮我分诊这个线上支持工单。"],
  "stages": [
    {
      "id": "INTAKE",
      "name": "信息收集",
      "promptTemplateId": "support_triage.intake",
      "artifactTitle": "# 支持工单分诊"
    }
  ]
}
```

校验规则：
- `workflowId` 和 stage `id` 使用大写数字下划线标识符。
- `agentId`、`slug`、`name`、`description`、`welcomeMessage` 非空。
- `slug` 使用小写 kebab-case。
- `promptTemplateId` 使用 `<folder>.<file>`，两段均为小写 snake_case。
- stage id 和 promptTemplateId 不允许重复。
- write 模式下，已有 workflow 或已有 prompt 文件默认失败，不覆盖。

## 输出行为

新增 CLI：`python3 scripts/validation/new_agents_workflow_scaffold.py --spec <spec.json> [--repo-root <repo>] [--write]`

preview 默认行为：
- 不写文件。
- 输出 planned writes，包括 `tools/new-agents/workflow_manifest.json` 和每个 prompt 文件路径。
- 输出后续 dry-run 命令：`python3 scripts/validation/new_agents_workflow_dry_run.py <repo-root>`。

write 行为：
- 更新 `tools/new-agents/workflow_manifest.json` 的 `workflows` 对象，插入最小 workflow block。
- 创建每个 `tools/new-agents/frontend/src/core/prompts/<folder>/<file>.ts` prompt skeleton，导出 `*_PROMPT` 和 `*_TEMPLATE`。
- 不自动修改前端 `workflows.ts` 映射、后端 contract、renderer/readiness；后续由 dry-run 显式报缺口。

## 文件范围

创建：
- `scripts/validation/new_agents_workflow_scaffold.py`

修改：
- `tools/new-agents/backend/tests/test_workflow_dry_run.py`
- `docs/todos/refactor/README.md`
- `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md`

## 验收条件

1. Given 合法 scaffold spec，When preview，Then CLI 展示 planned writes 和 dry-run 命令，且不写文件。
2. Given 合法 scaffold spec 且目标不存在，When write，Then manifest 增加 workflow block，prompt skeleton 文件创建且导出 `*_PROMPT` / `*_TEMPLATE`。
3. Given 已存在 prompt 文件或 workflow id，When write，Then 失败并保留原文件。
4. Given 非法 workflow id、slug、promptTemplateId 或重复 stage/template，When 加载 spec，Then 抛出明确错误。
5. Given 当前仓库，When 运行现有 dry-run，Then 当前在线 workflow 同步门禁仍通过。

## 验证计划

聚焦验证：
- `python3 -m pytest tools/new-agents/backend/tests/test_workflow_dry_run.py -q`
- `python3 scripts/validation/new_agents_workflow_dry_run.py .`
- `python3 -m py_compile scripts/validation/new_agents_workflow_scaffold.py scripts/validation/new_agents_workflow_dry_run.py`
- `git diff --check`

CI 等价门禁：
- 本轮只新增 Python 脚本、Python 测试和文档，不触碰 New Agents 前端 TypeScript、shared runtime、SSE/API、artifact contract、持久化模型或主用户路径；CI 等价本地门禁以相关 pytest、Python 语法检查和 dry-run 为准。
- 不运行真实 DeepSeek smoke；本轮不交付真实外部模型证据。
