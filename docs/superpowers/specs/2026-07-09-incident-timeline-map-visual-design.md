# INCIDENT_REVIEW/TIMELINE timeline-map 复杂视觉迁移设计

## 背景

目标模式复核 `docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md` 后，确认结构化失败治理剩余 P1 不应继续按薄切片推进。下一厚切片选择 `INCIDENT_REVIEW/TIMELINE` 从 Mermaid `timeline` 迁移到 `ai4se-visual timeline-map`。

当前 TIMELINE 阶段已经使用 `artifact_data`，后端校验 `fact_sources` 和 `timeline_events[].fact_ids`，再确定性渲染右侧 artifact。但视觉 contract 仍要求 Mermaid `timeline`，后端还需要对时间标签做全角冒号转义，说明该视觉仍依赖易碎 DSL。顶层 `visualProtocol` 已声明复杂业务图优先使用 `ai4se-visual`，`timeline-map` 也已列为 planned complex type。本设计把这一 planned type 变成可运行的 current type。

## Explore Project Context

- `workflow_manifest.json` 顶层 `visualProtocol` 已声明模型只输出 `artifact_data`、Mermaid 由后端生成、复杂图优先 `ai4se-visual`。
- `INCIDENT_REVIEW/TIMELINE` 目前 `visualContract.requiredMermaidDiagrams` 仍是 `["timeline"]`，`rendererOutputs` 仍写 `Mermaid timeline`。
- `agent_contracts.py` 的 `REQUIRED_ARTIFACT_MERMAID_DIAGRAMS` 仍把 TIMELINE 列为 Mermaid 必需图；`REQUIRED_ARTIFACT_STRUCTURED_VISUALS` 未包含 `timeline-map`。
- `artifact_data_renderers.py` 已有 `IncidentTimelineArtifactData`、事实引用 validator 和 TIMELINE Markdown renderer。
- 前端 `structuredVisuals.ts` 支持 matrix visual 与 `cause-map` node-edge visual，不支持 timeline 专用结构。
- `StructuredVisual.tsx` 复用共享渲染入口；新增 visual type 不需要新增 ArtifactPane 分支。
- PDF/DOCX 导出已有 Mermaid timeline 降级逻辑和结构化 visual 降级逻辑，但需要让 timeline-map 导出为可读时间线，而不是 raw JSON。

## Visual Companion Decision

本轮是工程设计与实现计划，不涉及 UI 方案多选或视觉稿评审。可用文字描述 timeline-map 的可访问布局，不启用浏览器视觉 companion。

## Clarifying Questions

问：这个切片真正服务的用户意图是什么？
答：用户在做故障复盘时，需要稳定查看事件发生顺序、事实来源和阻断性，而不是排查 Mermaid `timeline` 语法。

问：为什么不是先做服务端视觉成功门禁？
答：服务端门禁是下一轮重要工程信任闭环，但它是横切成功语义。先落地一个复杂 `ai4se-visual` 类型，可以让门禁有更明确的 structured visual schema 和 fixture 目标，同时给用户可见增量。

问：哪些相邻缺口必须同轮纳入？
答：后端 renderer、visual contract、manifest protocol current types、前端 parser、前端 component、PDF/DOCX 导出、prompt/template 中 Mermaid 提示清理和同步测试必须同轮纳入。只做其中一层会形成不可用半成品。

问：哪些缺口本轮明确不做？
答：不迁移所有 Mermaid 类型，不做 `flow-map` / `mindmap` / `sequence-flow`，不改 Mermaid repair endpoint，不引入 `mmdc`，不新增 agent-specific runtime、SSE、store 或 ArtifactPane 渲染管线，不让模型直接输出 `ai4se-visual`。

问：timeline-map 是否需要修改模型 schema，让模型输出 event id？
答：不需要。事件 id 由后端 renderer 基于事件顺序确定性派生，例如 `TL-001`。这样不扩大模型负担，也不引入新的 ID 漂移风险。

