import { useState } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from '/vite.svg'
import './App.css'
import SearchBar from "./components/SearchBar";
import SectionCard from "./components/SectionCard";

function App() {
  const [count, setCount] = useState(0)

  return (
    <div className="page-container">
      {/*Stock/Coin Search*/}
      <SearchBar placeholder="Search stock/coin..." />
      
      {/* Trending Section */}
      <SectionCard
        title="Trending"
        items={["TSLA", "DOGE", "ASML", "NVDA"]}
      />

      {/*Historical Backtest Search*/}
      <SearchBar placeholder="Search historical backtests..." />
      
      {/* Trending Section */}
      <SectionCard
        title="Infamous historical backtests"
        items={["GameStop 2021", "Elon Musk tweets vs TSLA"]}
      />
    </div>
  )
}

export default App
