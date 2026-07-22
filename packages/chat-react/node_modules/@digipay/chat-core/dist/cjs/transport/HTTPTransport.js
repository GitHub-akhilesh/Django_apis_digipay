"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.HTTPTransport = void 0;
class HTTPTransport {
    async connect() {
        // HTTP is stateless, connection ready immediately
        return Promise.resolve();
    }
    async disconnect() {
        return Promise.resolve();
    }
    async send(req) {
        const headers = {
            'Content-Type': 'application/json',
            ...(req.headers || {})
        };
        const config = {
            method: req.method || 'POST',
            headers
        };
        if (req.body && req.method !== 'GET') {
            config.body = typeof req.body === 'string' ? req.body : JSON.stringify(req.body);
        }
        const response = await fetch(req.url, config);
        const data = await response.json();
        return {
            status: response.status,
            ok: response.ok,
            data
        };
    }
}
exports.HTTPTransport = HTTPTransport;
//# sourceMappingURL=HTTPTransport.js.map