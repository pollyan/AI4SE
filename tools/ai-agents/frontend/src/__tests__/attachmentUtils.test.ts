import { describe, it, expect } from 'vitest';
import {
  validateFile,
  readFileContent,
  processFile,
  buildMessageWithAttachments,
  formatFileSize,
  ATTACHMENT_CONFIG
} from '../../utils/attachmentUtils';

describe('AttachmentUtils - ATTACHMENT_CONFIG', () => {
  it('配置应该正确', () => {
    expect(ATTACHMENT_CONFIG.ALLOWED_EXTENSIONS).toEqual(['.txt', '.md']);
    expect(ATTACHMENT_CONFIG.MAX_SIZE_BYTES).toBe(10 * 1024 * 1024);
    expect(ATTACHMENT_CONFIG.MAX_SIZE_MB).toBe(10);
  });
});

describe('AttachmentUtils - validateFile', () => {
  it('应该接受 .txt 文件', () => {
    const file = new File(['content'], 'test.txt', { type: 'text/plain' });
    expect(validateFile(file)).toBeNull();
  });

  it('应该接受 .md 文件', () => {
    const file = new File(['content'], 'README.md', { type: 'text/markdown' });
    expect(validateFile(file)).toBeNull();
  });

  it('应该拒绝 .pdf 文件', () => {
    const file = new File(['content'], 'doc.pdf', { type: 'application/pdf' });
    expect(validateFile(file)).toContain('不支持的文件格式');
  });

  it('应该拒绝大于 10MB 的文件', () => {
    const largeContent = 'x'.repeat(11 * 1024 * 1024);
    const file = new File([largeContent], 'large.txt', { type: 'text/plain' });
    expect(validateFile(file)).toContain('文件过大');
  });

  it('应该拒绝空文件', () => {
    const file = new File([], 'empty.txt', { type: 'text/plain' });
    expect(validateFile(file)).toContain('文件为空');
  });

  it('应该正确处理大小写扩展名', () => {
    const file = new File(['content'], 'TEST.TXT', { type: 'text/plain' });
    expect(validateFile(file)).toBeNull();
  });

  it('应该正确处理混合大小写', () => {
    const file = new File(['content'], 'ReadMe.Md', { type: 'text/markdown' });
    expect(validateFile(file)).toBeNull();
  });
});

describe('AttachmentUtils - formatFileSize', () => {
  it('应该格式化字节数', () => {
    expect(formatFileSize(500)).toBe('500 B');
    expect(formatFileSize(1023)).toBe('1023 B');
  });

  it('应该格式化千字节', () => {
    expect(formatFileSize(1024)).toBe('1.0 KB');
    expect(formatFileSize(2048)).toBe('2.0 KB');
    expect(formatFileSize(1536)).toBe('1.5 KB');
  });

  it('应该格式化兆字节', () => {
    expect(formatFileSize(1024 * 1024)).toBe('1.0 MB');
    expect(formatFileSize(5 * 1024 * 1024)).toBe('5.0 MB');
  });
});

