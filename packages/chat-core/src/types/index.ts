/**
 * Strict Type Definitions for DigiPay Chat Core SDK (Milestone A)
 */
import { Transport } from '../transport/Transport';
import { StorageAdapter } from '../storage/StorageAdapter';
import { AuthProvider } from '../auth/AuthProvider';

export type Role = 'user' | 'assistant' | 'system';

export interface ChatMessage {
  id?: string;
  role: Role;
  content: string;
  intent?: string;
  escalate?: boolean;
  confidenceScore?: number;
  policyChecked?: boolean;
  isError?: boolean;
  timestamp: Date;
}

export interface ChatSession {
  sessionId: string;
  cscId: string;
  createdAt: Date;
}

export interface ThemeConfig {
  primaryColor?: string;
  backgroundColor?: string;
  borderRadius?: number;
  fontFamily?: string;
  logoUrl?: string;
  mode?: 'light' | 'dark';
}

export interface ChatPluginLifecycle {
  name: string;
  onInit?: (client: any) => void;
  onSessionCreated?: (session: ChatSession) => void;
  onBeforeSend?: (text: string) => string;
  onAfterSend?: (response: AgentChatResponse) => void;
  onMessageReceived?: (msg: ChatMessage) => ChatMessage;
  onTyping?: (isTyping: boolean) => void;
  onDestroy?: () => void;
}

export type ChatPlugin = ChatPluginLifecycle;

export interface ChatClientOptions {
  baseUrl?: string;
  cscId?: string;
  username?: string;
  sessionId?: string;
  token?: string;
  transport?: Transport;
  storage?: StorageAdapter;
  authProvider?: AuthProvider;
  theme?: ThemeConfig;
  plugins?: ChatPlugin[];
}

export interface AgentChatResponse {
  status: string;
  response: string;
  intent: string;
  escalate: boolean;
  confidenceScore: number;
  policyChecked: boolean;
}
