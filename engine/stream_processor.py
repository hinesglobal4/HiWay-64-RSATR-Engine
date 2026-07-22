"""
HiWay RS+ATR Engine - Real-time Stream Processor
Handles live market data and indicator updates
"""

import asyncio
from typing import Callable, Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import pandas as pd
from collections import deque


@dataclass
class StreamUpdate:
    """Real-time market update"""
    symbol: str
    timestamp: datetime
    price: float
    bid: float
    ask: float
    volume: int
    bid_size: int
    ask_size: int


class CircularBuffer:
    """Memory-efficient circular buffer for streaming data"""
    
    def __init__(self, max_size: int):
        self.max_size = max_size
        self.buffer = deque(maxlen=max_size)
    
    def add(self, item):
        """Add item to buffer"""
        self.buffer.append(item)
    
    def get_numpy(self, key: str = None):
        """Get buffer as numpy array"""
        import numpy as np
        if key:
            return np.array([getattr(item, key, item[key]) for item in self.buffer])
        return np.array(list(self.buffer))
    
    def get_df(self, columns: Dict[str, str] = None) -> pd.DataFrame:
        """Get buffer as DataFrame"""
        if not self.buffer:
            return pd.DataFrame()
        
        data = {}
        for col, accessor in (columns or {}).items():
            data[col] = [getattr(item, accessor, item.get(accessor)) for item in self.buffer]
        
        return pd.DataFrame(data)


class StreamProcessor:
    """Processes real-time market data and computes indicators"""
    
    def __init__(self, buffer_size: int = 1000):
        self.buffer = CircularBuffer(buffer_size)
        self.callbacks: Dict[str, list] = {}
        self.last_update: Optional[datetime] = None
    
    def register_callback(self, event_type: str, callback: Callable):
        """Register callback for events"""
        if event_type not in self.callbacks:
            self.callbacks[event_type] = []
        self.callbacks[event_type].append(callback)
    
    async def process_update(self, update: StreamUpdate, 
                            indicator_func: Callable = None):
        """Process incoming market update"""
        self.buffer.add(update)
        self.last_update = update.timestamp
        
        # Fire callbacks
        await self._emit_event('update', update)
        
        # Compute indicator if provided
        if indicator_func:
            result = indicator_func()
            await self._emit_event('indicator', result)
    
    async def _emit_event(self, event_type: str, data: Any):
        """Emit event to registered callbacks"""
        if event_type not in self.callbacks:
            return
        
        tasks = [cb(data) for cb in self.callbacks[event_type]]
        if tasks:
            await asyncio.gather(*tasks)
    
    def get_current_data(self) -> Dict[str, Any]:
        """Get current buffered data"""
        if not self.buffer.buffer:
            return {}
        
        latest = self.buffer.buffer[-1]
        return {
            'timestamp': latest.timestamp,
            'price': latest.price,
            'bid': latest.bid,
            'ask': latest.ask,
            'spread': latest.ask - latest.bid,
            'volume': latest.volume,
            'buffer_size': len(self.buffer.buffer)
        }


class IndicatorStreamAdapter:
    """Adapts stream data to indicator calculations"""
    
    def __init__(self, processor: StreamProcessor, engine_calc_func: Callable):
        self.processor = processor
        self.engine_calc = engine_calc_func
    
    async def calculate_on_update(self, update: StreamUpdate):
        """Calculate indicator on each update"""
        df = self.processor.buffer.get_df({
            'timestamp': 'timestamp',
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'close': 'close'
        })
        
        if len(df) < 30:  # Need minimum bars
            return None
        
        result = self.engine_calc(df)
        return {
            'timestamp': update.timestamp,
            'rs_atr': result[-1],
            'signal': 1 if result[-1] >= 0 else -1
        }


class WebSocketHandler:
    """WebSocket connection handler for live streams"""
    
    def __init__(self, processor: StreamProcessor):
        self.processor = processor
        self.is_connected = False
    
    async def connect_alpaca(self, api_key: str):
        """Connect to Alpaca WebSocket (requires alpaca-py)"""
        try:
            from alpaca_trade_api.stream import Stream
            
            stream = Stream(api_key)
            
            async def on_bar(bar):
                update = StreamUpdate(
                    symbol=bar.symbol,
                    timestamp=bar.timestamp,
                    price=bar.close,
                    bid=bar.low,
                    ask=bar.high,
                    volume=bar.volume,
                    bid_size=0,
                    ask_size=0
                )
                await self.processor.process_update(update)
            
            stream.subscribe_bars(on_bar)
            await stream.run()
            self.is_connected = True
        except Exception as e:
            print(f"Alpaca WebSocket connection failed: {e}")
    
    async def connect_polygon(self, api_key: str):
        """Connect to Polygon WebSocket"""
        try:
            from polygon import WebSocketClient
            
            client = WebSocketClient(api_key)
            
            def on_message(data):
                for item in data:
                    update = StreamUpdate(
                        symbol=item.symbol,
                        timestamp=datetime.fromtimestamp(item.timestamp / 1000),
                        price=item.price,
                        bid=getattr(item, 'bid', item.price),
                        ask=getattr(item, 'ask', item.price),
                        volume=getattr(item, 'size', 0),
                        bid_size=0,
                        ask_size=0
                    )
                    asyncio.create_task(self.processor.process_update(update))
            
            client.on_message = on_message
            client.run()
            self.is_connected = True
        except Exception as e:
            print(f"Polygon WebSocket connection failed: {e}")
