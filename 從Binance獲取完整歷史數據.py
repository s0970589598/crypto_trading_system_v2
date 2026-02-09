#!/usr/bin/env python3
"""
從 Binance 獲取完整的 1m/3m/5m 歷史數據
並分析所有交易的進出場點技術指標
"""

import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import json
from pathlib import Path

def calculate_technical_indicators(df):
    """計算技術指標"""
    # EMA
    df['ema_7'] = df['close'].ewm(span=7, adjust=False).mean()
    df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
    
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # MACD
    ema_12 = df['close'].ewm(span=12, adjust=False).mean()
    ema_26 = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = ema_12 - ema_26
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['macd_hist'] = df['macd'] - df['macd_signal']
    
    # Bollinger Bands
    df['bb_middle'] = df['close'].rolling(window=20).mean()
    bb_std = df['close'].rolling(window=20).std()
    df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
    df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
    
    # ATR
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    df['atr'] = true_range.rolling(14).mean()
    
    # Volume MA
    df['volume_ma'] = df['volume'].rolling(window=20).mean()
    
    return df

def fetch_binance_klines(symbol, interval, start_time, end_time):
    """
    從 Binance API 批次獲取 K線數據
    
    優點：
    - 支援批次獲取歷史數據
    - 單次最多 1000 根，可分批
    - 無歷史時間限制
    """
    url = "https://api.binance.com/api/v3/klines"
    
    all_klines = []
    current_start = start_time
    batch_num = 0
    
    print(f"  開始獲取 {symbol} {interval} 數據...")
    print(f"  時間範圍: {start_time.strftime('%Y-%m-%d %H:%M')} 至 {end_time.strftime('%Y-%m-%d %H:%M')}")
    
    while current_start < end_time:
        batch_num += 1
        params = {
            'symbol': symbol,
            'interval': interval,
            'startTime': int(current_start.timestamp() * 1000),
            'endTime': int(end_time.timestamp() * 1000),
            'limit': 1000  # Binance 最大限制
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            klines = response.json()
            
            if not klines:
                break
            
            all_klines.extend(klines)
            
            # 更新起始時間為最後一根 K線的時間 + 1 毫秒
            last_time = klines[-1][0]
            current_start = datetime.fromtimestamp(last_time / 1000) + timedelta(milliseconds=1)
            
            print(f"    批次 {batch_num}: 已獲取 {len(all_klines)} 根 K線...", end='\r')
            
            # 避免 API 限流
            time.sleep(0.3)
            
        except Exception as e:
            print(f"    ❌ 異常: {e}")
            break
    
    print(f"    ✅ 完成，共 {len(all_klines)} 根 K線（{batch_num} 批次）")
    
    if not all_klines:
        return pd.DataFrame()
    
    # 轉換為 DataFrame
    df = pd.DataFrame(all_klines, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_volume', 'trades', 'taker_buy_base',
        'taker_buy_quote', 'ignore'
    ])
    
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df['close_time'] = pd.to_datetime(df['close_time'], unit='ms')
    
    # 轉換數據類型
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # 計算技術指標
    df = calculate_technical_indicators(df)
    
    return df

