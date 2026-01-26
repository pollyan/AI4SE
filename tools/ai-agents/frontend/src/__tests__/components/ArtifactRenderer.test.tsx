import { render, screen } from '@testing-library/react';
import { ArtifactRenderer } from '../../components/artifact/ArtifactRenderer';
import { AgentArtifact } from '../../types/artifact';

describe('ArtifactRenderer', () => {
  it('renders RequirementDoc correctly', () => {
    const artifact: AgentArtifact = {
      phase: 'requirement',
      version: '1.0',
      content: {
        scope: ['Login Page', 'API'],
        flow_mermaid: 'graph LR; A-->B',
        rules: [
          { id: 'R1', desc: 'Password must be strong', source: 'default' }
        ],
        assumptions: [
          { id: 'Q1', question: 'Is SSO supported?', status: 'pending' }
        ],
        nfr_markdown: 'Fast response'
      }
    };

    render(<ArtifactRenderer artifact={artifact} />);

    expect(screen.getByText('Scope')).toBeInTheDocument();
    expect(screen.getByText('Login Page')).toBeInTheDocument();
    expect(screen.getByText('Business Rules')).toBeInTheDocument();
    expect(screen.getByText('Password must be strong')).toBeInTheDocument();
    expect(screen.getByText('Assumptions')).toBeInTheDocument();
    expect(screen.getByText('Is SSO supported?')).toBeInTheDocument();
    expect(screen.getByText('pending')).toBeInTheDocument();
    // Check if mermaid code is rendered (raw)
    expect(screen.getByText((content) => content.includes('graph LR'))).toBeInTheDocument();
  });

  it('renders DesignDoc correctly', () => {
    const artifact: AgentArtifact = {
      phase: 'design',
      version: '1.0',
      content: {
        strategy_markdown: 'Test Strategy Content',
        test_points: {
          id: 'ROOT',
          label: 'Root Node',
          type: 'group',
          children: [
            { id: 'TP1', label: 'Child Point', type: 'point', priority: 'P0', is_new: true }
          ]
        }
      }
    };

    render(<ArtifactRenderer artifact={artifact} />);

    expect(screen.getByText('Test Strategy')).toBeInTheDocument();
    expect(screen.getByText('Test Strategy Content')).toBeInTheDocument();
    expect(screen.getByText('Test Point Topology')).toBeInTheDocument();
    expect(screen.getByText('Root Node')).toBeInTheDocument();
    expect(screen.getByText('Child Point')).toBeInTheDocument();
    expect(screen.getByText('P0')).toBeInTheDocument();
    expect(screen.getByText('New')).toBeInTheDocument();
  });

  it('renders CaseDoc correctly', () => {
    const artifact: AgentArtifact = {
      phase: 'cases',
      version: '1.0',
      content: {
        cases: [
          {
            id: 'TC1',
            title: 'Verify Login',
            tags: ['Smoke'],
            steps: [
              { action: 'Enter user', expect: 'Shown' }
            ]
          }
        ],
        stats: {
          total: 1,
          p0_count: 0,
          auto_ready: 1
        }
      }
    };

    render(<ArtifactRenderer artifact={artifact} />);

    expect(screen.getByText('Total Cases')).toBeInTheDocument();
    expect(screen.getAllByText('1')).toHaveLength(3); // Total, Auto Ready, Steps count
    expect(screen.getByText('TC1')).toBeInTheDocument();
    expect(screen.getByText('Verify Login')).toBeInTheDocument();
    expect(screen.getByText('Smoke')).toBeInTheDocument();
  });

  it('renders unknown artifact gracefully', () => {
    const artifact = {
      phase: 'unknown',
      version: '1.0',
      content: { foo: 'bar' }
    } as unknown as AgentArtifact;

    render(<ArtifactRenderer artifact={artifact} />);

    expect(screen.getByText('Unknown Artifact Type')).toBeInTheDocument();
    expect(screen.getByText((content) => content.includes('unknown'))).toBeInTheDocument();
  });
});
