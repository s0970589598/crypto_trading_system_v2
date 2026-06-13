#!/usr/bin/env python3
"""
深度分析進出場技術指標
找出失控交易和正常交易的差異
"""

import pandas as pd
import numpy as np
from pathlib import Path

def load_analysis_data():
    """載入分析數據"""
    file_path = 'analysis_results/entry_exit_analysis_binance_full.csv'
    
    if not Path(file_path).exists():
        print(f"❌ 找不到分析文件: {file_path}")
        print("請先運行: python3 從Binance獲取完整歷史數據.py")
        return None
    
    df = pd.read_csv(file_path)
    
    # 載入失控交易標記
    tilt_file = 'analysis_results/tilt_vs_normal_trades.csv'
    if Path(tilt_file).exists():
        tilt_df = pd.read_csv(tilt_file)
        # 合併失控交易標記
        df = df.merge(tilt_df[['open_time', 'is_tilt', 'trade_type']], 
                     on='open_time', how='left')
    else:
        # 如果沒有失控交易標記，根據規則判斷
        df['open_time'] = pd.to_datetime(df['open_time'])
        df = df.sort_values('open_time')
        df['prev_pnl'] = df['pnl'].shift(1)
        df['is_after_loss'] = df['prev_pnl'] < 0
        df['time_since_last'] = df['open_time'].diff().dt.total_seconds() / 60
        
        # 定義失控交易
        df['is_tilt'] = (
            (df['is_after_loss'] == True) & 
            (
                (df['time_since_last'] < 30) | 
                (df['holding_minutes'] < 5) | 
                (df['leverage'] > 80)
            )
        )
        df['trade_type'] = df['is_tilt'].apply(lambda x: '失控交易' if x else '正常交易')
    
    return df

