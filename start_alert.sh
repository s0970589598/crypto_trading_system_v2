#!/bin/bash
# 快速啟動交易提醒系統

echo "=================================="
echo "交易提醒系統 - 快速啟動"
echo "=================================="

# 檢查 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到 Python3，請先安裝"
    exit 1
fi

# 檢查依賴
echo "檢查依賴..."
python3 -c "import requests, pandas, numpy" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️ 缺少依賴，正在安裝..."
    pip3 install requests pandas numpy
fi

# 檢查 .env 文件
if [ ! -f .env ]; then
    echo "❌ 未找到 .env 配置文件"
    exit 1
fi

echo "✅ 配置檢查完成"
echo ""

# 啟動系統
python3 trading_alert_system.py
