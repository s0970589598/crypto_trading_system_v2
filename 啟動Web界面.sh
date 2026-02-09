#!/bin/bash
# 啟動 Web Dashboard

echo "🚀 正在啟動交易系統 Web Dashboard..."
echo ""

# 檢查 streamlit 是否安裝
if ! python3 -c "import streamlit" &> /dev/null; then
    echo "⚠️ Streamlit 未安裝，正在安裝..."
    pip3 install streamlit plotly openpyxl
    echo ""
fi

# 啟動 Web 界面
echo "✅ 啟動 Web 界面..."
echo "📱 瀏覽器會自動打開，或手動訪問："
echo ""
echo "   http://localhost:8501"
echo ""
echo "💡 提示："
echo "   - 使用側邊欄切換不同功能"
echo "   - 按 Ctrl+C 停止服務"
echo "   - 如果瀏覽器沒有自動打開，請手動訪問上面的地址"
echo ""

# 使用 python3 -m streamlit 確保能找到命令
python3 -m streamlit run web_dashboard.py
