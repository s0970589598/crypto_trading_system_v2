"""
數據管理器

提供統一的數據接口，支持多數據源、緩存、容錯和驗證。
"""

import pandas as pd
from typing import Dict, List, Optional, Tuple, Callable
from datetime import datetime, timedelta
import logging
from pathlib import Path
import json

from src.models.market_data import MarketData, TimeframeData


logger = logging.getLogger(__name__)


class DataSource:
    """數據源抽象類"""
    
    def __init__(self, name: str):
        """初始化數據源
        
        Args:
            name: 數據源名稱
        """
        self.name = name
    
    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> pd.DataFrame:
        """獲取 OHLCV 數據
        
        Args:
            symbol: 交易對
            timeframe: 時間週期
            start_time: 開始時間
            end_time: 結束時間
            limit: 數據條數限制
            
        Returns:
            pd.DataFrame: OHLCV 數據
            
        Raises:
            NotImplementedError: 子類必須實現此方法
        """
        raise NotImplementedError("子類必須實現 fetch_ohlcv 方法")


class CachedData:
    """緩存數據"""
    
    def __init__(self, data: pd.DataFrame, timestamp: datetime, ttl: int = 300):
        """初始化緩存數據
        
        Args:
            data: 數據
            timestamp: 緩存時間
            ttl: 生存時間（秒）
        """
        self.data = data
        self.timestamp = timestamp
        self.ttl = ttl
    
    def is_valid(self) -> bool:
        """檢查緩存是否有效
        
        Returns:
            bool: 是否有效
        """
        age = (datetime.now() - self.timestamp).total_seconds()
        return age < self.ttl