## Approaches

### 方案 A：只把 Mermaid timeline 换成 matrix 型 timeline-map

做法：复用现有 matrix visual 协议，`timeline-map` 使用 `columns/rows` 表达时间、事件、事实 ID、可信度、阻断性、状态。

优点：改动小，前端组件和导出几乎不用新增结构。
缺点：只是换了 type 名的表格，不能体现 timeline-map 是复杂业务视觉；后续对流程/顺序/节点类视觉的复用价值有限。

### 方案 B：新增 timeline 专用 visual kind

做法：`timeline-map` 使用 `events` 数组表达事件节点，每个 event 包含 `id`、`time`、`title`、`description`、`factIds`、`confidence`、`blocking`、`status`。前端 `StructuredVisual` 新增 timeline 视图，导出层将 events 渲染为可读时间线。

优点：符合复杂业务图主协议目标；结构比 Markdown 表格更稳定；后续 `timeline-map` 可被其他 workflow 复用。
缺点：需要新增 parser、component、export 和 contract 校验。

### 方案 C：保留 Mermaid timeline，同时额外输出 timeline-map

做法：TIMELINE 同时保留 Mermaid `timeline` 和新增 `timeline-map`。

优点：迁移风险最低。
缺点：继续保留易碎 DSL，用户和测试仍要维护两套视觉；与“复杂图不再依赖 Mermaid”目标冲突。

推荐方案：方案 B。它是一个完整厚切片，既消除 TIMELINE 对 Mermaid timeline 的依赖，又为后续复杂 visual type 建立前后端模板。

## Presented Design

### Architecture

保持共享 New Agents runtime 和现有 artifact Markdown 载体不变。模型仍只输出 `artifact_data`；后端仍负责 deterministic renderer；前端仍通过 Markdown fenced `ai4se-visual` block 进入共享 `StructuredVisual`。变化只发生在配置、contract、renderer、前端 parser/component/export 和测试。

### Data Contract

`timeline-map` JSON 结构：

```json
{
  "type": "timeline-map",
  "title": "事件时间线",
  "events": [
    {
      "id": "TL-001",
      "time": "10:05",
      "title": "支付回调失败",
      "description": "第三方回调多次超时，订单状态未更新。",
      "factIds": ["F-001"],
      "confidence": "高",
      "blocking": "是",
      "status": "已确认"
    }
  ]
}
```

字段规则：

- `type` 必须是 `timeline-map`。
- `events` 必须是非空数组。
- 每个 event 必须包含非空 `id`、`time`、`title`、`description`。
- `factIds` 必须是非空字符串数组。
- event id 必须唯一，由后端 renderer 按事件顺序派生。
- `confidence`、`blocking`、`status` 可选但如果存在必须是非空字符串。

### Backend Changes

- `workflow_manifest.json`：
  - 把 `timeline-map` 从 `plannedComplexTypes` 移到 `currentTypes`。
  - `INCIDENT_REVIEW/TIMELINE.visualContract` 从 required Mermaid `timeline` 改为 required structured visual `timeline-map`。
  - TIMELINE `rendererOutputs` 改为 `ai4se-visual timeline-map`。
  - TIMELINE forbidden outputs 同步禁止 `timeline-map JSON 代码块`，保持模型不得直接输出 visual JSON。
- `agent_contracts.py`：
  - 从 `REQUIRED_ARTIFACT_MERMAID_DIAGRAMS` 移除 `("INCIDENT_REVIEW", "TIMELINE")`。
  - 在 `REQUIRED_ARTIFACT_STRUCTURED_VISUALS` 增加 `("INCIDENT_REVIEW", "TIMELINE"): ["timeline-map"]`。
  - 增加 `timeline-map` schema prompt 和 `is_valid_timeline_map_visual_block()`。
