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
}
