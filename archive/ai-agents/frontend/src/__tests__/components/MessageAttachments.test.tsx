import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MessageAttachments } from '../../../components/chat/MessageAttachments';
import { MessageAttachment } from '../../../types';

describe('MessageAttachments 组件', () => {
  it('应该不显示任何内容（无附件时）', () => {
    const { container } = render(
      <MessageAttachments attachments={[]} />
    );

    expect(container.firstChild).toBeNull();
  });

  it('应该不显示任何内容（attachments 为 undefined）', () => {
    const { container } = render(
      <MessageAttachments attachments={undefined} />
    );

    expect(container.firstChild).toBeNull();
  });

  it('应该显示单个附件', () => {
    const attachments: MessageAttachment[] = [{
      filename: 'test.txt',
      size: 1024,
    }];

    render(<MessageAttachments attachments={attachments} />);

    expect(screen.getByText('test.txt')).toBeInTheDocument();
    expect(screen.getByText('(1.0 KB)')).toBeInTheDocument();
  });

  it('应该显示多个附件', () => {
    const attachments: MessageAttachment[] = [
      { filename: 'file1.txt', size: 1024 },
      { filename: 'file2.md', size: 2048 },
    ];

    render(<MessageAttachments attachments={attachments} />);

    expect(screen.getByText('file1.txt')).toBeInTheDocument();
    expect(screen.getByText('file2.md')).toBeInTheDocument();
  });

  it('应该正确格式化文件大小', () => {
    const attachments: MessageAttachment[] = [
      { filename: 'small.txt', size: 500 },
      { filename: 'medium.txt', size: 2048 },
      { filename: 'large.txt', size: 5 * 1024 * 1024 },
    ];

    render(<MessageAttachments attachments={attachments} />);

    expect(screen.getByText('(500 B)')).toBeInTheDocument();
    expect(screen.getByText('(2.0 KB)')).toBeInTheDocument();
    expect(screen.getByText('(5.0 MB)')).toBeInTheDocument();
  });

  it('应该显示文件图标', () => {
    const attachments: MessageAttachment[] = [{
      filename: 'test.txt',
      size: 1024,
    }];

    const { container } = render(
      <MessageAttachments attachments={attachments} />
    );

    const icon = container.querySelector('svg');
    expect(icon).toBeInTheDocument();
  });

  it('应该应用正确的样式类', () => {
    const attachments: MessageAttachment[] = [{
      filename: 'test.txt',
      size: 1024,
    }];

    const { container } = render(
      <MessageAttachments attachments={attachments} />
    );

    const wrapper = container.querySelector('.flex.flex-wrap');
    expect(wrapper).toBeInTheDocument();
  });
});
