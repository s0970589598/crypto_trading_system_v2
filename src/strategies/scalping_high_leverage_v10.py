"""
高槓桿剝頭皮策略 v10 (Scalping High Leverage - Adaptive Trend Riding)
專為 25x-125x 槓桿設計

v10 更新（自適應利潤奔跑版）：
目標：在保持低回撤的同時，提升獲利能力

核心改進（基於 v9）：
1. 訂單流強度過濾 (Order Flow/Volume Delta)
   - 觸發 TP1 時，若成交量 > 20MA * 1.5，延遲平倉改為追蹤止損
2. 盈虧比階梯化 (Tiered Risk-Reward)
   - 高波動趨勢市：目標盈虧比 3.5
   - 低波動震盪市：維持快進快出
3. 回撤恢復因子 (Recovery Factor)
   - 權益新高時：標準倉位
   - 回撤期：凱利公式變體微調倉位

風險管理（v10）：
- 止損：動態 1.2-1.8 ATR（根據環境）
- TP1：動態調整（根據成交量決定是否延遲）
- TP2：環境自適應（高波動 3.5x，低波動 2.0x）
- 追蹤止損：ATR 0.6-1.0 倍（根據趨勢強度）
"""

import pandas as pd
import numpy as np
import pandas_ta as ta
from typing import Tuple, Optional, Dict
from dataclasses import dataclass
from enum import Enum


class MarketRegime(Enum):
    """市場環境分類"""
    LOW_VOL_RANGE = "low_vol_range"      # 低波動震盪
    MID_VOL_TREND = "mid_vol_trend"      # 中波動趨勢
    HIGH_VOL_TREND = "high_vol_trend"    # 高波動趨勢
    HIGH_VOL_RANGE = "high_vol_range"    # 高波動震盪（危險）


@dataclass
class AdaptiveTakeProfit:
    """自適應止盈配置"""
    tp1_ratio: float           # TP1 盈虧比
    tp1_close_pct: float       # TP1 平倉比例
    tp2_ratio: float           # TP2 盈虧比
    use_trailing: bool         # 是否使用追蹤止損
    trailing_atr_mult: float   # 追蹤止損 ATR 倍數
    delay_tp1_on_volume: bool  # 成交量大時延遲 TP1


@dataclass
class PositionSizing:
    """倉位管理配置"""
    base_pct: float            # 基礎倉位百分比
    kelly_fraction: float      # 凱利係數
    max_drawdown_scale: float  # 回撤時的倉位縮放


