from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from sklearn.ensemble import GradientBoostingRegressor
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

app = FastAPI(title="Beginner Stock Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def calculate_moving_averages(history: pd.DataFrame, window_short=20, window_long=50):
    """Calculates Simple Moving Averages to show a basic DS/Quant concept."""
    if len(history) < window_long:
        return history

    history[f'SMA_{window_short}'] = history['Close'].rolling(window=window_short).mean()
    history[f'SMA_{window_long}'] = history['Close'].rolling(window=window_long).mean()
    
    # Calculate a simple trend: 1 if short MA is above long MA (Bullish), else -1 (Bearish)
    history['Trend'] = np.where(history[f'SMA_{window_short}'] > history[f'SMA_{window_long}'], 1, -1)
    
    return history

def engineer_features(df: pd.DataFrame):
    """Calculates advanced quantitative features (RSI, MACD, Volatility) for the ML model."""
    df = df.copy()
    
    # Needs at least ~35 rows to safely calculate these
    if len(df) < 35:
        return df

    # Use 'Close' (which we will map to 'Adj Close' during the yfinance pull to fix the Split/Dividend cliff issue)
    
    # Daily Return
    df['Return'] = df['Close'].pct_change()
    
    # Rolling Volatility (20-day standard deviation of returns)
    df['Volatility'] = df['Return'].rolling(window=20).std()

    # Relative Strength Index (RSI) - 14 day
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))

    # MACD (Moving Average Convergence Divergence)
    ema_12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema_26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema_12 - ema_26

    # Historical Sentiment Proxy: Normalized Volume Spikes
    # High volume compared to the 50-day average indicates historical news events.
    df['Volume_MA50'] = df['Volume'].rolling(window=50).mean()
    df['Normalized_Volume'] = df['Volume'] / df['Volume_MA50']
    
    # Drop the NaN rows created by rolling windows
    df.dropna(inplace=True)
    return df

def get_next_market_day(current_date: pd.Timestamp) -> pd.Timestamp:
    """Calculates the next valid US stock market trading day, skipping weekends and 2026 holidays."""
    holidays_2026 = {
        '2026-01-01', # New Year's Day
        '2026-01-19', # MLK Jr. Day
        '2026-02-16', # Presidents' Day
        '2026-04-03', # Good Friday
        '2026-05-25', # Memorial Day
        '2026-06-19', # Juneteenth
        '2026-07-03', # Independence Day (Observed)
        '2026-09-07', # Labor Day
        '2026-11-26', # Thanksgiving
        '2026-12-25'  # Christmas
    }
    
    next_date = current_date + pd.Timedelta(days=1)
    # .weekday() returns 5 for Saturday and 6 for Sunday
    while next_date.weekday() >= 5 or next_date.strftime('%Y-%m-%d') in holidays_2026:
        next_date += pd.Timedelta(days=1)
        
    return next_date

def forecast_price(history: pd.DataFrame, ticker: str, sentiment_score: float, days_to_predict=3):
    """Trains a Gradient Boosting Regressor on engineered technical features and NLP sentiment to forecast prices."""
    df = engineer_features(history)
    
    # We need enough data after dropping NaNs
    if len(df) < 50:
        return []
    
    # The 'Target' is predicting the N-day future close price
    df['Target'] = df['Close'].shift(-days_to_predict)
    
    # Bridge the gap: Sentiment-Adjusted Feature (Sub-Sector Whitelisting Fix)
    # Instead of broad sectors like "Industrials" which includes airlines, we strict-whitelist Defense & Energy tickers.
    crisis_hedge_tickers = ["LMT", "RTX", "GD", "NOC", "LHX", "XOM", "CVX", "SHEL", "COP"]
    adjusted_sentiment = sentiment_score
    if ticker.upper() in crisis_hedge_tickers and sentiment_score < 0:
        # Invert the negative sentiment to a positive signal for crisis-hedge companies specifically
        adjusted_sentiment = abs(sentiment_score) * 1.5 
        
    df['Sentiment_Score'] = adjusted_sentiment
    
    # We can't train on the last N days because we don't know the future yet
    train_df = df.dropna(subset=['Target']).copy()
    
    # Features the model will learn from, now including Normalized_Volume (Historical News Proxy)
    features = ['Close', 'Normalized_Volume', 'Return', 'Volatility', 'RSI', 'MACD', 'Sentiment_Score']
    
    X_train = train_df[features].values
    y_train = train_df['Target'].values
    
    try:
        model = GradientBoostingRegressor(n_estimators=100, learning_rate=0.1, max_depth=3, random_state=42)
        model.fit(X_train, y_train)
        
        # To predict the ACTUAL future, we simulate dynamic feature recalculation preventing self-fulfilling loops
        forecasts = []
        
        # We start with our current DataFrame, and row by row we will append predictions and recalculate
        sim_df = df.copy()
        
        for _ in range(days_to_predict):
            # Grab the features from the very last row
            current_features = sim_df[features].iloc[-1].values.reshape(1, -1)
            pred_price = model.predict(current_features)[0]
            forecasts.append(round(pred_price, 2))
            
            # Create a mock next day to dynamically calculate the next step's indicators
            last_idx = sim_df.index[-1]
            next_idx = get_next_market_day(last_idx)
            
            # Append the new prediction
            new_row = sim_df.iloc[-1].copy()
            new_row['Close'] = pred_price
            
            # Only keep the last 50 days to keep the dataframe small and fast
            sim_df = pd.concat([sim_df, pd.DataFrame([new_row], index=[next_idx])]).tail(50)
            
            # Dynamically recalculate features for the new row so the next loop has accurate math
            sim_df['Return'] = sim_df['Close'].pct_change()
            sim_df['Volatility'] = sim_df['Return'].rolling(window=20).std()
            
            delta = sim_df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            sim_df['RSI'] = 100 - (100 / (1 + (gain / loss)))
            
            forecasts[-1] = {
                "date": next_idx.strftime('%Y-%m-%d'),
                "price": round(pred_price, 2)
            }
            
        return forecasts
    except Exception as e:
        print(f"Gradient Boosting Forecasting error: {e}")
        return []

