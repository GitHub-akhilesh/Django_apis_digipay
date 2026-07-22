"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.ChatClient = void 0;
/**
 * Core ChatClient implementation with Transport, Storage, AuthProvider & Middleware abstractions
 */
const EventEmitter_1 = require("../events/EventEmitter");
const HTTPTransport_1 = require("../transport/HTTPTransport");
const LocalStorageAdapter_1 = require("../storage/LocalStorageAdapter");
const JWTAuthProvider_1 = require("../auth/JWTAuthProvider");
const Middleware_1 = require("../middleware/Middleware");
class ChatClient extends EventEmitter_1.TypedEventEmitter {
    constructor(options = {}) {
        super();
        this.history = [];
        this.pipeline = new Middleware_1.MiddlewarePipeline();
        this.plugins = [];
        this.baseUrl = (options.baseUrl || 'http://127.0.0.1:8000').replace(/\/$/, '');
        this.cscId = options.cscId || '500100100014';
        this.username = options.username || 'merchant_admin';
        this.theme = options.theme || { mode: 'dark', primaryColor: '#2563eb' };
        this.transport = options.transport || new HTTPTransport_1.HTTPTransport();
        this.storage = options.storage || new LocalStorageAdapter_1.LocalStorageAdapter();
        this.authProvider = options.authProvider || new JWTAuthProvider_1.JWTAuthProvider(this.baseUrl, this.username, this.cscId, this.transport);
        this.sessionId = options.sessionId || `sess_${Math.random().toString(36).substring(2, 11)}_${Date.now()}`;
        this.loadSession();
        if (options.plugins) {
            options.plugins.forEach(p => this.registerPlugin(p));
        }
    }
    async loadSession() {
        const key = `digipay_session_${this.cscId}`;
        const stored = await this.storage.getItem(key);
        if (stored) {
            this.sessionId = stored;
        }
        else {
            await this.storage.setItem(key, this.sessionId);
        }
        return this.sessionId;
    }
    use(middleware) {
        this.pipeline.use(middleware);
        return this;
    }
    registerPlugin(plugin) {
        this.plugins.push(plugin);
        if (plugin.onInit) {
            plugin.onInit(this);
        }
    }
    async authenticate() {
        this.emit('status', 'authenticating');
        const token = await this.authProvider.getToken();
        if (token) {
            this.emit('status', 'authenticated');
            this.emit('connected', { token });
        }
        else {
            this.emit('status', 'auth_failed');
        }
        return token;
    }
    async sendMessage(messageText) {
        if (!messageText || !messageText.trim())
            return null;
        let processedText = messageText.trim();
        // 1. Plugin onBeforeSend Lifecycle
        for (const plugin of this.plugins) {
            if (plugin.onBeforeSend) {
                processedText = plugin.onBeforeSend(processedText);
            }
        }
        const token = await this.authenticate();
        const userMessage = {
            role: 'user',
            content: processedText,
            timestamp: new Date()
        };
        this.history.push(userMessage);
        this.emit('message', userMessage);
        // Typing Event Lifecycle
        this.emit('typing', true);
        for (const plugin of this.plugins) {
            if (plugin.onTyping)
                plugin.onTyping(true);
        }
        try {
            const headers = {};
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }
            // 2. Execute Transport Request through Middleware Pipeline
            const response = await this.pipeline.execute({
                url: `${this.baseUrl}/api/v1/agent/chat`,
                method: 'POST',
                headers,
                body: {
                    sessionId: this.sessionId,
                    message: processedText,
                    cscId: this.cscId
                }
            }, (req) => this.transport.send(req));
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: Failed to reach API`);
            }
            const data = response.data;
            let assistantMsg = {
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
                if (plugin.onTyping)
                    plugin.onTyping(false);
            }
            this.emit('message', assistantMsg);
            if (data.escalate) {
                this.emit('escalate', assistantMsg);
            }
            return data;
        }
        catch (err) {
            this.emit('typing', false);
            const errorMsg = {
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
    destroy() {
        for (const plugin of this.plugins) {
            if (plugin.onDestroy)
                plugin.onDestroy();
        }
        this.emit('destroy');
    }
}
exports.ChatClient = ChatClient;