- `artifact_data_renderers.py`：
  - TIMELINE renderer 不再生成 Mermaid `timeline` fence。
  - 新增 `_render_timeline_map_visual()`，从 `timeline_events` 生成 `ai4se-visual timeline-map`。
  - 保留 Markdown 事件时间线表格，便于人读和纯文本导出。

### Frontend Changes

- `structuredVisuals.ts`：
  - `StructuredVisualType` 增加 `timeline-map`。
  - 增加 `TimelineStructuredVisual` 和 parser，校验 events、id 唯一性和必填字段。
- `StructuredVisual.tsx`：
  - 增加 timeline-map 视图：按时间顺序展示事件卡片，显示事实 ID、可信度、阻断性、状态。
  - 保持共享组件入口，不改 ArtifactPane 渲染管线。
- `artifactExport.ts` / `docxExport.ts`：
  - timeline-map 导出为可读事件序列，避免 raw JSON 泄露。
  - 不要求生成 SVG 或图片。
- prompt/template：
  - 清理 TIMELINE stage prompt 中要求 Mermaid timeline 和 Mermaid 冒号规避的旧提示。
  - 保持模型只输出 `artifact_data` 的约束。

### Error Handling

- 后端 renderer 输出的 timeline-map 必须通过 artifact contract；缺 events、重复 event id、缺 factIds 或未知 structured visual type 都应显式失败。
- 前端 parser 失败时继续显示结构化可视化格式错误，并进入现有 visual diagnostics。
- 不提供自动 repair 或 fallback Mermaid；失败不能被旧 Mermaid、草稿或 raw JSON 掩盖。

### Testing

后端测试：

- TIMELINE renderer fixture：最终 artifact 包含 `ai4se-visual timeline-map`，不包含 Mermaid timeline fence。
- artifact contract：缺 timeline-map 时失败，timeline-map 结构错误时失败。
- runtime raw JSON streaming：before-final delta 和 final output 均通过新 visual contract。
- workflow contract sync：manifest visualContract 与后端 required maps 同步；runtime instruction 不再声明 Mermaid timeline。

前端测试：

- `structuredVisuals.test.ts`：timeline-map 正向解析、缺 events、重复 id、缺 factIds 等负例。
- `StructuredVisual.test.tsx`：timeline-map 可访问渲染，不显示 raw JSON。
- `artifactExport.test.ts` / `docxExport.test.ts`：导出包含时间、事件、事实 ID。
- `workflows.test.ts` / prompt tests：TIMELINE stage required visual 改为 timeline-map，prompt 不再要求 Mermaid timeline。

回归命令：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_agent_contracts.py tools/new-agents/backend/tests/test_workflow_contract_sync.py -q -k "incident_timeline or visual_contract or timeline_map"
cd tools/new-agents/frontend && npm run test -- src/core/__tests__/structuredVisuals.test.ts src/components/__tests__/StructuredVisual.test.tsx src/core/__tests__/artifactExport.test.ts src/core/__tests__/docxExport.test.ts src/core/config/__tests__/workflows.test.ts src/core/prompts/__tests__/buildSystemPrompt.test.ts --run
./scripts/test/test-local.sh new-agents
```

## Non-Goals

- 不把所有 Mermaid 类型一次性迁移。
- 不新增 `mmdc` 或 backend Node/Chromium runtime。
- 不修改 Mermaid repair endpoint。
- 不改变 typed SSE schema。
- 不新增 Lisa/Alex 专属 runtime、store、API path 或 ArtifactPane 分支。
- 不让模型直接输出 `ai4se-visual` JSON。

## Spec Self-Review

- Placeholder scan：无 TBD/TODO/占位。
- Internal consistency：方案选择、数据结构、后端/前端职责与视觉协议一致。
- Scope check：范围集中在一个 workflow stage 和一个 visual type，可形成单个 implementation plan。
- Ambiguity check：`timeline-map` schema、失败路径、非目标和验收命令已明确。
