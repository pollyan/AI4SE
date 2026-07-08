# ROOT_CAUSE cause-map 结构化视觉纵切设计

## 目标承接检查

当前目标继续消化 `docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md`。Alex handoff 路线已完成，partial artifact streaming 路线已收口，上一轮已完成 `IDEA_BRAINSTORM/CONVERGE` 的 `artifactDataContract` 同步纵切并推送。当前没有未关闭的阻断测试、低于 80 分的 LLM judge 或用户新反馈需要改道。

本轮承接第 7 轮视觉产物稳定化专项，但不一次性完成全部视觉协议迁移。选择 `INCIDENT_REVIEW/ROOT_CAUSE` 的 `cause-map` 作为首个复杂 `ai4se-visual` 纵切，原因是它已经由后端从结构化 `artifact_data.why_chain` 确定性生成，业务语义天然是节点和因果边，却仍被前端按通用表格渲染。把它升级为节点 / 边结构，可以形成一个完整闭环：后端输出复杂图数据、前端解析强校验、前端按复杂图渲染、prompt/template 与测试同步更新。

工作区存在大量与本轮无关的既有脏文件和删除项。本轮只允许写入：

- `tools/new-agents/backend/artifact_data_renderers.py`
- `tools/new-agents/backend/agent_contracts.py`
- `tools/new-agents/backend/tests/test_agent_contracts.py`
- `tools/new-agents/backend/tests/test_artifact_data_renderers.py`
- `tools/new-agents/backend/tests/test_workflow_contract_sync.py`
- `tools/new-agents/frontend/src/core/structuredVisuals.ts`
- `tools/new-agents/frontend/src/core/__tests__/structuredVisuals.test.ts`
- `tools/new-agents/frontend/src/core/artifactExport.ts`
- `tools/new-agents/frontend/src/core/__tests__/artifactExport.test.ts`
- `tools/new-agents/frontend/src/core/docxExport.ts`
- `tools/new-agents/frontend/src/core/__tests__/docxExport.test.ts`
- `tools/new-agents/frontend/src/components/StructuredVisual.tsx`
- `tools/new-agents/frontend/src/components/__tests__/StructuredVisual.test.tsx`
- `tools/new-agents/frontend/src/core/prompts/incident_review/root_cause.ts`
- `docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md`
- 本 spec 和对应 plan

子智能体 / 旁路审查决策：本轮跨后端 renderer 和前端视觉组件，但只围绕一个 visual type，写入范围小且接口连续；不分发子智能体。验证会覆盖后端 renderer、前端 parser、前端组件和 New Agents 回归。

## 方案比较

方案 A：只给 `cause-map` 增加前端专用样式，但继续消费 `columns/rows` 表格 JSON。实现最小，但没有解决复杂图仍被表格协议承载的问题，不符合第 7 轮“复杂图优先结构化”的方向。

方案 B：新增通用节点 / 边形态，并让 `cause-map` 消费 `nodes/edges`。后端从 `why_chain` 确定性生成节点和因果边；前端 parser 校验节点唯一性与边引用完整性；组件用共享 `StructuredVisual` 渲染节点链路。这个方案能形成完整纵切，且不会新增 workflow 专属 renderer。

方案 C：把 ROOT_CAUSE 的鱼骨图 Mermaid mindmap 也迁移为新的 `mindmap` 或 `flow-map`。价值更大，但同时影响 artifact contract、prompt、导出和现有 Mermaid 证据，切片过宽。

本轮采用方案 B。方案 C 保留为后续第 7 轮继续推进的候选。

## 设计

`ai4se-visual` 新增节点 / 边形态，首个使用者是 `cause-map`：

```json
{
  "type": "cause-map",
  "title": "5-Why 根因链路图",
  "nodes": [
    {
      "id": "Why-1",
      "label": "Why-1",
      "title": "直接原因",
      "description": "发布前缺少关键路径回归门禁",
      "category": "流程",
      "evidence": "发布记录与测试记录",
      "confidence": "高",
      "status": "已确认"
    }
  ],
  "edges": [
    {
      "source": "Why-1",
      "target": "Why-2",
      "label": "继续追问"
    }
  ]
}
```

前端 `parseStructuredVisual()` 保留现有矩阵类视觉的 `columns/rows` 支持，同时对 `cause-map` 支持并优先校验 `nodes/edges`：

- `nodes` 必须是非空对象数组。
- 每个 node 必须有非空唯一 `id`、非空 `label` 和非空 `title`。
- `edges` 必须是数组；每条 edge 的 `source` 和 `target` 必须引用已存在 node。
- `description`、`category`、`evidence`、`confidence`、`status`、`label` 可选，但如果出现必须是非空字符串。

前端 `StructuredVisual` 根据 `visual.kind` 分流：矩阵形态仍渲染 table；节点 / 边形态渲染一组按顺序排列的节点和连接说明，并保留可读文本，便于截图、导出降级和无障碍查询。错误仍通过现有 validation callback 显式反馈。

PDF / DOCX 导出层同步消费 `visual.kind`。矩阵类视觉继续导出表格；节点 / 边类视觉导出标题、节点列表和连接列表的可读文本，不把原始 JSON 或旧表格结构泄漏给用户。

后端 `_render_incident_why_chain()` 改为输出 `cause-map` 的 `nodes/edges`，不再把 `cause-map` 生成为 `columns/rows`。节点顺序沿用 `why_chain` 顺序，边连接相邻项，标签使用“继续追问”。这仍是后端 deterministic renderer，从模型输出的结构化 `artifact_data` 编译而来，不要求模型手写 Mermaid 或前端反解析 Markdown。

`ROOT_CAUSE_TEMPLATE` 和后端 artifact contract 校验中的 `cause-map` 示例同步改为 `nodes/edges`。鱼骨图 Mermaid mindmap 本轮不迁移，仍由后端 renderer 从 `fishbone_categories` 确定性生成；本轮不把 Mermaid repair 或旧图缓存纳入成功路径。

## 验收标准

- 后端 ROOT_CAUSE partial 和 final artifact 中的 `cause-map` block 使用 `nodes/edges`，不再包含 `columns/rows`。
- 前端 parser 能解析 `cause-map` 节点 / 边结构，并显式拒绝重复 node id、未知 edge 引用和缺少必填字段。
- 前端 `StructuredVisual` 能把 `cause-map` 渲染为非表格的节点 / 边视图，并继续通过 validation callback 报告成功或失败。
- PDF / DOCX 导出能把 `cause-map` 节点 / 边结构投影成可读文本，不再假设所有 `ai4se-visual` 都有 `columns/rows`。
- `ROOT_CAUSE_TEMPLATE` 的 `cause-map` 示例与新协议一致。
- 后端 `agent_contracts.py` 的 structured visual contract 能接受合法 `cause-map` 节点 / 边结构，并拒绝缺失节点引用。
- 现有矩阵类 `ai4se-visual` 类型继续保持兼容。
- New Agents 相关前后端回归通过；提交前按目标模式执行全量本地验证或记录明确环境权限例外。
