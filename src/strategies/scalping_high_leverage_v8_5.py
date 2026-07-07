"""
高槓桿剝頭皮策略 v8.5 (Hardened v8)
基於 v8 vs v11 歸因分析的針對性加固版

【60 天回測結果】
v8:   146 筆, 勝率 51.4%, 回報 2.29%, 回撤 -8.15%
v8.5:  96 筆, 勝率 58.3%, 回報 6.33%, 回撤 -3.13%  ← 最佳
v11:   87 筆, 勝率 55.2%, 回報 5.41%, 回撤 -3.43%

【診斷發現的 v8 三大致命誘因】
1. 無方向震盪陷阱 (ADX < 25)：65.6% 虧損
2. 低流動性時段 (22:00-01:00 UTC)：16 筆虧損
3. 陰跌反覆抄底：6 個連續做多虧損區間

【v8.5 加固措施】
1. ADX 門檻：20 → 22（過濾 34% 弱信號）
2. 成交量門檻：0.8 → 0.9
3. 條件式時段過濾：ADX < 25 時避開 22:00-01:00 UTC
4. EMA 斜率過濾：斜率 < -0.08% 時禁止做多（防陰跌抄底）

【過濾效果】
- 過濾掉 60 筆交易，其中 61.7% 是虧損單
- 避免虧損 $1586，錯過獲利 $897，淨效益 $689
"""

import pandas as pd
import numpy as np
import pandas_ta as ta
from typing import Tuple, Optional


