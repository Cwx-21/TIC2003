import { useState } from 'react'
import './App.css'
import SearchBar from "./components/SearchBar";
import SectionCard from "./components/SectionCard";
import Chart from "./components/Chart";
import { stockData } from "./data/mockData";

function App() {
  const [selectedStock, setSelectedStock] = useState(null);
  const [selectedBacktest, setSelectedBacktest] = useState(null);

  const stockList = Object.keys(stockData);

  return (
    <div className="page-container">
      {selectedStock === null ? (
      <>
        {/*Stock/Coin Search*/}
        <SearchBar placeholder="Search stock/coin..." />
      
        {/* Trending Section */}
        <SectionCard
          title="Trending"
          items={stockList}
          onItemClick={setSelectedStock}
        /> 
      </>
      ) : (
        <>
          <Chart
              stockName={selectedStock}
              onBack={() => setSelectedStock(null)}
          /> 
        </>
      )}

      {selectedBacktest === null ? (
      <>
        {/*Historical Backtest Search*/}
      <SearchBar placeholder="Search historical backtests..." />
      
        {/* Trending Section */}
        <SectionCard
          title="Infamous historical backtests"
          items={["GameStop 2021", "Elon Musk tweets vs TSLA"]}
          onItemClick={setSelectedBacktest}
        />
      </>
      ) : (
        <>
          <Chart
              stockName={selectedBacktest}
              onBack={() => setSelectedBacktest(null)}
          /> 
        </>
      )}

      
    </div>
  )
}

export default App
