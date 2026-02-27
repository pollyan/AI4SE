import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { AttachmentList } from '../../../components/chat/AttachmentList';
import { PendingAttachment } from '../../../types';

describe('AttachmentList 组件', () => {
  it('应该不显示任何内容（无附件时）', () => {
    const { container } = render(
      <AttachmentList attachments={[]} onRemove={vi.fn()} />
    );

    expect(container.firstChild).toBeNull();
  });

  it('应该显示有效附件', () => {
    const attachments: PendingAttachment[] = [{
      id: '1',
      file: new File(['content'], 'test.txt'),
      filename: 'test.txt',
      size: 1024,
      content: 'content',
    }];

    render(<AttachmentList attachments={attachments} onRemove={vi.fn()} />);

    expect(screen.getByText('test.txt')).toBeInTheDocument();
    expect(screen.getByText('1.0 KB')).toBeInTheDocument();
  });

  it('应该显示多个附件', () => {
    const attachments: PendingAttachment[] = [
      {
        id: '1',
        file: new File(['content1'], 'file1.txt'),
        filename: 'file1.txt',
        size: 1024,
        content: 'content1',
      },
      {
        id: '2',
        file: new File(['content2'], 'file2.md'),
        filename: 'file2.md',
        size: 2048,
        content: 'content2',
      },
    ];

    render(<AttachmentList attachments={attachments} onRemove={vi.fn()} />);

    expect(screen.getByText('file1.txt')).toBeInTheDocument();
    expect(screen.getByText('file2.md')).toBeInTheDocument();
  });

  it('应该显示带错误的附件（红色样式）', () => {
    const attachments: PendingAttachment[] = [{
      id: '1',
      file: new File([''], 'empty.txt'),
      filename: 'empty.txt',
      size: 0,
      error: '文件为空: empty.txt',
    }];

    const { container } = render(
      <AttachmentList attachments={attachments} onRemove={vi.fn()} />
    );

    expect(screen.getByText('empty.txt')).toBeInTheDocument();
    expect(screen.getByText('文件为空: empty.txt')).toBeInTheDocument();

    // 检查错误样式（红色边框）
    const attachmentDiv = container.querySelector('.bg-red-50');
    expect(attachmentDiv).toBeInTheDocument();
  });

  it('应该调用 onRemove 回调（点击删除按钮）', () => {
    const onRemove = vi.fn();
    const attachments: PendingAttachment[] = [{
      id: '1',
      file: new File(['content'], 'test.txt'),
      filename: 'test.txt',
      size: 1024,
      content: 'content',
    }];

    render(<AttachmentList attachments={attachments} onRemove={onRemove} />);

    const removeButton = screen.getByRole('button', { name: /remove attachment/i });
    fireEvent.click(removeButton);

    expect(onRemove).toHaveBeenCalledWith('1');
    expect(onRemove).toHaveBeenCalledTimes(1);
  });

  it('应该正确显示文件图标', () => {
    const attachments: PendingAttachment[] = [{
      id: '1',
      file: new File(['content'], 'test.txt'),
      filename: 'test.txt',
      size: 1024,
      content: 'content',
    }];

    const { container } = render(
      <AttachmentList attachments={attachments} onRemove={vi.fn()} />
    );

    // 检查是否有 FileText 图标（lucide-react）
    const icon = container.querySelector('svg');
    expect(icon).toBeInTheDocument();
  });
});
