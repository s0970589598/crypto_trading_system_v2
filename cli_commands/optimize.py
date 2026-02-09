"""
參數優化命令實現
"""

import pandas as pd
import logging
import random
from pathlib import Path
from typing import Dict, List

from src.analysis.optimizer import Optimizer
from src.models.config import StrategyConfig
from src.strategies.multi_timeframe_strategy import MultiTimeframeStrategy
from src.strategies.breakout_strategy import BreakoutStrategy


logger = logging.getLogger(__name__)


def load_market_data(symbol: str, timeframes: List[str]) -> Dict[str, pd.DataFrame]:
    """
    載入市場數據
    
    Args:
        symbol: 交易對
        timeframes: 時間週期列表
    
    Returns:
        Dict[str, pd.DataFrame]: 週期 -> 數據
    """
    market_data = {}
    
    for timeframe in timeframes:
        filename = f"market_data_{symbol}_{timeframe}.csv"
        
        if not Path(filename).exists():
            logger.warning(f"數據文件不存在：{filename}")
            continue
        
        try:
            df = pd.read_csv(filename)
            
            # 轉換時間戳
            if df['timestamp'].dtype == 'object':
                df['timestamp'] = pd.to_datetime(df['timestamp'])
            elif df['timestamp'].dtype in ['int64', 'float64']:
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            df = df.sort_values('timestamp').reset_index(drop=True)
            
            market_data[timeframe] = df
            logger.info(f"載入數據：{filename}，{len(df)} 條記錄")
        
        except Exception as e:
            logger.error(f"載入數據文件 {filename} 失敗：{e}")
            continue
    
    return market_data


def get_strategy_class(strategy_id: str):
    """
    根據策略 ID 獲取策略類
    
    Args:
        strategy_id: 策略 ID
    
    Returns:
        type: 策略類
    """
    if 'multi-timeframe' in strategy_id.lower() or 'multi_timeframe' in strategy_id.lower():
        return MultiTimeframeStrategy
    elif 'breakout' in strategy_id.lower():
        return BreakoutStrategy
    else:
        logger.warning(f"無法推斷策略類型，使用默認的 MultiTimeframeStrategy")
        return MultiTimeframeStrategy


def run_optimize(args):
    """
    執行參數優化命令
    
    Args:
        args: 命令行參數
    """
    logger.info("開始參數優化")
    
    strategy_id = args.strategy
    
    # 載入策略配置
    config_file = Path(f"strategies/{strategy_id}.json")
    
    if not config_file.exists():
        logger.error(f"策略配置文件不存在：{config_file}")
        return
    
    config = StrategyConfig.from_json(str(config_file))
    
    # 獲取策略類
    strategy_class = get_strategy_class(strategy_id)
    
    # 載入市場數據
    market_data = load_market_data(config.symbol, config.timeframes)
    
    if not market_data:
        logger.error("無法載入市場數據")
        return
    
    # 創建優化器
    optimizer = Optimizer(
        strategy_class=strategy_class,
        base_config=config.to_dict(),
        market_data=market_data,
        initial_capital=1000.0,
        commission=0.0005,
        train_ratio=0.7,
        optimization_metric=args.metric
    )
    
    logger.info(f"優化方法：{args.method}")
    logger.info(f"優化指標：{args.metric}")
    
    # 根據方法執行優化
    if args.method == 'grid':
        # 定義參數網格
        param_grid = {
            'parameters.stop_loss_atr': [1.0, 1.5, 2.0, 2.5],
            'parameters.take_profit_atr': [2.0, 3.0, 4.0, 5.0],
            'risk_management.position_size': [0.10, 0.15, 0.20, 0.25],
            'risk_management.leverage': [3, 5, 7, 10],
        }
        
        # 如果是多週期策略，添加額外參數
        if strategy_class == MultiTimeframeStrategy:
            param_grid['parameters.ema_distance'] = [0.02, 0.03, 0.04, 0.05]
            param_grid['parameters.volume_threshold'] = [0.8, 1.0, 1.2, 1.5]
        
        # 如果是突破策略，添加額外參數
        elif strategy_class == BreakoutStrategy:
            param_grid['parameters.lookback_period'] = [15, 20, 25, 30]
            param_grid['parameters.volume_threshold'] = [1.2, 1.5, 1.8, 2.0]
        
        logger.info(f"參數網格：{param_grid}")
        
        result = optimizer.grid_search(
            param_grid=param_grid,
            max_combinations=200  # 限制最大組合數
        )
    
    elif args.method == 'random':
        # 定義參數分佈
        param_distributions = {
            'parameters.stop_loss_atr': lambda: random.uniform(0.5, 3.0),
            'parameters.take_profit_atr': lambda: random.uniform(1.5, 6.0),
            'risk_management.position_size': lambda: random.uniform(0.05, 0.30),
            'risk_management.leverage': lambda: random.randint(2, 15),
        }
        
        # 如果是多週期策略，添加額外參數
        if strategy_class == MultiTimeframeStrategy:
            param_distributions['parameters.ema_distance'] = lambda: random.uniform(0.01, 0.06)
            param_distributions['parameters.volume_threshold'] = lambda: random.uniform(0.5, 2.0)
        
        # 如果是突破策略，添加額外參數
        elif strategy_class == BreakoutStrategy:
            param_distributions['parameters.lookback_period'] = lambda: random.randint(10, 40)
            param_distributions['parameters.volume_threshold'] = lambda: random.uniform(1.0, 2.5)
        
        result = optimizer.random_search(
            param_distributions=param_distributions,
            n_iterations=args.iterations
        )
    
    elif args.method == 'bayesian':
        # 定義參數邊界
        param_bounds = {
            'parameters.stop_loss_atr': (0.5, 3.0),
            'parameters.take_profit_atr': (1.5, 6.0),
            'risk_management.position_size': (0.05, 0.30),
            'risk_management.leverage': (2, 15),
        }
        
        # 如果是多週期策略，添加額外參數
        if strategy_class == MultiTimeframeStrategy:
            param_bounds['parameters.ema_distance'] = (0.01, 0.06)
            param_bounds['parameters.volume_threshold'] = (0.5, 2.0)
        
        # 如果是突破策略，添加額外參數
        elif strategy_class == BreakoutStrategy:
            param_bounds['parameters.lookback_period'] = (10, 40)
            param_bounds['parameters.volume_threshold'] = (1.0, 2.5)
        
        result = optimizer.bayesian_optimization(
            param_bounds=param_bounds,
            n_iterations=args.iterations,
            n_initial_points=min(10, args.iterations // 5)
        )
    
    else:
        logger.error(f"未知的優化方法：{args.method}")
        return
    
    # 生成報告
    report = optimizer.generate_report(result)
    
    # 打印報告
    print("\n" + report)
    
    # 保存報告
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)
            f.write("\n\n")
            
            # 添加詳細結果
            f.write("=" * 80 + "\n")
            f.write("詳細結果\n")
            f.write("=" * 80 + "\n\n")
            
            import json
            json.dump(result.to_dict(), f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"優化報告已保存到：{output_path}")
    
    # 打印最佳參數的建議配置
    print("\n" + "=" * 80)
    print("建議配置")
    print("=" * 80)
    print("\n將以下參數更新到策略配置文件中：\n")
    
    import json
    print(json.dumps(result.best_params, indent=2, ensure_ascii=False))
    
    print("\n" + "=" * 80)
    
    logger.info("參數優化完成")
