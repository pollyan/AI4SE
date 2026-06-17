from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class StagePayload:
    chat: str
    markdown: str
    next_stage_id: str | None = None
    clarification_chat: str | None = None
    turns_before_transition: int = 2


STAGE_PAYLOADS: dict[tuple[str, str], StagePayload] = {
    ("TEST_DESIGN", "CLARIFY"): StagePayload(
        chat="需求澄清完成，请确认进入策略制定。",
        next_stage_id="STRATEGY",
        markdown="""# 需求分析文档

## 1. 被测系统与边界
登录与支付联动能力是本次被测系统，覆盖账号密码登录、短信验证码登录、支付提交、失败重试和账号锁定。

## 2. 系统交互与核心链路
用户从登录页进入，完成身份校验后进入支付页，支付结果回写订单中心。

## 3. 待澄清与阻断性问题
| 问题 | 状态 |
| --- | --- |
| 账号锁定阈值是否为 5 次失败 | 已确认 |

## 4. 隐式需求与非功能性考量
需要覆盖并发登录、敏感信息脱敏、安全审计和移动端兼容性。
""",
    ),
    ("TEST_DESIGN", "STRATEGY"): StagePayload(
        chat="测试策略蓝图完成，请确认进入用例编写。",
        next_stage_id="CASES",
        markdown="""# 测试策略蓝图

## 1. 质量目标
- P0 主链路上线前全部通过。
- 高风险安全场景必须有自动化或专项验证。

## 2. 风险分析

### 2.1 风险矩阵
| 风险 | 优先级 |
| --- | --- |
| 登录绕过 | P0 |

### 2.2 风险明细
| ID | 风险名称 | 缓解策略 |
| --- | --- | --- |
| R-001 | 账号锁定失效 | 覆盖连续失败和解锁流程 |

## 3. 测试技术选型
| ID | 技术 | 理由 |
| --- | --- | --- |
| TS-001 | API + E2E | 同时覆盖契约和主链路 |

## 4. 测试分层策略

### 4.1 测试金字塔
单元 50%，集成 30%，E2E 20%。

### 4.2 分层明细
| 层级 | 范围 |
| --- | --- |
| E2E | 登录到支付成功 |

## 5. 测试点拓扑
| ID | 测试点 | 优先级 |
| --- | --- | --- |
| TP-001 | 登录成功后支付 | P0 |
""",
    ),
    ("TEST_DESIGN", "CASES"): StagePayload(
        chat="测试用例集完成，请确认进入文档交付。",
        next_stage_id="DELIVERY",
        markdown="""# 测试用例集

## 1. 用例统计
共 6 条用例，P0 4 条，P1 2 条。

## 2. 用例清单
| ID | 用例标题 | 优先级 | 操作步骤 | 预期结果 |
| --- | --- | --- | --- | --- |
| TC-001 | 密码登录成功后支付 | P0 | 输入正确账号密码并提交支付 | 支付成功并生成订单 |
| TC-002 | 连续失败触发锁定 | P0 | 连续输入错误密码 | 账号被锁定并记录审计 |

## 3. 测试点覆盖追溯
| 测试点 | 覆盖用例 | 覆盖状态 |
| --- | --- | --- |
| 登录成功后支付 | TC-001 | 已覆盖 |
""",
    ),
    ("TEST_DESIGN", "DELIVERY"): StagePayload(
        chat="测试设计交付文档已完成。",
        markdown="""# 测试设计文档

## 文档信息
项目名称：登录支付链路测试设计。

## 第一部分：需求分析
覆盖登录、支付、失败重试、账号锁定和安全审计。

## 第二部分：测试策略
以 P0 主链路和高风险安全场景为优先级核心。

## 第三部分：测试用例
包含正向、异常、安全和兼容性用例。

## 附录：验收标准
- 所有 P0 用例通过。
- 高风险项均有对应缓解策略。
""",
    ),
    ("VALUE_DISCOVERY", "ELEVATOR"): StagePayload(
        chat="价值定位分析完成，请确认进入用户画像。",
        next_stage_id="PERSONA",
        markdown="""# 价值定位分析

## 产品核心定位
面向测试团队的 AI 测试设计助手，帮助从需求快速生成测试策略和用例。

## 目标用户概览
| 维度 | 描述 |
| --- | --- |
| 主要用户群体 | 中大型软件团队的测试负责人 |

## 独特价值主张
| 维度 | 我们 | 现有方案/竞品 |
| --- | --- | --- |
| 核心优势 | 结构化引导并沉淀产物 | 依赖人工经验 |

## 商业可行性初判
| 维度 | 判断 |
| --- | --- |
| 用户付费意愿 | 对节省测试设计时间有明确预算 |

## 60 秒电梯演讲
我们帮助测试团队把模糊需求快速转化为可执行测试资产。
""",
    ),
    ("VALUE_DISCOVERY", "PERSONA"): StagePayload(
        chat="用户画像分析完成，请确认进入用户旅程。",
        next_stage_id="JOURNEY",
        markdown="""# 用户画像分析

## 主要用户画像

### 画像 1：测试负责人

#### 基础特征
管理 5 到 20 人测试团队，关注质量风险和交付效率。

#### 行为特征
经常参与需求评审、测试计划制定和上线风险评估。

#### 需求动机
希望减少重复文档工作，同时提高风险识别完整度。

#### 核心痛点
| 痛点 | 频率 | 影响程度 | 现有方案不足 |
| --- | --- | --- | --- |
| 用例设计耗时 | 每周 | 高 | 人工依赖强 |

## 用户优先级排序
| 优先级 | 用户类型 | 理由 |
| --- | --- | --- |
| 核心用户 | 测试负责人 | 直接承担质量交付责任 |
""",
    ),
    ("VALUE_DISCOVERY", "JOURNEY"): StagePayload(
        chat="用户旅程分析完成，请确认进入需求蓝图。",
        next_stage_id="BLUEPRINT",
        markdown="""# 用户旅程分析

## 用户旅程地图
从需求输入到策略制定、用例编写、评审交付。

## 关键阶段详细分析
| 阶段 | 用户目标 | 主要痛点 |
| --- | --- | --- |
| 需求评审 | 找出风险 | 信息不完整 |

## 痛点优先级排序

### 高优先级痛点（必须解决）
测试设计耗时且遗漏风险。

### 中等优先级痛点（应该解决）
用例格式和覆盖追溯不统一。

### 低优先级痛点（可以解决）
导出格式需要适配团队模板。

## 核心机会点

### 主要机会点
用结构化智能体引导测试设计。

### 产品切入策略
优先切入需求评审后的测试策略和用例生成环节。
""",
    ),
    ("VALUE_DISCOVERY", "BLUEPRINT"): StagePayload(
        chat="需求蓝图已完成。",
        markdown="""# AI 测试设计助手需求蓝图

## 文档信息
| 维度 | 内容 |
| --- | --- |
| 产品方向 | AI 辅助测试设计 |

## 1. 产品概述

### 1.1 产品愿景
让测试团队更快识别风险并沉淀高质量测试资产。

### 1.2 定位声明
For 测试负责人 who 需要快速完成测试设计，the AI 测试设计助手 is a 结构化智能体工具 that 生成策略和用例。

### 1.3 核心价值
| 维度 | 描述 |
| --- | --- |
| 用户价值 | 节省测试设计时间 |

## 2. 目标用户（摘要）
测试负责人和资深测试工程师。

## 3. 核心需求

### 功能架构
需求输入、风险分析、策略生成、用例生成、交付导出。

### P0 需求（核心功能，必须实现）
| ID | 需求名称 | 验收标准 |
| --- | --- | --- |
| F-001 | 生成测试策略 | 包含风险和分层策略 |

### P1 需求（重要功能，应该实现）
团队模板适配。

### P2 需求（增值功能，可以实现）
历史项目复用。

## 4. 核心流程

### 主流程图
用户输入需求后，系统生成多阶段测试设计产物。

## 5. 成功指标
| 指标类型 | 指标名称 | 目标值 |
| --- | --- | --- |
| 产品指标 | 测试设计耗时降低 | 30% |

## 6. MVP 范围与计划

### MVP 包含功能
- F-001: 生成测试策略

### 迭代路线
| 版本 | 核心功能 |
| --- | --- |
| v1.0 | 策略和用例生成 |

## 7. 风险评估
| 风险类型 | 风险描述 | 缓解措施 |
| --- | --- | --- |
| 产品风险 | 输出不稳定 | 契约校验和人工确认 |
""",
    ),
}


def build_agent_sse_response(
    request_body: dict[str, Any],
    *,
    turn_index: int = 0,
) -> str:
    workflow_id = request_body["workflowId"]
    stage_id = request_body["stageId"]
    payload = STAGE_PAYLOADS[(workflow_id, stage_id)]
    should_request_next_stage = (
        payload.next_stage_id is not None
        and turn_index >= payload.turns_before_transition
    )
    output: dict[str, Any] = {
        "chat": (
            payload.chat
            if should_request_next_stage or not payload.next_stage_id
            else payload.clarification_chat
            or "当前阶段产出物已更新。我还需要你补充确认关键信息后，才会建议进入下一阶段。"
        ),
        "artifact_update": {
            "type": "replace",
            "markdown": payload.markdown,
        },
        "stage_action": None,
        "warnings": [],
    }
    if should_request_next_stage:
        output["stage_action"] = {
            "type": "request_next_stage",
            "target_stage_id": payload.next_stage_id,
        }
    event = {"type": "agent_turn", "output": output}
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\ndata: [DONE]\n\n"
