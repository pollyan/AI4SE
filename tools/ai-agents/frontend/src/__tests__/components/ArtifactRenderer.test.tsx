import { render, screen } from '@testing-library/react';
import { ArtifactRenderer } from '../../components/artifact/ArtifactRenderer';
import { AgentArtifact } from '../../types/artifact';

// Mock mermaid
vi.mock('mermaid', () => ({
  default: {
    initialize: vi.fn(),
    render: vi.fn().mockResolvedValue({ svg: '<svg>mock</svg>' }),
  },
}));

describe('ArtifactRenderer', () => {
  it('renders RequirementDoc correctly', async () => {
    const artifact: AgentArtifact = {
      phase: 'requirement',
      version: '1.0',
      content: {
        scope: ['Login Page', 'API'],
        out_of_scope: [],
        features: [],
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

    expect(screen.getByText('测试范围')).toBeInTheDocument();
    expect(screen.getByText('Login Page')).toBeInTheDocument();
    expect(screen.getByText('核心业务规则')).toBeInTheDocument();
    expect(screen.getByText('Password must be strong')).toBeInTheDocument();
    expect(screen.getByText('待澄清问题 / 已确认信息')).toBeInTheDocument();
    expect(screen.getByText('Is SSO supported?')).toBeInTheDocument();
    // Mermaid renders async, and we mock it to return svg string.
    // The component sets innerHTML. testing-library doesn't easily search inside innerHTML string unless we wait.
    // But we can check if the chart container exists.
    // Or await screen.findByText... wait, svg content might be hidden.
    // Let's remove the raw code check as it's no longer rendered as raw text.
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
