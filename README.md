# HiWay RS+ATR Trade Engine

A production-ready technical analysis indicator engine that evaluates market regime conditions through relative strength and volatility analysis. Built for traders, developers, and financial platforms.

---

## What Does It Do?

The HiWay RS+ATR Engine calculates a **Relative Strength + Average True Range (RSATR)** regime indicator that analyzes:

- **Comparative Performance**: How a stock's returns compare against a benchmark index (e.g., S&P 500)
- **Volatility Context**: Market volatility-adjusted strength analysis
- **Market Regime Classification**: Technical identification of bullish, bearish, or range-bound market regimes

**Technical Example:** If Apple gains 5% while the S&P 500 gains 6%, the RS+ATR calculation shows Apple is underperforming in relative terms—useful for technical regime analysis and market structure validation.

---

## Key Features

✅ **Multi-Data Source Support**
- Real-time data from Alpaca, Polygon.io
- Historical data from Yahoo Finance
- Automatic failover if one source fails

✅ **Easy Integration**
- REST API endpoints for technical analysis platforms
- Works with MetaTrader 5, ThinkorSwim, and custom dashboards
- Docker container for quick deployment

✅ **Real-Time & Batch Processing**
- Analyze single symbols or 100+ in batch
- Stream live market updates
- Batch regime scans for watchlists

✅ **Customizable Parameters**
- Adjust lookback periods and smoothing
- Choose between EMA or SMA smoothing
- Set your own benchmark (default: SPY)

---

## Installation

### Option 1: Docker (Recommended for Beginners)

```bash
# Build the container
docker build -t hiway-engine .

# Run the engine
docker run -p 5000:5000 hiway-engine
```

The API will be available at `http://localhost:5000`

### Option 2: Local Python Installation

```bash
# Clone the repository
git clone https://github.com/hinesglobal4/HiWay-64-Trade-Engine.git
cd HiWay-64-Trade-Engine

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

## Quick Start

### Using the REST API

Once the engine is running, you can make requests:

**Analyze regime for a single stock:**

```bash
curl -X POST http://localhost:5000/api/v1/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "AAPL",
    "benchmark": "SPY",
    "timeframe": "1d",
    "bars": 500
  }'
```

**Response:**
```json
{
  "symbol": "AAPL",
  "current": {
    "rs_atr": 0.45,
    "regime": 1,
    "close": 175.25
  },
  "timestamp": "2024-07-22T14:30:00"
}
```

**Get regime snapshot of multiple stocks:**

```bash
curl "http://localhost:5000/api/v1/snapshot?symbols=AAPL,MSFT,GOOGL&benchmark=SPY"
```

---

### Using Python Code

```python
from engine import create_engine
import asyncio

async def main():
    # Create and initialize the engine
    engine = create_engine({
        'data_provider': 'yahoo',
        'rs_lookback': 14,
        'atr_length': 14
    })
    await engine.initialize()
    
    # Analyze a single stock
    result = await engine.calculate_symbol('AAPL', benchmark='SPY')
    print(f"AAPL RS+ATR: {result['rs_atr']:.2f}")
    print(f"Regime: {'Bullish' if result['regime'] > 0 else 'Bearish'}")
    
    # Analyze multiple stocks
    symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
    results = await engine.calculate_batch(symbols)
    
    for r in results:
        print(f"{r['symbol']}: {r['rs_atr']:.2f}")
    
    await engine.shutdown()

asyncio.run(main())
```

---

## Understanding Regime Classification

### What the Numbers Mean

| RS+ATR Value | Regime Value | Technical Regime |
|---|---|---|
| **Positive** | **1** | Bullish Regime (outperforming) |
| **Negative** | **-1** | Bearish Regime (underperforming) |
| **Near Zero** | **~0** | Range-Bound Regime (market-tracking) |

### Example Regime Readings

- **AAPL RS+ATR = +0.75** → Strong bullish regime classification
- **MSFT RS+ATR = -0.32** → Clear bearish regime classification
- **TSLA RS+ATR = +0.05** → Range-bound with slight bullish lean

### Interpretation Guidance

The regime classification represents technical market structure analysis:

- **Bullish Regime (1)**: Stock's risk-adjusted returns exceed benchmark returns
- **Bearish Regime (-1)**: Stock's risk-adjusted returns lag benchmark returns
- **Range-Bound Regime (~0)**: Stock moving in line with benchmark performance

---

## API Endpoints

### POST `/api/v1/calculate`
Perform regime analysis for a single stock.

**Parameters:**
- `symbol` (string): Stock ticker (e.g., "AAPL")
- `benchmark` (string): Benchmark symbol (default: "SPY")
- `timeframe` (string): "1d", "1h", "15min" (default: "1d")
- `bars` (integer): Historical bars to analyze (default: 500)

**Response includes:**
- `rs_atr`: Normalized relative strength value
- `regime`: Regime classification (1, -1, or near 0)
- `close`: Current price
- `data`: Historical analysis data

---

### GET `/api/v1/snapshot`
Perform batch regime analysis for multiple stocks (faster for watchlists).

**Parameters:**
- `symbols` (string): Comma-separated tickers (e.g., "AAPL,MSFT,GOOGL")
- `benchmark` (string): Benchmark symbol (default: "SPY")
- `timeframe` (string): "1d", "1h", etc. (default: "1d")

**Response:**
- Array of regime snapshots for each symbol

---

### GET/POST `/api/v1/config`
View or update engine configuration parameters.

**GET:** Returns current parameters
```json
{
  "rs_lookback": 14,
  "atr_length": 14,
  "smoothing_length": 5,
  "use_ema": true
}
```

**POST:** Update parameters
```bash
curl -X POST http://localhost:5000/api/v1/config \
  -H "Content-Type: application/json" \
  -d '{
    "rs_lookback": 20,
    "atr_length": 20,
    "smoothing_length": 7
  }'
