"""
Lisa 工作流产出物模板定义

包含各阶段产出物的详细结构、格式要求和可视化示例。
"""

from ..artifact_models import RequirementDoc, DesignDoc, CaseDoc
from ..utils.markdown_generator import create_empty_requirement_doc, convert_to_markdown
from typing import Optional


def get_artifact_json_schemas() -> dict:
    return {
        "requirement": RequirementDoc.model_json_schema(),
        "design": DesignDoc.model_json_schema(),
        "cases": CaseDoc.model_json_schema(),
    }


def generate_requirement_template() -> str:
    example_doc = create_empty_requirement_doc()
    return convert_to_markdown(example_doc.model_dump(), "requirement")


def format_schema_for_prompt(schema: dict) -> str:
    """
    将 Pydantic JSON Schema 格式化为 Prompt 友好的示例

    Args:
        schema: Pydantic model_json_schema() 的输出

    Returns:
        str: 格式化的 JSON 示例字符串
    """
    import json

    def resolve_ref(ref: str, root_schema: dict) -> dict:
        """解析 $ref 引用，从 $defs 中获取定义"""
        if ref.startswith("#/$defs/"):
            def_name = ref.split("/")[-1]
            return root_schema.get("$defs", {}).get(def_name, {})
        return {}

    def build_example_from_schema(schema_obj: dict, root_schema: dict = None, visited: set = None) -> any:
        """递归构建示例数据"""
        if root_schema is None:
            root_schema = schema_obj
        if visited is None:
            visited = set()

        schema_id = id(schema_obj)
        if schema_id in visited:
            return {}  # 避免循环引用
        
        visited.add(schema_id)

        # 处理 $ref 引用
        if "$ref" in schema_obj:
            ref_schema = resolve_ref(schema_obj["$ref"], root_schema)
            result = build_example_from_schema(ref_schema, root_schema, visited)
            visited.remove(schema_id)
            return result

        # 处理 anyOf（选择第一个非 null 的类型）
        if "anyOf" in schema_obj:
            for sub_schema in schema_obj["anyOf"]:
                if sub_schema.get("type") != "null":
                    result = build_example_from_schema(sub_schema, root_schema, visited)
                    visited.remove(schema_id)
                    return result
            visited.remove(schema_id)
            return None

        prop_type = schema_obj.get("type")
        description = schema_obj.get("description", "")

        # 处理 enum 类型（如 Literal）
        enum_values = schema_obj.get("enum", [])
        if enum_values:
            result = enum_values[0]
        elif prop_type == "string":
            result = description or "字符串值"
        elif prop_type == "integer":
            result = 1
        elif prop_type == "number":
            result = 1.0
        elif prop_type == "boolean":
            result = True
        elif prop_type == "array":
            items_schema = schema_obj.get("items", {})
            if items_schema.get("type") == "object" or "$ref" in items_schema:
                result = [build_example_from_schema(items_schema, root_schema, visited)]
            else:
                result = ["示例项"]
        elif prop_type == "object":
            properties = schema_obj.get("properties", {})
            example = {}
            for prop_name, prop_schema in properties.items():
                example[prop_name] = build_example_from_schema(prop_schema, root_schema, visited)
            result = example
        else:
            # 默认返回空对象
            result = {}
            
        visited.remove(schema_id)
        return result

    # 构建主示例
    properties = schema.get("properties", {})
    example = {}
    visited_set = set()
    for prop_name, prop_schema in properties.items():
        example[prop_name] = build_example_from_schema(prop_schema, schema, visited_set)

    return json.dumps(example, ensure_ascii=False, indent=2)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. 需求澄清阶段 (Clarify) - 需求分析文档
# ═══════════════════════════════════════════════════════════════════════════════

