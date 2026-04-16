import { useEffect, useState } from "react";
import api from "./utils/api";
import SearchBar from "./components/SearchBar";
import SectionCardAsset from "./components/SectionCardAsset";
import SentimentTable from "./components/SentimentTable";
import Chart from "./components/Chart";
import Alerts from "./components/Alerts";
import filterCorrelationData from "./utils/filterCorrelationData";
import presetDates from "./utils/presetDates";
import displayAssets from "./utils/displayAssets";
import useAssets from "./hooks/useAssets";
import useSession from "./hooks/useSession";
import useCorrelationData from "./hooks/useCorrelationData";
import useSentimentLogs from "./hooks/useSentimentLogs";



function App() {
  const [selectedAsset, setSelectedAsset] = useState("");
  const [mode, setMode] = useState("backtest"); //toggle between live or backtest

  const [searchAsset, setSearchAsset] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [datePreset, setDatePreset] = useState("all");
  const [error, setError] = useState("");

  //asset list
  const { assets, error: assetsError } = useAssets();

  //session
  const { backtestId, sessionId } = useSession();

  //correlation data
  const {
    correlationData,
    loading,
    error: chartError,
  } = useCorrelationData(selectedAsset, mode, backtestId, sessionId);

  //sentiment table
  const { comments, error: commentsError } = useSentimentLogs(
		selectedAsset,
		backtestId
  );

  //display assets
  const displayedAssets = displayAssets(assets, searchAsset);

  //date range
  const filteredCorrelationData = filterCorrelationData(
    correlationData,
    startDate,
    endDate
  );

  //date presets
  const handleDatePresetChange = (preset) => {
    setDatePreset(preset);

    const { start, end } = presetDates(preset, correlationData);

    setStartDate(start);
    setEndDate(end);
  };

  const handleAssetClick = (symbol) => {
    setSelectedAsset(symbol);
    setMode("backtest");
    setStartDate("");
    setEndDate("");
  };

  const handleBack = () => {
    setSelectedAsset("");
    setStartDate("");
    setEndDate("");
    setError("");
  };

  return (
    <div className="layout">
      <div className="flex-between">
        <h1 className="title">HypeCheck</h1>
        {selectedAsset && (
          <div className="flex-between">
            <div className="mode-toggle">
              <button
                className="toggle-button backtest"
                onClick={() => setMode("backtest")}
                disabled={mode === "backtest"}
              >
                Backtest
              </button>
              <button
                className="toggle-button live"
                onClick={() => setMode("live")}
                disabled={mode === "live" || !sessionId}
              >
                Live{!sessionId ? " (no session)" : ""}
              </button>
            </div>
            <button className="btn-secondary" onClick={handleBack}>
              ⬅ Back
            </button>
          </div>
        )}
      </div>

      {error && <p>{error}</p>}

      {!selectedAsset && (
        <>
          {/*Asset Search*/}
          <SearchBar
            title="Search"
            search={searchAsset}
            setSearch={setSearchAsset}
            placeholder="Search assets..."
          />

          <SectionCardAsset
            title="Trending Assets"
            items={displayedAssets}
            onItemClick={handleAssetClick}
          />
        </>
      )}

      {/*Sentiment Table */}
      {selectedAsset && (
        <SentimentTable
          title="Comments and Sentiment"
          selectedAsset={selectedAsset}
          comments={comments}
					error={commentsError}
        />
      )}

      {/*Chart*/}
      {selectedAsset && (
        <>
          <Chart
            selectedAsset={selectedAsset}
            correlationData={filteredCorrelationData}
            loading={loading}
            mode={mode}
            startDate={startDate}
            endDate={endDate}
            setStartDate={setStartDate}
            setEndDate={setEndDate}
            datePreset={datePreset}
            handleDatePresetChange={handleDatePresetChange}
          />

          <Alerts selectedAsset={selectedAsset} />
        </>
      )}
    </div>
  );
}

export default App;
