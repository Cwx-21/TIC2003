import { test, expect } from "@playwright/test";

test.describe("Sentiment Table", () => {
	test("no asset is selected", async ({ page }) => {
		await page.route("**/api/assets", async (route) => {
			await route.fulfill({
				status: 200,
				contentType: "application/json",
				body: JSON.stringify({
					data: [{ symbol: "BTC", name: "Bitcoin" }],
				}),
			});
		});

		await page.goto("/");

		await expect(page.getByTestId("sentiment-table")).toHaveCount(0);
	});

	test("error contains a message", async ({ page }) => {
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
					data: [],
				}),
			});
		});

		await page.route("**/api/sentiment/BTC/logs?backtest_id=1", async (route) => {
			await route.fulfill({
				status: 500,
				contentType: "application/json",
				body: JSON.stringify({
					error: "Failed to load comments",
				}),
			});
		});

		await page.goto("/");

		await page.getByTestId("asset-card").first().click();

		await expect(page.getByTestId("error-message")).toBeVisible();
		await expect(page.getByTestId("error-message")).toContainText("Failed to load comments");
	});

	test("comments with URL values", async ({ page }) => {
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
					data: [],
				}),
			});
		});

		await page.route("**/api/sentiment/BTC/logs?backtest_id=1", async (route) => {
			await route.fulfill({
				status: 200,
				contentType: "application/json",
				body: JSON.stringify({
					data: [
						{
							id: 1,
							content: "BTC looks strong today",
							sentiment_score: 0.8,
							url: "https://example.com/post1",
						},
						{
							id: 2,
							content: "Momentum is building",
							sentiment_score: 0.6,
							url: "https://example.com/post2",
						},
					],
				}),
			});
		});

		await page.goto("/");

		await page.getByTestId("asset-card").first().click();

		await expect(page.getByTestId("sentiment-table")).toBeVisible();
		await expect(page.getByTestId("sentiment-table").locator("a")).toHaveCount(2);
	});

	test("comments without URL values", async ({ page }) => {
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
					data: [],
				}),
			});
		});

		await page.route("**/api/sentiment/BTC/logs?backtest_id=1", async (route) => {
			await route.fulfill({
				status: 200,
				contentType: "application/json",
				body: JSON.stringify({
					data: [
						{
							id: 1,
							content: "This should not appear",
							sentiment_score: 0.2,
						},
					],
				}),
			});
		});

		await page.goto("/");

		await page.getByTestId("asset-card").first().click();

		await expect(page.getByTestId("sentiment-table")).toHaveCount(0);
		await expect(page.getByTestId("no-comments-message")).toBeVisible();
	});

	test("no comments tied to the asset", async ({ page }) => {
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
					data: [],
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

		await expect(page.getByTestId("no-comments-message")).toBeVisible();
	});

	test("comments contains valid linked comments", async ({ page }) => {
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
					data: [],
				}),
			});
		});

		await page.route("**/api/sentiment/BTC/logs?backtest_id=1", async (route) => {
			await route.fulfill({
				status: 200,
				contentType: "application/json",
				body: JSON.stringify({
					data: [
						{
							id: 1,
							content: "BTC looks strong today",
							sentiment_score: 0.8,
							url: "https://example.com/post1",
						},
					],
				}),
			});
		});

		await page.goto("/");

		await page.getByTestId("asset-card").first().click();

		await expect(page.getByTestId("sentiment-table").locator("a").first()).toBeVisible();
	});
});