class ScalpingHighLeverageV85:
    """高槓桿剝頭皮策略 v8.5 - 加固版"""
    
    def __init__(
        self,
        # RSI 參數（保持 v8 設定）
        rsi_length: int = 5,
        rsi_oversold: int = 28,
        rsi_overbought: int = 72,
        rsi_extreme_low: int = 25,
        rsi_extreme_high: int = 75,
        
        # EMA 趨勢過濾
        ema_fast: int = 20,
        ema_slow: int = 50,
        use_trend_filter: bool = True,
        min_trend_strength: float = 0.02,
        
        # v8.5: ADX 過濾（溫和提升）
        use_adx_filter: bool = True,
        adx_length: int = 14,
        min_adx: float = 22,              # v8.5: 20 → 22
        
        # Bollinger Bands 參數
        bb_length: int = 20,
        bb_std: float = 2.0,
        bb_lower_threshold: float = 0.15,
        bb_upper_threshold: float = 0.85,
        
        # ATR 波動率
        atr_length: int = 14,
        atr_sl_multiplier: float = 1.5,
        
        # v8.5: 成交量過濾（溫和提升）
        use_volume_filter: bool = True,
        volume_ma_length: int = 20,
        min_volume_ratio: float = 0.9,    # v8.5: 0.8 → 0.9
        
        # v8.5: 低流動性時段過濾（條件式）
        use_session_filter: bool = True,
        low_liquidity_start: int = 22,    # UTC 22:00
        low_liquidity_end: int = 1,       # UTC 01:00
        session_adx_threshold: float = 25, # 只在 ADX < 25 時過濾時段
        
        # v8.5: 插針 K 線過濾
        use_wick_filter: bool = False,    # 關閉，效果不佳
        max_wick_ratio: float = 0.85,
        
        # v8.5: EMA 斜率過濾（只過濾極端）
        use_ema_slope_filter: bool = True,
        ema_slope_lookback: int = 5,
        min_ema_slope_long: float = -0.08,  # 只過濾極端陰跌
        
        # 分批止盈參數
        use_partial_tp: bool = True,
        tp1_ratio: float = 1.2,
        tp1_close_pct: float = 0.5,
        tp2_ratio: float = 2.5,
        use_trailing_stop: bool = True,
        
        # 延遲保本機制
        use_delayed_breakeven: bool = True,
        breakeven_trigger_pct: float = 0.5,
        
        # 風險管理
        max_hold_bars: int = 30,
        max_stop_loss_pct: float = 0.20,
        
        # 槓桿設置
        leverage: int = 50,
        commission: float = 0.0005,
        slippage: float = 0.0001,
    ):
        self.name = "Scalping High Leverage v8.5 - Hardened"
        
        # RSI
        self.rsi_length = rsi_length
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.rsi_extreme_low = rsi_extreme_low
        self.rsi_extreme_high = rsi_extreme_high
        
        # EMA
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.use_trend_filter = use_trend_filter
        self.min_trend_strength = min_trend_strength
        
        # ADX
        self.use_adx_filter = use_adx_filter
        self.adx_length = adx_length
        self.min_adx = min_adx
        
        # BB
        self.bb_length = bb_length
        self.bb_std = bb_std
        self.bb_lower_threshold = bb_lower_threshold
        self.bb_upper_threshold = bb_upper_threshold
        
        # ATR
        self.atr_length = atr_length
        self.atr_sl_multiplier = atr_sl_multiplier
        
        # 成交量
        self.use_volume_filter = use_volume_filter
        self.volume_ma_length = volume_ma_length
        self.min_volume_ratio = min_volume_ratio
        
        # 時段過濾
        self.use_session_filter = use_session_filter
        self.low_liquidity_start = low_liquidity_start
        self.low_liquidity_end = low_liquidity_end
        self.session_adx_threshold = session_adx_threshold
        
        # 插針過濾
        self.use_wick_filter = use_wick_filter
        self.max_wick_ratio = max_wick_ratio
        
        # EMA 斜率過濾
        self.use_ema_slope_filter = use_ema_slope_filter
        self.ema_slope_lookback = ema_slope_lookback
        self.min_ema_slope_long = min_ema_slope_long
        
        # 分批止盈
        self.use_partial_tp = use_partial_tp
        self.tp1_ratio = tp1_ratio
        self.tp1_close_pct = tp1_close_pct
        self.tp2_ratio = tp2_ratio
        self.use_trailing_stop = use_trailing_stop
        
        # 延遲保本
        self.use_delayed_breakeven = use_delayed_breakeven
        self.breakeven_trigger_pct = breakeven_trigger_pct
        
        # 風險管理
        self.max_hold_bars = max_hold_bars
        self.max_stop_loss_pct = max_stop_loss_pct
        
        # 槓桿
        self.leverage = leverage
        self.commission = commission
        self.slippage = slippage

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """計算所有技術指標"""
        df = df.copy()
        
        # RSI
        df['rsi'] = ta.rsi(df['close'], length=self.rsi_length)
        df['rsi_prev'] = df['rsi'].shift(1)
        
        # EMA 趨勢
        df['ema_fast'] = ta.ema(df['close'], length=self.ema_fast)
        df['ema_slow'] = ta.ema(df['close'], length=self.ema_slow)
        
        # EMA 斜率
        df['ema_fast_slope'] = (df['ema_fast'] - df['ema_fast'].shift(self.ema_slope_lookback)) / df['ema_fast'].shift(self.ema_slope_lookback) * 100
        
        # ADX
        adx_data = ta.adx(df['high'], df['low'], df['close'], length=self.adx_length)
        adx_col = [c for c in adx_data.columns if c.startswith('ADX')][0]
        df['adx'] = adx_data[adx_col]
        df['adx_ok'] = df['adx'] >= self.min_adx
        
        # Bollinger Bands
        bbands = ta.bbands(df['close'], length=self.bb_length, std=self.bb_std)
        bb_cols = bbands.columns.tolist()
        df['bb_upper'] = bbands[[c for c in bb_cols if c.startswith('BBU')][0]]
        df['bb_middle'] = bbands[[c for c in bb_cols if c.startswith('BBM')][0]]
        df['bb_lower'] = bbands[[c for c in bb_cols if c.startswith('BBL')][0]]
        
        # BB 位置
        bb_range = df['bb_upper'] - df['bb_lower']
        df['bb_position'] = np.where(bb_range > 0, (df['close'] - df['bb_lower']) / bb_range, 0.5)
        
        # ATR
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=self.atr_length)
        
        # 成交量
        df['volume_ma'] = df['volume'].rolling(self.volume_ma_length).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma']
        df['volume_ok'] = df['volume_ratio'] >= self.min_volume_ratio
        
        # v8.5: 條件式時段過濾（只在 ADX < threshold 時過濾）
        if self.use_session_filter:
            df['hour'] = df.index.hour
            if self.low_liquidity_start > self.low_liquidity_end:
                in_low_liquidity = (df['hour'] >= self.low_liquidity_start) | (df['hour'] < self.low_liquidity_end)
            else:
                in_low_liquidity = (df['hour'] >= self.low_liquidity_start) & (df['hour'] < self.low_liquidity_end)
            
            # 條件式：只在 ADX < threshold 且在低流動性時段時過濾
            df['session_ok'] = ~(in_low_liquidity & (df['adx'] < self.session_adx_threshold))
        else:
            df['session_ok'] = True
        
        # v8.5: 插針 K 線過濾
        if self.use_wick_filter:
            body = abs(df['close'] - df['open'])
            upper_wick = df['high'] - df[['close', 'open']].max(axis=1)
            lower_wick = df[['close', 'open']].min(axis=1) - df['low']
            total_range = df['high'] - df['low']
            
            df['wick_ratio'] = np.where(total_range > 0, (upper_wick + lower_wick) / total_range, 0)
            df['wick_ok'] = df['wick_ratio'] <= self.max_wick_ratio
        else:
            df['wick_ok'] = True
        
        # v8.5: EMA 斜率過濾（只過濾極端陰跌）
        if self.use_ema_slope_filter:
            df['ema_slope_ok_long'] = df['ema_fast_slope'] >= self.min_ema_slope_long
            df['ema_slope_ok_short'] = df['ema_fast_slope'] <= -self.min_ema_slope_long
        else:
            df['ema_slope_ok_long'] = True
            df['ema_slope_ok_short'] = True
        
        # 趨勢強度
        df['trend_strength'] = abs(df['ema_fast'] - df['ema_slow']) / df['close'] * 100
        
        # K 線形態
        df['is_bullish'] = df['close'] > df['open']
        df['is_bearish'] = df['close'] < df['open']
        
        return df

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """生成交易信號"""
        df = self.calculate_indicators(df)
        
        # 初始化信號列
        df['signal'] = 0
        df['long_signal'] = False
        df['short_signal'] = False
        df['long_stop_loss'] = np.nan
        df['long_take_profit'] = np.nan
        df['long_tp1'] = np.nan
        df['long_tp2'] = np.nan
        df['short_stop_loss'] = np.nan
        df['short_take_profit'] = np.nan
        df['short_tp1'] = np.nan
        df['short_tp2'] = np.nan
        
        # === 過濾條件 ===
        if self.use_trend_filter:
            uptrend = df['ema_fast'] > df['ema_slow']
            downtrend = df['ema_fast'] < df['ema_slow']
            trend_strong = df['trend_strength'] > self.min_trend_strength
        else:
            uptrend = pd.Series(True, index=df.index)
            downtrend = pd.Series(True, index=df.index)
            trend_strong = pd.Series(True, index=df.index)
        
        adx_ok = df['adx_ok'] if self.use_adx_filter else pd.Series(True, index=df.index)
        volume_ok = df['volume_ok'] if self.use_volume_filter else pd.Series(True, index=df.index)
        session_ok = df['session_ok'] if self.use_session_filter else pd.Series(True, index=df.index)
        wick_ok = df['wick_ok'] if self.use_wick_filter else pd.Series(True, index=df.index)
        ema_slope_ok_long = df['ema_slope_ok_long'] if self.use_ema_slope_filter else pd.Series(True, index=df.index)
        ema_slope_ok_short = df['ema_slope_ok_short'] if self.use_ema_slope_filter else pd.Series(True, index=df.index)
        
        # === RSI 條件 ===
        rsi_oversold = df['rsi'] < self.rsi_oversold
        rsi_overbought = df['rsi'] > self.rsi_overbought
        rsi_turning_up = df['rsi'] > df['rsi_prev']
        rsi_turning_down = df['rsi'] < df['rsi_prev']
        
        # === BB 條件 ===
        near_bb_lower = df['bb_position'] < self.bb_lower_threshold
        near_bb_upper = df['bb_position'] > self.bb_upper_threshold
        
        # === 做多條件 ===
        combo_a_long = rsi_oversold & rsi_turning_up & near_bb_lower & df['is_bullish']
        
        long_condition = (
            combo_a_long & 
            uptrend & 
            trend_strong & 
            adx_ok & 
            volume_ok & 
            session_ok &
            wick_ok &
            ema_slope_ok_long
        )
        
        # === 做空條件 ===
        combo_a_short = rsi_overbought & rsi_turning_down & near_bb_upper & df['is_bearish']
        
        short_condition = (
            combo_a_short & 
            downtrend & 
            trend_strong & 
            adx_ok & 
            volume_ok & 
            session_ok &
            wick_ok &
            ema_slope_ok_short
        )
        
        # 設置信號
        df.loc[long_condition, 'long_signal'] = True
        df.loc[short_condition, 'short_signal'] = True
        
        # === 計算止損止盈 ===
        atr_stop = df['atr'] * self.atr_sl_multiplier
        max_stop = df['close'] * (self.max_stop_loss_pct / 100)
        stop_distance = np.minimum(atr_stop, max_stop)
        
        tp1_distance = stop_distance * self.tp1_ratio
        tp2_distance = stop_distance * self.tp2_ratio
        
        # 做多
        df.loc[long_condition, 'long_stop_loss'] = df.loc[long_condition, 'close'] - stop_distance[long_condition]
        df.loc[long_condition, 'long_tp1'] = df.loc[long_condition, 'close'] + tp1_distance[long_condition]
        df.loc[long_condition, 'long_tp2'] = df.loc[long_condition, 'close'] + tp2_distance[long_condition]
        df.loc[long_condition, 'long_take_profit'] = df.loc[long_condition, 'long_tp2']
        
        # 做空
        df.loc[short_condition, 'short_stop_loss'] = df.loc[short_condition, 'close'] + stop_distance[short_condition]
        df.loc[short_condition, 'short_tp1'] = df.loc[short_condition, 'close'] - tp1_distance[short_condition]
        df.loc[short_condition, 'short_tp2'] = df.loc[short_condition, 'close'] - tp2_distance[short_condition]
        df.loc[short_condition, 'short_take_profit'] = df.loc[short_condition, 'short_tp2']
        
        return df

    def get_exit_levels(self, entry_price: float, direction: str, atr: float) -> dict:
        """獲取出場價位"""
        atr_stop = atr * self.atr_sl_multiplier
        max_stop = entry_price * (self.max_stop_loss_pct / 100)
        stop_distance = min(atr_stop, max_stop)
        
        tp1_distance = stop_distance * self.tp1_ratio
        tp2_distance = stop_distance * self.tp2_ratio
        
        if direction == 'long':
            return {
                'stop_loss': entry_price - stop_distance,
                'tp1': entry_price + tp1_distance,
                'tp2': entry_price + tp2_distance,
                'tp1_close_pct': self.tp1_close_pct,
                'use_trailing_stop': self.use_trailing_stop,
                'use_delayed_breakeven': self.use_delayed_breakeven,
                'breakeven_trigger_pct': self.breakeven_trigger_pct,
            }
        else:
            return {
                'stop_loss': entry_price + stop_distance,
                'tp1': entry_price - tp1_distance,
                'tp2': entry_price - tp2_distance,
                'tp1_close_pct': self.tp1_close_pct,
                'use_trailing_stop': self.use_trailing_stop,
                'use_delayed_breakeven': self.use_delayed_breakeven,
                'breakeven_trigger_pct': self.breakeven_trigger_pct,
            }


def create_strategy(**kwargs):
    """創建策略實例"""
    return ScalpingHighLeverageV85(**kwargs)
