/**
 * Authentication Provider Interface for @digipay/chat-core (Milestone A)
 */

export interface AuthProvider {
  getToken(): Promise<string | null>;
  refreshToken?(): Promise<string | null>;
  logout?(): Promise<void>;
}
