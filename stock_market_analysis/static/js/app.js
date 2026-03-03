// Global Chart instance
let stockChart = null;

// Helpers
const formatCurrency = (val) => {
    if (val === null || val === undefined) return '-';
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(val);
};

const formatNumber = (val) => {
    if (val === null || val === undefined) return '-';
    if (val >= 1e12) return (val / 1e12).toFixed(2) + ' Trillion';
    if (val >= 1e9) return (val / 1e9).toFixed(2) + ' Billion';
    if (val >= 1e6) return (val / 1e6).toFixed(2) + ' Million';
    return new Intl.NumberFormat('en-US').format(val);
};

const formatPercent = (val) => {
    if (val === null || val === undefined) return '-';
    return (val * 100).toFixed(2) + '%';
};

// Global tracking for Multiview / Time Machine
let activeStocks = []; // Array of stock data objects
let currentPeriod = '1y';

// Render Active Ticker Chips
function renderActiveChips() {
    const container = document.getElementById('activeTickersContainer');
    container.innerHTML = '';

    activeStocks.forEach((stock, index) => {
        const chip = document.createElement('div');
        chip.className = 'ticker-chip';
        chip.innerHTML = `
            ${stock.symbol}
            <span class="remove-btn" title="Remove">&times;</span>
        `;

        chip.querySelector('.remove-btn').addEventListener('click', () => {
            activeStocks.splice(index, 1);
            if (activeStocks.length === 0) {
                // If all removed, default back to AAPL
                fetchStockData('AAPL', false);
            } else {
                // Re-render UI with remaining stocks
                updateUI(activeStocks[0]); // update primary stats to the first stock
                renderChart();
                renderActiveChips();
            }
        });

        container.appendChild(chip);
    });
}

// Main Fetch function
async function fetchStockData(ticker, isCompare = false) {
    const loader = document.getElementById('loader');
    const layout = document.getElementById('dashboardLayout');

    // UI State
    if (!isCompare) {
        loader.classList.remove('hidden');
        layout.classList.add('hidden');
    }

    // Check if we already have it
    if (activeStocks.some(s => s.symbol.toUpperCase() === ticker.toUpperCase())) {
        if (!isCompare) {
            loader.classList.add('hidden');
            layout.classList.remove('hidden');
        }
        return; // Prevent duplicates
    }

    // Clear old errors/results
    errorMsg.classList.add('hidden');
    document.getElementById('tmResult').classList.add('hidden');
    document.getElementById('resetZoomBtn').style.display = 'none';

    try {
        const response = await fetch(`/api/stock/${ticker}?period=${currentPeriod}`);
        if (!response.ok) throw new Error('Network response was not ok');
        const data = await response.json();

        if (isCompare) {
            activeStocks.push(data);
        } else {
            activeStocks = [data]; // Reset mode
        }

        renderActiveChips();
        if (activeStocks.length > 0) {
            updateUI(activeStocks[0]); // Always update sidebar/badges with the primary (first) stock
        }
        renderChart(); // Redesigned to accept activeStocks implicitly

        loader.classList.add('hidden');
        layout.classList.remove('hidden');
    } catch (error) {
        console.error("Error fetching data:", error);
        if (!isCompare || activeStocks.length === 0) {
            loader.classList.add('hidden');
            errorMsg.classList.remove('hidden');
        }
    }
}

// Helper to fetch multiple stocks at once (e.g., when changing timeframe)
async function fetchAllActiveStocks() {
    if (activeStocks.length === 0) return;

    const loader = document.getElementById('loader');
    const layout = document.getElementById('dashboardLayout');

    loader.classList.remove('hidden');
    layout.classList.add('hidden');
    errorMsg.classList.add('hidden');

    // Save the current symbols to refetch them
    const tickersToFetch = activeStocks.map(s => s.symbol);

    // Clear the active stocks array so we can rebuild it freshly
    activeStocks = [];

    // Fetch the primary one first (index 0)
    await fetchStockData(tickersToFetch[0], false);

    // Fetch the rest concurrently
    if (tickersToFetch.length > 1) {
        const comparePromises = [];
        for (let i = 1; i < tickersToFetch.length; i++) {
            comparePromises.push(fetchStockData(tickersToFetch[i], true));
        }
        await Promise.all(comparePromises);
    }
}

