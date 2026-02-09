"""
市場數據模型
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any
import pandas as pd


@dataclass
class TimeframeData:
    """單週期數據"""
    timeframe: str  # 時間週期（如 '1h', '4h', '1d'）
    ohlcv: pd.DataFrame  # OHLCV 數據
    indicators: Dict[str, pd.Series]  # 技術指標
    
    def get_latest(self) -> Dict[str, float]:
        """獲取最新數據點
        
        Returns:
            Dict[str, float]: 最新數據字典，包含 OHLCV 和所有指標
        """
        if self.ohlcv.empty:
            return {}
        
        latest = {}
        
        # 獲取最新的 OHLCV
        last_row = self.ohlcv.iloc[-1]
        latest['open'] = float(last_row['open'])
        latest['high'] = float(last_row['high'])
        latest['low'] = float(last_row['low'])
        latest['close'] = float(last_row['close'])
        latest['volume'] = float(last_row['volume'])
        
        # 獲取最新的指標值
        for indicator_name, indicator_series in self.indicators.items():
            if not indicator_series.empty:
                latest[indicator_name] = float(indicator_series.iloc[-1])
        
        return latest
    
    def get_at_index(self, index: int) -> Dict[str, float]:
        """獲取指定索引的數據點
        
        Args:
            index: 數據索引
            
        Returns:
            Dict[str, float]: 數據字典
        """
        if self.ohlcv.empty or index >= len(self.ohlcv):
            return {}
        
        data = {}
        
        # 獲取 OHLCV
        row = self.ohlcv.iloc[index]
        data['open'] = float(row['open'])
        data['high'] = float(row['high'])
        data['low'] = float(row['low'])
        data['close'] = float(row['close'])
        data['volume'] = float(row['volume'])
        
        # 獲取指標值
        for indicator_name, indicator_series in self.indicators.items():
            if not indicator_series.empty and index < len(indicator_series):
                data[indicator_name] = float(indicator_series.iloc[index])
        
        return data


@dataclass
class MarketData:
    """市場數據"""
    symbol: str  # 交易對
    timestamp: datetime  # 時間戳
    timeframes: Dict[str, TimeframeData]  # 週期 -> 數據
    
    def get_timeframe(self, timeframe: str) -> TimeframeData:
        """獲取指定週期的數據
        
        Args:
            timeframe: 時間週期（如 '1h', '4h', '1d'）
            
        Returns:
            TimeframeData: 週期數據
            
        Raises:
            KeyError: 週期不存在
        """
        if timeframe not in self.timeframes:
            raise KeyError(f"週期 {timeframe} 不存在，可用週期：{list(self.timeframes.keys())}")
        
        return self.timeframes[timeframe]
    
    def has_timeframe(self, timeframe: str) -> bool:
        """檢查是否有指定週期的數據
        
        Args:
            timeframe: 時間週期
            
        Returns:
            bool: 是否存在
        """
        return timeframe in self.timeframes
    
    def get_all_timeframes(self) -> list:
        """獲取所有可用的時間週期
        
        Returns:
            list: 時間週期列表
        """
        return list(self.timeframes.keys())
    
    def get_latest_price(self) -> float:
        """獲取最新價格（從最小週期）
        
        Returns:
            float: 最新價格
        """
        # 優先順序：15m > 1h > 4h > 1d
        priority = ['15m', '1h', '4h', '1d']
        
        for tf in priority:
            if tf in self.timeframes:
                latest = self.timeframes[tf].get_latest()
                if 'close' in latest:
                    return latest['close']
        
        # 如果沒有優先週期，使用第一個可用的
        if self.timeframes:
            first_tf = list(self.timeframes.values())[0]
            latest = first_tf.get_latest()
            if 'close' in latest:
                return latest['close']
        
        return 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典
        
        Returns:
            Dict[str, Any]: 市場數據字典
        """
        return {
            'symbol': self.symbol,
            'timestamp': self.timestamp.isoformat(),
            'timeframes': {
                tf: {
                    'timeframe': data.timeframe,
                    'latest': data.get_latest(),
                }
                for tf, data in self.timeframes.items()
            }
        }
