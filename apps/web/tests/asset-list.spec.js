import { test, expect } from "@playwright/test";

test.describe("Asset List feature", () => {
	test("asset list contains items", async ({ page }) => {
		await page.route("**/api/assets", async (route) => {
			await route.fulfill({
				status: 200,
				contentType: "application/json",
				body: JSON.stringify({
					data: [
						{ symbol: "BTC", name: "Bitcoin" },
						{ symbol: "ETH", name: "Ethereum" },
						{ symbol: "DOGE", name: "Dogecoin" },
						{ symbol: "GME", name: "GameStop" },
						{ symbol: "TSLA", name: "Tesla" },
					],
				}),
			});
		});

		await page.goto("/");

		await expect(page.getByTestId("asset-list")).toBeVisible();
		await expect(page.getByTestId("asset-card")).toHaveCount(5);
	});

	test("asset list is empty", async ({ page }) => {
		await page.route("**/api/assets", async (route) => {
			await route.fulfill({
				status: 200,
				contentType: "application/json",
				body: JSON.stringify({
					data: [],
				}),
			});
		});

		await page.goto("/");

		await expect(page.getByTestId("asset-list")).toBeVisible();
		await expect(page.getByTestId("asset-card")).toHaveCount(0);
	});

	test("user clicks an asset card", async ({ page }) => {
		await page.route("**/api/assets", async (route) => {
			await route.fulfill({
				status: 200,
				contentType: "application/json",
				body: JSON.stringify({
					data: [{ symbol: "BTC", name: "Bitcoin" }],
				}),
			});
		});

		await page.route("**/api/backtests/latest", async (route) => {
			await route.fulfill({
				status: 200,
				contentType: "application/json",
				body: JSON.stringify({
					data: { id: 1 },
				}),
			});
		});

		await page.route("**/api/live-sessions/latest", async (route) => {
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
							weighted_sentiment: 0.4,
							sentiment_price_divergence: 0.1,
						},
					],
				}),
			});
		});

		await page.route("**/api/sentiment/BTC/logs?backtest_id=1", async (route) => {
			await route.fulfill({
				status: 200,
				contentType: "application/json",
				body: JSON.stringify({
					data: [],
				}),
			});
		});

		await page.goto("/");

		await page.getByTestId("asset-card").first().click();

		await expect(page.getByTestId("correlation-chart")).toBeVisible();
	});
});