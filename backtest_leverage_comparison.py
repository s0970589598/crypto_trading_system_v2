#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新架構槓桿對比回測

對比不同槓桿在新架構（20% 倉位）下的表現
"""

import pandas as pd
from datetime import datetime
from pathlib import Path
import json

from src.strategies.multi_timeframe_strategy import MultiTimeframeStrategy
from src.execution.backtest_engine import BacktestEngine
from src.models.config import StrategyConfig


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
    
    return data


def run_backtest_with_leverage(leverage: int, config_file: str, market_data: dict):
    """運行指定槓桿的回測"""
    # 載入配置
    with open(config_file, 'r') as f:
        config_dict = json.load(f)
    
    # 修改槓桿
    config_dict['risk_management']['leverage'] = leverage
    
    # 創建策略
    config = StrategyConfig.from_dict(config_dict)
    strategy = MultiTimeframeStrategy(config)
    
    # 創建回測引擎
    engine = BacktestEngine(initial_capital=1000.0, commission=0.0005)
    
    # 運行回測
    result = engine.run_single_strategy(strategy, market_data)
    
    return result


def main():
    """主函數"""
    print("=" * 100)
    print("新架構槓桿對比回測")
    print("=" * 100)
    print("\n配置：")
    print("  起始資金：1000 USDT")
    print("  倉位：20%")
    print("  止損：1.5 ATR（激進）/ 2.0 ATR（輕鬆）")
    print("  目標：3.0 ATR（激進）/ 4.0 ATR（輕鬆）")
    print("  手續費：0.05%")
    print("  遍歷週期：1h（自動選擇）")
    
    # 載入市場數據
    print("\n載入市場數據...")
    market_data = load_market_data('ETHUSDT')
    
    # 測試配置
    configs = [
        ("strategies/multi-timeframe-aggressive.json", "激進模式（1.5 ATR）"),
        ("strategies/multi-timeframe-relaxed.json", "輕鬆模式（2.0 ATR）")
    ]
    
    # 測試槓桿
    leverages = [1, 2, 3, 5, 10, 20]
    
    all_results = {}
    
    for config_file, mode_name in configs:
        print(f"\n{'=' * 100}")
        print(f"測試：{mode_name}")
        print(f"{'=' * 100}")
        
        mode_results = []
        
        for leverage in leverages:
            print(f"\n回測 {leverage}x 槓桿...")
            
            try:
                result = run_backtest_with_leverage(leverage, config_file, market_data)
                
                # 檢查是否爆倉（資金 <= 0）
                bankrupted = result.final_capital <= 0
                
                # 計算最大連續虧損
                max_consecutive_losses = 0
                current_consecutive_losses = 0
                for trade in result.trades:
                    if trade.pnl < 0:
                        current_consecutive_losses += 1
                        max_consecutive_losses = max(max_consecutive_losses, current_consecutive_losses)
                    else:
                        current_consecutive_losses = 0
                
                mode_results.append({
                    'leverage': leverage,
                    'trades': result.total_trades,
                    'wins': result.winning_trades,
                    'losses': result.losing_trades,
                    'win_rate': result.win_rate,
                    'final_capital': result.final_capital,
                    'total_return': result.total_pnl_pct,
                    'max_drawdown': result.max_drawdown_pct,
                    'sharpe_ratio': result.sharpe_ratio,
                    'profit_factor': result.profit_factor,
                    'max_consecutive_losses': max_consecutive_losses,
                    'bankrupted': bankrupted
                })
                
                print(f"  總交易：{result.total_trades}")
                print(f"  勝率：{result.win_rate:.2f}%")
                print(f"  最終資金：{result.final_capital:.2f} USDT")
                print(f"  總收益：{result.total_pnl_pct:+.2f}%")
                print(f"  最大回撤：{result.max_drawdown_pct:.2f}%")
                print(f"  夏普比率：{result.sharpe_ratio:.2f}")
                print(f"  獲利因子：{result.profit_factor:.2f}")
                print(f"  最大連損：{max_consecutive_losses} 次")
                
                if bankrupted:
                    print(f"  ⚠️ 爆倉！")
                
            except Exception as e:
                print(f"  ❌ 錯誤：{e}")
                mode_results.append({
                    'leverage': leverage,
                    'trades': 0,
                    'wins': 0,
                    'losses': 0,
                    'win_rate': 0,
                    'final_capital': 0,
                    'total_return': -100,
                    'max_drawdown': 100,
                    'sharpe_ratio': 0,
                    'profit_factor': 0,
                    'max_consecutive_losses': 0,
                    'bankrupted': True
                })
        
        all_results[mode_name] = mode_results
    
    # 打印對比表
    print("\n" + "=" * 100)
    print("激進模式（1.5 ATR）槓桿對比")
    print("=" * 100)
    print(f"\n{'槓桿':<8} {'交易數':<8} {'勝率':<10} {'最終資金':<12} {'收益率':<12} "
          f"{'最大回撤':<12} {'夏普比率':<10} {'獲利因子':<10} {'最大連損':<10} {'狀態':<10}")
    print("-" * 100)
    
    for r in all_results["激進模式（1.5 ATR）"]:
        status = "爆倉 ❌" if r['bankrupted'] else "存活 ✅"
        print(f"{r['leverage']}x{'':<6} {r['trades']:<8} {r['win_rate']:<9.2f}% "
              f"{r['final_capital']:<11.2f} {r['total_return']:+11.2f}% "
              f"{r['max_drawdown']:<11.2f}% {r['sharpe_ratio']:<9.2f} "
              f"{r['profit_factor']:<9.2f} {r['max_consecutive_losses']:<10} {status}")
    
    print("\n" + "=" * 100)
    print("輕鬆模式（2.0 ATR）槓桿對比")
    print("=" * 100)
    print(f"\n{'槓桿':<8} {'交易數':<8} {'勝率':<10} {'最終資金':<12} {'收益率':<12} "
          f"{'最大回撤':<12} {'夏普比率':<10} {'獲利因子':<10} {'最大連損':<10} {'狀態':<10}")
    print("-" * 100)
    
    for r in all_results["輕鬆模式（2.0 ATR）"]:
        status = "爆倉 ❌" if r['bankrupted'] else "存活 ✅"
        print(f"{r['leverage']}x{'':<6} {r['trades']:<8} {r['win_rate']:<9.2f}% "
              f"{r['final_capital']:<11.2f} {r['total_return']:+11.2f}% "
              f"{r['max_drawdown']:<11.2f}% {r['sharpe_ratio']:<9.2f} "
              f"{r['profit_factor']:<9.2f} {r['max_consecutive_losses']:<10} {status}")
    
    # 對比原始滿倉回測
    print("\n" + "=" * 100)
    print("與原始滿倉回測對比（激進模式）")
    print("=" * 100)
    print(f"\n{'配置':<25} {'槓桿':<8} {'倉位':<8} {'交易數':<8} {'勝率':<10} "
          f"{'收益率':<12} {'最大回撤':<12} {'風險調整收益':<15}")
    print("-" * 100)
    
    # 原始滿倉數據（從 full_position_backtest.py 的結果）
    original_results = [
        {'leverage': 1, 'return': 42.29, 'drawdown': 6.68, 'trades': 33, 'win_rate': 54.55},
        {'leverage': 2, 'return': 93.27, 'drawdown': 13.40, 'trades': 33, 'win_rate': 54.55},
        {'leverage': 3, 'return': 151.18, 'drawdown': 20.09, 'trades': 33, 'win_rate': 54.55},
        {'leverage': 5, 'return': 274.12, 'drawdown': 33.18, 'trades': 33, 'win_rate': 54.55},
        {'leverage': 10, 'return': 401.26, 'drawdown': 62.24, 'trades': 33, 'win_rate': 54.55},
        {'leverage': 20, 'return': -83.50, 'drawdown': 96.97, 'trades': 33, 'win_rate': 54.55},
    ]
    
    for orig in original_results:
        risk_adj = orig['return'] / orig['drawdown'] if orig['drawdown'] > 0 else 0
        print(f"{'原始滿倉':<25} {orig['leverage']}x{'':<6} {'100%':<8} {orig['trades']:<8} "
              f"{orig['win_rate']:<9.2f}% {orig['return']:+11.2f}% {orig['drawdown']:<11.2f}% "
              f"{risk_adj:<14.2f}")
    
    print()
    for r in all_results["激進模式（1.5 ATR）"]:
        if r['leverage'] <= 20:
            risk_adj = r['total_return'] / r['max_drawdown'] if r['max_drawdown'] > 0 else 0
            print(f"{'新架構 20% 倉位':<25} {r['leverage']}x{'':<6} {'20%':<8} {r['trades']:<8} "
                  f"{r['win_rate']:<9.2f}% {r['total_return']:+11.2f}% {r['max_drawdown']:<11.2f}% "
                  f"{risk_adj:<14.2f}")
    
    # 保存結果
    print("\n" + "=" * 100)
    print("保存結果...")
    
    # 保存為 CSV
    for mode_name, results in all_results.items():
        filename = f"leverage_comparison_{mode_name.replace('（', '_').replace('）', '').replace(' ', '_')}.csv"
        df = pd.DataFrame(results)
        df.to_csv(filename, index=False)
        print(f"  ✅ {filename}")
    
    print("\n" + "=" * 100)
    print("結論：")
    print("=" * 100)
    
    # 找出最佳槓桿
    agg_results = all_results["激進模式（1.5 ATR）"]
    best_leverage = max([r for r in agg_results if not r['bankrupted']], 
                       key=lambda x: x['total_return'] / max(x['max_drawdown'], 1))
    
    print(f"\n最佳風險調整收益（激進模式）：")
    print(f"  槓桿：{best_leverage['leverage']}x")
    print(f"  收益：{best_leverage['total_return']:+.2f}%")
    print(f"  回撤：{best_leverage['max_drawdown']:.2f}%")
    print(f"  風險調整收益：{best_leverage['total_return'] / max(best_leverage['max_drawdown'], 1):.2f}")
    
    print("\n建議：")
    print("  - 新手：1-2x 槓桿（安全穩健）")
    print("  - 有經驗：3-5x 槓桿（平衡收益風險）")
    print("  - 專家：5-10x 槓桿（高收益高風險）")
    print("  - ⚠️ 不建議超過 10x 槓桿（極易爆倉）")
    
    print("\n" + "=" * 100)


if __name__ == "__main__":
    main()
