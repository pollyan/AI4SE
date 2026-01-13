import { PendingAttachment } from '../types';

// 配置常量
export const ATTACHMENT_CONFIG = {
  ALLOWED_EXTENSIONS: ['.txt', '.md'],
  MAX_SIZE_BYTES: 10 * 1024 * 1024, // 10MB
  MAX_SIZE_MB: 10,
} as const;

/**
 * 验证文件类型和大小
 * @returns 错误消息，如果验证通过则返回 null
 */
export function validateFile(file: File): string | null {
  const fileName = file.name.toLowerCase();
  const hasValidExtension = ATTACHMENT_CONFIG.ALLOWED_EXTENSIONS.some(ext =>
    fileName.endsWith(ext)
  );

  if (!hasValidExtension) {
    return `不支持的文件格式: ${file.name}。仅支持 ${ATTACHMENT_CONFIG.ALLOWED_EXTENSIONS.join(', ')} 文件`;
  }

  if (file.size > ATTACHMENT_CONFIG.MAX_SIZE_BYTES) {
    return `文件过大: ${file.name}。最大支持 ${ATTACHMENT_CONFIG.MAX_SIZE_MB}MB`;
  }

  if (file.size === 0) {
    return `文件为空: ${file.name}`;
  }

  return null;
}

/**
 * 使用 FileReader 读取文件内容
 */
export function readFileContent(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();

    reader.onload = (event) => {
      const content = event.target?.result as string;
      if (content === undefined) {
        reject(new Error(`无法读取文件内容: ${file.name}`));
        return;
      }
      resolve(content);
    };

    reader.onerror = () => {
      reject(new Error(`文件读取失败: ${file.name}`));
    };

    reader.readAsText(file);
  });
}

/**
 * 处理文件：验证并提取内容
 */
export async function processFile(file: File): Promise<PendingAttachment> {
  const id = `attach-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

  const error = validateFile(file);
  if (error) {
    return {
      id,
      file,
      filename: file.name,
      size: file.size,
      error,
    };
  }

  try {
    const content = await readFileContent(file);
    return {
      id,
      file,
      filename: file.name,
      size: file.size,
      content,
    };
  } catch (err) {
    return {
      id,
      file,
      filename: file.name,
      size: file.size,
      error: err instanceof Error ? err.message : '未知错误',
    };
  }
}

/**
 * 构建包含附件内容的完整消息
 */
export function buildMessageWithAttachments(
  messageText: string,
  attachments: PendingAttachment[]
): string {
  if (attachments.length === 0) {
    return messageText;
  }

  const validAttachments = attachments.filter(a => a.content && !a.error);
  if (validAttachments.length === 0) {
    return messageText;
  }

  const parts = ['=== 相关文档内容 ==='];

  for (const attachment of validAttachments) {
    parts.push(`\n## 文档：${attachment.filename}`);
    parts.push('```');
    parts.push(attachment.content!);
    parts.push('```\n');
  }

  if (messageText.trim()) {
    parts.push('=== 用户问题 ===');
    parts.push(messageText);
  }

  return parts.join('\n');
}

/**
 * 格式化文件大小显示
 */
export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
