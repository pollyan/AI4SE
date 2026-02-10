
import { render, screen } from '@testing-library/react';
import { StructuredRequirementView } from '../StructuredRequirementView';
import fixture from '../__fixtures__/requirement.json';
import { RequirementDoc } from '../../../types/artifact';

// Mock mermaid
vi.mock('mermaid', () => ({
  default: {
    initialize: vi.fn(),
    render: vi.fn().mockResolvedValue({ svg: '<svg>mock</svg>' }),
  },
}));

describe('StructuredRequirementView', () => {
  it('renders scope items', () => {
    render(<StructuredRequirementView artifact={fixture as RequirementDoc} />);
    expect(screen.getByText('User Login')).toBeInTheDocument();
    expect(screen.getByText('Password Reset')).toBeInTheDocument();
  });

  it('renders out_of_scope items', () => {
    render(<StructuredRequirementView artifact={fixture as RequirementDoc} />);
    expect(screen.getByText('Social Login')).toBeInTheDocument();
    expect(screen.getByText('OAuth2 Integration')).toBeInTheDocument();
  });

  it('renders features', () => {
    render(<StructuredRequirementView artifact={fixture as RequirementDoc} />);
    expect(screen.getByText('F1')).toBeInTheDocument();
    expect(screen.getByText('用户登录')).toBeInTheDocument();
  });

  it('renders rules', () => {
    render(<StructuredRequirementView artifact={fixture as RequirementDoc} />);
    expect(screen.getByText('R1')).toBeInTheDocument();
    expect(screen.getByText('Password must be at least 8 chars')).toBeInTheDocument();
  });

  it('renders assumptions', () => {
    render(<StructuredRequirementView artifact={fixture as RequirementDoc} />);
    expect(screen.getByText('Q1')).toBeInTheDocument();
    expect(screen.getByText('Do we support 2FA?')).toBeInTheDocument();
  });
});
