import { test, expect } from "@playwright/test";

test.describe("Chart feature", () => {
	test("chart renders for BTC when data exists", async ({ page }) => {
		await page.route("**/api/assets", async (route) => {
			await route.fulfill({
				status: 200,
				contentType: "application/json",
				body: JSON.stringify({
					data: [{ symbol: "BTC", name: "Bitcoin" }],
				}),
			});
		});

		await page.route("**/api/backtests/latest**", async (route) => {
			await route.fulfill({
				status: 200,
				contentType: "application/json",
				body: JSON.stringify({
					data: { id: 1 },
				}),
			});
		});

		await page.route("**/api/live-sessions/latest**", async (route) => {
			await route.fulfill({
				status: 200,
				contentType: "application/json",
				body: JSON.stringify({
					data: { id: 2 },
				}),
			});
		});

		await page.route("**/api/correlation/BTC**", async (route) => {
			await route.fulfill({
				status: 200,
				contentType: "application/json",
				body: JSON.stringify({
					data: [
						{
							time_bucket: "2026-04-01T00:00:00Z",
							price_at_bucket: 65000,
							weighted_sentiment: 0.42,
							sentiment_price_divergence: 0.10,
						},
						{
							time_bucket: "2026-04-02T00:00:00Z",
							price_at_bucket: 65500,
							weighted_sentiment: 0.35,
							sentiment_price_divergence: 0.08,
						},
						{
							time_bucket: "2026-04-03T00:00:00Z",
							price_at_bucket: 66000,
							weighted_sentiment: 0.50,
							sentiment_price_divergence: 0.12,
						},
					],
				}),
			});
		});

		await page.route("**/api/sentiment/BTC/logs**", async (route) => {
			await route.fulfill({
				status: 200,
				contentType: "application/json",
				body: JSON.stringify({
					data: [],
				}),
			});
		});

		await page.goto("/");
		await page.getByText("Bitcoin (BTC)").click();

		await expect(page.getByText("Showing chart for BTC")).toBeVisible();
		await expect(page.getByTestId("correlation-chart")).toBeVisible();

		const canvas = page.getByTestId("correlation-chart").locator("canvas");
		await expect(canvas).toBeVisible();
	});

	test("chart shows loading message while data is loading", async ({ page }) => {
		await page.route("**/api/assets", async (route) => {
			await route.fulfill({
				status: 200,
				contentType: "application/json",
				body: JSON.stringify({
					data: [{ symbol: "BTC", name: "Bitcoin" }],
				}),
			});
		});

		await page.route("**/api/backtests/latest**", async (route) => {
			await route.fulfill({
				status: 200,
				contentType: "application/json",
				body: JSON.stringify({
					data: { id: 1 },
				}),
			});
		});

		await page.route("**/api/live-sessions/latest**", async (route) => {
			await route.fulfill({
				status: 200,
				contentType: "application/json",
				body: JSON.stringify({
					data: { id: 2 },
				}),
			});
		});

		await page.route("**/api/correlation/BTC**", async (route) => {
			await new Promise((resolve) => setTimeout(resolve, 1200));
			await route.fulfill({
				status: 200,
				contentType: "application/json",
				body: JSON.stringify({
					data: [],
				}),
			});
		});

		await page.route("**/api/sentiment/BTC/logs**", async (route) => {
			await route.fulfill({
				status: 200,
				contentType: "application/json",
				body: JSON.stringify({
					data: [],
				}),
			});
		});

		await page.goto("/");
		await page.getByText("Bitcoin (BTC)").click();

		await expect(page.getByTestId("chart-loading")).toBeVisible();
	});

	test("chart shows empty message in backtest mode when no data exists", async ({ page }) => {
		await page.route("**/api/assets", async (route) => {
			await route.fulfill({
				status: 200,
				contentType: "application/json",
				body: JSON.stringify({
					data: [{ symbol: "BTC", name: "Bitcoin" }],
				}),
			});
		});

		await page.route("**/api/backtests/latest**", async (route) => {
			await route.fulfill({
				status: 200,
				contentType: "application/json",
				body: JSON.stringify({
					data: { id: 1 },
				}),
			});
		});

		await page.route("**/api/live-sessions/latest**", async (route) => {
			await route.fulfill({
				status: 200,
				contentType: "application/json",
				body: JSON.stringify({
					data: { id: 2 },
				}),
			});
		});

		await page.route("**/api/correlation/BTC**", async (route) => {
			await route.fulfill({
				status: 200,
				contentType: "application/json",
				body: JSON.stringify({
					data: [],
				}),
			});
		});

		await page.route("**/api/sentiment/BTC/logs**", async (route) => {
			await route.fulfill({
				status: 200,
				contentType: "application/json",
				body: JSON.stringify({
					data: [],
				}),
			});
		});

		await page.goto("/");
		await page.getByText("Bitcoin (BTC)").click();

		await expect(page.getByTestId("chart-empty")).toContainText("No data for this asset.");
	});

	test("chart shows empty message in live mode when no live data exists", async ({ page }) => {
		await page.route("**/api/assets", async (route) => {
			await route.fulfill({
				status: 200,
				contentType: "application/json",
				body: JSON.stringify({
					data: [{ symbol: "BTC", name: "Bitcoin" }],
				}),
			});
		});

		await page.route("**/api/backtests/latest**", async (route) => {
			await route.fulfill({
				status: 200,
				contentType: "application/json",
				body: JSON.stringify({
					data: { id: 1 },
				}),
			});
		});

		await page.route("**/api/live-sessions/latest**", async (route) => {
			await route.fulfill({
				status: 200,
				contentType: "application/json",
				body: JSON.stringify({
					data: { id: 2 },
				}),
			});
		});

		await page.route("**/api/correlation/BTC?backtest_id=1&interval=1d", async (route) => {
			await route.fulfill({
				status: 200,
				contentType: "application/json",
				body: JSON.stringify({
					data: [
						{
							time_bucket: "2026-04-01T00:00:00Z",
							price_at_bucket: 65000,
							weighted_sentiment: 0.42,
							sentiment_price_divergence: 0.10,
						},
					],
				}),
			});
		});

		await page.route("**/api/correlation/BTC?session_id=2", async (route) => {
			await route.fulfill({
				status: 200,
				contentType: "application/json",
				body: JSON.stringify({
					data: [],
				}),
			});
		});

		await page.route("**/api/sentiment/BTC/logs**", async (route) => {
			await route.fulfill({
				status: 200,
				contentType: "application/json",
				body: JSON.stringify({
					data: [],
				}),
			});
		});

		await page.goto("/");
		await page.getByText("Bitcoin (BTC)").click();
		await page.getByRole("button", { name: /live/i }).click();

		await expect(page.getByTestId("chart-empty")).toContainText("No live data yet");
	});
});