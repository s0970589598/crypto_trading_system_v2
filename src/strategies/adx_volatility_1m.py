"""
ADX 波動交易策略 (1分鐘)
1-Minute Volatility Trading Strategy with ADX

策略說明:
- 利用 ADX 指標過濾市場波動性
- 搭配兩條特殊通道進行拉伸點
- 時間框架: 1分鐘
- 適合: 高波動市場

核心指標:
1. ADX (Average Directional Index) - 趨勢強度
2. 外通道 (Outer Channel) - 突破訊號
3. 內通道 (Inner Channel) - 回調確認

交易規則:
做多: 價格突破外通道 + 回調至內通道 + ADX > 30
做空: 價格突破外通道 + 回調至內通道 + ADX > 30

風險管理:
- 停損: 進場點附近的高/低點之外
- 停利: 風險回報比 1:1.5
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple


class ADXVolatility1M:
    """ADX 波動交易策略 (1分鐘)"""
    
    def __init__(
        self,
        adx_period: int = 12,
        adx_di_period: int = 12,
        adx_threshold: int = 15,  # ADX 閾值(降低以增加交易機會)
        outer_channel_length: int = 20,
        outer_channel_mult: float = 2.5,  # 外通道倍數(優化後最佳值)
        inner_channel_length: int = 20,
        inner_channel_mult: float = 1.0,  # 內通道倍數(優化後最佳值)
        risk_reward_ratio: float = 1.5,  # 風險回報比(優化後最佳值)
        stop_loss_atr_mult: float = 2.0,  # 停損 ATR 倍數(恢復原值)
        max_stop_loss_pct: float = 1.5,  # 最大止損百分比(放寬以增加交易機會)
        min_risk_reward: float = 1.0,  # 最小實際盈虧比(放寬)
        leverage: int = 3  # 槓桿倍數
    ):
        """
        初始化策略參數
        
        Args:
            adx_period: ADX 計算週期
            adx_di_period: DI+/DI- 計算週期
            adx_threshold: ADX 閾值 (必須大於此值才交易)
            outer_channel_length: 外通道長度(Keltner)
            outer_channel_mult: 外通道 ATR 倍數(Keltner)
            inner_channel_length: 內通道長度(Keltner)
            inner_channel_mult: 內通道 ATR 倍數(Keltner)
            risk_reward_ratio: 風險回報比
            stop_loss_atr_mult: 停損 ATR 倍數
            max_stop_loss_pct: 最大止損百分比 (避免止損過大)
            min_risk_reward: 最小實際盈虧比 (確保盈虧比合理)
        """
        self.name = "ADX Volatility 1M"
        self.adx_period = adx_period
        self.adx_di_period = adx_di_period
        self.adx_threshold = adx_threshold
        self.outer_channel_length = outer_channel_length
        self.outer_channel_mult = outer_channel_mult
        self.inner_channel_length = inner_channel_length
        self.inner_channel_mult = inner_channel_mult
        self.risk_reward_ratio = risk_reward_ratio
        self.stop_loss_atr_mult = stop_loss_atr_mult
        self.max_stop_loss_pct = max_stop_loss_pct
        self.min_risk_reward = min_risk_reward
        self.leverage = leverage
        
        # 狀態追蹤
        self.position = None
        self.entry_price = None
        self.stop_loss = None
        self.take_profit = None
        self.breakout_high = None
        self.breakout_low = None
    
    def calculate_adx(self, df: pd.DataFrame) -> pd.DataFrame:
        """計算 ADX 指標"""
        high = df['high']
        low = df['low']
        close = df['close']
        
        # 計算 +DM 和 -DM
        plus_dm = high.diff()
        minus_dm = -low.diff()
        
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0
        
        # 計算 TR (True Range)
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # 平滑 TR, +DM, -DM
        atr = tr.rolling(window=self.adx_di_period).mean()
        plus_dm_smooth = plus_dm.rolling(window=self.adx_di_period).mean()
        minus_dm_smooth = minus_dm.rolling(window=self.adx_di_period).mean()
        
        # 計算 +DI 和 -DI
        plus_di = 100 * (plus_dm_smooth / atr)
        minus_di = 100 * (minus_dm_smooth / atr)
        
        # 計算 DX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        
        # 計算 ADX
        adx = dx.rolling(window=self.adx_period).mean()
        
        df['adx'] = adx
        df['plus_di'] = plus_di
        df['minus_di'] = minus_di
        df['atr'] = atr
        
        return df
    
    def calculate_channels(self, df: pd.DataFrame) -> pd.DataFrame:
        """計算 Keltner Channels(外通道和內通道)"""
        close = df['close']
        high = df['high']
        low = df['low']
        
        # 計算 ATR(用於 Keltner Channels)
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # 外通道 (Outer Keltner Channel)
        outer_basis = close.rolling(window=self.outer_channel_length).mean()  # 使用 SMA
        outer_atr = tr.rolling(window=self.outer_channel_length).mean()
        df['outer_upper'] = outer_basis + (outer_atr * self.outer_channel_mult)
        df['outer_lower'] = outer_basis - (outer_atr * self.outer_channel_mult)
        df['outer_basis'] = outer_basis
        
        # 內通道 (Inner Keltner Channel)
        inner_basis = close.rolling(window=self.inner_channel_length).mean()
        inner_atr = tr.rolling(window=self.inner_channel_length).mean()
        df['inner_upper'] = inner_basis + (inner_atr * self.inner_channel_mult)
        df['inner_lower'] = inner_basis - (inner_atr * self.inner_channel_mult)
        df['inner_basis'] = inner_basis
        
        return df
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """計算所有指標"""
        df = self.calculate_adx(df)
        df = self.calculate_channels(df)
        return df
    
    def check_long_entry(self, df: pd.DataFrame, i: int) -> bool:
        """
        檢查做多入場條件
        
        條件:
        1. 前一根K線突破外通道上軌
        2. 當前K線回調至內通道內
        3. ADX > 閾值
        """
        if i < 2:
            return False
        
        current = df.iloc[i]
        prev = df.iloc[i-1]
        
        # 檢查 ADX
        if pd.isna(current['adx']) or current['adx'] < self.adx_threshold:
            return False
        
        # 檢查突破條件: 前一根K線突破外通道上軌
        breakout = prev['close'] > prev['outer_upper']
        
        # 檢查回調條件: 當前K線回調至內通道內
        pullback = current['close'] <= current['inner_upper']
        
        # 確保價格仍在上升趨勢中 (+DI > -DI)
        trend_up = current['plus_di'] > current['minus_di']
        
        return breakout and pullback and trend_up
    
    def check_short_entry(self, df: pd.DataFrame, i: int) -> bool:
        """
        檢查做空入場條件
        
        條件:
        1. 前一根K線突破外通道下軌
        2. 當前K線回調至內通道內
        3. ADX > 閾值
        """
        if i < 2:
            return False
        
        current = df.iloc[i]
        prev = df.iloc[i-1]
        
        # 檢查 ADX
        if pd.isna(current['adx']) or current['adx'] < self.adx_threshold:
            return False
        
        # 檢查突破條件: 前一根K線突破外通道下軌
        breakout = prev['close'] < prev['outer_lower']
        
        # 檢查回調條件: 當前K線回調至內通道內
        pullback = current['close'] >= current['inner_lower']
        
        # 確保價格仍在下降趨勢中 (-DI > +DI)
        trend_down = current['minus_di'] > current['plus_di']
        
        return breakout and pullback and trend_down
    
    def calculate_stop_loss_take_profit(
        self, 
        entry_price: float, 
        position_type: str,
        atr: float,
        recent_high: float,
        recent_low: float,
        current_high: float = None,
        current_low: float = None
    ) -> Tuple[Optional[float], Optional[float]]:
        """
        計算停損和停利價格
        
        策略邏輯:
        - 停損: 基於近期高低點 + ATR 緩衝 (更緊湊的風控)
        - 停利: 風險的 1.5 倍
        - 過濾: 如果止損過大或盈虧比不佳, 返回 None 放棄交易
        - 滑點預測: 使用當前K線的最高/最低點預測可能的最大虧損
        
        Args:
            entry_price: 入場價格
            position_type: 'long' 或 'short'
            atr: 當前 ATR 值
            recent_high: 近期高點
            recent_low: 近期低點
            current_high: 當前K線最高點 (用於預測滑點)
            current_low: 當前K線最低點 (用於預測滑點)
        
        Returns:
            (stop_loss, take_profit) 或 (None, None) 如果不符合條件
        """
        if position_type == 'long':
            # 做多: 停損設在近期低點下方
            stop_loss = recent_low - (atr * self.stop_loss_atr_mult)
            risk = entry_price - stop_loss
            
            # 預測最大虧損：考慮當前K線可能繼續下跌
            if current_low is not None and current_low < stop_loss:
                # 如果當前K線最低點已經低於止損價,使用最低點作為最壞情況
                worst_case_risk = entry_price - current_low
                worst_case_risk_pct = abs(worst_case_risk / entry_price) * 100
                
                # 如果最壞情況超過限制,放棄交易
                if worst_case_risk_pct > self.max_stop_loss_pct:
                    return None, None
            
            take_profit = entry_price + (risk * self.risk_reward_ratio)
        else:
            # 做空: 停損設在近期高點上方
            stop_loss = recent_high + (atr * self.stop_loss_atr_mult)
            risk = stop_loss - entry_price
            
            # 預測最大虧損：考慮當前K線可能繼續上漲
            if current_high is not None and current_high > stop_loss:
                # 如果當前K線最高點已經高於止損價,使用最高點作為最壞情況
                worst_case_risk = current_high - entry_price
                worst_case_risk_pct = abs(worst_case_risk / entry_price) * 100
                
                # 如果最壞情況超過限制,放棄交易
                if worst_case_risk_pct > self.max_stop_loss_pct:
                    return None, None
            
            take_profit = entry_price - (risk * self.risk_reward_ratio)
        
        # 檢查 1: 止損距離是否過大
        stop_loss_pct = abs(risk / entry_price) * 100
        if stop_loss_pct > self.max_stop_loss_pct:
            # 止損過大,放棄交易
            return None, None
        
        # 檢查 2: 實際盈虧比是否符合要求
        if position_type == 'long':
            potential_profit = take_profit - entry_price
        else:
            potential_profit = entry_price - take_profit
        
        actual_risk_reward = potential_profit / risk if risk > 0 else 0
        if actual_risk_reward < self.min_risk_reward:
            # 盈虧比不佳,放棄交易
            return None, None
        
        return stop_loss, take_profit
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """生成交易訊號"""
        df = self.calculate_indicators(df)
        
        df['signal'] = 0
        df['position'] = 0
        df['entry_price'] = np.nan
        df['stop_loss'] = np.nan
        df['take_profit'] = np.nan
        df['long_signal'] = 0
        df['short_signal'] = 0
        df['long_stop_loss'] = np.nan
        df['long_take_profit'] = np.nan
        df['short_stop_loss'] = np.nan
        df['short_take_profit'] = np.nan
        
        for i in range(len(df)):
            current = df.iloc[i]
            
            # 如果沒有持倉,檢查入場條件
            if self.position is None:
                if self.check_long_entry(df, i):
                    # 計算近期高低點 (過去10根K線)
                    lookback = min(10, i)
                    recent_high = df.iloc[i-lookback:i+1]['high'].max()
                    recent_low = df.iloc[i-lookback:i+1]['low'].min()
                    
                    entry_price = current['close']
                    stop_loss, take_profit = self.calculate_stop_loss_take_profit(
                        entry_price, 'long', current['atr'], recent_high, recent_low,
                        current_high=current['high'], current_low=current['low']
                    )
                    
                    # 檢查止損和盈虧比是否合理
                    if stop_loss is not None and take_profit is not None:
                        self.position = 'long'
                        self.entry_price = entry_price
                        self.stop_loss = stop_loss
                        self.take_profit = take_profit
                        
                        df.at[df.index[i], 'signal'] = 1
                        df.at[df.index[i], 'position'] = 1
                        df.at[df.index[i], 'entry_price'] = self.entry_price
                        df.at[df.index[i], 'stop_loss'] = self.stop_loss
                        df.at[df.index[i], 'take_profit'] = self.take_profit
                        df.at[df.index[i], 'long_signal'] = 1
                        df.at[df.index[i], 'long_stop_loss'] = self.stop_loss
                        df.at[df.index[i], 'long_take_profit'] = self.take_profit
                    # else: 止損過大或盈虧比不佳,放棄此次交易
                
                elif self.check_short_entry(df, i):
                    # 計算近期高低點
                    lookback = min(10, i)
                    recent_high = df.iloc[i-lookback:i+1]['high'].max()
                    recent_low = df.iloc[i-lookback:i+1]['low'].min()
                    
                    entry_price = current['close']
                    stop_loss, take_profit = self.calculate_stop_loss_take_profit(
                        entry_price, 'short', current['atr'], recent_high, recent_low,
                        current_high=current['high'], current_low=current['low']
                    )
                    
                    # 檢查止損和盈虧比是否合理
                    if stop_loss is not None and take_profit is not None:
                        self.position = 'short'
                        self.entry_price = entry_price
                        self.stop_loss = stop_loss
                        self.take_profit = take_profit
                        
                        df.at[df.index[i], 'signal'] = -1
                        df.at[df.index[i], 'position'] = -1
                        df.at[df.index[i], 'entry_price'] = self.entry_price
                        df.at[df.index[i], 'stop_loss'] = self.stop_loss
                        df.at[df.index[i], 'take_profit'] = self.take_profit
                        df.at[df.index[i], 'short_signal'] = 1
                        df.at[df.index[i], 'short_stop_loss'] = self.stop_loss
                        df.at[df.index[i], 'short_take_profit'] = self.take_profit
                    # else: 止損過大或盈虧比不佳,放棄此次交易
            
            # 如果有持倉,檢查出場條件
            else:
                df.at[df.index[i], 'position'] = 1 if self.position == 'long' else -1
                
                if self.position == 'long':
                    # 緊急止損：檢查當前虧損是否超過最大允許虧損
                    current_loss_pct = ((current['close'] - self.entry_price) / self.entry_price) * 100
                    if current_loss_pct < -self.max_stop_loss_pct:
                        # 虧損超過限制,立即平倉
                        df.at[df.index[i], 'signal'] = -1
                        self.position = None
                        self.entry_price = None
                    # 檢查停利或停損
                    elif current['high'] >= self.take_profit:
                        df.at[df.index[i], 'signal'] = -1  # 平倉
                        self.position = None
                        self.entry_price = None
                    elif current['low'] <= self.stop_loss:
                        df.at[df.index[i], 'signal'] = -1  # 停損
                        self.position = None
                        self.entry_price = None
                
                elif self.position == 'short':
                    # 緊急止損：檢查當前虧損是否超過最大允許虧損
                    current_loss_pct = ((self.entry_price - current['close']) / self.entry_price) * 100
                    if current_loss_pct < -self.max_stop_loss_pct:
                        # 虧損超過限制,立即平倉
                        df.at[df.index[i], 'signal'] = 1
                        self.position = None
                        self.entry_price = None
                    # 檢查停利或停損
                    elif current['low'] <= self.take_profit:
                        df.at[df.index[i], 'signal'] = 1  # 平倉
                        self.position = None
                        self.entry_price = None
                    elif current['high'] >= self.stop_loss:
                        df.at[df.index[i], 'signal'] = 1  # 停損
                        self.position = None
                        self.entry_price = None
        
        return df
    
    def get_position_size(self, capital: float, price: float) -> float:
        """計算倉位大小"""
        # 使用固定比例的資金
        position_value = capital * 0.95
        return position_value / price


def create_strategy(**kwargs):
    """創建策略實例(用於回測系統)"""
    return ADXVolatility1M(**kwargs)
