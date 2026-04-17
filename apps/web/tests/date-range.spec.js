import { test, expect } from "@playwright/test";

test.describe("Date Range Filtering", () => {
	test("a preset value is selected", async ({ page }) => {
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
							time_bucket: "2025-04-01T00:00:00Z",
							price_at_bucket: 50000,
							weighted_sentiment: 0.10,
							sentiment_price_divergence: 0.05,
						},
						{
							time_bucket: "2026-04-01T00:00:00Z",
							price_at_bucket: 65000,
							weighted_sentiment: 0.40,
							sentiment_price_divergence: 0.20,
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

		await expect(page.getByTestId("correlation-chart")).toBeVisible();

		await page.getByTestId("preset-select").selectOption("1y");

		await expect(page.getByTestId("preset-select")).toHaveValue("1y");
		await expect(page.getByTestId("date-start")).toHaveValue("2025-04-01");
		await expect(page.getByTestId("date-end")).toHaveValue("2026-04-01");
	});

	test("user changes start date", async ({ page }) => {
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
							weighted_sentiment: 0.40,
							sentiment_price_divergence: 0.10,
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

		await expect(page.getByTestId("correlation-chart")).toBeVisible();

		await page.getByTestId("date-start").fill("2026-01-01");

		await expect(page.getByTestId("date-start")).toHaveValue("2026-01-01");
	});

	test("user changes end date", async ({ page }) => {
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
							weighted_sentiment: 0.40,
							sentiment_price_divergence: 0.10,
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

		await expect(page.getByTestId("correlation-chart")).toBeVisible();

		await page.getByTestId("date-end").fill("2026-04-01");

		await expect(page.getByTestId("date-end")).toHaveValue("2026-04-01");
	});

	test("user clicks clear", async ({ page }) => {
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
							time_bucket: "2025-04-01T00:00:00Z",
							price_at_bucket: 50000,
							weighted_sentiment: 0.10,
							sentiment_price_divergence: 0.05,
						},
						{
							time_bucket: "2026-04-01T00:00:00Z",
							price_at_bucket: 65000,
							weighted_sentiment: 0.40,
							sentiment_price_divergence: 0.20,
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

		await expect(page.getByTestId("correlation-chart")).toBeVisible();

		await page.getByTestId("preset-select").selectOption("1y");
		await expect(page.getByTestId("date-start")).toHaveValue("2025-04-01");
		await expect(page.getByTestId("date-end")).toHaveValue("2026-04-01");

		await page.getByTestId("date-clear").click();

		await expect(page.getByTestId("preset-select")).toHaveValue("all");
		await expect(page.getByTestId("date-start")).toHaveValue("");
		await expect(page.getByTestId("date-end")).toHaveValue("");
	});
});