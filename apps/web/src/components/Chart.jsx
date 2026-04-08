import "chart.js/auto";
import { Line } from "react-chartjs-2";
import zoomPlugin from "chartjs-plugin-zoom";
import { Chart as ChartJS } from "chart.js";
import DateRangeSelector from "./DateRangeSelector";

ChartJS.register(zoomPlugin);

function Chart({
  selectedAsset,
  correlationData,
  loading,
  mode,
  startDate,
  endDate,
  setStartDate,
  setEndDate,
}) {
  const rows = [...correlationData].reverse();
  const labels = rows.map((r) => r.time_bucket.slice(0, 10));

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
        data: sentimentData
          .map((item) => item.weighted_avg_sentiment)
          .reverse(),
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
    <div className='container'>
      <div className='header'>
        <h2>Showing chart for {selectedAsset}</h2>
        <DateRangeSelector
          startDate={startDate}
          endDate={endDate}
          setStartDate={setStartDate}
          setEndDate={setEndDate}
        />
      </div>

      {priceData.length > 0 && sentimentData.length > 0 ? (
        <Line data={data} options={options} />
      ) : (
        <p>No data for this asset</p>
      )}
      {!loading && correlationData.length === 0 && (
        <div className="alert-empty">{emptyMessage}</div>
      )}
    </div>
  );
}

export default Chart;