function updateUI(data) {
    // Top Section
    document.getElementById('stockSymbol').textContent = data.symbol;
    document.getElementById('stockName').textContent = data.name;
    document.getElementById('stockSector').textContent = data.sector || 'N/A';

    // Update the search bar input to the resolved ticker if they searched by name
    document.getElementById('tickerInput').value = data.symbol;

    document.getElementById('currentPrice').textContent = formatCurrency(data.current_price);

    // Calculate Change
    const change = data.current_price - data.previous_close;
    const changePercent = (change / data.previous_close) * 100;
    const isPositive = change >= 0;

    const changeEl = document.getElementById('priceChange');
    changeEl.textContent = `${isPositive ? '+' : ''}${formatCurrency(change)} (${isPositive ? '+' : ''}${changePercent.toFixed(2)}%)`;
    changeEl.className = `price-change ${isPositive ? 'positive' : 'negative'}`;

    // Get latest trend from history
    const history = data.historical_data;
    if (history && history.length > 0) {
        const latest = history[history.length - 1];
        const trendEl = document.getElementById('dsTrend');
        const trendExpEl = document.getElementById('dsTrendExplain');

        if (latest.trend === 1) {
            trendEl.textContent = "Trend: Bullish ↑";
            trendEl.className = "ds-trend tooltip-wrapper";
            trendExpEl.textContent = "Short-term momentum is rising above long-term averages.";
            trendExpEl.classList.remove('hidden');
        } else {
            trendEl.textContent = "Trend: Bearish ↓";
            trendEl.className = "ds-trend bearish tooltip-wrapper";
            trendExpEl.textContent = "Short-term momentum is falling below long-term averages.";
            trendExpEl.classList.remove('hidden');
        }
        // Ensure the tooltip is hooked up properly to the CSS rule
        trendEl.setAttribute("data-tooltip", "Predicted by Simple Moving Average crossover.");
    }

    // Stats
    document.getElementById('marketCap').textContent = formatNumber(data.market_cap);

    // Market Cap Context Badge & Explanation
    const capCtxEl = document.getElementById('capContext');
    const capExpEl = document.getElementById('capExplain');
    if (data.market_cap && data.market_cap > 0) {
        let capExp = "";
        if (data.market_cap >= 200e9) { capCtxEl.textContent = 'Mega Cap'; capExp = 'Valuation is over $200B. Typically highly stable market leaders with less aggressive growth.'; }
        else if (data.market_cap >= 10e9) { capCtxEl.textContent = 'Large Cap'; capExp = 'Valuation is over $10B. Generally stable, well-established companies.'; }
        else if (data.market_cap >= 2e9) { capCtxEl.textContent = 'Mid Cap'; capExp = 'Valuation is over $2B. Often hits a sweet spot between growth potential and stability.'; }
        else { capCtxEl.textContent = 'Small Cap'; capExp = 'Valuation is under $2B. Higher growth potential but comes with higher risk and volatility.'; }

        capCtxEl.className = 'badge context-badge info';
        capCtxEl.classList.remove('hidden');
        capExpEl.textContent = capExp;
        capExpEl.classList.remove('hidden');
    } else {
        capCtxEl.classList.add('hidden');
        capExpEl.classList.add('hidden');
    }

    document.getElementById('peRatio').textContent = data.pe_ratio ? data.pe_ratio.toFixed(2) : '-';

    // P/E Context Badge & Explanation
    const peCtxEl = document.getElementById('peContext');
    const peExpEl = document.getElementById('peExplain');
    if (data.pe_context) {
        peCtxEl.textContent = data.pe_context;
        peCtxEl.className = 'badge context-badge';

        let peExp = "";
        if (data.pe_context === 'High') {
            peCtxEl.classList.add('alert');
            peExp = `Higher than the ${data.sector} sector average. Might be overvalued or priced for high growth.`;
        } else if (data.pe_context.includes('Low')) {
            peCtxEl.classList.add('normal');
            peExp = `Lower than the ${data.sector} sector average. Could indicate a value stock or underlying issues.`;
        } else {
            peCtxEl.classList.add('warning'); // Normal / Average
            peExp = `In line with the ${data.sector} sector average, indicating fair valuation compared to peers.`;
        }

        peCtxEl.classList.remove('hidden');
        peExpEl.textContent = peExp;
        peExpEl.classList.remove('hidden');
    } else {
        peCtxEl.classList.add('hidden');
        peExpEl.classList.add('hidden');
    }

    document.getElementById('volumeToday').textContent = formatNumber(data.volume_today);

    // Volume Context Badge & Explanation
    const volCtxEl = document.getElementById('volContext');
    const volExpEl = document.getElementById('volExplain');
    if (data.volume_context) {
        volCtxEl.textContent = data.volume_context;
        volCtxEl.className = 'badge context-badge';

        let volExp = "";
        if (data.volume_context === 'High Activity') {
            volCtxEl.classList.add('info');
            volExp = "Trading volume is higher than average, indicating strong market interest or news.";
        } else if (data.volume_context === 'Low Activity') {
            volCtxEl.classList.add('warning');
            volExp = "Trading volume is lower than average, meaning less liquidity and potentially less price movement.";
        } else {
            volCtxEl.classList.add('normal');
            volExp = "Trading volume is around the 10-day average, indicating typical market activity.";
        }

        volCtxEl.classList.remove('hidden');
        volExpEl.textContent = volExp;
        volExpEl.classList.remove('hidden');
    } else {
        volCtxEl.classList.add('hidden');
        volExpEl.classList.add('hidden');
    }

    // 52 Week High / Low
    const fiftyTwoRangeEl = document.getElementById('fiftyTwoWeekRange');
    if (data.fiftyTwoWeekHigh !== null && data.fiftyTwoWeekLow !== null &&
        data.fiftyTwoWeekHigh !== undefined && data.fiftyTwoWeekLow !== undefined) {
        fiftyTwoRangeEl.textContent = `$${data.fiftyTwoWeekHigh.toFixed(2)} / $${data.fiftyTwoWeekLow.toFixed(2)}`;
    } else {
        fiftyTwoRangeEl.textContent = '-';
    }

    document.getElementById('divYield').textContent = data.dividend_yield ? formatPercent(data.dividend_yield) : '-';

    // Summary
    document.getElementById('companySummary').textContent = data.summary || "No company information available.";

    // NLP Sentiment Badge
    const sentEl = document.getElementById('marketSentiment');
    const sentCtxEl = document.getElementById('sentimentLabel');
    const sentExpEl = document.getElementById('sentimentExplain');

    if (data.sentiment) {
        sentEl.textContent = data.sentiment.score.toFixed(2);
        sentCtxEl.textContent = data.sentiment.label;
        sentCtxEl.className = 'badge context-badge';

        let sentExp = "";
        if (data.sentiment.label === 'Positive') {
            sentCtxEl.classList.add('positive', 'info');
            sentExp = "Recent news headlines are generally positive.";
        } else if (data.sentiment.label === 'Negative') {
            sentCtxEl.classList.add('negative', 'alert');
            sentExp = "Recent news headlines are generally negative.";
        } else {
            sentCtxEl.classList.add('normal');
            sentExp = "Recent news context is mixed or neutral.";
        }

        sentCtxEl.classList.remove('hidden');
        sentExpEl.textContent = sentExp;

        let hoverBreakdown = `Micro (Company): ${data.sentiment.micro_score} | Macro (Market): ${data.sentiment.macro_score}\n\nTop Headlines:\n`;
        hoverBreakdown += data.sentiment.headlines.slice(0, 3).join("\n- ");

        sentExpEl.title = hoverBreakdown;
        sentExpEl.classList.remove('hidden');
    } else {
        sentEl.textContent = 'N/A';
        sentCtxEl.classList.add('hidden');
        sentExpEl.classList.add('hidden');
    }

    // Competitors Sidebar
    const compContainer = document.getElementById('competitorsList');
    compContainer.innerHTML = ''; // Clear old

    if (data.competitors && data.competitors.length > 0) {
        data.competitors.forEach(comp => {
            const isPos = comp.change_percent >= 0;
            const sign = isPos ? '+' : '';
            const changeClass = isPos ? 'positive' : 'negative';

            const card = document.createElement('div');
            card.className = 'competitor-card';
            card.innerHTML = `
                <div class="comp-header">
                    <span class="comp-symbol">${comp.symbol}</span>
                    <span class="comp-price">${formatCurrency(comp.price)}</span>
                </div>
                <div class="comp-change ${changeClass}">${sign}${comp.change_percent.toFixed(2)}%</div>
            `;

            // Add click listener to fetch this ticker
            card.addEventListener('click', () => {
                document.getElementById('tickerInput').value = comp.symbol;
                fetchStockData(comp.symbol);
            });

            compContainer.appendChild(card);
        });
    } else {
        compContainer.innerHTML = '<p style="color: var(--text-secondary); font-size: 0.85rem;">No competitors found.</p>';
    }
}

