"""
DataManager 屬性測試

測試數據管理器的正確性屬性。
"""

import pytest
import pandas as pd
from hypothesis import given, strategies as st, assume, settings, HealthCheck
from datetime import datetime, timedelta
from typing import Optional
import tempfile
from pathlib import Path

from src.managers.data_manager import DataManager, DataSource, CachedData


# ============================================================================
# 測試數據生成策略
# ============================================================================

@st.composite
def ohlcv_dataframe_strategy(draw, min_rows=10, max_rows=100):
    """生成有效的 OHLCV 數據"""
    n_rows = draw(st.integers(min_value=min_rows, max_value=max_rows))
    
    # 生成基礎價格
    base_price = draw(st.floats(min_value=100, max_value=100000))
    
    data = []
    current_time = datetime.now()
    
    for i in range(n_rows):
        # 生成 OHLCV 數據，確保 high >= low，且 open/close 在 high/low 之間
        low = base_price * draw(st.floats(min_value=0.95, max_value=1.0))
        high = low * draw(st.floats(min_value=1.0, max_value=1.05))
        open_price = draw(st.floats(min_value=low, max_value=high))
        close_price = draw(st.floats(min_value=low, max_value=high))
        volume = draw(st.floats(min_value=0, max_value=1000000))
        
        data.append({
            'timestamp': current_time - timedelta(minutes=i),
            'open': open_price,
            'high': high,
            'low': low,
            'close': close_price,
            'volume': volume,
        })
    
    return pd.DataFrame(data)


class MockDataSource(DataSource):
    """模擬數據源"""
    
    def __init__(self, name: str, should_fail: bool = False, data: Optional[pd.DataFrame] = None):
        """初始化模擬數據源
        
        Args:
            name: 數據源名稱
            should_fail: 是否應該失敗
            data: 返回的數據
        """
        super().__init__(name)
        self.should_fail = should_fail
        self.data = data
        self.call_count = 0
    
    def fetch_ohlcv(self, symbol, timeframe, start_time=None, end_time=None, limit=1000):
        """獲取 OHLCV 數據"""
        self.call_count += 1
        
        if self.should_fail:
            raise ValueError(f"模擬數據源失敗：{self.name}")
        
        if self.data is not None:
            return self.data.copy()
        
        # 生成默認數據
        return pd.DataFrame({
            'timestamp': [datetime.now()],
            'open': [50000.0],
            'high': [51000.0],
            'low': [49000.0],
            'close': [50500.0],
            'volume': [1000.0],
        })


# ============================================================================
# Property 28: 數據源容錯切換
# ============================================================================

# Feature: multi-strategy-system, Property 28: 數據源容錯切換
@settings(suppress_health_check=[HealthCheck.too_slow])
@given(
    data=ohlcv_dataframe_strategy(),
)
def test_data_source_failover(data):
    """
    對於任何數據請求，當主數據源失敗時，系統應該自動嘗試備用數據源，
    且最終返回有效數據或明確的錯誤。
    """
    # 創建失敗的主數據源
    primary = MockDataSource("primary", should_fail=True)
    
    # 創建成功的備用數據源
    backup = MockDataSource("backup", should_fail=False, data=data)
    
    # 創建數據管理器
    manager = DataManager(
        primary_source=primary,
        backup_sources=[backup],
        cache_ttl=300
    )
    
    # 獲取數據（應該從備用數據源獲取）
    result = manager.get_ohlcv("BTCUSDT", "1h", use_cache=False)
    
    # 驗證：主數據源被調用
    assert primary.call_count == 1, "主數據源應該被調用"
    
    # 驗證：備用數據源被調用
    assert backup.call_count == 1, "備用數據源應該被調用"
    
    # 驗證：返回的數據與備用數據源的數據相同
    assert len(result) == len(data), "返回的數據長度應該與備用數據源相同"
    assert list(result.columns) == list(data.columns), "返回的數據列應該與備用數據源相同"