class DataManager:
    """數據管理器
    
    提供統一的數據接口，支持：
    - 多數據源（主數據源 + 備用數據源）
    - 數據緩存（減少 API 調用）
    - 容錯切換（主數據源失敗時自動切換）
    - 數據驗證（完整性和準確性）
    - 數據持久化（保存和載入）
    """
    
    def __init__(
        self,
        primary_source: Optional[DataSource] = None,
        backup_sources: Optional[List[DataSource]] = None,
        cache_ttl: int = 300,
        data_dir: str = "data/market_data"
    ):
        """初始化數據管理器
        
        Args:
            primary_source: 主數據源
            backup_sources: 備用數據源列表
            cache_ttl: 緩存生存時間（秒）
            data_dir: 數據目錄
        """
        self.primary_source = primary_source
        self.backup_sources = backup_sources or []
        self.cache_ttl = cache_ttl
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 緩存：(symbol, timeframe) -> CachedData
        self.cache: Dict[Tuple[str, str], CachedData] = {}
        
        # 數據獲取歷史
        self.fetch_history: List[Dict] = []
    
    def get_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000,
        use_cache: bool = True
    ) -> pd.DataFrame:
        """獲取 OHLCV 數據
        
        支持緩存和容錯切換。
        
        Args:
            symbol: 交易對
            timeframe: 時間週期
            start_time: 開始時間
            end_time: 結束時間
            limit: 數據條數限制
            use_cache: 是否使用緩存
            
        Returns:
            pd.DataFrame: OHLCV 數據
            
        Raises:
            ValueError: 所有數據源都失敗
        """
        cache_key = (symbol, timeframe)
        
        # 檢查緩存
        if use_cache and cache_key in self.cache:
            cached = self.cache[cache_key]
            if cached.is_valid():
                logger.debug(f"從緩存返回數據：{symbol} {timeframe}")
                self._record_fetch(symbol, timeframe, "cache", success=True)
                return cached.data.copy()
        
        # 嘗試從主數據源獲取
        if self.primary_source:
            try:
                data = self.primary_source.fetch_ohlcv(
                    symbol, timeframe, start_time, end_time, limit
                )
                
                # 驗證數據
                if self._validate_data(data):
                    # 更新緩存
                    self.cache[cache_key] = CachedData(data, datetime.now(), self.cache_ttl)
                    self._record_fetch(symbol, timeframe, self.primary_source.name, success=True)
                    logger.info(f"從主數據源獲取數據：{symbol} {timeframe}，{len(data)} 條")
                    return data
                else:
                    logger.warning(f"主數據源數據驗證失敗：{symbol} {timeframe}")
            except Exception as e:
                logger.warning(f"主數據源失敗：{self.primary_source.name}，錯誤：{e}")
                self._record_fetch(symbol, timeframe, self.primary_source.name, success=False, error=str(e))
        
        # 嘗試備用數據源
        for backup in self.backup_sources:
            try:
                data = backup.fetch_ohlcv(
                    symbol, timeframe, start_time, end_time, limit
                )
                
                # 驗證數據
                if self._validate_data(data):
                    # 更新緩存
                    self.cache[cache_key] = CachedData(data, datetime.now(), self.cache_ttl)
                    self._record_fetch(symbol, timeframe, backup.name, success=True)
                    logger.info(f"從備用數據源獲取數據：{backup.name}，{symbol} {timeframe}，{len(data)} 條")
                    return data
                else:
                    logger.warning(f"備用數據源數據驗證失敗：{backup.name}，{symbol} {timeframe}")
            except Exception as e:
                logger.warning(f"備用數據源失敗：{backup.name}，錯誤：{e}")
                self._record_fetch(symbol, timeframe, backup.name, success=False, error=str(e))
        
        # 所有數據源都失敗
        error_msg = f"所有數據源都失敗：{symbol} {timeframe}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    def _validate_data(self, data: pd.DataFrame) -> bool:
        """驗證數據完整性和準確性
        
        檢查：
        1. 必需字段存在
        2. 數值在合理範圍內
        3. 沒有空值
        
        Args:
            data: 數據
            
        Returns:
            bool: 是否有效
        """
        if data is None or data.empty:
            return False
        
        # 檢查必需字段
        required_fields = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        for field in required_fields:
            if field not in data.columns:
                logger.warning(f"數據缺少必需字段：{field}")
                return False
        
        # 檢查空值
        if data[required_fields].isnull().any().any():
            logger.warning("數據包含空值")
            return False
        
        # 檢查數值範圍
        if (data['high'] < data['low']).any():
            logger.warning("數據異常：high < low")
            return False
        
        if (data['high'] < data['open']).any() or (data['high'] < data['close']).any():
            logger.warning("數據異常：high < open 或 high < close")
            return False
        
        if (data['low'] > data['open']).any() or (data['low'] > data['close']).any():
            logger.warning("數據異常：low > open 或 low > close")
            return False
        
        if (data['volume'] < 0).any():
            logger.warning("數據異常：volume < 0")
            return False
        
        # 檢查價格是否為正數
        price_fields = ['open', 'high', 'low', 'close']
        if (data[price_fields] <= 0).any().any():
            logger.warning("數據異常：價格 <= 0")
            return False
        
        return True
    
    def _record_fetch(
        self,
        symbol: str,
        timeframe: str,
        source: str,
        success: bool,
        error: Optional[str] = None
    ) -> None:
        """記錄數據獲取歷史
        
        Args:
            symbol: 交易對
            timeframe: 時間週期
            source: 數據源
            success: 是否成功
            error: 錯誤訊息
        """
        record = {
            'timestamp': datetime.now().isoformat(),
            'symbol': symbol,
            'timeframe': timeframe,
            'source': source,
            'success': success,
            'error': error,
        }
        self.fetch_history.append(record)
    
    def clear_cache(self, symbol: Optional[str] = None, timeframe: Optional[str] = None) -> int:
        """清除緩存
        
        Args:
            symbol: 交易對（可選，如果提供則只清除該交易對的緩存）
            timeframe: 時間週期（可選，如果提供則只清除該週期的緩存）
            
        Returns:
            int: 清除的緩存數量
        """
        if symbol is None and timeframe is None:
            # 清除所有緩存
            count = len(self.cache)
            self.cache.clear()
            logger.info(f"清除所有緩存：{count} 條")
            return count
        
        # 清除特定緩存
        keys_to_remove = []
        for key in self.cache.keys():
            cache_symbol, cache_timeframe = key
            if (symbol is None or cache_symbol == symbol) and \
               (timeframe is None or cache_timeframe == timeframe):
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.cache[key]
        
        logger.info(f"清除緩存：{len(keys_to_remove)} 條")
        return len(keys_to_remove)
    
    def save_data(self, symbol: str, timeframe: str, data: pd.DataFrame) -> str:
        """保存數據到文件
        
        Args:
            symbol: 交易對
            timeframe: 時間週期
            data: 數據
            
        Returns:
            str: 文件路徑
        """
        filename = f"{symbol}_{timeframe}.csv"
        filepath = self.data_dir / filename
        
        data.to_csv(filepath, index=False)
        logger.info(f"保存數據到文件：{filepath}")
        
        return str(filepath)
    
    def load_data(self, symbol: str, timeframe: str) -> Optional[pd.DataFrame]:
        """從文件載入數據
        
        Args:
            symbol: 交易對
            timeframe: 時間週期
            
        Returns:
            Optional[pd.DataFrame]: 數據，如果文件不存在則返回 None
        """
        filename = f"{symbol}_{timeframe}.csv"
        filepath = self.data_dir / filename
        
        if not filepath.exists():
            logger.warning(f"數據文件不存在：{filepath}")
            return None
        
        try:
            data = pd.read_csv(filepath)
            
            # 轉換 timestamp 列
            if 'timestamp' in data.columns:
                data['timestamp'] = pd.to_datetime(data['timestamp'])
            
            logger.info(f"從文件載入數據：{filepath}，{len(data)} 條")
            return data
        except Exception as e:
            logger.error(f"載入數據失敗：{filepath}，錯誤：{e}")
            return None
    
    def get_fetch_history(
        self,
        symbol: Optional[str] = None,
        source: Optional[str] = None,
        success_only: bool = False
    ) -> List[Dict]:
        """獲取數據獲取歷史
        
        Args:
            symbol: 交易對（可選）
            source: 數據源（可選）
            success_only: 只返回成功的記錄
            
        Returns:
            List[Dict]: 歷史記錄列表
        """
        history = self.fetch_history
        
        if symbol:
            history = [r for r in history if r['symbol'] == symbol]
        
        if source:
            history = [r for r in history if r['source'] == source]
        
        if success_only:
            history = [r for r in history if r['success']]
        
        return history
    
    def get_cache_stats(self) -> Dict:
        """獲取緩存統計
        
        Returns:
            Dict: 緩存統計信息
        """
        total = len(self.cache)
        valid = sum(1 for cached in self.cache.values() if cached.is_valid())
        expired = total - valid
        
        return {
            'total': total,
            'valid': valid,
            'expired': expired,
            'cache_ttl': self.cache_ttl,
        }
