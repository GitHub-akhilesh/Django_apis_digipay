/**
 * HTTP Transport Implementation using fetch API
 */
import { Transport, TransportRequest, TransportResponse } from './Transport';

export class HTTPTransport implements Transport {
  async connect(): Promise<void> {
    // HTTP is stateless, connection ready immediately
    return Promise.resolve();
  }

  async disconnect(): Promise<void> {
    return Promise.resolve();
  }

  async send<T = any>(req: TransportRequest): Promise<TransportResponse<T>> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(req.headers || {})
    };

    const config: RequestInit = {
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
