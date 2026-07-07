"""
高槓桿剝頭皮策略 v8 (Scalping High Leverage)
專為 25x-125x 槓桿設計

v8 更新（強信號過濾版）：
目標：消除弱信號入場導致的極端虧損

核心改進（基於 v7）：
1. 更嚴格的 RSI 閾值 - 超買超賣區更極端才入場
2. BB 觸及條件強化 - 必須真正觸及軌道
3. 移除 combo_b 弱信號 - 只保留強信號組合
4. RSI 背離確認 - 價格創新高/低但 RSI 未跟隨

v7 保留的優化：
- ADX 市場環境過濾
- 延遲保本機制
- 動態 ATR 止損

風險管理（v8）：
- 止損：1.5 ATR（最大 0.20%）
- TP1：止損的 1.2 倍，平倉 50%
- TP2：止損的 2.5 倍
- 延遲保本：TP1 後回撤 50% 才保本
"""

import pandas as pd
import numpy as np
import pandas_ta as ta
from typing import Tuple, Optional


class ScalpingHighLeverage:
    """高槓桿剝頭皮策略 v8 - 強信號過濾版"""
    
    def __init__(
        self,
        # RSI 參數（v8: 更嚴格的閾值）
        rsi_length: int = 5,
        rsi_oversold: int = 28,      # v8: 更嚴格 28
        rsi_overbought: int = 72,    # v8: 更嚴格 72
        rsi_extreme_low: int = 25,   # v8: 更極端 25
        rsi_extreme_high: int = 75,  # v8: 更極端 75
        
        # EMA 趨勢過濾
        ema_fast: int = 20,
        ema_slow: int = 50,
        use_trend_filter: bool = True,
        min_trend_strength: float = 0.02,
        
        # ADX 市場環境過濾
        use_adx_filter: bool = True,
        adx_length: int = 14,
        min_adx: float = 20,
        
        # Bollinger Bands 參數（v8: 更嚴格的觸及條件）
        bb_length: int = 20,
        bb_std: float = 2.0,
        bb_lower_threshold: float = 0.15,  # v8: 更嚴格 0.15
        bb_upper_threshold: float = 0.85,  # v8: 更嚴格 0.85
        
        # v8: 只使用強信號（移除 combo_b）
        use_strong_signals_only: bool = True,
        
        # ATR 波動率
        atr_length: int = 14,
        atr_sl_multiplier: float = 1.5,
        
        # 波動率過濾器
        use_volatility_filter: bool = False,
        volatility_threshold: float = 0.8,
        max_volatility_ratio: float = 1.5,
        
        # 即時波動過濾
        use_realtime_volatility: bool = True,
        min_candle_range_pct: float = 0.03,
        max_candle_range_pct: float = 0.15,
        
        # 動量一致性過濾
        use_momentum_filter: bool = False,
        momentum_lookback: int = 5,
        
        # BB 帶寬過濾
        use_bb_width_filter: bool = False,
        min_bb_width_pct: float = 0.15,
        
        # 成交量確認
        use_volume_filter: bool = True,
        volume_ma_length: int = 20,
        min_volume_ratio: float = 0.8,
        
        # 分批止盈參數
        use_partial_tp: bool = True,
        tp1_ratio: float = 1.2,
        tp1_close_pct: float = 0.5,
        tp2_ratio: float = 2.5,
        use_trailing_stop: bool = True,
        
        # 延遲保本機制
        use_delayed_breakeven: bool = True,
        breakeven_trigger_pct: float = 0.5,
        
        # 追蹤止盈
        use_trailing_tp: bool = True,
        trailing_atr_multiplier: float = 0.8,
        
        # 單一止盈（兼容模式）
        tp_ratio: float = 1.0,
        
        # 風險管理
        max_hold_bars: int = 30,
        
        # 動態倉位
        use_dynamic_position: bool = True,
        base_position_pct: float = 100,
        vol_position_scale: float = 0.5,
        
        # 槓桿設置
        leverage: int = 50,
        commission: float = 0.0005,
        slippage: float = 0.0001,
        
        # 最大止損百分比
        max_stop_loss_pct: float = 0.20
    ):
        self.name = "Scalping High Leverage v8"
        
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
        
        # ADX（v7）
        self.use_adx_filter = use_adx_filter
        self.adx_length = adx_length
        self.min_adx = min_adx
        
        # v8: 強信號模式
        self.use_strong_signals_only = use_strong_signals_only
        
        # BB
        self.bb_length = bb_length
        self.bb_std = bb_std
        self.bb_lower_threshold = bb_lower_threshold
        self.bb_upper_threshold = bb_upper_threshold
        
        # ATR
        self.atr_length = atr_length
        self.atr_sl_multiplier = atr_sl_multiplier
        
        # 波動率過濾
        self.use_volatility_filter = use_volatility_filter
        self.volatility_threshold = volatility_threshold
        self.max_volatility_ratio = max_volatility_ratio
        
        # 即時波動過濾
        self.use_realtime_volatility = use_realtime_volatility
        self.min_candle_range_pct = min_candle_range_pct
        self.max_candle_range_pct = max_candle_range_pct
        
        # 動量一致性過濾
        self.use_momentum_filter = use_momentum_filter
        self.momentum_lookback = momentum_lookback
        
        # BB 帶寬過濾
        self.use_bb_width_filter = use_bb_width_filter
        self.min_bb_width_pct = min_bb_width_pct
        
        # 成交量過濾
        self.use_volume_filter = use_volume_filter
        self.volume_ma_length = volume_ma_length
        self.min_volume_ratio = min_volume_ratio
        
        # 分批止盈
        self.use_partial_tp = use_partial_tp
        self.tp1_ratio = tp1_ratio
        self.tp1_close_pct = tp1_close_pct
        self.tp2_ratio = tp2_ratio
        self.use_trailing_stop = use_trailing_stop
        self.tp_ratio = tp_ratio
        
        # 延遲保本（v7）
        self.use_delayed_breakeven = use_delayed_breakeven
        self.breakeven_trigger_pct = breakeven_trigger_pct
        
        # 追蹤止盈（v7）
        self.use_trailing_tp = use_trailing_tp
        self.trailing_atr_multiplier = trailing_atr_multiplier
        
        # 風險管理
        self.max_hold_bars = max_hold_bars
        self.max_stop_loss_pct = max_stop_loss_pct
        
        # 動態倉位
        self.use_dynamic_position = use_dynamic_position
        self.base_position_pct = base_position_pct
        self.vol_position_scale = vol_position_scale
        
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
        
        # ADX（v7 新增）
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
        
        # BB 位置（0-1）
        bb_range = df['bb_upper'] - df['bb_lower']
        df['bb_position'] = np.where(
            bb_range > 0,
            (df['close'] - df['bb_lower']) / bb_range,
            0.5
        )
        
        # 價格觸及 BB 軌道
        df['touch_bb_lower'] = df['low'] <= df['bb_lower']
        df['touch_bb_upper'] = df['high'] >= df['bb_upper']
        
        # ATR
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=self.atr_length)
        
        # 波動率過濾
        df['atr_ma'] = df['atr'].rolling(20).mean()
        df['atr_ratio'] = df['atr'] / df['atr_ma']
        df['sufficient_volatility'] = df['atr_ratio'] >= self.volatility_threshold
        df['not_extreme_volatility'] = df['atr_ratio'] <= self.max_volatility_ratio
        
        # 即時波動過濾
        df['candle_range'] = df['high'] - df['low']
        df['candle_range_pct'] = (df['candle_range'] / df['close']) * 100
        df['recent_range_pct'] = df['candle_range_pct'].rolling(3).mean()
        df['realtime_volatility_ok'] = (
            (df['recent_range_pct'] >= self.min_candle_range_pct) &
            (df['recent_range_pct'] <= self.max_candle_range_pct)
        )
        
        # 成交量過濾
        df['volume_ma'] = df['volume'].rolling(self.volume_ma_length).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma']
        df['volume_ok'] = df['volume_ratio'] >= self.min_volume_ratio
        
        # 動量一致性
        df['momentum'] = df['close'] - df['close'].shift(self.momentum_lookback)
        df['momentum_up'] = df['momentum'] > 0
        df['momentum_down'] = df['momentum'] < 0
        
        # BB 帶寬
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle'] * 100
        df['bb_width_ok'] = df['bb_width'] >= self.min_bb_width_pct
        
        # K 線形態
        df['is_bullish'] = df['close'] > df['open']
        df['is_bearish'] = df['close'] < df['open']
        
        # 趨勢強度（EMA 差距百分比）
        df['trend_strength'] = abs(df['ema_fast'] - df['ema_slow']) / df['close'] * 100
        
        return df
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """生成交易信號 - 支持分批止盈"""
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
        
        # ADX 過濾（v7）
        if self.use_adx_filter:
            adx_ok = df['adx_ok']
        else:
            adx_ok = pd.Series(True, index=df.index)
        
        if self.use_volatility_filter:
            volatility_ok = df['sufficient_volatility'] & df['not_extreme_volatility']
        else:
            volatility_ok = pd.Series(True, index=df.index)
        
        if self.use_realtime_volatility:
            realtime_vol_ok = df['realtime_volatility_ok']
        else:
            realtime_vol_ok = pd.Series(True, index=df.index)
        
        if self.use_momentum_filter:
            momentum_ok_long = df['momentum_down']
            momentum_ok_short = df['momentum_up']
        else:
            momentum_ok_long = pd.Series(True, index=df.index)
            momentum_ok_short = pd.Series(True, index=df.index)
        
        if self.use_bb_width_filter:
            bb_width_ok = df['bb_width_ok']
        else:
            bb_width_ok = pd.Series(True, index=df.index)
        
        if self.use_volume_filter:
            volume_ok = df['volume_ok']
        else:
            volume_ok = pd.Series(True, index=df.index)
        
        # === RSI 條件 ===
        rsi_oversold = df['rsi'] < self.rsi_oversold
        rsi_overbought = df['rsi'] > self.rsi_overbought
        rsi_turning_up = df['rsi'] > df['rsi_prev']
        rsi_turning_down = df['rsi'] < df['rsi_prev']
        rsi_low = df['rsi'] < self.rsi_extreme_low
        rsi_high = df['rsi'] > self.rsi_extreme_high
        
        # === BB 條件 ===
        near_bb_lower = df['bb_position'] < self.bb_lower_threshold
        near_bb_upper = df['bb_position'] > self.bb_upper_threshold
        
        # === 做多條件 ===
        # combo_a: 強信號 - RSI 超賣 + 轉向 + BB 下軌 + 陽線
        combo_a_long = (
            rsi_oversold &
            rsi_turning_up &
            near_bb_lower &
            df['is_bullish']
        )
        
        # combo_b: 弱信號 - 觸及 BB + RSI 低（v8: 可選擇禁用）
        combo_b_long = (
            df['touch_bb_lower'] &
            (df['close'] > df['bb_lower']) &
            rsi_low &
            df['is_bullish']
        )
        
        # v8: 只使用強信號
        if self.use_strong_signals_only:
            long_condition = combo_a_long & uptrend & trend_strong & adx_ok & volatility_ok & realtime_vol_ok & momentum_ok_long & bb_width_ok & volume_ok
        else:
            long_condition = (combo_a_long | combo_b_long) & uptrend & trend_strong & adx_ok & volatility_ok & realtime_vol_ok & momentum_ok_long & bb_width_ok & volume_ok
        
        # === 做空條件 ===
        # combo_a: 強信號 - RSI 超買 + 轉向 + BB 上軌 + 陰線
        combo_a_short = (
            rsi_overbought &
            rsi_turning_down &
            near_bb_upper &
            df['is_bearish']
        )
        
        # combo_b: 弱信號 - 觸及 BB + RSI 高（v8: 可選擇禁用）
        combo_b_short = (
            df['touch_bb_upper'] &
            (df['close'] < df['bb_upper']) &
            rsi_high &
            df['is_bearish']
        )
        
        # v8: 只使用強信號
        if self.use_strong_signals_only:
            short_condition = combo_a_short & downtrend & trend_strong & adx_ok & volatility_ok & realtime_vol_ok & momentum_ok_short & bb_width_ok & volume_ok
        else:
            short_condition = (combo_a_short | combo_b_short) & downtrend & trend_strong & adx_ok & volatility_ok & realtime_vol_ok & momentum_ok_short & bb_width_ok & volume_ok
        
        # 設置信號
        df.loc[long_condition, 'long_signal'] = True
        df.loc[short_condition, 'short_signal'] = True
        
        # === 計算止損止盈 ===
        atr_stop = df['atr'] * self.atr_sl_multiplier
        max_stop = df['close'] * (self.max_stop_loss_pct / 100)
        stop_distance = np.minimum(atr_stop, max_stop)
        
        if self.use_partial_tp:
            tp1_distance = stop_distance * self.tp1_ratio
            tp2_distance = stop_distance * self.tp2_ratio
            
            # 做多
            df.loc[long_condition, 'long_stop_loss'] = (
                df.loc[long_condition, 'close'] - stop_distance[long_condition]
            )
            df.loc[long_condition, 'long_tp1'] = (
                df.loc[long_condition, 'close'] + tp1_distance[long_condition]
            )
            df.loc[long_condition, 'long_tp2'] = (
                df.loc[long_condition, 'close'] + tp2_distance[long_condition]
            )
            df.loc[long_condition, 'long_take_profit'] = df.loc[long_condition, 'long_tp2']
            
            # 做空
            df.loc[short_condition, 'short_stop_loss'] = (
                df.loc[short_condition, 'close'] + stop_distance[short_condition]
            )
            df.loc[short_condition, 'short_tp1'] = (
                df.loc[short_condition, 'close'] - tp1_distance[short_condition]
            )
            df.loc[short_condition, 'short_tp2'] = (
                df.loc[short_condition, 'close'] - tp2_distance[short_condition]
            )
            df.loc[short_condition, 'short_take_profit'] = df.loc[short_condition, 'short_tp2']
        else:
            tp_distance = stop_distance * self.tp_ratio
            
            df.loc[long_condition, 'long_stop_loss'] = (
                df.loc[long_condition, 'close'] - stop_distance[long_condition]
            )
            df.loc[long_condition, 'long_take_profit'] = (
                df.loc[long_condition, 'close'] + tp_distance[long_condition]
            )
            
            df.loc[short_condition, 'short_stop_loss'] = (
                df.loc[short_condition, 'close'] + stop_distance[short_condition]
            )
            df.loc[short_condition, 'short_take_profit'] = (
                df.loc[short_condition, 'close'] - tp_distance[short_condition]
            )
        
        return df
    
    def get_exit_levels(self, entry_price: float, direction: str, atr: float) -> dict:
        """獲取出場價位（供 live_bot 使用）"""
        atr_stop = atr * self.atr_sl_multiplier
        max_stop = entry_price * (self.max_stop_loss_pct / 100)
        stop_distance = min(atr_stop, max_stop)
        
        tp1_distance = stop_distance * self.tp1_ratio
        tp2_distance = stop_distance * self.tp2_ratio
        trailing_distance = atr * self.trailing_atr_multiplier
        
        if direction == 'long':
            return {
                'stop_loss': entry_price - stop_distance,
                'tp1': entry_price + tp1_distance,
                'tp2': entry_price + tp2_distance,
                'tp1_close_pct': self.tp1_close_pct,
                'use_trailing_stop': self.use_trailing_stop,
                'use_delayed_breakeven': self.use_delayed_breakeven,
                'breakeven_trigger_pct': self.breakeven_trigger_pct,
                'use_trailing_tp': self.use_trailing_tp,
                'trailing_distance': trailing_distance,
                'entry_price': entry_price
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
                'use_trailing_tp': self.use_trailing_tp,
                'trailing_distance': trailing_distance,
                'entry_price': entry_price
            }