def test_all_sources_fail():
    """測試所有數據源都失敗的情況"""
    # 創建都失敗的數據源
    primary = MockDataSource("primary", should_fail=True)
    backup1 = MockDataSource("backup1", should_fail=True)
    backup2 = MockDataSource("backup2", should_fail=True)
    
    # 創建數據管理器
    manager = DataManager(
        primary_source=primary,
        backup_sources=[backup1, backup2],
        cache_ttl=300
    )
    
    # 嘗試獲取數據（應該拋出異常）
    with pytest.raises(ValueError, match="所有數據源都失敗"):
        manager.get_ohlcv("BTCUSDT", "1h", use_cache=False)
    
    # 驗證：所有數據源都被調用
    assert primary.call_count == 1
    assert backup1.call_count == 1
    assert backup2.call_count == 1


# ============================================================================
# Property 29: 數據緩存效率
# ============================================================================

# Feature: multi-strategy-system, Property 29: 數據緩存效率
@given(
    data=ohlcv_dataframe_strategy(),
    num_requests=st.integers(min_value=2, max_value=10),
)
def test_cache_efficiency(data, num_requests):
    """
    對於任何在緩存有效期內的重複數據請求，系統應該從緩存返回數據，
    而不是重新調用 API。
    """
    # 創建數據源
    source = MockDataSource("test", should_fail=False, data=data)
    
    # 創建數據管理器（緩存 TTL 很長）
    manager = DataManager(
        primary_source=source,
        cache_ttl=3600  # 1 小時
    )
    
    # 第一次請求（應該調用數據源）
    result1 = manager.get_ohlcv("BTCUSDT", "1h", use_cache=True)
    assert source.call_count == 1, "第一次請求應該調用數據源"
    
    # 後續請求（應該從緩存返回）
    for i in range(num_requests - 1):
        result = manager.get_ohlcv("BTCUSDT", "1h", use_cache=True)
        assert source.call_count == 1, f"第 {i+2} 次請求不應該調用數據源"
        
        # 驗證：返回的數據與第一次相同
        assert len(result) == len(result1)
        pd.testing.assert_frame_equal(result, result1)


def test_cache_expiration():
    """測試緩存過期"""
    # 創建數據源
    data = pd.DataFrame({
        'timestamp': [datetime.now()],
        'open': [50000.0],
        'high': [51000.0],
        'low': [49000.0],
        'close': [50500.0],
        'volume': [1000.0],
    })
    source = MockDataSource("test", should_fail=False, data=data)
    
    # 創建數據管理器（緩存 TTL 很短）
    manager = DataManager(
        primary_source=source,
        cache_ttl=1  # 1 秒
    )
    
    # 第一次請求
    manager.get_ohlcv("BTCUSDT", "1h", use_cache=True)
    assert source.call_count == 1
    
    # 立即再次請求（應該從緩存返回）
    manager.get_ohlcv("BTCUSDT", "1h", use_cache=True)
    assert source.call_count == 1
    
    # 等待緩存過期
    import time
    time.sleep(1.1)
    
    # 再次請求（緩存已過期，應該重新調用數據源）
    manager.get_ohlcv("BTCUSDT", "1h", use_cache=True)
    assert source.call_count == 2


def test_cache_disabled():
    """測試禁用緩存"""
    data = pd.DataFrame({
        'timestamp': [datetime.now()],
        'open': [50000.0],
        'high': [51000.0],
        'low': [49000.0],
        'close': [50500.0],
        'volume': [1000.0],
    })
    source = MockDataSource("test", should_fail=False, data=data)
    
    manager = DataManager(primary_source=source, cache_ttl=3600)
    
    # 多次請求，禁用緩存
    for i in range(3):
        manager.get_ohlcv("BTCUSDT", "1h", use_cache=False)
        assert source.call_count == i + 1, f"禁用緩存時，每次請求都應該調用數據源"


