#!/usr/bin/env python3
"""測試型態識別 v2.0"""

import sys
import pandas as pd
import numpy as np
from datetime import datetime

sys.path.insert(0, '.')

from src.analysis.pattern_detector import PatternDetector
from src.analysis.market_analyzer import MarketAnalyzer

def test_pattern_detector():
    """測試型態偵測器"""
    print("=" * 60)
    print("測試型態識別 v2.0")
    print("=" * 60)
    
    # 1. 初始化
    detector = PatternDetector()
    print("✅ PatternDetector 初始化成功")
    
    # 2. 創建測試數據
    df = pd.DataFrame({
        'timestamp': pd.date_range('2024-01-01', periods=100, freq='1h'),
        'open': np.random.randn(100).cumsum() + 70000,
        'high': np.random.randn(100).cumsum() + 70200,
        'low': np.random.randn(100).cumsum() + 69800,
        'close': np.random.randn(100).cumsum() + 70000,
        'volume': np.random.rand(100) * 1000 + 500
    })
    
    print(f"✅ 測試數據創建成功：{len(df)} 根K線")
    
    # 3. 測試指標計算
    try:
        df_with_indicators = detector._ensure_indicators(df)
        print(f"✅ 指標計算成功")
        print(f"   欄位：{', '.join(df_with_indicators.columns)}")
    except Exception as e:
        print(f"❌ 指標計算失敗：{e}")
        import traceback
        traceback.print_exc()
        return
    
    # 4. 測試型態偵測
    try:
        patterns = detector.detect_all_patterns(df_with_indicators, -1)
        print(f"✅ 型態偵測成功，發現 {len(patterns)} 個型態")
        
        for pattern in patterns:
            print(f"\n   {pattern.emoji} {pattern.pattern_type.value}")
            print(f"   描述：{pattern.description}")
            print(f"   強度：{pattern.strength:.0f}")
            print(f"   時間：{pattern.timestamp}")
    except Exception as e:
        print(f"❌ 型態偵測失敗：{e}")
        import traceback
        traceback.print_exc()
        return
    
    print("\n" + "=" * 60)
    print("測試完成！")
    print("=" * 60)


def test_with_real_data():
    """使用真實數據測試"""
    print("\n" + "=" * 60)
    print("使用真實數據測試")
    print("=" * 60)
    
    try:
        analyzer = MarketAnalyzer()
        df = analyzer.load_market_data('BTCUSDT', '1h')
        
        if df is None or len(df) == 0:
            print("❌ 無法載入市場數據")
            return
        
        print(f"✅ 載入市場數據成功：{len(df)} 根K線")
        
        # 確保有指標
        if 'ema_12' not in df.columns:
            df = analyzer.calculate_indicators(df)
        
        # 偵測型態
        detector = PatternDetector()
        patterns = detector.detect_all_patterns(df, -1)
        
        print(f"✅ 發現 {len(patterns)} 個型態")
        
        for pattern in patterns:
            print(f"\n   {pattern.emoji} {pattern.pattern_type.value}")
            print(f"   描述：{pattern.description}")
            print(f"   強度：{pattern.strength:.0f}")
            print(f"   價格：${pattern.price:.2f}")
            print(f"   時間：{pattern.timestamp}")
        
    except Exception as e:
        print(f"❌ 測試失敗：{e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    test_pattern_detector()
    test_with_real_data()
