import { test, expect } from "@playwright/test";

function makeCorrelationData(count = 40) {
	return Array.from({ length: count }, (_, i) => {
		const date = new Date("2026-03-01T00:00:00Z");
		date.setUTCDate(date.getUTCDate() + i);

		return {
			time_bucket: date.toISOString(),
			price_at_bucket: 65000 + i * 150,
			weighted_sentiment: ((i % 10) - 5) / 10,
			sentiment_price_divergence: ((i % 6) - 3) / 20,
		};
	});
}

async function mockCommonRoutes(page) {
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

	await page.route("**/api/sentiment/BTC/logs**", async (route) => {
		await route.fulfill({
			status: 200,
			contentType: "application/json",
			body: JSON.stringify({
				data: [],
			}),
		});
	});
}

async function mockBacktestCorrelation(page, data) {
	await page.route("**/api/correlation/BTC?backtest_id=1&interval=1d", async (route) => {
		await route.fulfill({
			status: 200,
			contentType: "application/json",
			body: JSON.stringify({ data }),
		});
	});
}

async function mockLiveCorrelation(page, data) {
	await page.route("**/api/correlation/BTC?session_id=2", async (route) => {
		await route.fulfill({
			status: 200,
			contentType: "application/json",
			body: JSON.stringify({ data }),
		});
	});
}

test.describe("Chart feature", () => {

    test("loading exist", async ({ page }) => {
		await mockCommonRoutes(page);

		await page.route("**/api/correlation/BTC?backtest_id=1&interval=1d", async (route) => {
			await new Promise((resolve) => setTimeout(resolve, 2000));
			await route.fulfill({
				status: 200,
				contentType: "application/json",
				body: JSON.stringify({
					data: makeCorrelationData(12),
				}),
			});
		});

		await mockLiveCorrelation(page, []);

		await page.goto("/");
		await page.getByText("Bitcoin (BTC)").click();

		await expect(page.getByText("Loading...")).toBeVisible();
    });
    
	test("asset is selected", async ({ page }) => {
		await mockCommonRoutes(page);
		await mockBacktestCorrelation(page, makeCorrelationData(12));
		await mockLiveCorrelation(page, []);

		await page.goto("/");
		await page.getByText("Bitcoin (BTC)").click();

		await expect(page.getByText("Showing chart for BTC")).toBeVisible();

		const canvas = page.locator("canvas");
		await expect(canvas).toBeVisible();
	});

	test("correlation data is empty in backtest mode", async ({ page }) => {
		await mockCommonRoutes(page);
		await mockBacktestCorrelation(page, []);
		await mockLiveCorrelation(page, []);

		await page.goto("/");
		await page.getByText("Bitcoin (BTC)").click();

		await expect(page.getByText("No data for this asset.")).toBeVisible();
	});

	test("correlation data is empty in live mode", async ({ page }) => {
		await mockCommonRoutes(page);
		await mockBacktestCorrelation(page, makeCorrelationData(12));
		await mockLiveCorrelation(page, []);

		await page.goto("/");
		await page.getByText("Bitcoin (BTC)").click();
		await page.getByRole("button", { name: /live/i }).click();

		await expect(page.getByText(/No live data yet/i)).toBeVisible();
	});

	test("backtest and live mode toggle", async ({ page }) => {
		await mockCommonRoutes(page);
		await mockBacktestCorrelation(page, makeCorrelationData(12));
		await mockLiveCorrelation(page, makeCorrelationData(8));

		await page.goto("/");
		await page.getByText("Bitcoin (BTC)").click();

		await expect(page.getByText("Showing chart for BTC")).toBeVisible();
		await expect(page.locator("canvas")).toBeVisible();

		await page.getByRole("button", { name: /live/i }).click();

		await expect(page.getByText("Showing chart for BTC")).toBeVisible();
		await expect(page.locator("canvas")).toBeVisible();
	});

	test("chart zoom feature", async ({ page }) => {
		test.slow();

		await mockCommonRoutes(page);
		await mockBacktestCorrelation(page, makeCorrelationData(50));
		await mockLiveCorrelation(page, []);

		await page.goto("/");
		await page.getByText("Bitcoin (BTC)").click();

		const canvas = page.locator("canvas");
		await expect(canvas).toBeVisible();

		const box = await canvas.boundingBox();
		expect(box).not.toBeNull();

        await page.pause();

		await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
		await page.mouse.wheel(0, -900);

		await page.waitForTimeout(5000);
		await expect(canvas).toBeVisible();
	});

	test("chart pan feature", async ({ page }) => {
		test.slow();

		await mockCommonRoutes(page);
		await mockBacktestCorrelation(page, makeCorrelationData(60));
		await mockLiveCorrelation(page, []);

		await page.goto("/");
		await page.getByText("Bitcoin (BTC)").click();

		const canvas = page.locator("canvas");
		await expect(canvas).toBeVisible();

		const box = await canvas.boundingBox();
		expect(box).not.toBeNull();

		await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);

		await page.mouse.wheel(0, -900);
		await page.waitForTimeout(1500);

        await page.pause();

		const startX = box.x + box.width * 0.75;
		const endX = box.x + box.width * 0.35;
		const y = box.y + box.height * 0.5;

		await page.mouse.move(startX, y);
		await page.mouse.down();
		await page.mouse.move(endX, y, { steps: 20 });
		await page.mouse.up();

		await page.waitForTimeout(5000);
		await expect(canvas).toBeVisible();
	});
});