# ============================================================================
# Property 30: 數據完整性驗證
# ============================================================================

# Feature: multi-strategy-system, Property 30: 數據完整性驗證
@given(
    data=ohlcv_dataframe_strategy(),
)
def test_data_integrity_validation(data):
    """
    對於任何獲取的市場數據，系統應該驗證數據包含所有必需字段
    （timestamp, open, high, low, close, volume），且數值在合理範圍內。
    """
    source = MockDataSource("test", should_fail=False, data=data)
    manager = DataManager(primary_source=source)
    
    # 獲取數據
    result = manager.get_ohlcv("BTCUSDT", "1h", use_cache=False)
    
    # 驗證：包含所有必需字段
    required_fields = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
    for field in required_fields:
        assert field in result.columns, f"數據應該包含字段：{field}"
    
    # 驗證：沒有空值
    assert not result[required_fields].isnull().any().any(), "數據不應該包含空值"
    
    # 驗證：high >= low
    assert (result['high'] >= result['low']).all(), "high 應該 >= low"
    
    # 驗證：high >= open 和 high >= close
    assert (result['high'] >= result['open']).all(), "high 應該 >= open"
    assert (result['high'] >= result['close']).all(), "high 應該 >= close"
    
    # 驗證：low <= open 和 low <= close
    assert (result['low'] <= result['open']).all(), "low 應該 <= open"
    assert (result['low'] <= result['close']).all(), "low 應該 <= close"
    
    # 驗證：volume >= 0
    assert (result['volume'] >= 0).all(), "volume 應該 >= 0"
    
    # 驗證：價格 > 0
    price_fields = ['open', 'high', 'low', 'close']
    for field in price_fields:
        assert (result[field] > 0).all(), f"{field} 應該 > 0"


def test_invalid_data_rejection():
    """測試拒絕無效數據"""
    # 創建無效數據（high < low）
    invalid_data = pd.DataFrame({
        'timestamp': [datetime.now()],
        'open': [50000.0],
        'high': [49000.0],  # high < low（無效）
        'low': [51000.0],
        'close': [50500.0],
        'volume': [1000.0],
    })
    
    source = MockDataSource("test", should_fail=False, data=invalid_data)
    manager = DataManager(primary_source=source)
    
    # 嘗試獲取數據（應該失敗，因為數據無效）
    with pytest.raises(ValueError, match="所有數據源都失敗"):
        manager.get_ohlcv("BTCUSDT", "1h", use_cache=False)


def test_missing_field_rejection():
    """測試拒絕缺少字段的數據"""
    # 創建缺少字段的數據
    incomplete_data = pd.DataFrame({
        'timestamp': [datetime.now()],
        'open': [50000.0],
        'high': [51000.0],
        # 缺少 'low' 字段
        'close': [50500.0],
        'volume': [1000.0],
    })
    
    source = MockDataSource("test", should_fail=False, data=incomplete_data)
    manager = DataManager(primary_source=source)
    
    # 嘗試獲取數據（應該失敗）
    with pytest.raises(ValueError, match="所有數據源都失敗"):
        manager.get_ohlcv("BTCUSDT", "1h", use_cache=False)


# ============================================================================
# Property 31: 數據導出往返
# ============================================================================

