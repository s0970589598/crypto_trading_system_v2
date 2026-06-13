#!/bin/bash

echo "================================"
echo "數據獲取腳本整理"
echo "================================"
echo ""

# 1. 重命名主要腳本
echo "1️⃣  重命名主要腳本..."
if [ -f "fetch_market_data.py" ]; then
    mv fetch_market_data.py fetch_long_timeframe_data.py
    echo "  ✅ fetch_market_data.py → fetch_long_timeframe_data.py"
fi

if [ -f "從Binance獲取完整歷史數據.py" ]; then
    mv 從Binance獲取完整歷史數據.py fetch_short_timeframe_data.py
    echo "  ✅ 從Binance獲取完整歷史數據.py → fetch_short_timeframe_data.py"
fi

echo ""

# 2. 創建 tools 目錄
echo "2️⃣  創建 tools 目錄..."
mkdir -p tools
echo "  ✅ tools/ 目錄已創建"
echo ""

# 3. 移動測試腳本
echo "3️⃣  移動測試腳本到 tools/..."
if [ -f "測試BingX_API限制.py" ]; then
    mv 測試BingX_API限制.py tools/test_bingx_api.py
    echo "  ✅ 測試BingX_API限制.py → tools/test_bingx_api.py"
fi

if [ -f "測試批次獲取.py" ]; then
    mv 測試批次獲取.py tools/test_batch_fetch.py
    echo "  ✅ 測試批次獲取.py → tools/test_batch_fetch.py"
fi

echo ""

# 4. 刪除重複腳本
echo "4️⃣  刪除重複腳本..."
if [ -f "獲取短週期歷史數據.py" ]; then
    rm 獲取短週期歷史數據.py
    echo "  ✅ 已刪除：獲取短週期歷史數據.py"
fi

if [ -f "獲取完整歷史數據_1m3m5m.py" ]; then
    rm 獲取完整歷史數據_1m3m5m.py
    echo "  ✅ 已刪除：獲取完整歷史數據_1m3m5m.py"
fi

echo ""

# 5. 顯示最終結構
echo "================================"
echo "✅ 整理完成！"
echo "================================"
echo ""
echo "📁 最終結構："
echo ""
echo "數據獲取腳本："
echo "  ├── fetch_long_timeframe_data.py    # 長週期 (15m, 1h, 4h, 1d)"
echo "  ├── fetch_short_timeframe_data.py   # 短週期 (1m, 3m, 5m)"
echo "  └── tools/"
echo "      ├── test_bingx_api.py           # BingX API 測試"
echo "      └── test_batch_fetch.py         # 批次獲取測試"
echo ""
echo "💡 使用方式："
echo ""
echo "  # 獲取長週期數據（用於回測）"
echo "  python3 fetch_long_timeframe_data.py"
echo ""
echo "  # 獲取短週期數據（用於進出場分析）"
echo "  python3 fetch_short_timeframe_data.py"
echo ""
echo "  # 測試 API"
echo "  python3 tools/test_bingx_api.py"
echo ""