def analyze_trade_entry_exit(trades_file, market_data):
    """
    分析每筆交易的進出場點技術指標
    """
    # 讀取交易記錄
    with open(trades_file, 'r') as f:
        trades = json.load(f)
    
    results = []
    
    print("\n分析交易進出場點...")
    
    for idx, trade in enumerate(trades, 1):
        trade_id = trade.get('trade_id')
        symbol = trade.get('symbol', '').replace('-', '')  # ETH-USDT -> ETHUSDT
        open_time = pd.to_datetime(trade.get('open_time'))
        close_time = pd.to_datetime(trade.get('close_time'))
        entry_price = trade.get('entry_price')
        exit_price = trade.get('exit_price')
        pnl = trade.get('pnl')
        direction = trade.get('direction')
        leverage = trade.get('leverage')
        
        if symbol not in market_data:
            continue
        
        analysis = {
            'trade_id': trade_id,
            'symbol': symbol,
            'direction': direction,
            'open_time': open_time,
            'close_time': close_time,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'pnl': pnl,
            'leverage': leverage,
            'holding_minutes': (close_time - open_time).total_seconds() / 60
        }
        
        # 分析每個時間週期
        for interval, df in market_data[symbol].items():
            if df.empty:
                continue
            
            # 找到進場時的 K線（最接近但不晚於進場時間）
            entry_candles = df[df['timestamp'] <= open_time]
            if entry_candles.empty:
                continue
            
            entry_data = entry_candles.iloc[-1]
            
            # 找到出場時的 K線
            exit_candles = df[df['timestamp'] <= close_time]
            if exit_candles.empty:
                continue
            
            exit_data = exit_candles.iloc[-1]
            
            # 進場時的技術指標
            analysis[f'{interval}_entry_price'] = entry_data['close']
            analysis[f'{interval}_entry_ema7'] = entry_data['ema_7']
            analysis[f'{interval}_entry_ema20'] = entry_data['ema_20']
            analysis[f'{interval}_entry_ema50'] = entry_data['ema_50']
            analysis[f'{interval}_entry_rsi'] = entry_data['rsi']
            analysis[f'{interval}_entry_macd'] = entry_data['macd']
            analysis[f'{interval}_entry_macd_signal'] = entry_data['macd_signal']
            analysis[f'{interval}_entry_macd_hist'] = entry_data['macd_hist']
            analysis[f'{interval}_entry_bb_upper'] = entry_data['bb_upper']
            analysis[f'{interval}_entry_bb_lower'] = entry_data['bb_lower']
            analysis[f'{interval}_entry_atr'] = entry_data['atr']
            
            # 判斷趨勢
            if entry_data['ema_7'] > entry_data['ema_20'] > entry_data['ema_50']:
                analysis[f'{interval}_entry_trend'] = 'strong_uptrend'
            elif entry_data['ema_7'] > entry_data['ema_20']:
                analysis[f'{interval}_entry_trend'] = 'uptrend'
            elif entry_data['ema_7'] < entry_data['ema_20'] < entry_data['ema_50']:
                analysis[f'{interval}_entry_trend'] = 'strong_downtrend'
            elif entry_data['ema_7'] < entry_data['ema_20']:
                analysis[f'{interval}_entry_trend'] = 'downtrend'
            else:
                analysis[f'{interval}_entry_trend'] = 'sideways'
            
            # 判斷 MACD 狀態
            if entry_data['macd'] > entry_data['macd_signal'] and entry_data['macd_hist'] > 0:
                analysis[f'{interval}_entry_macd_state'] = 'bullish'
            elif entry_data['macd'] < entry_data['macd_signal'] and entry_data['macd_hist'] < 0:
                analysis[f'{interval}_entry_macd_state'] = 'bearish'
            elif entry_data['macd'] > entry_data['macd_signal']:
                analysis[f'{interval}_entry_macd_state'] = 'golden_cross'
            else:
                analysis[f'{interval}_entry_macd_state'] = 'death_cross'
            
            # 判斷 RSI 狀態
            if entry_data['rsi'] > 70:
                analysis[f'{interval}_entry_rsi_state'] = 'overbought'
            elif entry_data['rsi'] > 60:
                analysis[f'{interval}_entry_rsi_state'] = 'strong'
            elif entry_data['rsi'] > 40:
                analysis[f'{interval}_entry_rsi_state'] = 'neutral'
            elif entry_data['rsi'] > 30:
                analysis[f'{interval}_entry_rsi_state'] = 'weak'
            else:
                analysis[f'{interval}_entry_rsi_state'] = 'oversold'
            
            # 判斷布林帶位置
            price = entry_data['close']
            if price > entry_data['bb_upper']:
                analysis[f'{interval}_entry_bb_position'] = 'above_upper'
            elif price > (entry_data['bb_upper'] + entry_data['bb_middle']) / 2:
                analysis[f'{interval}_entry_bb_position'] = 'upper_half'
            elif price > entry_data['bb_lower']:
                analysis[f'{interval}_entry_bb_position'] = 'lower_half'
            else:
                analysis[f'{interval}_entry_bb_position'] = 'below_lower'
            
            # 出場時的指標
            analysis[f'{interval}_exit_price'] = exit_data['close']
            analysis[f'{interval}_exit_rsi'] = exit_data['rsi']
            analysis[f'{interval}_exit_macd'] = exit_data['macd']
            
            # 價格變化
            price_change = (exit_data['close'] - entry_data['close']) / entry_data['close'] * 100
            analysis[f'{interval}_price_change_pct'] = price_change
        
        results.append(analysis)
        
        if idx % 10 == 0:
            print(f"  已分析 {idx}/{len(trades)} 筆交易...")
    
    print(f"  ✅ 完成，共分析 {len(results)} 筆交易")
    
    return pd.DataFrame(results)

