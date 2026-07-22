"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.useChatContext = exports.ChatProvider = void 0;
const react_1 = __importStar(require("react"));
const chat_core_1 = require("@digipay/chat-core");
const ChatContext = (0, react_1.createContext)(undefined);
const ChatProvider = ({ children, ...options }) => {
    const [client] = (0, react_1.useState)(() => new chat_core_1.ChatClient(options));
    const [messages, setMessages] = (0, react_1.useState)([]);
    const [isTyping, setIsTyping] = (0, react_1.useState)(false);
    const [isEscalated, setIsEscalated] = (0, react_1.useState)(false);
    (0, react_1.useEffect)(() => {
        const unsubMsg = client.on('message', (msg) => {
            setMessages([...client.history]);
        });
        const unsubTyping = client.on('typing', (typing) => {
            setIsTyping(typing);
        });
        const unsubEscalate = client.on('escalate', () => {
            setIsEscalated(true);
        });
        client.authenticate();
        return () => {
            unsubMsg();
            unsubTyping();
            unsubEscalate();
            client.destroy();
        };
    }, [client]);
    const sendMessage = async (text) => {
        return await client.sendMessage(text);
    };
    const seedTestData = async () => {
        return await client.seedTestData();
    };
    return (react_1.default.createElement(ChatContext.Provider, { value: {
            client,
            messages,
            isTyping,
            isEscalated,
            sendMessage,
            seedTestData
        } }, children));
};
exports.ChatProvider = ChatProvider;
const useChatContext = () => {
    const ctx = (0, react_1.useContext)(ChatContext);
    if (!ctx) {
        throw new Error('useChatContext must be used within a <ChatProvider>');
    }
    return ctx;
};
exports.useChatContext = useChatContext;
