import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ["FLASK_TESTING"] = "1"

from app import create_app
from models import db
from run_persistence import create_agent_run, get_run_snapshot, record_artifact_version
from workflow_handoffs import export_run_handoffs, start_workflow_handoff


BLUEPRINT_MARKDOWN = """# AI 测试资产管理平台需求蓝图

## 文档信息
| 维度 | 内容 |
| --- | --- |
| Artifact 名称 | 可评审需求蓝图 |
| 蓝图状态 | 可交接 Lisa |

## 1. 产品概述
AI 测试资产管理平台。

### 1.1 产品愿景
帮助团队沉淀测试资产。

### 1.2 定位声明
面向测试负责人，解决测试资产分散问题。

### 1.3 核心价值
| 维度 | 描述 |
| --- | --- |
| 用户价值 | 提升测试资产复用效率 |

## 2. 目标用户（摘要）
| 用户类型 | 核心痛点 | 优先级 |
| --- | --- | --- |
| 测试负责人 | 测试资产分散 | 核心用户 |

## 3. 核心需求
### 功能架构
```mermaid
mindmap
    root(("AI 测试资产管理平台"))
        ("测试资产")
            ["策略"]
            ["用例"]
```

### P0 需求（核心功能，必须实现）
| ID | 需求名称 | 用户故事 | 对应痛点 | 范围边界 | 依赖 | 验收标准 | 可测试性等级 | owner | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| F-001 | 自动生成测试策略和用例 | 作为测试负责人，我想生成测试资产，以便提升复用效率 | 测试资产分散 | 支持策略和用例生成 | LLM 配置 | 能生成可评审策略和用例 | 高 | 产品 | 已确认 |

### P1 需求（重要功能，应该实现）
| ID | 需求名称 | 用户故事 | 对应痛点 | 范围边界 | 依赖 | 验收标准 | 可测试性等级 | owner | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

### P2 需求（增值功能，可以实现）
| ID | 需求名称 | 用户故事 | 对应痛点 | 范围边界 | 依赖 | 验收标准 | 可测试性等级 | owner | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

## 4. 核心流程
### 主流程图
```mermaid
flowchart TD
    A["输入需求"] --> B["生成策略"]
    B --> C["生成用例"]
```

## 5. 成功指标
| 指标类型 | 指标名称 | 目标值 | 衡量方式 |
| --- | --- | --- | --- |
| 产品指标 | 资产生成完成率 | 90% | 运行记录 |

## 6. MVP 范围与计划
### MVP 包含功能
- [x] F-001: 自动生成测试策略和用例

### 迭代路线
| 版本 | 时间 | 核心功能 | 目标 |
| --- | --- | --- | --- |
| v1.0 MVP | 4 周 | 核心资产生成 | 验证主价值 |

## 7. 非功能需求
| 类型 | 需求描述 | 指标/约束 | 验证方式 | owner | 状态 |
| --- | --- | --- | --- | --- | --- |
| 性能 | 生成响应可接受 | 60 秒内返回 | 冒烟测试 | 研发 | 已确认 |

## 8. 验收标准
| 验收 ID | 关联需求 | 验收标准 | 验证方式 | 可测试性等级 | owner | 状态 |
| --- | --- | --- | --- | --- | --- | --- |
| AC-001 | F-001 | 可生成策略和用例 artifact | 自动化测试 | 高 | 测试 | 已确认 |

## 9. 路线图
```ai4se-visual
{"type":"roadmap","columns":["版本","时间","核心功能","目标","成功指标"],"rows":[{"版本":"v1.0 MVP","时间":"4 周","核心功能":"核心资产生成","目标":"验证主价值","成功指标":"资产生成完成率"}]}
```

## 10. 风险评估
| 风险类型 | 风险描述 | 可能性 | 影响 | 缓解措施 | owner | 状态 |
| --- | --- | --- | --- | --- | --- | --- |
| 产品风险 | 输出质量不稳定 | 中 | 高 | 增加评审门禁 | 产品 | 已确认 |

## 11. Lisa Handoff 输入
| 输入类型 | ID | 内容 | 来源 | 给 Lisa 的用途 | 状态 |
| --- | --- | --- | --- | --- | --- |
| 需求 | F-001 | 自动生成测试策略和用例 | P0 需求 | 需求评审 / 测试设计 | 已确认 |
| 验收标准 | AC-001 | 可生成策略和用例 artifact | 验收标准 | 测试断言 | 已确认 |

## 12. 阶段门禁
- [x] P0 需求均具备验收标准、owner 和可测试性等级。
"""

