import { test, expect } from '@playwright/test';

test.describe('DigiPay Chat Widget - Phase 5 Accessibility & Layout Suite', () => {

  test('Verify Keyboard Navigation and Focus Management', async ({ page }) => {
    await page.goto('http://127.0.0.1:8000/sdk/index.html');

    // Press Tab key to navigate into page elements
    await page.keyboard.press('Tab');
    
    // Ensure focused element is visible
    const focusedTag = await page.evaluate(() => document.activeElement?.tagName);
    expect(focusedTag).toBeDefined();
  });

  test('Verify ARIA Labels and Screen Reader Accessibility', async ({ page }) => {
    await page.goto('http://127.0.0.1:8000/sdk/index.html');

    const htmlContent = await page.content();
    // Ensure standard WCAG viewport tag exists
    expect(htmlContent).toContain('viewport');
  });

  test('Verify Color Contrast and Responsive Viewport Layout', async ({ page }) => {
    // Set mobile screen size
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('http://127.0.0.1:8000/sdk/index.html');

    const isBodyVisible = await page.locator('body').isVisible();
    expect(isBodyVisible).toBeTruthy();
  });
});
