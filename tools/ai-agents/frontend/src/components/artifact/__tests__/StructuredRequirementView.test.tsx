import { render, screen } from '@testing-library/react';
import { StructuredRequirementView } from '../StructuredRequirementView';
import { describe, it, expect } from 'vitest';
import { RequirementDoc } from '../../../types/artifact';

describe('StructuredRequirementView Diff Highlighting', () => {
  it('renders diff classes for added and modified items', () => {
    const mockArtifact: RequirementDoc = {
      scope: [],
      out_of_scope: [],
      features: [],
      flow_mermaid: "",
      rules: [
        { id: "R1", desc: "Added Rule", source: "Auto", _diff: "added" },
        { id: "R2", desc: "Modified Rule", source: "User", _diff: "modified" },
        { id: "R3", desc: "Normal Rule", source: "System" }
      ],
      assumptions: [],
      nfr_markdown: ""
    };

    const { container } = render(<StructuredRequirementView artifact={mockArtifact} />);

    // Check for added class on R1 row
    const addedRow = screen.getByText('R1').closest('tr');
    expect(addedRow).toBeInTheDocument();
    // We expect className to contain 'diff-added'
    // Using string matching or classList check
    expect(addedRow?.className).toContain('diff-added');

    // Check for modified class on R2 row
    const modifiedRow = screen.getByText('R2').closest('tr');
    expect(modifiedRow).toBeInTheDocument();
    expect(modifiedRow?.className).toContain('diff-modified');

    // Check for normal row on R3 row
    const normalRow = screen.getByText('R3').closest('tr');
    expect(normalRow).toBeInTheDocument();
    expect(normalRow?.className).not.toContain('diff-modified');
  });

  it('renders Diff Legend when diffs are present', () => {
    const mockArtifact: RequirementDoc = {
      scope: [],
      out_of_scope: [],
      features: [],
      flow_mermaid: "",
      rules: [{ id: "R1", desc: "Added", source: "A", _diff: "added" }],
      assumptions: []
    };
    render(<StructuredRequirementView artifact={mockArtifact} />);
    expect(screen.getByText('变更图例:')).toBeInTheDocument();
    expect(screen.getByText('新增内容')).toBeInTheDocument();
  });

  it('does NOT render Diff Legend when no diffs', () => {
    const mockArtifact: RequirementDoc = {
      scope: [],
      out_of_scope: [],
      features: [],
      flow_mermaid: "",
      rules: [{ id: "R1", desc: "No Diff", source: "A" }],
      assumptions: []
    };
    render(<StructuredRequirementView artifact={mockArtifact} />);
    expect(screen.queryByText('变更图例:')).not.toBeInTheDocument();
  });

  it('renders Mermaid Title when scope_mermaid is present', () => {
    const mockArtifact: RequirementDoc = {
      scope: [],
      out_of_scope: [],
      features: [],
      flow_mermaid: "",
      rules: [],
      assumptions: [],
      scope_mermaid: "graph TD; A-->B;"
    };
    render(<StructuredRequirementView artifact={mockArtifact} />);
    expect(screen.getByText('测试范围总览')).toBeInTheDocument();
    expect(screen.getByText('展示核心模块与外部系统的交互边界')).toBeInTheDocument();
  });
});