def main():
    print("=" * 80)
    print("從 Binance 獲取完整的 1m/3m/5m 歷史數據")
    print("=" * 80)
    print()
    
    # 讀取交易記錄，確定時間範圍
    trades_file = 'data/review_history/quality_scores.json'
    
    if not Path(trades_file).exists():
        print(f"❌ 找不到交易記錄: {trades_file}")
        return
    
    with open(trades_file, 'r') as f:
        trades = json.load(f)
    
    # 找出最早和最晚的交易時間
    trade_times = [pd.to_datetime(t['open_time']) for t in trades]
    earliest_trade = min(trade_times)
    latest_trade = max(trade_times)
    
    print(f"交易時間範圍:")
    print(f"  最早: {earliest_trade}")
    print(f"  最晚: {latest_trade}")
    print(f"  總交易數: {len(trades)}")
    print()
    
    # 設定數據獲取範圍（交易前後各延長 1 天，確保有足夠數據計算技術指標）
    start_time = earliest_trade - timedelta(days=1)
    end_time = latest_trade + timedelta(days=1)
    
    print(f"數據獲取範圍:")
    print(f"  開始: {start_time.strftime('%Y-%m-%d %H:%M')}")
    print(f"  結束: {end_time.strftime('%Y-%m-%d %H:%M')}")
    print(f"  天數: {(end_time - start_time).days} 天")
    print()
    
    # 設定參數
    symbols = ['ETHUSDT']  # Binance 格式
    intervals = ['1m', '3m', '5m']
    
    # 獲取數據
    market_data = {}
    
    for symbol in symbols:
        print(f"【{symbol}】")
        market_data[symbol] = {}
        
        for interval in intervals:
            df = fetch_binance_klines(symbol, interval, start_time, end_time)
            
            if not df.empty:
                market_data[symbol][interval] = df
                
                # 保存原始數據
                output_dir = Path('market_data_binance')
                output_dir.mkdir(exist_ok=True)
                
                filename = output_dir / f"{symbol}_{interval}_full.csv"
                df.to_csv(filename, index=False)
                print(f"    💾 已保存: {filename}")
                print(f"    📊 覆蓋時間: {df['timestamp'].min()} 至 {df['timestamp'].max()}")
            else:
                print(f"    ⚠️  無數據")
        
        print()
    
    # 分析交易進出場點
    print("=" * 80)
    print("分析交易進出場點")
    print("=" * 80)
    
    analysis_df = analyze_trade_entry_exit(trades_file, market_data)
    
    if not analysis_df.empty:
        # 保存分析結果
        output_file = 'analysis_results/entry_exit_analysis_binance_full.csv'
        analysis_df.to_csv(output_file, index=False)
        print(f"\n✅ 分析完成，已保存: {output_file}")
        
        # 顯示統計
        print()
        print("=" * 80)
        print("進場點技術指標統計")
        print("=" * 80)
        
        for interval in intervals:
            trend_col = f'{interval}_entry_trend'
            macd_col = f'{interval}_entry_macd_state'
            rsi_col = f'{interval}_entry_rsi_state'
            
            if trend_col not in analysis_df.columns:
                continue
            
            print(f"\n【{interval} 週期】")
            
            # 趨勢分布
            print("  趨勢分布:")
            trend_counts = analysis_df[trend_col].value_counts()
            for trend, count in trend_counts.items():
                subset = analysis_df[analysis_df[trend_col] == trend]
                pnl_avg = subset['pnl'].mean()
                win_rate = (subset['pnl'] > 0).sum() / len(subset) * 100
                print(f"    {trend}: {count} 筆，平均盈虧 {pnl_avg:.2f} USDT，勝率 {win_rate:.1f}%")
            
            # MACD 狀態
            print("  MACD 狀態:")
            macd_counts = analysis_df[macd_col].value_counts()
            for state, count in macd_counts.items():
                subset = analysis_df[analysis_df[macd_col] == state]
                pnl_avg = subset['pnl'].mean()
                win_rate = (subset['pnl'] > 0).sum() / len(subset) * 100
                print(f"    {state}: {count} 筆，平均盈虧 {pnl_avg:.2f} USDT，勝率 {win_rate:.1f}%")
            
            # RSI 狀態
            print("  RSI 狀態:")
            rsi_counts = analysis_df[rsi_col].value_counts()
            for state, count in rsi_counts.items():
                subset = analysis_df[analysis_df[rsi_col] == state]
                pnl_avg = subset['pnl'].mean()
                win_rate = (subset['pnl'] > 0).sum() / len(subset) * 100
                print(f"    {state}: {count} 筆，平均盈虧 {pnl_avg:.2f} USDT，勝率 {win_rate:.1f}%")
    else:
        print("⚠️  無法分析交易數據")
    
    print()
    print("=" * 80)
    print("完成！")
    print("=" * 80)
    print()
    print("📁 數據保存位置:")
    print("  - 原始 K線數據: market_data_binance/")
    print("  - 進出場分析: analysis_results/entry_exit_analysis_binance_full.csv")
    print()
    print("💡 下一步:")
    print("  1. 查看 CSV 文件，分析進出場點的技術指標")
    print("  2. 找出虧損交易的共同特徵")
    print("  3. 對比正常交易和失控交易的技術指標差異")
    print("  4. 運行: python3 深度分析進出場指標.py")

if __name__ == "__main__":
    main()
