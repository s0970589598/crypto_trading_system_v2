"""
高槓桿剝頭皮策略 v11 (Equity Curve Smoothing)
專為 25x-125x 槓桿設計

v11 更新（權益曲線平滑化版）：
基於 v10 分析結果的優化：
- 離群值問題：3 筆超大獲利 (17-20%) 支撐整體績效
- 多空不平衡：做多 73 筆 vs 做空 44 筆，空單勝率較低
- 持倉時間：5-10 分鐘勝率最低 (46.9%)
- 獲利回吐：29 筆交易回吐 > 3%

核心改進：
1. 波動率標定倉位 (Risk Parity) - 等風險貢獻
2. MFE 利潤保護 - 浮盈達 5% 後回落至 2% 強制平倉
3. 時間止損 - 5-10 分鐘未脫離成本區則平倉
4. 多空平衡 - 空單增加更嚴格過濾
5. 獲利曲線守護者 - 連續獲利後降低交易頻率
"""

import pandas as pd
import numpy as np
import pandas_ta as ta
from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum


class MarketRegime(Enum):
    LOW_VOL_RANGE = "low_vol_range"
    MID_VOL_TREND = "mid_vol_trend"
    HIGH_VOL_TREND = "high_vol_trend"
    HIGH_VOL_RANGE = "high_vol_range"


@dataclass
class RiskParityConfig:
    """風險平價配置"""
    target_risk_pct: float = 0.5      # 目標單筆風險 (佔總資金%)
    base_atr_reference: float = 0.0   # 基準 ATR (動態計算)
    min_position_scale: float = 0.3   # 最小倉位縮放
    max_position_scale: float = 1.5   # 最大倉位縮放


@dataclass
class ProfitProtection:
    """利潤保護配置"""
    mfe_trigger_pct: float = 5.0      # MFE 觸發閾值
    protection_floor_pct: float = 2.0  # 保護底線
    enabled: bool = True


@dataclass
class TimeStop:
    """時間止損配置"""
    danger_zone_start: int = 5        # 危險區開始 (分鐘)
    danger_zone_end: int = 10         # 危險區結束 (分鐘)
    cost_zone_pct: float = 0.5        # 成本區定義 (±0.5%)
    enabled: bool = True


class EquityCurveGuardian:
    """
    獲利曲線守護者
    
    功能：
    1. 追蹤連續獲利/虧損
    2. 連續獲利後降低交易頻率（防止過度交易）
    3. 連續虧損後暫停交易（v9 已有）
    """
    
    def __init__(
        self,
        consecutive_win_threshold: int = 3,   # 連續獲利閾值
        win_cooldown_bars: int = 30,          # 獲利後冷卻期
        consecutive_loss_threshold: int = 2,  # 連續虧損閾值
        loss_cooldown_bars: int = 60,         # 虧損後冷卻期
    ):
        self.consecutive_win_threshold = consecutive_win_threshold
        self.win_cooldown_bars = win_cooldown_bars
        self.consecutive_loss_threshold = consecutive_loss_threshold
        self.loss_cooldown_bars = loss_cooldown_bars
        
        self.consecutive_wins = 0
        self.consecutive_losses = 0
        self.cooldown_until = None
        self.total_profit_today = 0.0
    
    def record_trade(self, pnl: float, current_bar: int) -> None:
        """記錄交易結果"""
        if pnl > 0:
            self.consecutive_wins += 1
            self.consecutive_losses = 0
            self.total_profit_today += pnl
            
            # 連續獲利後冷卻
            if self.consecutive_wins >= self.consecutive_win_threshold:
                self.cooldown_until = current_bar + self.win_cooldown_bars
                self.consecutive_wins = 0  # 重置
        else:
            self.consecutive_losses += 1
            self.consecutive_wins = 0
            
            # 連續虧損後冷卻
            if self.consecutive_losses >= self.consecutive_loss_threshold:
                self.cooldown_until = current_bar + self.loss_cooldown_bars
                self.consecutive_losses = 0
    
    def can_trade(self, current_bar: int) -> bool:
        """檢查是否可以交易"""
        if self.cooldown_until is None:
            return True
        if current_bar >= self.cooldown_until:
            self.cooldown_until = None
            return True
        return False
    
    def reset_daily(self):
        """每日重置"""
        self.total_profit_today = 0.0


