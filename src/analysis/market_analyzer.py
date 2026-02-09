"""
市場分析模塊

提供市場數據管理、技術指標計算和市場環境分析功能
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import requests
import time
from typing import Dict, Optional, Tuple, List


class MarketAnalyzer:
    """市場分析器"""
    
    def __init__(self, data_dir: str = "."):
        """初始化市場分析器
        
        Args:
            data_dir: 市場數據目錄
        """
        self.data_dir = Path(data_dir)
        self.market_data: Dict[str, Dict[str, pd.DataFrame]] = {}
        self.cache_expiry_hours = 24  # 數據過期時間（小時）
    
    def load_market_data(self, symbol: str, interval: str = '1h') -> Optional[pd.DataFrame]:
        """載入市場數據，如果不存在則自動下載
        
        Args:
            symbol: 交易對（如 BTCUSDT）
            interval: 時間週期（15m, 1h, 4h, 1d）
            
        Returns:
            Optional[pd.DataFrame]: 市場數據
        """
        filename = self.data_dir / f"market_data_{symbol}_{interval}.csv"
        
        # 如果文件不存在，嘗試下載
        if not filename.exists():
            print(f"⚠️ 市場數據文件不存在：{filename}")
            print(f"🔄 正在從 Binance API 下載 {symbol} {interval} 數據...")
            
            # 下載最近 90 天的數據
            end_time = datetime.now()
            start_time = end_time - timedelta(days=90)
            
            df = self._fetch_binance_klines(symbol, interval, start_time, end_time)
            
            if df is not None and len(df) > 0:
                # 保存到文件
                df.to_csv(filename, index=False)
                print(f"✅ 成功下載並保存 {len(df)} 根 K 線數據到 {filename}")
                return df
            else:
                print(f"❌ 下載數據失敗")
                return None
        
        try:
            df = pd.read_csv(filename)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # 檢查數據是否需要更新
            if len(df) > 0:
                last_time = df['timestamp'].max()
                hours_old = (datetime.now() - last_time).total_seconds() / 3600
                
                if hours_old > self.cache_expiry_hours:
                    print(f"📊 數據已過期 {hours_old:.1f} 小時，正在更新...")
                    df = self._update_market_data(symbol, interval, df)
            
            return df
        
        except Exception as e:
            print(f"❌ 載入市場數據失敗：{e}")
            return None
    
    def _update_market_data_for_timestamp(
        self, 
        symbol: str, 
        interval: str, 
        timestamp: datetime,
        existing_df: pd.DataFrame
    ) -> pd.DataFrame:
        """為特定時間點更新市場數據
        
        Args:
            symbol: 交易對
            interval: 時間週期
            timestamp: 目標時間點
            existing_df: 現有數據
            
        Returns:
            pd.DataFrame: 更新後的數據
        """
        try:
            data_start = existing_df['timestamp'].min()
            data_end = existing_df['timestamp'].max()
            
            # 判斷需要往前還是往後補齊
            if timestamp < data_start:
                # 往前補齊
                print(f"📥 往前補齊數據：{timestamp} -> {data_start}")
                new_data = self._fetch_binance_klines(
                    symbol,
                    interval,
                    timestamp - timedelta(days=30),  # 多獲取一些數據
                    data_start
                )
            else:
                # 往後補齊
                print(f"📥 往後補齊數據：{data_end} -> {timestamp}")
                new_data = self._fetch_binance_klines(
                    symbol,
                    interval,
                    data_end,
                    timestamp + timedelta(days=1)
                )
            
            if new_data is not None and len(new_data) > 0:
                # 合併數據
                combined_df = pd.concat([existing_df, new_data], ignore_index=True)
                combined_df = combined_df.drop_duplicates(subset=['timestamp'], keep='last')
                combined_df = combined_df.sort_values('timestamp').reset_index(drop=True)
                
                # 保存更新後的數據
                filename = self.data_dir / f"market_data_{symbol}_{interval}.csv"
                combined_df.to_csv(filename, index=False)
                
                print(f"✅ 已補齊 {len(new_data)} 根 K 線")
                return combined_df
            
            return existing_df
        
        except Exception as e:
            print(f"❌ 補齊數據失敗：{e}")
            return existing_df
    
    def _update_market_data(self, symbol: str, interval: str, existing_df: pd.DataFrame) -> pd.DataFrame:
        """更新市場數據
        
        Args:
            symbol: 交易對
            interval: 時間週期
            existing_df: 現有數據
            
        Returns:
            pd.DataFrame: 更新後的數據
        """
        try:
            # 獲取最後一筆數據的時間
            last_time = existing_df['timestamp'].max()
            end_time = datetime.now()
            
            # 如果數據已經是最新的，直接返回
            if (end_time - last_time).total_seconds() < 3600:  # 小於1小時
                return existing_df
            
            # 從 Binance 獲取新數據
            new_data = self._fetch_binance_klines(
                symbol, 
                interval, 
                last_time + timedelta(seconds=1), 
                end_time
            )
            
            if new_data is not None and len(new_data) > 0:
                # 合併數據
                combined_df = pd.concat([existing_df, new_data], ignore_index=True)
                combined_df = combined_df.drop_duplicates(subset=['timestamp'], keep='last')
                combined_df = combined_df.sort_values('timestamp').reset_index(drop=True)
                
                # 保存更新後的數據
                filename = self.data_dir / f"market_data_{symbol}_{interval}.csv"
                combined_df.to_csv(filename, index=False)
                
                print(f"✅ 已更新 {len(new_data)} 根新 K 線")
                return combined_df
            
            return existing_df
        
        except Exception as e:
            print(f"❌ 更新市場數據失敗：{e}")
            return existing_df
    
    def _fetch_binance_klines(
        self, 
        symbol: str, 
        interval: str, 
        start_time: datetime, 
        end_time: datetime
    ) -> Optional[pd.DataFrame]:
        """從 Binance API 獲取 K 線數據
        
        Args:
            symbol: 交易對
            interval: 時間週期
            start_time: 開始時間
            end_time: 結束時間
            
        Returns:
            Optional[pd.DataFrame]: K 線數據
        """
        url = "https://api.binance.com/api/v3/klines"
        
        all_klines = []
        current_start = start_time
        
        while current_start < end_time:
            params = {
                'symbol': symbol,
                'interval': interval,
                'startTime': int(current_start.timestamp() * 1000),
                'endTime': int(end_time.timestamp() * 1000),
                'limit': 1000
            }
            
            try:
                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()
                klines = response.json()
                
                if not klines:
                    break
                
                all_klines.extend(klines)
                
                # 更新起始時間
                last_time = klines[-1][0]
                current_start = datetime.fromtimestamp(last_time / 1000) + timedelta(seconds=1)
                
                # 避免 API 限制
                time.sleep(0.5)
            
            except Exception as e:
                print(f"❌ 獲取數據失敗：{e}")
                break
        
        if not all_klines:
            return None
        
        # 轉換為 DataFrame
        df = pd.DataFrame(all_klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_base',
            'taker_buy_quote', 'ignore'
        ])
        
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df['close_time'] = pd.to_datetime(df['close_time'], unit='ms')
        
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
        
        return df
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """計算技術指標
        
        Args:
            df: 市場數據
            
        Returns:
            pd.DataFrame: 包含技術指標的數據
        """
        df = df.copy()
        
        # 1. 移動平均線 - 使用 EMA（與策略一致）
        df['ema_7'] = df['close'].ewm(span=7, adjust=False).mean()
        df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
        
        # 保留 SMA 作為參考
        df['sma_7'] = df['close'].rolling(window=7).mean()
        df['sma_25'] = df['close'].rolling(window=25).mean()
        df['sma_99'] = df['close'].rolling(window=99).mean()
        
        # 2. MACD（使用 EMA）
        df['ema_12'] = df['close'].ewm(span=12, adjust=False).mean()
        df['ema_26'] = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = df['ema_12'] - df['ema_26']
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # 3. RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # 4. ATR (Average True Range)
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        df['atr'] = true_range.rolling(14).mean()
        
        # 5. 布林帶（使用 SMA）
        df['bb_middle'] = df['close'].rolling(window=20).mean()
        bb_std = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
        
        # 6. 成交量指標
        df['volume_sma'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma']
        
        return df
    
    def analyze_market_at_time(
        self, 
        symbol: str, 
        timestamp: datetime, 
        intervals: List[str] = None
    ) -> Optional[Dict]:
        """分析特定時間點的市場狀態（多時區）
        
        Args:
            symbol: 交易對
            timestamp: 時間點
            intervals: 時間週期列表（默認：['15m', '1h', '4h', '1d']）
            
        Returns:
            Optional[Dict]: 市場分析結果（包含多時區分析）
        """
        if intervals is None:
            intervals = ['15m', '1h', '4h', '1d']
        
        multi_timeframe_analysis = {}
        
        # 分析每個時間週期
        for interval in intervals:
            analysis = self._analyze_single_timeframe(symbol, timestamp, interval)
            if analysis:
                multi_timeframe_analysis[interval] = analysis
        
        # 如果沒有任何時區的數據，返回 None
        if not multi_timeframe_analysis:
            return None
        
        # 綜合分析（使用 1h 作為主要時區）
        primary_analysis = multi_timeframe_analysis.get('1h') or multi_timeframe_analysis.get('4h')
        
        if not primary_analysis:
            # 如果沒有 1h 或 4h，使用第一個可用的
            primary_analysis = list(multi_timeframe_analysis.values())[0]
        
        # 添加多時區信息
        primary_analysis['multi_timeframe'] = multi_timeframe_analysis
        
        return primary_analysis
    
    def _analyze_single_timeframe(
        self, 
        symbol: str, 
        timestamp: datetime, 
        interval: str
    ) -> Optional[Dict]:
        """分析單個時間週期
        
        Args:
            symbol: 交易對
            timestamp: 時間點
            interval: 時間週期
            
        Returns:
            Optional[Dict]: 市場分析結果
        """
        # 載入市場數據
        df = self.load_market_data(symbol, interval)
        
        if df is None or len(df) == 0:
            print(f"⚠️ 無法載入 {symbol} {interval} 數據")
            return None
        
        # 檢查數據範圍是否足夠
        data_start = df['timestamp'].min()
        data_end = df['timestamp'].max()
        
        # 如果時間點不在數據範圍內，嘗試更新數據
        if timestamp < data_start or timestamp > data_end:
            print(f"📊 時間點 {timestamp} 不在數據範圍內 ({data_start} - {data_end})")
            print(f"🔄 正在更新 {symbol} {interval} 數據...")
            
            # 更新數據
            df = self._update_market_data_for_timestamp(symbol, interval, timestamp, df)
            
            if df is None or len(df) == 0:
                print(f"❌ 無法更新數據")
                return None
        
        # 計算技術指標
        df = self.calculate_indicators(df)
        
        # 找到最接近的時間點
        df['time_diff'] = abs((df['timestamp'] - timestamp).dt.total_seconds())
        closest_idx = df['time_diff'].idxmin()
        
        # 如果時間差太大（超過2個週期），返回 None
        interval_seconds = self._interval_to_seconds(interval)
        if df.loc[closest_idx, 'time_diff'] > interval_seconds * 2:
            return None
        
        # 獲取當前和前一根 K 線
        if closest_idx < 1:
            return None
        
        current = df.loc[closest_idx]
        previous = df.loc[closest_idx - 1]
        
        # 分析結果
        analysis = {
            'timestamp': current['timestamp'],
            'price': current['close'],
            'open': current['open'],
            'high': current['high'],
            'low': current['low'],
            
            # 趨勢分析（使用 EMA）
            'trend': self._analyze_trend(df, closest_idx),
            'trend_strength': self._calculate_trend_strength(df, closest_idx),
            
            # 技術指標
            'rsi': current['rsi'],
            'rsi_state': self._analyze_rsi(current['rsi']),
            
            'macd': current['macd'],
            'macd_signal': current['macd_signal'],
            'macd_hist': current['macd_hist'],
            'macd_state': self._analyze_macd(current, previous),
            
            # 移動平均線 - EMA（主要）
            'ema_7': current['ema_7'],
            'ema_20': current['ema_20'],
            'ema_50': current['ema_50'],
            'ema_12': current['ema_12'],
            'ema_26': current['ema_26'],
            
            # 移動平均線 - SMA（參考）
            'sma_7': current['sma_7'],
            'sma_25': current['sma_25'],
            'sma_99': current['sma_99'],
            
            'ma_alignment': self._analyze_ma_alignment(current),
            
            # 波動率
            'atr': current['atr'],
            'atr_pct': (current['atr'] / current['close']) * 100,
            'volatility': self._analyze_volatility(current),
            
            # 布林帶
            'bb_position': self._analyze_bb_position(current),
            
            # 成交量
            'volume': current['volume'],
            'volume_ratio': current['volume_ratio'],
            'volume_state': self._analyze_volume(current),
            
            # 支撐/阻力
            'support_resistance': self._find_support_resistance(df, closest_idx),
        }
        
        return analysis
    
    def _interval_to_seconds(self, interval: str) -> int:
        """轉換時間週期為秒數"""
        mapping = {
            '1m': 60,
            '5m': 300,
            '15m': 900,
            '1h': 3600,
            '4h': 14400,
            '1d': 86400
        }
        return mapping.get(interval, 3600)
    
    def _analyze_trend(self, df: pd.DataFrame, idx: int) -> str:
        """分析趨勢方向（使用 EMA）"""
        if idx < 50:
            return 'unknown'
        
        current = df.loc[idx]
        ema_7 = current['ema_7']
        ema_20 = current['ema_20']
        ema_50 = current['ema_50']
        
        if pd.isna(ema_7) or pd.isna(ema_20) or pd.isna(ema_50):
            return 'unknown'
        
        # 多頭排列（EMA 7 > EMA 20 > EMA 50）
        if ema_7 > ema_20 > ema_50:
            return 'strong_uptrend'
        elif ema_7 > ema_20:
            return 'uptrend'
        # 空頭排列（EMA 7 < EMA 20 < EMA 50）
        elif ema_7 < ema_20 < ema_50:
            return 'strong_downtrend'
        elif ema_7 < ema_20:
            return 'downtrend'
        else:
            return 'sideways'
    
    def _calculate_trend_strength(self, df: pd.DataFrame, idx: int) -> float:
        """計算趨勢強度（0-100）使用 EMA"""
        if idx < 20:
            return 50.0
        
        current = df.loc[idx]
        
        # 基於 EMA 斜率
        ema_7_slope = 0
        ema_20_slope = 0
        
        if idx >= 7:
            ema_7_slope = (current['ema_7'] - df.loc[idx-7, 'ema_7']) / df.loc[idx-7, 'ema_7'] * 100
        
        if idx >= 20:
            ema_20_slope = (current['ema_20'] - df.loc[idx-20, 'ema_20']) / df.loc[idx-20, 'ema_20'] * 100
        
        # 綜合評分
        strength = 50 + (ema_7_slope * 10) + (ema_20_slope * 5)
        return max(0, min(100, strength))
    
    def _analyze_rsi(self, rsi: float) -> str:
        """分析 RSI 狀態"""
        if pd.isna(rsi):
            return 'unknown'
        
        if rsi >= 70:
            return 'overbought'
        elif rsi >= 60:
            return 'strong'
        elif rsi >= 40:
            return 'neutral'
        elif rsi >= 30:
            return 'weak'
        else:
            return 'oversold'
    
    def _analyze_macd(self, current: pd.Series, previous: pd.Series) -> str:
        """分析 MACD 狀態"""
        if pd.isna(current['macd']) or pd.isna(previous['macd']):
            return 'unknown'
        
        # 金叉/死叉
        if current['macd'] > current['macd_signal'] and previous['macd'] <= previous['macd_signal']:
            return 'golden_cross'
        elif current['macd'] < current['macd_signal'] and previous['macd'] >= previous['macd_signal']:
            return 'death_cross'
        elif current['macd'] > current['macd_signal']:
            return 'bullish'
        else:
            return 'bearish'
    
    def _analyze_ma_alignment(self, current: pd.Series) -> str:
        """分析均線排列（使用 EMA）"""
        ema_7 = current['ema_7']
        ema_20 = current['ema_20']
        ema_50 = current['ema_50']
        
        if pd.isna(ema_7) or pd.isna(ema_20) or pd.isna(ema_50):
            return 'unknown'
        
        if ema_7 > ema_20 > ema_50:
            return 'bullish'
        elif ema_7 < ema_20 < ema_50:
            return 'bearish'
        else:
            return 'mixed'
    
    def _analyze_volatility(self, current: pd.Series) -> str:
        """分析波動率"""
        atr_pct = (current['atr'] / current['close']) * 100
        
        if pd.isna(atr_pct):
            return 'unknown'
        
        if atr_pct > 5:
            return 'very_high'
        elif atr_pct > 3:
            return 'high'
        elif atr_pct > 1.5:
            return 'normal'
        else:
            return 'low'
    
    def _analyze_bb_position(self, current: pd.Series) -> str:
        """分析布林帶位置"""
        if pd.isna(current['bb_upper']) or pd.isna(current['bb_lower']):
            return 'unknown'
        
        price = current['close']
        upper = current['bb_upper']
        lower = current['bb_lower']
        middle = current['bb_middle']
        
        if price >= upper:
            return 'above_upper'
        elif price >= middle:
            return 'upper_half'
        elif price >= lower:
            return 'lower_half'
        else:
            return 'below_lower'
    
    def _analyze_volume(self, current: pd.Series) -> str:
        """分析成交量"""
        if pd.isna(current['volume_ratio']):
            return 'unknown'
        
        ratio = current['volume_ratio']
        
        if ratio > 2:
            return 'very_high'
        elif ratio > 1.5:
            return 'high'
        elif ratio > 0.8:
            return 'normal'
        else:
            return 'low'
    
    def _find_support_resistance(self, df: pd.DataFrame, idx: int, lookback: int = 50) -> Dict:
        """尋找支撐和阻力位"""
        if idx < lookback:
            return {'support': None, 'resistance': None}
        
        # 獲取最近的價格數據
        recent_df = df.loc[max(0, idx-lookback):idx]
        current_price = df.loc[idx, 'close']
        
        # 尋找局部高點和低點
        highs = recent_df['high'].nlargest(5).values
        lows = recent_df['low'].nsmallest(5).values
        
        # 找到最近的支撐和阻力
        resistance = None
        support = None
        
        for high in highs:
            if high > current_price:
                resistance = high
                break
        
        for low in lows:
            if low < current_price:
                support = low
                break
        
        return {
            'support': support,
            'resistance': resistance,
            'distance_to_support': ((current_price - support) / current_price * 100) if support else None,
            'distance_to_resistance': ((resistance - current_price) / current_price * 100) if resistance else None
        }
