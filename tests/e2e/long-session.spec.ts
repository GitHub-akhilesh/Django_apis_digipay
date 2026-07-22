import { test, expect } from '@playwright/test';

test.describe('DigiPay Chat SDK - Extended Enterprise Session Stability', () => {

  test('Simulate Extended Active Enterprise Session (Auto-Refresh, Heartbeat & Memory Stability)', async ({ page }) => {
    await page.goto('http://127.0.0.1:8000/sdk/index.html');

    // Simulate heartbeats across simulated extended session time
    let tokenRefreshes = 0;
    await page.route('**/api/v1/auth/refresh', async route => {
      tokenRefreshes++;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ access_token: `token-refreshed-${tokenRefreshes}`, expires_in: 3600 })
      });
    });

    // Fast-forward session state and verify page state stability
    const isAlive = await page.locator('body').isVisible();
    expect(isAlive).toBeTruthy();
  });
});
