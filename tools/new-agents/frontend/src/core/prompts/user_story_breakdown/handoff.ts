export const HANDOFF_PROMPT = `基于 Ready / Not Ready 故事卡片，准备可交给后续 AI Coding 准备流程读取的单故事 Handoff 清单。

引导流程：
1. 列出 Ready Story 总览，说明每张故事为什么可以交接。
2. 为每张 Ready story 输出需求包字段，包括 storyId、requirementId、acceptanceCriteria、businessRules 和 openQuestions。
3. 记录上游追溯和 Not Ready 阻塞项。
4. 明确 AI Coding 输入边界：这里只交付需求信息，不交付实现计划。

【重要】：
- Handoff 清单不等于开发任务清单。
- 不输出文件路径、代码修改计划、接口实现方案、架构方案或测试命令。
- 如果故事不 ready，必须留在 Not Ready 阻塞项，不能伪装成交接包。`;

export const HANDOFF_TEMPLATE = `# 单故事 Handoff 清单

## 1. Ready Story 总览
| storyId | 标题 | requirementId | 用户价值 | Ready 理由 | 状态 |
| --- | --- | --- | --- | --- | --- |
| US-001 | [故事标题] | REQ-001 | [用户获得的业务结果] | [验收标准和业务规则已明确] | ready |

## 2. 单故事需求包
| 字段 | US-001 |
| --- | --- |
| storyId | US-001 |
| requirementId | REQ-001 |
| userStory | 作为[用户角色]，我想要[能力]，以便[业务价值] |
| acceptanceCriteria | [验收标准 1]；[验收标准 2] |
| businessRules | [业务规则] |
| nonFunctionalNotes | [相关非功能要求或不适用说明] |
| outOfScope | [明确不包含范围] |
| dependencies | [依赖或前置条件] |
| openQuestions | [仍需关注但不阻塞交接的问题；如果没有写“无”] |

## 3. 上游追溯
| storyId | sourceWorkflow | sourceStage | sourceRequirement | sourceSlice | 追溯说明 |
| --- | --- | --- | --- | --- | --- |
| US-001 | VALUE_DISCOVERY | BLUEPRINT | REQ-001 | MVP-001 | [从需求蓝图到故事地图的追溯说明] |

## 4. Not Ready 阻塞项
| storyId | requirementId | 阻塞原因 | 需要补充的问题 | 建议处理 |
| --- | --- | --- | --- | --- |
| US-101 | REQ-101 | [缺少验收标准或依赖不清] | [问题] | [下一步确认动作] |

## 5. AI Coding 输入边界
| 可以交接 | 不在本清单中交接 |
| --- | --- |
| 用户故事正文、来源需求、业务规则、验收标准、不做范围、依赖、开放问题 | 工程实施内容、代码层设计、开发任务拆分、执行类指令 |

## 6. 阶段门禁
- [ ] 每个 ready story 都有 storyId、requirementId 和 acceptanceCriteria。
- [ ] 每个需求包都只包含需求信息和追溯信息。
- [ ] Not Ready story 没有进入 ready handoff 清单。
- [ ] AI Coding 输入边界已经明确排除实现层内容。
`;
