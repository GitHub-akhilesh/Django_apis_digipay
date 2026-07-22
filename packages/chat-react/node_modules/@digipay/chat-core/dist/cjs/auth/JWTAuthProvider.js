"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.JWTAuthProvider = void 0;
class JWTAuthProvider {
    constructor(baseUrl, username, cscId, transport) {
        this.baseUrl = baseUrl;
        this.username = username;
        this.cscId = cscId;
        this.transport = transport;
        this.cachedToken = null;
    }
    async getToken() {
        if (this.cachedToken)
            return this.cachedToken;
        try {
            const res = await this.transport.send({
                url: `${this.baseUrl}/api/v1/auth/token`,
                method: 'POST',
                body: { username: this.username, cscId: this.cscId }
            });
            if (res.ok && res.data && res.data.access_token) {
                this.cachedToken = res.data.access_token;
                return this.cachedToken;
            }
        }
        catch (err) {
            console.warn('[JWTAuthProvider] Token fetch failed:', err);
        }
        return null;
    }
    async logout() {
        this.cachedToken = null;
    }
}
exports.JWTAuthProvider = JWTAuthProvider;
//# sourceMappingURL=JWTAuthProvider.js.map