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
exports.DigiPayChatWidget = void 0;
const react_1 = __importStar(require("react"));
const ChatContext_1 = require("../context/ChatContext");
const useChat_1 = require("../hooks/useChat");
const InnerWidget = ({ mode }) => {
    const [isOpen, setIsOpen] = (0, react_1.useState)(mode !== 'floating');
    const [input, setInput] = (0, react_1.useState)('');
    const messages = (0, useChat_1.useMessages)();
    const { sendMessage, seedTestData, isTyping, isEscalated } = (0, useChat_1.useChat)();
    const handleSend = async (e) => {
        if (e)
            e.preventDefault();
        if (!input.trim())
            return;
        const text = input;
        setInput('');
        await sendMessage(text);
    };
    if (mode === 'floating' && !isOpen) {
        return (react_1.default.createElement("button", { onClick: () => setIsOpen(true), style: {
                position: 'fixed',
                bottom: 24,
                right: 24,
                width: 60,
                height: 60,
                borderRadius: '50%',
                background: '#2563eb',
                color: '#fff',
                border: 'none',
                cursor: 'pointer',
                boxShadow: '0 8px 24px rgba(37,99,235,0.4)',
                fontSize: 24,
                zIndex: 99999
            } }, "\uD83D\uDCAC"));
    }
    return (react_1.default.createElement("div", { style: {
            width: mode === 'inline' ? '100%' : 380,
            height: mode === 'sidebar' ? '100vh' : 560,
            background: '#0f172a',
            color: '#f8fafc',
            borderRadius: mode === 'inline' ? 12 : 20,
            display: 'flex',
            flexDirection: 'column',
            boxShadow: mode === 'floating' ? '0 20px 50px rgba(0,0,0,0.5)' : 'none',
            border: '1px solid rgba(255,255,255,0.1)',
            position: mode === 'floating' ? 'fixed' : 'relative',
            bottom: mode === 'floating' ? 96 : undefined,
            right: mode === 'floating' ? 24 : undefined,
            zIndex: 99998
        } },
        react_1.default.createElement("div", { style: { padding: '16px 20px', background: '#1e293b', display: 'flex', justifyContent: 'space-between', alignItems: 'center' } },
            react_1.default.createElement("h4", { style: { margin: 0, fontSize: 16 } }, "DigiPay AI Assistant"),
            mode === 'floating' && (react_1.default.createElement("button", { onClick: () => setIsOpen(false), style: { background: 'transparent', border: 'none', color: '#94a3b8', fontSize: 20, cursor: 'pointer' } }, "\u00D7"))),
        react_1.default.createElement("div", { style: { flex: 1, padding: 16, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 12 } },
            messages.map((m, i) => (react_1.default.createElement("div", { key: i, style: {
                    alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start',
                    background: m.role === 'user' ? '#2563eb' : '#1e293b',
                    color: '#fff',
                    padding: '10px 14px',
                    borderRadius: 12,
                    maxWidth: '85%',
                    fontSize: 14
                } },
                m.content,
                m.escalate && react_1.default.createElement("div", { style: { fontSize: 11, color: '#fdba74', marginTop: 4 } }, "\u26A0\uFE0F Escalated to Support")))),
            isTyping && react_1.default.createElement("div", { style: { fontSize: 12, color: '#94a3b8' } }, "Assistant is typing..."),
            isEscalated && react_1.default.createElement("div", { style: { fontSize: 12, color: '#fb923c' } }, "Human agent notified.")),
        react_1.default.createElement("form", { onSubmit: handleSend, style: { padding: 12, background: '#0f172a', display: 'flex', gap: 8, borderTop: '1px solid rgba(255,255,255,0.1)' } },
            react_1.default.createElement("input", { value: input, onChange: (e) => setInput(e.target.value), placeholder: "Ask a question...", style: { flex: 1, background: '#1e293b', border: '1px solid rgba(255,255,255,0.1)', color: '#fff', borderRadius: 8, padding: '8px 12px', fontSize: 14 } }),
            react_1.default.createElement("button", { type: "submit", style: { background: '#2563eb', color: '#fff', border: 'none', borderRadius: 8, padding: '8px 16px', cursor: 'pointer' } }, "Send"))));
};
const DigiPayChatWidget = ({ cscId = '500100100014', baseUrl = 'http://127.0.0.1:8000', username = 'merchant_admin', mode = 'floating' }) => {
    return (react_1.default.createElement(ChatContext_1.ChatProvider, { cscId: cscId, baseUrl: baseUrl, username: username },
        react_1.default.createElement(InnerWidget, { mode: mode })));
};
exports.DigiPayChatWidget = DigiPayChatWidget;