def _fetch_and_score_news(ticker_str: str, analyzer: SentimentIntensityAnalyzer):
    """Helper to fetch and score the top 5 news articles for a specific ticker."""
    try:
        stock = yf.Ticker(ticker_str)
        news = stock.news
        if not news:
            return 0.0, []
            
        scores = []
        headlines = []
        
        for item in news[:5]:
            title = item.get("content", {}).get("title", "")
            if title:
                headlines.append(title)
                score = analyzer.polarity_scores(title)
                scores.append(score["compound"])
                
        if scores:
            return sum(scores) / len(scores), headlines
    except Exception:
        pass
    return 0.0, []

def analyze_sentiment(ticker_str: str):
    """Implements Dual-Layer Sentiment Architecture: Micro (Ticker) + Macro (SPY)."""
    analyzer = SentimentIntensityAnalyzer()
    
    # 1. Micro Sentiment (The requested ticker)
    micro_score, micro_headlines = _fetch_and_score_news(ticker_str, analyzer)
    
    # 2. Macro Sentiment (SPY ETF as a broad market proxy)
    # If the user is searching for SPY, we don't need to double-fetch
    macro_score = micro_score
    macro_headlines = []
    if ticker_str.upper() != "SPY":
        macro_score, macro_headlines = _fetch_and_score_news("SPY", analyzer)
        
    # 3. Blending Algorithm
    # Default: 60% Micro / 40% Macro
    weight_micro = 0.60
    weight_macro = 0.40
    
    # Override: If Macro is in severe crisis (e.g., highly negative global news), 
    # the market drags everything down. We invert the weights.
    if macro_score < -0.30:
        weight_micro = 0.30
        weight_macro = 0.70
        
    blended_score = (micro_score * weight_micro) + (macro_score * weight_macro)
    
    # Map final score to a category
    if blended_score >= 0.05:
        label = "Positive"
    elif blended_score <= -0.05:
        label = "Negative"
    else:
        label = "Neutral"
        
    return {
        "score": round(blended_score, 2),
        "label": label,
        "micro_score": round(micro_score, 2),
        "macro_score": round(macro_score, 2),
        "headlines": micro_headlines,
        "macro_headlines": macro_headlines
    }

def search_ticker_symbol(query: str):
    """Attempts to resolve a company name (e.g., 'Apple') to a ticker symbol (e.g., 'AAPL')."""
    try:
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={query}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            quotes = res.json().get('quotes', [])
            for q in quotes:
                if q.get('quoteType') in ['EQUITY', 'ETF', 'INDEX', 'MUTUALFUND']:
                    return q.get('symbol')
    except Exception:
        pass
    return query  # Fallback to the original search string

