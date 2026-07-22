"""
HiWay RS+ATR Engine - Orchestration & Deployment
Coordinates all engine components and manages lifecycle
"""

import asyncio
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import logging

from .hiway_rs_atr_core import RSATREngine, RSATRConfig
from .data_provider import DataAggregator, YahooFinanceDataProvider, AlpacaDataProvider
from .stream_processor import StreamProcessor, CircularBuffer
from .rest_api import RSATRRestAPI


class EngineState(Enum):
    """Engine lifecycle states"""
    IDLE = "idle"
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    SHUTDOWN = "shutdown"


@dataclass
class EngineMetrics:
    """Engine performance metrics"""
    total_calculations: int = 0
    failed_calculations: int = 0
    avg_calculation_time_ms: float = 0.0
    last_update_time: Optional[float] = None
    active_symbols: int = 0
    buffer_utilization: float = 0.0


class HiWayEngine:
    """Main orchestration engine combining all components"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.state = EngineState.IDLE
        self.metrics = EngineMetrics()
        
        self.rsatr_engine: Optional[RSATREngine] = None
        self.data_provider: Optional[DataAggregator] = None
        self.stream_processor: Optional[StreamProcessor] = None
        self.rest_api: Optional[RSATRRestAPI] = None
        
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO)
    
    async def initialize(self):
        """Initialize all engine components"""
        self.state = EngineState.INITIALIZING
        self.logger.info("Initializing HiWay RSATR Engine...")
        
        try:
            rsatr_config = RSATRConfig(
                rs_lookback=self.config.get('rs_lookback', 14),
                atr_length=self.config.get('atr_length', 14),
                smoothing_length=self.config.get('smoothing_length', 5),
                use_ema=self.config.get('use_ema', True)
            )
            self.rsatr_engine = RSATREngine(rsatr_config)
            self.logger.info("Core engine initialized")
            
            provider_type = self.config.get('data_provider', 'yahoo')
            if provider_type == 'yahoo':
                primary = YahooFinanceDataProvider()
            elif provider_type == 'alpaca':
                primary = AlpacaDataProvider(
                    self.config['alpaca_key'],
                    self.config['alpaca_secret']
                )
            else:
                primary = YahooFinanceDataProvider()
            
            self.data_provider = DataAggregator(primary, fallback_providers=[])
            self.logger.info(f"Data provider initialized: {provider_type}")
            
            self.stream_processor = StreamProcessor(
                buffer_size=self.config.get('buffer_size', 1000)
            )
            self.logger.info("Stream processor initialized")
            
            self.rest_api = RSATRRestAPI(self.rsatr_engine, self.data_provider)
            self.logger.info("REST API initialized")
            
            self.state = EngineState.RUNNING
            self.logger.info("HiWay RSATR Engine ready")
            
        except Exception as e:
            self.state = EngineState.ERROR
            self.logger.error(f"Initialization failed: {e}")
            raise
    
    async def calculate_symbol(self, symbol: str, benchmark: str = "SPY",
                              timeframe: str = "1d", bars: int = 500) -> Dict[str, Any]:
        """Calculate RSATR for a symbol"""
        try:
            self.metrics.total_calculations += 1
            
            stock_df = self.data_provider.primary.get_dataframe(symbol, timeframe, bars)
            bench_df = self.data_provider.primary.get_dataframe(benchmark, timeframe, bars)
            
            result_df = self.rsatr_engine.calculate_dataframe(stock_df, bench_df)
            
            latest = result_df.iloc[-1]
            rs_atr_value = latest['rs_atr']
            signal = 1 if rs_atr_value >= 0 else -1
            
            return {
                'symbol': symbol,
                'benchmark': benchmark,
                'rs_atr': float(rs_atr_value),
                'signal': signal,
                'price': float(latest['close']),
                'timestamp': latest.name.isoformat() if hasattr(latest.name, 'isoformat') else str(latest.name)
            }
        
        except Exception as e:
            self.metrics.failed_calculations += 1
            self.logger.error(f"Calculation failed for {symbol}: {e}")
            return {'error': str(e), 'symbol': symbol}
    
    async def calculate_batch(self, symbols: list, benchmark: str = "SPY",
                             timeframe: str = "1d") -> list:
        """Calculate RSATR for multiple symbols"""
        tasks = [self.calculate_symbol(sym, benchmark, timeframe) for sym in symbols]
        return await asyncio.gather(*tasks)
    
    def get_status(self) -> Dict[str, Any]:
        """Get engine status"""
        return {
            'state': self.state.value,
            'metrics': {
                'total_calculations': self.metrics.total_calculations,
                'failed_calculations': self.metrics.failed_calculations,
                'avg_calculation_time_ms': self.metrics.avg_calculation_time_ms,
                'active_symbols': self.metrics.active_symbols
            },
            'config': {
                'rs_lookback': self.rsatr_engine.config.rs_lookback if self.rsatr_engine else None,
                'atr_length': self.rsatr_engine.config.atr_length if self.rsatr_engine else None,
                'smoothing_length': self.rsatr_engine.config.smoothing_length if self.rsatr_engine else None,
                'use_ema': self.rsatr_engine.config.use_ema if self.rsatr_engine else None
            }
        }
    
    async def shutdown(self):
        """Gracefully shutdown engine"""
        self.logger.info("Shutting down HiWay RSATR Engine...")
        self.state = EngineState.SHUTDOWN
        self.logger.info("Engine shutdown complete")
    
    def start_rest_api(self, host: str = '0.0.0.0', port: int = 5000):
        """Start REST API server"""
        self.logger.info(f"Starting REST API on {host}:{port}")
        self.rest_api.run(host, port, debug=self.config.get('debug', False))


def create_engine(config: Dict[str, Any] = None) -> HiWayEngine:
    """Factory function to create configured engine"""
    default_config = {
        'rs_lookback': 14,
        'atr_length': 14,
        'smoothing_length': 5,
        'use_ema': True,
        'data_provider': 'yahoo',
        'buffer_size': 1000,
        'stream_enabled': False,
        'debug': False
    }
    
    if config:
        default_config.update(config)
    
    return HiWayEngine(default_config)


if __name__ == '__main__':
    import sys
    
    async def main():
        engine = create_engine({
            'data_provider': 'yahoo',
            'stream_enabled': False
        })
        
        await engine.initialize()
        
        symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
        results = await engine.calculate_batch(symbols)
        
        for result in results:
            if 'error' not in result:
                print(f"{result['symbol']}: RS+ATR={result['rs_atr']:.4f}, Signal={result['signal']}")
            else:
                print(f"{result['symbol']}: Error - {result['error']}")
        
        print("\nEngine Status:")
        status = engine.get_status()
        print(f"  State: {status['state']}")
        print(f"  Total Calculations: {status['metrics']['total_calculations']}")
        print(f"  Failed: {status['metrics']['failed_calculations']}")
        
        await engine.shutdown()
    
    asyncio.run(main())