class RiskParityPositionSizer:
    """
    風險平價倉位計算器
    
    原理：確保每筆交易對總資金的「風險貢獻」恆定
    公式：Position Size = Target Risk / (ATR * Leverage)
    """
    
    def __init__(
        self,
        target_risk_pct: float = 0.5,    # 目標風險 0.5%
        atr_lookback: int = 60,          # ATR 參考期
        min_scale: float = 0.3,
        max_scale: float = 1.5,
    ):
        self.target_risk_pct = target_risk_pct
        self.atr_lookback = atr_lookback
        self.min_scale = min_scale
        self.max_scale = max_scale
        self.base_atr = None
    
    def update_base_atr(self, atr_series: pd.Series):
        """更新基準 ATR"""
        self.base_atr = atr_series.rolling(self.atr_lookback).mean().iloc[-1]
    
    def calculate_position_scale(
        self,
        current_atr: float,
        current_price: float,
        leverage: int
    ) -> float:
        """
        計算倉位縮放因子
        
        Args:
            current_atr: 當前 ATR
            current_price: 當前價格
            leverage: 槓桿倍數
        
        Returns:
            float: 倉位縮放因子 (0.3 - 1.5)
        """
        if self.base_atr is None or self.base_atr == 0:
            return 1.0
        
        # ATR 比率：當前波動 / 基準波動
        atr_ratio = current_atr / self.base_atr
        
        # 反向縮放：波動大時縮小倉位
        # scale = 1 / atr_ratio (但限制在 min-max 範圍)
        scale = 1.0 / atr_ratio
        
        return max(self.min_scale, min(self.max_scale, scale))
    
    def get_position_size_pct(
        self,
        base_position_pct: float,
        current_atr: float,
        current_price: float,
        leverage: int,
        equity_scale: float = 1.0
    ) -> float:
        """
        獲取最終倉位百分比
        
        Args:
            base_position_pct: 基礎倉位百分比
            current_atr: 當前 ATR
            current_price: 當前價格
            leverage: 槓桿倍數
            equity_scale: 權益曲線縮放因子
        
        Returns:
            float: 最終倉位百分比
        """
        vol_scale = self.calculate_position_scale(current_atr, current_price, leverage)
        return base_position_pct * vol_scale * equity_scale


