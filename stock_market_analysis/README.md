# 📈 Advanced ML Stock Market Dashboard

Welcome to the **Advanced ML Stock Market Dashboard**. This project demonstrates a full-stack integration of dynamic web technologies, Natural Language Processing (NLP), and Mathematical Machine Learning to build a sophisticated algorithmic forecasting system.

This dashboard goes beyond simple price plotting. It ingests historical market data, dynamically engineers momentum features, mathematically scores global multi-layered news sentiment, and feeds this matrix into a state-of-the-art Decision Tree predictive algorithm.

---

## 🏗️ Architecture & Tech Stack

### Backend (The "Algorithmic Engine")
*   **Language**: Python 3.10+
*   **Framework**: `FastAPI` (Chosen for its asynchronous, high-performance API routing and built-in data validation).
*   **Data Ingestion**: `yfinance` (Real-time fetching of OHLCV market data and metadata without rate-limiting API keys).
*   **Data Manipulation**: `pandas` & `numpy` (Core matrix manipulation, rolling window calculations, and `NaN` handling).
*   **Machine Learning**: `scikit-learn` (Specifically, the `GradientBoostingRegressor` for time-series forecasting).
*   **Natural Language Processing**: `vaderSentiment` (Lexicon and rule-based sentiment analysis tuned for microblog/news contexts).

### Frontend (The "Bloomberg Terminal")
*   **Markup / Styling**: Modern HTML5 and pure Vanilla CSS3. The UI utilizes a strict Dark Mode, CSS Grid/Flexbox for responsive layouts, and "Glassmorphism" for a premium aesthetic, deliberately avoiding heavy UI libraries like Tailwind or React to demonstrate fundamental frontend mastery.
*   **Interactivity**: Vanilla JavaScript handles asynchronous API fetching (`fetch`), DOM manipulation, and dynamic tooltip rendering.
*   **Data Visualization**: `Chart.js` (Renders interactive, zoomable, pan-able HTML5 canvas charts overlaid with moving averages and dashed-line ML projections).

---

## 🧠 The Mathematics & Machine Learning Pipeline

This application models real-world algorithmic trading logic to solve common ML time-series pitfalls. Be prepared to discuss these four core pillars during an interview:

### 1. Feature Engineering (`pandas`)
Raw prices (`$150`, `$152`) are nearly useless to an ML algorithm. The backend `engineer_features` function mathematically transforms the raw `Close` array into normalized technical momentum indicators:
*   **Daily Return**: The percentage change day-over-day (`df['Close'].pct_change()`).
*   **Rolling Volatility**: The 20-day standard deviation of those daily returns, measuring market instability.
*   **RSI (Relative Strength Index)**: A 14-day momentum oscillator that measures the speed and change of price movements, outputting a normalized scale from 0 to 100.
*   **MACD (Moving Average Convergence Divergence)**: The mathematical difference between the 12-day Exponential Moving Average (EMA) and the 26-day EMA, signaling momentum shifts.
*   **Volume Anomaly Proxy**: Normalizes today's volume against the 50-day average. Massive spikes serve as a quantitative proxy for "Historical News Events," preventing the AI from falsely assuming today's news caused last year's price action.

### 2. Dual-Layer NLP Sentiment Architecture (`vaderSentiment`)
The system does not just blindly read news about a company. It uses a **Dual-Layer Architecture** to prevent localized positive news from blinding the model to global macro-economic collapses.
*   **Micro Score**: Fetches the top 5 recent headlines specifically tagged to the requested ticker (e.g., `AAPL` earnings) and generates a `-1.0` to `+1.0` compound score.
*   **Macro Score**: Fetches the top 5 broad market headlines using the `SPY` ETF as a proxy for the S&P 500 / Global Economy.
*   **The Blend**: The backend mathematically blends these (60% Micro / 40% Macro). However, it implements a dynamic override logic: if the Macro score drops below a severe crisis threshold (`-0.30`), the weights invert (30% Micro / 70% Macro) so the AI correctly identifies the macroeconomic headwind.

### 3. Sub-Sector Crisis Inversion
Standard ML models falter when global news is intensely negative (e.g., war), as they assume all stocks will crash. 
*   This backend checks the incoming ticker against a hardcoded whitelist of "Crisis-Hedge" equities (e.g., Defense contractors like `LMT`, `RTX` or Energy giants like `XOM`). 
*   If the ticker is whitelisted and the Dual-Layer Sentiment is negative, the model mathematically inverts the sentiment score using a `1.5x` multiplier (`adjusted = abs(sentiment) * 1.5`), teaching the predictive engine that global instability is actually a growth catalyst for that specific asset class.

### 4. Gradient Boosting & Dynamic Autoregressive Generation (`scikit-learn`)
The forecasting engine uses a `GradientBoostingRegressor`, which builds an ensemble of shallow decision trees, sequentially correcting the errors of the previous trees.
*   **Adjusted Close Training**: The model purposefully fetches `auto_adjust=True` data from `yfinance`. This smooths out corporate actions (like a 4-for-1 stock split), preventing the ML model from interpreting a split as a catastrophic 75% market crash.
*   **Preventing "Self-Fulfilling Recursion"**: When projecting 3 days into the future, the model does not just blindly forecast Day 2 based on Day 1's static old features. It executes a simulation loop: it predicts Day 1, appends that prediction to a virtual dataframe, **mathematically recalculates the 14-day RSI and Volatility from scratch**, and *then* predicts Day 2.
*   **Calendar Awareness**: A custom `get_next_market_day()` loop ensures the ML model leaps over weekends and officially recognized U.S. Stock Market Holidays (e.g., Thanksgiving, MLK Day) when generating the `YYYY-MM-DD` timestamps for its projections.

---

## 🚀 Getting Started

1. **Clone the repository**:
   ```bash
   git clone https://github.com/adamvj/StockMarketAnalysis.git
   cd StockMarketAnalysis
   ```

2. **Set up the Python Virtual Environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Run the FastAPI Server**:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

4. **View the Dashboard**:
   Open your browser and navigate to `http://localhost:8000/`.
