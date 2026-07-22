"""
HiWay RS+ATR Engine - Core Calculation Module
© hinesglobal4
Converts Pine Script RSATR logic to production-grade Python
"""

import numpy as np
import pandas as pd
from typing import Tuple, Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class RSATRConfig:
    """Configuration for RSATR calculation"""
    rs_lookback: int = 14
    atr_length: int = 14
    smoothing_length: int = 5
    use_ema: bool = True
    benchmark_symbol: str = "SPY"


class ATRCalculator:
    """Average True Range calculation"""
    
    @staticmethod
    def calculate(high: np.ndarray, low: np.ndarray, close: np.ndarray, 
                  period: int = 14) -> np.ndarray:
        """
        Calculate ATR using Wilder's Smoothing
        
        Args:
            high: High prices array
            low: Low prices array
            close: Close prices array
            period: ATR period (default 14)
            
        Returns:
            ATR values array
        """
        tr1 = high - low
        tr2 = np.abs(high - np.roll(close, 1))
        tr3 = np.abs(low - np.roll(close, 1))
        
        tr = np.max([tr1, tr2, tr3], axis=0)
        
        # Wilder's smoothing
        atr = np.zeros_like(tr, dtype=float)
        atr[period] = np.mean(tr[1:period+1])
        
        for i in range(period + 1, len(tr)):
            atr[i] = (atr[i-1] * (period - 1) + tr[i]) / period
        
        return atr


class RelativeStrengthCalculator:
    """Relative Strength (return-based) calculation"""
    
    @staticmethod
    def calculate_return(prices: np.ndarray, lookback: int) -> np.ndarray:
        """
        Calculate returns over lookback period
        
        Args:
            prices: Close prices array
            lookback: Lookback period
            
        Returns:
            Return values array
        """
        returns = np.zeros_like(prices, dtype=float)
        returns[lookback:] = (prices[lookback:] / prices[:-lookback] - 1)
        return returns
    
    @staticmethod
    def calculate_rs(stock_return: np.ndarray, 
                    benchmark_return: np.ndarray) -> np.ndarray:
        """
        Calculate Relative Strength as difference in returns
        
        Args:
            stock_return: Stock return array
            benchmark_return: Benchmark return array
            
        Returns:
            RS values array
        """
        return stock_return - benchmark_return


class SmoothingCalculator:
    """EMA and SMA smoothing"""
    
    @staticmethod
    def ema(series: np.ndarray, period: int) -> np.ndarray:
        """Calculate Exponential Moving Average"""
        result = np.zeros_like(series, dtype=float)
        multiplier = 2 / (period + 1)
        
        result[period-1] = np.mean(series[:period])
        
        for i in range(period, len(series)):
            if not np.isnan(series[i]):
                result[i] = series[i] * multiplier + result[i-1] * (1 - multiplier)
        
        return result
    
    @staticmethod
    def sma(series: np.ndarray, period: int) -> np.ndarray:
        """Calculate Simple Moving Average"""
        return pd.Series(series).rolling(window=period).mean().values


class RSATREngine:
    """Main HiWay RS+ATR calculation engine"""
    
    def __init__(self, config: RSATRConfig = None):
        self.config = config or RSATRConfig()
        self.atr_calc = ATRCalculator()
        self.rs_calc = RelativeStrengthCalculator()
        self.smooth_calc = SmoothingCalculator()
    
    def calculate(self, stock_data: Dict[str, np.ndarray], 
                 benchmark_data: Dict[str, np.ndarray]) -> np.ndarray:
        """
        Calculate RS+ATR indicator values
        
        Args:
            stock_data: {'high': array, 'low': array, 'close': array}
            benchmark_data: {'close': array}
            
        Returns:
            Smoothed RS+ATR values array
        """
        # Extract stock data
        stock_close = stock_data['close']
        stock_high = stock_data.get('high', stock_close)
        stock_low = stock_data.get('low', stock_close)
        benchmark_close = benchmark_data['close']
        
        # Calculate returns
        stock_return = self.rs_calc.calculate_return(
            stock_close, self.config.rs_lookback
        )
        benchmark_return = self.rs_calc.calculate_return(
            benchmark_close, self.config.rs_lookback
        )
        
        # Calculate RS
        relative_strength = self.rs_calc.calculate_rs(
            stock_return, benchmark_return
        )
        
        # Calculate ATR
        atr_value = self.atr_calc.calculate(
            stock_high, stock_low, stock_close, self.config.atr_length
        )
        
        # Normalize RS by ATR
        rs_atr = np.divide(relative_strength, atr_value, 
                          where=atr_value!=0, out=np.zeros_like(relative_strength))
        
        # Apply smoothing
        if self.config.use_ema:
            rs_atr_smoothed = self.smooth_calc.ema(rs_atr, self.config.smoothing_length)
        else:
            rs_atr_smoothed = self.smooth_calc.sma(rs_atr, self.config.smoothing_length)
        
        return rs_atr_smoothed
    
    def calculate_dataframe(self, stock_df: pd.DataFrame, 
                           benchmark_df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate RS+ATR for DataFrame input
        
        Args:
            stock_df: DataFrame with 'high', 'low', 'close' columns
            benchmark_df: DataFrame with 'close' column
            
        Returns:
            DataFrame with RS+ATR values
        """
        stock_data = {
            'high': stock_df['high'].values,
            'low': stock_df['low'].values,
            'close': stock_df['close'].values
        }
        benchmark_data = {
            'close': benchmark_df['close'].values
        }
        
        rs_atr_values = self.calculate(stock_data, benchmark_data)
        
        result_df = stock_df.copy()
        result_df['rs_atr'] = rs_atr_values
        result_df['signal'] = np.where(rs_atr_values >= 0, 1, -1)  # 1=bullish, -1=bearish
        
        return result_df
