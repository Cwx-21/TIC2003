# 1 Abstract

Retail investors today often make high-stakes financial decisions based on social media hype rather than fundamental data. Institutional investors use advanced social listening tools but regular users become confused by bot-created fake trends and artificial pump and dump market manipulation schemes. HypeCheck is a social media event & data processing system that aims to measure the correlation between social media sentiment and financial reality.

The system utilizes a hybrid approach wherein the system analyzes historical archives from Reddit (obtained using the Kaggle/Pushshift data set) to backtest the sentiment baseline against past events (like the GameStop squeeze from 2021), all while simultaneously analyzing current events from communication platforms like Telegram for monitoring purposes. Using Natural Language Processing (NLP) tools and techniques, the system utilizes sentiment analysis to convert qualitative data into quantitative data using sentiment scores. However, the system also utilizes a whale watcher credibility engine, which allows the system to analyze the data and identify smart money sentiment, thereby filtering out bot spams based on user data. The system demonstrates the results on a dashboard, allowing users to see both historical backtests and live Sentiment.

The project uses a hybrid microservice architecture, which includes a Python-based ETL engine for extensive data processing and sentiment analysis, together with a Node.js (Express) backend that supports multiple users at once for API services. The system shows data engineering skills through its ability to handle real-time data flow, store data in PostgreSQL, and display information in real time.

# 2 Proposed Architecture

Data Ingestion & Analysis Engine (Python Service):

- A dedicated background service acting as the system's ETL pipeline.
- Uses **Telethon** for live Telegram monitoring and a **Backtesting Engine** for historical Reddit data processing.
- The system operates in two modes:
  1. **Live Mode**: Captures real-time Telegram sentiment and correlates with live market pricing.
  2. **Backtest Mode**: Replays historical Reddit datasets (e.g., from 2024-2025) to validate sentiment-price correlation strategies against historical market data.
- Immediately cleans text and applies the VADER algorithm to generate Sentiment Scores (-1 to +1).
- Writes structured, scored data directly into the PostgreSQL database.

Data Storage (PostgreSQL):

- Acts as the central warehouse and decoupled bridge between the Python service and Node.js service.
- Utilizes JSONB columns to store raw social logs (for audit) and relational tables for processed sentiment metrics.

Backend Web API (Node.js/Express):

- A lightweight, non-blocking REST API service.
- Connects to PostgreSQL using an ORM (Sequelize) to serve frontend requests (e.g., GET /api/sentiment/bitcoin). It handles rate limiting and data formatting for the UI.

User Facing Dashboard (Frontend):

- A React.js + Vite single-page application.
- Renders interactive dual-axis charts (Price vs. Sentiment), allowing users to zoom into specific timeframes to analyze correlation.

# 3 Project Details

## 3.1 Benefits/Motivations

- **Quantifying FOMO & Emotional Investing:** Retail investors often buy at the top due to fear of missing out(FOMO). By visualizing sentiment alongside price, this system helps users identify when a rally is driven purely by emotional hype rather than financial substance.
- **Combating Market Manipulation:** Social media is plagued by sybil attacks (bot farms) designed to artificially pump assets. Our system's unique credibility filter protects investors by distinguishing between genuine community sentiment and coordinated spam campaigns.
- **Overcoming Information Overload:** During high-volatility events, thousands of messages are posted per minute which is far too many for a human to read. This system condenses massive streams of unstructured text into a single, actionable sentiment score, allowing for better decision-making.

## 3.2 Development Stack

| **Layer**            | **Technologies**                                      | **Remarks**                                                                                                                                                                                                                       |
| -------------------- | ----------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Frontend**         | React.js, Vite, Tailwind CSS, Axios                   | **React + Vite** provides a high-performance, component-based UI.                                                                                                                                                                 |
| ---                  | ---                                                   | ---                                                                                                                                                                                                                               |
| **Backend**          | Nodejs, Sequelize, Express                            | **Node.js** is selected for its non-blocking I/O, ideal for handling concurrent API requests. **Sequelize** simplifies database schema management between the backend and database.                                               |
| ---                  | ---                                                   | ---                                                                                                                                                                                                                               |
| **Database**         | PostgreSQL                                            | Selected over MySQL for its superior **JSONB** support (allowing storage of unstructured social media logs) and robust handling of time-series financial data.                                                                    |
| ---                  | ---                                                   | ---                                                                                                                                                                                                                               |
| **ETL Pipeline**     | Python 3, Pandas, VADER, Telethon (Telegram)          | **Python** is the industry standard for Data Science. It is used strictly for the "heavy lifting": fetching live data via Telethon, processing historical CSVs for Reddit backtesting, and running the VADER sentiment algorithm. |
| ---                  | ---                                                   | ---                                                                                                                                                                                                                               |
| **Third-party APIs** | CoinGecko, Yahoo Finance, Telegram, Kaggle (Datasets) | Primary sources for live social sentiment (Telegram), historical sentiment (Reddit/Kaggle), and market pricing (CoinGecko/Yahoo).                                                                                                 |
| ---                  | ---                                                   | ---                                                                                                                                                                                                                               |

## 4 Surveys/Studies

Social Media Platforms, particularly those with a large user base like Twitter (now X), have shown records of influencing the prices of certain stocks/coins. This resulted in multiple studies conducted to understand the underlying cause behind this.

A well-known example of a social media post affecting stock prices is the case of Elon Musk, the CEO of Tesla. On May 1 2020, Elon Musk tweeted on Twitter, "Tesla's stock price is too high imo" (in my opinion). This tweet caused an immediate drop in the stock price. The stock price of Tesla dropped by US$13 billion and closed the day with a 10% lower price than the day before. In 2021, discussions on the Reddit community r/WallStreetBets influenced the price of GameStop stock. Many users promoted the stock over a short period of time, which led to a sharp increase in its price and trading activity.

Cryptocurrency markets have also been influenced by these social media platforms to a greater extent. This is likely due to the smaller and more volatile market that cryptocurrency has. Posts on social media sites like Reddit, Twitter, and TikTok have often resulted in short-term fluctuations of cryptocurrency prices. News reports have shown that meme coins often gain attention and experience price increases after going viral on social media. For example, some meme coins gained large followings after trending on TikTok and other platforms, which contributed to increased trading activity.

Multiple academic studies and surveys have tried to understand this correlation between social media platforms and the financial market. These studies focus on sentiment analysis and observe how public sentiment correlates with price movement.

## 5 How our proposal differentiates

**Historical Backtesting**: HypeCheck incorporates historical replay. By ingesting Kaggle/Pushshift archives of Reddit activity during major financial events, our system can effectively replay the past to show how the model would have predicted previous market movements.

**Live Signal-to-Noise Isolation**: For real-time operations, we focus on Telegram. Our credibility algorithm filters out spam bots in these channels to isolate verified human sentiment.

**Real-Time Divergence Detection**: While most studies perform post-mortem analysis, HypeCheck operates on a high-frequency 10-second operational cycle. This granular data resolution allows for the detection of micro-trends and specific moments where price action and social sentiment move in opposite directions.

<br/>

# References

- <https://www.nasdaq.com/articles/how-does-social-media-influence-the-financial-markets>
- <https://www.reuters.com/business/finance/how-tweets-by-teslas-elon-musk-have-moved-markets-2021-11-08/>
- <https://en.wikipedia.org/wiki/GameStop_short_squeeze>
- <https://www.nature.com/articles/s44260-025-00042-2>
- <https://www.okx.com/learn/chill-guy-meme-coin-tiktok-legal-controversy>
