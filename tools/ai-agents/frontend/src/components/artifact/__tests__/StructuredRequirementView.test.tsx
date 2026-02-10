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
    expect(normalRow?.className).not.toContain('diff-added');
    expect(normalRow?.className).not.toContain('diff-modified');
  });
});
