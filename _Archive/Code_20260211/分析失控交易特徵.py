#!/usr/bin/env python3
"""
分析失控交易 vs 正常交易的差異
找出問題點在哪裡
"""

import json
import pandas as pd
from datetime import datetime, timedelta

# Load data
with open('data/review_history/quality_scores.json', 'r') as f:
    trades = json.load(f)

df = pd.DataFrame(trades)

# Calculate holding times
df['open_time'] = pd.to_datetime(df['open_time'])
df['close_time'] = pd.to_datetime(df['close_time'])
df['holding_minutes'] = (df['close_time'] - df['open_time']).dt.total_seconds() / 60

# Calculate time between trades
df = df.sort_values('open_time')
df['time_since_last_trade'] = df['open_time'].diff().dt.total_seconds() / 60

# Identify previous trade result
df['prev_pnl'] = df['pnl'].shift(1)
df['is_after_loss'] = df['prev_pnl'] < 0

# Categorize trades
df['is_short_term'] = df['holding_minutes'] < 5
df['is_profitable'] = df['pnl'] > 0

print("=" * 80)
print("【失控交易特徵分析】")
print("=" * 80)
print()

# 1. 虧損後的交易行為
print("1️⃣  虧損後的交易行為")
print("-" * 80)

after_loss = df[df['is_after_loss'] == True]
after_win = df[df['is_after_loss'] == False]

print(f"虧損後交易數: {len(after_loss)}")
print(f"獲利後交易數: {len(after_win)}")
print()

print("【交易間隔對比】")
print(f"  虧損後平均間隔: {after_loss['time_since_last_trade'].mean():.1f} 分鐘")
print(f"  獲利後平均間隔: {after_win['time_since_last_trade'].mean():.1f} 分鐘")
print(f"  差異: {((after_loss['time_since_last_trade'].mean() / after_win['time_since_last_trade'].mean() - 1) * 100):.1f}%")
print()

print("【持倉時間對比】")
print(f"  虧損後平均持倉: {after_loss['holding_minutes'].mean():.1f} 分鐘")
print(f"  獲利後平均持倉: {after_win['holding_minutes'].mean():.1f} 分鐘")
print()

print("【槓桿對比】")
print(f"  虧損後平均槓桿: {after_loss['leverage'].mean():.1f}x")
print(f"  獲利後平均槓桿: {after_win['leverage'].mean():.1f}x")
print(f"  差異: {((after_loss['leverage'].mean() / after_win['leverage'].mean() - 1) * 100):.1f}%")
print()

print("【勝率對比】")
print(f"  虧損後勝率: {(after_loss['is_profitable'].sum() / len(after_loss) * 100):.1f}%")
print(f"  獲利後勝率: {(after_win['is_profitable'].sum() / len(after_win) * 100):.1f}%")
print()

# 2. 短線交易細分
print("\n" + "=" * 80)
print("2️⃣  短線交易（<5分鐘）細分分析")
print("-" * 80)

short_trades = df[df['is_short_term'] == True]
short_after_loss = short_trades[short_trades['is_after_loss'] == True]
short_after_win = short_trades[short_trades['is_after_loss'] == False]

print(f"總短線交易: {len(short_trades)} 筆")
print(f"  - 虧損後的短線交易: {len(short_after_loss)} 筆 ({len(short_after_loss)/len(short_trades)*100:.1f}%)")
print(f"  - 獲利後的短線交易: {len(short_after_win)} 筆 ({len(short_after_win)/len(short_trades)*100:.1f}%)")
print()

print("【虧損後的短線交易】")
print(f"  交易數: {len(short_after_loss)}")
print(f"  總盈虧: {short_after_loss['pnl'].sum():.2f} USDT")
print(f"  平均盈虧: {short_after_loss['pnl'].mean():.2f} USDT")
print(f"  勝率: {(short_after_loss['is_profitable'].sum() / len(short_after_loss) * 100):.1f}%")
print(f"  平均槓桿: {short_after_loss['leverage'].mean():.1f}x")
print(f"  平均間隔: {short_after_loss['time_since_last_trade'].mean():.1f} 分鐘")
print()

print("【獲利後的短線交易】")
print(f"  交易數: {len(short_after_win)}")
print(f"  總盈虧: {short_after_win['pnl'].sum():.2f} USDT")
print(f"  平均盈虧: {short_after_win['pnl'].mean():.2f} USDT")
print(f"  勝率: {(short_after_win['is_profitable'].sum() / len(short_after_win) * 100):.1f}%")
print(f"  平均槓桿: {short_after_win['leverage'].mean():.1f}x")
print(f"  平均間隔: {short_after_win['time_since_last_trade'].mean():.1f} 分鐘")
print()

