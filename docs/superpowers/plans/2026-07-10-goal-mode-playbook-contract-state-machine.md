# 目标模式 Playbook 契约状态机实施计划

> **供 Agent 执行：** 必须使用 `superpowers:subagent-driven-development`（推荐）或 `superpowers:executing-plans`，按任务实施本计划。步骤使用复选框（`- [ ]`）跟踪。

> **实施状态（2026-07-10）：** Playbook 重写、规则迁移审查、12 个行为探针、独立复审和附录退役均已完成。下列已完成步骤按实际证据标记；“恢复测试质量扫描提示词设计”留待用户查看本次效果后继续。

**目标：** 将三份重叠的目标模式策略文档替换为一份保持行为效果、基于契约状态机的 Playbook，使规则更易执行、恢复和维护。

**架构：** 围绕显式执行状态、必需产物、转换门禁和失败路由重写 `goal-mode-playbook.md`。当前实现事实继续由 `AGENTS.md`、`docs/TESTING.md`、package scripts 和 CI 承载；退役两份附录前，使用规则迁移清单和行为探针验证新 Playbook。

**技术栈：** Markdown、Mermaid、Git、基于 shell 的静态文档检查、只读多 Agent 审查。

## 全局约束

- 保留 `AGENTS.md`、`docs/todos/refactor/README.md` 和 `docs/todos/2026-07-10-new-agents-architecture-refactor.md` 中所有用户已有脏改动。
- 不修改业务代码、测试、CI workflow、test runner、package script 或归档 / 历史执行记录。
- 不以行数、文件数或字符数作为完成标准。
- 保持 `docs/strategy/goal-mode-playbook.md` 为唯一面向未来的目标模式入口。
- 规则覆盖和行为审查通过前，不得删除任一附录。
- 所有文件修改使用 `apply_patch`，且只 stage 当前任务拥有的路径。
- 将 `PASS`、`FAIL`、`NOT_RUN`、`BLOCKED`、`TIMEOUT` 和 `FLAKY` 视为不同验证状态；重试不得抹除首次失败证据。
- 早期执行曾读取已退役附录的历史陈述保持不变，因为它们是证据而非未来指令。

---

### 任务 1：将主 Playbook 重写为可执行契约

**文件：**
- 修改：`docs/strategy/goal-mode-playbook.md`
- 读取：`docs/superpowers/specs/2026-07-10-goal-mode-playbook-contract-state-machine-design.md`
- 读取：`docs/strategy/goal-mode-cga-template.md`
- 读取：`docs/strategy/goal-mode-ci-verification.md`

**接口：**
- 输入：已批准的设计，以及原三份策略文档中的每条规范性规则。
- 输出：可独立执行的 `goal-mode-playbook.md`，显式包含 `BOOTSTRAP`、`ASSESS`、`MILESTONE`、`DESIGN`、`PLAN`、`IMPLEMENT`、`VERIFY`、`DELIVER`、`NEXT` 和 `WAIT`。

- [x] **步骤 1：记录重写前基线**

执行：

```bash
wc -l docs/strategy/goal-mode-playbook.md docs/strategy/goal-mode-cga-template.md docs/strategy/goal-mode-ci-verification.md
rg -n '^## |^### ' docs/strategy/goal-mode-playbook.md docs/strategy/goal-mode-cga-template.md docs/strategy/goal-mode-ci-verification.md
```

预期：三份文件合计约 700 行；标题列表能看出重复的 CGA、切片厚度、验证和交付章节。

- [x] **步骤 2：对旧 Playbook 运行红态静态契约检查**

执行：

```bash
rg -n 'BOOTSTRAP|ASSESS|MILESTONE|DESIGN|PLAN|IMPLEMENT|VERIFY|DELIVER|NEXT|WAIT|NOT_RUN|TIMEOUT|FLAKY' docs/strategy/goal-mode-playbook.md
```

预期：无法找到完整状态与结果契约；旧 Playbook 未定义全部必需状态标识和诚实验证状态。

- [x] **步骤 3：使用已批准的状态机结构替换主 Playbook**

使用 `apply_patch` 替换 `docs/strategy/goal-mode-playbook.md` 的完整内容。新文件必须包含以下章节和职责：

