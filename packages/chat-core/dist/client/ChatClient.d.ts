/**
 * Core ChatClient implementation with Transport, Storage, AuthProvider & Middleware abstractions
 */
import { TypedEventEmitter } from '../events/EventEmitter';
import { Transport } from '../transport/Transport';
import { StorageAdapter } from '../storage/StorageAdapter';
import { AuthProvider } from '../auth/AuthProvider';
import { MiddlewarePipeline, MiddlewareFunction } from '../middleware/Middleware';
import { ChatClientOptions, ChatMessage, ChatPlugin, ThemeConfig, AgentChatResponse } from '../types';
export declare class ChatClient extends TypedEventEmitter {
    readonly baseUrl: string;
    readonly cscId: string;
    readonly username: string;
    sessionId: string;
    history: ChatMessage[];
    theme: ThemeConfig;
    transport: Transport;
    storage: StorageAdapter;
    authProvider: AuthProvider;
    pipeline: MiddlewarePipeline;
    private plugins;
    constructor(options?: ChatClientOptions);
    private loadSession;
    use(middleware: MiddlewareFunction): this;
    registerPlugin(plugin: ChatPlugin): void;
    authenticate(): Promise<string | null>;
    seedTestData(): Promise<any>;
    sendMessage(messageText: string): Promise<AgentChatResponse | null>;
    destroy(): void;
}
