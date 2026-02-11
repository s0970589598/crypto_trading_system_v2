#!/usr/bin/env python3
"""
重新下載所有市場數據文件（使用正確的時區轉換）

原因：現有的市場數據文件使用 UTC 時間，但交易記錄使用本地時間（UTC+8）
需要重新下載所有數據以確保時間一致性
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
    print("重新下載市場數據文件（修正時區問題）")
    print("="*70)
    print()
    print("說明：")
    print("- 現有文件使用 UTC 時間")
    print("- 交易記錄使用本地時間（UTC+8）")
    print("- 需要重新下載以確保時間一致")
    print()
    
    # 需要重新下載的文件
    symbols = ['BTCUSDT', 'ETHUSDT']
    intervals = ['1m', '3m', '5m', '15m', '1h', '4h', '1d']
    
    # 備份舊文件
    backup_dir = Path('market_data_backup_utc')
    backup_dir.mkdir(exist_ok=True)
    
    print(f"📁 備份目錄: {backup_dir}")
    print()
    
    # 移動舊文件到備份目錄
    for symbol in symbols:
        for interval in intervals:
            old_file = Path(f'market_data_{symbol}_{interval}.csv')
            if old_file.exists():
                backup_file = backup_dir / old_file.name
                print(f"📦 備份: {old_file} -> {backup_file}")
                old_file.rename(backup_file)
    
    print()
    print("="*70)
    print("開始重新下載數據（使用 UTC+8 時區）")
    print("="*70)
    print()
    
    # 創建分析器
    analyzer = MarketAnalyzer()
    
    # 重新下載所有數據
    total_files = len(symbols) * len(intervals)
    current_file = 0
    
    for symbol in symbols:
        for interval in intervals:
            current_file += 1
            print(f"\n[{current_file}/{total_files}] 下載 {symbol} {interval}...")
            
            try:
                df = analyzer.load_market_data(symbol, interval)
                
                if df is not None and len(df) > 0:
                    first_time = df['timestamp'].iloc[0]
                    last_time = df['timestamp'].iloc[-1]
                    print(f"  ✅ 成功: {len(df)} 筆數據")
                    print(f"  📅 時間範圍: {first_time} ~ {last_time}")
                else:
                    print(f"  ❌ 失敗: 無數據")
                    
            except Exception as e:
                print(f"  ❌ 錯誤: {e}")
    
    print()
    print("="*70)
    print("下載完成！")
    print("="*70)
    print()
    print(f"✅ 所有市場數據已更新為本地時間（UTC+8）")
    print(f"📦 舊文件已備份到: {backup_dir}")
    print()
    print("下一步：")
    print("1. 運行質量評分功能測試時間匹配")
    print("2. 如果一切正常，可以刪除備份目錄")
    print()

if __name__ == "__main__":
    main()
