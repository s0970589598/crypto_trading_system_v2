#!/usr/bin/env python3
"""
快速重新下載關鍵時區的市場數據（15m, 1h, 4h, 1d）

1m, 3m, 5m 數據量較大，可以稍後下載
先確保主要時區的數據正確
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# 直接導入 MarketAnalyzer
import importlib.util
spec = importlib.util.spec_from_file_location("market_analyzer", "src/analysis/market_analyzer.py")
market_analyzer_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(market_analyzer_module)
MarketAnalyzer = market_analyzer_module.MarketAnalyzer

def main():
    print("="*70)
    print("快速重新下載關鍵時區數據（修正時區問題）")
    print("="*70)
    print()
    print("下載時區：15m, 1h, 4h, 1d（跳過 1m, 3m, 5m）")
    print()
    
    # 只下載關鍵時區
    symbols = ['BTCUSDT', 'ETHUSDT']
    intervals = ['15m', '1h', '4h', '1d']  # 跳過 1m, 3m, 5m
    
    # 備份舊文件（如果存在）
    backup_dir = Path('market_data_backup_utc')
    backup_dir.mkdir(exist_ok=True)
    
    for symbol in symbols:
        for interval in intervals:
            old_file = Path(f'market_data_{symbol}_{interval}.csv')
            if old_file.exists():
                backup_file = backup_dir / old_file.name
                if not backup_file.exists():  # 避免重複備份
                    print(f"📦 備份: {old_file.name}")
                    old_file.rename(backup_file)
    
    print()
    print("="*70)
    print("開始下載")
    print("="*70)
    print()
    
    # 創建分析器
    analyzer = MarketAnalyzer()
    
    # 下載數據
    total_files = len(symbols) * len(intervals)
    current_file = 0
    success_count = 0
    
    for symbol in symbols:
        for interval in intervals:
            current_file += 1
            print(f"[{current_file}/{total_files}] 下載 {symbol} {interval}...", end=' ')
            
            try:
                df = analyzer.load_market_data(symbol, interval)
                
                if df is not None and len(df) > 0:
                    first_time = df['timestamp'].iloc[0]
                    last_time = df['timestamp'].iloc[-1]
                    print(f"✅ {len(df)} 筆")
                    print(f"    時間: {last_time}")
                    success_count += 1
                else:
                    print(f"❌ 無數據")
                    
            except Exception as e:
                print(f"❌ 錯誤: {e}")
    
    print()
    print("="*70)
    print(f"完成！成功下載 {success_count}/{total_files} 個文件")
    print("="*70)
    print()
    
    if success_count == total_files:
        print("✅ 所有關鍵時區數據已更新為本地時間（UTC+8）")
        print()
        print("下一步：")
        print("1. 測試質量評分功能")
        print("2. 如果需要 1m/3m/5m 數據，運行：python3 重新下載市場數據_修正時區.py")
    else:
        print(f"⚠️ 部分文件下載失敗，請檢查錯誤信息")

if __name__ == "__main__":
    main()