class ScalpingHighLeverageV11:
    """高槓桿剝頭皮策略 v11 - 權益曲線平滑化版"""
    
    def __init__(
        self,
        # === 繼承 v10 參數 ===
        rsi_length: int = 5,
        rsi_oversold: int = 28,
        rsi_overbought: int = 72,
        rsi_extreme_low: int = 25,
        rsi_extreme_high: int = 75,
        ema_fast: int = 20,
        ema_slow: int = 50,
        use_trend_filter: bool = True,
        min_trend_strength: float = 0.02,
        use_adx_filter: bool = True,
        adx_length: int = 14,
        min_adx: float = 20,
        bb_length: int = 20,
        bb_std: float = 2.0,
        bb_lower_threshold: float = 0.15,
        bb_upper_threshold: float = 0.85,
        use_strong_signals_only: bool = True,
        atr_length: int = 14,
        atr_sl_multiplier: float = 1.5,
        use_regime_filter: bool = True,
        regime_lookback: int = 60,
        low_vol_threshold: float = 0.7,
        high_vol_threshold: float = 1.3,
        low_vol_atr_mult: float = 1.2,
        mid_vol_atr_mult: float = 1.5,
        high_vol_atr_mult: float = 1.8,
        skip_high_volatility: bool = False,
        use_session_filter: bool = True,
        avoid_low_liquidity: bool = True,
        low_liquidity_start: int = 21,
        low_liquidity_end: int = 1,
        use_volume_filter: bool = True,
        volume_ma_length: int = 20,
        min_volume_ratio: float = 0.8,
        
        # v10 參數
        use_order_flow_filter: bool = True,
        volume_surge_threshold: float = 1.5,
        use_tiered_rr: bool = True,
        low_vol_tp_ratio: float = 2.0,
        mid_vol_tp_ratio: float = 2.5,
        high_vol_trend_tp_ratio: float = 3.5,
        
        # === v11 新增參數 ===
        # 風險平價倉位
        use_risk_parity: bool = True,
        target_risk_pct: float = 0.5,
        risk_parity_min_scale: float = 0.3,
        risk_parity_max_scale: float = 1.5,
        
        # MFE 利潤保護
        use_mfe_protection: bool = True,
        mfe_trigger_pct: float = 5.0,
        mfe_protection_floor_pct: float = 2.0,
        
        # 時間止損
        use_time_stop: bool = True,
        time_stop_start: int = 5,
        time_stop_end: int = 10,
        cost_zone_pct: float = 0.5,
        
        # 多空平衡（空單更嚴格）
        use_short_filter: bool = True,
        short_min_adx: float = 25,           # 空單需要更強趨勢
        short_min_volume_ratio: float = 1.0, # 空單需要更大成交量
        
        # 獲利曲線守護者
        use_equity_guardian: bool = True,
        consecutive_win_threshold: int = 3,
        win_cooldown_bars: int = 30,
        consecutive_loss_threshold: int = 2,
        loss_cooldown_bars: int = 60,
        
        # 基礎參數
        use_partial_tp: bool = True,
        tp1_ratio: float = 1.2,
        tp1_close_pct: float = 0.5,
        tp2_ratio: float = 2.5,
        use_trailing_stop: bool = True,
        use_delayed_breakeven: bool = True,
        breakeven_trigger_pct: float = 0.5,
        max_hold_bars: int = 30,
        base_position_pct: float = 100,
        leverage: int = 50,
        commission: float = 0.0005,
        slippage: float = 0.0001,
        max_stop_loss_pct: float = 0.20,
        use_realtime_volatility: bool = True,
        min_candle_range_pct: float = 0.03,
        max_candle_range_pct: float = 0.15,
    ):
        self.name = "Scalping High Leverage v11 - Equity Curve Smoothing"
        
        # 繼承參數
        self.rsi_length = rsi_length
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.rsi_extreme_low = rsi_extreme_low
        self.rsi_extreme_high = rsi_extreme_high
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.use_trend_filter = use_trend_filter
        self.min_trend_strength = min_trend_strength
        self.use_adx_filter = use_adx_filter
        self.adx_length = adx_length
        self.min_adx = min_adx
        self.use_strong_signals_only = use_strong_signals_only
        self.bb_length = bb_length
        self.bb_std = bb_std
        self.bb_lower_threshold = bb_lower_threshold
        self.bb_upper_threshold = bb_upper_threshold
        self.atr_length = atr_length
        self.atr_sl_multiplier = atr_sl_multiplier
        self.use_regime_filter = use_regime_filter
        self.regime_lookback = regime_lookback
        self.low_vol_threshold = low_vol_threshold
        self.high_vol_threshold = high_vol_threshold
        self.low_vol_atr_mult = low_vol_atr_mult
        self.mid_vol_atr_mult = mid_vol_atr_mult
        self.high_vol_atr_mult = high_vol_atr_mult
        self.skip_high_volatility = skip_high_volatility
        self.use_session_filter = use_session_filter
        self.avoid_low_liquidity = avoid_low_liquidity
        self.low_liquidity_start = low_liquidity_start
        self.low_liquidity_end = low_liquidity_end
        self.use_volume_filter = use_volume_filter
        self.volume_ma_length = volume_ma_length
        self.min_volume_ratio = min_volume_ratio
        self.use_order_flow_filter = use_order_flow_filter
        self.volume_surge_threshold = volume_surge_threshold
        self.use_tiered_rr = use_tiered_rr
        self.low_vol_tp_ratio = low_vol_tp_ratio
        self.mid_vol_tp_ratio = mid_vol_tp_ratio
        self.high_vol_trend_tp_ratio = high_vol_trend_tp_ratio

        # v11 新增參數
        self.use_risk_parity = use_risk_parity
        self.target_risk_pct = target_risk_pct
        self.risk_parity_min_scale = risk_parity_min_scale
        self.risk_parity_max_scale = risk_parity_max_scale
        self.use_mfe_protection = use_mfe_protection
        self.mfe_trigger_pct = mfe_trigger_pct
        self.mfe_protection_floor_pct = mfe_protection_floor_pct
        self.use_time_stop = use_time_stop
        self.time_stop_start = time_stop_start
        self.time_stop_end = time_stop_end
        self.cost_zone_pct = cost_zone_pct
        self.use_short_filter = use_short_filter
        self.short_min_adx = short_min_adx
        self.short_min_volume_ratio = short_min_volume_ratio
        self.use_equity_guardian = use_equity_guardian
        self.consecutive_win_threshold = consecutive_win_threshold
        self.win_cooldown_bars = win_cooldown_bars
        self.consecutive_loss_threshold = consecutive_loss_threshold
        self.loss_cooldown_bars = loss_cooldown_bars
        
        # 基礎參數
        self.use_partial_tp = use_partial_tp
        self.tp1_ratio = tp1_ratio
        self.tp1_close_pct = tp1_close_pct
        self.tp2_ratio = tp2_ratio
        self.use_trailing_stop = use_trailing_stop
        self.use_delayed_breakeven = use_delayed_breakeven
        self.breakeven_trigger_pct = breakeven_trigger_pct
        self.max_hold_bars = max_hold_bars
        self.base_position_pct = base_position_pct
        self.leverage = leverage
        self.commission = commission
        self.slippage = slippage
        self.max_stop_loss_pct = max_stop_loss_pct
        self.use_realtime_volatility = use_realtime_volatility
        self.min_candle_range_pct = min_candle_range_pct
        self.max_candle_range_pct = max_candle_range_pct
        
        # 初始化模組
        self.position_sizer = RiskParityPositionSizer(
            target_risk_pct=target_risk_pct,
            min_scale=risk_parity_min_scale,
            max_scale=risk_parity_max_scale,
        )
        self.equity_guardian = EquityCurveGuardian(
            consecutive_win_threshold=consecutive_win_threshold,
            win_cooldown_bars=win_cooldown_bars,
            consecutive_loss_threshold=consecutive_loss_threshold,
            loss_cooldown_bars=loss_cooldown_bars,
        )
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """計算所有技術指標"""
        df = df.copy()
        
        # RSI
        df['rsi'] = ta.rsi(df['close'], length=self.rsi_length)
        df['rsi_prev'] = df['rsi'].shift(1)
        
        # EMA
        df['ema_fast'] = ta.ema(df['close'], length=self.ema_fast)
        df['ema_slow'] = ta.ema(df['close'], length=self.ema_slow)
        
        # ADX
        adx_data = ta.adx(df['high'], df['low'], df['close'], length=self.adx_length)
        adx_col = [c for c in adx_data.columns if c.startswith('ADX')][0]
        df['adx'] = adx_data[adx_col]
        df['adx_ok'] = df['adx'] >= self.min_adx
        df['adx_ok_short'] = df['adx'] >= self.short_min_adx  # v11: 空單更嚴格
        
        # Bollinger Bands
        bbands = ta.bbands(df['close'], length=self.bb_length, std=self.bb_std)
        bb_cols = bbands.columns.tolist()
        df['bb_upper'] = bbands[[c for c in bb_cols if c.startswith('BBU')][0]]
        df['bb_middle'] = bbands[[c for c in bb_cols if c.startswith('BBM')][0]]
        df['bb_lower'] = bbands[[c for c in bb_cols if c.startswith('BBL')][0]]
        
        bb_range = df['bb_upper'] - df['bb_lower']
        df['bb_position'] = np.where(bb_range > 0, (df['close'] - df['bb_lower']) / bb_range, 0.5)
        df['touch_bb_lower'] = df['low'] <= df['bb_lower']
        df['touch_bb_upper'] = df['high'] >= df['bb_upper']
        
        # ATR
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=self.atr_length)
        df['atr_ma'] = df['atr'].rolling(20).mean()
        df['atr_ratio'] = df['atr'] / df['atr_ma']
        
        # v11: 更新風險平價基準 ATR
        if self.use_risk_parity:
            self.position_sizer.update_base_atr(df['atr'])
        
        # 環境分類
        if self.use_regime_filter:
            df['atr_ma_long'] = df['atr'].rolling(self.regime_lookback).mean()
            df['regime_ratio'] = df['atr'] / df['atr_ma_long']
            df['regime'] = 'mid'
            df.loc[df['regime_ratio'] < self.low_vol_threshold, 'regime'] = 'low'
            df.loc[df['regime_ratio'] > self.high_vol_threshold, 'regime'] = 'high'
            
            df['dynamic_atr_mult'] = self.mid_vol_atr_mult
            df.loc[df['regime'] == 'low', 'dynamic_atr_mult'] = self.low_vol_atr_mult
            df.loc[df['regime'] == 'high', 'dynamic_atr_mult'] = self.high_vol_atr_mult
            
            df['regime_ok'] = ~df['regime'].isin(['high']) if self.skip_high_volatility else True
        else:
            df['regime'] = 'mid'
            df['dynamic_atr_mult'] = self.atr_sl_multiplier
            df['regime_ok'] = True
        
        # 時段過濾
        if self.use_session_filter and self.avoid_low_liquidity:
            df['hour'] = df.index.hour
            if self.low_liquidity_start > self.low_liquidity_end:
                df['low_liquidity'] = (df['hour'] >= self.low_liquidity_start) | (df['hour'] < self.low_liquidity_end)
            else:
                df['low_liquidity'] = (df['hour'] >= self.low_liquidity_start) & (df['hour'] < self.low_liquidity_end)
            df['session_ok'] = ~df['low_liquidity']
        else:
            df['session_ok'] = True
        
        # 成交量
        df['volume_ma'] = df['volume'].rolling(self.volume_ma_length).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma']
        df['volume_ok'] = df['volume_ratio'] >= self.min_volume_ratio
        df['volume_ok_short'] = df['volume_ratio'] >= self.short_min_volume_ratio  # v11: 空單更嚴格
        df['volume_surge'] = df['volume_ratio'] > self.volume_surge_threshold
        
        # 趨勢強度
        df['trend_strength'] = abs(df['ema_fast'] - df['ema_slow']) / df['close'] * 100
        
        # K 線形態
        df['is_bullish'] = df['close'] > df['open']
        df['is_bearish'] = df['close'] < df['open']
        
        # 即時波動過濾
        df['candle_range'] = df['high'] - df['low']
        df['candle_range_pct'] = (df['candle_range'] / df['close']) * 100
        df['recent_range_pct'] = df['candle_range_pct'].rolling(3).mean()
        df['realtime_volatility_ok'] = (
            (df['recent_range_pct'] >= self.min_candle_range_pct) &
            (df['recent_range_pct'] <= self.max_candle_range_pct)
        )
        
        # v11: 計算倉位縮放因子
        if self.use_risk_parity:
            df['position_scale'] = df.apply(
                lambda row: self.position_sizer.calculate_position_scale(
                    row['atr'], row['close'], self.leverage
                ) if pd.notna(row['atr']) else 1.0,
                axis=1
            )
        else:
            df['position_scale'] = 1.0
        
        return df

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """生成交易信號 - v11 權益曲線平滑化版"""
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
        adx_ok_short = df['adx_ok_short'] if self.use_short_filter else adx_ok
        
        volume_ok = df['volume_ok'] if self.use_volume_filter else pd.Series(True, index=df.index)
        volume_ok_short = df['volume_ok_short'] if self.use_short_filter else volume_ok
        
        session_ok = df['session_ok'] if self.use_session_filter else pd.Series(True, index=df.index)
        regime_ok = df['regime_ok'] if self.use_regime_filter else pd.Series(True, index=df.index)
        realtime_vol_ok = df['realtime_volatility_ok'] if self.use_realtime_volatility else pd.Series(True, index=df.index)
        
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
        long_condition = combo_a_long & uptrend & trend_strong & adx_ok & volume_ok & session_ok & regime_ok & realtime_vol_ok
        
        # === 做空條件（v11: 更嚴格）===
        combo_a_short = rsi_overbought & rsi_turning_down & near_bb_upper & df['is_bearish']
        short_condition = combo_a_short & downtrend & trend_strong & adx_ok_short & volume_ok_short & session_ok & regime_ok & realtime_vol_ok
        
        # 設置信號
        df.loc[long_condition, 'long_signal'] = True
        df.loc[short_condition, 'short_signal'] = True
        
        # === 計算止盈止損 ===
        for idx in df[long_condition | short_condition].index:
            row = df.loc[idx]
            regime = row['regime']
            
            # 動態盈虧比
            if regime == 'high':
                tp2_ratio = self.high_vol_trend_tp_ratio
            elif regime == 'low':
                tp2_ratio = self.low_vol_tp_ratio
            else:
                tp2_ratio = self.mid_vol_tp_ratio
            
            atr_stop = row['atr'] * row['dynamic_atr_mult']
            max_stop = row['close'] * (self.max_stop_loss_pct / 100)
            stop_distance = min(atr_stop, max_stop)
            
            tp1_distance = stop_distance * self.tp1_ratio
            tp2_distance = stop_distance * tp2_ratio
            
            if df.loc[idx, 'long_signal']:
                df.loc[idx, 'long_stop_loss'] = row['close'] - stop_distance
                df.loc[idx, 'long_tp1'] = row['close'] + tp1_distance
                df.loc[idx, 'long_tp2'] = row['close'] + tp2_distance
                df.loc[idx, 'long_take_profit'] = df.loc[idx, 'long_tp2']
            
            if df.loc[idx, 'short_signal']:
                df.loc[idx, 'short_stop_loss'] = row['close'] + stop_distance
                df.loc[idx, 'short_tp1'] = row['close'] - tp1_distance
                df.loc[idx, 'short_tp2'] = row['close'] - tp2_distance
                df.loc[idx, 'short_take_profit'] = df.loc[idx, 'short_tp2']
        
        return df

    def get_position_size_pct(
        self,
        current_atr: float,
        current_price: float,
        equity_scale: float = 1.0
    ) -> float:
        """
        v11 倉位計算公式
        
        Position Size = Base Size × Vol Scale × Equity Scale
        
        其中：
        - Vol Scale = Base ATR / Current ATR (風險平價)
        - Equity Scale = 回撤調整因子
        """
        if not self.use_risk_parity:
            return self.base_position_pct * equity_scale
        
        vol_scale = self.position_sizer.calculate_position_scale(
            current_atr, current_price, self.leverage
        )
        
        return self.base_position_pct * vol_scale * equity_scale
    
    def check_mfe_protection(
        self,
        entry_price: float,
        current_price: float,
        max_favorable_price: float,
        direction: str
    ) -> bool:
        """
        檢查 MFE 利潤保護是否觸發
        
        條件：浮盈曾達 5% 但回落至 2% 時強制平倉
        
        Returns:
            bool: True 表示應該平倉
        """
        if not self.use_mfe_protection:
            return False
        
        if direction == 'long':
            mfe_pct = (max_favorable_price - entry_price) / entry_price * 100
            current_pct = (current_price - entry_price) / entry_price * 100
        else:
            mfe_pct = (entry_price - max_favorable_price) / entry_price * 100
            current_pct = (entry_price - current_price) / entry_price * 100
        
        # MFE 達到觸發閾值，且當前利潤回落到保護底線
        if mfe_pct >= self.mfe_trigger_pct and current_pct <= self.mfe_protection_floor_pct:
            return True
        
        return False
    
    def check_time_stop(
        self,
        bars_held: int,
        entry_price: float,
        current_price: float,
        direction: str
    ) -> bool:
        """
        檢查時間止損是否觸發
        
        條件：持倉 5-10 分鐘且仍在成本區 (±0.5%)
        
        Returns:
            bool: True 表示應該平倉
        """
        if not self.use_time_stop:
            return False
        
        # 檢查是否在危險時間區間
        if not (self.time_stop_start <= bars_held <= self.time_stop_end):
            return False
        
        # 計算當前利潤
        if direction == 'long':
            current_pct = (current_price - entry_price) / entry_price * 100
        else:
            current_pct = (entry_price - current_price) / entry_price * 100
        
        # 檢查是否在成本區
        if abs(current_pct) <= self.cost_zone_pct:
            return True
        
        return False
    
    def get_exit_levels(
        self,
        entry_price: float,
        direction: str,
        atr: float,
        regime: str = 'mid',
        volume_ratio: float = 1.0,
    ) -> dict:
        """獲取出場價位（供 live_bot 使用）"""
        # 動態盈虧比
        if regime == 'high':
            tp2_ratio = self.high_vol_trend_tp_ratio
        elif regime == 'low':
            tp2_ratio = self.low_vol_tp_ratio
        else:
            tp2_ratio = self.mid_vol_tp_ratio
        
        # 動態 ATR 倍數
        if regime == 'low':
            atr_mult = self.low_vol_atr_mult
        elif regime == 'high':
            atr_mult = self.high_vol_atr_mult
        else:
            atr_mult = self.mid_vol_atr_mult
        
        atr_stop = atr * atr_mult
        max_stop = entry_price * (self.max_stop_loss_pct / 100)
        stop_distance = min(atr_stop, max_stop)
        
        tp1_distance = stop_distance * self.tp1_ratio
        tp2_distance = stop_distance * tp2_ratio
        
        if direction == 'long':
            return {
                'stop_loss': entry_price - stop_distance,
                'tp1': entry_price + tp1_distance,
                'tp2': entry_price + tp2_distance,
                'tp1_close_pct': self.tp1_close_pct,
                'use_mfe_protection': self.use_mfe_protection,
                'mfe_trigger_pct': self.mfe_trigger_pct,
                'mfe_protection_floor_pct': self.mfe_protection_floor_pct,
                'use_time_stop': self.use_time_stop,
                'time_stop_start': self.time_stop_start,
                'time_stop_end': self.time_stop_end,
                'cost_zone_pct': self.cost_zone_pct,
            }
        else:
            return {
                'stop_loss': entry_price + stop_distance,
                'tp1': entry_price - tp1_distance,
                'tp2': entry_price - tp2_distance,
                'tp1_close_pct': self.tp1_close_pct,
                'use_mfe_protection': self.use_mfe_protection,
                'mfe_trigger_pct': self.mfe_trigger_pct,
                'mfe_protection_floor_pct': self.mfe_protection_floor_pct,
                'use_time_stop': self.use_time_stop,
                'time_stop_start': self.time_stop_start,
                'time_stop_end': self.time_stop_end,
                'cost_zone_pct': self.cost_zone_pct,
            }