@app.get("/api/stock/{ticker}")
async def get_stock_data(ticker: str, period: str = "1y"):
    try:
        resolved_ticker = search_ticker_symbol(ticker)
        stock = yf.Ticker(resolved_ticker)
        info = stock.info
        
        valid_periods = ["1d", "1mo", "6mo", "1y", "5y", "10y", "max"]
        if period not in valid_periods:
            period = "1y"
            
        # Determine Interval based on Period to optimize JSON payload
        if period == "1d":
            interval = "5m"
        elif period in ["10y", "max"]:
            interval = "1wk"
        else:
            interval = "1d"
            
        # Fix 4: Adjusted Close
        history = stock.history(period=period, interval=interval, auto_adjust=True)
        if history.empty:
            raise HTTPException(status_code=404, detail="No data found for this ticker")
            
        history = calculate_moving_averages(history)
        
        # 1. NLP Sentiment Analysis (Must run first to feed the ML model)
        sentiment_data = analyze_sentiment(resolved_ticker)
        raw_sentiment_score = sentiment_data["score"] if sentiment_data else 0.0
        
        # 2. ML Price Forecasting (Sentiment-Adjusted & Edge-Case Corrected)
        forecasts = forecast_price(history, resolved_ticker, raw_sentiment_score, days_to_predict=3)
        
        # Format history for JSON response (replace NaN with None)
        history_clean = history.replace({np.nan: None})
        
        date_format = '%Y-%m-%d %H:%M' if period == "1d" else '%Y-%m-%d'
        
        historical_records = []
        for index, row in history_clean.iterrows():
            record = {
                "date": index.strftime(date_format),
                "open": row.get('Open'),
                "high": row.get('High'),
                "low": row.get('Low'),
                "close": row.get('Close'),
                "volume": row.get('Volume'),
                "sma_20": row.get('SMA_20'),
                "sma_50": row.get('SMA_50'),
                "trend": row.get('Trend')
            }
            historical_records.append(record)
            
        # Calculate Contextual Metrics
        pe = info.get("trailingPE")
        sector = info.get("sector", "")
        
        # 1. P/E Context (simplistic hardcoded averages for demonstration)
        sector_pe_averages = {
            "Technology": 35,
            "Healthcare": 25,
            "Financial Services": 15,
            "Consumer Cyclical": 22,
            "Energy": 10,
            "Industrials": 20,
            "Communication Services": 20,
            "Consumer Defensive": 20,
            "Basic Materials": 15,
            "Real Estate": 30,
            "Utilities": 18
        }
        
        pe_context = None
        if pe is not None:
            avg_pe = sector_pe_averages.get(sector, 20) # Default to 20 if sector unknown
            if pe > avg_pe * 1.5:
                pe_context = "High"
            elif pe < avg_pe * 0.5:
                pe_context = "Low (Value)"
            else:
                pe_context = "Normal"
                
        # 2. Market Cap Context
        market_cap = info.get("marketCap")
        cap_context = None
        if market_cap:
            if market_cap >= 200_000_000_000:
                cap_context = "Mega Cap"
            elif market_cap >= 10_000_000_000:
                cap_context = "Large Cap"
            elif market_cap >= 2_000_000_000:
                cap_context = "Mid Cap"
            elif market_cap >= 300_000_000:
                cap_context = "Small Cap"
            else:
                cap_context = "Micro/Nano Cap"
                
        # 3. Volume Context
        volume = info.get("volume")
        avg_volume = info.get("averageVolume10days") or info.get("averageVolume")
        vol_context = None
        if volume and avg_volume:
            if volume > avg_volume * 1.5:
                vol_context = "High Activity"
            elif volume < avg_volume * 0.5:
                vol_context = "Low Activity"
            else:
                vol_context = "Normal Volume"

        # 4. Fetch Competitors (Hardcoded fallback map due to yfinance info limitations)
        sector_competitors_map = {
            "Technology": ["MSFT", "GOOGL", "AAPL", "NVDA"],
            "Healthcare": ["JNJ", "UNH", "PFE", "ABBV"],
            "Financial Services": ["JPM", "BAC", "V", "MA"],
            "Consumer Cyclical": ["AMZN", "TSLA", "HD", "NKE"],
            "Energy": ["XOM", "CVX", "SHEL", "COP"],
            "Industrials": ["HON", "UPS", "BA", "CAT"],
            "Communication Services": ["META", "NFLX", "DIS", "T"],
            "Consumer Defensive": ["WMT", "PG", "KO", "PEP"],
            "Basic Materials": ["LIN", "BHP", "RIO", "SHW"],
            "Real Estate": ["PLD", "AMT", "CCI", "EQIX"],
            "Utilities": ["NEE", "DUK", "SO", "D"]
        }
        
        competitor_tickers = sector_competitors_map.get(sector, ["SPY", "QQQ", "DIA"]) # default to indices
        competitor_tickers = [t for t in competitor_tickers if t != resolved_ticker.upper()][:3] # 3 max, not self
        
        competitors_data = []
        for comp_ticker in competitor_tickers:
            try:
                comp_info = yf.Ticker(comp_ticker).info
                comp_curr = comp_info.get("currentPrice", comp_info.get("regularMarketPrice"))
                comp_prev = comp_info.get("previousClose")
                if comp_curr and comp_prev:
                    change_pct = ((comp_curr - comp_prev) / comp_prev) * 100
                    competitors_data.append({
                        "symbol": comp_ticker,
                        "price": comp_curr,
                        "change_percent": change_pct
                    })
            except Exception:
                pass # skip if fetching fails for a competitor

        # Build educational response
        response = {
            "symbol": resolved_ticker.upper(),
            "name": info.get("shortName", resolved_ticker.upper()),
            "current_price": info.get("currentPrice", info.get("regularMarketPrice")),
            "previous_close": info.get("previousClose"),
            "fiftyTwoWeekHigh": info.get("fiftyTwoWeekHigh"),
            "fiftyTwoWeekLow": info.get("fiftyTwoWeekLow"),
            "market_cap": info.get("marketCap"),
            "volume_today": volume,
            "volume_context": vol_context,
            "pe_ratio": pe,
            "pe_context": pe_context,
            "dividend_yield": info.get("dividendYield"),
            "sector": sector,
            "industry": info.get("industry"),
            "summary": info.get("longBusinessSummary"),
            "historical_data": historical_records,
            "competitors": competitors_data,
            "ml_forecasts": forecasts,
            "sentiment": sentiment_data
        }
        
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Mount static files for the frontend
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return FileResponse("static/index.html")