class AdaptiveTrendRiding:
    """
    v10 核心模組：自適應利潤奔跑
    
    功能：
    1. 根據成交量動態調整 TP1 平倉策略
    2. 根據市場環境調整盈虧比
    3. 根據權益曲線調整倉位
    """
    
    def __init__(
        self,
        # 訂單流參數
        volume_ma_length: int = 20,
        volume_surge_threshold: float = 1.5,  # 成交量激增閾值
        
        # 環境自適應盈虧比
        low_vol_tp_ratio: float = 2.0,        # 低波動：快進快出
        mid_vol_tp_ratio: float = 2.5,        # 中波動：標準
        high_vol_trend_tp_ratio: float = 3.5, # 高波動趨勢：利潤奔跑
        
        # 追蹤止損參數
        base_trailing_atr: float = 0.8,
        tight_trailing_atr: float = 0.6,      # 趨勢強時更緊
        loose_trailing_atr: float = 1.0,      # 趨勢弱時更鬆
        
        # 凱利公式參數
        kelly_win_rate: float = 0.55,         # 預估勝率
        kelly_avg_win: float = 1.5,           # 平均獲利倍數
        kelly_avg_loss: float = 1.0,          # 平均虧損倍數
        kelly_fraction: float = 0.25,         # 凱利係數使用比例（保守）
        
        # 回撤恢復參數
        drawdown_threshold: float = 0.03,     # 3% 回撤觸發
        recovery_scale_min: float = 0.5,      # 最小倉位縮放
        recovery_scale_max: float = 1.2,      # 恢復期最大倉位
    ):
        self.volume_ma_length = volume_ma_length
        self.volume_surge_threshold = volume_surge_threshold
        
        self.low_vol_tp_ratio = low_vol_tp_ratio
        self.mid_vol_tp_ratio = mid_vol_tp_ratio
        self.high_vol_trend_tp_ratio = high_vol_trend_tp_ratio
        
        self.base_trailing_atr = base_trailing_atr
        self.tight_trailing_atr = tight_trailing_atr
        self.loose_trailing_atr = loose_trailing_atr
        
        self.kelly_win_rate = kelly_win_rate
        self.kelly_avg_win = kelly_avg_win
        self.kelly_avg_loss = kelly_avg_loss
        self.kelly_fraction = kelly_fraction
        
        self.drawdown_threshold = drawdown_threshold
        self.recovery_scale_min = recovery_scale_min
        self.recovery_scale_max = recovery_scale_max

    def classify_market_regime(
        self, 
        atr_ratio: float, 
        adx: float, 
        trend_strength: float
    ) -> MarketRegime:
        """
        分類市場環境
        
        Args:
            atr_ratio: ATR / ATR_MA（波動率比率）
            adx: ADX 值（趨勢強度）
            trend_strength: EMA 趨勢強度
        
        Returns:
            MarketRegime: 市場環境分類
        """
        is_high_vol = atr_ratio > 1.3
        is_low_vol = atr_ratio < 0.7
        is_trending = adx > 25 and trend_strength > 0.03
        
        if is_high_vol:
            if is_trending:
                return MarketRegime.HIGH_VOL_TREND
            else:
                return MarketRegime.HIGH_VOL_RANGE
        elif is_low_vol:
            return MarketRegime.LOW_VOL_RANGE
        else:
            if is_trending:
                return MarketRegime.MID_VOL_TREND
            else:
                return MarketRegime.LOW_VOL_RANGE
    
    def get_adaptive_tp_config(
        self, 
        regime: MarketRegime,
        volume_ratio: float
    ) -> AdaptiveTakeProfit:
        """
        根據市場環境獲取自適應止盈配置
        
        Args:
            regime: 市場環境
            volume_ratio: 當前成交量 / MA
        
        Returns:
            AdaptiveTakeProfit: 止盈配置
        """
        # 成交量激增時延遲 TP1
        delay_tp1 = volume_ratio > self.volume_surge_threshold
        
        if regime == MarketRegime.HIGH_VOL_TREND:
            # 高波動趨勢：利潤奔跑模式
            return AdaptiveTakeProfit(
                tp1_ratio=1.5,
                tp1_close_pct=0.3 if delay_tp1 else 0.5,  # 成交量大時只平 30%
                tp2_ratio=self.high_vol_trend_tp_ratio,
                use_trailing=True,
                trailing_atr_mult=self.tight_trailing_atr,
                delay_tp1_on_volume=delay_tp1
            )
        elif regime == MarketRegime.MID_VOL_TREND:
            # 中波動趨勢：標準模式
            return AdaptiveTakeProfit(
                tp1_ratio=1.2,
                tp1_close_pct=0.4 if delay_tp1 else 0.5,
                tp2_ratio=self.mid_vol_tp_ratio,
                use_trailing=True,
                trailing_atr_mult=self.base_trailing_atr,
                delay_tp1_on_volume=delay_tp1
            )
        elif regime == MarketRegime.LOW_VOL_RANGE:
            # 低波動震盪：快進快出
            return AdaptiveTakeProfit(
                tp1_ratio=1.0,
                tp1_close_pct=0.6,  # 快速獲利了結
                tp2_ratio=self.low_vol_tp_ratio,
                use_trailing=False,  # 不追蹤，直接止盈
                trailing_atr_mult=self.loose_trailing_atr,
                delay_tp1_on_volume=False
            )
        else:  # HIGH_VOL_RANGE - 危險環境
            # 高波動震盪：保守模式
            return AdaptiveTakeProfit(
                tp1_ratio=1.0,
                tp1_close_pct=0.7,  # 快速減倉
                tp2_ratio=1.5,
                use_trailing=False,
                trailing_atr_mult=self.loose_trailing_atr,
                delay_tp1_on_volume=False
            )

    def calculate_kelly_position(
        self,
        win_rate: float = None,
        avg_win: float = None,
        avg_loss: float = None
    ) -> float:
        """
        計算凱利公式建議倉位
        
        Kelly % = W - [(1-W) / R]
        W = 勝率
        R = 盈虧比 (avg_win / avg_loss)
        
        Returns:
            float: 建議倉位比例 (0-1)
        """
        w = win_rate or self.kelly_win_rate
        avg_w = avg_win or self.kelly_avg_win
        avg_l = avg_loss or self.kelly_avg_loss
        
        if avg_l == 0:
            return 0
        
        r = avg_w / avg_l
        kelly = w - ((1 - w) / r)
        
        # 使用部分凱利（更保守）
        kelly_adjusted = kelly * self.kelly_fraction
        
        # 限制在合理範圍
        return max(0, min(1, kelly_adjusted))
    
    def get_recovery_position_scale(
        self,
        current_equity: float,
        peak_equity: float,
        recent_win_rate: float = None
    ) -> float:
        """
        根據回撤狀態計算倉位縮放因子
        
        策略：
        - 權益新高：標準倉位 (1.0)
        - 小回撤 (<3%)：維持倉位
        - 中回撤 (3-5%)：縮小倉位，但若勝率高則微增
        - 大回撤 (>5%)：大幅縮小倉位
        
        Args:
            current_equity: 當前權益
            peak_equity: 歷史最高權益
            recent_win_rate: 近期勝率（可選）
        
        Returns:
            float: 倉位縮放因子
        """
        if peak_equity <= 0:
            return 1.0
        
        drawdown = (peak_equity - current_equity) / peak_equity
        
        if drawdown <= 0:
            # 權益新高
            return 1.0
        elif drawdown < self.drawdown_threshold:
            # 小回撤：維持
            return 1.0
        elif drawdown < 0.05:
            # 中回撤：根據勝率調整
            base_scale = 0.8
            if recent_win_rate and recent_win_rate > 0.6:
                # 勝率高，可以稍微激進
                return min(base_scale + 0.1, 1.0)
            return base_scale
        elif drawdown < 0.08:
            # 較大回撤
            return 0.6
        else:
            # 大回撤：最小倉位
            return self.recovery_scale_min

    def calculate_dynamic_trailing_stop(
        self,
        entry_price: float,
        current_price: float,
        direction: str,
        atr: float,
        regime: MarketRegime,
        profit_pct: float
    ) -> float:
        """
        計算動態追蹤止損價位
        
        策略：
        - 利潤 < 1%：使用較寬的追蹤距離
        - 利潤 1-2%：標準追蹤距離
        - 利潤 > 2%：收緊追蹤距離，鎖定利潤
        
        Args:
            entry_price: 入場價
            current_price: 當前價
            direction: 'long' 或 'short'
            atr: 當前 ATR
            regime: 市場環境
            profit_pct: 當前利潤百分比
        
        Returns:
            float: 追蹤止損價位
        """
        # 根據利潤階段調整追蹤距離
        if profit_pct < 0.01:
            # 利潤小：寬鬆追蹤
            trail_mult = self.loose_trailing_atr
        elif profit_pct < 0.02:
            # 中等利潤：標準追蹤
            trail_mult = self.base_trailing_atr
        else:
            # 大利潤：緊密追蹤，鎖定利潤
            trail_mult = self.tight_trailing_atr
        
        # 高波動趨勢市可以更寬鬆
        if regime == MarketRegime.HIGH_VOL_TREND:
            trail_mult *= 1.2
        
        trail_distance = atr * trail_mult
        
        if direction == 'long':
            return current_price - trail_distance
        else:
            return current_price + trail_distance


