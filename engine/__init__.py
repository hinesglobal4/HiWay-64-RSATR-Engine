"""HiWay RS+ATR Trade Engine Package"""
from .hiway_rs_atr_core import RSATREngine, RSATRConfig
from .data_provider import DataAggregator, AlpacaDataProvider, YahooFinanceDataProvider
from .orchestrator import HiWayEngine, create_engine

__version__ = '1.0.0'
__author__ = 'hinesglobal4'

__all__ = [
    'RSATREngine',
    'RSATRConfig',
    'DataAggregator',
    'AlpacaDataProvider',
    'YahooFinanceDataProvider',
    'HiWayEngine',
    'create_engine'
]