function renderChart() {
    if (!activeStocks || activeStocks.length === 0) return;

    const ctx = document.getElementById('stockChart').getContext('2d');
    if (stockChart) stockChart.destroy();

    const isMulti = activeStocks.length > 1;
    const datasets = [];
    let commonDates = [];

    // Colors palette for multiple lines (Blue, Purple, Emerald, Orange, Rose)
    const baseColors = [
        'rgba(59, 130, 246, 1)',   // Blue
        'rgba(168, 85, 247, 1)',  // Purple
        'rgba(16, 185, 129, 1)',  // Emerald
        'rgba(245, 158, 11, 1)',   // Orange
        'rgba(244, 63, 94, 1)'    // Rose
    ];

    activeStocks.forEach((stock, index) => {
        let history = stock.historical_data;
        let forecasts = stock.ml_forecasts;
        if (!history || history.length === 0) return;

        const dateLabels = history.map(d => d.date);
        let prices = history.map(d => d.close);

        // Define baseline for % return calculation if multi
        const baselinePrice = isMulti ? prices[0] : null;

        if (isMulti) {
            prices = prices.map(p => ((p - baselinePrice) / baselinePrice) * 100);
        }

        // We use the dates of the first stock (Primary) for the X-axis
        if (index === 0) {
            commonDates = [...dateLabels];
            if (forecasts && forecasts.length > 0) {
                for (let i = 0; i < forecasts.length; i++) {
                    commonDates.push(forecasts[i].date);
                }
            }
        }

        const color = baseColors[index % baseColors.length];

        // 1. Plot the Main Price Line
        let paddedPrices = [...prices];
        if (forecasts && forecasts.length > 0) {
            for (let i = 0; i < forecasts.length; i++) paddedPrices.push(null);
        }

        datasets.push({
            label: `${stock.symbol} Price${isMulti ? ' (% Return)' : ''}`,
            data: paddedPrices,
            borderColor: color,
            backgroundColor: color.replace(', 1)', ', 0.1)'),
            borderWidth: 2,
            fill: !isMulti,
            tension: 0.1,
            pointRadius: 0,
            pointHoverRadius: 5
        });

        // 2. Plot ML Forecast Line (Dotted)
        if (forecasts && forecasts.length > 0) {
            const mlPredictions = new Array(prices.length).fill(null);
            mlPredictions[prices.length - 1] = prices[prices.length - 1]; // Connect to last known point

            for (let i = 0; i < forecasts.length; i++) {
                let p = forecasts[i].price;
                if (isMulti) p = ((p - baselinePrice) / baselinePrice) * 100;
                mlPredictions.push(p);
            }

            datasets.push({
                label: `${stock.symbol} ML Forecast`,
                data: mlPredictions,
                borderColor: color,
                borderWidth: 2,
                borderDash: [5, 5],
                fill: false,
                tension: 0.1,
                pointRadius: 3,
                pointHoverRadius: 6,
                pointBackgroundColor: color
            });
        }

        // 3. Plot SMAs ONLY if single view
        if (!isMulti) {
            const sma20 = history.map(d => d.sma_20);
            const sma50 = history.map(d => d.sma_50);

            let padded20 = [...sma20];
            let padded50 = [...sma50];
            if (forecasts) {
                for (let i = 0; i < forecasts.length; i++) {
                    padded20.push(null);
                    padded50.push(null);
                }
            }

            datasets.push({
                label: 'SMA 20',
                data: padded20,
                borderColor: 'rgba(16, 185, 129, 0.8)',
                borderWidth: 1.5,
                borderDash: [5, 5],
                fill: false,
                tension: 0.1,
                pointRadius: 0
            });
            datasets.push({
                label: 'SMA 50',
                data: padded50,
                borderColor: 'rgba(245, 158, 11, 0.8)',
                borderWidth: 1.5,
                borderDash: [2, 2],
                fill: false,
                tension: 0.1,
                pointRadius: 0
            });
        }
    });

    Chart.defaults.color = '#94a3b8';
    Chart.defaults.font.family = "'Inter', sans-serif";

    stockChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: commonDates,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            plugins: {
                zoom: {
                    zoom: {
                        wheel: { enabled: true },
                        pinch: { enabled: true },
                        mode: 'xy',
                        onZoomComplete: () => { document.getElementById('resetZoomBtn').style.display = 'inline-block'; }
                    },
                    pan: {
                        enabled: true,
                        mode: 'xy',
                        onPanComplete: () => { document.getElementById('resetZoomBtn').style.display = 'inline-block'; }
                    }
                },
                legend: {
                    display: false // Using custom HTML legend
                },
                tooltip: {
                    backgroundColor: 'rgba(15, 23, 42, 0.9)',
                    titleColor: '#fff',
                    bodyColor: '#cbd5e1',
                    borderColor: 'rgba(255,255,255,0.1)',
                    borderWidth: 1,
                    padding: 10,
                    callbacks: {
                        label: function (context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            if (context.parsed.y !== null) {
                                if (isMulti) {
                                    label += context.parsed.y.toFixed(2) + '%';
                                } else {
                                    label += new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(context.parsed.y);
                                }
                            }
                            return label;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    ticks: { maxTicksLimit: 8 }
                },
                y: {
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    ticks: {
                        callback: function (value) {
                            return isMulti ? value.toFixed(2) + '%' : '$' + value;
                        }
                    }
                }
            }
        }
    });
}

