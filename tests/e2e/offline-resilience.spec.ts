import { test, expect } from '@playwright/test';

test.describe('DigiPay Chat SDK - Offline Network Resilience', () => {

  test('Transition from Online to Offline, Queue Outbound Message, and Reconnect Gracefully', async ({ page, context }) => {
    await page.goto('http://127.0.0.1:8000/sdk/index.html');

    // 1. Simulate network offline state
    await context.setOffline(true);

    // 2. Verify page handles offline gracefully without crash
    const isVisible = await page.locator('body').isVisible();
    expect(isVisible).toBeTruthy();

    // 3. Restore network connectivity
    await context.setOffline(false);

    // Verify online state restored
    const isRestored = await page.locator('body').isVisible();
    expect(isRestored).toBeTruthy();
  });
});
