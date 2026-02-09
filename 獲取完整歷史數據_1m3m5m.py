#!/usr/bin/env python3
"""
獲取完整的 1m/3m/5m 歷史數據（覆蓋所有交易時間）
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

def fetch_bingx_klines_batch(symbol, interval, start_time, end_time):
    """分批獲取 BingX K線數據"""
    base_url = "https://open-api.bingx.com"
    endpoint = "/openApi/swap/v2/quote/klines"
    
    all_klines = []
    current_start = start_time
    batch_num = 0
    
    print(f"  開始獲取 {symbol} {interval} 數據...")
    print(f"  時間範圍: {start_time.strftime('%Y-%m-%d %H:%M')} 至 {end_time.strftime('%Y-%m-%d %H:%M')}")
    
    while current_start < end_time:
        batch_num += 1
        url = f"{base_url}{endpoint}"
        params = {
            'symbol': symbol,
            'interval': interval,
            'startTime': int(current_start.timestamp() * 1000),
            'endTime': int(end_time.timestamp() * 1000),
            'limit': 1440
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
            
            print(f"    批次 {batch_num}: 已獲取 {len(all_klines)} 根 K線...", end='\r')
            
            # 避免 API 限流
            time.sleep(0.5)
            
        except Exception as e:
            print(f"    ❌ 異常: {e}")
            break
    
    print(f"    ✅ 完成，共 {len(all_klines)} 根 K線（{batch_num} 批次）")
    
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

def main():
    print("=" * 80)
    print("獲取完整的 1m/3m/5m 歷史數據")
    print("=" * 80)
    print()
    
    # 讀取交易記錄，確定時間範圍
    trades_file = 'data/review_history/quality_scores.json'
    with open(trades_file, 'r') as f:
        trades = json.load(f)
    
    # 找出最早和最晚的交易時間
    trade_times = [pd.to_datetime(t['open_time']) for t in trades]
    earliest_trade = min(trade_times)
    latest_trade = max(trade_times)
    
    print(f"交易時間範圍:")
    print(f"  最早: {earliest_trade}")
    print(f"  最晚: {latest_trade}")
    print()
    
    # 設定數據獲取範圍（交易前後各延長 1 天）
    start_time = earliest_trade - timedelta(days=1)
    end_time = latest_trade + timedelta(days=1)
    
    print(f"數據獲取範圍:")
    print(f"  開始: {start_time.strftime('%Y-%m-%d %H:%M')}")
    print(f"  結束: {end_time.strftime('%Y-%m-%d %H:%M')}")
    print(f"  天數: {(end_time - start_time).days} 天")
    print()
    
    # 設定參數
    symbols = ['ETH-USDT']
    intervals = ['1m', '3m', '5m']
    
    # 獲取數據
    market_data = {}
    
    for symbol in symbols:
        print(f"【{symbol}】")
        market_data[symbol] = {}
        
        for interval in intervals:
            df = fetch_bingx_klines_batch(symbol, interval, start_time, end_time)
            
            if not df.empty:
                market_data[symbol][interval] = df
                
                # 保存原始數據
                output_dir = Path('market_data_short_timeframe')
                output_dir.mkdir(exist_ok=True)
                
                filename = output_dir / f"{symbol.replace('-', '')}_{interval}_full.csv"
                df.to_csv(filename, index=False)
                print(f"    💾 已保存: {filename}")
                print(f"    📊 覆蓋時間: {df['timestamp'].min()} 至 {df['timestamp'].max()}")
            else:
                print(f"    ⚠️  無數據")
        
        print()
    
    print("=" * 80)
    print("完成！")
    print("=" * 80)
    print()
    print("📁 數據已保存到: market_data_short_timeframe/")
    print()
    print("💡 下一步:")
    print("  運行分析腳本: python3 分析進出場技術指標.py")

if __name__ == "__main__":
    main()
