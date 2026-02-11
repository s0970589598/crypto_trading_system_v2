#!/bin/bash

echo "================================"
echo "清理舊數據目錄"
echo "================================"
echo ""

# 檢查是否存在舊的數據目錄
if [ -d "market_data_binance" ]; then
    echo "發現舊的數據目錄: market_data_binance/"
    echo ""
    
    # 列出文件
    echo "📁 目錄內容:"
    ls -lh market_data_binance/
    echo ""
    
    # 詢問是否刪除
    read -p "是否刪除此目錄？(y/n): " confirm
    
    if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
        rm -rf market_data_binance/
        echo "✅ 已刪除 market_data_binance/"
    else
        echo "⏭️  跳過刪除"
    fi
else
    echo "✅ 沒有發現舊的數據目錄"
fi

echo ""

# 檢查是否存在舊的短週期數據目錄
if [ -d "market_data_short_timeframe" ]; then
    echo "發現舊的數據目錄: market_data_short_timeframe/"
    echo ""
    
    # 列出文件
    echo "📁 目錄內容:"
    ls -lh market_data_short_timeframe/
    echo ""
    
    # 詢問是否刪除
    read -p "是否刪除此目錄？(y/n): " confirm
    
    if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
        rm -rf market_data_short_timeframe/
        echo "✅ 已刪除 market_data_short_timeframe/"
    else
        echo "⏭️  跳過刪除"
    fi
else
    echo "✅ 沒有發現舊的數據目錄"
fi

echo ""
echo "================================"
echo "完成！"
echo "================================"
echo ""
echo "💡 說明："
echo "  - 所有數據現在統一保存在項目根目錄"
echo "  - 命名格式：market_data_SYMBOL_INTERVAL.csv"
echo "  - 例如：market_data_ETHUSDT_1m.csv"
echo ""
