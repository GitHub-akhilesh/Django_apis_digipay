"use strict";
/**
 * Typed Event Emitter for DigiPay Chat Core SDK (Phase 3)
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.TypedEventEmitter = void 0;
class TypedEventEmitter {
    constructor() {
        this.listeners = new Map();
    }
    on(event, callback) {
        if (!this.listeners.has(event)) {
            this.listeners.set(event, []);
        }
        this.listeners.get(event).push(callback);
        // Return unsubscribe function
        return () => this.off(event, callback);
    }
    off(event, callback) {
        const list = this.listeners.get(event);
        if (list) {
            this.listeners.set(event, list.filter(cb => cb !== callback));
        }
    }
    emit(event, data) {
        const list = this.listeners.get(event);
        if (list) {
            list.forEach(cb => cb(data));
        }
    }
}
exports.TypedEventEmitter = TypedEventEmitter;
//# sourceMappingURL=EventEmitter.js.map