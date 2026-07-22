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
        
        await self._emit_event('update', update)
        
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