class ScalpingHighLeverageV10:
    """高槓桿剝頭皮策略 v10 - 自適應利潤奔跑版"""
    
    def __init__(
        self,
        # === 繼承 v9 參數 ===
        # RSI 參數
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
        
        # ADX 市場環境過濾
        use_adx_filter: bool = True,
        adx_length: int = 14,
        min_adx: float = 20,
        
        # Bollinger Bands 參數
        bb_length: int = 20,
        bb_std: float = 2.0,
        bb_lower_threshold: float = 0.15,
        bb_upper_threshold: float = 0.85,
        
        # 強信號模式
        use_strong_signals_only: bool = True,
        
        # ATR 波動率
        atr_length: int = 14,
        atr_sl_multiplier: float = 1.5,
        
        # 環境自適應參數
        use_regime_filter: bool = True,
        regime_lookback: int = 60,
        low_vol_threshold: float = 0.7,
        high_vol_threshold: float = 1.3,
        low_vol_atr_mult: float = 1.2,
        mid_vol_atr_mult: float = 1.5,
        high_vol_atr_mult: float = 1.8,
        skip_high_volatility: bool = False,
        
        # 連虧保護
        use_loss_protection: bool = True,
        max_consecutive_losses: int = 2,
        cooldown_bars: int = 60,
        
        # 時段過濾
        use_session_filter: bool = True,
        avoid_low_liquidity: bool = True,
        low_liquidity_start: int = 21,
        low_liquidity_end: int = 1,
        
        # 成交量過濾
        use_volume_filter: bool = True,
        volume_ma_length: int = 20,
        min_volume_ratio: float = 0.8,

        # === v10 新增：自適應利潤奔跑參數 ===
        # 訂單流強度過濾
        use_order_flow_filter: bool = True,
        volume_surge_threshold: float = 1.5,  # 成交量激增閾值
        delay_tp1_on_surge: bool = True,      # 成交量大時延遲 TP1
        
        # 盈虧比階梯化
        use_tiered_rr: bool = True,
        low_vol_tp_ratio: float = 2.0,        # 低波動盈虧比
        mid_vol_tp_ratio: float = 2.5,        # 中波動盈虧比
        high_vol_trend_tp_ratio: float = 3.5, # 高波動趨勢盈虧比
        
        # 動態追蹤止損
        use_adaptive_trailing: bool = True,
        base_trailing_atr: float = 0.8,
        tight_trailing_atr: float = 0.6,
        loose_trailing_atr: float = 1.0,
        
        # 回撤恢復因子
        use_recovery_factor: bool = True,
        drawdown_threshold: float = 0.03,
        recovery_scale_min: float = 0.5,
        recovery_scale_max: float = 1.2,
        
        # 凱利公式參數
        use_kelly_sizing: bool = True,
        kelly_win_rate: float = 0.55,
        kelly_avg_win: float = 1.5,
        kelly_avg_loss: float = 1.0,
        kelly_fraction: float = 0.25,
        
        # 基礎參數
        use_partial_tp: bool = True,
        tp1_ratio: float = 1.2,
        tp1_close_pct: float = 0.5,
        tp2_ratio: float = 2.5,
        use_trailing_stop: bool = True,
        use_delayed_breakeven: bool = True,
        breakeven_trigger_pct: float = 0.5,
        use_trailing_tp: bool = True,
        trailing_atr_multiplier: float = 0.8,
        tp_ratio: float = 1.0,
        max_hold_bars: int = 30,
        use_dynamic_position: bool = True,
        base_position_pct: float = 100,
        vol_position_scale: float = 0.5,
        leverage: int = 50,
        commission: float = 0.0005,
        slippage: float = 0.0001,
        max_stop_loss_pct: float = 0.20,
        
        # 即時波動過濾
        use_realtime_volatility: bool = True,
        min_candle_range_pct: float = 0.03,
        max_candle_range_pct: float = 0.15,
    ):
        self.name = "Scalping High Leverage v10 - Adaptive Trend Riding"
        
        # 繼承 v9 參數
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
        self.use_loss_protection = use_loss_protection
        self.max_consecutive_losses = max_consecutive_losses
        self.cooldown_bars = cooldown_bars
        self.use_session_filter = use_session_filter
        self.avoid_low_liquidity = avoid_low_liquidity
        self.low_liquidity_start = low_liquidity_start
        self.low_liquidity_end = low_liquidity_end
        self.use_volume_filter = use_volume_filter
        self.volume_ma_length = volume_ma_length
        self.min_volume_ratio = min_volume_ratio

        # v10 新增參數
        self.use_order_flow_filter = use_order_flow_filter
        self.volume_surge_threshold = volume_surge_threshold
        self.delay_tp1_on_surge = delay_tp1_on_surge
        self.use_tiered_rr = use_tiered_rr
        self.low_vol_tp_ratio = low_vol_tp_ratio
        self.mid_vol_tp_ratio = mid_vol_tp_ratio
        self.high_vol_trend_tp_ratio = high_vol_trend_tp_ratio
        self.use_adaptive_trailing = use_adaptive_trailing
        self.base_trailing_atr = base_trailing_atr
        self.tight_trailing_atr = tight_trailing_atr
        self.loose_trailing_atr = loose_trailing_atr
        self.use_recovery_factor = use_recovery_factor
        self.drawdown_threshold = drawdown_threshold
        self.recovery_scale_min = recovery_scale_min
        self.recovery_scale_max = recovery_scale_max
        self.use_kelly_sizing = use_kelly_sizing
        self.kelly_win_rate = kelly_win_rate
        self.kelly_avg_win = kelly_avg_win
        self.kelly_avg_loss = kelly_avg_loss
        self.kelly_fraction = kelly_fraction
        
        # 基礎參數
        self.use_partial_tp = use_partial_tp
        self.tp1_ratio = tp1_ratio
        self.tp1_close_pct = tp1_close_pct
        self.tp2_ratio = tp2_ratio
        self.use_trailing_stop = use_trailing_stop
        self.use_delayed_breakeven = use_delayed_breakeven
        self.breakeven_trigger_pct = breakeven_trigger_pct
        self.use_trailing_tp = use_trailing_tp
        self.trailing_atr_multiplier = trailing_atr_multiplier
        self.tp_ratio = tp_ratio
        self.max_hold_bars = max_hold_bars
        self.use_dynamic_position = use_dynamic_position
        self.base_position_pct = base_position_pct
        self.vol_position_scale = vol_position_scale
        self.leverage = leverage
        self.commission = commission
        self.slippage = slippage
        self.max_stop_loss_pct = max_stop_loss_pct
        self.use_realtime_volatility = use_realtime_volatility
        self.min_candle_range_pct = min_candle_range_pct
        self.max_candle_range_pct = max_candle_range_pct
        
        # 初始化自適應模組
        self.trend_rider = AdaptiveTrendRiding(
            volume_ma_length=volume_ma_length,
            volume_surge_threshold=volume_surge_threshold,
            low_vol_tp_ratio=low_vol_tp_ratio,
            mid_vol_tp_ratio=mid_vol_tp_ratio,
            high_vol_trend_tp_ratio=high_vol_trend_tp_ratio,
            base_trailing_atr=base_trailing_atr,
            tight_trailing_atr=tight_trailing_atr,
            loose_trailing_atr=loose_trailing_atr,
            kelly_win_rate=kelly_win_rate,
            kelly_avg_win=kelly_avg_win,
            kelly_avg_loss=kelly_avg_loss,
            kelly_fraction=kelly_fraction,
            drawdown_threshold=drawdown_threshold,
            recovery_scale_min=recovery_scale_min,
            recovery_scale_max=recovery_scale_max,
        )
        
        # 交易狀態追蹤
        self.peak_equity = 0
        self.current_equity = 0
        self.recent_trades = []  # 用於計算近期勝率

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """計算所有技術指標（繼承 v9 + v10 新增）"""
        df = df.copy()
        
        # === v9 指標 ===
        # RSI
        df['rsi'] = ta.rsi(df['close'], length=self.rsi_length)
        df['rsi_prev'] = df['rsi'].shift(1)
        
        # EMA 趨勢
        df['ema_fast'] = ta.ema(df['close'], length=self.ema_fast)
        df['ema_slow'] = ta.ema(df['close'], length=self.ema_slow)
        
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
        df['touch_bb_lower'] = df['low'] <= df['bb_lower']
        df['touch_bb_upper'] = df['high'] >= df['bb_upper']
        
        # ATR
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=self.atr_length)
        df['atr_ma'] = df['atr'].rolling(20).mean()
        df['atr_ratio'] = df['atr'] / df['atr_ma']
        
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
            
            if self.skip_high_volatility:
                df['regime_ok'] = df['regime'] != 'high'
            else:
                df['regime_ok'] = True
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
        
        # === v10 新增指標 ===
        # 成交量激增檢測
        df['volume_surge'] = df['volume_ratio'] > self.volume_surge_threshold
        
        # 趨勢強度（用於環境分類）
        df['trend_strength'] = abs(df['ema_fast'] - df['ema_slow']) / df['close'] * 100
        
        # 詳細環境分類（v10）
        df['market_regime'] = df.apply(
            lambda row: self.trend_rider.classify_market_regime(
                row['atr_ratio'] if pd.notna(row['atr_ratio']) else 1.0,
                row['adx'] if pd.notna(row['adx']) else 20,
                row['trend_strength'] if pd.notna(row['trend_strength']) else 0
            ).value,
            axis=1
        )
        
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
        
        return df

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """生成交易信號 - v10 自適應止盈版"""
        df = self.calculate_indicators(df)
        
        # 初始化信號列
        df['signal'] = 0
        df['long_signal'] = False
        df['short_signal'] = False
        df['long_stop_loss'] = np.nan
        df['long_take_profit'] = np.nan
        df['long_tp1'] = np.nan
        df['long_tp2'] = np.nan
        df['long_tp1_close_pct'] = np.nan
        df['short_stop_loss'] = np.nan
        df['short_take_profit'] = np.nan
        df['short_tp1'] = np.nan
        df['short_tp2'] = np.nan
        df['short_tp1_close_pct'] = np.nan
        df['use_trailing'] = False
        df['trailing_atr_mult'] = np.nan
        df['delay_tp1'] = False
        
        # === 過濾條件（繼承 v9）===
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
        
        # === 做空條件 ===
        combo_a_short = rsi_overbought & rsi_turning_down & near_bb_upper & df['is_bearish']
        short_condition = combo_a_short & downtrend & trend_strong & adx_ok & volume_ok & session_ok & regime_ok & realtime_vol_ok
        
        # 設置信號
        df.loc[long_condition, 'long_signal'] = True
        df.loc[short_condition, 'short_signal'] = True
        
        # === v10: 計算自適應止盈止損 ===
        for idx in df[long_condition | short_condition].index:
            row = df.loc[idx]
            regime = MarketRegime(row['market_regime'])
            volume_ratio = row['volume_ratio'] if pd.notna(row['volume_ratio']) else 1.0
            
            # 獲取自適應止盈配置
            tp_config = self.trend_rider.get_adaptive_tp_config(regime, volume_ratio)
            
            # 計算止損距離
            atr_stop = row['atr'] * row['dynamic_atr_mult']
            max_stop = row['close'] * (self.max_stop_loss_pct / 100)
            stop_distance = min(atr_stop, max_stop)
            
            # 計算止盈距離（v10: 使用自適應盈虧比）
            tp1_distance = stop_distance * tp_config.tp1_ratio
            tp2_distance = stop_distance * tp_config.tp2_ratio
            
            if df.loc[idx, 'long_signal']:
                df.loc[idx, 'long_stop_loss'] = row['close'] - stop_distance
                df.loc[idx, 'long_tp1'] = row['close'] + tp1_distance
                df.loc[idx, 'long_tp2'] = row['close'] + tp2_distance
                df.loc[idx, 'long_take_profit'] = df.loc[idx, 'long_tp2']
                df.loc[idx, 'long_tp1_close_pct'] = tp_config.tp1_close_pct
            
            if df.loc[idx, 'short_signal']:
                df.loc[idx, 'short_stop_loss'] = row['close'] + stop_distance
                df.loc[idx, 'short_tp1'] = row['close'] - tp1_distance
                df.loc[idx, 'short_tp2'] = row['close'] - tp2_distance
                df.loc[idx, 'short_take_profit'] = df.loc[idx, 'short_tp2']
                df.loc[idx, 'short_tp1_close_pct'] = tp_config.tp1_close_pct
            
            # 追蹤止損配置
            df.loc[idx, 'use_trailing'] = tp_config.use_trailing
            df.loc[idx, 'trailing_atr_mult'] = tp_config.trailing_atr_mult
            df.loc[idx, 'delay_tp1'] = tp_config.delay_tp1_on_volume
        
        return df

    def get_exit_levels(
        self, 
        entry_price: float, 
        direction: str, 
        atr: float,
        regime: str = 'mid',
        volume_ratio: float = 1.0,
        current_equity: float = None,
        peak_equity: float = None
    ) -> dict:
        """
        獲取出場價位（供 live_bot 使用）- v10 自適應版
        
        Args:
            entry_price: 入場價
            direction: 'long' 或 'short'
            atr: 當前 ATR
            regime: 市場環境 ('low', 'mid', 'high')
            volume_ratio: 成交量比率
            current_equity: 當前權益（用於倉位調整）
            peak_equity: 歷史最高權益
        """
        # 轉換環境分類
        if regime == 'high':
            market_regime = MarketRegime.HIGH_VOL_TREND
        elif regime == 'low':
            market_regime = MarketRegime.LOW_VOL_RANGE
        else:
            market_regime = MarketRegime.MID_VOL_TREND
        
        # 獲取自適應止盈配置
        tp_config = self.trend_rider.get_adaptive_tp_config(market_regime, volume_ratio)
        
        # 計算止損距離
        if regime == 'low':
            atr_mult = self.low_vol_atr_mult
        elif regime == 'high':
            atr_mult = self.high_vol_atr_mult
        else:
            atr_mult = self.mid_vol_atr_mult
        
        atr_stop = atr * atr_mult
        max_stop = entry_price * (self.max_stop_loss_pct / 100)
        stop_distance = min(atr_stop, max_stop)
        
        tp1_distance = stop_distance * tp_config.tp1_ratio
        tp2_distance = stop_distance * tp_config.tp2_ratio
        trailing_distance = atr * tp_config.trailing_atr_mult
        
        # 計算倉位縮放因子
        position_scale = 1.0
        if self.use_recovery_factor and current_equity and peak_equity:
            position_scale = self.trend_rider.get_recovery_position_scale(
                current_equity, peak_equity
            )
        
        if direction == 'long':
            return {
                'stop_loss': entry_price - stop_distance,
                'tp1': entry_price + tp1_distance,
                'tp2': entry_price + tp2_distance,
                'tp1_close_pct': tp_config.tp1_close_pct,
                'use_trailing_stop': tp_config.use_trailing,
                'use_delayed_breakeven': self.use_delayed_breakeven,
                'breakeven_trigger_pct': self.breakeven_trigger_pct,
                'use_trailing_tp': self.use_trailing_tp,
                'trailing_distance': trailing_distance,
                'entry_price': entry_price,
                'delay_tp1_on_volume': tp_config.delay_tp1_on_volume,
                'position_scale': position_scale,
                'market_regime': market_regime.value,
            }
        else:
            return {
                'stop_loss': entry_price + stop_distance,
                'tp1': entry_price - tp1_distance,
                'tp2': entry_price - tp2_distance,
                'tp1_close_pct': tp_config.tp1_close_pct,
                'use_trailing_stop': tp_config.use_trailing,
                'use_delayed_breakeven': self.use_delayed_breakeven,
                'breakeven_trigger_pct': self.breakeven_trigger_pct,
                'use_trailing_tp': self.use_trailing_tp,
                'trailing_distance': trailing_distance,
                'entry_price': entry_price,
                'delay_tp1_on_volume': tp_config.delay_tp1_on_volume,
                'position_scale': position_scale,
                'market_regime': market_regime.value,
            }

    def update_equity_tracking(self, current_equity: float):
        """更新權益追蹤（用於回撤恢復因子）"""
        self.current_equity = current_equity
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity
    
    def record_trade_result(self, is_win: bool, profit_pct: float):
        """記錄交易結果（用於動態調整）"""
        self.recent_trades.append({
            'is_win': is_win,
            'profit_pct': profit_pct
        })
        # 只保留最近 20 筆
        if len(self.recent_trades) > 20:
            self.recent_trades.pop(0)
    
    def get_recent_win_rate(self) -> float:
        """計算近期勝率"""
        if not self.recent_trades:
            return self.kelly_win_rate
        wins = sum(1 for t in self.recent_trades if t['is_win'])
        return wins / len(self.recent_trades)
    
    def get_position_size_multiplier(self) -> float:
        """
        獲取倉位大小乘數
        
        結合凱利公式和回撤恢復因子
        """
        # 基礎凱利倉位
        kelly_size = self.trend_rider.calculate_kelly_position(
            win_rate=self.get_recent_win_rate()
        )
        
        # 回撤調整
        recovery_scale = self.trend_rider.get_recovery_position_scale(
            self.current_equity,
            self.peak_equity,
            self.get_recent_win_rate()
        )
        
        # 綜合倉位乘數
        return kelly_size * recovery_scale


