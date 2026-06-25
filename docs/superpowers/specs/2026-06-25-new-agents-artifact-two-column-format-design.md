# New Agents 产出物二列说明表去表格化设计

## Current State Gap Analysis

### 事实源快照

- 已读取：剩余活跃 todo、`artifact_data_renderers.py`、renderer 测试、前端 LLM parser 测试中对表格输出的断言、目标模式事实源和 New Agents 架构原则。
- 当前工作区：intent-tester 生成文件为既有脏文件，本轮不触碰、不 stage。
- 本轮允许写入：`tools/new-agents/backend/artifact_data_renderers.py`、相关后端/前端测试、本 spec、配套 plan 和对应 todo 记录。

### 能力包聚合

| 能力包 | 聚合的原始缺口 | 用户动作链 / 工程信任闭环 | 为什么不能再拆薄 | 验收证据 |
| --- | --- | --- | --- | --- |
| 二列说明表去表格化 | `artifact-format-over-tabularization-audit.md`；截图中的 `策略摘要` 表格；`文档信息`、`报告信息`、`定位摘要` 等二列说明表 | 用户阅读右侧 Artifact -> 摘要/元信息/说明性内容以自然定义列表呈现 -> 风险/追溯/矩阵仍保持表格 | 只改 STRATEGY 会过薄；直接取消所有表格会破坏追溯矩阵。本轮抽取共享二列说明渲染规则，覆盖所有同类调用点 | renderer 测试、LLM parser 回归、diff check |
| 本轮 Diff 标识 | diff 标识 todo | 用户审阅新增/删除变化 | 独立 ArtifactPane 状态能力 | 后续 |

### 排序结论

本轮选择“二列说明表去表格化”。它覆盖截图主痛点，并且能通过共享 `_markdown_table` 的窄规则影响所有同类二列说明表，不新增 Lisa/Alex 专属分支。

### 切片厚度门禁

- 入口：后端 deterministic artifact renderer。
- 动作：Agent Runtime 将 `artifact_data` 渲染为右侧 Markdown Artifact。
- 处理：`字段/内容`、`维度/内容`、`格子/内容`、`属性/详情` 这类二列说明表转为 Markdown 定义列表；其他多列表格走原表格渲染。
- 可见结果：`策略摘要`、`文档信息` 等不再大面积表格化；FMEA、风险矩阵、追溯矩阵、用例表仍保留表格。
- 状态承接：不改变 artifact_data schema、SSE、store、导出入口或可视化契约。
- 失败反馈：不伪造数据；只改变 Markdown 呈现形态。
- 证据：代表性 renderer 输出测试和 LLM parser 回归。
- 结论：通过。

## Superpowers 自问自答

### Explore Project Context

`artifact_data_renderers.py` 中 `_markdown_table(...)` 是后端确定性 Markdown 表格的集中出口。大量业务表格使用多列结构，不能取消。但截图反馈中的 `策略摘要`、`文档信息`、`定位摘要` 等主要使用 `["字段", "内容"]` 或同义二列头，这类内容更适合定义列表。

前端 `ReactMarkdown` 和导出路径都能处理普通列表；因此本轮不需要改 ArtifactPane 渲染管线。由于后端 renderer 是结构化输出阶段的事实来源，优先在 renderer 层统一处理。

### Visual Companion Decision

本轮是 Markdown 输出形态收敛，不需要新增视觉 mockup；验证通过 Markdown 输出断言完成。

### Clarifying Questions

- 用户是谁：阅读右侧 New Agents Artifact 的用户。
- 用户要完成什么：快速扫读摘要和元信息，不被连续二列表格打断。
- 成功状态是什么：说明性二列表格转为自然列表；结构化追溯表格保留。
- 不做什么：不取消所有表格，不改 artifact_data schema，不让模型自由拼 Markdown。

### Approaches

1. 推荐：在 `_markdown_table` 中识别固定的二列说明表头并渲染为定义列表。优点是覆盖面广、改动集中、不会影响多列表格；缺点是同一表头下确实需要横向比较的极少数场景也会变成列表，但这些表头本身不适合横向比较。
2. 不选：逐个 renderer 手工改。它更精细，但容易漏掉同类场景，且变更面更大。
3. 不选：改前端 CSS 让表格看起来不像表格。它不改变 Markdown/DOCX/PDF 的实际语义，不能解决导出和阅读节奏问题。

### Presented Design

新增 `_definition_list(...)` helper，把二列说明 rows 渲染为：

```markdown
- **字段名**：字段内容
```

`_markdown_table(...)` 仅当 headers 精确等于 `["字段", "内容"]`、`["维度", "内容"]`、`["格子", "内容"]` 或 `["属性", "详情"]` 时调用该 helper。所有其他 headers 保持原表格输出。

测试覆盖三点：`策略摘要` 不再含 `| 字段 | 内容 |`；`附录：文档信息` 不再含二列表格；FMEA/风险表仍含 Markdown table。

## 验收条件

1. Given `TEST_DESIGN/STRATEGY` artifact_data，When 后端渲染策略摘要，Then `## 1. 策略摘要` 下不包含 `| 字段 | 内容 |`。
2. Given 任意文档信息 renderer，When 后端渲染附录，Then `文档信息` 不再输出 `字段/内容` 或 `维度/内容` 表格。
3. Given 风险、测试点、用例、覆盖矩阵等多列数据，When 后端渲染，Then 仍输出 Markdown 表格或 `ai4se-visual`。
4. Given 前端消费 artifact update，When Markdown 包含定义列表，Then parser 不需要新增分支且现有 artifact 写入测试通过。

## 非目标

- 不取消所有表格。
- 不降低结构化 artifact_data 契约严格性。
- 不绕过后端确定性渲染。
- 不实现完整视觉截图验收；浏览器权限当前受沙箱限制，后续可在有权限环境补跑。
