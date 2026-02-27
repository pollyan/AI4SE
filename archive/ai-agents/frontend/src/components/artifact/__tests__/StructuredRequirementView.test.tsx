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


  it('renders inline diff for modified rule description', () => {
    const mockArtifact: RequirementDoc = {
      scope: [],
      out_of_scope: [],
      features: [],
      flow_mermaid: "",
      rules: [
        {
          id: "R1",
          desc: "New Description",
          source: "Auto",
          _diff: "modified",
          _prev: { desc: "Old Description" }
        }
      ],
      assumptions: [],
      nfr_markdown: ""
    };

    render(<StructuredRequirementView artifact={mockArtifact} />);

    // "Old Description" vs "New Description"
    // Sentence diff: "Old Description" (deleted), "New Description" (inserted)

    const deletedPart = screen.getByText('Old Description');
    expect(deletedPart).toHaveClass('diff-deleted');

    const insertedPart = screen.getByText('New Description');
    expect(insertedPart).toHaveClass('diff-inserted');

    // "Description" should NOT be present as a separate common part
    // because the whole sentence changed.
    expect(screen.queryByText((content, element) => {
      return element?.tagName.toLowerCase() === 'span' &&
        content === 'Description' &&
        !element.classList.contains('diff-deleted') &&
        !element.classList.contains('diff-inserted');
    })).not.toBeInTheDocument();
  });

  it('renders inline diff for Feature fields', () => {
    const mockArtifact: RequirementDoc = {
      scope: [],
      out_of_scope: [],
      features: [
        {
          id: "F1",
          name: "New Feature Name",
          desc: "New Desc",
          priority: "P0",
          acceptance: [],
          _diff: "modified",
          _prev: {
            name: "Old Feature Name",
            desc: "Old Desc"
          }
        }
      ],
      flow_mermaid: "",
      rules: [],
      assumptions: [],
      nfr_markdown: ""
    };

    render(<StructuredRequirementView artifact={mockArtifact} />);

    // Feature Name Diff
    // Expect "Old Feature Name" to be deleted (whole sentence)
    const deletedName = screen.getByText("Old Feature Name");
    expect(deletedName).toHaveClass('diff-deleted');

    const insertedName = screen.getByText("New Feature Name");
    expect(insertedName).toHaveClass('diff-inserted');

    // Feature Desc Diff
    // "Old Desc" vs "New Desc"
    const deletedDesc = screen.getByText("Old Desc");
    expect(deletedDesc).toHaveClass('diff-deleted');

    const insertedDesc = screen.getByText("New Desc");
    expect(insertedDesc).toHaveClass('diff-inserted');
  });

  it('renders inline diff for Assumption fields', () => {
    const mockArtifact: RequirementDoc = {
      scope: [],
      out_of_scope: [],
      features: [],
      flow_mermaid: "",
      rules: [],
      assumptions: [
        {
          id: "A1",
          question: "New Question?",
          note: "New Note",
          priority: "P1",
          status: "confirmed",
          _diff: "modified",
          _prev: {
            question: "Old Question?",
            note: "Old Note"
          }
        }
      ],
      nfr_markdown: ""
    };

    render(<StructuredRequirementView artifact={mockArtifact} />);

    // "Old Question?" vs "New Question?" -> Whole sentence replacement
    // "Old Note" vs "New Note" -> Whole sentence replacement (treated as one sentence if no punctuation)

    // Check for "Old Question?" text being deleted
    const deletedQ = screen.getByText("Old Question?");
    expect(deletedQ).toHaveClass('diff-deleted');

    // Check for "Old Note" text being deleted
    const deletedN = screen.getByText("Old Note");
    expect(deletedN).toHaveClass('diff-deleted');

    // Check for inserts
    const insertedQ = screen.getByText("New Question?");
    expect(insertedQ).toHaveClass('diff-inserted');

    const insertedN = screen.getByText("New Note");
    expect(insertedN).toHaveClass('diff-inserted');
  });

  it('renders scope and out_of_scope correctly (without diff classes for now)', () => {
    const mockArtifact: RequirementDoc = {
      scope: ["Item A", "Item B"],
      out_of_scope: ["Item X"],
      features: [],
      flow_mermaid: "",
      rules: [],
      assumptions: [],
      nfr_markdown: ""
    };

    render(<StructuredRequirementView artifact={mockArtifact} />);

    // Check Scope
    expect(screen.getByText("Item A")).toBeInTheDocument();
    expect(screen.getByText("Item B")).toBeInTheDocument();

    // We just check they are rendered.
    expect(screen.getByText("Item X")).toBeInTheDocument();
  });

  it('renders clean interface when backend clears transient diffs (Turn 2)', () => {
    // This simulates the state after "Transient State Management" cleanup
    // where the backend returns no _diff or _prev fields because the item is unchanged in the new turn.
    const mockArtifact: RequirementDoc = {
      scope: [],
      out_of_scope: [],
      features: [],
      flow_mermaid: "",
      rules: [
        {
          id: "R1",
          desc: "Stable Rule Content",
          source: "System"
          // No _diff or _prev here
        }
      ],
      assumptions: [],
      nfr_markdown: ""
    };

    render(<StructuredRequirementView artifact={mockArtifact} />);

    // Check that the content is rendered
    const ruleContent = screen.getByText("Stable Rule Content");
    expect(ruleContent).toBeInTheDocument();

    // Verify ABSENCE of any diff classes
    // The row should not have diff-modified or diff-added
    // Note: getByText returns the element containing the text. 
    // In StructuredRequirementView, desc is rendered inside a DiffField which inside a td.
    // The row (tr) gets the class.
    const row = ruleContent.closest('tr');
    expect(row).not.toHaveClass('diff-modified');
    expect(row).not.toHaveClass('diff-added');

    // The text itself should not be inside .diff-inserted or .diff-deleted
    // If it was wrapped like <span class="diff-inserted">Stable...</span>, getByText would return that span.
    expect(ruleContent).not.toHaveClass('diff-inserted');
    expect(ruleContent).not.toHaveClass('diff-deleted');
  });
});