```

---

### GET `/health`
Check if the engine is running and healthy.

```bash
curl http://localhost:5000/health
```

---

## Technical Calculation Methodology

### The Formula (Simplified)

1. **Calculate Period Returns**: Measure price change over lookback period
   - Stock Return = (Today's Price / Price 14 days ago) - 1
   - Benchmark Return = (SPY Today / SPY 14 days ago) - 1

2. **Relative Strength (RS)**: Compare return differential
   - RS = Stock Return - Benchmark Return

3. **Average True Range (ATR)**: Measure price volatility
   - Calculates average price movement range

4. **Normalize RS by Volatility**: Adjust for market conditions
   - RS+ATR = RS / ATR
   - Volatility-adjusted comparative strength

5. **Smoothing**: Apply moving average to reduce noise
   - Final Classification = EMA or SMA of RS+ATR

---

## Use Cases

### 📊 For Technical Analysts
- Analyze stock performance relative to market benchmarks
- Identify outperformers and underperformers in watchlists
- Validate market regime changes with volatility context

### 🤖 For Algorithmic Trading
- Build systematic regime-based strategies
- Integrate into backtesting and validation systems
- Create multi-symbol watchlist scanners

### 📈 For Trading Platforms
- Add as a custom indicator to MetaTrader 5
- Embed in ThinkorSwim analysis tools
- Display real-time regime analysis in dashboards

### 💼 For Portfolio Analysts
- Monitor relative performance of holdings
- Identify regime shifts for portfolio structure
- Validate performance attribution

---

## Architecture Overview

The engine is built in **layers** for scalability and maintainability:

```
Dashboard/User Interface
        ↓
    REST API (Flask)
        ↓
  Orchestrator (Coordinator)
        ↓
  ┌─────────────────────────────┐
  │  Core Analysis Engine       │
  │  ├─ Relative Strength       │
  │  ├─ ATR Calculator          │
  │  └─ Smoothing (EMA/SMA)     │
  └─────────────────────────────┘
        ↓
  ┌─────────────────────────────┐
  │  Real-Time Stream Processor │
  │  └─ Circular Buffers        │
  └─────────────────────────────┘
        ↓
  ┌─────────────────────────────┐
  │  Data Providers             │
  │  ├─ Alpaca                  │
  │  ├─ Polygon.io              │
  │  └─ Yahoo Finance           │
  └─────────────────────────────┘
```

For technical architecture details, see [ARCHITECTURE.md](ARCHITECTURE.md).

---

## Configuration Parameters

Fine-tune the engine via the `/api/v1/config` endpoint:

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `rs_lookback` | 14 | Periods for return comparison |
| `atr_length` | 14 | Periods for volatility measurement |
| `smoothing_length` | 5 | Periods for signal smoothing |
| `use_ema` | true | Smoothing method (EMA vs SMA) |

**Parameter Guidance:**
- **Shorter lookbacks (7-10)**: More responsive regime detection
- **Longer lookbacks (20-30)**: Smoother, more stable classifications
- **Higher smoothing**: Cleaner regimes, trades lag

---

## Troubleshooting

### API Connection Issues
```bash
# Verify the engine is running
docker ps  # Check if container is active

# Or start Python API directly
python -m engine.rest_api
```

### Data Provider Failures
The engine automatically attempts multiple data sources. If errors persist:
1. Verify internet connectivity
2. Confirm stock ticker validity (e.g., "AAPL" not "apple")
3. Try different timeframe parameter

### High Latency
- Use `/snapshot` endpoint for multiple symbols instead of repeated `/calculate` calls
- Reduce `bars` parameter
- Deploy closer to data source

---

## Performance Specifications

| Component | Throughput |
|-----------|-----------|
| Single regime analysis | 10-50ms |
| Batch of 50 stocks | 100-500ms |
| Real-time streaming | <5ms per tick |

Performance depends on network conditions and data provider response times.

---

## Important Disclaimer

⚠️ **This tool provides technical analysis indicators for regime classification and market structure validation.**

- This engine analyzes technical market structure and is provided for informational purposes only
- RS+ATR regime analysis should be combined with your own research and analysis
- Past performance and technical patterns do not guarantee future results
- Market analysis is inherently uncertain; always validate conclusions independently
- Use this tool responsibly as part of your broader investment research process

---

## Contributing

Found an issue or have a suggestion?

1. Open an issue with detailed description
2. Include stock tickers and configuration used
3. Attach any relevant error messages or data

---

## Next Steps

1. **Deploy the engine** (Docker or local installation)
2. **Test the API** with your preferred symbols
3. **Integrate** with your analysis platform
4. **Customize** parameters for your analysis approach
5. **Monitor** performance and regime classifications

---

## Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)** – Technical design, deployment scaling, and advanced configurations
- **[requirements.txt](requirements.txt)** – All dependencies and versions
- **[Dockerfile](Dockerfile)** – Container configuration
- **Pine Script source** – Original indicator implementation

---

## Questions?

- 📧 Check existing GitHub issues first
- 🔍 Review [ARCHITECTURE.md](ARCHITECTURE.md) for technical details
- 💡 Examine source code comments in `engine/` folder

---

**Version:** 1.0.0  
**Author:** hinesglobal4  
**License:** Mozilla Public License 2.0  
**Last Updated:** 2026-07-22