def analyze_by_timeframe(df, interval):
    """分析特定時間週期的技術指標"""
    
    trend_col = f'{interval}_entry_trend'
    macd_col = f'{interval}_entry_macd_state'
    rsi_col = f'{interval}_entry_rsi_state'
    bb_col = f'{interval}_entry_bb_position'
    
    if trend_col not in df.columns:
        return None
    
    print(f"\n{'=' * 80}")
    print(f"【{interval} 週期深度分析】")
    print('=' * 80)
    
    # 1. 失控交易 vs 正常交易
    print(f"\n1️⃣  失控交易 vs 正常交易")
    print('-' * 80)
    
    for trade_type in ['失控交易', '正常交易']:
        subset = df[df['trade_type'] == trade_type]
        if len(subset) == 0:
            continue
        
        print(f"\n【{trade_type}】({len(subset)} 筆)")
        print(f"  總盈虧: {subset['pnl'].sum():.2f} USDT")
        print(f"  平均盈虧: {subset['pnl'].mean():.2f} USDT")
        print(f"  勝率: {(subset['pnl'] > 0).sum() / len(subset) * 100:.1f}%")
        
        # 趨勢分布
        if trend_col in subset.columns:
            print(f"\n  趨勢分布:")
            for trend in subset[trend_col].value_counts().index[:3]:
                count = (subset[trend_col] == trend).sum()
                pct = count / len(subset) * 100
                pnl = subset[subset[trend_col] == trend]['pnl'].mean()
                print(f"    {trend}: {count} 筆 ({pct:.1f}%)，平均 {pnl:.2f} USDT")
        
        # MACD 分布
        if macd_col in subset.columns:
            print(f"\n  MACD 狀態:")
            for state in subset[macd_col].value_counts().index[:3]:
                count = (subset[macd_col] == state).sum()
                pct = count / len(subset) * 100
                pnl = subset[subset[macd_col] == state]['pnl'].mean()
                print(f"    {state}: {count} 筆 ({pct:.1f}%)，平均 {pnl:.2f} USDT")
        
        # RSI 分布
        if rsi_col in subset.columns:
            print(f"\n  RSI 狀態:")
            for state in subset[rsi_col].value_counts().index[:3]:
                count = (subset[rsi_col] == state).sum()
                pct = count / len(subset) * 100
                pnl = subset[subset[rsi_col] == state]['pnl'].mean()
                print(f"    {state}: {count} 筆 ({pct:.1f}%)，平均 {pnl:.2f} USDT")
    
    # 2. 最差技術指標組合
    print(f"\n2️⃣  最差技術指標組合（虧損最多）")
    print('-' * 80)
    
    grouped = df.groupby([trend_col, macd_col, rsi_col])['pnl'].agg(['count', 'sum', 'mean'])
    worst = grouped.sort_values('sum').head(5)
    
    for idx, row in worst.iterrows():
        if row['sum'] < 0:
            print(f"\n  {idx[0]} + {idx[1]} + {idx[2]}:")
            print(f"    交易數: {int(row['count'])} 筆")
            print(f"    總虧損: {row['sum']:.2f} USDT")
            print(f"    平均虧損: {row['mean']:.2f} USDT")
            
            # 檢查這個組合中失控交易的比例
            combo_df = df[
                (df[trend_col] == idx[0]) & 
                (df[macd_col] == idx[1]) & 
                (df[rsi_col] == idx[2])
            ]
            tilt_pct = (combo_df['is_tilt'] == True).sum() / len(combo_df) * 100
            print(f"    失控交易比例: {tilt_pct:.1f}%")
    
    # 3. 最佳技術指標組合
    print(f"\n3️⃣  最佳技術指標組合（盈利最多）")
    print('-' * 80)
    
    best = grouped.sort_values('sum', ascending=False).head(5)
    
    for idx, row in best.iterrows():
        if row['sum'] > 0:
            print(f"\n  {idx[0]} + {idx[1]} + {idx[2]}:")
            print(f"    交易數: {int(row['count'])} 筆")
            print(f"    總盈利: {row['sum']:.2f} USDT")
            print(f"    平均盈利: {row['mean']:.2f} USDT")
            
            # 檢查這個組合中失控交易的比例
            combo_df = df[
                (df[trend_col] == idx[0]) & 
                (df[macd_col] == idx[1]) & 
                (df[rsi_col] == idx[2])
            ]
            tilt_pct = (combo_df['is_tilt'] == True).sum() / len(combo_df) * 100
            print(f"    失控交易比例: {tilt_pct:.1f}%")
    
    # 4. 逆勢交易分析
    print(f"\n4️⃣  逆勢交易分析")
    print('-' * 80)
    
    # Long 在 downtrend
    long_downtrend = df[
        (df['direction'] == 'Long') & 
        (df[trend_col].str.contains('downtrend', na=False))
    ]
    
    if len(long_downtrend) > 0:
        print(f"\n  做多在下跌趨勢:")
        print(f"    交易數: {len(long_downtrend)} 筆")
        print(f"    總盈虧: {long_downtrend['pnl'].sum():.2f} USDT")
        print(f"    勝率: {(long_downtrend['pnl'] > 0).sum() / len(long_downtrend) * 100:.1f}%")
        print(f"    失控交易比例: {(long_downtrend['is_tilt'] == True).sum() / len(long_downtrend) * 100:.1f}%")
    
    # Short 在 uptrend
    short_uptrend = df[
        (df['direction'] == 'Short') & 
        (df[trend_col].str.contains('uptrend', na=False))
    ]
    
    if len(short_uptrend) > 0:
        print(f"\n  做空在上漲趨勢:")
        print(f"    交易數: {len(short_uptrend)} 筆")
        print(f"    總盈虧: {short_uptrend['pnl'].sum():.2f} USDT")
        print(f"    勝率: {(short_uptrend['pnl'] > 0).sum() / len(short_uptrend) * 100:.1f}%")
        print(f"    失控交易比例: {(short_uptrend['is_tilt'] == True).sum() / len(short_uptrend) * 100:.1f}%")
    
    # 5. RSI 極端值分析
    print(f"\n5️⃣  RSI 極端值分析")
    print('-' * 80)
    
    rsi_value_col = f'{interval}_entry_rsi'
    if rsi_value_col in df.columns:
        # RSI > 70 做多
        long_overbought = df[
            (df['direction'] == 'Long') & 
            (df[rsi_value_col] > 70)
        ]
        
        if len(long_overbought) > 0:
            print(f"\n  做多在 RSI > 70 (超買):")
            print(f"    交易數: {len(long_overbought)} 筆")
            print(f"    總盈虧: {long_overbought['pnl'].sum():.2f} USDT")
            print(f"    勝率: {(long_overbought['pnl'] > 0).sum() / len(long_overbought) * 100:.1f}%")
            print(f"    失控交易比例: {(long_overbought['is_tilt'] == True).sum() / len(long_overbought) * 100:.1f}%")
        
        # RSI < 30 做空
        short_oversold = df[
            (df['direction'] == 'Short') & 
            (df[rsi_value_col] < 30)
        ]
        
        if len(short_oversold) > 0:
            print(f"\n  做空在 RSI < 30 (超賣):")
            print(f"    交易數: {len(short_oversold)} 筆")
            print(f"    總盈虧: {short_oversold['pnl'].sum():.2f} USDT")
            print(f"    勝率: {(short_oversold['pnl'] > 0).sum() / len(short_oversold) * 100:.1f}%")
            print(f"    失控交易比例: {(short_oversold['is_tilt'] == True).sum() / len(short_oversold) * 100:.1f}%")