# Feature: multi-strategy-system, Property 31: 數據導出往返
@given(
    data=ohlcv_dataframe_strategy(),
)
def test_data_export_import_roundtrip(data):
    """
    對於任何市場數據或交易數據，導出到文件後再導入，
    應該得到等價的數據（所有字段相同）。
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # 創建數據管理器
        manager = DataManager(data_dir=tmpdir)
        
        # 保存數據
        filepath = manager.save_data("BTCUSDT", "1h", data)
        assert Path(filepath).exists(), "文件應該被創建"
        
        # 載入數據
        loaded_data = manager.load_data("BTCUSDT", "1h")
        assert loaded_data is not None, "應該能夠載入數據"
        
        # 驗證：載入的數據與原始數據相同
        assert len(loaded_data) == len(data), "數據長度應該相同"
        assert list(loaded_data.columns) == list(data.columns), "數據列應該相同"
        
        # 驗證：數值相同（允許小的浮點數誤差）
        for col in data.columns:
            if col == 'timestamp':
                # timestamp 可能需要特殊處理
                continue
            if data[col].dtype in ['float64', 'float32']:
                assert loaded_data[col].equals(data[col]) or \
                       (loaded_data[col] - data[col]).abs().max() < 1e-6, \
                       f"列 {col} 的數值應該相同"


# ============================================================================
# 單元測試
# ============================================================================

def test_data_manager_initialization():
    """測試數據管理器初始化"""
    source = MockDataSource("test")
    manager = DataManager(primary_source=source, cache_ttl=300)
    
    assert manager.primary_source == source
    assert manager.cache_ttl == 300
    assert len(manager.cache) == 0
    assert len(manager.fetch_history) == 0


def test_clear_cache():
    """測試清除緩存"""
    data = pd.DataFrame({
        'timestamp': [datetime.now()],
        'open': [50000.0],
        'high': [51000.0],
        'low': [49000.0],
        'close': [50500.0],
        'volume': [1000.0],
    })
    
    source = MockDataSource("test", data=data)
    manager = DataManager(primary_source=source)
    
    # 添加緩存
    manager.get_ohlcv("BTCUSDT", "1h")
    manager.get_ohlcv("ETHUSDT", "1h")
    assert len(manager.cache) == 2
    
    # 清除特定緩存
    count = manager.clear_cache(symbol="BTCUSDT")
    assert count == 1
    assert len(manager.cache) == 1
    
    # 清除所有緩存
    count = manager.clear_cache()
    assert count == 1
    assert len(manager.cache) == 0


def test_fetch_history():
    """測試數據獲取歷史"""
    data = pd.DataFrame({
        'timestamp': [datetime.now()],
        'open': [50000.0],
        'high': [51000.0],
        'low': [49000.0],
        'close': [50500.0],
        'volume': [1000.0],
    })
    
    source = MockDataSource("test", data=data)
    manager = DataManager(primary_source=source)
    
    # 獲取數據
    manager.get_ohlcv("BTCUSDT", "1h", use_cache=False)
    manager.get_ohlcv("ETHUSDT", "1h", use_cache=False)
    
    # 檢查歷史
    history = manager.get_fetch_history()
    assert len(history) == 2
    
    # 過濾歷史
    btc_history = manager.get_fetch_history(symbol="BTCUSDT")
    assert len(btc_history) == 1
    assert btc_history[0]['symbol'] == "BTCUSDT"


def test_cache_stats():
    """測試緩存統計"""
    data = pd.DataFrame({
        'timestamp': [datetime.now()],
        'open': [50000.0],
        'high': [51000.0],
        'low': [49000.0],
        'close': [50500.0],
        'volume': [1000.0],
    })
    
    source = MockDataSource("test", data=data)
    manager = DataManager(primary_source=source, cache_ttl=1)
    
    # 添加緩存
    manager.get_ohlcv("BTCUSDT", "1h")
    
    # 檢查統計
    stats = manager.get_cache_stats()
    assert stats['total'] == 1
    assert stats['valid'] == 1
    assert stats['expired'] == 0
    
    # 等待緩存過期
    import time
    time.sleep(1.1)
    
    # 再次檢查統計
    stats = manager.get_cache_stats()
    assert stats['total'] == 1
    assert stats['valid'] == 0
    assert stats['expired'] == 1


def test_load_nonexistent_data():
    """測試載入不存在的數據"""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = DataManager(data_dir=tmpdir)
        
        # 嘗試載入不存在的數據
        data = manager.load_data("BTCUSDT", "1h")
        assert data is None, "不存在的數據應該返回 None"
