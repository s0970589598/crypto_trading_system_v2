#!/usr/bin/env python3
"""
測試 BingX API 是否支援批次獲取歷史數據
"""

import requests
from datetime import datetime, timedelta
import time

def test_batch_fetch():
    """測試批次獲取"""
    
    base_url = "https://open-api.bingx.com"
    endpoint = "/openApi/swap/v2/quote/klines"
    
    symbol = "ETH-USDT"
    interval = "1m"
    
    # 測試不同的時間範圍
    now = datetime.now()
    
    test_cases = [
        ("最近 1 天", now - timedelta(days=1), now),
        ("最近 3 天", now - timedelta(days=3), now),
        ("最近 7 天", now - timedelta(days=7), now),
        ("最近 14 天", now - timedelta(days=14), now),
        ("7-14 天前", now - timedelta(days=14), now - timedelta(days=7)),
        ("14-21 天前", now - timedelta(days=21), now - timedelta(days=14)),
    ]
    
    print("=" * 80)
    print("測試 BingX API 批次獲取能力")
    print("=" * 80)
    print()
    
    for label, start_time, end_time in test_cases:
        print(f"【{label}】")
        print(f"  請求時間: {start_time.strftime('%Y-%m-%d %H:%M')} 至 {end_time.strftime('%Y-%m-%d %H:%M')}")
        
        url = f"{base_url}{endpoint}"
        params = {
            'symbol': symbol,
            'interval': interval,
            'startTime': int(start_time.timestamp() * 1000),
            'endTime': int(end_time.timestamp() * 1000),
            'limit': 1440
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if data.get('code') == 0:
                klines = data.get('data', [])
                
                if klines:
                    first_time = datetime.fromtimestamp(klines[0]['time'] / 1000)
                    last_time = datetime.fromtimestamp(klines[-1]['time'] / 1000)
                    
                    print(f"  返回數量: {len(klines)} 根")
                    print(f"  實際時間: {first_time.strftime('%Y-%m-%d %H:%M')} 至 {last_time.strftime('%Y-%m-%d %H:%M')}")
                    
                    # 檢查是否返回了請求的時間範圍
                    if first_time < start_time + timedelta(hours=1):
                        print(f"  ✅ 返回了請求的起始時間附近的數據")
                    else:
                        print(f"  ❌ 沒有返回請求的起始時間數據")
                        print(f"     請求: {start_time.strftime('%Y-%m-%d %H:%M')}")
                        print(f"     實際: {first_time.strftime('%Y-%m-%d %H:%M')}")
                        print(f"     差距: {(first_time - start_time).days} 天")
                else:
                    print(f"  ⚠️  無數據")
            else:
                print(f"  ❌ 錯誤: {data.get('msg')}")
        
        except Exception as e:
            print(f"  ❌ 異常: {e}")
        
        print()
        time.sleep(0.5)
    
    print("=" * 80)
    print("結論")
    print("=" * 80)
    print()
    print("如果所有測試都返回「最近的數據」，說明 BingX API 不支援獲取歷史數據。")
    print("如果能返回「請求的起始時間附近的數據」，說明可以批次獲取。")

if __name__ == "__main__":
    test_batch_fetch()
