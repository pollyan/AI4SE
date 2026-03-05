import { WorkflowDef, WorkflowType } from './types';
import { IMPROVEMENT_PROMPT, IMPROVEMENT_TEMPLATE } from './prompts/incident_review/improvement';
import { ROOT_CAUSE_PROMPT, ROOT_CAUSE_TEMPLATE } from './prompts/incident_review/root_cause';
import { TIMELINE_PROMPT, TIMELINE_TEMPLATE } from './prompts/incident_review/timeline';
import { DEFINE_PROMPT, DEFINE_TEMPLATE } from './prompts/idea_brainstorm/define';
import { DIVERGE_PROMPT, DIVERGE_TEMPLATE } from './prompts/idea_brainstorm/diverge';
import { CONVERGE_PROMPT, CONVERGE_TEMPLATE } from './prompts/idea_brainstorm/converge';
import { CONCEPT_PROMPT, CONCEPT_TEMPLATE } from './prompts/idea_brainstorm/concept';
import { CLARIFY_PROMPT, CLARIFY_TEMPLATE } from './prompts/test_design/clarify';
import { STRATEGY_PROMPT, STRATEGY_TEMPLATE } from './prompts/test_design/strategy';
import { CASES_PROMPT, CASES_TEMPLATE } from './prompts/test_design/cases';
import { DELIVERY_PROMPT, DELIVERY_TEMPLATE } from './prompts/test_design/delivery';
import { REVIEW_PROMPT, REVIEW_TEMPLATE } from './prompts/req_review/review';
import { REPORT_PROMPT, REPORT_TEMPLATE } from './prompts/req_review/report';
import { ELEVATOR_PROMPT, ELEVATOR_TEMPLATE } from './prompts/value_discovery/elevator';
import { PERSONA_PROMPT, PERSONA_TEMPLATE } from './prompts/value_discovery/persona';
import { JOURNEY_PROMPT, JOURNEY_TEMPLATE } from './prompts/value_discovery/journey';
import { BLUEPRINT_PROMPT, BLUEPRINT_TEMPLATE } from './prompts/value_discovery/blueprint';

