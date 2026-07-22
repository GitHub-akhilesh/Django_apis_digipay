/**
 * Core ChatClient implementation with Transport, Storage, AuthProvider & Middleware abstractions
 */
import { TypedEventEmitter } from '../events/EventEmitter';
import { Transport } from '../transport/Transport';
import { HTTPTransport } from '../transport/HTTPTransport';
import { StorageAdapter } from '../storage/StorageAdapter';
import { LocalStorageAdapter } from '../storage/LocalStorageAdapter';
import { AuthProvider } from '../auth/AuthProvider';
import { JWTAuthProvider } from '../auth/JWTAuthProvider';
import { MiddlewarePipeline, MiddlewareFunction } from '../middleware/Middleware';
import {
  ChatClientOptions,
  ChatMessage,
  ChatPlugin,
  ThemeConfig,
  AgentChatResponse
} from '../types';

export class ChatClient extends TypedEventEmitter {
  public readonly baseUrl: string;
  public readonly cscId: string;
  public readonly username: string;
  public sessionId: string;
  public history: ChatMessage[] = [];
  public theme: ThemeConfig;

  public transport: Transport;
  public storage: StorageAdapter;
  public authProvider: AuthProvider;
  public pipeline = new MiddlewarePipeline();
  private plugins: ChatPlugin[] = [];

  constructor(options: ChatClientOptions = {}) {
    super();
    this.baseUrl = (options.baseUrl || 'http://127.0.0.1:8000').replace(/\/$/, '');
    this.cscId = options.cscId || '500100100014';
    this.username = options.username || 'merchant_admin';
    this.theme = options.theme || { mode: 'dark', primaryColor: '#2563eb' };

    this.transport = options.transport || new HTTPTransport();
    this.storage = options.storage || new LocalStorageAdapter();
    this.authProvider = options.authProvider || new JWTAuthProvider(
      this.baseUrl,
      this.username,
      this.cscId,
      this.transport
    );

    this.sessionId = options.sessionId || `sess_${Math.random().toString(36).substring(2, 11)}_${Date.now()}`;
    this.loadSession();

    if (options.plugins) {
      options.plugins.forEach(p => this.registerPlugin(p));
    }
  }

  private async loadSession(): Promise<string> {
    const key = `digipay_session_${this.cscId}`;
    const stored = await this.storage.getItem(key);
    if (stored) {
      this.sessionId = stored;
    } else {
      await this.storage.setItem(key, this.sessionId);
    }
    return this.sessionId;
  }

  use(middleware: MiddlewareFunction): this {
    this.pipeline.use(middleware);
    return this;
  }

  registerPlugin(plugin: ChatPlugin): void {
    this.plugins.push(plugin);
    if (plugin.onInit) {
      plugin.onInit(this);
    }
  }

  async authenticate(): Promise<string | null> {
    this.emit('status', 'authenticating');
    const token = await this.authProvider.getToken();
    if (token) {
      this.emit('status', 'authenticated');
      this.emit('connected', { token });
    } else {
      this.emit('status', 'auth_failed');
    }
    return token;
  }

  async seedTestData(): Promise<any> {
    const res = await this.transport.send({
      url: `${this.baseUrl}/api/v1/agent/test-seed`,
      method: 'POST'
    });
    return res.data;
  }

  async sendMessage(messageText: string): Promise<AgentChatResponse | null> {
    if (!messageText || !messageText.trim()) return null;

    let processedText = messageText.trim();

    // 1. Plugin onBeforeSend Lifecycle
    for (const plugin of this.plugins) {
      if (plugin.onBeforeSend) {
        processedText = plugin.onBeforeSend(processedText);
      }
    }

    const token = await this.authenticate();

    const userMessage: ChatMessage = {
      role: 'user',
      content: processedText,
      timestamp: new Date()
    };

    this.history.push(userMessage);
    this.emit('message', userMessage);

    // Typing Event Lifecycle
    this.emit('typing', true);
    for (const plugin of this.plugins) {
      if (plugin.onTyping) plugin.onTyping(true);
    }

    try {
      const headers: Record<string, string> = {};
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      // 2. Execute Transport Request through Middleware Pipeline
      const response = await this.pipeline.execute(
        {
          url: `${this.baseUrl}/api/v1/agent/chat`,
          method: 'POST',
          headers,
          body: {
            sessionId: this.sessionId,
            message: processedText,
            cscId: this.cscId
          }
        },
        (req) => this.transport.send<AgentChatResponse>(req)
      );

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: Failed to reach API`);
      }

      const data: AgentChatResponse = response.data;

      let assistantMsg: ChatMessage = {
        role: 'assistant',
        content: data.response,
        intent: data.intent,
        escalate: data.escalate,
        confidenceScore: data.confidenceScore,
        policyChecked: data.policyChecked,
        timestamp: new Date()
      };

      // 3. Plugin onMessageReceived and onAfterSend Lifecycle
      for (const plugin of this.plugins) {
        if (plugin.onMessageReceived) {
          assistantMsg = plugin.onMessageReceived(assistantMsg);
        }
        if (plugin.onAfterSend) {
          plugin.onAfterSend(data);
        }
      }

      this.history.push(assistantMsg);

      this.emit('typing', false);
      for (const plugin of this.plugins) {
        if (plugin.onTyping) plugin.onTyping(false);
      }

      this.emit('message', assistantMsg);

      if (data.escalate) {
        this.emit('escalate', assistantMsg);
      }

      return data;
    } catch (err: any) {
      this.emit('typing', false);
      const errorMsg: ChatMessage = {
        role: 'assistant',
        content: `Error: ${err.message}`,
        isError: true,
        timestamp: new Date()
      };
      this.history.push(errorMsg);
      this.emit('error', err);
      this.emit('message', errorMsg);
      throw err;
    }
  }

  destroy(): void {
    for (const plugin of this.plugins) {
      if (plugin.onDestroy) plugin.onDestroy();
    }
    this.emit('destroy');
  }
}
