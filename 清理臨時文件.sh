#!/bin/bash

echo "=========================================="
echo "清理臨時文件和備份文件"
echo "=========================================="

# 1. 刪除備份文件
echo ""
echo "1. 刪除數據備份文件..."
rm -f market_data_*.csv.backup
rm -f market_data_*.csv.before_fill
echo "   ✅ 完成"

# 2. 刪除測試腳本
echo ""
echo "2. 刪除測試腳本..."
rm -f 測試*.py
rm -f test_*.py
rm -f 檢查*.py
rm -f 驗證*.py
echo "   ✅ 完成"

# 3. 整理文檔到 docs 目錄
echo ""
echo "3. 整理文檔..."

# 創建文檔目錄
mkdir -p docs/功能說明
mkdir -p docs/更新記錄
mkdir -p docs/快速參考

# 移動功能說明文檔
mv -f K線型態識別功能說明.md docs/功能說明/ 2>/dev/null
mv -f 實時市場分析_K線圖功能說明.md docs/功能說明/ 2>/dev/null
mv -f 數據缺失檢測與修復說明.md docs/功能說明/ 2>/dev/null
mv -f CMT_Level3專業分析功能說明.md docs/功能說明/ 2>/dev/null

# 移動快速參考
mv -f 型態識別快速參考.md docs/快速參考/ 2>/dev/null
mv -f 型態識別_快速開始.md docs/快速參考/ 2>/dev/null
mv -f 新功能快速參考_2026-02-10.md docs/快速參考/ 2>/dev/null
mv -f CMT快速參考.md docs/快速參考/ 2>/dev/null

# 移動更新記錄
mv -f 型態識別功能完成總結.md docs/更新記錄/ 2>/dev/null
mv -f K線圖功能完成總結.md docs/更新記錄/ 2>/dev/null
mv -f 今日功能更新總覽_2026-02-10.md docs/更新記錄/ 2>/dev/null

# 移動視覺化說明
mv -f 型態識別視覺化說明.md docs/功能說明/ 2>/dev/null

# 保留在根目錄的重要文檔
# - README_型態識別.md (主要入口)
# - README.md (項目說明)

echo "   ✅ 完成"

# 4. 刪除舊的說明文檔（已過時）
echo ""
echo "4. 刪除過時的說明文檔..."
rm -f *修復說明.md
rm -f *完成總結.md
rm -f *更新說明.md
rm -f *功能說明.md
rm -f *使用說明.md
rm -f *指南.md
rm -f *總結.md
rm -f *預覽.md
rm -f *確認.md
rm -f *導入*.md
rm -f *問題*.md
echo "   ✅ 完成"

# 5. 顯示保留的文件
echo ""
echo "=========================================="
echo "保留的重要文件："
echo "=========================================="
echo ""
echo "📚 主要文檔："
echo "   - README.md"
echo "   - README_型態識別.md"
echo ""
echo "🔧 工具腳本："
echo "   - 檢測並填補缺失數據.py"
echo "   - 測試型態識別.py"
echo ""
echo "📁 文檔目錄："
echo "   - docs/功能說明/"
echo "   - docs/快速參考/"
echo "   - docs/更新記錄/"
echo ""
echo "=========================================="
echo "清理完成！"
echo "=========================================="
