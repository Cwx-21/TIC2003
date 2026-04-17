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
  datePreset,
  handleDatePresetChange,
}) {
  const rows = [...correlationData].reverse();
  const labels = rows.map((r) => r.time_bucket.slice(0, 10));

  const data = {
    labels,
    datasets: [
      {
        label: "Price",
        data: rows.map((r) => r.price_at_bucket),
        borderColor: "blue",
        backgroundColor: "blue",
        yAxisID: "priceAxis",
        pointRadius: 0,
      },
      {
        label: "Sentiment",
        data: rows.map((r) => r.weighted_sentiment),
        borderColor: "green",
        backgroundColor: "green",
        yAxisID: "sentimentAxis",
        pointRadius: 0,
      },
    ],
  };

  const options = {
    responsive: true,
    interaction: {
      mode: "index",
      intersect: false,
      axis: "x",
    },
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
    plugins: {
      zoom: {
        pan: {
          enabled: true,
          mode: "x",
        },
        zoom: {
          wheel: {
            enabled: true,
          },
          pinch: {
            enabled: true,
          },
          mode: "x",
        },
      },
    },
  };

  const emptyMessage =
    mode === "live"
      ? "No live data yet — ETL is running."
      : "No data for this asset.";

  return (
    <div className="container">
      <div className="flex-between"  style={{ marginBottom: "24px" }}>
        <h2>Showing chart for {selectedAsset}</h2>
        <DateRangeSelector
          startDate={startDate}
          endDate={endDate}
          setStartDate={setStartDate}
          setEndDate={setEndDate}
          datePreset={datePreset}
          handleDatePresetChange={handleDatePresetChange}
        />
      </div>

      {loading && <p>Loading...</p>}
      {!loading && correlationData.length > 0 && (
        <Line data={data} options={options} />
      )}
      {!loading && correlationData.length === 0 && (
        <div className="empty-container">{emptyMessage}</div>
      )}
    </div>
  );
}

export default Chart;
