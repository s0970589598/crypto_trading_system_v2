#!/usr/bin/env python3
"""
測試 BingX API 的歷史數據限制
"""

import requests
import json
from datetime import datetime, timedelta

def test_bingx_kline_limits():
    """
    測試 BingX API 的 K線數據限制
    """
    
    print("=" * 80)
    print("BingX API K線數據限制測試")
    print("=" * 80)
    print()
    
    # BingX API endpoint
    base_url = "https://open-api.bingx.com"
    kline_endpoint = "/openApi/swap/v2/quote/klines"
    
    # 測試參數
    symbol = "ETH-USDT"
    intervals = ['1m', '3m', '5m', '15m', '1h', '4h', '1d']
    
    print("📊 測試不同時間週期的數據限制")
    print("-" * 80)
    
    for interval in intervals:
        print(f"\n【{interval} 週期】")
        
        # 測試 1: 最大 limit 參數
        print("  測試 1: 最大 limit 參數")
        for limit in [100, 500, 1000, 1440, 2000]:
            url = f"{base_url}{kline_endpoint}"
            params = {
                'symbol': symbol,
                'interval': interval,
                'limit': limit
            }
            
            try:
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('code') == 0:
                        klines = data.get('data', [])
                        print(f"    limit={limit}: ✅ 成功，返回 {len(klines)} 根 K線")
                        if len(klines) < limit:
                            print(f"      ⚠️  實際返回少於請求數量")
                    else:
                        print(f"    limit={limit}: ❌ 錯誤 - {data.get('msg')}")
                        break
                else:
                    print(f"    limit={limit}: ❌ HTTP {response.status_code}")
                    break
            except Exception as e:
                print(f"    limit={limit}: ❌ 異常 - {e}")
                break
        
        # 測試 2: 時間範圍限制
        print(f"\n  測試 2: 歷史數據時間範圍")
        now = datetime.now()
        time_ranges = [
            ("1 天前", now - timedelta(days=1)),
            ("7 天前", now - timedelta(days=7)),
            ("30 天前", now - timedelta(days=30)),
            ("90 天前", now - timedelta(days=90)),
            ("180 天前", now - timedelta(days=180)),
            ("365 天前", now - timedelta(days=365)),
        ]
        
        for label, start_time in time_ranges:
            url = f"{base_url}{kline_endpoint}"
            params = {
                'symbol': symbol,
                'interval': interval,
                'startTime': int(start_time.timestamp() * 1000),
                'endTime': int(now.timestamp() * 1000),
                'limit': 1000
            }
            
            try:
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('code') == 0:
                        klines = data.get('data', [])
                        if klines:
                            first_time = datetime.fromtimestamp(klines[0]['time'] / 1000)
                            print(f"    {label}: ✅ 成功，返回 {len(klines)} 根，最早 {first_time.strftime('%Y-%m-%d %H:%M')}")
                        else:
                            print(f"    {label}: ⚠️  無數據")
                    else:
                        print(f"    {label}: ❌ 錯誤 - {data.get('msg')}")
                else:
                    print(f"    {label}: ❌ HTTP {response.status_code}")
            except Exception as e:
                print(f"    {label}: ❌ 異常 - {e}")
    
    print("\n" + "=" * 80)
    print("📝 BingX API 文檔參考")
    print("=" * 80)
    print("官方文檔: https://bingx-api.github.io/docs/")
    print("K線接口: /openApi/swap/v2/quote/klines")
    print()
    print("參數說明:")
    print("  - symbol: 交易對 (例如: ETH-USDT)")
    print("  - interval: 時間週期 (1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 12h, 1d, 3d, 1w, 1M)")
    print("  - limit: 返回數量 (默認 500, 最大 1440)")
    print("  - startTime: 開始時間 (毫秒時間戳)")
    print("  - endTime: 結束時間 (毫秒時間戳)")
    print()
    print("限制說明:")
    print("  - 單次請求最多返回 1440 根 K線")
    print("  - 需要分批獲取歷史數據")
    print("  - 建議請求間隔 0.5-1 秒，避免觸發限流")
    print("=" * 80)

if __name__ == "__main__":
    test_bingx_kline_limits()