STORY_BREAKDOWN_MARKDOWN = """# 用户故事拆解包

## 输入分析
| 字段 | 内容 |
| --- | --- |
| 来源类型 | PRD |
| 产品目标 | 把测试资产生成能力拆成可交付迭代 |

## Epic Map
| Epic ID | 名称 | 用户价值 | 优先级 |
| --- | --- | --- | --- |
| EPIC-001 | 测试资产生成 | 减少从需求到测试设计的手工整理成本 | P0 |

## User Story Backlog
| Story ID | Epic ID | 标题 | User Story | 优先级 | Sprint | 可测试性 |
| --- | --- | --- | --- | --- | --- | --- |
| US-001 | EPIC-001 | 需求澄清基线 | 作为测试负责人，我想把需求输入转成澄清清单，以便在开发前发现遗漏。 | P0 | Sprint 1 | 高 |
| US-002 | EPIC-001 | 测试策略生成 | 作为测试负责人，我想自动获得风险、测试点和测试层级建议，以便快速组织评审。 | P0 | Sprint 1 | 高 |

## 验收标准
| AC ID | Story ID | 验收标准 | 验证方式 | 状态 |
| --- | --- | --- | --- | --- |
| AC-001 | US-001 | 输入需求后生成事实、边界、业务规则和待澄清问题。 | 后端 contract test + UI smoke | 待验证 |

## 依赖与风险
| 类型 | ID | 关联 Story | 内容 | 缓解措施 |
| --- | --- | --- | --- | --- |
| 依赖 | DEP-001 | US-001 -> US-002 | 模型输出必须使用 artifact_data 结构化数据。 | runtime instruction 和 renderer contract 双门禁 |
| 风险 | RISK-001 | US-001, US-002 | 故事拆解缺少可测试验收标准。 | 所有 P0 故事必须绑定验收标准和 Sprint 切片 |

## Sprint 切片建议
| Sprint | 目标 | Story IDs | 交付物 |
| --- | --- | --- | --- |
| Sprint 1 | 打通需求澄清到策略的最小闭环 | US-001, US-002 | 可评审 artifact_data 输出和右侧 Markdown artifact |

## Lisa Handoff 输入
| 输入 ID | 目标 workflow | Story IDs | 内容 | 用途 |
| --- | --- | --- | --- | --- |
| HI-001 | TEST_DESIGN | US-001 | 需求澄清基线及其验收标准 | Lisa 测试设计输入 |
| HI-002 | REQ_REVIEW | US-001, US-002 | 故事、验收标准、依赖和风险一致性评审 | Lisa 需求评审输入 |

## 阶段门禁
- [x] 所有 P0 用户故事均具备验收标准和 Sprint 切片。
"""


@pytest.fixture
def app():
    db_fd, db_path = tempfile.mkstemp()
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        }
    )
    with app.app_context():
        db.create_all()
        yield app
    os.close(db_fd)
    os.unlink(db_path)


def test_export_run_handoffs_returns_configured_lisa_targets(app):
    with app.app_context():
        run = create_agent_run("VALUE_DISCOVERY", "alex", "BLUEPRINT")
        record_artifact_version(run.id, "BLUEPRINT", BLUEPRINT_MARKDOWN)

        result = export_run_handoffs(run.id)

    assert result["runId"] == run.id
    assert result["sourceWorkflowId"] == "VALUE_DISCOVERY"
    assert [
        (handoff["targetWorkflowId"], handoff["targetStageId"], handoff["targetAgentId"])
        for handoff in result["handoffs"]
    ] == [
        ("TEST_DESIGN", "CLARIFY", "lisa"),
        ("REQ_REVIEW", "REVIEW", "lisa"),
    ]
    first = result["handoffs"][0]
    assert first["sourceStageId"] == "BLUEPRINT"
    assert first["sourceArtifactVersion"] == 1
    assert "VALUE_DISCOVERY/BLUEPRINT" in first["prompt"]
    assert "TEST_DESIGN/CLARIFY" in first["prompt"]
    assert "AI 测试资产管理平台" in first["prompt"]
    assert "Alex 产出的需求蓝图" not in first["prompt"]


