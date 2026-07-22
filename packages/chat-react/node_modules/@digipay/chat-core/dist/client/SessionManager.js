"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.SessionManager = void 0;
class SessionManager {
    constructor() {
        this.keyPrefix = 'digipay_session_';
    }
    getOrCreateSession(cscId, customSessionId) {
        if (customSessionId) {
            return { sessionId: customSessionId, cscId, createdAt: new Date() };
        }
        const key = `${this.keyPrefix}${cscId}`;
        let sid = typeof localStorage !== 'undefined' ? localStorage.getItem(key) : null;
        if (!sid) {
            sid = `sess_${Math.random().toString(36).substring(2, 11)}_${Date.now()}`;
            if (typeof localStorage !== 'undefined') {
                localStorage.setItem(key, sid);
            }
        }
        return { sessionId: sid, cscId, createdAt: new Date() };
    }
    clearSession(cscId) {
        const key = `${this.keyPrefix}${cscId}`;
        if (typeof localStorage !== 'undefined') {
            localStorage.removeItem(key);
        }
    }
}
exports.SessionManager = SessionManager;
