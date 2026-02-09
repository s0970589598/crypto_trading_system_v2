"""
多週期共振策略

基於多個時間週期的趨勢一致性進行交易決策。
遷移自 trading_alert_system.py
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
from datetime import datetime

from src.execution.strategy import Strategy
from src.models.config import StrategyConfig
from src.models.market_data import MarketData
from src.models.trading import Signal, Position


class MultiTimeframeStrategy(Strategy):
    """
    多週期共振策略
    
    進場條件：
    1. 4H 和 1H 趨勢一致（同為上升或下降）
    2. RSI 在 30-70 範圍內
    3. 價格接近 EMA（3% 以內）
    4. 成交量確認（> 平均值）
    
    出場條件：
    1. 止損：entry_price - (ATR * stop_loss_atr)
    2. 獲利：entry_price + (ATR * take_profit_atr)
    """
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        
        # 從配置中獲取參數
        params = config.parameters
        self.stop_loss_atr = params.get('stop_loss_atr', 1.5)
        self.take_profit_atr = params.get('take_profit_atr', 3.0)
        self.rsi_range = params.get('rsi_range', [30, 70])
        self.ema_distance = params.get('ema_distance', 0.03)
        self.volume_threshold = params.get('volume_threshold', 1.0)
    
    def generate_signal(self, market_data: MarketData) -> Signal:
        """
        生成交易信號
        
        Args:
            market_data: 市場數據（包含多週期 OHLCV 和指標）
        
        Returns:
            Signal: 交易信號
        """
        # 獲取各週期數據
        tf_1d = market_data.get_timeframe('1d')
        tf_4h = market_data.get_timeframe('4h')
        tf_1h = market_data.get_timeframe('1h')
        tf_15m = market_data.get_timeframe('15m')
        
        # 計算技術指標
        indicators = self._calculate_indicators(tf_1d, tf_4h, tf_1h, tf_15m)
        
        # 檢查進場條件
        should_enter, direction = self._check_entry_conditions(indicators)
        
        if not should_enter:
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
                metadata=indicators
            )
        
        # 生成進場信號
        price = indicators['price']
        atr = indicators['atr_1h']
        
        # 計算止損和目標
        if direction == 'long':
            stop_loss = price - (atr * self.stop_loss_atr)
            take_profit = price + (atr * self.take_profit_atr)
        else:
            stop_loss = price + (atr * self.stop_loss_atr)
            take_profit = price - (atr * self.take_profit_atr)
        
        # 計算倉位大小（由 BacktestEngine 或 LiveTrader 調用 calculate_position_size）
        position_size = 0.0  # 將由執行引擎計算
        
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
            position_size=position_size,
            confidence=confidence,
            metadata=indicators
        )
    
    def calculate_position_size(self, capital: float, price: float) -> float:
        """
        計算倉位大小
        
        Args:
            capital: 可用資金
            price: 當前價格
        
        Returns:
            float: 倉位大小（幣數）
        """
        # 使用配置的倉位比例
        position_value = capital * self.config.risk_management.position_size
        
        # 考慮槓桿
        leverage = self.config.risk_management.leverage
        position_value *= leverage
        
        # 轉換為幣數
        size = position_value / price
        
        return size
    
    def calculate_stop_loss(self, entry_price: float, direction: str, atr: float) -> float:
        """
        計算止損價格
        
        Args:
            entry_price: 進場價格
            direction: 方向（'long' 或 'short'）
            atr: ATR 值
        
        Returns:
            float: 止損價格
        """
        if direction == 'long':
            return entry_price - (atr * self.stop_loss_atr)
        else:
            return entry_price + (atr * self.stop_loss_atr)
    
    def calculate_take_profit(self, entry_price: float, direction: str, atr: float) -> float:
        """
        計算目標價格
        
        Args:
            entry_price: 進場價格
            direction: 方向（'long' 或 'short'）
            atr: ATR 值
        
        Returns:
            float: 目標價格
        """
        if direction == 'long':
            return entry_price + (atr * self.take_profit_atr)
        else:
            return entry_price - (atr * self.take_profit_atr)
    
    def should_exit(self, position: Position, market_data: MarketData) -> bool:
        """
        判斷是否應該出場
        
        Args:
            position: 當前持倉
            market_data: 市場數據
        
        Returns:
            bool: 是否應該出場
        """
        # 獲取當前價格
        tf_15m = market_data.get_timeframe('15m')
        current_price = tf_15m.get_latest()['close']
        
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
        
        # 檢查趨勢反轉
        tf_4h = market_data.get_timeframe('4h')
        tf_1h = market_data.get_timeframe('1h')
        
        trend_4h = self._calculate_trend(tf_4h.ohlcv)
        trend_1h = self._calculate_trend(tf_1h.ohlcv)
        
        # 如果趨勢反轉，提前出場
        if position.direction == 'long' and trend_4h == 'Downtrend' and trend_1h == 'Downtrend':
            return True
        if position.direction == 'short' and trend_4h == 'Uptrend' and trend_1h == 'Uptrend':
            return True
        
        return False
    
    def _calculate_indicators(self, tf_1d, tf_4h, tf_1h, tf_15m) -> Dict:
        """計算所有需要的技術指標"""
        # 計算趨勢
        trend_1d = self._calculate_trend(tf_1d.ohlcv)
        trend_4h = self._calculate_trend(tf_4h.ohlcv)
        trend_1h = self._calculate_trend(tf_1h.ohlcv)
        trend_15m = self._calculate_trend(tf_15m.ohlcv)
        
        # 計算 RSI
        rsi_15m = self._calculate_rsi(tf_15m.ohlcv, period=14)
        
        # 計算 ATR
        atr_1h = self._calculate_atr(tf_1h.ohlcv, period=14)
        
        # 計算 EMA
        ema20_1h = self._calculate_ema(tf_1h.ohlcv['close'], period=20)
        ema50_1h = self._calculate_ema(tf_1h.ohlcv['close'], period=50)
        
        # 獲取當前價格
        price = tf_1h.ohlcv.iloc[-1]['close']
        
        # 計算成交量比率
        volume_20d_avg = tf_15m.ohlcv['volume'].rolling(window=20).mean().iloc[-1]
        current_volume = tf_15m.ohlcv.iloc[-1]['volume']
        volume_ratio = current_volume / volume_20d_avg if volume_20d_avg > 0 else 0
        
        return {
            'trend_1d': trend_1d,
            'trend_4h': trend_4h,
            'trend_1h': trend_1h,
            'trend_15m': trend_15m,
            'rsi_15m': rsi_15m,
            'atr_1h': atr_1h,
            'price': price,
            'ema20_1h': ema20_1h,
            'ema50_1h': ema50_1h,
            'volume_ratio': volume_ratio
        }
    
    def _check_entry_conditions(self, indicators: Dict) -> tuple[bool, Optional[str]]:
        """
        檢查進場條件
        
        Returns:
            (should_enter, direction): 是否進場和方向
        """
        # 1. 檢查趨勢一致性（4H 和 1H）
        trend_4h = indicators['trend_4h']
        trend_1h = indicators['trend_1h']
        
        if trend_4h != trend_1h or trend_4h not in ['Uptrend', 'Downtrend']:
            return False, None
        
        direction = 'long' if trend_4h == 'Uptrend' else 'short'
        
        # 2. 檢查 RSI
        rsi = indicators['rsi_15m']
        if not (self.rsi_range[0] <= rsi <= self.rsi_range[1]):
            return False, None
        
        # 3. 檢查價格是否接近 EMA
        price = indicators['price']
        ema20 = indicators['ema20_1h']
        ema50 = indicators['ema50_1h']
        
        near_ema20 = abs(price - ema20) / ema20 < self.ema_distance
        near_ema50 = abs(price - ema50) / ema50 < self.ema_distance
        
        if not (near_ema20 or near_ema50):
            return False, None
        
        # 4. 檢查成交量
        if indicators['volume_ratio'] < self.volume_threshold:
            return False, None
        
        return True, direction
    
    def _calculate_confidence(self, indicators: Dict) -> float:
        """
        計算信號置信度（0-1）
        
        基於：
        - 趨勢強度
        - RSI 位置
        - 價格與 EMA 的距離
        - 成交量比率
        """
        confidence = 0.0
        
        # 趨勢一致性（最多 0.4）
        if indicators['trend_1d'] == indicators['trend_4h'] == indicators['trend_1h']:
            confidence += 0.4
        elif indicators['trend_4h'] == indicators['trend_1h']:
            confidence += 0.3
        
        # RSI 位置（最多 0.2）
        rsi = indicators['rsi_15m']
        if 40 <= rsi <= 60:
            confidence += 0.2
        elif 35 <= rsi <= 65:
            confidence += 0.15
        elif 30 <= rsi <= 70:
            confidence += 0.1
        
        # 價格與 EMA 的距離（最多 0.2）
        price = indicators['price']
        ema20 = indicators['ema20_1h']
        ema50 = indicators['ema50_1h']
        
        dist_ema20 = abs(price - ema20) / ema20
        dist_ema50 = abs(price - ema50) / ema50
        
        min_dist = min(dist_ema20, dist_ema50)
        if min_dist < 0.01:
            confidence += 0.2
        elif min_dist < 0.02:
            confidence += 0.15
        elif min_dist < 0.03:
            confidence += 0.1
        
        # 成交量（最多 0.2）
        volume_ratio = indicators['volume_ratio']
        if volume_ratio > 1.5:
            confidence += 0.2
        elif volume_ratio > 1.2:
            confidence += 0.15
        elif volume_ratio > 1.0:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _calculate_trend(self, df: pd.DataFrame) -> str:
        """
        計算趨勢方向
        
        使用 EMA 20 和 EMA 50 判斷趨勢
        """
        if len(df) < 50:
            return 'Unknown'
        
        ema20 = self._calculate_ema(df['close'], period=20)
        ema50 = self._calculate_ema(df['close'], period=50)
        
        if ema20 > ema50:
            return 'Uptrend'
        elif ema20 < ema50:
            return 'Downtrend'
        else:
            return 'Sideways'
    
    def _calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> float:
        """計算 RSI 指標"""
        if len(df) < period + 1:
            return 50.0
        
        close = df['close'].values
        delta = np.diff(close)
        
        gain = np.where(delta > 0, delta, 0)
        loss = np.where(delta < 0, -delta, 0)
        
        avg_gain = np.mean(gain[-period:])
        avg_loss = np.mean(loss[-period:])
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
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
    
    def _calculate_ema(self, series: pd.Series, period: int) -> float:
        """計算 EMA 指標"""
        if len(series) < period:
            return series.iloc[-1]
        
        ema = series.ewm(span=period, adjust=False).mean()
        return ema.iloc[-1]