def test_export_story_breakdown_handoffs_returns_lisa_targets(app):
    with app.app_context():
        run = create_agent_run("STORY_BREAKDOWN", "alex", "SPRINT_PLAN")
        record_artifact_version(run.id, "SPRINT_PLAN", STORY_BREAKDOWN_MARKDOWN)

        result = export_run_handoffs(run.id)

    assert result["runId"] == run.id
    assert result["sourceWorkflowId"] == "STORY_BREAKDOWN"
    assert [
        (handoff["targetWorkflowId"], handoff["targetStageId"], handoff["targetAgentId"])
        for handoff in result["handoffs"]
    ] == [
        ("TEST_DESIGN", "CLARIFY", "lisa"),
        ("REQ_REVIEW", "REVIEW", "lisa"),
    ]
    test_design = result["handoffs"][0]
    req_review = result["handoffs"][1]
    assert test_design["sourceStageId"] == "SPRINT_PLAN"
    assert test_design["sourceArtifactVersion"] == 1
    assert "STORY_BREAKDOWN/SPRINT_PLAN" in test_design["prompt"]
    assert "TEST_DESIGN/CLARIFY" in test_design["prompt"]
    assert "User Story Backlog" in test_design["prompt"]
    assert "AC-001" in test_design["prompt"]
    assert "DEP-001" in test_design["prompt"]
    assert "RISK-001" in test_design["prompt"]
    assert "REQ_REVIEW/REVIEW" in req_review["prompt"]


def test_export_run_handoffs_returns_empty_without_required_artifact(app):
    with app.app_context():
        run = create_agent_run("VALUE_DISCOVERY", "alex", "JOURNEY")

        result = export_run_handoffs(run.id)

    assert result["handoffs"] == []


def test_export_run_handoffs_returns_empty_for_non_source_workflow(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")

        result = export_run_handoffs(run.id)

    assert result["handoffs"] == []


def test_start_workflow_handoff_creates_target_run_with_handoff_prompt(app):
    with app.app_context():
        source_run = create_agent_run("VALUE_DISCOVERY", "alex", "BLUEPRINT")
        record_artifact_version(source_run.id, "BLUEPRINT", BLUEPRINT_MARKDOWN)
        source_run_id = source_run.id

        result = start_workflow_handoff(
            source_run.id,
            "value-discovery-blueprint-to-test-design",
        )
        target_snapshot = get_run_snapshot(result["targetRunId"])

    assert result["sourceRunId"] == source_run_id
    assert result["targetRunId"]
    assert result["targetWorkflowId"] == "TEST_DESIGN"
    assert result["targetStageId"] == "CLARIFY"
    assert result["targetAgentId"] == "lisa"
    assert target_snapshot["run"]["workflowId"] == "TEST_DESIGN"
    assert target_snapshot["run"]["agentId"] == "lisa"
    assert target_snapshot["run"]["currentStageId"] == "CLARIFY"
    assert target_snapshot["messages"] == [
        {
            "role": "user",
            "content": result["prompt"],
            "sequenceIndex": 1,
        }
    ]


def test_start_workflow_handoff_rejects_unknown_candidate(app):
    with app.app_context():
        source_run = create_agent_run("VALUE_DISCOVERY", "alex", "BLUEPRINT")
        record_artifact_version(source_run.id, "BLUEPRINT", BLUEPRINT_MARKDOWN)

        with pytest.raises(ValueError, match="未知 handoff"):
            start_workflow_handoff(source_run.id, "missing-handoff")
