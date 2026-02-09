#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多週期共振策略回測腳本

使用新架構回測多週期共振策略。
"""

import pandas as pd
from datetime import datetime
from pathlib import Path

from src.strategies.multi_timeframe_strategy import MultiTimeframeStrategy
from src.execution.backtest_engine import BacktestEngine
from src.models.config import StrategyConfig
import json


def load_market_data(symbol: str) -> dict:
    """載入市場數據"""
    timeframes = ['1d', '4h', '1h', '15m']
    data = {}
    
    for tf in timeframes:
        filename = f"market_data_{symbol}_{tf}.csv"
        if Path(filename).exists():
            df = pd.read_csv(filename)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            data[tf] = df
            print(f"✅ 載入 {tf} 數據：{len(df)} 條")
        else:
            print(f"⚠️ 找不到 {tf} 數據文件：{filename}")
    
    return data


def main():
    """主函數"""
    print("=" * 80)
    print("多週期共振策略回測")
    print("=" * 80)
    
    # 載入策略配置
    config_file = "strategies/multi-timeframe-aggressive.json"
    print(f"\n載入策略配置：{config_file}")
    
    with open(config_file, 'r') as f:
        config_dict = json.load(f)
    
    config = StrategyConfig.from_dict(config_dict)
    print(f"策略：{config.strategy_name}")
    print(f"版本：{config.version}")
    print(f"標的：{config.symbol}")
    print(f"週期：{', '.join(config.timeframes)}")
    
    # 創建策略實例
    strategy = MultiTimeframeStrategy(config)
    print(f"\n✅ 策略實例創建成功")
    print(f"止損：{strategy.stop_loss_atr} ATR")
    print(f"目標：{strategy.take_profit_atr} ATR")
    
    # 載入市場數據
    print(f"\n載入市場數據...")
    market_data = load_market_data(config.symbol)
    
    if not market_data:
        print("❌ 沒有可用的市場數據")
        return
    
    # 檢查數據完整性
    required_timeframes = set(config.timeframes)
    available_timeframes = set(market_data.keys())
    
    if not required_timeframes.issubset(available_timeframes):
        missing = required_timeframes - available_timeframes
        print(f"❌ 缺少必需的週期數據：{missing}")
        return
    
    # 創建回測引擎
    initial_capital = 1000.0
    commission = 0.0005
    
    print(f"\n創建回測引擎...")
    print(f"初始資金：{initial_capital} USDT")
    print(f"手續費率：{commission * 100}%")
    
    engine = BacktestEngine(initial_capital, commission)
    
    # 運行回測
    print(f"\n開始回測...")
    print("-" * 80)
    
    result = engine.run_single_strategy(strategy, market_data)
    
    # 顯示結果
    print("\n" + "=" * 80)
    print("回測結果")
    print("=" * 80)
    
    print(f"\n📊 基本信息")
    print(f"策略 ID：{result.strategy_id}")
    print(f"開始日期：{result.start_date}")
    print(f"結束日期：{result.end_date}")
    print(f"回測天數：{(result.end_date - result.start_date).days} 天")
    
    print(f"\n💰 資金情況")
    print(f"初始資金：{result.initial_capital:.2f} USDT")
    print(f"最終資金：{result.final_capital:.2f} USDT")
    print(f"淨損益：{result.total_pnl:.2f} USDT ({result.total_pnl_pct:.2f}%)")
    
    print(f"\n📈 交易統計")
    print(f"總交易數：{result.total_trades}")
    print(f"獲利交易：{result.winning_trades}")
    print(f"虧損交易：{result.losing_trades}")
    print(f"勝率：{result.win_rate:.2f}%")
    
    if result.total_trades > 0:
        print(f"\n💵 損益分析")
        print(f"平均獲利：{result.avg_win:.2f} USDT")
        print(f"平均虧損：{result.avg_loss:.2f} USDT")
        print(f"獲利因子：{result.profit_factor:.2f}")
        
        print(f"\n⚠️ 風險指標")
        print(f"最大回撤：{result.max_drawdown:.2f} USDT ({result.max_drawdown_pct:.2f}%)")
        print(f"夏普比率：{result.sharpe_ratio:.2f}")
    
    # 保存結果
    output_file = f"backtest_result_{config.strategy_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    result.save(output_file)
    print(f"\n✅ 結果已保存到：{output_file}")
    
    # 顯示交易明細
    if result.trades and len(result.trades) > 0:
        print(f"\n📋 交易明細（最近 10 筆）")
        print("-" * 80)
        
        for trade in result.trades[-10:]:
            direction_emoji = "📈" if trade.direction == 'long' else "📉"
            pnl_emoji = "✅" if trade.pnl > 0 else "❌"
            
            print(f"{direction_emoji} {trade.entry_time.strftime('%Y-%m-%d %H:%M')} | "
                  f"進場: ${trade.entry_price:.2f} | "
                  f"出場: ${trade.exit_price:.2f} | "
                  f"{pnl_emoji} {trade.pnl:.2f} USDT ({trade.pnl_pct:.2f}%) | "
                  f"{trade.exit_reason}")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
