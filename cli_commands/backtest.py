"""
回測命令實現
"""

import pandas as pd
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from src.execution.backtest_engine import BacktestEngine
from src.models.config import StrategyConfig
from src.strategies.multi_timeframe_strategy import MultiTimeframeStrategy
from src.strategies.breakout_strategy import BreakoutStrategy


logger = logging.getLogger(__name__)


# 策略類映射
STRATEGY_CLASSES = {
    'MultiTimeframeStrategy': MultiTimeframeStrategy,
    'BreakoutStrategy': BreakoutStrategy,
}


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
        # 嘗試載入數據文件
        filename = f"market_data_{symbol}_{timeframe}.csv"
        
        if not Path(filename).exists():
            logger.warning(f"數據文件不存在：{filename}")
            continue
        
        try:
            df = pd.read_csv(filename)
            
            # 確保有必需的列
            required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
            if not all(col in df.columns for col in required_columns):
                logger.error(f"數據文件 {filename} 缺少必需的列")
                continue
            
            # 轉換時間戳
            if df['timestamp'].dtype == 'object':
                df['timestamp'] = pd.to_datetime(df['timestamp'])
            elif df['timestamp'].dtype in ['int64', 'float64']:
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # 排序
            df = df.sort_values('timestamp').reset_index(drop=True)
            
            market_data[timeframe] = df
            logger.info(f"載入數據：{filename}，{len(df)} 條記錄")
        
        except Exception as e:
            logger.error(f"載入數據文件 {filename} 失敗：{e}")
            continue
    
    return market_data


def load_strategy(strategy_id: str):
    """
    載入策略
    
    Args:
        strategy_id: 策略 ID
    
    Returns:
        Strategy: 策略實例
    """
    # 查找配置文件
    config_file = Path(f"strategies/{strategy_id}.json")
    
    if not config_file.exists():
        raise FileNotFoundError(f"策略配置文件不存在：{config_file}")
    
    # 載入配置
    config = StrategyConfig.from_json(str(config_file))
    
    # 根據策略 ID 推斷策略類
    # 這裡使用簡單的命名約定
    if 'multi-timeframe' in strategy_id.lower() or 'multi_timeframe' in strategy_id.lower():
        strategy_class = MultiTimeframeStrategy
    elif 'breakout' in strategy_id.lower():
        strategy_class = BreakoutStrategy
    else:
        # 默認使用 MultiTimeframeStrategy
        logger.warning(f"無法推斷策略類型，使用默認的 MultiTimeframeStrategy")
        strategy_class = MultiTimeframeStrategy
    
    # 創建策略實例
    strategy = strategy_class(config)
    
    logger.info(f"載入策略：{strategy_id} ({strategy_class.__name__})")
    
    return strategy


def print_backtest_result(result, strategy_id: str):
    """
    打印回測結果
    
    Args:
        result: 回測結果
        strategy_id: 策略 ID
    """
    print("\n" + "=" * 80)
    print(f"回測結果：{strategy_id}")
    print("=" * 80)
    
    print(f"\n時間範圍：{result.start_date} 至 {result.end_date}")
    print(f"初始資金：{result.initial_capital:.2f} USDT")
    print(f"最終資金：{result.final_capital:.2f} USDT")
    print(f"總損益：{result.total_pnl:.2f} USDT ({result.total_pnl_pct:.2%})")
    
    print(f"\n交易統計：")
    print(f"  總交易數：{result.total_trades}")
    print(f"  獲利交易：{result.winning_trades}")
    print(f"  虧損交易：{result.losing_trades}")
    print(f"  勝率：{result.win_rate:.2%}")
    
    print(f"\n損益統計：")
    print(f"  平均獲利：{result.avg_win:.2f} USDT")
    print(f"  平均虧損：{result.avg_loss:.2f} USDT")
    print(f"  獲利因子：{result.profit_factor:.2f}")
    
    print(f"\n風險指標：")
    print(f"  最大回撤：{result.max_drawdown:.2f} USDT ({result.max_drawdown_pct:.2%})")
    print(f"  夏普比率：{result.sharpe_ratio:.2f}")
    
    print("=" * 80)


