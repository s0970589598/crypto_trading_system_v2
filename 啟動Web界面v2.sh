#!/bin/bash

echo "=========================================="
echo "🚀 啟動 Web Dashboard v2"
echo "=========================================="
echo ""
echo "新版本特點："
echo "  ✅ 按照 10 大功能分類組織"
echo "  ✅ 更清晰的導航結構"
echo "  ✅ 完整的功能覆蓋"
echo ""
echo "正在啟動..."
echo ""

python3 -m streamlit run web_dashboard_v2.py --server.headless true --server.port 8502

echo ""
echo "=========================================="
echo "✅ Web Dashboard v2 已啟動"
echo "=========================================="
echo ""
echo "訪問地址："
echo "  本地：http://localhost:8502"
echo ""
echo "按 Ctrl+C 停止服務"
echo ""