ARTIFACT_CLARIFY_REQUIREMENTS = """
# 需求分析文档

## 1. 需求全景图
> 使用 ```mermaid mindmap``` 绘制核心需求、功能要点和关键约束

## 2. 功能详细规格

| ID | 功能名称 | 描述 | 验收标准 | 优先级 |
|----|----------|------|----------|--------|
| F1 | [功能名] | [描述] | [验收标准列表] | P0/P1/P2 |

## 3. 业务流程图
> 使用 ```mermaid graph TD``` 绘制核心业务流程

## 4. 非功能需求 (NFR)
- **性能**: [QPS/响应时间等]
- **安全**: [加密/认证等]
- **兼容性**: [浏览器/设备等]

## 5. 待澄清问题
> 需求中模糊、矛盾或缺失的信息，需与用户确认。问题按优先级（P0/P1/P2）分组显示。

## 6. 已确认信息
> 根据用户澄清逐步填充

---
> 可根据实际情况添加其他章节：如数据模型、接口规范、状态机等

"""

ARTIFACT_REQ_REVIEW_RECORD = """
# 需求评审记录

## 1. 评审概况
- **需求名称**: [名称]
- **评审阶段**: 需求澄清
- **状态**: 进行中

## 2. 核心业务理解
> 基于对话记录当前对业务的理解
- **业务目标**: [待补充]
- **关键流程**: [待补充]

## 3. 待确认问题 (Issues)
| ID | 问题描述 | 状态 | 结论 |
|----|----------|------|------|
| Q1 | [问题]   | 待确认 | - |

## 4. 评审结论
> 暂无
"""


# ═══════════════════════════════════════════════════════════════════════════════
# 2. 策略制定阶段 (Strategy) - 测试策略蓝图
# ═══════════════════════════════════════════════════════════════════════════════

ARTIFACT_STRATEGY_BLUEPRINT = """
# 测试策略蓝图

## 1. 风险分析 (FMEA)

```mermaid
quadrantChart
    title 风险矩阵
    x-axis 低发生的可能性 --> 高发生的可能性
    y-axis 低影响程度 --> 高影响程度
    quadrant-1 重点监控
    quadrant-2 核心测试
    quadrant-3 快速验证
    quadrant-4 常规回归
    "风险点A": [0.8, 0.9]
    "风险点B": [0.3, 0.8]
    "风险点C": [0.4, 0.2]
```

| 风险项 | 潜在失效模式 | 影响分析 | 缓解策略 |
|--------|--------------|----------|----------|
| R1     | [模式]       | [影响]   | [策略]   |

## 2. 测试分层策略

```mermaid
block-beta
columns 1
  block:e2e
    E2E_Tests["端到端测试 (UI/API) - 10%"]
  end
  block:integration
    Integration_Tests["集成测试 (Service/DB) - 30%"]
  end
  block:unit
    Unit_Tests["单元测试 (Function/Class) - 60%"]
  end
  style E2E_Tests fill:#f9f,stroke:#333,stroke-width:2px
  style Integration_Tests fill:#bbf,stroke:#333,stroke-width:2px
  style Unit_Tests fill:#cfc,stroke:#333,stroke-width:2px
```

## 3. 测试类型与工具
- **功能测试**: [工具/方法]
- **性能测试**: [工具/指标]
- **安全测试**: [工具/扫描]

## 4. 资源与环境规划
- **测试环境**: [Dev / Staging / Prod]
- **数据准备**: [造数脚本 / 生产脱敏]
- **人力投入**: [估算]
"""


# ═══════════════════════════════════════════════════════════════════════════════
# 3. 用例编写阶段 (Cases) - 测试用例集
# ═══════════════════════════════════════════════════════════════════════════════

