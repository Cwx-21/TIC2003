import "chart.js/auto";
import { Line } from "react-chartjs-2";

function Chart({ stock, onBack }) {

    const data = stock ? {
        labels: stock.labels,
        datasets: [
            {
                label: "Price",
                data: stock.price,
				borderColor: "blue",
				backgroundColor:"blue",
				yAxisID: "priceAxis",
				pointRadius: 0
            },
            {
                label: "Sentiment",
                data: stock.sentiment,
				borderColor: "green",
				backgroundColor:"green",
				yAxisID: "sentimentAxis",
				pointRadius: 0
            },
        ],
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
				<h2> {stock ? `Showing chart for ${stock.symbol}` : `No data found for ${stock.name}`} </h2>
				<button className="back-button" onClick={onBack}> Back </button>
			</div>

			{stock ? (<Line data={data} options={options} />) : <p>No data for this stock</p>}
		</div>
	);
}

export default Chart;