import { FENCE } from './utils/constants';
export const WORKFLOWS: Record<WorkflowType, WorkflowDef> = {
    TEST_DESIGN: {
        id: 'TEST_DESIGN',
        agentId: 'lisa',
        name: '测试设计',
        description: '对传入需求进行逻辑拆解与边界梳理',
        stages: [
            {
                id: 'CLARIFY',
                name: '需求澄清',
                description: CLARIFY_PROMPT,
                template: CLARIFY_TEMPLATE
            },
            {
                id: 'STRATEGY',
                name: '策略制定',
                description: STRATEGY_PROMPT,
                template: STRATEGY_TEMPLATE
            },
            {
                id: 'CASES',
                name: '用例编写',
                description: CASES_PROMPT,
                template: CASES_TEMPLATE
            },
            {
                id: 'DELIVERY',
                name: '文档交付',
                description: DELIVERY_PROMPT,
                template: DELIVERY_TEMPLATE
            }
        ],
        onboarding: {
            welcomeMessage: '你好！我是 Lisa 测试专家。我会用 **FMEA 风险分析**、**测试金字塔**等专业方法，引导你从需求澄清到用例编写，完成一份高质量的测试设计文档。',
            starterPrompts: [
                '帮我设计一份登录功能的测试用例',
                '这是我们的需求文档，请帮我分析测试点',
                '我们要上线一个支付功能，需要完整的测试策略'
            ],
            inputPlaceholder: '描述你想测试的功能，或粘贴需求文档...'
        }
    },
    REQ_REVIEW: {
        id: 'REQ_REVIEW',
        agentId: 'lisa',
        name: '需求评审',
        description: '分析需求完整性并评估测试风险',
        stages: [
            {
                id: 'REVIEW',
                name: '深度评审',
                description: REVIEW_PROMPT,
                template: REVIEW_TEMPLATE
            },
            {
                id: 'REPORT',
                name: '评审报告',
                description: REPORT_PROMPT,
                template: REPORT_TEMPLATE
            }
        ],
        onboarding: {
            welcomeMessage: '你好！我会从**可测试性、完整性、边界定义**等 7 个专业维度，帮你深度审查需求文档，输出结构化的评审问题清单。',
            starterPrompts: [
                '请帮我评审这份需求文档的可测试性',
                '这个需求描述比较模糊，帮我找出所有不明确的地方',
                '我们下周要做需求评审会，帮我提前扫描一下这份 PRD'
            ],
            inputPlaceholder: '粘贴需求文档内容，或描述需要评审的需求...'
        }
    },
    INCIDENT_REVIEW: {
        id: 'INCIDENT_REVIEW',
        agentId: 'lisa',
        name: '故障复盘',
        description: '系统化复盘故障根因并生成改进计划',
        stages: [
            {
                id: 'TIMELINE',
                name: '事件还原',
                description: TIMELINE_PROMPT,
                template: TIMELINE_TEMPLATE
            },
            {
                id: 'ROOT_CAUSE',
                name: '根因分析',
                description: ROOT_CAUSE_PROMPT,
                template: ROOT_CAUSE_TEMPLATE
            },
            {
                id: 'IMPROVEMENT',
                name: '改进报告',
                description: IMPROVEMENT_PROMPT,
                template: IMPROVEMENT_TEMPLATE
            }
        ],
        onboarding: {
            welcomeMessage: '你好！我会用**敏捷教练式的结构化方法**，引导你完成故障复盘。我们会依次完成事件时间线还原、5-Why 根因分析和改进计划制定。',
            starterPrompts: [
                '昨天线上出了一个支付失败的故障，帮我做复盘',
                '我们有一个 P1 级别的生产事故需要复盘分析',
                '系统在高峰期出现了服务降级，需要做根因分析'
            ],
            inputPlaceholder: '描述一下这次故障的基本情况...'
        }
    },
    IDEA_BRAINSTORM: {
        id: 'IDEA_BRAINSTORM',
        agentId: 'alex',
        name: '创意头脑风暴',
        description: '针对模糊痛点或概念，探索发散各种创意可能并收敛为具体的产品概念。',
        stages: [
            {
                id: 'DEFINE',
                name: '问题域分析',
                description: DEFINE_PROMPT,
                template: DEFINE_TEMPLATE
            },
            {
                id: 'DIVERGE',
                name: '创意发散',
                description: DIVERGE_PROMPT,
                template: DIVERGE_TEMPLATE
            },
            {
                id: 'CONVERGE',
                name: '收敛聚焦',
                description: CONVERGE_PROMPT,
                template: CONVERGE_TEMPLATE
            },
            {
                id: 'CONCEPT',
                name: '概念输出',
                description: CONCEPT_PROMPT,
                template: CONCEPT_TEMPLATE
            }
        ],
        onboarding: {
            welcomeMessage: '你好！我是 Alex，你的产品创新顾问。告诉我你的初步想法，我们一起把它变成可实现的产品概念！',
            starterPrompts: [
                '我有个做宠物社区的想法',
                '我想帮独立开发者解决变现难题',
                '我觉得现在的记账软件都太复杂了'
            ],
            inputPlaceholder: '描述你想做的产品或解决的问题...'
        }
    },
    VALUE_DISCOVERY: {
        id: 'VALUE_DISCOVERY',
        agentId: 'alex',
        name: '价值发现',
        description: '帮助用户将已有的产品方向系统化梳理，通过价值定位、用户画像、旅程分析，输出结构化需求蓝图。',
        stages: [
            {
                id: 'ELEVATOR',
                name: '价值定位',
                description: ELEVATOR_PROMPT,
                template: ELEVATOR_TEMPLATE
            },
            {
                id: 'PERSONA',
                name: '用户画像',
                description: PERSONA_PROMPT,
                template: PERSONA_TEMPLATE
            },
            {
                id: 'JOURNEY',
                name: '用户旅程',
                description: JOURNEY_PROMPT,
                template: JOURNEY_TEMPLATE
            },
            {
                id: 'BLUEPRINT',
                name: '需求蓝图',
                description: BLUEPRINT_PROMPT,
                template: BLUEPRINT_TEMPLATE
            }
        ],
        onboarding: {
            welcomeMessage: '你好！我是 Alex，产品价值发现顾问。告诉我你想做的产品方向，我会用系统化的方法帮你梳理清楚它的场景、用户和核心价值。',
            starterPrompts: [
                '我们团队想做一个面向中小企业的智能客户管理系统，初步方向已确定，但还没想清楚核心场景',
                '我们计划用 AI 帮测试工程师自动生成测试用例，想验证一下这个方向的价值',
                '我有个想法：做一款帮产品经理自动整理用户反馈的工具，想系统梳理一下'
            ],
            inputPlaceholder: '描述你已有的产品方向或想法...'
        }
    }
};
