#!/usr/bin/env python3
"""
快速更新市場數據

更新所有現有的市場數據文件到最新
"""

import sys
import os
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
    print("快速更新市場數據")
    print("="*70)
    print()
    
    # 掃描現有數據文件
    data_files = list(Path('.').glob('market_data_*.csv'))
    
    if not data_files:
        print("⚠️ 未找到任何市場數據文件")
        print("請先運行：python3 快速重新下載_關鍵時區.py")
        return
    
    print(f"找到 {len(data_files)} 個數據文件")
    print()
    
    # 解析文件名
    files_to_update = []
    for file in data_files:
        parts = file.name.replace('market_data_', '').replace('.csv', '').split('_')
        if len(parts) >= 2:
            symbol = parts[0]
            interval = parts[1]
            files_to_update.append((symbol, interval, file))
    
    # 創建分析器
    analyzer = MarketAnalyzer()
    
    # 更新數據
    success_count = 0
    failed_count = 0
    
    for i, (symbol, interval, file) in enumerate(files_to_update, 1):
        print(f"[{i}/{len(files_to_update)}] 更新 {symbol} {interval}...", end=' ')
        
        try:
            # 重新載入數據（會自動更新）
            # 臨時降低過期時間閾值以強制更新
            original_expiry = analyzer.cache_expiry_hours
            analyzer.cache_expiry_hours = 0  # 強制更新
            
            df = analyzer.load_market_data(symbol, interval)
            
            analyzer.cache_expiry_hours = original_expiry  # 恢復原值
            
            if df is not None and len(df) > 0:
                last_time = df['timestamp'].max()
                print(f"✅ 成功（最新：{last_time}）")
                success_count += 1
            else:
                print(f"❌ 失敗")
                failed_count += 1
        
        except Exception as e:
            print(f"❌ 錯誤：{e}")
            failed_count += 1
    
    print()
    print("="*70)
    print(f"更新完成！成功：{success_count}，失敗：{failed_count}")
    print("="*70)
    print()
    
    if success_count > 0:
        print("✅ 數據已更新到最新")
        print("💡 現在可以使用實時市場分析功能了")
    
    if failed_count > 0:
        print(f"⚠️ {failed_count} 個文件更新失敗，請檢查錯誤信息")

if __name__ == "__main__":
    main()