ARTIFACT_CASES_SET = """
# 测试用例集

## 1. 测试用例架构
```mermaid
graph LR
    Root[测试用例集] --> Func[功能测试]
    Root --> NonFunc[非功能测试]
    
    Func --> Normal[正常场景]
    Func --> Abnormal[异常场景]
    
    Normal --> C1[用例1]
    Abnormal --> C2[用例2]
```

## 2. 核心场景列表

| ID | 场景描述 | 前置条件 | 关键步骤 | 预期结果 | 类型 |
|----|----------|----------|----------|----------|------|
| TC01 | [场景] | [条件] | 1. [步1]<br>2. [步2] | [结果] | 冒烟 |
| TC02 | ... | ... | ... | ... | 回归 |

## 3. 详细用例设计

### TC-001: [用例标题]
- **优先级**: P0
- **测试技术**: [如：边界值]
- **测试数据**:
  ```json
  {
    "key": "value"
  }
  ```
- **执行步骤**:
  1. 步骤描述 1
  2. 步骤描述 2
- **断言点**:
  - [ ] 检查点 A
  - [ ] 检查点 B

### TC-002: ...

## 4. 边界值分析表
| 参数 | 类型 | 范围/规则 | 上点 | 内点 | 离点 | 预期 |
|------|------|-----------|------|------|------|------|
| [P1] | int  | [1, 100]  | 1, 100 | 50 | 0, 101 | ... |
"""


# ═══════════════════════════════════════════════════════════════════════════════
# 4. 文档交付阶段 (Delivery) - 最终交付文档
# ═══════════════════════════════════════════════════════════════════════════════

ARTIFACT_DELIVERY_FINAL = """
# 测试设计文档 (Final)

## 文档概览
- **项目名称**: [项目名称]
- **版本**: V1.0
- **生成时间**: [日期]

## 1. 核心产出物汇总

### 1.1 需求画像
> *引用自需求分析文档*
- **核心功能数**: [N]
- **关键约束**: [列表]

### 1.2 策略概览
> *引用自测试策略蓝图*
- **风险等级**: [高/中/低]
- **重点覆盖**: [区域]

### 1.3 用例统计
```mermaid
pie title 测试用例分布
    "P0 (核心)" : 20
    "P1 (重要)" : 50
    "P2 (一般)" : 30
```

## 2. 完整内容索引
> 以下引用各阶段详细产出...

### [附录 A] 需求分析详情
*(此处应包含完整需求文档内容)*

### [附录 B] 测试策略详情
*(此处应包含完整策略文档内容)*

### [附录 C] 测试用例详情
*(此处应包含完整用例集内容)*

## 3. 验收签字
- [ ] 产品经理确认
- [ ] 开发负责人确认
- [ ] 测试负责人确认
"""


# ═══════════════════════════════════════════════════════════════════════════════
# 5. 通用提示词 (General Prompts)
# ═══════════════════════════════════════════════════════════════════════════════


