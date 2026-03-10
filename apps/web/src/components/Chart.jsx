import "chart.js/auto";
import { Line } from "react-chartjs-2";
import { stockData } from "../data/mockData";

function Chart({ stockName, onBack }) {

    const currentStock = stockData[stockName];

    const data = currentStock ? {
        labels: currentStock.labels,
        datasets: [
            {
                label: "Price",
                data: currentStock.price,
                borderColor: "blue",
                yAxisID: "priceAxis"
            },
            {
                label: "Sentiment",
                data: currentStock.sentiment,
                borderColor: "red",
                yAxisID: "sentimentAxis"
            }
        ]
    } : null;

    const options = {
		responsive: true,
		scales: {
			priceAxis: {
				type: "linear",
				position: "left",
			},
			sentimentAxis: {
				type: "linear",
				position: "right",
				grid: {
					drawOnChartArea: false,
				},
			},
		},
	};
    
    return (
		<div className="card">
			<div className="chart-header">
				<h2>
					{currentStock
						? `Showing chart for ${stockName}`
						: `No data found for ${stockName}`}
				</h2>
				<button className="back-button" onClick={onBack}>
					Back
				</button>
			</div>

			{currentStock && <Line data={data} options={options} />}
		</div>
	);
}

export default Chart;