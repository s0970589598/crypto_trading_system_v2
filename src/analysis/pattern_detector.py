"""
K線型態識別模組
識別技術分析型態：避雷針、假突破、頭肩頂/底、支撐阻力有效性
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class PatternType(Enum):
    """型態類型"""
    LIGHTNING_ROD = "避雷針"  # 長上影線
    INVERTED_HAMMER = "倒錘子"  # 長下影線
    FAKEOUT_UP = "假突破"  # 向上假突破
    FAKEOUT_DOWN = "假跌破"  # 向下假跌破
    HEAD_SHOULDERS_TOP = "頭肩頂"
    HEAD_SHOULDERS_BOTTOM = "頭肩底"
    DOUBLE_TOP = "雙頂"
    DOUBLE_BOTTOM = "雙底"


@dataclass
class PatternSignal:
    """型態信號"""
    pattern_type: PatternType
    timestamp: pd.Timestamp
    price: float
    strength: float  # 0-100，信號強度
    description: str
    emoji: str  # 顯示用的表情符號
    
    
@dataclass
class SupportResistance:
    """支撐/阻力位"""
    level: float
    touches: int  # 觸碰次數
    strength: float  # 有效性強度 0-100
    last_touch: pd.Timestamp
    is_support: bool  # True=支撐, False=阻力


class PatternDetector:
    """K線型態偵測器 v2.0 - 多因子共振版
    
    整合：K線型態 + 成交量分析 + MACD背離
    """
    
    def __init__(self):
        # 避雷針參數
        self.lightning_rod_ratio = 2.0  # 上影線至少是實體的2倍
        self.lightning_rod_body_ratio = 0.3  # 實體不超過整根K線的30%
        
        # 假突破參數
        self.fakeout_threshold = 0.002  # 突破幅度閾值 0.2%
        self.fakeout_retracement = 0.5  # 回撤至少50%
        self.fakeout_lookback = 20  # 回看K線數量
        
        # 頭肩頂參數
        self.hs_tolerance = 0.02  # 肩膀高度容差 2%
        self.hs_min_bars = 15  # 最小K線數量
        
        # 支撐阻力參數
        self.sr_proximity = 0.005  # 價格接近度 0.5%
        self.sr_lookback = 100  # 回看K線數量
        self.sr_min_touches = 2  # 最少觸碰次數
        
        # 成交量參數
        self.volume_surge_ratio = 1.5  # 爆量閾值（相對於均量）
        self.volume_ma_period = 20  # 均量週期
        
        # MACD 背離參數
        self.divergence_lookback = 20  # 背離檢測回看週期
        
    def detect_all_patterns(self, df: pd.DataFrame, current_idx: int = -1) -> List[PatternSignal]:
        """
        偵測所有型態（v2.0 多因子共振版）
        
        Args:
            df: K線數據（必須包含 volume, macd, macd_hist 欄位）
            current_idx: 當前索引位置（-1表示最新）
            
        Returns:
            型態信號列表
        """
        if current_idx == -1:
            current_idx = len(df) - 1
            
        # 確保有必要的指標
        df = self._ensure_indicators(df)
        
        signals = []
        
        # 1. 避雷針/倒錘子（加入成交量和MACD確認）
        lightning = self.detect_lightning_rod_v2(df, current_idx)
        if lightning:
            signals.append(lightning)
            
        # 2. 假突破（加入成交量確認）
        fakeout = self.detect_fakeout_v2(df, current_idx)
        if fakeout:
            signals.append(fakeout)
            
        # 3. 頭肩頂/底
        head_shoulders = self.detect_head_shoulders(df, current_idx)
        if head_shoulders:
            signals.append(head_shoulders)
            
        # 4. 雙頂/雙底
        double_pattern = self.detect_double_pattern(df, current_idx)
        if double_pattern:
            signals.append(double_pattern)
            
        return signals
    
    def _ensure_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """確保數據包含必要的技術指標"""
        df = df.copy()
        
        # 成交量均線
        if 'volume_sma' not in df.columns:
            df['volume_sma'] = df['volume'].rolling(window=self.volume_ma_period).mean()
        
        # 相對成交量
        if 'volume_ratio' not in df.columns:
            df['volume_ratio'] = df['volume'] / df['volume_sma']
        
        # MACD（如果沒有）
        if 'macd' not in df.columns or 'macd_hist' not in df.columns:
            exp1 = df['close'].ewm(span=12, adjust=False).mean()
            exp2 = df['close'].ewm(span=26, adjust=False).mean()
            df['macd'] = exp1 - exp2
            df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
            df['macd_hist'] = df['macd'] - df['macd_signal']
        
        return df
    
    def _check_volume_confirmation(self, df: pd.DataFrame, idx: int) -> Tuple[bool, str]:
        """
        檢查成交量確認
        
        Returns:
            (是否爆量, 描述)
        """
        if idx < 1:
            return False, "數據不足"
        
        current_vol = df.iloc[idx]['volume']
        prev_vol = df.iloc[idx - 1]['volume']
        vol_ratio = df.iloc[idx].get('volume_ratio', 1.0)
        
        # 條件1：相對於均量放大
        is_surge_vs_ma = vol_ratio > self.volume_surge_ratio
        
        # 條件2：相對於前一根放大
        is_surge_vs_prev = current_vol > prev_vol * 1.3
        
        if is_surge_vs_ma and is_surge_vs_prev:
            return True, f"爆量確認(均量{vol_ratio:.1f}x)"
        elif is_surge_vs_ma:
            return True, f"成交量放大({vol_ratio:.1f}x)"
        elif is_surge_vs_prev:
            return False, f"成交量略增({current_vol/prev_vol:.1f}x)"
        else:
            return False, "⚠️成交量不足"
    
    def _check_macd_divergence(self, df: pd.DataFrame, idx: int, is_top: bool = True) -> Tuple[bool, str]:
        """
        檢查MACD背離
        
        Args:
            is_top: True=檢查頂背離, False=檢查底背離
            
        Returns:
            (是否背離, 描述)
        """
        if idx < self.divergence_lookback:
            return False, "數據不足"
        
        lookback_df = df.iloc[max(0, idx - self.divergence_lookback):idx + 1]
        current = df.iloc[idx]
        
        if is_top:
            # 頂背離：價格創新高，但MACD沒創新高
            recent_high_price = lookback_df['high'].max()
            recent_high_macd = lookback_df['macd'].max()
            
            if current['high'] >= recent_high_price * 0.999:  # 接近或創新高
                if current['macd'] < recent_high_macd * 0.95:  # MACD明顯低於前高
                    return True, "MACD頂背離"
        else:
            # 底背離：價格創新低，但MACD沒創新低
            recent_low_price = lookback_df['low'].min()
            recent_low_macd = lookback_df['macd'].min()
            
            if current['low'] <= recent_low_price * 1.001:  # 接近或創新低
                if current['macd'] > recent_low_macd * 1.05:  # MACD明顯高於前低
                    return True, "MACD底背離"
        
        # 檢查動能衰竭
        if idx >= 1:
            prev_hist = df.iloc[idx - 1]['macd_hist']
            curr_hist = current['macd_hist']
            
            if is_top and curr_hist < prev_hist and curr_hist > 0:
                return True, "多頭動能衰竭"
            elif not is_top and curr_hist > prev_hist and curr_hist < 0:
                return True, "空頭動能衰竭"
        
        return False, "動能正常"
    
    def detect_lightning_rod_v2(self, df: pd.DataFrame, idx: int) -> Optional[PatternSignal]:
        """
        偵測避雷針/倒錘子（v2.0 多因子共振版）
        
        特徵：
        - K線型態：上影線/下影線至少是實體的2倍
        - 成交量確認：必須伴隨成交量放大
        - MACD確認：動能背離或衰竭
        
        只有多因子共振時才發出高強度信號
        """
        if idx < 1 or idx >= len(df):
            return None
            
        row = df.iloc[idx]
        open_price = row['open']
        high = row['high']
        low = row['low']
        close = row['close']
        
        # 計算實體和影線
        body = abs(close - open_price)
        upper_shadow = high - max(open_price, close)
        lower_shadow = min(open_price, close) - low
        total_range = high - low
        
        if total_range == 0:
            return None
        
        # 避雷針（長上影線）
        if upper_shadow > 0 and body > 0:
            upper_ratio = upper_shadow / body
            body_percent = body / total_range
            
            if upper_ratio >= self.lightning_rod_ratio and body_percent <= self.lightning_rod_body_ratio:
                # 多因子分析
                score = 0
                reasons = ["K線:避雷針"]
                
                # 因子1：成交量確認
                vol_confirmed, vol_desc = self._check_volume_confirmation(df, idx)
                reasons.append(vol_desc)
                if vol_confirmed:
                    score += 1
                
                # 因子2：MACD背離/動能衰竭
                macd_confirmed, macd_desc = self._check_macd_divergence(df, idx, is_top=True)
                reasons.append(macd_desc)
                if macd_confirmed:
                    score += 1
                
                # 計算強度：基礎強度 + 確認因子加成
                base_strength = min(100, (upper_ratio / 3) * 100 * (1 - body_percent))
                
                # 共振加成
                if score >= 2:
                    # 三因子共振：K線+成交量+MACD
                    strength = min(100, base_strength * 1.3)
                    quality = "⭐⭐⭐"
                elif score == 1:
                    # 雙因子確認
                    strength = min(100, base_strength * 1.1)
                    quality = "⭐⭐"
                else:
                    # 僅K線型態，降低強度
                    strength = min(100, base_strength * 0.7)
                    quality = "⭐"
                
                description = f"{quality} 避雷針：{' + '.join(reasons)}"
                
                return PatternSignal(
                    pattern_type=PatternType.LIGHTNING_ROD,
                    timestamp=row['timestamp'],
                    price=high,
                    strength=strength,
                    description=description,
                    emoji="⚡"
                )
        
        # 倒錘子（長下影線）
        if lower_shadow > 0 and body > 0:
            lower_ratio = lower_shadow / body
            body_percent = body / total_range
            
            if lower_ratio >= self.lightning_rod_ratio and body_percent <= self.lightning_rod_body_ratio:
                # 多因子分析
                score = 0
                reasons = ["K線:倒錘子"]
                
                # 因子1：成交量確認
                vol_confirmed, vol_desc = self._check_volume_confirmation(df, idx)
                reasons.append(vol_desc)
                if vol_confirmed:
                    score += 1
                
                # 因子2：MACD背離/動能衰竭
                macd_confirmed, macd_desc = self._check_macd_divergence(df, idx, is_top=False)
                reasons.append(macd_desc)
                if macd_confirmed:
                    score += 1
                
                # 計算強度
                base_strength = min(100, (lower_ratio / 3) * 100 * (1 - body_percent))
                
                if score >= 2:
                    strength = min(100, base_strength * 1.3)
                    quality = "⭐⭐⭐"
                elif score == 1:
                    strength = min(100, base_strength * 1.1)
                    quality = "⭐⭐"
                else:
                    strength = min(100, base_strength * 0.7)
                    quality = "⭐"
                
                description = f"{quality} 倒錘子：{' + '.join(reasons)}"
                
                return PatternSignal(
                    pattern_type=PatternType.INVERTED_HAMMER,
                    timestamp=row['timestamp'],
                    price=low,
                    strength=strength,
                    description=description,
                    emoji="🔨"
                )
        
        return None
    
    def detect_fakeout_v2(self, df: pd.DataFrame, idx: int) -> Optional[PatternSignal]:
        """
        偵測假突破/假跌破（v2.0 多因子共振版）
        
        特徵：
        1. 價格突破關鍵位（支撐/阻力）
        2. 突破幅度小（< 0.2%）
        3. 快速回撤（至少50%）
        4. 收盤回到關鍵位內側
        5. 成交量確認：突破失敗時爆量 = 強力信號
        """
        if idx < self.fakeout_lookback:
            return None
            
        current = df.iloc[idx]
        lookback_df = df.iloc[idx - self.fakeout_lookback:idx]
        
        if len(lookback_df) == 0:
            return None
        
        # 找出近期高低點
        recent_high = lookback_df['high'].max()
        recent_low = lookback_df['low'].min()
        
        # 檢查向上假突破
        if current['high'] > recent_high:
            breakout_size = (current['high'] - recent_high) / recent_high
            
            # 突破幅度要小
            if breakout_size <= self.fakeout_threshold:
                # 檢查是否快速回撤
                retracement = (current['high'] - current['close']) / (current['high'] - recent_high)
                
                if retracement >= self.fakeout_retracement and current['close'] < recent_high:
                    # 多因子分析
                    score = 0
                    reasons = [f"假突破({breakout_size*100:.2f}%後回撤{retracement*100:.0f}%)"]
                    
                    # 因子1：成交量確認（假突破時爆量 = 主力倒貨）
                    vol_confirmed, vol_desc = self._check_volume_confirmation(df, idx)
                    if vol_confirmed:
                        score += 1
                        reasons.append(f"爆量拒絕({vol_desc})")
                    else:
                        reasons.append(vol_desc)
                    
                    # 因子2：MACD頂背離
                    macd_confirmed, macd_desc = self._check_macd_divergence(df, idx, is_top=True)
                    if macd_confirmed:
                        score += 1
                        reasons.append(macd_desc)
                    
                    # 計算強度
                    base_strength = min(100, retracement * 100)
                    
                    if score >= 2:
                        strength = min(100, base_strength * 1.3)
                        quality = "⭐⭐⭐"
                        confidence = "High"
                    elif score == 1:
                        strength = min(100, base_strength * 1.1)
                        quality = "⭐⭐"
                        confidence = "Medium"
                    else:
                        strength = min(100, base_strength * 0.8)
                        quality = "⭐"
                        confidence = "Low"
                    
                    description = f"{quality} 假突破({confidence})：{' + '.join(reasons)}"
                    
                    return PatternSignal(
                        pattern_type=PatternType.FAKEOUT_UP,
                        timestamp=current['timestamp'],
                        price=current['high'],
                        strength=strength,
                        description=description,
                        emoji="🚫⬆️"
                    )
        
        # 檢查向下假跌破
        if current['low'] < recent_low:
            breakout_size = (recent_low - current['low']) / recent_low
            
            if breakout_size <= self.fakeout_threshold:
                retracement = (current['close'] - current['low']) / (recent_low - current['low'])
                
                if retracement >= self.fakeout_retracement and current['close'] > recent_low:
                    # 多因子分析
                    score = 0
                    reasons = [f"假跌破({breakout_size*100:.2f}%後反彈{retracement*100:.0f}%)"]
                    
                    # 因子1：成交量確認（假跌破時爆量 = 主力吸籌）
                    vol_confirmed, vol_desc = self._check_volume_confirmation(df, idx)
                    if vol_confirmed:
                        score += 1
                        reasons.append(f"爆量反彈({vol_desc})")
                    else:
                        reasons.append(vol_desc)
                    
                    # 因子2：MACD底背離
                    macd_confirmed, macd_desc = self._check_macd_divergence(df, idx, is_top=False)
                    if macd_confirmed:
                        score += 1
                        reasons.append(macd_desc)
                    
                    # 計算強度
                    base_strength = min(100, retracement * 100)
                    
                    if score >= 2:
                        strength = min(100, base_strength * 1.3)
                        quality = "⭐⭐⭐"
                        confidence = "High"
                    elif score == 1:
                        strength = min(100, base_strength * 1.1)
                        quality = "⭐⭐"
                        confidence = "Medium"
                    else:
                        strength = min(100, base_strength * 0.8)
                        quality = "⭐"
                        confidence = "Low"
                    
                    description = f"{quality} 假跌破({confidence})：{' + '.join(reasons)}"
                    
                    return PatternSignal(
                        pattern_type=PatternType.FAKEOUT_DOWN,
                        timestamp=current['timestamp'],
                        price=current['low'],
                        strength=strength,
                        description=description,
                        emoji="🚫⬇️"
                    )
        
        return None
    
    def detect_head_shoulders(self, df: pd.DataFrame, idx: int) -> Optional[PatternSignal]:
        """
        偵測頭肩頂/頭肩底型態
        
        特徵：
        - 左肩 - 頭部 - 右肩
        - 頭部明顯高於/低於兩肩
        - 兩肩高度相近（容差2%）
        """
        if idx < self.hs_min_bars * 3:
            return None
        
        lookback_df = df.iloc[max(0, idx - 60):idx + 1]
        
        # 找出局部極值點
        highs = self._find_local_extrema(lookback_df, 'high', is_max=True)
        lows = self._find_local_extrema(lookback_df, 'low', is_max=False)
        
        # 頭肩頂：需要3個高點
        if len(highs) >= 3:
            # 取最後3個高點
            left_shoulder, head, right_shoulder = highs[-3:]
            
            # 檢查頭部是否最高
            if head['value'] > left_shoulder['value'] and head['value'] > right_shoulder['value']:
                # 檢查兩肩是否相近
                shoulder_diff = abs(left_shoulder['value'] - right_shoulder['value']) / left_shoulder['value']
                
                if shoulder_diff <= self.hs_tolerance:
                    # 檢查是否在右肩附近
                    if idx - right_shoulder['idx'] <= 5:
                        strength = min(100, (1 - shoulder_diff / self.hs_tolerance) * 100)
                        
                        return PatternSignal(
                            pattern_type=PatternType.HEAD_SHOULDERS_TOP,
                            timestamp=df.iloc[idx]['timestamp'],
                            price=right_shoulder['value'],
                            strength=strength,
                            description=f"頭肩頂：右肩形成，兩肩差異{shoulder_diff*100:.1f}%，看跌信號",
                            emoji="👤⬇️"
                        )
        
        # 頭肩底：需要3個低點
        if len(lows) >= 3:
            left_shoulder, head, right_shoulder = lows[-3:]
            
            if head['value'] < left_shoulder['value'] and head['value'] < right_shoulder['value']:
                shoulder_diff = abs(left_shoulder['value'] - right_shoulder['value']) / left_shoulder['value']
                
                if shoulder_diff <= self.hs_tolerance:
                    if idx - right_shoulder['idx'] <= 5:
                        strength = min(100, (1 - shoulder_diff / self.hs_tolerance) * 100)
                        
                        return PatternSignal(
                            pattern_type=PatternType.HEAD_SHOULDERS_BOTTOM,
                            timestamp=df.iloc[idx]['timestamp'],
                            price=right_shoulder['value'],
                            strength=strength,
                            description=f"頭肩底：右肩形成，兩肩差異{shoulder_diff*100:.1f}%，看漲信號",
                            emoji="👤⬆️"
                        )
        
        return None
    
    def detect_double_pattern(self, df: pd.DataFrame, idx: int) -> Optional[PatternSignal]:
        """偵測雙頂/雙底型態"""
        if idx < 20:
            return None
        
        lookback_df = df.iloc[max(0, idx - 40):idx + 1]
        
        # 找出局部極值
        highs = self._find_local_extrema(lookback_df, 'high', is_max=True)
        lows = self._find_local_extrema(lookback_df, 'low', is_max=False)
        
        # 雙頂
        if len(highs) >= 2:
            first_peak, second_peak = highs[-2:]
            price_diff = abs(first_peak['value'] - second_peak['value']) / first_peak['value']
            
            if price_diff <= 0.02 and idx - second_peak['idx'] <= 3:
                strength = min(100, (1 - price_diff / 0.02) * 100)
                
                return PatternSignal(
                    pattern_type=PatternType.DOUBLE_TOP,
                    timestamp=df.iloc[idx]['timestamp'],
                    price=second_peak['value'],
                    strength=strength,
                    description=f"雙頂：兩個高點差異{price_diff*100:.1f}%，看跌信號",
                    emoji="⛰️⛰️⬇️"
                )
        
        # 雙底
        if len(lows) >= 2:
            first_bottom, second_bottom = lows[-2:]
            price_diff = abs(first_bottom['value'] - second_bottom['value']) / first_bottom['value']
            
            if price_diff <= 0.02 and idx - second_bottom['idx'] <= 3:
                strength = min(100, (1 - price_diff / 0.02) * 100)
                
                return PatternSignal(
                    pattern_type=PatternType.DOUBLE_BOTTOM,
                    timestamp=df.iloc[idx]['timestamp'],
                    price=second_bottom['value'],
                    strength=strength,
                    description=f"雙底：兩個低點差異{price_diff*100:.1f}%，看漲信號",
                    emoji="🏔️🏔️⬆️"
                )
        
        return None
    
    def calculate_support_resistance(
        self, 
        df: pd.DataFrame, 
        current_idx: int = -1
    ) -> Tuple[List[SupportResistance], List[SupportResistance]]:
        """
        計算支撐/阻力位及其有效性
        
        Returns:
            (支撐位列表, 阻力位列表)
        """
        if current_idx == -1:
            current_idx = len(df) - 1
        
        lookback_df = df.iloc[max(0, current_idx - self.sr_lookback):current_idx + 1]
        current_price = df.iloc[current_idx]['close']
        
        # 找出所有局部高低點
        highs = self._find_local_extrema(lookback_df, 'high', is_max=True)
        lows = self._find_local_extrema(lookback_df, 'low', is_max=False)
        
        # 聚類相近的價格水平
        resistance_levels = self._cluster_price_levels([h['value'] for h in highs], current_price)
        support_levels = self._cluster_price_levels([l['value'] for l in lows], current_price)
        
        # 計算每個水平的觸碰次數和強度
        supports = []
        for level in support_levels:
            touches, last_touch = self._count_touches(lookback_df, level, is_support=True)
            if touches >= self.sr_min_touches:
                strength = self._calculate_sr_strength(touches, last_touch, current_idx)
                supports.append(SupportResistance(
                    level=level,
                    touches=touches,
                    strength=strength,
                    last_touch=last_touch,
                    is_support=True
                ))
        
        resistances = []
        for level in resistance_levels:
            touches, last_touch = self._count_touches(lookback_df, level, is_support=False)
            if touches >= self.sr_min_touches:
                strength = self._calculate_sr_strength(touches, last_touch, current_idx)
                resistances.append(SupportResistance(
                    level=level,
                    touches=touches,
                    strength=strength,
                    last_touch=last_touch,
                    is_support=False
                ))
        
        # 按強度排序
        supports.sort(key=lambda x: x.strength, reverse=True)
        resistances.sort(key=lambda x: x.strength, reverse=True)
        
        return supports[:5], resistances[:5]  # 返回前5個最強的
    
    def _find_local_extrema(
        self, 
        df: pd.DataFrame, 
        column: str, 
        is_max: bool, 
        window: int = 5
    ) -> List[Dict]:
        """找出局部極值點"""
        extrema = []
        
        for i in range(window, len(df) - window):
            current = df.iloc[i][column]
            left_window = df.iloc[i - window:i][column]
            right_window = df.iloc[i + 1:i + window + 1][column]
            
            if is_max:
                if current >= left_window.max() and current >= right_window.max():
                    extrema.append({
                        'idx': i,
                        'value': current,
                        'timestamp': df.iloc[i]['timestamp']
                    })
            else:
                if current <= left_window.min() and current <= right_window.min():
                    extrema.append({
                        'idx': i,
                        'value': current,
                        'timestamp': df.iloc[i]['timestamp']
                    })
        
        return extrema
    
    def _cluster_price_levels(self, prices: List[float], current_price: float) -> List[float]:
        """將相近的價格聚類成水平"""
        if not prices:
            return []
        
        prices = sorted(prices)
        clusters = []
        current_cluster = [prices[0]]
        
        for price in prices[1:]:
            if abs(price - current_cluster[-1]) / current_cluster[-1] <= self.sr_proximity:
                current_cluster.append(price)
            else:
                clusters.append(np.mean(current_cluster))
                current_cluster = [price]
        
        if current_cluster:
            clusters.append(np.mean(current_cluster))
        
        return clusters
    
    def _count_touches(
        self, 
        df: pd.DataFrame, 
        level: float, 
        is_support: bool
    ) -> Tuple[int, pd.Timestamp]:
        """計算價格觸碰某水平的次數"""
        touches = 0
        last_touch = None
        
        for idx, row in df.iterrows():
            if is_support:
                # 支撐：低點接近水平
                if abs(row['low'] - level) / level <= self.sr_proximity:
                    touches += 1
                    last_touch = row['timestamp']
            else:
                # 阻力：高點接近水平
                if abs(row['high'] - level) / level <= self.sr_proximity:
                    touches += 1
                    last_touch = row['timestamp']
        
        return touches, last_touch
    
    def _calculate_sr_strength(
        self, 
        touches: int, 
        last_touch: pd.Timestamp, 
        current_idx: int
    ) -> float:
        """
        計算支撐/阻力強度
        
        因素：
        1. 觸碰次數（越多越強）
        2. 最近觸碰時間（越近越有效）
        """
        # 觸碰次數得分（最多10次）
        touch_score = min(touches / 10, 1.0) * 60
        
        # 時間衰減得分（假設每個索引代表一個時間單位）
        # 最近的觸碰得分更高
        time_score = 40  # 基礎分
        
        return min(100, touch_score + time_score)
