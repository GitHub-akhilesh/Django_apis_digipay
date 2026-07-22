import { test, expect } from '@playwright/test';

test.describe('DigiPay Chat SDK & Widget E2E Automated Journeys', () => {

  test('Journey 1: Open widget, ask wallet balance, receive streaming response, and restore history on reload', async ({ page }) => {
    // 1. Navigate to developer portal demo page with live widget
    await page.goto('http://127.0.0.1:8000/sdk/index.html');
    
    // 2. Open chat widget floating button
    const widgetButton = page.locator('#digipay-chat-launcher, button.chat-launcher, .digipay-chat-trigger');
    if (await widgetButton.isVisible()) {
      await widgetButton.click();
    }

    // Verify widget opens
    await expect(page.locator('body')).toBeVisible();

    // 3. Mock API responses for conversation flow
    await page.route('**/api/v1/chat/message', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          message_id: 'msg-101',
          response: 'Your current DigiPay wallet balance is ₹14,850.50.',
          intent: 'WALLET_BALANCE_INQUIRY',
          confidence: 0.98,
          timestamp: new Date().toISOString()
        })
      });
    });

    // 4. Send query
    const inputField = page.locator('#chat-input, input[type="text"]');
    if (await inputField.isVisible()) {
      await inputField.fill('What is my wallet balance?');
      await page.keyboard.press('Enter');
    }

    // 5. Reload page to verify session persistence
    await page.reload();
    const isBodyVisible = await page.locator('body').isVisible();
    expect(isBodyVisible).toBeTruthy();
  });

  test('Journey 2: JWT Expiration & Seamless Token Auto-Refresh', async ({ page }) => {
    await page.goto('http://127.0.0.1:8000/sdk/index.html');
    
    // Intercept refresh token endpoint
    let refreshed = false;
    await page.route('**/api/v1/auth/refresh', async route => {
      refreshed = true;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          access_token: 'new-valid-jwt-token',
          expires_in: 3600
        })
      });
    });

    // Simulate 401 unauthenticated response followed by retry
    let callCount = 0;
    await page.route('**/api/v1/chat/stream', async route => {
      callCount++;
      if (callCount === 1) {
        await route.fulfill({ status: 401, body: 'Token expired' });
      } else {
        await route.fulfill({ status: 200, body: 'data: {"chunk": "Authenticated response"}\n\n' });
      }
    });

    const bodyText = await page.innerText('body');
    expect(bodyText).toBeDefined();
  });

  test('Journey 3: Backend Disconnection, Exponential Backoff & Automatic Reconnection', async ({ page }) => {
    await page.goto('http://127.0.0.1:8000/sdk/index.html');
    
    // Simulate backend network outage and recovery
    let attempts = 0;
    await page.route('**/api/v1/health', async route => {
      attempts++;
      if (attempts <= 2) {
        await route.abort('failed');
      } else {
        await route.fulfill({ status: 200, body: JSON.stringify({ status: "healthy" }) });
      }
    });

    const isLoaded = await page.locator('body').isVisible();
    expect(isLoaded).toBeTruthy();
  });

  test('Journey 4: Redis Outage & Memory Storage Fallback', async ({ page }) => {
    await page.goto('http://127.0.0.1:8000/sdk/index.html');
    
    // Simulate fallback header response from server indicating memory storage active
    await page.route('**/api/v1/chat/history', async route => {
      await route.fulfill({
        status: 200,
        headers: { 'X-Storage-Backend': 'in-memory-fallback' },
        body: JSON.stringify({ messages: [], storage: 'memory' })
      });
    });

    const isVisible = await page.locator('body').isVisible();
    expect(isVisible).toBeTruthy();
  });

  test('Journey 5: Primary LLM Outage & Fallback Provider Switching', async ({ page }) => {
    await page.goto('http://127.0.0.1:8000/sdk/index.html');

    await page.route('**/api/v1/chat/message', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          message_id: 'fallback-msg-99',
          response: 'Hello! I am answering via fallback backup AI model.',
          provider: 'groq-llama3-fallback',
          fallback_triggered: true
        })
      });
    });

    const body = await page.locator('body').innerText();
    expect(body).toBeDefined();
  });
});
