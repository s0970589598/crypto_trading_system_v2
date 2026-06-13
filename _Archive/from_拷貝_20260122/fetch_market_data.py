#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
獲取 BTC/ETH 歷史價格數據並進行多週期分析
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests
import time
import json

def fetch_binance_klines(symbol, interval, start_time, end_time):
    """
    從 Binance API 獲取 K 線數據
    interval: 1m, 5m, 15m, 1h, 4h, 1d
    """
    url = "https://api.binance.com/api/v3/klines"
    
    all_klines = []
    current_start = start_time
    
    while current_start < end_time:
        params = {
            'symbol': symbol,
            'interval': interval,
            'startTime': int(current_start.timestamp() * 1000),
            'endTime': int(end_time.timestamp() * 1000),
            'limit': 1000
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            klines = response.json()
            
            if not klines:
                break
                
            all_klines.extend(klines)
            
            # 更新起始時間為最後一根 K 線的時間
            last_time = klines[-1][0]
            current_start = datetime.fromtimestamp(last_time / 1000) + timedelta(seconds=1)
            
            # 避免 API 限制
            time.sleep(0.5)
            
        except Exception as e:
            print(f"Error fetching {symbol} {interval}: {e}")
            break
    
    # 轉換為 DataFrame
    df = pd.DataFrame(all_klines, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_volume', 'trades', 'taker_buy_base',
        'taker_buy_quote', 'ignore'
    ])
    
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df['close_time'] = pd.to_datetime(df['close_time'], unit='ms')
    
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)
    
    return df

# 設定時間範圍
start_date = datetime(2025, 10, 24)
end_date = datetime(2026, 1, 21)

print("=" * 100)
print("開始獲取歷史價格數據")
print("=" * 100)
print(f"時間範圍：{start_date.date()} 至 {end_date.date()}")
print(f"交易對：BTCUSDT, ETHUSDT")
print(f"週期：15m, 1h, 4h, 1d")
print("=" * 100)

# 獲取數據
intervals = ['15m', '1h', '4h', '1d']
symbols = ['BTCUSDT', 'ETHUSDT']

market_data = {}

for symbol in symbols:
    print(f"\n正在獲取 {symbol} 數據...")
    market_data[symbol] = {}
    
    for interval in intervals:
        print(f"  - {interval} K 線...", end='')
        df = fetch_binance_klines(symbol, interval, start_date, end_date)
        market_data[symbol][interval] = df
        print(f" 完成 ({len(df)} 根 K 線)")

# 保存數據
print("\n保存數據...")
for symbol in symbols:
    for interval in intervals:
        filename = f"market_data_{symbol}_{interval}.csv"
        market_data[symbol][interval].to_csv(filename, index=False)
        print(f"  - {filename}")

print("\n數據獲取完成！")
print("=" * 100)
