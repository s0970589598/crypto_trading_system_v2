#!/usr/bin/env python3
"""
獲取 1m/3m/5m 歷史數據並分析進出場點的技術指標
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
    
    return df

def fetch_bingx_klines(symbol, interval, start_time, end_time):
    """
    從 BingX API 獲取 K線數據
    
    限制：
    - 單次最多返回 1440 根 K線
    - 需要分批獲取
    """
    base_url = "https://open-api.bingx.com"
    endpoint = "/openApi/swap/v2/quote/klines"
    
    all_klines = []
    current_start = start_time
    
    print(f"  開始獲取 {symbol} {interval} 數據...")
    
    while current_start < end_time:
        url = f"{base_url}{endpoint}"
        params = {
            'symbol': symbol,
            'interval': interval,
            'startTime': int(current_start.timestamp() * 1000),
            'endTime': int(end_time.timestamp() * 1000),
            'limit': 1440  # BingX 最大限制
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('code') != 0:
                print(f"    ❌ API 錯誤: {data.get('msg')}")
                break
            
            klines = data.get('data', [])
            
            if not klines:
                break
            
            all_klines.extend(klines)
            
            # 更新起始時間
            last_time = klines[-1]['time']
            current_start = datetime.fromtimestamp(last_time / 1000) + timedelta(seconds=1)
            
            print(f"    已獲取 {len(all_klines)} 根 K線...", end='\r')
            
            # 避免 API 限流
            time.sleep(0.5)
            
        except Exception as e:
            print(f"    ❌ 異常: {e}")
            break
    
    print(f"    ✅ 完成，共 {len(all_klines)} 根 K線")
    
    if not all_klines:
        return pd.DataFrame()
    
    # 轉換為 DataFrame
    df = pd.DataFrame(all_klines)
    df['timestamp'] = pd.to_datetime(df['time'], unit='ms')
    
    # 重命名欄位
    df = df.rename(columns={
        'open': 'open',
        'high': 'high',
        'low': 'low',
        'close': 'close',
        'volume': 'volume'
    })
    
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
    
    for trade in trades:
        trade_id = trade.get('trade_id')
        symbol = trade.get('symbol', '').replace('-', '')  # ETH-USDT -> ETHUSDT
        open_time = pd.to_datetime(trade.get('open_time'))
        close_time = pd.to_datetime(trade.get('close_time'))
        entry_price = trade.get('entry_price')
        exit_price = trade.get('exit_price')
        pnl = trade.get('pnl')
        
        if symbol not in market_data:
            continue
        
        analysis = {
            'trade_id': trade_id,
            'symbol': symbol,
            'open_time': open_time,
            'close_time': close_time,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'pnl': pnl,
            'holding_minutes': (close_time - open_time).total_seconds() / 60
        }
        
        # 分析每個時間週期
        for interval, df in market_data[symbol].items():
            # 找到進場時的 K線
            entry_candle = df[df['timestamp'] <= open_time].tail(1)
            if entry_candle.empty:
                continue
            
            entry_data = entry_candle.iloc[0]
            
            # 找到出場時的 K線
            exit_candle = df[df['timestamp'] <= close_time].tail(1)
            if exit_candle.empty:
                continue
            
            exit_data = exit_candle.iloc[0]
            
            # 記錄技術指標
            analysis[f'{interval}_entry_price'] = entry_data['close']
            analysis[f'{interval}_entry_ema7'] = entry_data['ema_7']
            analysis[f'{interval}_entry_ema20'] = entry_data['ema_20']
            analysis[f'{interval}_entry_rsi'] = entry_data['rsi']
            analysis[f'{interval}_entry_macd'] = entry_data['macd']
            analysis[f'{interval}_entry_macd_signal'] = entry_data['macd_signal']
            
            # 判斷趨勢
            if entry_data['ema_7'] > entry_data['ema_20']:
                analysis[f'{interval}_entry_trend'] = 'uptrend'
            else:
                analysis[f'{interval}_entry_trend'] = 'downtrend'
            
            # 判斷 MACD 狀態
            if entry_data['macd'] > entry_data['macd_signal']:
                analysis[f'{interval}_entry_macd_state'] = 'bullish'
            else:
                analysis[f'{interval}_entry_macd_state'] = 'bearish'
            
            # 判斷 RSI 狀態
            if entry_data['rsi'] > 70:
                analysis[f'{interval}_entry_rsi_state'] = 'overbought'
            elif entry_data['rsi'] < 30:
                analysis[f'{interval}_entry_rsi_state'] = 'oversold'
            else:
                analysis[f'{interval}_entry_rsi_state'] = 'neutral'
            
            # 出場時的指標
            analysis[f'{interval}_exit_price'] = exit_data['close']
            analysis[f'{interval}_exit_rsi'] = exit_data['rsi']
            analysis[f'{interval}_exit_macd'] = exit_data['macd']
        
        results.append(analysis)
    
    return pd.DataFrame(results)

def main():
    print("=" * 80)
    print("獲取 1m/3m/5m 歷史數據並分析進出場點")
    print("=" * 80)
    print()
    
    # 設定參數
    symbols = ['ETH-USDT']  # BingX 格式
    intervals = ['1m', '3m', '5m']
    
    # 時間範圍：最近 7 天（根據你的交易記錄調整）
    end_time = datetime.now()
    start_time = end_time - timedelta(days=7)
    
    print(f"時間範圍: {start_time.strftime('%Y-%m-%d %H:%M')} 至 {end_time.strftime('%Y-%m-%d %H:%M')}")
    print(f"交易對: {', '.join(symbols)}")
    print(f"週期: {', '.join(intervals)}")
    print()
    
    # 獲取數據
    market_data = {}
    
    for symbol in symbols:
        print(f"【{symbol}】")
        market_data[symbol] = {}
        
        for interval in intervals:
            df = fetch_bingx_klines(symbol, interval, start_time, end_time)
            
            if not df.empty:
                market_data[symbol][interval] = df
                
                # 保存原始數據
                output_dir = Path('market_data_short_timeframe')
                output_dir.mkdir(exist_ok=True)
                
                filename = output_dir / f"{symbol.replace('-', '')}_{interval}.csv"
                df.to_csv(filename, index=False)
                print(f"    💾 已保存: {filename}")
            else:
                print(f"    ⚠️  無數據")
        
        print()
    
    # 分析交易進出場點
    print("=" * 80)
    print("分析交易進出場點")
    print("=" * 80)
    print()
    
    trades_file = 'data/review_history/quality_scores.json'
    
    if Path(trades_file).exists():
        print(f"讀取交易記錄: {trades_file}")
        
        # 轉換 symbol 格式
        market_data_converted = {}
        for symbol, data in market_data.items():
            converted_symbol = symbol.replace('-', '')
            market_data_converted[converted_symbol] = data
        
        analysis_df = analyze_trade_entry_exit(trades_file, market_data_converted)
        
        if not analysis_df.empty:
            # 保存分析結果
            output_file = 'analysis_results/entry_exit_analysis_short_timeframe.csv'
            analysis_df.to_csv(output_file, index=False)
            print(f"✅ 分析完成，已保存: {output_file}")
            print(f"   共分析 {len(analysis_df)} 筆交易")
            
            # 顯示統計
            print()
            print("=" * 80)
            print("進場點技術指標統計")
            print("=" * 80)
            
            for interval in intervals:
                trend_col = f'{interval}_entry_trend'
                macd_col = f'{interval}_entry_macd_state'
                rsi_col = f'{interval}_entry_rsi_state'
                
                if trend_col in analysis_df.columns:
                    print(f"\n【{interval} 週期】")
                    
                    # 趨勢分布
                    print("  趨勢分布:")
                    trend_counts = analysis_df[trend_col].value_counts()
                    for trend, count in trend_counts.items():
                        pnl_avg = analysis_df[analysis_df[trend_col] == trend]['pnl'].mean()
                        print(f"    {trend}: {count} 筆，平均盈虧 {pnl_avg:.2f} USDT")
                    
                    # MACD 狀態
                    print("  MACD 狀態:")
                    macd_counts = analysis_df[macd_col].value_counts()
                    for state, count in macd_counts.items():
                        pnl_avg = analysis_df[analysis_df[macd_col] == state]['pnl'].mean()
                        print(f"    {state}: {count} 筆，平均盈虧 {pnl_avg:.2f} USDT")
                    
                    # RSI 狀態
                    print("  RSI 狀態:")
                    rsi_counts = analysis_df[rsi_col].value_counts()
                    for state, count in rsi_counts.items():
                        pnl_avg = analysis_df[analysis_df[rsi_col] == state]['pnl'].mean()
                        print(f"    {state}: {count} 筆，平均盈虧 {pnl_avg:.2f} USDT")
        else:
            print("⚠️  無法分析交易數據")
    else:
        print(f"⚠️  找不到交易記錄: {trades_file}")
    
    print()
    print("=" * 80)
    print("完成！")
    print("=" * 80)
    print()
    print("📁 數據保存位置:")
    print("  - 原始 K線數據: market_data_short_timeframe/")
    print("  - 進出場分析: analysis_results/entry_exit_analysis_short_timeframe.csv")
    print()
    print("💡 下一步:")
    print("  1. 查看 CSV 文件，分析進出場點的技術指標")
    print("  2. 找出虧損交易的共同特徵")
    print("  3. 對比正常交易和失控交易的技術指標差異")

if __name__ == "__main__":
    main()