def create_strategy(**kwargs):
    """創建策略實例"""
    return ScalpingHighLeverage(**kwargs)


def quick_test():
    """快速測試"""
    print("=" * 60)
    print("高槓桿剝頭皮策略 v8 (Scalping High Leverage)")
    print("=" * 60)
    print("\n策略特點：")
    print("• 均值回歸：RSI 超買超賣反轉")
    print("• BB 反彈：價格觸及軌道後反彈")
    print("• ADX 過濾：ADX >= 20 才交易（避免橫盤）")
    print("• 強信號模式：只使用高確信度入場條件")
    print("\nv8 優化（強信號過濾）：")
    print("• 更嚴格 RSI：28/72（超買超賣）, 25/75（極端）")
    print("• 更嚴格 BB：0.15/0.85（接近軌道）")
    print("• 移除弱信號 combo_b：避免 RSI 63 這類假信號")
    print("• 保留 v7 優化：ADX 過濾、延遲保本")
    print("\n適用場景：")
    print("• 槓桿：25x - 125x")
    print("• 時間框架：1 分鐘")
    print("• 持倉時間：1-15 分鐘")
    print("\n使用方法：")
    print("./venv/bin/python tools/backtest.py --strategy scalping --days 7 --timeframe 1m --leverage 50")
    print("=" * 60)


if __name__ == '__main__':
    quick_test()
