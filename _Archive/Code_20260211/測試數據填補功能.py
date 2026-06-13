#!/usr/bin/env python3
"""測試數據填補功能"""

import sys
sys.path.insert(0, '.')

from src.analysis.market_analyzer import MarketAnalyzer

def test_detect_missing_gaps():
    """測試檢測缺失功能"""
    print("=" * 60)
    print("測試檢測缺失功能")
    print("=" * 60)
    
    analyzer = MarketAnalyzer()
    
    # 測試 BTCUSDT 1h
    print("\n測試 BTCUSDT 1h:")
    gaps = analyzer.detect_missing_gaps('BTCUSDT', '1h')
    
    if not gaps:
        print("✅ 沒有缺失的K線數據")
    else:
        total_missing = sum(gap['missing_count'] for gap in gaps)
        print(f"⚠️ 發現 {len(gaps)} 個缺失時間段，共 {total_missing} 個缺失K線")
        
        # 顯示前3個
        for i, gap in enumerate(gaps[:3], 1):
            print(f"   {i}. {gap['start_time']} 至 {gap['end_time']} ({gap['missing_count']} 個)")
    
    print("\n" + "=" * 60)
    print("測試完成")
    print("=" * 60)


def test_fill_missing_data():
    """測試填補缺失功能（不實際執行，只顯示會做什麼）"""
    print("\n" + "=" * 60)
    print("測試填補缺失功能（模擬）")
    print("=" * 60)
    
    analyzer = MarketAnalyzer()
    
    # 先檢測
    gaps = analyzer.detect_missing_gaps('BTCUSDT', '1h')
    
    if not gaps:
        print("✅ 沒有缺失數據，無需填補")
    else:
        total_missing = sum(gap['missing_count'] for gap in gaps)
        print(f"\n如果執行 fill_missing_data()，將會：")
        print(f"1. 從 Binance API 獲取 {len(gaps)} 個時間段的數據")
        print(f"2. 填補 {total_missing} 個缺失的K線")
        print(f"3. 保存到 CSV 文件")
        print(f"\n要實際執行，請運行：")
        print(f"   python3 檢測並填補缺失數據.py --fetch")


if __name__ == '__main__':
    test_detect_missing_gaps()
    test_fill_missing_data()
