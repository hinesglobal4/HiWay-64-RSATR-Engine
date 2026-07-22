# HiWay RS+ATR Trade Engine - Architecture & Stack Documentation

## Overview
Complete production-grade translation of Pine Script RSATR indicator to Python + C++ with multi-platform dashboard integration.

## Architecture Stack Layers

### Layer 1: CALCULATION ENGINE (Core Logic)
- **File**: `engine/hiway_rs_atr_core.py`
- **Components**:
  - `RSATREngine` - Main calculation orchestrator
  - `ATRCalculator` - Wilder's smoothed ATR
  - `RelativeStrengthCalculator` - Return-based RS (stock vs benchmark)
  - `SmoothingCalculator` - EMA/SMA smoothing
- **Purpose**: Pure calculations, framework-agnostic
- **Performance**: Python with numpy optimization

---

### Layer 2: DATA PROVIDER (Feed Management)
- **File**: `engine/data_provider.py`
- **Providers**:
  - `AlpacaDataProvider` - Real-time + historical
  - `PolygonDataProvider` - Enterprise market data
  - `YahooFinanceDataProvider` - Free backtesting
  - `DataAggregator` - Automatic failover & redundancy
- **Purpose**: Abstract data sources, handle retries/failures
- **Supports**: Multiple timeframes, bars, async fetching

---

### Layer 3: STREAM PROCESSOR (Real-Time Updates)
- **File**: `engine/stream_processor.py`
- **Components**:
  - `StreamProcessor` - Circular buffers, event system
  - `CircularBuffer` - Memory-efficient ring buffer
- **Purpose**: Ingest tick/bar data, compute rolling indicators
- **Features**: Async callbacks, configurable buffer size

---

### Layer 4: API LAYER (External Integration)
- **File**: `engine/rest_api.py`
- **Endpoints**:
  - `POST /api/v1/calculate` - Compute RS+ATR for symbol(s)
  - `GET /api/v1/snapshot` - Batch snapshots (multi-symbol)
  - `GET/POST /api/v1/config` - Manage engine parameters
  - `GET /health` - Service health check
- **Bridges**:
  - MetaTrader 5 (via WebSocket)
  - ThinkorSwim (via webhook)
  - Custom dashboards (via REST)
- **Framework**: Flask (lightweight, easy to containerize)

---

### Layer 5: ORCHESTRATION (Lifecycle Management)
- **File**: `engine/orchestrator.py`
- **Components**:
  - `HiWayEngine` - Centralized coordinator
  - `EngineState` - Lifecycle (IDLE→INITIALIZING→RUNNING→SHUTDOWN)
  - `EngineMetrics` - Performance tracking
- **Responsibilities**:
  - Initialize all sub-components
  - Batch/streaming calculation routing
  - Graceful shutdown + resource cleanup
  - Status monitoring

---

## How Many Stacks Do You Need?

### For Single Strategy (1 Broker, 1 Symbol)
**Stack Count: 1 (Minimal)**
```
User Dashboard
    ↓
REST API (Flask) [Port 5000]
    ↓
HiWay Engine (Orchestrator)
    ├→ Core Calc (Python)
    ├→ Data Provider (Yahoo)
    └→ Stream Processor (disabled)
```

---

### For Multi-Symbol Watchlist (5-50 symbols)
**Stack Count: 2-3**
```
Stack 1: Public Symbols (Watchlist)
- REST API + Flask
- Data: Yahoo Finance
- Runs every 1-5 minutes

Stack 2: Real-Time Trading (Active Positions)
- WebSocket Handler
- Data: Alpaca/Polygon streams
- Runs every tick

Optional Stack 3: Batch Scanner
- Async batch processor
- Runs nightly
- Outputs scan results
```

---

### For Hedge Fund / Broker Integration (100+ symbols, multiple strategies)
**Stack Count: 4-6**

```
┌─────────────────────────────────────────────┐
│        DASHBOARD LAYER                      │
├─────────────────────────────────────────────┤
│ MetaTrader | ThinkorSwim | Custom Web UI   │
└──────────────┬──────────────────────────────┘
               │
┌──────────────┴──────────────────────────────┐
│        API LAYER (Stack 1-2)                │
├─────────────────────────────────────────────┤
│ REST API #1 (Public Data)    [5000]        │
│ REST API #2 (Real-Time)      [5001]        │
│ WebSocket API                [5002]        │
└──────────────┬──────────────────────────────┘
               │
┌──────────────┴──────────────────────────────┐
│    ORCHESTRATION LAYER (Stack 3)            │
├─────────────────────────────────────────────┤
│ HiWay Engine Coordinator                   │
│ - Task routing                             │
│ - State management                         │
│ - Performance monitoring                   │
└──────────────┬──────────────────────────────┘
               │
┌──────────────┴──────────────────────────────┐
│  PROCESSING LAYER (Stacks 4-5)             │
├─────────────────────────────────────────────┤
│ Stream Processor (Live Quotes)  Stack 4    │
│ Batch Calculator (EOD Scans)    Stack 5    │
│ Historical Backtest Engine      Stack 6    │
└──────────────┬──────────────────────────────┘
               │
┌──────────────┴──────────────────────────────┐
│    DATA LAYER                               │
├─────────────────────────────────────────────┤
│ Alpaca (Live + Historical)                 │
│ Polygon.io (Enterprise)                    │
│ Yahoo Finance (Backup)                     │
│ Local Cache (Redis)                        │
└─────────────────────────────────────────────┘
```

**Recommended Stack Breakdown:**

| Tier | Stacks | Components | Purpose |
|------|--------|-----------|----------|
| **Entry (Retail)** | 1 | Flask API + Orchestrator | Single-symbol trading |
| **Professional** | 2-3 | REST + WebSocket + Batch | Multi-symbol, live + EOD |
| **Enterprise** | 4-6 | Dedicated API, stream, calc, historical | Institutional grade |
| **HFT/Premium** | 7+ | Per-symbol calculators, GPU acceleration | Algorithmic hedging |

---

## Performance Characteristics

| Component | Throughput | Latency | Stack Count |
|-----------|-----------|---------|-------------|
| Python Core | 1K calc/sec | 1-10ms | 1 |
| REST API (Flask) | 100 req/sec | 50-100ms | 1 |
| Stream Processor | 1K bars/sec | 5-50ms | 1 |
| Batch Processor | 10K bars/day | - | 1 |

**Total Stacks Needed** = 1 (core) + 1 (data) + 1 (api) + 1 (orchestrator) + N (processing stacks by workload)

**Minimal: 3-4 stacks**
**Recommended: 4-5 stacks**
**Enterprise: 6-8 stacks**

---

## Next Steps

1. **Deploy Stack 1 (Core + API)**: Flask server with Yahoo data
2. **Add Stack 2 (Real-time)**: WebSocket stream processor
3. **Add Stack 3 (Batch)**: Nightly scanner
4. **Bridge platforms**: MetaTrader/ThinkorSwim integration
5. **Monitor & optimize**: Metrics, caching, load balancing

See `requirements.txt` for dependencies and `Dockerfile` for containerized deployment.