# 3. 極短線交易（<1分鐘）
print("\n" + "=" * 80)
print("3️⃣  極短線交易（<1分鐘）分析")
print("-" * 80)

ultra_short = df[df['holding_minutes'] < 1]
ultra_short_after_loss = ultra_short[ultra_short['is_after_loss'] == True]

print(f"極短線交易總數: {len(ultra_short)} 筆")
print(f"  - 虧損後: {len(ultra_short_after_loss)} 筆 ({len(ultra_short_after_loss)/len(ultra_short)*100:.1f}%)")
print(f"  總盈虧: {ultra_short['pnl'].sum():.2f} USDT")
print(f"  勝率: {(ultra_short['is_profitable'].sum() / len(ultra_short) * 100):.1f}%")
print()

# 4. 連續虧損後的行為
print("\n" + "=" * 80)
print("4️⃣  連續虧損後的行為變化")
print("-" * 80)

# Calculate consecutive losses
df['consecutive_losses'] = 0
consecutive = 0
for i in range(len(df)):
    if df.iloc[i]['pnl'] < 0:
        consecutive += 1
    else:
        consecutive = 0
    df.iloc[i, df.columns.get_loc('consecutive_losses')] = consecutive

# Trades after 2+ consecutive losses
after_2_losses = df[df['consecutive_losses'] >= 2]
after_3_losses = df[df['consecutive_losses'] >= 3]

print(f"連續虧損 2 次後的交易: {len(after_2_losses)} 筆")
print(f"  平均槓桿: {after_2_losses['leverage'].mean():.1f}x")
print(f"  短線交易比例: {(after_2_losses['is_short_term'].sum() / len(after_2_losses) * 100):.1f}%")
print(f"  勝率: {(after_2_losses['is_profitable'].sum() / len(after_2_losses) * 100):.1f}%")
print()

print(f"連續虧損 3 次後的交易: {len(after_3_losses)} 筆")
print(f"  平均槓桿: {after_3_losses['leverage'].mean():.1f}x")
print(f"  短線交易比例: {(after_3_losses['is_short_term'].sum() / len(after_3_losses) * 100):.1f}%")
print(f"  勝率: {(after_3_losses['is_profitable'].sum() / len(after_3_losses) * 100):.1f}%")
print()

# 5. 快速交易（間隔<30分鐘）
print("\n" + "=" * 80)
print("5️⃣  快速交易（間隔<30分鐘）分析")
print("-" * 80)

quick_trades = df[df['time_since_last_trade'] < 30]
quick_after_loss = quick_trades[quick_trades['is_after_loss'] == True]

print(f"快速交易總數: {len(quick_trades)} 筆")
print(f"  - 虧損後快速交易: {len(quick_after_loss)} 筆 ({len(quick_after_loss)/len(quick_trades)*100:.1f}%)")
print(f"  總盈虧: {quick_trades['pnl'].sum():.2f} USDT")
print(f"  勝率: {(quick_trades['is_profitable'].sum() / len(quick_trades) * 100):.1f}%")
print()

print("【虧損後的快速交易】")
print(f"  交易數: {len(quick_after_loss)}")
print(f"  總盈虧: {quick_after_loss['pnl'].sum():.2f} USDT")
print(f"  勝率: {(quick_after_loss['is_profitable'].sum() / len(quick_after_loss) * 100):.1f}%")
print(f"  平均槓桿: {quick_after_loss['leverage'].mean():.1f}x")
print()

# 6. 正常交易（間隔>60分鐘 且 持倉>15分鐘）
print("\n" + "=" * 80)
print("6️⃣  正常交易（間隔>60分鐘 且 持倉>15分鐘）")
print("-" * 80)

normal_trades = df[(df['time_since_last_trade'] > 60) & (df['holding_minutes'] > 15)]

print(f"正常交易數: {len(normal_trades)} 筆")
print(f"  總盈虧: {normal_trades['pnl'].sum():.2f} USDT")
print(f"  平均盈虧: {normal_trades['pnl'].mean():.2f} USDT")
print(f"  勝率: {(normal_trades['is_profitable'].sum() / len(normal_trades) * 100):.1f}%")
print(f"  平均槓桿: {normal_trades['leverage'].mean():.1f}x")
print(f"  平均持倉: {normal_trades['holding_minutes'].mean():.1f} 分鐘")
print()

