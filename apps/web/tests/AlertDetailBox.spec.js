import { test, expect } from "@playwright/test";

const mockAssets = [{ name: "Bitcoin", symbol: "BTC" }];

const mockCorrelationData = [
  {
    time_bucket: "2026-04-16T00:00:00.000Z",
    price_at_bucket: 85000,
    weighted_sentiment: 0.4,
    sentiment_price_divergence: 0.1,
  },
];

const mockComments = [
  {
    id: 1,
    content: "Strong momentum today",
    sentiment_score: 0.92,
    url: "https://example.com/post",
  },
];

const mockAlerts = [
  {
    id: 1,
    asset_symbol: "BTC",
    alert_type: "price divergence",
    severity: "warning",
    message: "BTC diverged from weighted sentiment.",
    event_timestamp: "2026-04-17T10:00:00.000Z",
    details: {
      divergence: 0.1234,
      price_close: 84500,
      price_change_pct: -3.45,
      weighted_sentiment: 0.8421,
      message_volume: 123,
    },
  },
];

async function mockAppApis(page) {
  await page.route("**/api/assets", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ data: mockAssets }),
    });
  });

  await page.route("**/api/backtests", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ data: [{ id: "bt-123" }] }),
    });
  });

  await page.route("**/api/sessions?status=running", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ data: [{ id: "session-777" }] }),
    });
  });

  await page.route("**/api/correlation/BTC**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ data: mockCorrelationData }),
    });
  });

  await page.route("**/api/sentiment/BTC/logs**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ data: mockComments }),
    });
  });

  await page.route("**/api/alerts**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ data: mockAlerts }),
    });
  });
}

async function openAlertsSection(page) {
  await mockAppApis(page);
  await page.goto("/");
  await page.getByText("Bitcoin (BTC)").click();

  const alertsSection = page.locator(".container").filter({
    has: page.getByRole("heading", { name: "Price Warning Alerts" }),
  });

  await expect(
    page.getByRole("heading", { name: "Price Warning Alerts" }),
  ).toBeVisible();
  return alertsSection;
}

test.describe("AlertDetailBox via Alerts", () => {
  test("renders title and content", async ({ page }) => {
    const alertsSection = await openAlertsSection(page);

    const weightedSentimentBox = alertsSection.locator(".details-box").filter({
      has: page.locator(".details-label", { hasText: "Weighted Sentiment" }),
    });

    await expect(weightedSentimentBox.locator(".details-label")).toHaveText(
      "Weighted Sentiment",
    );
    await expect(weightedSentimentBox.locator(".details-value")).toHaveText(
      "0.8421",
    );
  });

  test("applies styling class to value", async ({ page }) => {
    const alertsSection = await openAlertsSection(page);

    const priceChangeBox = alertsSection.locator(".details-box").filter({
      has: page.locator(".details-label", { hasText: "Price Change %" }),
    });

    await expect(priceChangeBox.locator(".details-value")).toHaveClass(
      /negative/,
    );
  });
});
