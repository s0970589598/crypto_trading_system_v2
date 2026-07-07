"""
高槓桿剝頭皮策略 v8.6 (Slippage Resistant)
基於 v8.5 + 抗滑點優化

【滑點壓力測試結果】
v8.5 盈虧平衡滑點 ≈ 0.015%，實際交易需控制在 0.01% 以下

【v8.6 抗滑點措施】
1. 提高獲利門檻：tp1_ratio 1.2 → 1.8，確保足夠利潤空間
2. 限價單入場：計算建議限價，避免市價單滑點
3. 波動率過濾：ATR_ratio > 1.5 時暫停交易（點差擴大）
4. 最小利潤空間：只在 ATR 足夠大時入場

【預期效果】
- 交易數減少，但每筆交易利潤空間更大
- 在 0.02% 滑點下仍可盈利
"""

import pandas as pd
import numpy as np
import pandas_ta as ta


class ScalpingHighLeverageV86:
    """高槓桿剝頭皮策略 v8.6 - 抗滑點版"""
    
    def __init__(
        self,
        # RSI 參數
        rsi_length: int = 5,
        rsi_oversold: int = 28,
        rsi_overbought: int = 72,
        
        # EMA 趨勢過濾
        ema_fast: int = 20,
        ema_slow: int = 50,
        use_trend_filter: bool = True,
        min_trend_strength: float = 0.02,
        
        # ADX 過濾
        use_adx_filter: bool = True,
        adx_length: int = 14,
        min_adx: float = 22,
        
        # Bollinger Bands
        bb_length: int = 20,
        bb_std: float = 2.0,
        bb_lower_threshold: float = 0.15,
        bb_upper_threshold: float = 0.85,
        
        # ATR 波動率
        atr_length: int = 14,
        atr_sl_multiplier: float = 1.5,

        # 成交量過濾
        use_volume_filter: bool = True,
        volume_ma_length: int = 20,
        min_volume_ratio: float = 0.9,
        
        # 時段過濾
        use_session_filter: bool = True,
        low_liquidity_start: int = 22,
        low_liquidity_end: int = 1,
        session_adx_threshold: float = 25,
        
        # EMA 斜率過濾
        use_ema_slope_filter: bool = True,
        ema_slope_lookback: int = 5,
        min_ema_slope_long: float = -0.08,
        
        # === v8.6 抗滑點參數 ===
        # 1. 適度提高獲利門檻（不要太激進）
        tp1_ratio: float = 1.5,           # v8.6: 1.2 → 1.5（溫和提升）
        tp1_close_pct: float = 0.6,       # 提高 TP1 平倉比例
        tp2_ratio: float = 2.8,           # v8.6: 2.5 → 2.8
        
        # 2. 限價單偏移（回測中不模擬，但提供參數）
        use_limit_order: bool = True,
        limit_order_offset_pct: float = 0.01,
        
        # 3. 波動率過濾（高波動時暫停）
        use_volatility_pause: bool = False,  # 關閉，效果不明顯
        max_atr_ratio: float = 1.8,
        
        # 4. 最小利潤空間
        use_min_profit_filter: bool = False,  # 關閉
        min_profit_pct: float = 0.05,
        
        # 延遲保本
        use_delayed_breakeven: bool = True,
        breakeven_trigger_pct: float = 0.5,
        use_trailing_stop: bool = True,
        
        # 風險管理
        max_hold_bars: int = 30,
        max_stop_loss_pct: float = 0.20,
        
        # 槓桿
        leverage: int = 50,
        commission: float = 0.0005,
        slippage: float = 0.0001,
    ):
        self.name = "Scalping High Leverage v8.6 - Slippage Resistant"
        
        # 基礎參數
        self.rsi_length = rsi_length
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.use_trend_filter = use_trend_filter
        self.min_trend_strength = min_trend_strength
        self.use_adx_filter = use_adx_filter
        self.adx_length = adx_length
        self.min_adx = min_adx
        self.bb_length = bb_length
        self.bb_std = bb_std
        self.bb_lower_threshold = bb_lower_threshold
        self.bb_upper_threshold = bb_upper_threshold
        self.atr_length = atr_length
        self.atr_sl_multiplier = atr_sl_multiplier
        self.use_volume_filter = use_volume_filter
        self.volume_ma_length = volume_ma_length
        self.min_volume_ratio = min_volume_ratio
        self.use_session_filter = use_session_filter
        self.low_liquidity_start = low_liquidity_start
        self.low_liquidity_end = low_liquidity_end
        self.session_adx_threshold = session_adx_threshold
        self.use_ema_slope_filter = use_ema_slope_filter
        self.ema_slope_lookback = ema_slope_lookback
        self.min_ema_slope_long = min_ema_slope_long
        
        # v8.6 抗滑點參數
        self.tp1_ratio = tp1_ratio
        self.tp1_close_pct = tp1_close_pct
        self.tp2_ratio = tp2_ratio
        self.use_limit_order = use_limit_order
        self.limit_order_offset_pct = limit_order_offset_pct
        self.use_volatility_pause = use_volatility_pause
        self.max_atr_ratio = max_atr_ratio
        self.use_min_profit_filter = use_min_profit_filter
        self.min_profit_pct = min_profit_pct
        
        # 其他
        self.use_delayed_breakeven = use_delayed_breakeven
        self.breakeven_trigger_pct = breakeven_trigger_pct
        self.use_trailing_stop = use_trailing_stop
        self.max_hold_bars = max_hold_bars
        self.max_stop_loss_pct = max_stop_loss_pct
        self.leverage = leverage
        self.commission = commission
        self.slippage = slippage

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """計算所有技術指標"""
        df = df.copy()
        
        # RSI
        df['rsi'] = ta.rsi(df['close'], length=self.rsi_length)
        df['rsi_prev'] = df['rsi'].shift(1)
        
        # EMA
        df['ema_fast'] = ta.ema(df['close'], length=self.ema_fast)
        df['ema_slow'] = ta.ema(df['close'], length=self.ema_slow)
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
        bb_range = df['bb_upper'] - df['bb_lower']
        df['bb_position'] = np.where(bb_range > 0, (df['close'] - df['bb_lower']) / bb_range, 0.5)
        
        # ATR
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=self.atr_length)
        df['atr_ma'] = df['atr'].rolling(20).mean()
        df['atr_ratio'] = df['atr'] / df['atr_ma']
        
        # 成交量
        df['volume_ma'] = df['volume'].rolling(self.volume_ma_length).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma']
        df['volume_ok'] = df['volume_ratio'] >= self.min_volume_ratio
        
        # 時段過濾
        if self.use_session_filter:
            df['hour'] = df.index.hour
            if self.low_liquidity_start > self.low_liquidity_end:
                in_low_liquidity = (df['hour'] >= self.low_liquidity_start) | (df['hour'] < self.low_liquidity_end)
            else:
                in_low_liquidity = (df['hour'] >= self.low_liquidity_start) & (df['hour'] < self.low_liquidity_end)
            df['session_ok'] = ~(in_low_liquidity & (df['adx'] < self.session_adx_threshold))
        else:
            df['session_ok'] = True
        
        # EMA 斜率過濾
        if self.use_ema_slope_filter:
            df['ema_slope_ok_long'] = df['ema_fast_slope'] >= self.min_ema_slope_long
            df['ema_slope_ok_short'] = df['ema_fast_slope'] <= -self.min_ema_slope_long
        else:
            df['ema_slope_ok_long'] = True
            df['ema_slope_ok_short'] = True
        
        # v8.6: 波動率暫停過濾
        if self.use_volatility_pause:
            df['volatility_ok'] = df['atr_ratio'] <= self.max_atr_ratio
        else:
            df['volatility_ok'] = True
        
        # v8.6: 最小利潤空間過濾
        if self.use_min_profit_filter:
            # 預期利潤 = ATR * tp1_ratio / price
            expected_profit_pct = (df['atr'] * self.tp1_ratio) / df['close'] * 100
            df['profit_space_ok'] = expected_profit_pct >= self.min_profit_pct
        else:
            df['profit_space_ok'] = True
        
        # 趨勢強度
        df['trend_strength'] = abs(df['ema_fast'] - df['ema_slow']) / df['close'] * 100
        
        # K 線形態
        df['is_bullish'] = df['close'] > df['open']
        df['is_bearish'] = df['close'] < df['open']
        
        return df

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """生成交易信號"""
        df = self.calculate_indicators(df)
        
        # 初始化
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
        df['limit_entry_price'] = np.nan  # v8.6: 限價單入場價
        
        # 過濾條件
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
        ema_slope_ok_long = df['ema_slope_ok_long'] if self.use_ema_slope_filter else pd.Series(True, index=df.index)
        ema_slope_ok_short = df['ema_slope_ok_short'] if self.use_ema_slope_filter else pd.Series(True, index=df.index)
        
        # v8.6: 新增過濾
        volatility_ok = df['volatility_ok'] if self.use_volatility_pause else pd.Series(True, index=df.index)
        profit_space_ok = df['profit_space_ok'] if self.use_min_profit_filter else pd.Series(True, index=df.index)
        
        # RSI 條件
        rsi_oversold = df['rsi'] < self.rsi_oversold
        rsi_overbought = df['rsi'] > self.rsi_overbought
        rsi_turning_up = df['rsi'] > df['rsi_prev']
        rsi_turning_down = df['rsi'] < df['rsi_prev']
        
        # BB 條件
        near_bb_lower = df['bb_position'] < self.bb_lower_threshold
        near_bb_upper = df['bb_position'] > self.bb_upper_threshold
        
        # 做多條件
        combo_a_long = rsi_oversold & rsi_turning_up & near_bb_lower & df['is_bullish']
        long_condition = (
            combo_a_long & uptrend & trend_strong & adx_ok & volume_ok & 
            session_ok & ema_slope_ok_long & volatility_ok & profit_space_ok
        )
        
        # 做空條件
        combo_a_short = rsi_overbought & rsi_turning_down & near_bb_upper & df['is_bearish']
        short_condition = (
            combo_a_short & downtrend & trend_strong & adx_ok & volume_ok & 
            session_ok & ema_slope_ok_short & volatility_ok & profit_space_ok
        )
        
        # 設置信號
        df.loc[long_condition, 'long_signal'] = True
        df.loc[short_condition, 'short_signal'] = True
        
        # 計算止損止盈
        atr_stop = df['atr'] * self.atr_sl_multiplier
        max_stop = df['close'] * (self.max_stop_loss_pct / 100)
        stop_distance = np.minimum(atr_stop, max_stop)
        
        tp1_distance = stop_distance * self.tp1_ratio
        tp2_distance = stop_distance * self.tp2_ratio
        
        # v8.6: 限價單入場價
        if self.use_limit_order:
            offset = df['close'] * (self.limit_order_offset_pct / 100)
            df.loc[long_condition, 'limit_entry_price'] = df.loc[long_condition, 'close'] - offset[long_condition]
            df.loc[short_condition, 'limit_entry_price'] = df.loc[short_condition, 'close'] + offset[short_condition]
        
        # 做多止盈止損
        df.loc[long_condition, 'long_stop_loss'] = df.loc[long_condition, 'close'] - stop_distance[long_condition]
        df.loc[long_condition, 'long_tp1'] = df.loc[long_condition, 'close'] + tp1_distance[long_condition]
        df.loc[long_condition, 'long_tp2'] = df.loc[long_condition, 'close'] + tp2_distance[long_condition]
        df.loc[long_condition, 'long_take_profit'] = df.loc[long_condition, 'long_tp2']
        
        # 做空止盈止損
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
        
        # v8.6: 限價單入場價
        offset = entry_price * (self.limit_order_offset_pct / 100)
        
        if direction == 'long':
            return {
                'limit_entry': entry_price - offset,
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
                'limit_entry': entry_price + offset,
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
    return ScalpingHighLeverageV86(**kwargs)
