import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { AttachmentButton } from '../../../components/chat/AttachmentButton';

describe('AttachmentButton 组件', () => {
  it('应该渲染按钮', () => {
    render(<AttachmentButton onFilesSelected={vi.fn()} />);

    const button = screen.getByRole('button', { name: /attach files/i });
    expect(button).toBeInTheDocument();
    expect(button).toHaveAttribute('title', '附加文件 (.txt, .md)');
  });

  it('应该打开文件选择器（点击按钮）', () => {
    const onFilesSelected = vi.fn();
    render(<AttachmentButton onFilesSelected={onFilesSelected} />);

    const button = screen.getByRole('button');
    fireEvent.click(button);

    const input = document.querySelector('input[type="file"]');
    expect(input).toHaveAttribute('type', 'file');
  });

  it('应该调用 onFilesSelected（选择文件后）', () => {
    const onFilesSelected = vi.fn();
    render(<AttachmentButton onFilesSelected={onFilesSelected} />);

    const input = document.querySelector('input[type="file"]') as HTMLInputElement;

    const file = new File(['content'], 'test.txt');
    fireEvent.change(input, { target: { files: [file] } });

    expect(onFilesSelected).toHaveBeenCalledWith([file]);
  });

  it('应该接受多个文件', () => {
    const onFilesSelected = vi.fn();
    render(<AttachmentButton onFilesSelected={onFilesSelected} />);

    const input = document.querySelector('input[type="file"]') as HTMLInputElement;

    const file1 = new File(['content1'], 'file1.txt');
    const file2 = new File(['content2'], 'file2.md');
    fireEvent.change(input, { target: { files: [file1, file2] } });

    expect(onFilesSelected).toHaveBeenCalledWith([file1, file2]);
  });

  it('应该限制文件类型为 .txt 和 .md', () => {
    render(<AttachmentButton onFilesSelected={vi.fn()} />);

    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    expect(input).toHaveAttribute('accept', '.txt,.md');
  });

  it('应该支持 multiple 属性', () => {
    render(<AttachmentButton onFilesSelected={vi.fn()} />);

    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    expect(input).toHaveAttribute('multiple');
  });

  it('应该在禁用状态下禁用按钮和输入', () => {
    render(<AttachmentButton onFilesSelected={vi.fn()} disabled={true} />);

    const button = screen.getByRole('button');
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;

    expect(button).toBeDisabled();
    expect(input).toBeDisabled();
  });

  it('应该重置 input 值（允许重复选择同一文件）', () => {
    const onFilesSelected = vi.fn();
    render(<AttachmentButton onFilesSelected={onFilesSelected} />);

    const input = document.querySelector('input[type="file"]') as HTMLInputElement;

    const file = new File(['content'], 'test.txt');

    // 第一次选择
    fireEvent.change(input, { target: { files: [file] } });
    expect(onFilesSelected).toHaveBeenCalledTimes(1);

    // 检查 input 值已重置
    expect(input.value).toBe('');
  });
});