// Event Listeners
document.getElementById('timeframeSelector').addEventListener('click', (e) => {
    if (e.target.classList.contains('time-btn')) {
        // Update active class
        document.querySelectorAll('.time-btn').forEach(btn => btn.classList.remove('active'));
        e.target.classList.add('active');

        // Update period and fetch
        currentPeriod = e.target.getAttribute('data-period');

        // If we have active stocks, refresh all of them. Otherwise default to input
        if (activeStocks.length > 0) {
            fetchAllActiveStocks();
        } else {
            const ticker = document.getElementById('tickerInput').value.trim() || 'AAPL';
            fetchStockData(ticker);
        }
    }
});

document.getElementById('resetZoomBtn').addEventListener('click', (e) => {
    if (stockChart) {
        stockChart.resetZoom();
        e.target.style.display = 'none';
    }
});

document.getElementById('searchBtn').addEventListener('click', () => {
    const ticker = document.getElementById('tickerInput').value.trim();
    if (ticker) {
        if (activeStocks.length > 0) {
            // Replace primary stock, keep comparators, and fetch all
            activeStocks[0].symbol = ticker;
            fetchAllActiveStocks();
        } else {
            fetchStockData(ticker, false); // Normal replace
        }
    }
});

document.getElementById('compareBtn').addEventListener('click', () => {
    const ticker = document.getElementById('tickerInput').value.trim();
    if (ticker) fetchStockData(ticker, true); // Append to multiview
});