def create_strategy(**kwargs):
    """創建策略實例"""
    return ScalpingHighLeverageV10(**kwargs)


# ============================================================
# 利潤奔跑虛擬碼 (Profit Riding Pseudocode)
# ============================================================
"""
【利潤奔跑邏輯 - 高槓桿安全版】

1. 入場後初始化：
   - 設置初始止損 (SL)
   - 設置 TP1, TP2 目標
   - 記錄入場時的市場環境和成交量

2. 價格到達 TP1 時：
   IF volume_ratio > 1.5:  # 成交量激增
       # 延遲平倉，改為追蹤止損
       close_position(30%)  # 只平 30%
       activate_trailing_stop(remaining_70%)
       trailing_distance = ATR * 0.6  # 緊密追蹤
   ELSE:
       close_position(50%)  # 標準平倉 50%
       move_stop_to_breakeven()

3. 追蹤止損邏輯：
   WHILE position_open:
       IF profit_pct < 1%:
           trailing_distance = ATR * 1.0  # 寬鬆
       ELIF profit_pct < 2%:
           trailing_distance = ATR * 0.8  # 標準
       ELSE:
           trailing_distance = ATR * 0.6  # 緊密鎖利
       
       IF direction == 'long':
           new_stop = current_price - trailing_distance
           stop_loss = MAX(stop_loss, new_stop)  # 只能上移
       ELSE:
           new_stop = current_price + trailing_distance
           stop_loss = MIN(stop_loss, new_stop)  # 只能下移

4. 環境自適應盈虧比：
   IF regime == HIGH_VOL_TREND:
       tp2_ratio = 3.5  # 讓利潤奔跑
   ELIF regime == MID_VOL_TREND:
       tp2_ratio = 2.5  # 標準
   ELSE:  # LOW_VOL_RANGE
       tp2_ratio = 2.0  # 快進快出

5. 回撤恢復倉位調整：
   drawdown = (peak_equity - current_equity) / peak_equity
   
   IF drawdown <= 0:
       position_scale = 1.0  # 權益新高，標準倉位
   ELIF drawdown < 3%:
       position_scale = 1.0  # 小回撤，維持
   ELIF drawdown < 5%:
       IF recent_win_rate > 60%:
           position_scale = 0.9  # 勝率高，稍微保守
       ELSE:
           position_scale = 0.8  # 縮小倉位
   ELIF drawdown < 8%:
       position_scale = 0.6  # 較大回撤
   ELSE:
       position_scale = 0.5  # 最小倉位，保護本金
"""


