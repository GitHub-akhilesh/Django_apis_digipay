/**
 * JWT Auth Provider implementation for @digipay/chat-core
 */
import { AuthProvider } from './AuthProvider';
import { Transport } from '../transport/Transport';

export class JWTAuthProvider implements AuthProvider {
  private cachedToken: string | null = null;

  constructor(
    private baseUrl: string,
    private username: string,
    private cscId: string,
    private transport: Transport
  ) {}

  async getToken(): Promise<string | null> {
    if (this.cachedToken) return this.cachedToken;

    try {
      const res = await this.transport.send<{ access_token: string }>({
        url: `${this.baseUrl}/api/v1/auth/token`,
        method: 'POST',
        body: { username: this.username, cscId: this.cscId }
      });

      if (res.ok && res.data && res.data.access_token) {
        this.cachedToken = res.data.access_token;
        return this.cachedToken;
      }
    } catch (err) {
      console.warn('[JWTAuthProvider] Token fetch failed:', err);
    }
    return null;
  }

  async logout(): Promise<void> {
    this.cachedToken = null;
  }
}
