"""
參數優化器

提供多種參數優化方法：
- 網格搜索（Grid Search）
- 隨機搜索（Random Search）
- 貝葉斯優化（Bayesian Optimization）
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Any, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, field
import logging
import itertools
import random
from copy import deepcopy

from src.execution.strategy import Strategy
from src.execution.backtest_engine import BacktestEngine
from src.models.backtest import BacktestResult


logger = logging.getLogger(__name__)


@dataclass
class OptimizationResult:
    """優化結果"""
    best_params: Dict[str, Any]
    best_score: float
    all_results: List[Dict[str, Any]]
    train_performance: Dict[str, float]
    validation_performance: Dict[str, float]
    parameter_sensitivity: Dict[str, List[Tuple[Any, float]]]
    optimization_time: float
    method: str
    
    def to_dict(self) -> dict:
        """轉換為字典"""
        return {
            'best_params': self.best_params,
            'best_score': self.best_score,
            'train_performance': self.train_performance,
            'validation_performance': self.validation_performance,
            'parameter_sensitivity': self.parameter_sensitivity,
            'optimization_time': self.optimization_time,
            'method': self.method,
            'total_combinations_tested': len(self.all_results),
        }


class Optimizer:
    """參數優化器
    
    支持多種優化方法：
    - 網格搜索：測試所有參數組合
    - 隨機搜索：隨機採樣參數空間
    - 貝葉斯優化：使用高斯過程優化
    """
    
    def __init__(
        self,
        strategy_class: type,
        base_config: Dict[str, Any],
        market_data: Dict[str, pd.DataFrame],
        initial_capital: float = 1000.0,
        commission: float = 0.0005,
        train_ratio: float = 0.7,
        optimization_metric: str = 'sharpe_ratio'
    ):
        """初始化優化器
        
        Args:
            strategy_class: 策略類
            base_config: 基礎配置
            market_data: 市場數據
            initial_capital: 初始資金
            commission: 手續費率
            train_ratio: 訓練集比例（0-1）
            optimization_metric: 優化指標（sharpe_ratio, profit_factor, win_rate等）
        """
        self.strategy_class = strategy_class
        self.base_config = base_config
        self.market_data = market_data
        self.initial_capital = initial_capital
        self.commission = commission
        self.train_ratio = train_ratio
        self.optimization_metric = optimization_metric
        
        # 分割訓練集和驗證集
        self.train_data, self.validation_data = self._split_data()
        
        logger.info(f"優化器初始化完成，優化指標：{optimization_metric}")
    
    def _split_data(self) -> Tuple[Dict[str, pd.DataFrame], Dict[str, pd.DataFrame]]:
        """分割訓練集和驗證集
        
        Returns:
            Tuple[Dict, Dict]: (訓練集, 驗證集)
        """
        train_data = {}
        validation_data = {}
        
        for timeframe, df in self.market_data.items():
            # 計算分割點
            split_idx = int(len(df) * self.train_ratio)
            
            # 分割數據
            train_data[timeframe] = df.iloc[:split_idx].copy()
            validation_data[timeframe] = df.iloc[split_idx:].copy()
            
            logger.debug(f"{timeframe}: 訓練集 {len(train_data[timeframe])} 條，驗證集 {len(validation_data[timeframe])} 條")
        
        return train_data, validation_data
    
    def _evaluate_params(
        self,
        params: Dict[str, Any],
        data: Dict[str, pd.DataFrame]
    ) -> Tuple[float, BacktestResult]:
        """評估參數組合
        
        Args:
            params: 參數字典
            data: 市場數據
        
        Returns:
            Tuple[float, BacktestResult]: (評分, 回測結果)
        """
        # 創建配置
        config = deepcopy(self.base_config)
        
        # 更新參數
        for key, value in params.items():
            if '.' in key:
                # 處理嵌套參數（如 risk_management.leverage）
                parts = key.split('.')
                current = config
                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                current[parts[-1]] = value
            else:
                config[key] = value
        
        # 創建策略實例
        from src.models.config import StrategyConfig
        strategy_config = StrategyConfig.from_dict(config)
        strategy = self.strategy_class(strategy_config)
        
        # 回測
        engine = BacktestEngine(self.initial_capital, self.commission)
        result = engine.run_single_strategy(strategy, data)
        
        # 獲取評分
        score = self._get_score(result)
        
        return score, result
    
    def _get_score(self, result: BacktestResult) -> float:
        """獲取回測結果的評分
        
        Args:
            result: 回測結果
        
        Returns:
            float: 評分
        """
        if self.optimization_metric == 'sharpe_ratio':
            return result.sharpe_ratio
        elif self.optimization_metric == 'profit_factor':
            return result.profit_factor
        elif self.optimization_metric == 'win_rate':
            return result.win_rate
        elif self.optimization_metric == 'total_pnl':
            return result.total_pnl
        elif self.optimization_metric == 'total_pnl_pct':
            return result.total_pnl_pct
        else:
            # 默認使用夏普比率
            return result.sharpe_ratio
    
    def grid_search(
        self,
        param_grid: Dict[str, List[Any]],
        max_combinations: Optional[int] = None
    ) -> OptimizationResult:
        """網格搜索
        
        測試所有參數組合。
        
        Args:
            param_grid: 參數網格，格式：{'param_name': [value1, value2, ...]}
            max_combinations: 最大組合數（可選，用於限制搜索空間）
        
        Returns:
            OptimizationResult: 優化結果
        """
        logger.info("開始網格搜索")
        start_time = datetime.now()
        
        # 生成所有參數組合
        param_names = list(param_grid.keys())
        param_values = [param_grid[name] for name in param_names]
        all_combinations = list(itertools.product(*param_values))
        
        # 限制組合數
        if max_combinations and len(all_combinations) > max_combinations:
            logger.warning(f"參數組合數 {len(all_combinations)} 超過限制 {max_combinations}，將隨機採樣")
            all_combinations = random.sample(all_combinations, max_combinations)
        
        logger.info(f"總共 {len(all_combinations)} 個參數組合")
        
        # 測試所有組合
        all_results = []
        best_score = float('-inf')
        best_params = None
        best_train_result = None
        best_validation_result = None
        
        for i, combination in enumerate(all_combinations):
            # 構建參數字典
            params = dict(zip(param_names, combination))
            
            try:
                # 在訓練集上評估
                train_score, train_result = self._evaluate_params(params, self.train_data)
                
                # 在驗證集上評估
                validation_score, validation_result = self._evaluate_params(params, self.validation_data)
                
                # 記錄結果
                result_entry = {
                    'params': params,
                    'train_score': train_score,
                    'validation_score': validation_score,
                    'train_trades': train_result.total_trades,
                    'validation_trades': validation_result.total_trades,
                }
                all_results.append(result_entry)
                
                # 更新最佳結果（基於驗證集）
                if validation_score > best_score:
                    best_score = validation_score
                    best_params = params
                    best_train_result = train_result
                    best_validation_result = validation_result
                
                if (i + 1) % 10 == 0:
                    logger.info(f"進度：{i + 1}/{len(all_combinations)}，當前最佳評分：{best_score:.4f}")
            
            except Exception as e:
                logger.error(f"評估參數組合失敗：{params}，錯誤：{e}")
                continue
        
        # 計算參數敏感度
        parameter_sensitivity = self._calculate_sensitivity(all_results, param_names)
        
        # 計算優化時間
        optimization_time = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"網格搜索完成，最佳評分：{best_score:.4f}，耗時：{optimization_time:.2f}秒")
        
        return OptimizationResult(
            best_params=best_params or {},
            best_score=best_score,
            all_results=all_results,
            train_performance=best_train_result.to_dict() if best_train_result else {},
            validation_performance=best_validation_result.to_dict() if best_validation_result else {},
            parameter_sensitivity=parameter_sensitivity,
            optimization_time=optimization_time,
            method='grid_search',
        )
    
    def random_search(
        self,
        param_distributions: Dict[str, Callable[[], Any]],
        n_iterations: int = 100
    ) -> OptimizationResult:
        """隨機搜索
        
        隨機採樣參數空間。
        
        Args:
            param_distributions: 參數分佈，格式：{'param_name': sampling_function}
            n_iterations: 迭代次數
        
        Returns:
            OptimizationResult: 優化結果
        """
        logger.info(f"開始隨機搜索，迭代次數：{n_iterations}")
        start_time = datetime.now()
        
        all_results = []
        best_score = float('-inf')
        best_params = None
        best_train_result = None
        best_validation_result = None
        
        for i in range(n_iterations):
            # 隨機採樣參數
            params = {name: sampler() for name, sampler in param_distributions.items()}
            
            try:
                # 在訓練集上評估
                train_score, train_result = self._evaluate_params(params, self.train_data)
                
                # 在驗證集上評估
                validation_score, validation_result = self._evaluate_params(params, self.validation_data)
                
                # 記錄結果
                result_entry = {
                    'params': params,
                    'train_score': train_score,
                    'validation_score': validation_score,
                    'train_trades': train_result.total_trades,
                    'validation_trades': validation_result.total_trades,
                }
                all_results.append(result_entry)
                
                # 更新最佳結果
                if validation_score > best_score:
                    best_score = validation_score
                    best_params = params
                    best_train_result = train_result
                    best_validation_result = validation_result
                
                if (i + 1) % 10 == 0:
                    logger.info(f"進度：{i + 1}/{n_iterations}，當前最佳評分：{best_score:.4f}")
            
            except Exception as e:
                logger.error(f"評估參數組合失敗：{params}，錯誤：{e}")
                continue
        
        # 計算參數敏感度
        param_names = list(param_distributions.keys())
        parameter_sensitivity = self._calculate_sensitivity(all_results, param_names)
        
        # 計算優化時間
        optimization_time = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"隨機搜索完成，最佳評分：{best_score:.4f}，耗時：{optimization_time:.2f}秒")
        
        return OptimizationResult(
            best_params=best_params or {},
            best_score=best_score,
            all_results=all_results,
            train_performance=best_train_result.to_dict() if best_train_result else {},
            validation_performance=best_validation_result.to_dict() if best_validation_result else {},
            parameter_sensitivity=parameter_sensitivity,
            optimization_time=optimization_time,
            method='random_search',
        )
    
    def bayesian_optimization(
        self,
        param_bounds: Dict[str, Tuple[float, float]],
        n_iterations: int = 50,
        n_initial_points: int = 10
    ) -> OptimizationResult:
        """貝葉斯優化
        
        使用高斯過程優化參數。
        
        Args:
            param_bounds: 參數邊界，格式：{'param_name': (min, max)}
            n_iterations: 迭代次數
            n_initial_points: 初始隨機點數量
        
        Returns:
            OptimizationResult: 優化結果
        """
        logger.info(f"開始貝葉斯優化，迭代次數：{n_iterations}")
        start_time = datetime.now()
        
        # 簡化版貝葉斯優化（不使用外部庫）
        # 實際應用中建議使用 scikit-optimize 或 optuna
        
        param_names = list(param_bounds.keys())
        all_results = []
        best_score = float('-inf')
        best_params = None
        best_train_result = None
        best_validation_result = None
        
        # 階段1：隨機初始化
        logger.info(f"階段1：隨機初始化 {n_initial_points} 個點")
        for i in range(n_initial_points):
            # 隨機採樣
            params = {
                name: np.random.uniform(bounds[0], bounds[1])
                for name, bounds in param_bounds.items()
            }
            
            try:
                train_score, train_result = self._evaluate_params(params, self.train_data)
                validation_score, validation_result = self._evaluate_params(params, self.validation_data)
                
                result_entry = {
                    'params': params,
                    'train_score': train_score,
                    'validation_score': validation_score,
                    'train_trades': train_result.total_trades,
                    'validation_trades': validation_result.total_trades,
                }
                all_results.append(result_entry)
                
                if validation_score > best_score:
                    best_score = validation_score
                    best_params = params
                    best_train_result = train_result
                    best_validation_result = validation_result
            
            except Exception as e:
                logger.error(f"評估參數組合失敗：{params}，錯誤：{e}")
                continue
        
        # 階段2：基於已有結果進行優化
        logger.info(f"階段2：優化搜索 {n_iterations - n_initial_points} 次")
        for i in range(n_initial_points, n_iterations):
            # 簡化策略：在最佳參數附近搜索
            if best_params:
                params = {}
                for name, bounds in param_bounds.items():
                    # 在最佳值附近添加噪聲
                    best_value = best_params[name]
                    noise_scale = (bounds[1] - bounds[0]) * 0.1  # 10% 的範圍
                    new_value = best_value + np.random.normal(0, noise_scale)
                    # 確保在邊界內
                    new_value = np.clip(new_value, bounds[0], bounds[1])
                    params[name] = new_value
            else:
                # 如果沒有最佳參數，隨機採樣
                params = {
                    name: np.random.uniform(bounds[0], bounds[1])
                    for name, bounds in param_bounds.items()
                }
            
            try:
                train_score, train_result = self._evaluate_params(params, self.train_data)
                validation_score, validation_result = self._evaluate_params(params, self.validation_data)
                
                result_entry = {
                    'params': params,
                    'train_score': train_score,
                    'validation_score': validation_score,
                    'train_trades': train_result.total_trades,
                    'validation_trades': validation_result.total_trades,
                }
                all_results.append(result_entry)
                
                if validation_score > best_score:
                    best_score = validation_score
                    best_params = params
                    best_train_result = train_result
                    best_validation_result = validation_result
                
                if (i + 1) % 10 == 0:
                    logger.info(f"進度：{i + 1}/{n_iterations}，當前最佳評分：{best_score:.4f}")
            
            except Exception as e:
                logger.error(f"評估參數組合失敗：{params}，錯誤：{e}")
                continue
        
        # 計算參數敏感度
        parameter_sensitivity = self._calculate_sensitivity(all_results, param_names)
        
        # 計算優化時間
        optimization_time = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"貝葉斯優化完成，最佳評分：{best_score:.4f}，耗時：{optimization_time:.2f}秒")
        
        return OptimizationResult(
            best_params=best_params or {},
            best_score=best_score,
            all_results=all_results,
            train_performance=best_train_result.to_dict() if best_train_result else {},
            validation_performance=best_validation_result.to_dict() if best_validation_result else {},
            parameter_sensitivity=parameter_sensitivity,
            optimization_time=optimization_time,
            method='bayesian_optimization',
        )
    
    def _calculate_sensitivity(
        self,
        all_results: List[Dict[str, Any]],
        param_names: List[str]
    ) -> Dict[str, List[Tuple[Any, float]]]:
        """計算參數敏感度
        
        Args:
            all_results: 所有結果
            param_names: 參數名稱列表
        
        Returns:
            Dict: 參數敏感度，格式：{'param_name': [(value, score), ...]}
        """
        sensitivity = {}
        
        for param_name in param_names:
            # 收集該參數的所有值和對應的評分
            param_scores = []
            for result in all_results:
                if 'params' in result and param_name in result['params']:
                    value = result['params'][param_name]
                    score = result.get('validation_score', 0.0)
                    param_scores.append((value, score))
            
            # 按值排序
            param_scores.sort(key=lambda x: x[0])
            sensitivity[param_name] = param_scores
        
        return sensitivity
    
    def generate_report(self, result: OptimizationResult) -> str:
        """生成優化報告
        
        Args:
            result: 優化結果
        
        Returns:
            str: 報告文本
        """
        report = []
        report.append("=" * 80)
        report.append("參數優化報告")
        report.append("=" * 80)
        report.append(f"優化方法：{result.method}")
        report.append(f"優化指標：{self.optimization_metric}")
        report.append(f"測試組合數：{len(result.all_results)}")
        report.append(f"優化時間：{result.optimization_time:.2f} 秒")
        report.append("")
        
        report.append("最佳參數：")
        report.append("-" * 80)
        for param, value in result.best_params.items():
            if isinstance(value, float):
                report.append(f"  {param}: {value:.4f}")
            else:
                report.append(f"  {param}: {value}")
        report.append("")
        
        report.append("訓練集性能：")
        report.append("-" * 80)
        train_perf = result.train_performance
        report.append(f"  總交易數：{train_perf.get('total_trades', 0)}")
        report.append(f"  勝率：{train_perf.get('win_rate', 0):.2%}")
        report.append(f"  總損益：{train_perf.get('total_pnl', 0):.2f} USDT")
        report.append(f"  獲利因子：{train_perf.get('profit_factor', 0):.2f}")
        report.append(f"  夏普比率：{train_perf.get('sharpe_ratio', 0):.2f}")
        report.append("")
        
        report.append("驗證集性能：")
        report.append("-" * 80)
        val_perf = result.validation_performance
        report.append(f"  總交易數：{val_perf.get('total_trades', 0)}")
        report.append(f"  勝率：{val_perf.get('win_rate', 0):.2%}")
        report.append(f"  總損益：{val_perf.get('total_pnl', 0):.2f} USDT")
        report.append(f"  獲利因子：{val_perf.get('profit_factor', 0):.2f}")
        report.append(f"  夏普比率：{val_perf.get('sharpe_ratio', 0):.2f}")
        report.append("")
        
        report.append("參數敏感度分析：")
        report.append("-" * 80)
        for param_name, scores in result.parameter_sensitivity.items():
            if scores:
                values = [s[0] for s in scores]
                score_values = [s[1] for s in scores]
                min_val = min(values)
                max_val = max(values)
                min_score = min(score_values)
                max_score = max(score_values)
                score_range = max_score - min_score
                
                report.append(f"  {param_name}:")
                report.append(f"    範圍：{min_val:.4f} - {max_val:.4f}")
                report.append(f"    評分範圍：{min_score:.4f} - {max_score:.4f}")
                report.append(f"    敏感度：{score_range:.4f}")
        
        report.append("=" * 80)
        
        return "\n".join(report)
