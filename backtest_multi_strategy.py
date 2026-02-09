#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多策略組合回測腳本

同時回測多個策略，驗證策略隔離和資金分配。
"""

import pandas as pd
from datetime import datetime
from pathlib import Path
import json

from src.strategies.multi_timeframe_strategy import MultiTimeframeStrategy
from src.strategies.breakout_strategy import BreakoutStrategy
from src.execution.backtest_engine import BacktestEngine
from src.models.config import StrategyConfig


def load_market_data(symbol: str, timeframes: list) -> dict:
    """載入市場數據"""
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
    print("多策略組合回測")
    print("=" * 80)
    
    # 載入策略配置
    strategies_config = [
        {
            "file": "strategies/multi-timeframe-aggressive.json",
            "class": MultiTimeframeStrategy,
            "name": "多週期共振策略"
        },
        {
            "file": "strategies/breakout-strategy.json",
            "class": BreakoutStrategy,
            "name": "突破策略"
        }
    ]
    
    strategies = []
    all_timeframes = set()
    
    for config_info in strategies_config:
        print(f"\n載入策略配置：{config_info['file']}")
        
        with open(config_info['file'], 'r') as f:
            config_dict = json.load(f)
        
        config = StrategyConfig.from_dict(config_dict)
        strategy = config_info['class'](config)
        strategies.append(strategy)
        
        # 收集所有需要的週期
        all_timeframes.update(config.timeframes)
        
        print(f"✅ {config_info['name']} 載入成功")
        print(f"   策略 ID：{config.strategy_id}")
        print(f"   週期：{', '.join(config.timeframes)}")
        print(f"   倉位：{config.risk_management.position_size * 100}%")
        print(f"   槓桿：{config.risk_management.leverage}x")
    
    # 載入市場數據
    print(f"\n載入市場數據...")
    symbol = strategies[0].config.symbol
    market_data = load_market_data(symbol, sorted(all_timeframes))
    
    if not market_data:
        print("❌ 沒有可用的市場數據")
        return
    
    # 創建回測引擎
    initial_capital = 1000.0
    commission = 0.0005
    
    print(f"\n創建回測引擎...")
    print(f"初始資金：{initial_capital} USDT")
    print(f"手續費率：{commission * 100}%")
    
    engine = BacktestEngine(initial_capital, commission)
    
    # 定義資金分配（可選）
    capital_allocation = {
        "multi-timeframe-aggressive": 0.5,  # 50%
        "breakout-strategy": 0.5,  # 50%
    }
    
    print(f"\n資金分配：")
    for strategy_id, allocation in capital_allocation.items():
        print(f"  {strategy_id}: {allocation * 100}%")
    
    # 運行多策略回測
    print(f"\n開始多策略回測...")
    print("-" * 80)
    
    results_dict = engine.run_multi_strategy(
        strategies,
        market_data,
        capital_allocation=capital_allocation
    )
    
    # 計算整體結果
    strategy_results = list(results_dict.values())
    
    # 合併所有交易
    all_trades = []
    for result in strategy_results:
        all_trades.extend(result.trades)
    all_trades.sort(key=lambda t: t.entry_time)
    
    # 計算整體指標
    total_initial_capital = sum(r.initial_capital for r in strategy_results)
    total_final_capital = sum(r.final_capital for r in strategy_results)
    total_pnl = total_final_capital - total_initial_capital
    total_pnl_pct = total_pnl / total_initial_capital if total_initial_capital > 0 else 0
    
    total_trades_count = sum(r.total_trades for r in strategy_results)
    winning_trades = sum(r.winning_trades for r in strategy_results)
    losing_trades = sum(r.losing_trades for r in strategy_results)
    win_rate = winning_trades / total_trades_count if total_trades_count > 0 else 0
    
    # 計算整體獲利因子
    total_wins = sum(t.pnl for t in all_trades if t.pnl > 0)
    total_losses = abs(sum(t.pnl for t in all_trades if t.pnl < 0))
    profit_factor = total_wins / total_losses if total_losses > 0 else 0
    
    # 計算整體最大回撤
    equity_curve = [total_initial_capital]
    for trade in all_trades:
        equity_curve.append(equity_curve[-1] + trade.pnl)
    
    peak = equity_curve[0]
    max_drawdown = 0
    for equity in equity_curve:
        if equity > peak:
            peak = equity
        drawdown = peak - equity
        if drawdown > max_drawdown:
            max_drawdown = drawdown
    
    max_drawdown_pct = max_drawdown / peak if peak > 0 else 0
    
    # 獲取日期範圍
    start_date = min(r.start_date for r in strategy_results)
    end_date = max(r.end_date for r in strategy_results)
    
    # 顯示結果
    print("\n" + "=" * 80)
    print("多策略回測結果")
    print("=" * 80)
    
    print(f"\n📊 基本信息")
    print(f"開始日期：{start_date}")
    print(f"結束日期：{end_date}")
    print(f"回測天數：{(end_date - start_date).days} 天")
    print(f"策略數量：{len(strategy_results)}")
    
    print(f"\n💰 整體資金情況")
    print(f"初始資金：{total_initial_capital:.2f} USDT")
    print(f"最終資金：{total_final_capital:.2f} USDT")
    print(f"淨損益：{total_pnl:.2f} USDT ({total_pnl_pct:.2%})")
    
    print(f"\n📈 整體交易統計")
    print(f"總交易數：{total_trades_count}")
    print(f"獲利交易：{winning_trades}")
    print(f"虧損交易：{losing_trades}")
    print(f"勝率：{win_rate:.2%}")
    
    if total_trades_count > 0:
        avg_win = total_wins / winning_trades if winning_trades > 0 else 0
        avg_loss = total_losses / losing_trades if losing_trades > 0 else 0
        
        print(f"\n💵 整體損益分析")
        print(f"平均獲利：{avg_win:.2f} USDT")
        print(f"平均虧損：{avg_loss:.2f} USDT")
        print(f"獲利因子：{profit_factor:.2f}")
        
        print(f"\n⚠️ 整體風險指標")
        print(f"最大回撤：{max_drawdown:.2f} USDT ({max_drawdown_pct:.2%})")
    
    # 顯示各策略詳情
    print(f"\n" + "=" * 80)
    print("各策略詳細結果")
    print("=" * 80)
    
    for strategy_id, strategy_result in results_dict.items():
        print(f"\n📌 策略：{strategy_id}")
        print(f"   初始資金：{strategy_result.initial_capital:.2f} USDT")
        print(f"   最終資金：{strategy_result.final_capital:.2f} USDT")
        print(f"   淨損益：{strategy_result.total_pnl:.2f} USDT ({strategy_result.total_pnl_pct:.2%})")
        print(f"   交易數：{strategy_result.total_trades}")
        print(f"   勝率：{strategy_result.win_rate:.2%}")
        
        if strategy_result.total_trades > 0:
            print(f"   獲利因子：{strategy_result.profit_factor:.2f}")
            print(f"   最大回撤：{strategy_result.max_drawdown:.2f} USDT ({strategy_result.max_drawdown_pct:.2%})")
    
    # 保存結果
    output_file = f"backtest_result_multi_strategy_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    # 保存各策略結果
    for strategy_id, result in results_dict.items():
        result.save(f"{output_file.replace('.json', '')}_{strategy_id}.json")
    print(f"\n✅ 結果已保存")
    
    # 顯示交易明細
    if all_trades and len(all_trades) > 0:
        print(f"\n📋 交易明細（最近 10 筆）")
        print("-" * 80)
        
        for trade in all_trades[-10:]:
            direction_emoji = "📈" if trade.direction == 'long' else "📉"
            pnl_emoji = "✅" if trade.pnl > 0 else "❌"
            
            print(f"{direction_emoji} [{trade.strategy_id}] "
                  f"{trade.entry_time.strftime('%Y-%m-%d %H:%M')} | "
                  f"進場: ${trade.entry_price:.2f} | "
                  f"出場: ${trade.exit_price:.2f} | "
                  f"{pnl_emoji} {trade.pnl:.2f} USDT ({trade.pnl_pct:.2%}) | "
                  f"{trade.exit_reason}")
    
    print("\n" + "=" * 80)
    
    # 驗證策略隔離
    print("\n🔍 驗證策略隔離")
    print("-" * 80)
    
    total_allocated = sum(capital_allocation.values())
    print(f"資金分配總和：{total_allocated * 100}%")
    
    strategy_pnl_sum = sum(r.total_pnl for r in strategy_results)
    print(f"各策略損益總和：{strategy_pnl_sum:.2f} USDT")
    print(f"整體損益：{total_pnl:.2f} USDT")
    print(f"差異：{abs(strategy_pnl_sum - total_pnl):.2f} USDT")
    
    if abs(strategy_pnl_sum - total_pnl) < 1.0:
        print("✅ 策略隔離驗證通過")
    else:
        print("⚠️ 策略隔離可能存在問題")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
