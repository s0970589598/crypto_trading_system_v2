"""
多因子短線進階策略 v2
Multi-Factor Short-Term Advanced Strategy

策略說明:
- 多因子共振進場：成交量、MACD、趨勢、突破、波動率
- 分批止盈：第一目標出 50%，剩餘持有到第二目標
- 保本止損：盈利達到一定程度後，止損移到入場價
- 移動止損：隨著價格上漲，止損跟著上移保護利潤

風險管理:
- 止損: ATR × 1.0
- 第一止盈: ATR × 1.5 (出 50%)
- 第二止盈: ATR × 3.0 (出剩餘 50%)
- 保本觸發: 盈利 >= 1×ATR 時，止損移到入場價
- 移動止損: 跟隨最高/最低點
"""

import pandas as pd
import numpy as np
import pandas_ta as ta
from typing import Tuple, Optional


class MultiFactorShort:
    """多因子短線進階策略 v2 - 分批止盈 + 保本止損"""
    
    def __init__(
        self,
        # ATR 參數
        atr_length: int = 14,
        atr_mul_sl: float = 1.0,  # 止損倍數
        atr_mul_tp1: float = 1.5,  # 第一止盈倍數（出 50%）
        atr_mul_tp2: float = 3.0,  # 第二止盈倍數（出剩餘）
        atr_floor: float = 0.0008,  # 最小波動率
        
        # 趨勢參數
        ma_length: int = 50,  # SMA 長度
        ma_length_fast: int = 20,  # 快速 SMA
        breakout_length: int = 8,  # 高低點突破回看長度
        
        # MACD 參數
        macd_fast: int = 12,
        macd_slow: int = 26,
        macd_signal: int = 9,
        
        # 成交量參數
        vol_min: int = 0,  # 最小成交量
        
        # 風險管理
        risk_ratio: float = 1.5,  # 最低盈虧比
        max_stop_loss_pct: float = 1.0,  # 最大止損百分比
        
        # 趨勢過濾
        use_trend_filter: bool = False,  # 關閉趨勢過濾（原始版本）
        trend_strength_min: float = 0.1,  # 最小趨勢強度
        
        # 震盪市場過濾（新增）
        use_range_filter: bool = True,  # 啟用震盪市場過濾
        range_lookback: int = 20,  # 回看 K 線數（20 根 15m = 5 小時）
        range_threshold: float = 1.5,  # 區間閾值（%）：區間 < 1.5% 視為震盪
        
        # 分批止盈
        partial_exit_ratio: float = 0.5,  # 第一目標出場比例
        
        # 保本止損
        breakeven_trigger_atr: float = 1.0,  # 盈利達到 1×ATR 時觸發保本
        breakeven_buffer_pct: float = 0.1,  # 保本緩衝（入場價 + 0.1%）
        
        # 移動止損
        use_trailing_stop: bool = True,
        trailing_atr_mult: float = 1.0,  # 移動止損距離
        
        # 交易設置
        leverage: int = 5,
        commission: float = 0.0005
    ):
        self.name = "Multi-Factor Short"
        
        # ATR 參數
        self.atr_length = atr_length
        self.atr_mul_sl = atr_mul_sl
        self.atr_mul_tp1 = atr_mul_tp1
        self.atr_mul_tp2 = atr_mul_tp2
        self.atr_floor = atr_floor
        
        # 趨勢參數
        self.ma_length = ma_length
        self.ma_length_fast = ma_length_fast
        self.breakout_length = breakout_length
        
        # MACD 參數
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal
        
        # 成交量參數
        self.vol_min = vol_min
        
        # 風險管理
        self.risk_ratio = risk_ratio
        self.max_stop_loss_pct = max_stop_loss_pct
        
        # 趨勢過濾
        self.use_trend_filter = use_trend_filter
        self.trend_strength_min = trend_strength_min
        
        # 震盪市場過濾
        self.use_range_filter = use_range_filter
        self.range_lookback = range_lookback
        self.range_threshold = range_threshold
        
        # 分批止盈
        self.partial_exit_ratio = partial_exit_ratio
        
        # 保本止損
        self.breakeven_trigger_atr = breakeven_trigger_atr
        self.breakeven_buffer_pct = breakeven_buffer_pct
        
        # 移動止損
        self.use_trailing_stop = use_trailing_stop
        self.trailing_atr_mult = trailing_atr_mult
        
        # 交易設置
        self.leverage = leverage
        self.commission = commission
        
        # 狀態追蹤
        self._reset_position()
    
    def _reset_position(self):
        """重置持倉狀態"""
        self.position = None
        self.entry_price = None
        self.entry_atr = None
        self.stop_loss = None
        self.take_profit_1 = None
        self.take_profit_2 = None
        self.trailing_stop = None
        self.highest_since_entry = None
        self.lowest_since_entry = None
        self.partial_exited = False  # 是否已部分出場
        self.breakeven_activated = False  # 是否已觸發保本
        self.position_size = 1.0  # 當前倉位比例
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """計算所有技術指標"""
        df = df.copy()
        
        # ATR
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=self.atr_length)
        
        # SMA（慢速和快速）
        df['sma'] = ta.sma(df['close'], length=self.ma_length)
        df['sma_fast'] = ta.sma(df['close'], length=self.ma_length_fast)
        
        # 趨勢強度：價格與 SMA 的距離（百分比）
        df['trend_strength'] = (df['close'] - df['sma']) / df['sma'] * 100
        
        # MACD
        macd = ta.macd(df['close'], fast=self.macd_fast, slow=self.macd_slow, signal=self.macd_signal)
        df['macd'] = macd[f'MACD_{self.macd_fast}_{self.macd_slow}_{self.macd_signal}']
        df['macd_signal'] = macd[f'MACDs_{self.macd_fast}_{self.macd_slow}_{self.macd_signal}']
        df['macd_hist'] = macd[f'MACDh_{self.macd_fast}_{self.macd_slow}_{self.macd_signal}']
        
        # MACD 方向
        df['macd_pass'] = (df['macd'] > df['macd_signal']).astype(int) * 2 - 1
        
        # 高低點突破
        df['hh'] = df['high'].rolling(window=self.breakout_length).max()
        df['ll'] = df['low'].rolling(window=self.breakout_length).min()
        
        # 成交量條件
        df['vol_pass'] = df['volume'] > self.vol_min
        
        # 波動率條件
        df['volatility'] = df['atr'] / df['close']
        df['volatility_pass'] = df['volatility'] > self.atr_floor
        
        # 震盪市場檢測：計算近期價格區間
        df['range_high'] = df['high'].rolling(window=self.range_lookback).max()
        df['range_low'] = df['low'].rolling(window=self.range_lookback).min()
        df['range_pct'] = (df['range_high'] - df['range_low']) / df['close'] * 100
        # 如果區間 < 閾值，視為震盪市場，不適合突破策略
        df['is_trending'] = df['range_pct'] >= self.range_threshold
        
        return df
    
    def check_long_entry(self, df: pd.DataFrame, i: int) -> Tuple[bool, Optional[float], Optional[float], Optional[float], Optional[float]]:
        """
        檢查做多入場條件
        返回: (是否入場, 止損價, 第一止盈, 第二止盈, ATR)
        """
        if i < max(self.breakout_length, self.range_lookback) + 1:
            return False, None, None, None, None
        
        current = df.iloc[i]
        prev_hh = df.iloc[i-1]['hh']
        
        # 震盪市場過濾：在震盪市場中不交易
        if self.use_range_filter and not current['is_trending']:
            return False, None, None, None, None
        
        # 檢查所有條件
        vol_pass = current['vol_pass']
        macd_pass = current['macd_pass'] > 0
        trend_pass = current['close'] > current['sma']
        breakout_pass = current['close'] > prev_hh
        volatility_pass = current['volatility_pass']
        
        # 趨勢過濾：快速 SMA 必須在慢速 SMA 上方，且趨勢強度足夠
        if self.use_trend_filter:
            sma_aligned = current['sma_fast'] > current['sma']
            trend_strong = current['trend_strength'] > self.trend_strength_min
            trend_filter_pass = sma_aligned and trend_strong
        else:
            trend_filter_pass = True
        
        if not (vol_pass and macd_pass and trend_pass and breakout_pass and volatility_pass and trend_filter_pass):
            return False, None, None, None, None
        
        # 計算止損止盈
        atr = current['atr']
        entry_price = current['close']
        stop_loss = entry_price - atr * self.atr_mul_sl
        take_profit_1 = entry_price + atr * self.atr_mul_tp1
        take_profit_2 = entry_price + atr * self.atr_mul_tp2
        
        # 檢查盈虧比（用第一止盈計算）
        risk = entry_price - stop_loss
        reward = take_profit_1 - entry_price
        
        if risk <= 0:
            return False, None, None, None, None
        
        risk_reward = reward / risk
        if risk_reward < self.risk_ratio:
            return False, None, None, None, None
        
        # 檢查最大止損限制
        stop_loss_pct = (risk / entry_price) * 100
        if stop_loss_pct > self.max_stop_loss_pct:
            return False, None, None, None, None
        
        return True, stop_loss, take_profit_1, take_profit_2, atr
    
    def check_short_entry(self, df: pd.DataFrame, i: int) -> Tuple[bool, Optional[float], Optional[float], Optional[float], Optional[float]]:
        """
        檢查做空入場條件
        返回: (是否入場, 止損價, 第一止盈, 第二止盈, ATR)
        """
        if i < max(self.breakout_length, self.range_lookback) + 1:
            return False, None, None, None, None
        
        current = df.iloc[i]
        prev_ll = df.iloc[i-1]['ll']
        
        # 震盪市場過濾：在震盪市場中不交易
        if self.use_range_filter and not current['is_trending']:
            return False, None, None, None, None
        
        # 檢查所有條件
        vol_pass = current['vol_pass']
        macd_pass = current['macd_pass'] < 0
        trend_pass = current['close'] < current['sma']
        breakout_pass = current['close'] < prev_ll
        volatility_pass = current['volatility_pass']
        
        # 趨勢過濾：快速 SMA 必須在慢速 SMA 下方，且趨勢強度足夠
        if self.use_trend_filter:
            sma_aligned = current['sma_fast'] < current['sma']
            trend_strong = current['trend_strength'] < -self.trend_strength_min
            trend_filter_pass = sma_aligned and trend_strong
        else:
            trend_filter_pass = True
        
        if not (vol_pass and macd_pass and trend_pass and breakout_pass and volatility_pass and trend_filter_pass):
            return False, None, None, None, None
        
        # 計算止損止盈
        atr = current['atr']
        entry_price = current['close']
        stop_loss = entry_price + atr * self.atr_mul_sl
        take_profit_1 = entry_price - atr * self.atr_mul_tp1
        take_profit_2 = entry_price - atr * self.atr_mul_tp2
        
        # 檢查盈虧比
        risk = stop_loss - entry_price
        reward = entry_price - take_profit_1
        
        if risk <= 0:
            return False, None, None, None, None
        
        risk_reward = reward / risk
        if risk_reward < self.risk_ratio:
            return False, None, None, None, None
        
        # 檢查最大止損限制
        stop_loss_pct = (risk / entry_price) * 100
        if stop_loss_pct > self.max_stop_loss_pct:
            return False, None, None, None, None
        
        return True, stop_loss, take_profit_1, take_profit_2, atr
    
    def update_position_management(self, current_price: float, current_high: float, current_low: float, current_atr: float):
        """更新持倉管理：保本止損 + 移動止損"""
        if self.position is None:
            return
        
        if self.position == 'long':
            # 更新最高點
            if self.highest_since_entry is None or current_high > self.highest_since_entry:
                self.highest_since_entry = current_high
            
            # 計算當前盈利（以 ATR 為單位）
            profit_atr = (current_price - self.entry_price) / self.entry_atr
            
            # 保本止損：盈利達到觸發點時，止損移到入場價
            if not self.breakeven_activated and profit_atr >= self.breakeven_trigger_atr:
                self.breakeven_activated = True
                breakeven_price = self.entry_price * (1 + self.breakeven_buffer_pct / 100)
                if breakeven_price > self.stop_loss:
                    self.stop_loss = breakeven_price
                    self.trailing_stop = breakeven_price
            
            # 移動止損：跟隨最高點
            if self.use_trailing_stop and self.breakeven_activated:
                trailing_distance = current_atr * self.trailing_atr_mult
                new_trailing = self.highest_since_entry - trailing_distance
                
                # 只能往上移動
                if new_trailing > self.trailing_stop:
                    self.trailing_stop = new_trailing
                    # 同時更新止損
                    if new_trailing > self.stop_loss:
                        self.stop_loss = new_trailing
        
        elif self.position == 'short':
            # 更新最低點
            if self.lowest_since_entry is None or current_low < self.lowest_since_entry:
                self.lowest_since_entry = current_low
            
            # 計算當前盈利（以 ATR 為單位）
            profit_atr = (self.entry_price - current_price) / self.entry_atr
            
            # 保本止損
            if not self.breakeven_activated and profit_atr >= self.breakeven_trigger_atr:
                self.breakeven_activated = True
                breakeven_price = self.entry_price * (1 - self.breakeven_buffer_pct / 100)
                if breakeven_price < self.stop_loss:
                    self.stop_loss = breakeven_price
                    self.trailing_stop = breakeven_price
            
            # 移動止損
            if self.use_trailing_stop and self.breakeven_activated:
                trailing_distance = current_atr * self.trailing_atr_mult
                new_trailing = self.lowest_since_entry + trailing_distance
                
                # 只能往下移動
                if new_trailing < self.trailing_stop:
                    self.trailing_stop = new_trailing
                    if new_trailing < self.stop_loss:
                        self.stop_loss = new_trailing
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """生成交易訊號"""
        df = self.calculate_indicators(df)
        
        # 初始化信號列
        df['signal'] = 0
        df['position'] = 0
        df['entry_price'] = np.nan
        df['stop_loss'] = np.nan
        df['take_profit'] = np.nan
        df['long_signal'] = False
        df['short_signal'] = False
        df['long_stop_loss'] = np.nan
        df['long_take_profit'] = np.nan
        df['long_take_profit_2'] = np.nan  # 第二止盈
        df['short_stop_loss'] = np.nan
        df['short_take_profit'] = np.nan
        df['short_take_profit_2'] = np.nan  # 第二止盈
        df['partial_exit'] = False  # 分批出場標記
        df['exit_ratio'] = 0.0  # 出場比例
        
        # 重置狀態
        self._reset_position()
        
        for i in range(len(df)):
            current = df.iloc[i]
            
            # 如果沒有持倉，檢查入場條件
            if self.position is None:
                # 檢查做多
                long_entry, long_sl, long_tp1, long_tp2, atr = self.check_long_entry(df, i)
                if long_entry:
                    self.position = 'long'
                    self.entry_price = current['close']
                    self.entry_atr = atr
                    self.stop_loss = long_sl
                    self.take_profit_1 = long_tp1
                    self.take_profit_2 = long_tp2
                    self.trailing_stop = long_sl
                    self.highest_since_entry = current['high']
                    self.position_size = 1.0
                    
                    df.at[df.index[i], 'signal'] = 1
                    df.at[df.index[i], 'position'] = 1
                    df.at[df.index[i], 'entry_price'] = self.entry_price
                    df.at[df.index[i], 'stop_loss'] = self.stop_loss
                    df.at[df.index[i], 'take_profit'] = self.take_profit_1
                    df.at[df.index[i], 'long_signal'] = True
                    df.at[df.index[i], 'long_stop_loss'] = self.stop_loss
                    df.at[df.index[i], 'long_take_profit'] = self.take_profit_1
                    df.at[df.index[i], 'long_take_profit_2'] = self.take_profit_2
                    continue
                
                # 檢查做空
                short_entry, short_sl, short_tp1, short_tp2, atr = self.check_short_entry(df, i)
                if short_entry:
                    self.position = 'short'
                    self.entry_price = current['close']
                    self.entry_atr = atr
                    self.stop_loss = short_sl
                    self.take_profit_1 = short_tp1
                    self.take_profit_2 = short_tp2
                    self.trailing_stop = short_sl
                    self.lowest_since_entry = current['low']
                    self.position_size = 1.0
                    
                    df.at[df.index[i], 'signal'] = -1
                    df.at[df.index[i], 'position'] = -1
                    df.at[df.index[i], 'entry_price'] = self.entry_price
                    df.at[df.index[i], 'stop_loss'] = self.stop_loss
                    df.at[df.index[i], 'take_profit'] = self.take_profit_1
                    df.at[df.index[i], 'short_signal'] = True
                    df.at[df.index[i], 'short_stop_loss'] = self.stop_loss
                    df.at[df.index[i], 'short_take_profit'] = self.take_profit_1
                    df.at[df.index[i], 'short_take_profit_2'] = self.take_profit_2
                    continue
            
            # 如果有持倉，檢查出場條件
            else:
                df.at[df.index[i], 'position'] = 1 if self.position == 'long' else -1
                
                # 更新持倉管理（保本 + 移動止損）
                self.update_position_management(
                    current['close'],
                    current['high'],
                    current['low'],
                    current['atr']
                )
                
                if self.position == 'long':
                    # 第一止盈（分批出場）
                    if not self.partial_exited and current['high'] >= self.take_profit_1:
                        self.partial_exited = True
                        self.position_size = 1.0 - self.partial_exit_ratio
                        df.at[df.index[i], 'partial_exit'] = True
                        df.at[df.index[i], 'exit_ratio'] = self.partial_exit_ratio
                        # 觸發保本
                        self.breakeven_activated = True
                        self.stop_loss = self.entry_price * (1 + self.breakeven_buffer_pct / 100)
                        self.trailing_stop = self.stop_loss
                    
                    # 第二止盈（全部出場）
                    if self.partial_exited and current['high'] >= self.take_profit_2:
                        df.at[df.index[i], 'signal'] = -1
                        df.at[df.index[i], 'exit_ratio'] = self.position_size
                        self._reset_position()
                    # 止損（移動止損或固定止損）
                    elif current['low'] <= self.stop_loss:
                        df.at[df.index[i], 'signal'] = -1
                        df.at[df.index[i], 'exit_ratio'] = self.position_size
                        self._reset_position()
                
                elif self.position == 'short':
                    # 第一止盈（分批出場）
                    if not self.partial_exited and current['low'] <= self.take_profit_1:
                        self.partial_exited = True
                        self.position_size = 1.0 - self.partial_exit_ratio
                        df.at[df.index[i], 'partial_exit'] = True
                        df.at[df.index[i], 'exit_ratio'] = self.partial_exit_ratio
                        # 觸發保本
                        self.breakeven_activated = True
                        self.stop_loss = self.entry_price * (1 - self.breakeven_buffer_pct / 100)
                        self.trailing_stop = self.stop_loss
                    
                    # 第二止盈（全部出場）
                    if self.partial_exited and current['low'] <= self.take_profit_2:
                        df.at[df.index[i], 'signal'] = 1
                        df.at[df.index[i], 'exit_ratio'] = self.position_size
                        self._reset_position()
                    # 止損
                    elif current['high'] >= self.stop_loss:
                        df.at[df.index[i], 'signal'] = 1
                        df.at[df.index[i], 'exit_ratio'] = self.position_size
                        self._reset_position()
        
        return df
    
    def get_position_size(self, capital: float, price: float) -> float:
        """計算倉位大小"""
        position_value = capital * 0.10
        return position_value / price


def create_strategy(**kwargs):
    """創建策略實例"""
    return MultiFactorShort(**kwargs)


def quick_test():
    """快速測試"""
    print("=" * 60)
    print("多因子短線進階策略 v2")
    print("=" * 60)
    print("\n新功能：")
    print("✓ 分批止盈：第一目標出 50%，剩餘持有到第二目標")
    print("✓ 保本止損：盈利達 1×ATR 時，止損移到入場價")
    print("✓ 移動止損：跟隨最高/最低點保護利潤")
    print("\n默認參數：")
    print("• 止損: 1.0×ATR")
    print("• 第一止盈: 1.5×ATR (出 50%)")
    print("• 第二止盈: 3.0×ATR (出剩餘)")
    print("• 保本觸發: 盈利 >= 1×ATR")
    print("• SMA: 50")
    print("=" * 60)


if __name__ == '__main__':
    quick_test()
