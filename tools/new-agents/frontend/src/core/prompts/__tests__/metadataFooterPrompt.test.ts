import { describe, expect, it } from 'vitest';

import { CLARIFY_TEMPLATE } from '../test_design/clarify';
import { STRATEGY_TEMPLATE } from '../test_design/strategy';
import { CASES_TEMPLATE } from '../test_design/cases';
import { DELIVERY_TEMPLATE } from '../test_design/delivery';
import { REVIEW_TEMPLATE } from '../req_review/review';
import { REPORT_TEMPLATE } from '../req_review/report';
import { IMPROVEMENT_TEMPLATE } from '../incident_review/improvement';
import { ELEVATOR_TEMPLATE } from '../value_discovery/elevator';
import { PERSONA_TEMPLATE } from '../value_discovery/persona';
import { JOURNEY_TEMPLATE } from '../value_discovery/journey';
import { BLUEPRINT_TEMPLATE } from '../value_discovery/blueprint';
import { INPUT_ANALYSIS_TEMPLATE } from '../story_breakdown/input_analysis';
import { EPIC_MAPPING_TEMPLATE } from '../story_breakdown/epic_mapping';
import { STORY_BACKLOG_TEMPLATE } from '../story_breakdown/story_backlog';
import { SPRINT_PLAN_TEMPLATE } from '../story_breakdown/sprint_plan';
import { INVENTORY_TEMPLATE } from '../prd_review/inventory';
import { QUALITY_AUDIT_TEMPLATE } from '../prd_review/quality_audit';
import { COMPLETION_PLAN_TEMPLATE } from '../prd_review/completion_plan';
import { REVISION_BLUEPRINT_TEMPLATE } from '../prd_review/revision_blueprint';

describe('artifact metadata footer prompt mirrors', () => {
    it.each([
        ['TEST_DESIGN/CLARIFY', CLARIFY_TEMPLATE, '## 文档信息'],
        ['TEST_DESIGN/STRATEGY', STRATEGY_TEMPLATE, '## 文档信息'],
        ['TEST_DESIGN/CASES', CASES_TEMPLATE, '## 文档信息'],
        ['TEST_DESIGN/DELIVERY', DELIVERY_TEMPLATE, '## 1. 文档信息'],
        ['REQ_REVIEW/REVIEW', REVIEW_TEMPLATE, '## 评审信息'],
        ['REQ_REVIEW/REPORT', REPORT_TEMPLATE, '## 评审信息'],
        ['INCIDENT_REVIEW/IMPROVEMENT', IMPROVEMENT_TEMPLATE, '## 报告信息'],
        ['VALUE_DISCOVERY/ELEVATOR', ELEVATOR_TEMPLATE, '## 文档信息'],
        ['VALUE_DISCOVERY/PERSONA', PERSONA_TEMPLATE, '## 文档信息'],
        ['VALUE_DISCOVERY/JOURNEY', JOURNEY_TEMPLATE, '## 文档信息'],
        ['VALUE_DISCOVERY/BLUEPRINT', BLUEPRINT_TEMPLATE, '## 文档信息'],
    ])('%s keeps business content before a compact metadata footer', (_stage, template, heading) => {
        const headingIndex = template.lastIndexOf(heading);
        expect(headingIndex).toBeGreaterThan(0);
        expect(template.slice(headingIndex)).toContain('文档元信息：');
        expect(template.slice(headingIndex)).not.toContain('|---');
        expect(template.slice(headingIndex)).not.toContain('| ---');
    });

    it.each([
        ['STORY_BREAKDOWN/INPUT_ANALYSIS', INPUT_ANALYSIS_TEMPLATE],
        ['STORY_BREAKDOWN/EPIC_MAPPING', EPIC_MAPPING_TEMPLATE],
        ['STORY_BREAKDOWN/STORY_BACKLOG', STORY_BACKLOG_TEMPLATE],
        ['STORY_BREAKDOWN/SPRINT_PLAN', SPRINT_PLAN_TEMPLATE],
        ['PRD_REVIEW/INVENTORY', INVENTORY_TEMPLATE],
        ['PRD_REVIEW/QUALITY_AUDIT', QUALITY_AUDIT_TEMPLATE],
        ['PRD_REVIEW/COMPLETION_PLAN', COMPLETION_PLAN_TEMPLATE],
        ['PRD_REVIEW/REVISION_BLUEPRINT', REVISION_BLUEPRINT_TEMPLATE],
    ])('%s tells the deterministic renderer to append one-line metadata', (_stage, template) => {
        expect(template).toContain('先渲染全部业务正文');
        expect(template).toContain('“## 文档信息”单行展示 document_info 元信息');
        expect(template).toContain('不要把元信息放在正文开头或渲染成表格');
    });

    it.each([
        [
            'VALUE_DISCOVERY/ELEVATOR',
            ELEVATOR_TEMPLATE,
            'Artifact 名称：价值定位诊断报告',
            '状态：可进入用户画像 / 需补充定位信息 / 暂缓',
        ],
        [
            'VALUE_DISCOVERY/PERSONA',
            PERSONA_TEMPLATE,
            'Artifact 名称：用户画像与决策链分析',
            '状态：可进入用户旅程 / 需补充画像证据 / 暂缓',
        ],
        [
            'VALUE_DISCOVERY/JOURNEY',
            JOURNEY_TEMPLATE,
            'Artifact 名称：用户旅程与机会地图',
            '状态：可进入需求蓝图 / 需补充旅程证据 / 暂缓',
        ],
    ])('%s mirrors the exact backend metadata semantics', (_stage, template, name, status) => {
        expect(template).toContain(name);
        expect(template).toContain(status);
    });

    it('mirrors the incident improvement status and timestamp contracts', () => {
        expect(IMPROVEMENT_TEMPLATE).toContain('待复查 / 可关闭 / 暂缓关闭');
        expect(IMPROVEMENT_TEMPLATE).toContain('生成时间：YYYY-MM-DD HH:MM');
    });
});
