"""
參數優化器示例

展示如何使用 Optimizer 進行策略參數優化。
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json

from src.analysis.optimizer import Optimizer
from src.strategies.multi_timeframe_strategy import MultiTimeframeStrategy


def load_market_data():
    """載入市場數據"""
    print("載入市場數據...")
    
    # 嘗試載入真實數據
    try:
        data_1h = pd.read_csv('market_data_ETHUSDT_1h.csv')
        data_1h['timestamp'] = pd.to_datetime(data_1h['timestamp'])
        
        data_4h = pd.read_csv('market_data_ETHUSDT_4h.csv')
        data_4h['timestamp'] = pd.to_datetime(data_4h['timestamp'])
        
        data_1d = pd.read_csv('market_data_ETHUSDT_1d.csv')
        data_1d['timestamp'] = pd.to_datetime(data_1d['timestamp'])
        
        data_15m = pd.read_csv('market_data_ETHUSDT_15m.csv')
        data_15m['timestamp'] = pd.to_datetime(data_15m['timestamp'])
        
        market_data = {
            '15m': data_15m,
            '1h': data_1h,
            '4h': data_4h,
            '1d': data_1d,
        }
        
        print(f"成功載入市場數據：")
        for timeframe, df in market_data.items():
            print(f"  {timeframe}: {len(df)} 條數據")
        
        return market_data
    
    except FileNotFoundError:
        print("未找到市場數據文件，使用模擬數據...")
        return generate_synthetic_data()


def generate_synthetic_data():
    """生成模擬市場數據"""
    n_candles = 1000
    timestamps = [datetime.now() - timedelta(hours=i) for i in range(n_candles, 0, -1)]
    
    # 生成隨機價格走勢
    base_price = 2000.0
    prices = [base_price]
    
    for _ in range(n_candles - 1):
        change = np.random.normal(0, 0.02)  # 2% 標準差
        new_price = prices[-1] * (1 + change)
        prices.append(new_price)
    
    data = {
        'timestamp': timestamps,
        'open': prices,
        'high': [p * 1.01 for p in prices],
        'low': [p * 0.99 for p in prices],
        'close': prices,
        'volume': [np.random.uniform(1000, 10000) for _ in range(n_candles)],
    }
    
    df = pd.DataFrame(data)
    
    # 為不同週期創建相同的數據（簡化版本）
    return {
        '15m': df.copy(),
        '1h': df.copy(),
        '4h': df.copy(),
        '1d': df.copy(),
    }


def create_base_config():
    """創建基礎策略配置"""
    return {
        'strategy_id': 'multi-timeframe-v1',
        'strategy_name': '多週期共振策略',
        'version': '1.0.0',
        'enabled': True,
        'symbol': 'ETHUSDT',
        'timeframes': ['1d', '4h', '1h', '15m'],
        'parameters': {
            'stop_loss_atr': 1.5,
            'take_profit_atr': 3.0,
            'rsi_range': [30, 70],
            'ema_distance': 0.03,
            'volume_threshold': 1.0,
        },
        'risk_management': {
            'position_size': 0.20,
            'leverage': 5,
            'max_trades_per_day': 3,
            'max_consecutive_losses': 3,
            'daily_loss_limit': 0.10,
        },
        'entry_conditions': [],
        'exit_conditions': {},
        'notifications': {},
    }


def example_grid_search():
    """示例：網格搜索"""
    print("\n" + "=" * 80)
    print("示例 1：網格搜索")
    print("=" * 80)
    
    # 載入數據
    market_data = load_market_data()
    base_config = create_base_config()
    
    # 創建優化器
    optimizer = Optimizer(
        strategy_class=MultiTimeframeStrategy,
        base_config=base_config,
        market_data=market_data,
        initial_capital=1000.0,
        train_ratio=0.7,
        optimization_metric='sharpe_ratio',
    )
    
    # 定義參數網格
    param_grid = {
        'parameters.stop_loss_atr': [1.0, 1.5, 2.0],
        'parameters.take_profit_atr': [2.0, 3.0, 4.0],
    }
    
    print(f"\n參數網格：")
    for param, values in param_grid.items():
        print(f"  {param}: {values}")
    
    # 執行網格搜索
    print(f"\n開始網格搜索...")
    result = optimizer.grid_search(param_grid, max_combinations=9)
    
    # 顯示結果
    print(f"\n網格搜索完成！")
    print(f"測試組合數：{len(result.all_results)}")
    print(f"最佳評分：{result.best_score:.4f}")
    print(f"最佳參數：")
    for param, value in result.best_params.items():
        print(f"  {param}: {value:.4f}")
    
    # 生成報告
    report = optimizer.generate_report(result)
    print(f"\n{report}")
    
    return result


def example_random_search():
    """示例：隨機搜索"""
    print("\n" + "=" * 80)
    print("示例 2：隨機搜索")
    print("=" * 80)
    
    # 載入數據
    market_data = load_market_data()
    base_config = create_base_config()
    
    # 創建優化器
    optimizer = Optimizer(
        strategy_class=MultiTimeframeStrategy,
        base_config=base_config,
        market_data=market_data,
        initial_capital=1000.0,
        train_ratio=0.7,
        optimization_metric='profit_factor',
    )
    
    # 定義參數分佈
    param_distributions = {
        'parameters.stop_loss_atr': lambda: np.random.uniform(0.5, 3.0),
        'parameters.take_profit_atr': lambda: np.random.uniform(1.0, 5.0),
        'risk_management.position_size': lambda: np.random.uniform(0.1, 0.3),
    }
    
    print(f"\n參數分佈：")
    for param in param_distributions.keys():
        print(f"  {param}")
    
    # 執行隨機搜索
    print(f"\n開始隨機搜索（20 次迭代）...")
    result = optimizer.random_search(param_distributions, n_iterations=20)
    
    # 顯示結果
    print(f"\n隨機搜索完成！")
    print(f"測試組合數：{len(result.all_results)}")
    print(f"最佳評分：{result.best_score:.4f}")
    print(f"最佳參數：")
    for param, value in result.best_params.items():
        print(f"  {param}: {value:.4f}")
    
    # 生成報告
    report = optimizer.generate_report(result)
    print(f"\n{report}")
    
    return result


def example_bayesian_optimization():
    """示例：貝葉斯優化"""
    print("\n" + "=" * 80)
    print("示例 3：貝葉斯優化")
    print("=" * 80)
    
    # 載入數據
    market_data = load_market_data()
    base_config = create_base_config()
    
    # 創建優化器
    optimizer = Optimizer(
        strategy_class=MultiTimeframeStrategy,
        base_config=base_config,
        market_data=market_data,
        initial_capital=1000.0,
        train_ratio=0.7,
        optimization_metric='sharpe_ratio',
    )
    
    # 定義參數邊界
    param_bounds = {
        'parameters.stop_loss_atr': (0.5, 3.0),
        'parameters.take_profit_atr': (1.0, 5.0),
    }
    
    print(f"\n參數邊界：")
    for param, bounds in param_bounds.items():
        print(f"  {param}: {bounds}")
    
    # 執行貝葉斯優化
    print(f"\n開始貝葉斯優化（15 次迭代）...")
    result = optimizer.bayesian_optimization(
        param_bounds,
        n_iterations=15,
        n_initial_points=5
    )
    
    # 顯示結果
    print(f"\n貝葉斯優化完成！")
    print(f"測試組合數：{len(result.all_results)}")
    print(f"最佳評分：{result.best_score:.4f}")
    print(f"最佳參數：")
    for param, value in result.best_params.items():
        print(f"  {param}: {value:.4f}")
    
    # 生成報告
    report = optimizer.generate_report(result)
    print(f"\n{report}")
    
    return result


def save_optimization_result(result, filename):
    """保存優化結果"""
    result_dict = result.to_dict()
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(result_dict, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"\n優化結果已保存到：{filename}")


def main():
    """主函數"""
    print("=" * 80)
    print("參數優化器示例")
    print("=" * 80)
    
    # 示例 1：網格搜索
    try:
        result1 = example_grid_search()
        save_optimization_result(result1, 'optimization_result_grid_search.json')
    except Exception as e:
        print(f"\n網格搜索失敗：{e}")
    
    # 示例 2：隨機搜索
    try:
        result2 = example_random_search()
        save_optimization_result(result2, 'optimization_result_random_search.json')
    except Exception as e:
        print(f"\n隨機搜索失敗：{e}")
    
    # 示例 3：貝葉斯優化
    try:
        result3 = example_bayesian_optimization()
        save_optimization_result(result3, 'optimization_result_bayesian.json')
    except Exception as e:
        print(f"\n貝葉斯優化失敗：{e}")
    
    print("\n" + "=" * 80)
    print("所有示例完成！")
    print("=" * 80)


if __name__ == '__main__':
    main()
