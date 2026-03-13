const generateLabels = () => {
	return Array.from({ length: 250 }, (_, i) => `Day ${i + 1}`);
};

//generate random price trend
const generatePrices = (startPrice) => {
	let prices = [startPrice];

	for (let i = 1; i < 250; i++) {
		const change = (Math.random() - 0.5) * 10;
		prices.push(Math.max(1, prices[i - 1] + change));
	}

	return prices;
};

const generateSentiment = () => {
	let sentiment = [0];

	for (let i = 1; i < 250; i++) {
		const change = (Math.random() - 0.5) * 0.2;
		let newValue = sentiment[i - 1] + change;

		newValue = Math.max(-1, Math.min(1, newValue));

		sentiment.push(Number(newValue.toFixed(2)));
	}

	return sentiment;
};


export const stockData = [
	{
		name: "Apple",
		symbol: "AAPL",
		category: "stock",
		labels: generateLabels(),
		price: generatePrices(180),
		sentiment: generateSentiment()
	},
	{
		name: "Tesla",
		symbol: "TSLA",
		category: "stock",
		labels: generateLabels(),
		price: generatePrices(240),
		sentiment: generateSentiment()
	},
	{
		name: "Microsoft",
		symbol: "MSFT",
		category: "stock",
		labels: generateLabels(),
		price: generatePrices(330),
		sentiment: generateSentiment()
	},
	{
		name: "Amazon",
		symbol: "AMZN",
		category: "stock",
		labels: generateLabels(),
		price: generatePrices(150),
		sentiment: generateSentiment()
	},
	{
		name: "Nvidia",
		symbol: "NVDA",
		category: "stock",
		labels: generateLabels(),
		price: generatePrices(700),
		sentiment: generateSentiment()
	},
		{
		name: "Bitcoin",
		symbol: "BTC",
		category: "coin",
		labels: generateLabels(),
		price: generatePrices(62000),
		sentiment: generateSentiment()
	},
	{
		name: "Ethereum",
		symbol: "ETH",
		category: "coin",
		labels: generateLabels(),
		price: generatePrices(3200),
		sentiment: generateSentiment()
	},
	{
		name: "Solana",
		symbol: "SOL",
		category: "coin",
		labels: generateLabels(),
		price: generatePrices(150),
		sentiment: generateSentiment()
	},
	{
		name: "Cardano",
		symbol: "ADA",
		category: "coin",
		labels: generateLabels(),
		price: generatePrices(1.2),
		sentiment: generateSentiment()
	},
	{
		name: "Dogecoin",
		symbol: "DOGE",
		category: "coin",
		labels: generateLabels(),
		price: generatePrices(0.15),
		sentiment: generateSentiment()
	}
];

export const backtestData = [
	{name:"GameStop 2021"}, {name: "Elon Musk Tweets vs TSLA"}
];