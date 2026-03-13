import { useState } from 'react'
import './App.css'
import SearchBar from "./components/SearchBar";
import SectionCardStock from "./components/SectionCardStock";
import SectionCardBacktest from "./components/SectionCardBacktest";
import Chart from "./components/Chart";
import { stockData, backtestData } from "./data/mockData";

function App() {
  const [selectedStock, setSelectedStock] = useState(null);
  const [selectedBacktest, setSelectedBacktest] = useState(null);
	const [searchStock, setSearchStock] = useState("");
	const [searchBacktest, setSearchBacktest] = useState("");
  
  //search stock
  const filteredStocks = stockData.filter((item) => {
		return (item.name.toLowerCase().includes(searchStock.toLowerCase()) ||
				  item.symbol.toLowerCase().includes(searchStock.toLowerCase()));
  });
  
  //search backtest
	const filteredBacktests = backtestData.filter((item) => {
		return item.name.toLowerCase().includes(searchBacktest.toLowerCase());
  });
  
  let displayedStocks;

  if (searchStock === "") {
    const shuffle = [...stockData].sort(() => 0.5 - Math.random());
    displayedStocks = shuffle.slice(0, 5);
  } else {
    displayedStocks = filteredStocks;
  }

  const displayedBacktests = searchBacktest === "" ? filteredBacktests.slice(0, 5) : filteredBacktests;

  return (
    <div className="page-container">
      <h1 text-align="center">HypeCheck</h1>
      {selectedStock === null ? (
      <>
        {/*Stock/Coin Search*/}
          <SearchBar
            placeholder="Search stock/coin..."
            searchTerm={searchStock}
            setSearchTerm={setSearchStock}
          />
      
        {/* Trending Section */}
        <SectionCardStock
          title={"Trending stocks and coins"}
          items={displayedStocks}
          onItemClick={setSelectedStock}
        /> 
      </>
      ) : (
        <>
          <Chart
              stock={selectedStock}
              onBack={() => setSelectedStock(null)}
          /> 
        </>
      )}

      {selectedBacktest === null ? (
      <>
        {/*Historical Backtest Search*/}
          <SearchBar
            placeholder="Search historical backtests..."
            searchTerm={searchBacktest}
						setSearchTerm={setSearchBacktest}
          />
      
        {/* Trending Section */}
        <SectionCardBacktest
          title="Infamous historical backtests"
          items={displayedBacktests}
          onItemClick={setSelectedBacktest}
        />
      </>
      ) : (
        <>
          <Chart
              stock={selectedBacktest}
              onBack={() => setSelectedBacktest(null)}
          /> 
        </>
      )}

      
    </div>
  )
}

export default App
