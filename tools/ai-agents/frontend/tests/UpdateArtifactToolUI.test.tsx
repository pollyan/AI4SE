import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { UpdateArtifactView } from '../components/tools/UpdateArtifactToolUI';

describe('UpdateArtifactToolUI', () => {
  it('renders loading state', () => {
    render(
      <UpdateArtifactView 
        args={{ key: 'test', markdown_body: 'content' }} 
        status={{ type: 'running' }} 
      />
    );
    expect(screen.getByText('📝 正在更新文档...')).toBeDefined();
  });

  it('renders completed state', () => {
    render(
      <UpdateArtifactView 
        args={{ key: 'test', markdown_body: 'content' }} 
        status={{ type: 'result' }} 
      />
    );
    expect(screen.getByText('✅ 已更新右侧产出物面板')).toBeDefined();
  });
});