def quick_test():
    """快速測試"""
    print("=" * 70)
    print("高槓桿剝頭皮策略 v10 (Adaptive Trend Riding)")
    print("=" * 70)
    print("\n策略特點（繼承 v9）：")
    print("• 均值回歸：RSI 超買超賣反轉")
    print("• BB 反彈：價格觸及軌道後反彈")
    print("• ADX 過濾：ADX >= 20 才交易")
    print("• 環境自適應止損：低/中/高波動使用不同 ATR 倍數")
    print("\nv10 新增功能：")
    print("• 訂單流強度過濾：成交量 > 1.5x MA 時延遲 TP1")
    print("• 盈虧比階梯化：高波動趨勢 3.5x，低波動 2.0x")
    print("• 動態追蹤止損：根據利潤階段調整追蹤距離")
    print("• 回撤恢復因子：凱利公式變體調整倉位")
    print("\n環境分類與盈虧比：")
    print("• LOW_VOL_RANGE  : TP2 = 2.0x SL（快進快出）")
    print("• MID_VOL_TREND  : TP2 = 2.5x SL（標準）")
    print("• HIGH_VOL_TREND : TP2 = 3.5x SL（利潤奔跑）")
    print("• HIGH_VOL_RANGE : TP2 = 1.5x SL（保守）")
    print("\n使用方法：")
    print("./venv/bin/python tools/backtest.py --strategy scalping_v10 --days 60")
    print("=" * 70)


if __name__ == '__main__':
    quick_test()
