"""
Optimizer 屬性測試

測試參數優化器的正確性屬性。
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any

from src.analysis.optimizer import Optimizer, OptimizationResult
from src.strategies.multi_timeframe_strategy import MultiTimeframeStrategy
from src.models.config import StrategyConfig


# 測試數據生成器
@st.composite
def market_data_strategy(draw):
    """生成市場數據"""
    n_candles = draw(st.integers(min_value=200, max_value=500))
    base_price = draw(st.floats(min_value=1000, max_value=50000))
    
    timestamps = [datetime.now() - timedelta(hours=i) for i in range(n_candles, 0, -1)]
    
    data = {
        'timestamp': timestamps,
        'open': [],
        'high': [],
        'low': [],
        'close': [],
        'volume': [],
    }
    
    current_price = base_price
    for _ in range(n_candles):
        change = draw(st.floats(min_value=-0.05, max_value=0.05))
        current_price = current_price * (1 + change)
        
        open_price = current_price
        high_price = open_price * (1 + abs(draw(st.floats(min_value=0, max_value=0.02))))
        low_price = open_price * (1 - abs(draw(st.floats(min_value=0, max_value=0.02))))
        close_price = draw(st.floats(min_value=low_price, max_value=high_price))
        volume = draw(st.floats(min_value=100, max_value=10000))
        
        data['open'].append(open_price)
        data['high'].append(high_price)
        data['low'].append(low_price)
        data['close'].append(close_price)
        data['volume'].append(volume)
    
    df = pd.DataFrame(data)
    return {'1h': df}


@st.composite
def param_grid_strategy(draw):
    """生成參數網格"""
    # 生成 2-3 個參數
    n_params = draw(st.integers(min_value=2, max_value=3))
    
    param_grid = {}
    for i in range(n_params):
        param_name = f"param_{i}"
        # 每個參數 2-4 個值
        n_values = draw(st.integers(min_value=2, max_value=4))
        values = [draw(st.floats(min_value=0.1, max_value=10.0)) for _ in range(n_values)]
        param_grid[param_name] = values
    
    return param_grid


# Feature: multi-strategy-system, Property 12: 參數優化數據分離
@given(market_data_strategy())
@settings(max_examples=100, deadline=None)
def test_data_separation(market_data):
    """
    對於任何參數優化過程，訓練集和驗證集不應該有重疊的數據點。
    
    Validates: Requirements 5.4
    """
    # 創建基礎配置
    base_config = {
        'strategy_id': 'test-strategy',
        'strategy_name': 'Test Strategy',
        'version': '1.0.0',
        'enabled': True,
        'symbol': 'BTCUSDT',
        'timeframes': ['1h'],
        'parameters': {
            'stop_loss_atr': 1.5,
            'take_profit_atr': 3.0,
        },
        'risk_management': {
            'position_size': 0.1,
            'leverage': 1,
            'max_trades_per_day': 10,
            'max_consecutive_losses': 5,
            'daily_loss_limit': 0.5,
        },
        'entry_conditions': [],
        'exit_conditions': {},
        'notifications': {},
    }
    
    # 創建優化器
    optimizer = Optimizer(
        strategy_class=MultiTimeframeStrategy,
        base_config=base_config,
        market_data=market_data,
        train_ratio=0.7,
    )
    
    # 驗證數據分離
    for timeframe in market_data.keys():
        train_df = optimizer.train_data[timeframe]
        validation_df = optimizer.validation_data[timeframe]
        
        # 獲取時間戳
        train_timestamps = set(train_df['timestamp'].tolist())
        validation_timestamps = set(validation_df['timestamp'].tolist())
        
        # 驗證沒有重疊
        overlap = train_timestamps.intersection(validation_timestamps)
        assert len(overlap) == 0, f"訓練集和驗證集有 {len(overlap)} 個重疊的數據點"
        
        # 驗證訓練集在驗證集之前
        if len(train_df) > 0 and len(validation_df) > 0:
            last_train_time = train_df['timestamp'].max()
            first_validation_time = validation_df['timestamp'].min()
            assert last_train_time <= first_validation_time, "訓練集應該在驗證集之前"


# Feature: multi-strategy-system, Property 13: 網格搜索完整性
@given(param_grid_strategy())
@settings(max_examples=50, deadline=None)
def test_grid_search_completeness(param_grid):
    """
    對於任何定義的參數網格，網格搜索應該測試所有可能的參數組合。
    
    Validates: Requirements 5.1
    """
    # 計算預期的組合數
    expected_combinations = 1
    for values in param_grid.values():
        expected_combinations *= len(values)
    
    # 如果組合數太大，跳過測試
    assume(expected_combinations <= 100)
    
    # 創建簡單的市場數據
    n_candles = 200
    timestamps = [datetime.now() - timedelta(hours=i) for i in range(n_candles, 0, -1)]
    base_price = 10000.0
    
    data = {
        'timestamp': timestamps,
        'open': [base_price] * n_candles,
        'high': [base_price * 1.01] * n_candles,
        'low': [base_price * 0.99] * n_candles,
        'close': [base_price] * n_candles,
        'volume': [1000.0] * n_candles,
    }
    
    market_data = {'1h': pd.DataFrame(data)}
    
    # 創建基礎配置
    base_config = {
        'strategy_id': 'test-strategy',
        'strategy_name': 'Test Strategy',
        'version': '1.0.0',
        'enabled': True,
        'symbol': 'BTCUSDT',
        'timeframes': ['1h'],
        'parameters': {
            'stop_loss_atr': 1.5,
            'take_profit_atr': 3.0,
        },
        'risk_management': {
            'position_size': 0.1,
            'leverage': 1,
            'max_trades_per_day': 10,
            'max_consecutive_losses': 5,
            'daily_loss_limit': 0.5,
        },
        'entry_conditions': [],
        'exit_conditions': {},
        'notifications': {},
    }
    
    # 創建優化器
    optimizer = Optimizer(
        strategy_class=MultiTimeframeStrategy,
        base_config=base_config,
        market_data=market_data,
        train_ratio=0.7,
    )
    
    # 執行網格搜索
    result = optimizer.grid_search(param_grid)
    
    # 驗證測試了所有組合
    assert len(result.all_results) == expected_combinations, \
        f"應該測試 {expected_combinations} 個組合，實際測試了 {len(result.all_results)} 個"
    
    # 驗證所有參數組合都是唯一的
    tested_combinations = set()
    for res in result.all_results:
        params_tuple = tuple(sorted(res['params'].items()))
        assert params_tuple not in tested_combinations, "發現重複的參數組合"
        tested_combinations.add(params_tuple)


# Feature: multi-strategy-system, Property 14: 優化報告完整性
@given(st.integers(min_value=5, max_value=20))
@settings(max_examples=50, deadline=None)
def test_optimization_report_completeness(n_iterations):
    """
    對於任何完成的參數優化，生成的報告應該包含最佳參數、訓練集性能、
    驗證集性能和參數敏感度分析。
    
    Validates: Requirements 5.6, 5.7
    """
    # 創建簡單的市場數據
    n_candles = 200
    timestamps = [datetime.now() - timedelta(hours=i) for i in range(n_candles, 0, -1)]
    base_price = 10000.0
    
    data = {
        'timestamp': timestamps,
        'open': [base_price] * n_candles,
        'high': [base_price * 1.01] * n_candles,
        'low': [base_price * 0.99] * n_candles,
        'close': [base_price] * n_candles,
        'volume': [1000.0] * n_candles,
    }
    
    market_data = {'1h': pd.DataFrame(data)}
    
    # 創建基礎配置
    base_config = {
        'strategy_id': 'test-strategy',
        'strategy_name': 'Test Strategy',
        'version': '1.0.0',
        'enabled': True,
        'symbol': 'BTCUSDT',
        'timeframes': ['1h'],
        'parameters': {
            'stop_loss_atr': 1.5,
            'take_profit_atr': 3.0,
        },
        'risk_management': {
            'position_size': 0.1,
            'leverage': 1,
            'max_trades_per_day': 10,
            'max_consecutive_losses': 5,
            'daily_loss_limit': 0.5,
        },
        'entry_conditions': [],
        'exit_conditions': {},
        'notifications': {},
    }
    
    # 創建優化器
    optimizer = Optimizer(
        strategy_class=MultiTimeframeStrategy,
        base_config=base_config,
        market_data=market_data,
        train_ratio=0.7,
    )
    
    # 定義參數分佈
    param_distributions = {
        'param_1': lambda: np.random.uniform(0.5, 5.0),
        'param_2': lambda: np.random.uniform(1.0, 10.0),
    }
    
    # 執行隨機搜索
    result = optimizer.random_search(param_distributions, n_iterations=n_iterations)
    
    # 驗證結果包含所有必需字段
    assert result.best_params is not None, "結果應該包含最佳參數"
    assert isinstance(result.best_params, dict), "最佳參數應該是字典"
    
    assert result.train_performance is not None, "結果應該包含訓練集性能"
    assert isinstance(result.train_performance, dict), "訓練集性能應該是字典"
    
    assert result.validation_performance is not None, "結果應該包含驗證集性能"
    assert isinstance(result.validation_performance, dict), "驗證集性能應該是字典"
    
    assert result.parameter_sensitivity is not None, "結果應該包含參數敏感度"
    assert isinstance(result.parameter_sensitivity, dict), "參數敏感度應該是字典"
    
    # 驗證參數敏感度包含所有參數
    for param_name in param_distributions.keys():
        assert param_name in result.parameter_sensitivity, \
            f"參數敏感度應該包含參數 {param_name}"
    
    # 生成報告
    report = optimizer.generate_report(result)
    
    # 驗證報告包含關鍵信息
    assert "最佳參數" in report, "報告應該包含最佳參數"
    assert "訓練集性能" in report, "報告應該包含訓練集性能"
    assert "驗證集性能" in report, "報告應該包含驗證集性能"
    assert "參數敏感度分析" in report, "報告應該包含參數敏感度分析"
    
    # 驗證報告包含優化方法和指標
    assert result.method in report, "報告應該包含優化方法"
    assert optimizer.optimization_metric in report, "報告應該包含優化指標"


# 額外的單元測試風格的屬性測試
def test_optimizer_initialization():
    """測試優化器初始化"""
    # 創建簡單的市場數據
    n_candles = 100
    timestamps = [datetime.now() - timedelta(hours=i) for i in range(n_candles, 0, -1)]
    
    data = {
        'timestamp': timestamps,
        'open': [10000.0] * n_candles,
        'high': [10100.0] * n_candles,
        'low': [9900.0] * n_candles,
        'close': [10000.0] * n_candles,
        'volume': [1000.0] * n_candles,
    }
    
    market_data = {'1h': pd.DataFrame(data)}
    
    base_config = {
        'strategy_id': 'test-strategy',
        'strategy_name': 'Test Strategy',
        'version': '1.0.0',
        'enabled': True,
        'symbol': 'BTCUSDT',
        'timeframes': ['1h'],
        'parameters': {},
        'risk_management': {
            'position_size': 0.1,
            'leverage': 1,
            'max_trades_per_day': 10,
            'max_consecutive_losses': 5,
            'daily_loss_limit': 0.5,
        },
        'entry_conditions': [],
        'exit_conditions': {},
        'notifications': {},
    }
    
    # 測試不同的訓練集比例
    for train_ratio in [0.5, 0.6, 0.7, 0.8]:
        optimizer = Optimizer(
            strategy_class=MultiTimeframeStrategy,
            base_config=base_config,
            market_data=market_data,
            train_ratio=train_ratio,
        )
        
        # 驗證數據分割
        train_size = len(optimizer.train_data['1h'])
        validation_size = len(optimizer.validation_data['1h'])
        total_size = train_size + validation_size
        
        assert total_size == n_candles, "訓練集和驗證集的總大小應該等於原始數據大小"
        
        actual_ratio = train_size / total_size
        assert abs(actual_ratio - train_ratio) < 0.05, \
            f"實際訓練集比例 {actual_ratio:.2f} 應該接近設定值 {train_ratio:.2f}"


def test_optimization_result_to_dict():
    """測試優化結果轉換為字典"""
    result = OptimizationResult(
        best_params={'param1': 1.5, 'param2': 2.0},
        best_score=0.85,
        all_results=[
            {'params': {'param1': 1.0, 'param2': 2.0}, 'train_score': 0.7, 'validation_score': 0.6},
            {'params': {'param1': 1.5, 'param2': 2.0}, 'train_score': 0.9, 'validation_score': 0.85},
        ],
        train_performance={'win_rate': 0.6, 'total_pnl': 100.0},
        validation_performance={'win_rate': 0.55, 'total_pnl': 80.0},
        parameter_sensitivity={'param1': [(1.0, 0.6), (1.5, 0.85)]},
        optimization_time=120.5,
        method='grid_search',
    )
    
    result_dict = result.to_dict()
    
    # 驗證字典包含所有必需字段
    assert 'best_params' in result_dict
    assert 'best_score' in result_dict
    assert 'train_performance' in result_dict
    assert 'validation_performance' in result_dict
    assert 'parameter_sensitivity' in result_dict
    assert 'optimization_time' in result_dict
    assert 'method' in result_dict
    assert 'total_combinations_tested' in result_dict
    
    # 驗證值
    assert result_dict['best_params'] == {'param1': 1.5, 'param2': 2.0}
    assert result_dict['best_score'] == 0.85
    assert result_dict['total_combinations_tested'] == 2
    assert result_dict['method'] == 'grid_search'
