import { useEffect, useState } from 'react'
import './App.css'
import api from "./utils/api";
import SearchBar from "./components/SearchBar";
import SectionCardStock from "./components/SectionCardAsset";
import SectionCardBacktest from "./components/SectionCardBacktest";
import Chart from "./components/Chart";

function App() {
  const [assets, setAssets] = useState([]);
  const [selectedAsset, setSelectedAsset] = useState("");
  const [mode, setMode] = useState("live"); //toggle between live or backtest

  const [sentimentData, setSentimentData] = useState([]);
  const [priceData, setPriceData] = useState([]);

  const [searchAsset, setSearchAsset] = useState("");
  const [searchHistorical, setSearchHistorical] = useState("");
  const [error, setError] = useState("");
  
  //load asset list
  useEffect(() => {
    api.get("/assets")
      .then((res) => {
        setAssets(res.data.data);
      })
      .catch(() => {
        setError("Failed to load assets");
      });
  }, []);
  
  //when user selects asset
  useEffect(() => {
    if (!selectedAsset) return;

    setError("");

    Promise.all([
      api.get(`/sentiment/${selectedAsset}`),
      api.get(`/prices/${selectedAsset}`),
    ])
      .then(([sentimentRes, priceRes]) => {
        setSentimentData(sentimentRes.data.data);
        setPriceData(priceRes.data.data);
      })
      .catch(() => {
        setError("Failed to load chart data");
      });
  }, [selectedAsset]);


  //search assets
  const filteredAssets = assets.filter((item) => {
		return (item.name.toLowerCase().includes(searchAsset.toLowerCase()) ||
				  item.symbol.toLowerCase().includes(searchAsset.toLowerCase()));
  });
  
  const displayedAssets = searchAsset ? filteredAssets : assets.slice(0, 5);

  const handleAssetClick = (symbol) => {
		setSelectedAsset(symbol);
		setMode("live");
	};

  const handleBack = () => {
		setSelectedAsset("");
		setSentimentData([]);
		setPriceData([]);
		setError("");
  };
  
  return (
    <div className="page-container">
      <h1 className="title">HypeCheck</h1>

        {error && <p>{error}</p>}

        {!selectedAsset && (
        <>
          {/*Asset Search*/}
            <SearchBar
              search={searchAsset}
              setSearch={setSearchAsset}
              placeholder="Search assets..."
            />

            <SectionCardStock
              title="Trending Assets"
              items={displayedAssets}
              onItemClick={handleAssetClick}
            />

            {/* <SectionCardBacktest
              search={searchHistorical}
              setSearch={setSearchHistorical}
            /> */}
          </>
        )}

      {/*Chart*/}
        {selectedAsset && (
          <Chart
            selectedAsset={selectedAsset}
            priceData={priceData}
            sentimentData={sentimentData}
            mode={mode}
            setMode={setMode}
            onBack={handleBack}
          />
        )}
    </div>
  );
}

export default App
