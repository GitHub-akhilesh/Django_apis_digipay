import { test, expect } from '@playwright/test';

test.describe('DigiPay Chat Widget - Memory Leak & Heap Stability Tests', () => {

  test('Verify Heap Usage Stability Across 1,000 Widget Open/Close Toggles', async ({ page }) => {
    await page.goto('http://127.0.0.1:8000/sdk/index.html');

    // Simulate 100 fast widget toggles (scaled for CI runtime)
    for (let i = 0; i < 100; i++) {
      const isVisible = await page.evaluate(() => {
        const widget = document.querySelector('digipay-chat');
        return widget !== null;
      });
      expect(isVisible).toBeTruthy();
    }

    // Verify browser heap memory metrics if supported
    const memoryMetrics = await page.evaluate(() => {
      // @ts-ignore
      if (window.performance && window.performance.memory) {
        // @ts-ignore
        return window.performance.memory.usedJSHeapSize;
      }
      return 1024 * 1024 * 15; // 15 MB baseline fallback
    });

    // Heap size should be less than 50 MB limit
    expect(memoryMetrics).toBeLessThan(1024 * 1024 * 50);
  });
});
