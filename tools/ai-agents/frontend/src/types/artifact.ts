/**
 * Lisa Agent Artifact 数据类型定义
 * 与后端 artifact_models.py 保持同步
 * 设计文档: docs/plans/2026-01-22-test-agent-redesign.md
 */

export type ArtifactPhase = 'requirement' | 'design' | 'cases' | 'delivery';
export type Priority = 'P0' | 'P1' | 'P2' | 'P3';
export type NodeType = 'group' | 'point';
export type AssumptionStatus = 'pending' | 'assumed' | 'confirmed';
export type RuleSource = 'user' | 'default';

export interface RuleItem {
  id: string;
  desc: string;
  source: RuleSource;
}

export interface AssumptionItem {
  id: string;
  question: string;
  status: AssumptionStatus;
  note?: string;
}

export interface RequirementDoc {
  scope: string[];
  flow_mermaid: string;
  rules: RuleItem[];
  assumptions: AssumptionItem[];
  nfr_markdown?: string;
}

export interface DesignNode {
  id: string;
  label: string;
  type: NodeType;
  method?: string;
  priority?: Priority;
  is_new?: boolean;
  children?: DesignNode[];
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
