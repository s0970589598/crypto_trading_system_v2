"""
Optimizer 單元測試

測試參數優化器的具體功能。
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from src.analysis.optimizer import Optimizer, OptimizationResult
from src.strategies.multi_timeframe_strategy import MultiTimeframeStrategy


def create_simple_market_data(n_candles=200):
    """創建簡單的市場數據用於測試"""
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
    
    return {'1h': pd.DataFrame(data)}


def create_base_config():
    """創建基礎配置"""
    return {
        'strategy_id': 'test-strategy',
        'strategy_name': 'Test Strategy',
        'version': '1.0.0',
        'enabled': True,
        'symbol': 'BTCUSDT',
        'timeframes': ['1h'],
        'parameters': {
            'stop_loss_atr': 1.5,
            'take_profit_atr': 3.0,
            'rsi_range': [30, 70],
            'ema_distance': 0.03,
            'volume_threshold': 1.0,
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


class TestOptimizerInitialization:
    """測試優化器初始化"""
    
    def test_initialization_with_default_params(self):
        """測試使用默認參數初始化"""
        market_data = create_simple_market_data()
        base_config = create_base_config()
        
        optimizer = Optimizer(
            strategy_class=MultiTimeframeStrategy,
            base_config=base_config,
            market_data=market_data,
        )
        
        assert optimizer.strategy_class == MultiTimeframeStrategy
        assert optimizer.base_config == base_config
        assert optimizer.train_ratio == 0.7
        assert optimizer.optimization_metric == 'sharpe_ratio'
    
    def test_initialization_with_custom_params(self):
        """測試使用自定義參數初始化"""
        market_data = create_simple_market_data()
        base_config = create_base_config()
        
        optimizer = Optimizer(
            strategy_class=MultiTimeframeStrategy,
            base_config=base_config,
            market_data=market_data,
            train_ratio=0.8,
            optimization_metric='profit_factor',
        )
        
        assert optimizer.train_ratio == 0.8
        assert optimizer.optimization_metric == 'profit_factor'
    
    def test_data_split(self):
        """測試數據分割"""
        n_candles = 100
        market_data = create_simple_market_data(n_candles)
        base_config = create_base_config()
        
        optimizer = Optimizer(
            strategy_class=MultiTimeframeStrategy,
            base_config=base_config,
            market_data=market_data,
            train_ratio=0.7,
        )
        
        # 驗證訓練集和驗證集大小
        train_size = len(optimizer.train_data['1h'])
        validation_size = len(optimizer.validation_data['1h'])
        
        assert train_size + validation_size == n_candles
        assert abs(train_size / n_candles - 0.7) < 0.05  # 允許小誤差


class TestGridSearch:
    """測試網格搜索"""
    
    def test_grid_search_with_small_grid(self):
        """測試小規模網格搜索"""
        market_data = create_simple_market_data()
        base_config = create_base_config()
        
        optimizer = Optimizer(
            strategy_class=MultiTimeframeStrategy,
            base_config=base_config,
            market_data=market_data,
        )
        
        # 定義小規模參數網格
        param_grid = {
            'parameters.stop_loss_atr': [1.0, 2.0],
            'parameters.take_profit_atr': [2.0, 3.0],
        }
        
        # 執行網格搜索
        result = optimizer.grid_search(param_grid)
        
        # 驗證結果
        assert isinstance(result, OptimizationResult)
        assert result.method == 'grid_search'
        assert len(result.all_results) <= 4  # 最多 2x2 = 4 個組合
    
    def test_grid_search_with_max_combinations(self):
        """測試限制最大組合數的網格搜索"""
        market_data = create_simple_market_data()
        base_config = create_base_config()
        
        optimizer = Optimizer(
            strategy_class=MultiTimeframeStrategy,
            base_config=base_config,
            market_data=market_data,
        )
        
        # 定義較大的參數網格
        param_grid = {
            'parameters.stop_loss_atr': [1.0, 1.5, 2.0, 2.5],
            'parameters.take_profit_atr': [2.0, 2.5, 3.0, 3.5],
        }
        
        # 限制最大組合數
        result = optimizer.grid_search(param_grid, max_combinations=5)
        
        # 驗證結果
        assert len(result.all_results) <= 5


class TestRandomSearch:
    """測試隨機搜索"""
    
    def test_random_search_basic(self):
        """測試基本隨機搜索"""
        market_data = create_simple_market_data()
        base_config = create_base_config()
        
        optimizer = Optimizer(
            strategy_class=MultiTimeframeStrategy,
            base_config=base_config,
            market_data=market_data,
        )
        
        # 定義參數分佈
        param_distributions = {
            'parameters.stop_loss_atr': lambda: np.random.uniform(0.5, 3.0),
            'parameters.take_profit_atr': lambda: np.random.uniform(1.0, 5.0),
        }
        
        # 執行隨機搜索
        result = optimizer.random_search(param_distributions, n_iterations=5)
        
        # 驗證結果
        assert isinstance(result, OptimizationResult)
        assert result.method == 'random_search'
        assert len(result.all_results) <= 5
    
    def test_random_search_randomness(self):
        """測試隨機搜索的隨機性"""
        market_data = create_simple_market_data()
        base_config = create_base_config()
        
        optimizer = Optimizer(
            strategy_class=MultiTimeframeStrategy,
            base_config=base_config,
            market_data=market_data,
        )
        
        # 定義參數分佈
        param_distributions = {
            'parameters.stop_loss_atr': lambda: np.random.uniform(0.5, 3.0),
        }
        
        # 執行兩次隨機搜索
        result1 = optimizer.random_search(param_distributions, n_iterations=10)
        result2 = optimizer.random_search(param_distributions, n_iterations=10)
        
        # 驗證兩次搜索的參數不完全相同（隨機性）
        params1 = [r['params']['parameters.stop_loss_atr'] for r in result1.all_results if r['params']]
        params2 = [r['params']['parameters.stop_loss_atr'] for r in result2.all_results if r['params']]
        
        # 至少有一些參數不同
        if len(params1) > 0 and len(params2) > 0:
            assert params1 != params2


class TestBayesianOptimization:
    """測試貝葉斯優化"""
    
    def test_bayesian_optimization_basic(self):
        """測試基本貝葉斯優化"""
        market_data = create_simple_market_data()
        base_config = create_base_config()
        
        optimizer = Optimizer(
            strategy_class=MultiTimeframeStrategy,
            base_config=base_config,
            market_data=market_data,
        )
        
        # 定義參數邊界
        param_bounds = {
            'parameters.stop_loss_atr': (0.5, 3.0),
            'parameters.take_profit_atr': (1.0, 5.0),
        }
        
        # 執行貝葉斯優化
        result = optimizer.bayesian_optimization(
            param_bounds,
            n_iterations=10,
            n_initial_points=3
        )
        
        # 驗證結果
        assert isinstance(result, OptimizationResult)
        assert result.method == 'bayesian_optimization'
        assert len(result.all_results) <= 10


class TestDataSeparation:
    """測試數據分離"""
    
    def test_train_validation_no_overlap(self):
        """測試訓練集和驗證集沒有重疊"""
        market_data = create_simple_market_data(100)
        base_config = create_base_config()
        
        optimizer = Optimizer(
            strategy_class=MultiTimeframeStrategy,
            base_config=base_config,
            market_data=market_data,
            train_ratio=0.7,
        )
        
        # 獲取時間戳
        train_timestamps = set(optimizer.train_data['1h']['timestamp'].tolist())
        validation_timestamps = set(optimizer.validation_data['1h']['timestamp'].tolist())
        
        # 驗證沒有重疊
        overlap = train_timestamps.intersection(validation_timestamps)
        assert len(overlap) == 0
    
    def test_train_before_validation(self):
        """測試訓練集在驗證集之前"""
        market_data = create_simple_market_data(100)
        base_config = create_base_config()
        
        optimizer = Optimizer(
            strategy_class=MultiTimeframeStrategy,
            base_config=base_config,
            market_data=market_data,
            train_ratio=0.7,
        )
        
        # 獲取最後的訓練時間和第一個驗證時間
        last_train_time = optimizer.train_data['1h']['timestamp'].max()
        first_validation_time = optimizer.validation_data['1h']['timestamp'].min()
        
        # 驗證訓練集在驗證集之前
        assert last_train_time <= first_validation_time


class TestOptimizationResult:
    """測試優化結果"""
    
    def test_optimization_result_to_dict(self):
        """測試優化結果轉換為字典"""
        result = OptimizationResult(
            best_params={'param1': 1.5},
            best_score=0.85,
            all_results=[
                {'params': {'param1': 1.0}, 'train_score': 0.7, 'validation_score': 0.6},
                {'params': {'param1': 1.5}, 'train_score': 0.9, 'validation_score': 0.85},
            ],
            train_performance={'win_rate': 0.6},
            validation_performance={'win_rate': 0.55},
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
        assert result_dict['best_params'] == {'param1': 1.5}
        assert result_dict['best_score'] == 0.85
        assert result_dict['total_combinations_tested'] == 2


class TestReportGeneration:
    """測試報告生成"""
    
    def test_generate_report_basic(self):
        """測試基本報告生成"""
        market_data = create_simple_market_data()
        base_config = create_base_config()
        
        optimizer = Optimizer(
            strategy_class=MultiTimeframeStrategy,
            base_config=base_config,
            market_data=market_data,
        )
        
        # 創建測試結果
        result = OptimizationResult(
            best_params={'parameters.stop_loss_atr': 1.5},
            best_score=0.85,
            all_results=[],
            train_performance={'win_rate': 0.6, 'total_pnl': 100.0, 'total_trades': 10},
            validation_performance={'win_rate': 0.55, 'total_pnl': 80.0, 'total_trades': 8},
            parameter_sensitivity={'parameters.stop_loss_atr': [(1.0, 0.6), (1.5, 0.85)]},
            optimization_time=120.5,
            method='grid_search',
        )
        
        # 生成報告
        report = optimizer.generate_report(result)
        
        # 驗證報告包含關鍵信息
        assert '參數優化報告' in report
        assert '最佳參數' in report
        assert '訓練集性能' in report
        assert '驗證集性能' in report
        assert '參數敏感度分析' in report
        assert 'grid_search' in report
        assert 'sharpe_ratio' in report
    
    def test_report_contains_metrics(self):
        """測試報告包含性能指標"""
        market_data = create_simple_market_data()
        base_config = create_base_config()
        
        optimizer = Optimizer(
            strategy_class=MultiTimeframeStrategy,
            base_config=base_config,
            market_data=market_data,
        )
        
        result = OptimizationResult(
            best_params={},
            best_score=0.85,
            all_results=[],
            train_performance={
                'win_rate': 0.6,
                'total_pnl': 100.0,
                'total_trades': 10,
                'profit_factor': 2.5,
                'sharpe_ratio': 1.8,
            },
            validation_performance={
                'win_rate': 0.55,
                'total_pnl': 80.0,
                'total_trades': 8,
                'profit_factor': 2.0,
                'sharpe_ratio': 1.5,
            },
            parameter_sensitivity={},
            optimization_time=120.5,
            method='random_search',
        )
        
        report = optimizer.generate_report(result)
        
        # 驗證報告包含性能指標
        assert '勝率' in report
        assert '總損益' in report
        assert '獲利因子' in report
        assert '夏普比率' in report