```markdown
# AI4SE 目标模式运行手册

## 1. 目标模式契约
- 规范语义：必须、默认、允许
- 唯一入口、事实源优先级、授权边界、暂停条件
- 长期 todo、CGA/承接、spec、plan、验证记录职责

## 2. 执行状态机
- Mermaid 状态流
- BOOTSTRAP / ASSESS / MILESTONE / DESIGN / PLAN
- IMPLEMENT / VERIFY / DELIVER / NEXT / WAIT
- 每个状态均定义：进入条件、必需产物、离开门禁、失败路由

## 3. 评估与厚切片契约
- 完整 CGA 与承接检查的互斥选择条件
- 两套紧凑必填 schema
- 强制改道条件
- 入口、动作、处理、可见结果、状态承接、失败反馈、证据七项门禁
- 工程信任闭环的严格适用条件

## 4. 协作、设计与实现
- 单工作区与 dirty diff 保护
- 主 Agent / 子智能体责任、写入边界、复核和两次失败降级
- brainstorming -> 中文 spec -> implementation plan -> TDD/文档验证

## 5. 验证、CI 与证据
- 聚焦 -> 必要跨层 -> 动态 CI 映射 -> 完成型全量验证
- PASS / FAIL / NOT_RUN / BLOCKED / TIMEOUT / FLAKY
- 首错保留、retry-to-green 禁止冒充稳定通过
- deterministic/mock/真实 UI/真实前后端/真实外部服务与模型证据分层
- CI 等价最小记录字段
- 远端 CI 首错、比较、分类、复现、防复发和重跑闭环

## 6. 记录与交付
- 稳定事实源和 todo 更新
- 精确 staging、聚焦 commit、默认及时 push 及例外
- 完成说明、HEAD/远端/未提交 diff、残余风险
- 进度按能力包计算

## 7. 最小启动提示词
- 只声明目标、授权和 Playbook 路径
```

不得复制旧填空模板、长示例目录、固定命令矩阵、当前 CI job 名、模型设置、覆盖率阈值或数字化 diff 大小阈值。

- [x] **步骤 4：运行绿态静态 schema 检查**

执行：

```bash
rg -n 'BOOTSTRAP|ASSESS|MILESTONE|DESIGN|PLAN|IMPLEMENT|VERIFY|DELIVER|NEXT|WAIT' docs/strategy/goal-mode-playbook.md
rg -n 'PASS|FAIL|NOT_RUN|BLOCKED|TIMEOUT|FLAKY' docs/strategy/goal-mode-playbook.md
rg -n '入口|动作|处理|可见结果|状态承接|失败反馈|证据' docs/strategy/goal-mode-playbook.md
rg -n '完整 CGA|目标承接检查|未选候选去向|工程信任闭环|首个真实错误|CI 等价' docs/strategy/goal-mode-playbook.md
```

预期：每条命令都能在单一文件中找到完整必需词汇。

- [x] **步骤 5：检查文档格式和 ownership**

执行：

```bash
git diff --check -- docs/strategy/goal-mode-playbook.md
git status --short
git diff -- docs/strategy/goal-mode-playbook.md
```

预期：无 whitespace 错误；本任务只修改 `goal-mode-playbook.md`；三处用户已有改动保持不变。

- [x] **步骤 6：在附录仍存在时提交可独立使用的新 Playbook**

执行：

```bash
git add docs/strategy/goal-mode-playbook.md
git diff --cached --name-only
git commit -m "docs(goal-mode): 重构目标模式状态机"
```

预期：staged 列表仅包含 `docs/strategy/goal-mode-playbook.md`，且 commit 成功。

### 任务 2：证明规则覆盖与行为等价

**文件：**
- 若审查发现缺口则修改：`docs/strategy/goal-mode-playbook.md`
- 读取：`docs/strategy/goal-mode-cga-template.md`
- 读取：`docs/strategy/goal-mode-ci-verification.md`
- 读取：`docs/superpowers/specs/2026-07-10-goal-mode-playbook-contract-state-machine-design.md`

**接口：**
- 输入：新 Playbook 和仍保留的附录。
- 输出：不存在未映射 P0/P1 规则、所有行为探针通过的已审查 Playbook。

- [x] **步骤 1：审查期间建立临时规则迁移清单**