def generate_trading_rules(df):
    """根據分析結果生成交易規則"""
    
    print(f"\n{'=' * 80}")
    print("🎯 交易規則建議")
    print('=' * 80)
    
    rules = []
    
    # 分析失控交易的特徵
    tilt_trades = df[df['is_tilt'] == True]
    normal_trades = df[df['is_tilt'] == False]
    
    print(f"\n基於 {len(df)} 筆交易的分析結果：")
    print(f"  - 失控交易: {len(tilt_trades)} 筆，總虧損 {tilt_trades['pnl'].sum():.2f} USDT")
    print(f"  - 正常交易: {len(normal_trades)} 筆，總盈虧 {normal_trades['pnl'].sum():.2f} USDT")
    
    print(f"\n【禁止交易規則】")
    print('-' * 80)
    
    rule_num = 1
    
    # 規則 1: 虧損後冷靜期
    print(f"\n{rule_num}. 虧損後強制冷靜期")
    print(f"   ❌ 虧損後 60 分鐘內禁止交易")
    print(f"   ❌ 連續虧損 2 次後 120 分鐘內禁止交易")
    print(f"   ❌ 連續虧損 3 次後當日停止交易")
    rule_num += 1
    
    # 規則 2: 虧損後降低槓桿
    print(f"\n{rule_num}. 虧損後降低槓桿")
    print(f"   ⚠️  正常狀態: 最高 50x")
    print(f"   ⚠️  虧損 1 次後: 降至 30x")
    print(f"   ⚠️  虧損 2 次後: 降至 20x")
    print(f"   ⚠️  虧損 3 次後: 降至 10x")
    rule_num += 1
    
    # 規則 3: 最短持倉時間
    print(f"\n{rule_num}. 最短持倉時間限制")
    print(f"   ❌ 禁止持倉 < 5 分鐘的交易")
    print(f"   ⚠️  虧損後最短持倉時間: 15 分鐘")
    rule_num += 1
    
    # 分析技術指標規則
    for interval in ['1m', '3m', '5m']:
        trend_col = f'{interval}_entry_trend'
        macd_col = f'{interval}_entry_macd_state'
        rsi_col = f'{interval}_entry_rsi_state'
        
        if trend_col not in df.columns:
            continue
        
        # 找出虧損最多的組合
        grouped = df.groupby([trend_col, macd_col, rsi_col])['pnl'].agg(['count', 'sum'])
        worst = grouped[grouped['sum'] < 0].sort_values('sum').head(3)
        
        if len(worst) > 0:
            print(f"\n{rule_num}. {interval} 週期禁止進場條件")
            for idx, row in worst.iterrows():
                if row['count'] >= 3:  # 至少 3 筆交易
                    print(f"   ❌ {idx[0]} + {idx[1]} + {idx[2]}")
                    print(f"      ({int(row['count'])} 筆交易，總虧損 {row['sum']:.2f} USDT)")
            rule_num += 1
    
    print(f"\n【建議進場條件】")
    print('-' * 80)
    
    # 找出盈利的組合
    for interval in ['1m', '3m', '5m']:
        trend_col = f'{interval}_entry_trend'
        macd_col = f'{interval}_entry_macd_state'
        rsi_col = f'{interval}_entry_rsi_state'
        
        if trend_col not in df.columns:
            continue
        
        grouped = df.groupby([trend_col, macd_col, rsi_col])['pnl'].agg(['count', 'sum', 'mean'])
        best = grouped[grouped['sum'] > 0].sort_values('sum', ascending=False).head(3)
        
        if len(best) > 0:
            print(f"\n{interval} 週期最佳進場條件:")
            for idx, row in best.iterrows():
                if row['count'] >= 2:
                    win_rate = (df[
                        (df[trend_col] == idx[0]) & 
                        (df[macd_col] == idx[1]) & 
                        (df[rsi_col] == idx[2])
                    ]['pnl'] > 0).sum() / row['count'] * 100
                    
                    print(f"   ✅ {idx[0]} + {idx[1]} + {idx[2]}")
                    print(f"      ({int(row['count'])} 筆，總盈利 {row['sum']:.2f} USDT，勝率 {win_rate:.1f}%)")
    
    print(f"\n【多時區確認規則】")
    print('-' * 80)
    print(f"\n建議使用多時區確認，提高勝率:")
    print(f"   1. 1m 看精確進場點")
    print(f"   2. 3m 看短期趨勢確認")
    print(f"   3. 5m 看中期趨勢確認")
    print(f"   4. 15m 看大趨勢方向")
    print(f"\n   ✅ 只有當 3m + 5m + 15m 趨勢一致時才進場")
    print(f"   ✅ 使用 1m 找精確的進場點")

def main():
    print("=" * 80)
    print("深度分析進出場技術指標")
    print("=" * 80)
    
    # 載入數據
    df = load_analysis_data()
    
    if df is None:
        return
    
    print(f"\n✅ 已載入 {len(df)} 筆交易數據")
    print(f"   - 失控交易: {(df['is_tilt'] == True).sum()} 筆")
    print(f"   - 正常交易: {(df['is_tilt'] == False).sum()} 筆")
    
    # 分析各時間週期
    for interval in ['1m', '3m', '5m']:
        analyze_by_timeframe(df, interval)
    
    # 生成交易規則
    generate_trading_rules(df)
    
    print(f"\n{'=' * 80}")
    print("分析完成！")
    print('=' * 80)
    print()
    print("💡 建議:")
    print("  1. 重點關注「失控交易」的技術指標特徵")
    print("  2. 避免在虧損後使用「最差技術指標組合」進場")
    print("  3. 實施「禁止交易規則」，防止情緒失控")
    print("  4. 使用「多時區確認」，提高勝率")

if __name__ == "__main__":
    main()
