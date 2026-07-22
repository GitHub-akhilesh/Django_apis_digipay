/**
 * JWT Auth Provider implementation for @digipay/chat-core
 */
import { AuthProvider } from './AuthProvider';
import { Transport } from '../transport/Transport';
export declare class JWTAuthProvider implements AuthProvider {
    private baseUrl;
    private username;
    private cscId;
    private transport;
    private cachedToken;
    constructor(baseUrl: string, username: string, cscId: string, transport: Transport);
    getToken(): Promise<string | null>;
    logout(): Promise<void>;
}
//# sourceMappingURL=JWTAuthProvider.d.ts.map