# 7. 失控交易定義
print("\n" + "=" * 80)
print("7️⃣  失控交易特徵定義")
print("-" * 80)

# 定義失控交易：虧損後 + (間隔<30分鐘 或 持倉<5分鐘 或 槓桿>80x)
df['is_tilt'] = (
    (df['is_after_loss'] == True) & 
    (
        (df['time_since_last_trade'] < 30) | 
        (df['holding_minutes'] < 5) | 
        (df['leverage'] > 80)
    )
)

tilt_trades = df[df['is_tilt'] == True]
normal_trades_v2 = df[df['is_tilt'] == False]

print("失控交易定義：虧損後 + (間隔<30分鐘 或 持倉<5分鐘 或 槓桿>80x)")
print()

print(f"【失控交易】{len(tilt_trades)} 筆 ({len(tilt_trades)/len(df)*100:.1f}%)")
print(f"  總盈虧: {tilt_trades['pnl'].sum():.2f} USDT")
print(f"  平均盈虧: {tilt_trades['pnl'].mean():.2f} USDT")
print(f"  勝率: {(tilt_trades['is_profitable'].sum() / len(tilt_trades) * 100):.1f}%")
print(f"  平均槓桿: {tilt_trades['leverage'].mean():.1f}x")
print(f"  平均持倉: {tilt_trades['holding_minutes'].mean():.1f} 分鐘")
print(f"  平均間隔: {tilt_trades['time_since_last_trade'].mean():.1f} 分鐘")
print()

print(f"【正常交易】{len(normal_trades_v2)} 筆 ({len(normal_trades_v2)/len(df)*100:.1f}%)")
print(f"  總盈虧: {normal_trades_v2['pnl'].sum():.2f} USDT")
print(f"  平均盈虧: {normal_trades_v2['pnl'].mean():.2f} USDT")
print(f"  勝率: {(normal_trades_v2['is_profitable'].sum() / len(normal_trades_v2) * 100):.1f}%")
print(f"  平均槓桿: {normal_trades_v2['leverage'].mean():.1f}x")
print(f"  平均持倉: {normal_trades_v2['holding_minutes'].mean():.1f} 分鐘")
print(f"  平均間隔: {normal_trades_v2['time_since_last_trade'].mean():.1f} 分鐘")
print()

# 8. 關鍵發現
print("\n" + "=" * 80)
print("8️⃣  關鍵發現：問題點在哪裡？")
print("=" * 80)
print()

impact = tilt_trades['pnl'].sum()
total_loss = df[df['pnl'] < 0]['pnl'].sum()

print(f"✅ 失控交易造成的虧損: {impact:.2f} USDT")
print(f"✅ 佔總虧損比例: {abs(impact / total_loss * 100):.1f}%")
print()

print(f"✅ 如果移除失控交易:")
print(f"   總盈虧: {df['pnl'].sum():.2f} → {normal_trades_v2['pnl'].sum():.2f} USDT")
print(f"   改善: {normal_trades_v2['pnl'].sum() - df['pnl'].sum():.2f} USDT")
print(f"   勝率: {(df['is_profitable'].sum() / len(df) * 100):.1f}% → {(normal_trades_v2['is_profitable'].sum() / len(normal_trades_v2) * 100):.1f}%")
print()

print("🎯 結論:")
print(f"   - 失控交易只佔 {len(tilt_trades)/len(df)*100:.1f}% 的交易數")
print(f"   - 但造成了 {abs(impact / total_loss * 100):.1f}% 的虧損")
print(f"   - 正常交易的勝率是 {(normal_trades_v2['is_profitable'].sum() / len(normal_trades_v2) * 100):.1f}%")
print(f"   - 失控交易的勝率只有 {(tilt_trades['is_profitable'].sum() / len(tilt_trades) * 100):.1f}%")
print()

# 9. 保存詳細數據
print("\n" + "=" * 80)
print("9️⃣  保存詳細分析數據")
print("-" * 80)

# 標記每筆交易
df['trade_type'] = df['is_tilt'].apply(lambda x: '失控交易' if x else '正常交易')

# 保存到 CSV
output_file = 'analysis_results/tilt_vs_normal_trades.csv'
df[['open_time', 'symbol', 'direction', 'pnl', 'holding_minutes', 'leverage', 
    'time_since_last_trade', 'is_after_loss', 'consecutive_losses', 
    'is_short_term', 'is_tilt', 'trade_type']].to_csv(output_file, index=False)

print(f"✅ 詳細數據已保存到: {output_file}")
print()

print("=" * 80)
print("分析完成！")
print("=" * 80)