document.getElementById('tickerInput').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        const ticker = e.target.value.trim();
        if (ticker) {
            if (activeStocks.length > 0) {
                // Replace primary stock, keep comparators, and fetch all
                activeStocks[0].symbol = ticker;
                fetchAllActiveStocks();
            } else {
                fetchStockData(ticker, false);
            }
        }
    }
});

// Time Machine Calculator
document.getElementById('tmCalculateBtn').addEventListener('click', () => {
    if (!activeStocks || activeStocks.length === 0) return;

    const amount = parseFloat(document.getElementById('tmAmount').value);
    const months = parseInt(document.getElementById('tmDuration').value);
    if (isNaN(amount) || amount <= 0) return;

    // Safety check for Chart Timeframes
    const periodMonths = { '1d': 0, '1mo': 1, '6mo': 6, '1y': 12, '5y': 60, '10y': 120, 'max': Infinity };
    if (periodMonths[currentPeriod] !== undefined && months > periodMonths[currentPeriod]) {
        const tmResult = document.getElementById('tmResult');
        tmResult.className = 'tm-result negative';
        const durationStr = months >= 12 ? (months / 12) + ' Years' : months + ' Months';
        tmResult.innerHTML = `<p style="color: var(--accent-danger); font-weight: 500;">Please select a longer chart timeframe above to look back ${durationStr}!</p>`;
        tmResult.classList.remove('hidden');
        return;
    }

    const tmResult = document.getElementById('tmResult');
    tmResult.innerHTML = ''; // Clear old

    const targetDateObj = new Date();
    targetDateObj.setMonth(targetDateObj.getMonth() - months);
    const targetTime = targetDateObj.getTime();

    // Baseline Savings
    const savingsRatePerMonth = 0.045 / 12;
    const savingsValue = amount * Math.pow(1 + savingsRatePerMonth, months);
    const savingsProfit = savingsValue - amount;

    let htmlOutput = `<h4 style="margin-bottom: 0.5rem;">If you invested ${formatCurrency(amount)}:</h4>`;
    htmlOutput += `<div style="display: flex; flex-direction: column; gap: 0.5rem; margin-bottom: 1rem;">`;

    // Calculate for each active stock
    let results = [];
    activeStocks.forEach(stock => {
        const history = stock.historical_data;
        if (!history || history.length === 0) return;

        let closestIndex = 0;
        let minDiff = Infinity;

        for (let i = 0; i < history.length; i++) {
            const d = new Date(history[i].date).getTime();
            const diff = Math.abs(d - targetTime);
            if (diff < minDiff) {
                minDiff = diff;
                closestIndex = i;
            }
        }

        const pastPrice = history[closestIndex].close;
        const currentPrice = stock.current_price;
        const pastDate = history[closestIndex].date;

        if (!pastPrice || !currentPrice) return;

        const sharesBought = amount / pastPrice;
        const currentValue = sharesBought * currentPrice;
        const profitLoss = currentValue - amount;
        const returnPct = (profitLoss / amount) * 100;

        results.push({
            symbol: stock.symbol,
            date: pastDate,
            currentValue,
            profitLoss,
            returnPct
        });
    });

    // Sort by most profitable
    results.sort((a, b) => b.profitLoss - a.profitLoss);

    results.forEach(res => {
        const isPos = res.profitLoss >= 0;
        const colorClass = isPos ? 'positive' : 'negative';
        const sign = isPos ? '+' : '';
        htmlOutput += `
            <div style="display: flex; justify-content: space-between; align-items: center; background: rgba(0,0,0,0.2); padding: 0.75rem; border-radius: 8px; border-left: 4px solid var(--${isPos ? 'accent-success' : 'accent-danger'})">
                <span style="font-weight: 600; font-size: 1.1rem; width: 60px;">${res.symbol}</span>
                <div style="flex-grow: 1; text-align: right;">
                    <span style="font-size: 1.1rem; font-weight: 700; margin-right: 0.5rem;">${formatCurrency(res.currentValue)}</span>
                    <span class="${colorClass}" style="font-size: 0.9rem;">${sign}${formatCurrency(res.profitLoss)} (${res.returnPct.toFixed(2)}%)</span>
                </div>
            </div>
        `;
    });

    htmlOutput += `</div>`;
    htmlOutput += `<p style="font-size: 0.85rem; color: var(--text-secondary); text-align: center;">*Standard 4.5% APY Savings Account: +${formatCurrency(savingsProfit)}</p>`;

    tmResult.className = `tm-result`;
    tmResult.innerHTML = htmlOutput;
    tmResult.classList.remove('hidden');
});

// Initial load
document.addEventListener('DOMContentLoaded', () => {
    fetchStockData('AAPL');
});