def build_artifact_update_prompt(
    artifact_key: str,
    current_stage: str,
    template_outline: str,
    existing_artifact: Optional[dict] = None,
    reasoning_hint: Optional[str] = None,
) -> str:
    """
    构建产出物更新 Prompt（动态注入 Schema）

    Args:
        artifact_key: 产出物唯一标识
        current_stage: 当前阶段名称
        template_outline: 模板大纲
        existing_artifact: 现有的工件数据（可选，用于增量更新上下文）
        reasoning_hint: 来自 ReasoningNode 的上下文感知更新提示 (Optional)

    Returns:
        str: 完整的 Prompt 文本
    """
    # 阶段到 artifact_type 的映射
    stage_to_type = {
        "clarify": "requirement",
        "strategy": "design",
        "cases": "cases",
        "delivery": "delivery",
    }

    artifact_type = stage_to_type.get(current_stage, "requirement")
    schemas = get_artifact_json_schemas()

    # 为当前阶段生成示例
    current_schema = schemas.get(artifact_type)
    schema_example = (
        format_schema_for_prompt(current_schema) if current_schema else "{}"
    )

    # 增量更新上下文
    incremental_context = ""
    if existing_artifact:
        import json

        existing_json = json.dumps(existing_artifact, ensure_ascii=False, indent=2)
        incremental_context = f"""
**INCREMENTAL UPDATE MODE ACTIVE**:
Current State:
```json
{existing_json}
```
**INSTRUCTIONS**:
- Only output changed items or new additions.
- Use ID to match existing items (e.g. assumptions, rules).
- **CRITICAL**: To update an existing item in a list (like changing a "pending" assumption to "confirmed"), you MUST include that item in your JSON output with its `id` and the updated fields (`status`, `note`). If you omit the list or the item, it will NOT be updated!
- Do not output unchanged items if possible (to save tokens), unless necessary for context.
"""

    # [新增] 注入 Reasoning Hint
    reasoning_context = ""
    if reasoning_hint:
        reasoning_context = f"""
**来自推理智能体的重要上下文 (CONTEXT FROM REASONING AGENT)**:
{reasoning_hint}

请务必根据上述上下文更新文档，尤其是其中提到的风险、决策和**状态变更**。
如果上下文中包含"状态变更"指令（如 "Q-001 → confirmed"），你**必须**在 `assumptions` 列表中找到对应 ID 的条目，
将其 `status` 更新为 `confirmed`，并在 `note` 字段中填写确认结论。
"""
    else:
        # 兜底规则：即使没有 hint，也提醒 LLM 关注对话中的状态变更
        reasoning_context = """
**通用规则 (FALLBACK RULE)**:
如果对话历史中用户已经明确回答或确认了 `assumptions` 列表中的某个待确认问题（status 为 "pending"），
你**必须**将对应条目的 `status` 更新为 `confirmed`，并在 `note` 字段中记录用户的确认结论。
不要遗漏任何已在对话中被回答的问题。
"""

    return f"""
系统内部指令：
你正处于产出物更新阶段 (Artifact Update Phase)。

**严重警告 (CRITICAL RULES)**：
1. 你必须调用 `UpdateStructuredArtifact` 工具。
2. `key` 必须严格使用："{artifact_key}"。
3. `artifact_type` 必须使用："{artifact_type}"。
4. `content` 字段必须是符合对应类型的 JSON 对象，而不是 Markdown 字符串。

{reasoning_context}

{incremental_context}

**当前阶段的 JSON Schema 示例**:

```json
{schema_example}
```

**参考模板结构 (REFERENCE TEMPLATE)**：
虽然你需要输出 JSON，但内容逻辑应参考以下 Markdown 结构：
```
{template_outline}
```

请将上述 Markdown 结构中的信息，严格映射到 `UpdateStructuredArtifact` 工具的 `content` JSON 字段中。
**严禁臆造 Schema 中不存在的字段（如 'summary', 'sections' 等）。**
**所有字段名称必须与上方 JSON Schema 示例完全一致。**
"""


# 保留旧版 Prompt 作为后备（用于模板字符串替换的场景）
ARTIFACT_UPDATE_PROMPT = """
系统内部指令：
你正处于产出物更新阶段 (Artifact Update Phase)。

**严重警告 (CRITICAL RULES)**：
1. 你必须调用 `UpdateStructuredArtifact` 工具。
2. `key` 必须严格使用："{artifact_key}"。
3. `artifact_type` 必须根据当前阶段选择：
   - clarify -> "requirement"
   - strategy -> "design"
   - cases -> "cases"
   - delivery -> "delivery"
4. `content` 字段必须是符合对应类型的 JSON 对象，而不是 Markdown 字符串。

**参考模板结构 (REFERENCE TEMPLATE)**：
```
{template_outline}
```

请将上述 Markdown 结构中的信息，严格映射到 `UpdateStructuredArtifact` 工具的 `content` JSON 字段中。
**严禁臆造 Schema 中不存在的字段。所有字段必须符合 Pydantic 模型定义。**
**提示：查看 artifact_models.py 中的 RequirementDoc, DesignDoc, CaseDoc 定义获取准确的字段列表。**
"""
