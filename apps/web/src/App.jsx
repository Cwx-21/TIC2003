import { useEffect, useState } from "react";
import api from "./utils/api";
import SearchBar from "./components/SearchBar";
import SectionCardAsset from "./components/SectionCardAsset";
import DateRangeSelector from "./components/DateRangeSelector";
import Chart from "./components/Chart";
import Alerts from "./components/Alerts";

function App() {
  const [assets, setAssets] = useState([]);
  const [selectedAsset, setSelectedAsset] = useState("");
  const [mode, setMode] = useState("backtest"); //toggle between live or backtest

  const [correlationData, setCorrelationData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [backtestId, setBacktestId] = useState(null);
  const [sessionId, setSessionId] = useState(null);

  const [searchAsset, setSearchAsset] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [datePreset, setDatePreset] = useState("all");
  const [error, setError] = useState("");

  // For alerts
  const [alerts, setAlerts] = useState([]);
  const [limit, setLimit] = useState(10);

  //load asset list
  useEffect(() => {
    api
      .get("/assets")
      .then((res) => {
        setAssets(res.data.data || []);
      })
      .catch(() => {
        setError("Failed to load assets");
      });
  }, []);

  // Load latest backtest ID and active session ID on mount
  useEffect(() => {
    Promise.all([api.get("/backtests"), api.get("/sessions?status=running")])
      .then(([btRes, sesRes]) => {
        setBacktestId(btRes.data.data[0]?.id ?? null);
        setSessionId(sesRes.data.data[0]?.id ?? null);
      })
      .catch(() => {
        // Non-fatal: chart will show empty state
      });
  }, []);

  // Fetch correlation data when asset or mode changes
  useEffect(() => {
    if (!selectedAsset) return;
    if (mode === "backtest" && !backtestId) return;
    if (mode === "live" && !sessionId) return;

    const controller = new AbortController();

    const params =
      mode === "backtest"
        ? `?backtest_id=${backtestId}&interval=1d`
        : `?session_id=${sessionId}`;

    Promise.resolve()
      .then(() => {
        setError("");
        setLoading(true);
        setCorrelationData([]);
        return api.get(`/correlation/${selectedAsset}${params}`, {
          signal: controller.signal,
        });
      })
      .then((res) => setCorrelationData(res.data.data || []))
      .catch((err) => {
        if (err.name !== "CanceledError" && err.code !== "ERR_CANCELED") {
          setError("Failed to load chart data");
        }
      })
      .finally(() => setLoading(false));

    return () => controller.abort();
  }, [selectedAsset, mode, backtestId, sessionId]);

  //search assets
  const filteredAssets = assets.filter((item) => {
    return (
      item.name.toLowerCase().includes(searchAsset.toLowerCase()) ||
      item.symbol.toLowerCase().includes(searchAsset.toLowerCase())
    );
  });

  const displayedAssets = searchAsset ? filteredAssets : assets.slice(0, 5);

  const handleAssetClick = (symbol) => {
    setSelectedAsset(symbol);
    setMode("backtest");
    setStartDate("");
    setEndDate("");
  };

  const handleBack = () => {
    setSelectedAsset("");
    setCorrelationData([]);
    setStartDate("");
    setEndDate("");
    setError("");
  };

  //date range selector
  const filteredCorrelationData = correlationData.filter((item) => {
    const itemDay = item.time_bucket.slice(0, 10);

    const afterStart = startDate ? itemDay >= startDate : true;
    const beforeEnd = endDate ? itemDay <= endDate : true;

    return afterStart && beforeEnd;
  });

  //date presets
  const handleDatePresetChange = (preset) => {
    setDatePreset(preset);

    if (!correlationData.length) return;

    const sortedData = [...correlationData].sort(
      (a, b) => new Date(a.time_bucket) - new Date(b.time_bucket)
    );

    const firstDate = sortedData[0].time_bucket.slice(0, 10);
    const lastDate = sortedData[sortedData.length - 1].time_bucket.slice(0, 10);

    if (preset === "all") {
      setStartDate("");
      setEndDate("");
      return;
    }

    const end = new Date(lastDate);
    const start = new Date(lastDate);

    if (preset === "5y") {
      start.setFullYear(start.getFullYear() - 5);
    } else if (preset === "1y") {
      start.setFullYear(start.getFullYear() - 1);
    } else if (preset === "1m") {
      start.setMonth(start.getMonth() - 1);
    } else if (preset === "1d") {
      start.setDate(start.getDate() - 1);
    }

    const formattedStart = start.toISOString().slice(0, 10);
    const formattedEnd = end.toISOString().slice(0, 10);

    setStartDate(formattedStart < firstDate ? firstDate : formattedStart);
    setEndDate(formattedEnd);
  };

  return (
    <div className="page-container">
      <div className="flex-container">
        <h1 className="title">HypeCheck</h1>
        {selectedAsset && (
          <div className="flex-container">
            <div className="mode-toggle">
              <button
                onClick={() => setMode("backtest")}
                disabled={mode === "backtest"}
              >
                Backtest
              </button>
              <button
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
