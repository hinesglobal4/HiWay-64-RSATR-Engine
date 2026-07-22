"""
HiWay RS+ATR Engine - Data Provider Layer
Abstraction for multiple data sources (real-time APIs, historical data)
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional, Tuple, List
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dataclasses import dataclass


@dataclass
class BarData:
    """Bar/candle data structure"""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


class DataProvider(ABC):
    """Abstract base for data providers"""
    
    @abstractmethod
    def get_bars(self, symbol: str, timeframe: str, 
                 limit: int = 500) -> List[BarData]:
        """Get historical bars"""
        pass
    
    @abstractmethod
    def get_latest_bar(self, symbol: str, timeframe: str) -> BarData:
        """Get latest bar for symbol"""
        pass
    
    @abstractmethod
    def get_dataframe(self, symbol: str, timeframe: str, 
                      limit: int = 500) -> pd.DataFrame:
        """Get bars as DataFrame"""
        pass


class AlpacaDataProvider(DataProvider):
    """Alpaca Markets data provider"""
    
    def __init__(self, api_key: str, secret_key: str, base_url: str = None):
        try:
            from alpaca_trade_api import REST
            self.api = REST(api_key, secret_key, base_url or "https://api.alpaca.markets")
        except ImportError:
            raise ImportError("alpaca-trade-api not installed")
    
    def get_bars(self, symbol: str, timeframe: str, limit: int = 500) -> List[BarData]:
        """Fetch bars from Alpaca"""
        try:
            bars = self.api.get_bars(symbol, timeframe, limit=limit)
            return [
                BarData(
                    timestamp=bar.t,
                    open=bar.o,
                    high=bar.h,
                    low=bar.l,
                    close=bar.c,
                    volume=bar.v
                )
                for bar in bars
            ]
        except Exception as e:
            raise RuntimeError(f"Alpaca data fetch failed: {e}")
    
    def get_latest_bar(self, symbol: str, timeframe: str) -> BarData:
        """Get latest bar"""
        bars = self.get_bars(symbol, timeframe, limit=1)
        return bars[0] if bars else None
    
    def get_dataframe(self, symbol: str, timeframe: str, limit: int = 500) -> pd.DataFrame:
        """Get bars as DataFrame"""
        bars = self.get_bars(symbol, timeframe, limit)
        return pd.DataFrame([
            {
                'timestamp': bar.timestamp,
                'open': bar.open,
                'high': bar.high,
                'low': bar.low,
                'close': bar.close,
                'volume': bar.volume
            }
            for bar in bars
        ])


class PolygonDataProvider(DataProvider):
    """Polygon.io data provider"""
    
    def __init__(self, api_key: str):
        try:
            from polygon import RESTClient
            self.client = RESTClient(api_key)
        except ImportError:
            raise ImportError("polygon-api-client not installed")
    
    def get_bars(self, symbol: str, timeframe: str, limit: int = 500) -> List[BarData]:
        """Fetch bars from Polygon"""
        try:
            timeframe_map = {'1min': '1', '5min': '5', '15min': '15', 
                           '1h': '60', '1d': 'day'}
            poly_timeframe = timeframe_map.get(timeframe, timeframe)
            
            bars = self.client.list_aggs(symbol, 1, poly_timeframe, limit=limit)
            
            return [
                BarData(
                    timestamp=datetime.fromtimestamp(bar.timestamp / 1000),
                    open=bar.open,
                    high=bar.high,
                    low=bar.low,
                    close=bar.close,
                    volume=bar.volume
                )
                for bar in bars
            ]
        except Exception as e:
            raise RuntimeError(f"Polygon data fetch failed: {e}")
    
    def get_latest_bar(self, symbol: str, timeframe: str) -> BarData:
        """Get latest bar"""
        bars = self.get_bars(symbol, timeframe, limit=1)
        return bars[-1] if bars else None
    
    def get_dataframe(self, symbol: str, timeframe: str, limit: int = 500) -> pd.DataFrame:
        """Get bars as DataFrame"""
        bars = self.get_bars(symbol, timeframe, limit)
        return pd.DataFrame([
            {
                'timestamp': bar.timestamp,
                'open': bar.open,
                'high': bar.high,
                'low': bar.low,
                'close': bar.close,
                'volume': bar.volume
            }
            for bar in bars
        ]).set_index('timestamp')


class YahooFinanceDataProvider(DataProvider):
    """Yahoo Finance data provider (free, for backtesting)"""
    
    def __init__(self):
        try:
            import yfinance
            self.yf = yfinance
        except ImportError:
            raise ImportError("yfinance not installed")
    
    def get_bars(self, symbol: str, timeframe: str, limit: int = 500) -> List[BarData]:
        """Fetch bars from Yahoo Finance"""
        try:
            period_map = {'1d': f'{limit}d', '1h': '60d', '15min': '60d'}
            period = period_map.get(timeframe, '1y')
            
            ticker = self.yf.Ticker(symbol)
            hist = ticker.history(period=period, interval=timeframe)
            
            bars = []
            for idx, row in hist.tail(limit).iterrows():
                bars.append(BarData(
                    timestamp=idx,
                    open=row['Open'],
                    high=row['High'],
                    low=row['Low'],
                    close=row['Close'],
                    volume=int(row['Volume'])
                ))
            return bars
        except Exception as e:
            raise RuntimeError(f"Yahoo Finance fetch failed: {e}")
    
    def get_latest_bar(self, symbol: str, timeframe: str) -> BarData:
        """Get latest bar"""
        bars = self.get_bars(symbol, timeframe, limit=1)
        return bars[-1] if bars else None
    
    def get_dataframe(self, symbol: str, timeframe: str, limit: int = 500) -> pd.DataFrame:
        """Get bars as DataFrame"""
        bars = self.get_bars(symbol, timeframe, limit)
        return pd.DataFrame([
            {
                'timestamp': bar.timestamp,
                'open': bar.open,
                'high': bar.high,
                'low': bar.low,
                'close': bar.close,
                'volume': bar.volume
            }
            for bar in bars
        ]).set_index('timestamp')


class DataAggregator:
    """Manages multiple data providers with failover"""
    
    def __init__(self, primary_provider: DataProvider, 
                 fallback_providers: List[DataProvider] = None):
        self.primary = primary_provider
        self.fallbacks = fallback_providers or []
    
    def get_bars(self, symbol: str, timeframe: str, limit: int = 500) -> pd.DataFrame:
        """Get bars with automatic failover"""
        providers = [self.primary] + self.fallbacks
        
        for provider in providers:
            try:
                return provider.get_dataframe(symbol, timeframe, limit)
            except Exception as e:
                print(f"Provider {provider.__class__.__name__} failed: {e}")
                continue
        
        raise RuntimeError("All data providers failed")