对三份旧文档中的每条规范性规则，在 reviewer notes 中记录以下处置之一：

```text
KEEP:§2.1
MERGE:§3.2
SOURCE:docs/TESTING.md
DROP:与规则 R-017 完全重复
```

预期：没有未分类规则；任何 `DROP` 决定都未删除转换门禁、必需产物、失败路由、证据边界或交付条件。该清单仅作为审查证据，不新增为仓库永久文件。

- [x] **步骤 2：派发独立只读 reviewer**

Reviewer A 检查规则丢失、需求矛盾、不可达状态和可绕过的转换门禁。Reviewer B 检查 CGA / 承接选择、厚切片行为、CI 映射、诚实验证状态、证据分层和远端 CI 恢复。两位 reviewer 均不得编辑文件。

预期：每位 reviewer 都返回带严重级别、来源规则、新章节位置和建议修正的 findings。P0/P1 finding 阻止附录删除。

- [x] **步骤 3：运行已批准设计中的 12 个行为探针**

用以下输入审查 Playbook，并要求产生指定决策：

```text
1. 用户未指定目标 -> 完整 CGA，至少比较两个能力包候选；确实只有一个时说明原因。
2. 已确认下一切片且事实未变 -> 目标承接检查。
3. 已确认下一切片但出现阻断失败 / 用户纠错 -> 改道，不继续承接。
4. 单字段 / parser / 按钮 / 测试请求 -> 扩大边界、证明工程信任例外，或暂缓。
5. 工作区存在无关 dirty 改动 -> 保护并隔离 ownership。
6. 共享 API / SSE / 持久化变更 -> 跨层验证加动态 CI 映射。
7. 全量脚本通过但 CI 风险未映射 -> 不宣称 CI 等价。
8. skip / 零收集 / timeout / 缺依赖 -> 不记为 `PASS`。
9. mock 浏览器 E2E 通过 -> 不宣称真实后端或真实模型质量通过。
10. 远端 CI 失败 -> 比较本地证据、复现、防复发、重跑。
11. 子智能体失败或越界修改 -> 主 Agent 复核，缩小范围重试一次，再降级。
12. 切片未完成验证 -> 不交付，也不转换到 `NEXT`。
```

预期：12 个结果都由 Playbook 直接要求，不依赖任一附录。

- [x] **步骤 4：修复每个 P0/P1 审查缺口**

使用 `apply_patch` 更新 `goal-mode-playbook.md`。不得新增永久文件。重复步骤 1–3，直到 reviewer 不再发现 P0/P1 执行退化。

- [x] **步骤 5：验证修复；仅当审查改变 Playbook 时提交**

执行：

```bash
git diff --check -- docs/strategy/goal-mode-playbook.md
git diff -- docs/strategy/goal-mode-playbook.md
```

如果存在改动：

```bash
git add docs/strategy/goal-mode-playbook.md
git diff --cached --name-only
git commit -m "docs(goal-mode): 补齐状态机执行门禁"
```

预期：没有格式错误；若形成 commit，只包含 Playbook。

### 任务 3：安全退役两份附录

**文件：**
- 删除：`docs/strategy/goal-mode-cga-template.md`
- 删除：`docs/strategy/goal-mode-ci-verification.md`
- 仅当存在面向未来的引用时修改：包含该引用的确切活跃文件

**接口：**
- 输入：已经审查且所有行为探针通过的 Playbook。
- 输出：单一、面向未来且不再实时依赖任一附录的目标模式规则源。

- [x] **步骤 1：删除前证明不存在面向未来的引用**

执行：

```bash
rg -n 'goal-mode-cga-template\.md|goal-mode-ci-verification\.md' docs/strategy AGENTS.md docs/index.md docs/todos/refactor/README.md docs/plans/2026-06-25-new-agents-agent-framework-phase1-phase2.md docs/todos/2026-07-10-new-agents-architecture-refactor.md
rg -n 'goal-mode-cga-template\.md|goal-mode-ci-verification\.md' --glob '!.git/**' --glob '!.superpowers/**' .
```

