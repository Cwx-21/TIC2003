import "chart.js/auto";
import { Line } from "react-chartjs-2";

function Chart({ selectedAsset, priceData, sentimentData, onBack }) {

	//dates from priceData
	const labels = priceData.map((item) => item.event_date).reverse();

    const data = {
		labels,
		datasets: [
			{
				label: "Price",
				data: priceData.map((item) => item.price_close).reverse(),
				borderColor: "blue",
				backgroundColor: "blue",
				yAxisID: "priceAxis",
				pointRadius: 0,
			},
			{
				label: "Sentiment",
				data: sentimentData.map((item) => item.weighted_avg_sentiment).reverse(),
				borderColor: "green",
				backgroundColor: "green",
				yAxisID: "sentimentAxis",
				pointRadius: 0,
			},
		],
	};

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
				min: -1,
				max: 1,
				grid: {
					drawOnChartArea: false,
				},
			},
		},
	};
    
    return (
		<div className="card">
			<div className="chart-header">
				<h2>Showing chart for {selectedAsset}</h2>
				<button className="back-button" onClick={onBack}> Back </button>
			</div>

			{priceData.length > 0 && sentimentData.length > 0 ?
				(<Line data={data} options={options} />) :
				(<p>No data for this asset</p>)
			}
		</div>
	);
}

export default Chart;