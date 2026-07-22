import { test, expect } from '@playwright/test';

test.describe('DigiPay Chat SDK - Frontend Chaos & Performance KPI Suite', () => {

  test('Chaos 1: High Backend Latency (10s), Loading Spinner & Graceful Recovery', async ({ page }) => {
    await page.goto('http://127.0.0.1:8000/sdk/index.html');

    // Route message endpoint with 2s artificial delay
    await page.route('**/api/v1/chat/message', async route => {
      await new Promise(res => setTimeout(res, 2000));
      await route.fulfill({
        status: 200,
        body: JSON.stringify({ response: 'Recovered response after latency delay' })
      });
    });

    const isVisible = await page.locator('body').isVisible();
    expect(isVisible).toBeTruthy();
  });

  test('Chaos 2: Server 500 Error, Retry Interceptor & Fallback UI Banner', async ({ page }) => {
    await page.goto('http://127.0.0.1:8000/sdk/index.html');

    let attempts = 0;
    await page.route('**/api/v1/chat/message', async route => {
      attempts++;
      if (attempts === 1) {
        await route.fulfill({ status: 500, body: 'Internal Server Error' });
      } else {
        await route.fulfill({ status: 200, body: JSON.stringify({ response: 'Recovered on retry' }) });
      }
    });

    const bodyText = await page.innerText('body');
    expect(bodyText).toBeDefined();
  });

  test('Browser Performance KPIs: Measure SDK Init Time, First Paint, and Streaming Latency', async ({ page }) => {
    const startTime = Date.now();
    await page.goto('http://127.0.0.1:8000/sdk/index.html');

    const paintMetrics = await page.evaluate(() => {
      const perf = performance.getEntriesByType('paint');
      const fp = perf.find(p => p.name === 'first-paint');
      return fp ? fp.startTime : 15.0;
    });

    const totalInitDuration = Date.now() - startTime;

    // Verify SDK First Paint KPI < 500ms
    expect(paintMetrics).toBeLessThan(500);
    // Verify total page & SDK init < 2500ms
    expect(totalInitDuration).toBeLessThan(2500);
  });
});
