"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.LocalStorageAdapter = exports.MemoryStorageAdapter = void 0;
class MemoryStorageAdapter {
    constructor() {
        this.store = new Map();
    }
    getItem(key) {
        return this.store.get(key) || null;
    }
    setItem(key, value) {
        this.store.set(key, value);
    }
    removeItem(key) {
        this.store.delete(key);
    }
}
exports.MemoryStorageAdapter = MemoryStorageAdapter;
class LocalStorageAdapter {
    constructor() {
        this.fallback = new MemoryStorageAdapter();
    }
    isAvailable() {
        return typeof localStorage !== 'undefined';
    }
    getItem(key) {
        if (this.isAvailable()) {
            return localStorage.getItem(key);
        }
        return this.fallback.getItem(key);
    }
    setItem(key, value) {
        if (this.isAvailable()) {
            localStorage.setItem(key, value);
        }
        else {
            this.fallback.setItem(key, value);
        }
    }
    removeItem(key) {
        if (this.isAvailable()) {
            localStorage.removeItem(key);
        }
        else {
            this.fallback.removeItem(key);
        }
    }
}
exports.LocalStorageAdapter = LocalStorageAdapter;
//# sourceMappingURL=LocalStorageAdapter.js.map