预期：第一条命令在两份附录之外没有匹配；全仓扫描的每个额外匹配都被分类为活跃引用、迁移记录或历史快照。如果仍有活跃引用，使用 `apply_patch` 将其替换为 `docs/strategy/goal-mode-playbook.md`；不得仅为消除历史命中而编辑本次迁移设计 / 计划或带日期的执行快照。

- [x] **步骤 2：使用 `apply_patch` 删除附录**

仅在任务 2 没有阻断 finding 后删除两份文件。

- [x] **步骤 3：验证删除和历史引用处理**

执行：

```bash
test ! -e docs/strategy/goal-mode-cga-template.md
test ! -e docs/strategy/goal-mode-ci-verification.md
rg -n 'goal-mode-cga-template\.md|goal-mode-ci-verification\.md' docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md docs/todos/archive || true
```

预期：两份文件均不存在。剩余匹配如有，只能是带日期的历史事实，并刻意保持不变。

- [x] **步骤 4：运行本任务最终静态文档检查**

执行：

```bash
git diff --check -- docs/strategy/goal-mode-cga-template.md docs/strategy/goal-mode-ci-verification.md
git status --short
git diff --stat
```

预期：没有 whitespace 错误；任务 diff 包含两份删除，以及有明确理由的未来引用修正；用户 dirty 文件未被本任务修改。

- [x] **步骤 5：提交附录退役**

执行：

```bash
git add docs/strategy/goal-mode-cga-template.md docs/strategy/goal-mode-ci-verification.md
git diff --cached --name-only
git commit -m "docs(goal-mode): 退役目标模式重复附录"
```

预期：只提交两份已删除附录和必要的未来引用迁移。

### 任务 4：最终验收与交接

**文件：**
- 验证：`docs/strategy/goal-mode-playbook.md`
- 验证：`docs/superpowers/specs/2026-07-10-goal-mode-playbook-contract-state-machine-design.md`
- 验证：`docs/superpowers/plans/2026-07-10-goal-mode-playbook-contract-state-machine.md`

**接口：**
- 输入：已提交的 Playbook 重写和附录退役。
- 输出：有证据支撑的完成报告，以及回到测试质量扫描提示词设计的清晰交接。

- [x] **步骤 1：运行完整静态验收套件**

执行：

```bash
rg -n 'BOOTSTRAP|ASSESS|MILESTONE|DESIGN|PLAN|IMPLEMENT|VERIFY|DELIVER|NEXT|WAIT' docs/strategy/goal-mode-playbook.md
rg -n 'PASS|FAIL|NOT_RUN|BLOCKED|TIMEOUT|FLAKY' docs/strategy/goal-mode-playbook.md
rg -n '完整 CGA|目标承接检查|未选候选去向|入口|状态承接|失败反馈|工程信任闭环|首个真实错误|CI 等价' docs/strategy/goal-mode-playbook.md
git diff --check a8390a56..HEAD
```

预期：所有强制契约均存在，完整重构提交范围没有 whitespace 错误。

- [x] **步骤 2：确认未来引用和工作区 ownership**

执行：

```bash
rg -n 'goal-mode-cga-template\.md|goal-mode-ci-verification\.md' docs/strategy AGENTS.md docs/index.md docs/todos/refactor/README.md docs/plans/2026-06-25-new-agents-agent-framework-phase1-phase2.md docs/todos/2026-07-10-new-agents-architecture-refactor.md
rg -n 'goal-mode-cga-template\.md|goal-mode-ci-verification\.md' --glob '!.git/**' --glob '!.superpowers/**' .
git status -sb
git log --oneline a8390a56..HEAD
```

预期：没有面向未来的旧附录引用；全仓匹配均被分类为迁移记录或带日期 / 已归档历史事实；用户 dirty 文件仍存在且未 stage；显式范围日志展示包括设计提交在内的所有聚焦重构 commit。

- [x] **步骤 3：诚实记录验证范围**

完成报告必须说明：这是文档治理变更，通过规则迁移、静态检查、行为探针和独立审查验证；不得声称运行过应用测试、真实浏览器测试、外部服务或 LLM 质量门。

- [ ] **步骤 4：恢复原始任务**

完成测试策略与质量保障扫描提示词时，仅以新 Playbook 作为治理规则源。扫描证据写入扫描报告；目标态与厚切片写入活跃 todo；未来实施细节写入各切片 spec / plan。
