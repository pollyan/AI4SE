export enum AssistantId {
  Alex = 'alex',
  Lisa = 'lisa',
}

export interface Assistant {
  id: AssistantId;
  name: string;
  initial: string;
  role: string;
  description: string;
  colorClass: string;
  bgColorClass: string;
  borderColorClass: string;
  textColorClass: string;
  systemInstruction: string;
  welcomeMessage: string;
}

export interface ChatMessage {
  role: 'user' | 'model';
  text: string;
  timestamp: number;
  isThinking?: boolean;
  attachments?: MessageAttachment[];  // 新增：附件元数据
}

// 待发送的附件（用户选择后，发送前）
export interface PendingAttachment {
  id: string;
  file: File;
  filename: string;
  size: number;
  content?: string;  // 提取的文本内容
  error?: string;    // 验证错误消息
}

// 消息中的附件元数据（发送后）
export interface MessageAttachment {
  filename: string;
  size: number;
}
