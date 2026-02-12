/**
 * Lisa Agent Artifact 数据类型定义
 * 与后端 artifact_models.py 保持同步
 * 设计文档: docs/plans/2026-01-22-test-agent-redesign.md
 */

export type ArtifactPhase = 'requirement' | 'design' | 'cases' | 'delivery';
export type Priority = 'P0' | 'P1' | 'P2' | 'P3';
export type NodeType = 'group' | 'point';
export type AssumptionStatus = 'pending' | 'assumed' | 'confirmed';
export type RuleSource = string;

export interface Diffable {
  _diff?: 'added' | 'modified';
  [key: string]: any;
}

export interface DesignNode extends Diffable {

  id: string;
  label: string;
  type: NodeType;
  method?: string;
  priority?: Priority;
  is_new?: boolean;
  children?: DesignNode[];
  _diff?: 'added' | 'modified';
  _prev?: Partial<DesignNode>;
}

export interface RuleItem extends Diffable {
  id: string;
  desc: string;
  source: RuleSource;
  _diff?: 'added' | 'modified';
  _prev?: Partial<RuleItem>;
}

export interface AssumptionItem extends Diffable {
  id: string;
  question: string;
  status: AssumptionStatus;
  priority?: Priority;
  note?: string | null;
  _diff?: 'added' | 'modified';
  _prev?: Partial<AssumptionItem>;
}

export interface FeatureItem extends Diffable {
  id: string;
  name: string;
  desc: string;
  acceptance: string[];
  priority: Priority;
  _diff?: 'added' | 'modified';
  _prev?: Partial<FeatureItem>;
}

export interface RequirementDoc {
  scope: string[];
  out_of_scope: string[];
  scope_mermaid?: string | null;
  features: FeatureItem[];
  flow_mermaid: string;
  rules: RuleItem[];
  assumptions: AssumptionItem[];
  nfr_markdown?: string | null;
}

export interface DesignDoc {
  strategy_markdown: string;
  test_points: DesignNode;
}

export interface CaseStep {
  action: string;
  expect: string;
}

export interface CaseItem {
  id: string;
  title: string;
  precondition?: string;
  steps: CaseStep[];
  tags: string[];
  script?: string;
  _diff?: 'added' | 'modified';
  _prev?: Partial<CaseItem>;
}

export interface CaseDoc {
  cases: CaseItem[];
  stats?: {
    total: number;
    p0_count?: number;
    auto_ready?: number;
  };
}

export interface DeliveryDoc {
  title: string;
  version: string;
  requirement: RequirementDoc;
  design: DesignDoc;
  cases: CaseDoc;
  summary_markdown?: string;
}

export interface AgentArtifact {
  phase: ArtifactPhase;
  version: string;
  content: RequirementDoc | DesignDoc | CaseDoc | DeliveryDoc;
}

export function isRequirementDoc(content: AgentArtifact['content']): content is RequirementDoc {
  return 'scope' in content && 'rules' in content;
}

export function isDesignDoc(content: AgentArtifact['content']): content is DesignDoc {
  return 'strategy_markdown' in content && 'test_points' in content;
}

export function isCaseDoc(content: AgentArtifact['content']): content is CaseDoc {
  return 'cases' in content && Array.isArray((content as CaseDoc).cases);
}

export function isDeliveryDoc(content: AgentArtifact['content']): content is DeliveryDoc {
  return 'requirement' in content && 'design' in content && 'cases' in content;
}
