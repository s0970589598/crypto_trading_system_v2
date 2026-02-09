"""
突破策略

基於價格突破關鍵阻力/支撐位進行交易。
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional

from src.execution.strategy import Strategy
from src.models.config import StrategyConfig
from src.models.market_data import MarketData
from src.models.trading import Signal, Position


class BreakoutStrategy(Strategy):
    """
    突破策略
    
    進場條件：
    1. 價格突破 20 日高點（做多）或低點（做空）
    2. 成交量確認（> 1.5x 平均值）
    3. ATR 確認（波動性足夠）
    
    出場條件：
    1. 止損：entry_price - (ATR * stop_loss_atr)
    2. 獲利：entry_price + (ATR * take_profit_atr)
    """
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        
        # 從配置中獲取參數
        params = config.parameters
        self.lookback_period = params.get('lookback_period', 20)
        self.volume_threshold = params.get('volume_threshold', 1.5)
        self.atr_threshold = params.get('atr_threshold', 0.02)
        self.stop_loss_atr = params.get('stop_loss_atr', 2.0)
        self.take_profit_atr = params.get('take_profit_atr', 4.0)
    
    def generate_signal(self, market_data: MarketData) -> Signal:
        """
        生成交易信號
        
        Args:
            market_data: 市場數據
        
        Returns:
            Signal: 交易信號
        """
        # 獲取主要週期數據（使用 1h）
        tf_1h = market_data.get_timeframe('1h')
        
        # 檢查數據是否足夠
        if len(tf_1h.ohlcv) < self.lookback_period + 1:
            return self._hold_signal(market_data)
        
        # 計算指標
        indicators = self._calculate_indicators(tf_1h)
        
        # 檢查進場條件
        should_enter, direction = self._check_entry_conditions(indicators)
        
        if not should_enter:
            return self._hold_signal(market_data)
        
        # 生成進場信號
        price = indicators['price']
        atr = indicators['atr']
        
        # 計算止損和目標
        if direction == 'long':
            stop_loss = price - (atr * self.stop_loss_atr)
            take_profit = price + (atr * self.take_profit_atr)
        else:
            stop_loss = price + (atr * self.stop_loss_atr)
            take_profit = price - (atr * self.take_profit_atr)
        
        # 計算信號置信度
        confidence = self._calculate_confidence(indicators)
        
        return Signal(
            strategy_id=self.config.strategy_id,
            timestamp=market_data.timestamp,
            symbol=self.config.symbol,
            action='BUY' if direction == 'long' else 'SELL',
            direction=direction,
            entry_price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            position_size=self.config.risk_management.position_size,
            confidence=confidence,
            metadata=indicators
        )
    
    def calculate_position_size(self, capital: float, price: float) -> float:
        """計算倉位大小"""
        position_value = capital * self.config.risk_management.position_size
        leverage = self.config.risk_management.leverage
        position_value *= leverage
        size = position_value / price
        return size
    
    def calculate_stop_loss(self, entry_price: float, direction: str, atr: float) -> float:
        """計算止損價格"""
        if direction == 'long':
            return entry_price - (atr * self.stop_loss_atr)
        else:
            return entry_price + (atr * self.stop_loss_atr)
    
    def calculate_take_profit(self, entry_price: float, direction: str, atr: float) -> float:
        """計算目標價格"""
        if direction == 'long':
            return entry_price + (atr * self.take_profit_atr)
        else:
            return entry_price - (atr * self.take_profit_atr)
    
    def should_exit(self, position: Position, market_data: MarketData) -> bool:
        """判斷是否應該出場"""
        # 獲取當前價格
        tf_1h = market_data.get_timeframe('1h')
        current_price = tf_1h.get_latest()['close']
        
        # 檢查止損
        if position.direction == 'long':
            if current_price <= position.stop_loss:
                return True
        else:
            if current_price >= position.stop_loss:
                return True
        
        # 檢查獲利
        if position.direction == 'long':
            if current_price >= position.take_profit:
                return True
        else:
            if current_price <= position.take_profit:
                return True
        
        return False
    
    def _hold_signal(self, market_data: MarketData) -> Signal:
        """生成 HOLD 信號"""
        return Signal(
            strategy_id=self.config.strategy_id,
            timestamp=market_data.timestamp,
            symbol=self.config.symbol,
            action='HOLD',
            direction=None,
            entry_price=0.0,
            stop_loss=0.0,
            take_profit=0.0,
            position_size=0.0,
            confidence=0.0,
        )
    
    def _calculate_indicators(self, tf_data) -> Dict:
        """計算所有需要的技術指標"""
        df = tf_data.ohlcv
        
        # 獲取當前價格
        price = df.iloc[-1]['close']
        
        # 計算 N 日高點和低點
        high_n = df['high'].rolling(window=self.lookback_period).max().iloc[-2]  # 不包括當前K線
        low_n = df['low'].rolling(window=self.lookback_period).min().iloc[-2]
        
        # 計算 ATR
        atr = self._calculate_atr(df, period=14)
        
        # 計算成交量比率
        volume_ma = df['volume'].rolling(window=20).mean().iloc[-1]
        current_volume = df.iloc[-1]['volume']
        volume_ratio = current_volume / volume_ma if volume_ma > 0 else 0
        
        # 計算 ATR 百分比（波動性）
        atr_pct = atr / price if price > 0 else 0
        
        return {
            'price': price,
            'high_n': high_n,
            'low_n': low_n,
            'atr': atr,
            'atr_pct': atr_pct,
            'volume_ratio': volume_ratio,
        }
    
    def _check_entry_conditions(self, indicators: Dict) -> tuple[bool, Optional[str]]:
        """檢查進場條件"""
        price = indicators['price']
        high_n = indicators['high_n']
        low_n = indicators['low_n']
        volume_ratio = indicators['volume_ratio']
        atr_pct = indicators['atr_pct']
        
        # 檢查波動性
        if atr_pct < self.atr_threshold:
            return False, None
        
        # 檢查成交量
        if volume_ratio < self.volume_threshold:
            return False, None
        
        # 檢查突破
        if price > high_n:
            # 向上突破
            return True, 'long'
        elif price < low_n:
            # 向下突破
            return True, 'short'
        
        return False, None
    
    def _calculate_confidence(self, indicators: Dict) -> float:
        """計算信號置信度"""
        confidence = 0.0
        
        # 成交量確認（最多 0.4）
        volume_ratio = indicators['volume_ratio']
        if volume_ratio > 2.0:
            confidence += 0.4
        elif volume_ratio > 1.5:
            confidence += 0.3
        elif volume_ratio > 1.0:
            confidence += 0.2
        
        # 波動性確認（最多 0.3）
        atr_pct = indicators['atr_pct']
        if atr_pct > 0.04:
            confidence += 0.3
        elif atr_pct > 0.03:
            confidence += 0.2
        elif atr_pct > 0.02:
            confidence += 0.1
        
        # 突破強度（最多 0.3）
        price = indicators['price']
        high_n = indicators['high_n']
        low_n = indicators['low_n']
        
        if price > high_n:
            breakout_strength = (price - high_n) / high_n
            if breakout_strength > 0.02:
                confidence += 0.3
            elif breakout_strength > 0.01:
                confidence += 0.2
            else:
                confidence += 0.1
        elif price < low_n:
            breakout_strength = (low_n - price) / low_n
            if breakout_strength > 0.02:
                confidence += 0.3
            elif breakout_strength > 0.01:
                confidence += 0.2
            else:
                confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """計算 ATR 指標"""
        if len(df) < period + 1:
            return 0.0
        
        high = df['high'].values
        low = df['low'].values
        close = df['close'].values
        
        tr = np.maximum(
            high[1:] - low[1:],
            np.maximum(
                np.abs(high[1:] - close[:-1]),
                np.abs(low[1:] - close[:-1])
            )
        )
        
        atr = np.mean(tr[-period:])
        
        return atr
