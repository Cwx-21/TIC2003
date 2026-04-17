import { test, expect } from "@playwright/test";

test.describe("Search Bar function", () => {
	test("input field contains value", async ({ page }) => {
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

		await page.getByTestId("asset-search").fill("BTC");

		await expect(page.getByTestId("asset-card")).toHaveCount(1);
		await expect(page.getByText("Bitcoin (BTC)")).toBeVisible();
	});

	test("search value is empty", async ({ page }) => {
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
						{ symbol: "AAPL", name: "Apple" },
					],
				}),
			});
		});

		await page.goto("/");

		await page.getByTestId("asset-search").fill("BTC");
		await page.getByTestId("asset-search").clear();

		await expect(page.getByTestId("asset-card")).toHaveCount(5);
		await expect(page.getByText("Apple (AAPL)")).toHaveCount(0);
	});
});