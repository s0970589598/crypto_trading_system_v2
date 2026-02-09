#!/usr/bin/env python3
"""快速查看回測結果"""

import json
import glob
import pandas as pd

print("\n" + "=" * 70)
print("🚀 交易系統 - 快速查看")
print("=" * 70)

# 1. 最新回測結果
print("\n📈 最新回測結果")
print("-" * 70)

files = glob.glob('backtest_result_*.json')
if files:
    latest = max(files, key=lambda x: x.split('_')[-2] + x.split('_')[-1].replace('.json', ''))
    
    with open(latest) as f:
        r = json.load(f)
    
    print(f"策略：{r['strategy_id']}")
    print(f"時間：{r['start_date'][:10]} 至 {r['end_date'][:10]}")
    print(f"\n💰 收益：")
    print(f"   初始：{r['initial_capital']:.2f} USDT")
    print(f"   最終：{r['final_capital']:.2f} USDT")
    print(f"   收益：+{r['total_pnl_pct']:.2f}%")
    print(f"\n📊 交易：")
    print(f"   總數：{r['total_trades']}")
    print(f"   勝率：{r['win_rate']:.2f}%")
    print(f"   獲利因子：{r['profit_factor']:.2f}")
    print(f"\n⚠️ 風險：")
    print(f"   最大回撤：-{r['max_drawdown_pct']:.2f}%")
    print(f"   夏普比率：{r['sharpe_ratio']:.2f}")
else:
    print("❌ 沒有回測結果")

# 2. 槓桿對比
print("\n" + "=" * 70)
print("📊 槓桿對比（激進模式）")
print("-" * 70)

try:
    df = pd.read_csv('leverage_comparison_激進模式_1.5_ATR.csv')
    
    print(f"\n{'槓桿':<6} {'收益':<10} {'回撤':<10} {'勝率':<8} {'風險調整':<10} {'評級'}")
    print("-" * 70)
    
    for _, row in df.iterrows():
        lev = int(row['leverage'])
        ret = row['total_return']
        dd = row['max_drawdown']
        wr = row['win_rate']
        ra = ret / dd if dd > 0 else 0
        
        if ra > 1.7:
            rating = "⭐⭐⭐⭐"
        elif ra > 1.5:
            rating = "⭐⭐⭐"
        elif ra > 1.3:
            rating = "⭐⭐"
        else:
            rating = "⭐"
        
        print(f"{lev}x     +{ret:>6.2f}%  -{dd:>6.2f}%  {wr:>5.1f}%  {ra:>6.2f}     {rating}")
    
    best_idx = (df['total_return'] / df['max_drawdown']).idxmax()
    best_lev = int(df.loc[best_idx, 'leverage'])
    print(f"\n💡 推薦：{best_lev}x 槓桿（最佳風險調整收益）")
    
except FileNotFoundError:
    print("⚠️ 請先運行：python3 backtest_leverage_comparison.py")

# 3. 可用策略
print("\n" + "=" * 70)
print("⚙️ 可用策略")
print("-" * 70)

configs = glob.glob('strategies/*.json')
for cfg in sorted(configs):
    with open(cfg) as f:
        c = json.load(f)
    
    status = "✅" if c.get('enabled', False) else "❌"
    name = c.get('name', 'Unknown')
    id = c.get('id', 'unknown')
    
    params = c.get('parameters', {})
    risk = c.get('risk_management', {})
    
    stop = params.get('stop_loss_atr', '?')
    target = params.get('take_profit_atr', '?')
    pos = risk.get('position_size', 0) * 100
    lev = risk.get('leverage', '?')
    
    print(f"\n{status} {name}")
    print(f"   ID: {id}")
    print(f"   止損: {stop} ATR | 目標: {target} ATR | 倉位: {pos:.0f}% | 槓桿: {lev}x")

# 4. 快速命令
print("\n" + "=" * 70)
print("🎯 快速命令")
print("-" * 70)
print("""
1️⃣ 運行回測：
   python3 backtest_multi_timeframe.py

2️⃣ 測試槓桿：
   python3 backtest_leverage_comparison.py

3️⃣ 查看結果：
   python3 快速查看.py

4️⃣ 閱讀教學：
   open 新手入門教學.md

5️⃣ 查看策略：
   open PROGRESSIVE_POSITION_STRATEGY.md
""")

print("=" * 70)
print()
