# QG-019 产出物元信息文末轻量化实施计划

> 当前唯一厚切片是 [`QG-019 / 产出物元信息退出首屏重表格`](../specs/2026-07-16-qg019-lightweight-artifact-metadata-design.md#厚切片身份基线)，顺序基线见[活跃 todo](../../todos/2026-07-16-new-agents-streaming-and-artifact-ux.md#待办总览)。下列均为内部实现步骤（非切片），不得单独验收、提交、推送或计算进度。

## 工作区与 ownership

- 基线：`master@cb2fb87e`；启动时仅 `tools/intent-tester/test-results/proxy/junit.xml` 为无关 runner 生成文件，始终禁止修改、回滚和暂存。
- 主 Agent 独占共享接线与所有 writer 权限：`artifact_render_plan.py`、renderer/schema、frontend 生产代码、prompt/template、spec/plan/todo、测试与交付。
- 设计期只读旁路审计：`qg019_metadata_audit` 负责 25-stage 字段分类；`qg019_frontend_audit` 负责 ArtifactPane/历史/导出/browser 影响。两者不得写文件。主 Agent 必须复核其证据和最终 diff。
- 正式审查在候选最终 diff 完成后，以整个 QG-019 为唯一单位分别执行 Spec 与 Standards 维度；不为内部步骤建立独立审查门禁。
- 不设置正式审查前高风险契约冻结检查点：本切片沿用已交付的 role seam，不改公共 API/schema/persistence；RED 与跨层 tracer 足以在最终审查前控制返工风险。

## 内部实现步骤 1（非切片）：先冻结共享顺序失败契约，并让 CLARIFY tracer 变绿

### RED

修改 `tools/new-agents/backend/tests/test_artifact_render_plan.py`，先写并运行失败测试：

1. `ArtifactRenderPlan` 拒绝未知 role、重复 section id 和没有 business section 的配置。
2. 即使 metadata 在配置 tuple 前部，partial 与 final 的 canonical `completed_section_ids` / Markdown 都必须是 business prefix + metadata suffix。
3. metadata-only partial 返回 `None`；业务字段一旦完整，首个右栏内容是业务 section，compact metadata 在尾部且不含表格。
4. CLARIFY 完整 fixture 保留 normalized `document_info`，但正文从“需求事实清单”开始，结尾是一行 compact “文档元信息”。

记录首次失败命令与断言，不以现有通过测试代替 RED。

### 最小 GREEN

- 在 `artifact_render_plan.py` 建立受校验的 canonical role order，partial/final 共用；错误配置显式失败。
- 在 `artifact_data_renderer_base.py` 建立共享 compact metadata helper，提供稳定行内转义且拒绝空键值。
- 将 CLARIFY metadata renderer 改为 helper，保持 schema、persistence 和 typed SSE 不变。
- 运行该 tracer 的 backend 聚焦测试，复核 diff 只落在计划路径。

## 内部实现步骤 2（非切片）：在同一 tracer 中拆分 TEST_DESIGN/DELIVERY 混合字段

### RED

先增加 DELIVERY 测试，证明当前“文档信息”表错误混合并前置：

- 项目名称、交付状态、总用例、高风险项必须出现在 `## 1. 交付概览` 业务 section。
- artifact/workflow/stage/status/version/generated_at 只能出现在文末 compact footer。
- partial 先显示执行摘要/交付概览，footer 永不成为首个业务增量；final exact convergence 保持。

### GREEN

- 把 `_render_delivery_document_info` 拆成 business overview 与 compact metadata 两个投影。
- 调整 DELIVERY plan dependencies 和 validation，使派生用例/风险计数仍由原共享验证器保护。
- 更新受影响 runtime/renderer 测试中的事实字符串；立即运行 DELIVERY backend runtime→SSE 聚焦回归。

## 内部实现步骤 3（非切片）：逐 workflow 扩展混合分类和纯 footer

每个 workflow 都按“先 RED → 最小 renderer/plan 改动 → 该 workflow GREEN → 主 Agent diff 复核”执行，不积累到最后统一调试：

1. `REQ_REVIEW/REVIEW`：需求名称、概述、结论倾向留在业务上下文；artifact 名称和评审时间进入 footer。
2. `REQ_REVIEW/REPORT`：需求名称、评审输入、参与方留在业务上下文；artifact 名称和评审时间进入 footer。
3. `INCIDENT_REVIEW/IMPROVEMENT`：故障、严重度、行动数、复查日期、关闭状态留在业务概览；版本、生成时间进入 footer。
4. `VALUE_DISCOVERY/BLUEPRINT`：产品方向留在业务概览；版本、日期、artifact 名称、蓝图状态进入 footer；产品名继续生成标题。
5. `PRD_REVIEW/*`：四个 stage 共用纯 compact `document_info` footer。
6. 为 TEST_DESIGN/STRATEGY/CASES、VALUE/ELEVATOR/PERSONA/JOURNEY、STORY_BREAKDOWN 四阶段补上共用 compact footer；删除 ELEVATOR/PERSONA 业务摘要中混入的 Artifact 名称；对 Incident 前两阶段和 Idea 四阶段明确断言不伪造 metadata，业务摘要未被误标。

完成后执行 25-stage 参数化测试：stage registry 与 manifest 完全一致；role 序列、首段业务、footer 非表格、partial/final exact、normalized data 保留全部成立。

## 内部实现步骤 4（非切片）：立即闭合真实 UI + mock backend 消费链

### RED

- 在 frontend integration/ArtifactPane 测试中加入长文 + compact footer：preview 的 DOM 顺序、code/edit 原文、历史预览/恢复内容与 Markdown 下载均保持业务在前、footer 在后。
- 在 `docxExport` 测试中检查生成文档 XML 同时包含业务 marker 和 metadata marker，且顺序一致。
- 新增或扩展 browser E2E，以 7 个 workflow 的真实 React workspace、mock typed SSE、窄 viewport 运行：首屏业务 marker 先于 footer；容器可滚动；滚动到底部后 footer 可发现；没有可见 footer 的代表 workflow 不出现大型文档信息表。不得使用截图或像素坐标断言。

### GREEN

- metadata helper 不输出 `---`，并保留既有 H1-H3 元信息标题，使 preview 独立分块、DOCX/PDF 不导出字面分隔符、历史 section lock anchor 不漂移。预期生产 frontend 无需修改；若 RED 暴露 generic Markdown/history/export 缺陷，只能修共享 `ArtifactPane` / export seam，禁止 workflow 专属分支。
- 先运行 7-workflow browser 新用例，再运行 ArtifactPane、history、export 与 stream 聚焦集。

## 内部实现步骤 5（非切片）：同步模板、契约与长期事实

- 把 CLARIFY、DELIVERY、REQ REVIEW/REPORT、INCIDENT IMPROVEMENT、VALUE BLUEPRINT、PRD 四阶段的 prompt/template 可见示例改为正文优先、文末 compact metadata；结构化 `document_info` 要求不删除。
- 更新对应 prompt contract 测试，机械保护 metadata 仅决定展示层级而非 schema 可选性。
- 更新 `docs/TESTING.md`、必要的 `tools/new-agents/CONTEXT.md` 或 API/架构事实；若 contract 未变化，不改 `docs/api-contracts.md` 并在交付说明记录原因。
- 不提前修改 QG-020 的执行模式；todo 只在审查和完成型验证全部通过后更新 QG-019 结果。

## 内部实现步骤 6（非切片）：厚切片级正式审查

准备唯一 QG-019 审查包：

- spec 与本 plan 链接；基线 `cb2fb87e` 到候选 diff；文件 ownership；Intent JUnit 排除事实。
- 共享 role/order 与 compact footer 契约；五类混合字段分类；25-stage 矩阵；历史/导出兼容边界。
- backend/frontend/browser 聚焦命令、首次 RED 与最终 GREEN；已知缺口与生成物处理。

分别派发：

- **Spec review**：逐条核验厚切片身份、用户验收、25-stage 分类、首屏/文末、结构化保留、7-workflow consumer 证据。
- **Standards review**：核验共享 runtime、无 workflow 分支/第二状态源/reverse parsing/silent fallback、类型与测试、dirty ownership。

Critical / Important 必须修复并复审关闭；Minor 必须修复或记录风险、owner 与去向。审查属于同一个 QG-019 门禁。

## 完成型验证

最终代码、模板和文档落定后，新鲜运行：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests -q
cd tools/new-agents/frontend && npm run test -- --run && npm run lint && npm run build
cd ../../..
.venv/bin/python -m pytest -o addopts='' tests/e2e/new_agents_browser -q
./scripts/test/test-local.sh new-agents
./scripts/test/test-local.sh
.venv/bin/python -m flake8 --select=E9,F63,F7,F82 \
  tools/new-agents tests/e2e/new_agents_browser
git diff --check
git status --short
```

浏览器和全仓 runner 如受沙箱本地端口/Mach port 权限阻断，保留首次 `BLOCKED` 证据后在具备权限的同一事实版本重跑；不得把环境阻断改写为 PASS。runner 生成的 Intent JUnit 始终 unstaged。

CI 等价映射：backend renderer/runtime/persistence 对应 backend 全量；React/history/export 对应 frontend test/lint/build；窄栏用户路径对应 browser 全量；共享仓库影响对应 `test-local.sh` 两级入口。真实模型/judge 属于 QG-020，不是本切片质量门。

## 实施结果

- RED 证据覆盖 canonical order、identity mismatch、manifest heading/version 漂移、跨 consumer 实体保真与 frontend 语义差异；修正后的聚焦集、backend/frontend 全量、browser 专项/全量及两级 runner 全部通过。
- 正式 Spec review 与 Standards review 最终均为 PASS；所有 Important/Minor 已修复，精确 heading tracer 额外通过两种近似标题 mutation 验证。
- 最终矩阵为 25/25 stage、19 visible compact footer、6 no-footer；7/7 workflow headless DOM 专项、preview/code/edit/history/lock/Markdown/DOCX/PDF 均有可定位测试。
- `tools/intent-tester/test-results/proxy/junit.xml` 仅由 runner 更新并保持 unstaged；QG-020 的 DeepSeek runner、凭证或 CI 调度未进入本切片。

## 精确交付

1. 全部门禁通过后，将活跃 todo 的 QG-019 改为 DONE，记录 25-stage 分类、19 个 visible-footer stage / 6 个无纯元信息 stage、7-workflow DOM 与完整 runner 证据；下一入口写为 QG-020 ASSESS。
2. 逐文件核对 diff，精确 stage QG-019 spec/plan、实现、测试、模板和事实文档；`tools/intent-tester/test-results/proxy/junit.xml` 必须保持 unstaged。
3. 运行 `git diff --cached --check`，核对 staged name/status/stat，形成唯一聚焦提交：

```bash
git commit -m "fix(new-agents): 轻量化产出物文档元信息"
```

4. 记录 commit SHA 并按 Playbook push。只有远端同步成功后才进入 QG-020；不得在本提交中提前加入 DeepSeek runner 或 CI 凭证逻辑。