def create_strategy(**kwargs):
    """創建策略實例"""
    return ScalpingHighLeverageV11(**kwargs)


# ============================================================
# v11 倉位計算公式 (Python)
# ============================================================
"""
【風險平價倉位計算】

def calculate_position_size(
    base_position_pct: float,    # 基礎倉位 (如 10%)
    current_atr: float,          # 當前 ATR
    base_atr: float,             # 基準 ATR (60 期均值)
    equity_scale: float,         # 權益曲線縮放 (0.5-1.2)
    min_scale: float = 0.3,      # 最小縮放
    max_scale: float = 1.5,      # 最大縮放
) -> float:
    '''
    Position Size = Base × Vol Scale × Equity Scale
    
    Vol Scale = Base ATR / Current ATR
    - ATR 高 → 縮小倉位
    - ATR 低 → 放大倉位
    '''
    # 波動率縮放
    vol_scale = base_atr / current_atr if current_atr > 0 else 1.0
    vol_scale = max(min_scale, min(max_scale, vol_scale))
    
    # 最終倉位
    return base_position_pct * vol_scale * equity_scale


【獲利曲線守護者邏輯】

class EquityCurveGuardian:
    def should_trade(self, current_bar: int) -> Tuple[bool, str]:
        '''
        決定是否允許交易
        
        Returns:
            (can_trade, reason)
        '''
        # 連續 3 勝後冷卻 30 分鐘
        if self.consecutive_wins >= 3:
            self.cooldown_until = current_bar + 30
            self.consecutive_wins = 0
            return False, "連續獲利冷卻"
        
        # 連續 2 虧後冷卻 60 分鐘
        if self.consecutive_losses >= 2:
            self.cooldown_until = current_bar + 60
            self.consecutive_losses = 0
            return False, "連續虧損冷卻"
        
        # 冷卻期中
        if self.cooldown_until and current_bar < self.cooldown_until:
            return False, "冷卻期中"
        
        return True, "允許交易"


【MFE 利潤保護邏輯】

def check_profit_protection(
    entry_price: float,
    current_price: float,
    max_favorable_price: float,  # 持倉期間最高/最低價
    direction: str,
    mfe_trigger: float = 5.0,    # MFE 觸發閾值
    protection_floor: float = 2.0 # 保護底線
) -> bool:
    '''
    浮盈達 5% 後回落至 2% 時強制平倉
    '''
    if direction == 'long':
        mfe_pct = (max_favorable_price - entry_price) / entry_price * 100
        current_pct = (current_price - entry_price) / entry_price * 100
    else:
        mfe_pct = (entry_price - max_favorable_price) / entry_price * 100
        current_pct = (entry_price - current_price) / entry_price * 100
    
    # MFE 達標且利潤回落
    if mfe_pct >= mfe_trigger and current_pct <= protection_floor:
        return True  # 觸發保護，應該平倉
    
    return False
"""


def quick_test():
    """快速測試"""
    print("=" * 70)
    print("高槓桿剝頭皮策略 v11 (Equity Curve Smoothing)")
    print("=" * 70)
    print("\n基於 v10 分析的優化：")
    print("• 離群值：3 筆超大獲利 (17-20%) 支撐績效")
    print("• 多空不平衡：做多 73 筆 vs 做空 44 筆")
    print("• 持倉時間：5-10 分鐘勝率最低 (46.9%)")
    print("• 獲利回吐：29 筆交易回吐 > 3%")
    print("\nv11 新增功能：")
    print("• 風險平價倉位：ATR 高時自動縮小倉位")
    print("• MFE 利潤保護：浮盈 5% 回落至 2% 強制平倉")
    print("• 時間止損：5-10 分鐘未脫離成本區則平倉")
    print("• 多空平衡：空單 ADX >= 25, 成交量 >= 1.0x")
    print("• 獲利曲線守護者：連續 3 勝後冷卻 30 分鐘")
    print("\n使用方法：")
    print("./venv/bin/python tools/backtest.py --strategy scalping_v11 --days 60")
    print("=" * 70)


if __name__ == '__main__':
    quick_test()
