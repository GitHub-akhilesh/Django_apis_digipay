/**
 * SessionManager service for handling chat sessions, token caching, and storage.
 */
import { ChatSession } from '../types';

export class SessionManager {
  private keyPrefix = 'digipay_session_';

  getOrCreateSession(cscId: string, customSessionId?: string): ChatSession {
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

  clearSession(cscId: string): void {
    const key = `${this.keyPrefix}${cscId}`;
    if (typeof localStorage !== 'undefined') {
      localStorage.removeItem(key);
    }
  }
}