def run_backtest(args):
    """
    執行回測命令
    
    Args:
        args: 命令行參數
    """
    logger.info("開始回測")
    
    # 解析日期
    start_date = None
    end_date = None
    
    if args.start:
        try:
            start_date = datetime.strptime(args.start, '%Y-%m-%d')
        except ValueError:
            logger.error(f"無效的開始日期格式：{args.start}，應為 YYYY-MM-DD")
            return
    
    if args.end:
        try:
            end_date = datetime.strptime(args.end, '%Y-%m-%d')
        except ValueError:
            logger.error(f"無效的結束日期格式：{args.end}，應為 YYYY-MM-DD")
            return
    
    # 載入策略
    strategies = []
    all_timeframes = set()
    symbols = set()
    
    for strategy_id in args.strategy:
        try:
            strategy = load_strategy(strategy_id)
            strategies.append(strategy)
            
            # 收集所有需要的時間週期和交易對
            all_timeframes.update(strategy.config.timeframes)
            symbols.add(strategy.config.symbol)
        
        except Exception as e:
            logger.error(f"載入策略 {strategy_id} 失敗：{e}")
            continue
    
    if not strategies:
        logger.error("沒有成功載入任何策略")
        return
    
    # 檢查是否所有策略使用相同的交易對
    if len(symbols) > 1:
        logger.warning(f"策略使用了不同的交易對：{symbols}，將分別載入數據")
    
    # 載入市場數據
    all_market_data = {}
    
    for symbol in symbols:
        market_data = load_market_data(symbol, list(all_timeframes))
        
        if not market_data:
            logger.error(f"無法載入 {symbol} 的市場數據")
            return
        
        all_market_data[symbol] = market_data
    
    # 創建回測引擎
    engine = BacktestEngine(
        initial_capital=args.capital,
        commission=args.commission
    )
    
    # 執行回測
    results = {}
    
    if len(strategies) == 1:
        # 單策略回測
        strategy = strategies[0]
        symbol = strategy.config.symbol
        market_data = all_market_data[symbol]
        
        logger.info(f"回測策略：{strategy.get_id()}")
        
        result = engine.run_single_strategy(
            strategy,
            market_data,
            start_date,
            end_date
        )
        
        results[strategy.get_id()] = result
        
        # 打印結果
        print_backtest_result(result, strategy.get_id())
    
    else:
        # 多策略回測
        logger.info(f"回測 {len(strategies)} 個策略")
        
        # 平均分配資金
        capital_allocation = {
            strategy.get_id(): 1.0 / len(strategies)
            for strategy in strategies
        }
        
        # 假設所有策略使用相同的交易對（取第一個）
        symbol = list(symbols)[0]
        market_data = all_market_data[symbol]
        
        results = engine.run_multi_strategy(
            strategies,
            market_data,
            capital_allocation,
            start_date,
            end_date
        )
        
        # 打印每個策略的結果
        for strategy_id, result in results.items():
            print_backtest_result(result, strategy_id)
        
        # 打印組合統計
        print("\n" + "=" * 80)
        print("多策略組合統計")
        print("=" * 80)
        
        total_pnl = sum(r.total_pnl for r in results.values())
        total_trades = sum(r.total_trades for r in results.values())
        
        print(f"\n總損益：{total_pnl:.2f} USDT ({total_pnl / args.capital:.2%})")
        print(f"總交易數：{total_trades}")
        print(f"策略數量：{len(results)}")
        
        print("=" * 80)
    
    # 保存結果
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 保存為 JSON
        output_data = {}
        for strategy_id, result in results.items():
            output_data[strategy_id] = result.to_dict()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"回測結果已保存到：{output_path}")
    
    logger.info("回測完成")