describe('AttachmentUtils - buildMessageWithAttachments', () => {
  it('应该将消息与附件内容组合', () => {
    const attachments = [{
      id: '1',
      file: new File(['File content here'], 'test.txt'),
      filename: 'test.txt',
      size: 15,
      content: 'File content here',
    }];

    const result = buildMessageWithAttachments('My question', attachments);

    expect(result).toContain('=== 相关文档内容 ===');
    expect(result).toContain('## 文档：test.txt');
    expect(result).toContain('File content here');
    expect(result).toContain('=== 用户问题 ===');
    expect(result).toContain('My question');
  });

  it('应该处理多个附件', () => {
    const attachments = [
      {
        id: '1',
        file: new File(['Content 1'], 'file1.txt'),
        filename: 'file1.txt',
        size: 9,
        content: 'Content 1',
      },
      {
        id: '2',
        file: new File(['Content 2'], 'file2.md'),
        filename: 'file2.md',
        size: 9,
        content: 'Content 2',
      },
    ];

    const result = buildMessageWithAttachments('Question', attachments);

    expect(result).toContain('## 文档：file1.txt');
    expect(result).toContain('## 文档：file2.md');
    expect(result).toContain('Content 1');
    expect(result).toContain('Content 2');
  });

  it('应该仅返回原始消息（无附件时）', () => {
    const result = buildMessageWithAttachments('Text only', []);
    expect(result).toBe('Text only');
  });

  it('应该忽略有错误的附件', () => {
    const attachments = [
      {
        id: '1',
        file: new File(['Valid content'], 'valid.txt'),
        filename: 'valid.txt',
        size: 13,
        content: 'Valid content',
      },
      {
        id: '2',
        file: new File([''], 'invalid.txt'),
        filename: 'invalid.txt',
        size: 0,
        error: '文件为空: invalid.txt',
      },
    ];

    const result = buildMessageWithAttachments('Question', attachments);

    expect(result).toContain('Valid content');
    expect(result).not.toContain('invalid.txt');
  });

  it('应该处理仅附件无消息文本的情况', () => {
    const attachments = [{
      id: '1',
      file: new File(['Only file'], 'test.txt'),
      filename: 'test.txt',
      size: 9,
      content: 'Only file',
    }];

    const result = buildMessageWithAttachments('', attachments);

    expect(result).toContain('=== 相关文档内容 ===');
    expect(result).toContain('Only file');
    expect(result).not.toContain('=== 用户问题 ===');
  });
});

describe('AttachmentUtils - processFile', () => {
  it('应该成功处理有效的 .txt 文件', async () => {
    const file = new File(['Test content'], 'test.txt', { type: 'text/plain' });
    const result = await processFile(file);

    expect(result.filename).toBe('test.txt');
    expect(result.content).toBe('Test content');
    expect(result.error).toBeUndefined();
    expect(result.id).toMatch(/^attach-\d+-[a-z0-9]+$/);
    expect(result.size).toBe(12);
  });

  it('应该成功处理有效的 .md 文件', async () => {
    const file = new File(['# Markdown'], 'README.md', { type: 'text/markdown' });
    const result = await processFile(file);

    expect(result.filename).toBe('README.md');
    expect(result.content).toBe('# Markdown');
    expect(result.error).toBeUndefined();
  });

  it('应该返回无效文件的错误', async () => {
    const file = new File(['content'], 'test.pdf', { type: 'application/pdf' });
    const result = await processFile(file);

    expect(result.error).toBeDefined();
    expect(result.error).toContain('不支持的文件格式');
    expect(result.content).toBeUndefined();
  });

  it('应该为空文件返回错误', async () => {
    const file = new File([], 'empty.txt', { type: 'text/plain' });
    const result = await processFile(file);

    expect(result.error).toBeDefined();
    expect(result.error).toContain('文件为空');
  });

  it('应该为大文件返回错误', async () => {
    const largeContent = 'x'.repeat(11 * 1024 * 1024);
    const file = new File([largeContent], 'large.txt', { type: 'text/plain' });
    const result = await processFile(file);

    expect(result.error).toBeDefined();
    expect(result.error).toContain('文件过大');
  });
});

describe('AttachmentUtils - readFileContent', () => {
  it('应该读取文本文件内容', async () => {
    const file = new File(['Hello World'], 'test.txt');
    const content = await readFileContent(file);

    expect(content).toBe('Hello World');
  });

  it('应该读取带有特殊字符的内容', async () => {
    const specialContent = '中文测试\n换行符\t制表符';
    const file = new File([specialContent], 'test.txt');
    const content = await readFileContent(file);

    expect(content).toBe(specialContent);
  });

  it('应该读取多行文本', async () => {
    const multiline = 'Line 1\nLine 2\nLine 3';
    const file = new File([multiline], 'test.txt');
    const content = await readFileContent(file);

    expect(content).toBe(multiline);
  });
});
