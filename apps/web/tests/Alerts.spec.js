import { test, expect } from "@playwright/test";

const mockAssets = [
  { name: "Bitcoin", symbol: "BTC" },
  { name: "Ethereum", symbol: "ETH" },
];

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
      price_change_pct: -1.2345,
      weighted_sentiment: 0.8123,
      message_volume: 123,
    },
  },
  {
    id: 2,
    asset_symbol: "BTC",
    alert_type: "price spike",
    severity: "critical",
    message: "BTC price spiked rapidly.",
    event_timestamp: "2026-04-17T11:00:00.000Z",
    details: {
      divergence: 0.9876,
      price_close: 86000,
      price_change_pct: 4.321,
      weighted_sentiment: 0.9543,
      message_volume: 456,
    },
  },
  {
    id: 3,
    asset_symbol: "BTC",
    alert_type: "normal activity",
    severity: "info",
    message: "BTC is trading normally.",
    event_timestamp: "2026-04-17T09:00:00.000Z",
    details: {
      divergence: 0.0123,
      price_close: 84000,
      price_change_pct: 0.4567,
      weighted_sentiment: 0.4012,
      message_volume: 88,
    },
  },
];

async function mockAppApis(page, options = {}) {
  const {
    alertsStatus = 200,
    alertsData = mockAlerts,
    captureAlertUrls = null,
  } = options;

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
    if (captureAlertUrls) {
      captureAlertUrls.push(route.request().url());
    }

    await route.fulfill({
      status: alertsStatus,
      contentType: "application/json",
      body: JSON.stringify(
        alertsStatus >= 400
          ? { message: "Server error" }
          : { data: alertsData },
      ),
    });
  });
}

async function openAlertsSection(page, options = {}) {
  await mockAppApis(page, options);
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

test.describe("Alerts", () => {
  test("renders fetched alerts and sorts by severity", async ({ page }) => {
    const alertsSection = await openAlertsSection(page);

    await expect(alertsSection.locator(".card.alert")).toHaveCount(3);
    await expect(alertsSection.locator(".alert-pill")).toHaveText([
      "critical",
      "warning",
      "info",
    ]);
    await expect(
      alertsSection.getByText("BTC price spiked rapidly."),
    ).toBeVisible();
  });

  test("filters alerts by severity", async ({ page }) => {
    const alertsSection = await openAlertsSection(page);

    await alertsSection.locator("select").nth(0).selectOption("critical");

    await expect(alertsSection.locator(".card.alert")).toHaveCount(1);
    await expect(
      alertsSection.getByText("BTC price spiked rapidly."),
    ).toBeVisible();
    await expect(
      alertsSection.getByText("BTC diverged from weighted sentiment."),
    ).toHaveCount(0);
  });

  test("sends selected limit in the request query", async ({ page }) => {
    const alertRequestUrls = [];
    const alertsSection = await openAlertsSection(page, {
      captureAlertUrls: alertRequestUrls,
    });

    await alertsSection.locator("select").nth(1).selectOption("5");

    await expect
      .poll(() => {
        const lastUrl = alertRequestUrls[alertRequestUrls.length - 1];
        return lastUrl ? new URL(lastUrl).searchParams.get("limit") : null;
      })
      .toBe("5");
  });

  test("shows an empty state when the API returns no alerts", async ({
    page,
  }) => {
    const alertsSection = await openAlertsSection(page, {
      alertsData: [],
    });

    await expect(
      alertsSection.getByText("No alerts found for the selected filters."),
    ).toBeVisible();
  });

  test("shows an error state when the API fails", async ({ page }) => {
    const alertsSection = await openAlertsSection(page, {
      alertsStatus: 500,
    });

    await expect(
      alertsSection.getByText("Failed to load alerts"),
    ).toBeVisible();
  });
});
