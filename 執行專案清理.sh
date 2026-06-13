#!/bin/bash
# 專案資產清理腳本
# 日期：2026-02-11
# 用途：安全歸檔冗餘檔案

set -e  # 遇到錯誤立即停止

echo "=========================================="
echo "🧹 專案資產清理腳本"
echo "=========================================="
echo ""
echo "⚠️  警告：此腳本將移動檔案到 _Archive/ 目錄"
echo "   所有檔案可以隨時恢復"
echo ""
echo "按 Enter 繼續，或 Ctrl+C 取消..."
read

# ==================== 階段 0：創建歸檔目錄 ====================
echo ""
echo "📁 階段 0：創建歸檔目錄..."
mkdir -p _Archive/Doc_20260211
mkdir -p _Archive/Code_20260211
mkdir -p _Archive/Script_20260211
echo "✅ 歸檔目錄已創建"

# ==================== 階段 1：歸檔文檔 ====================
echo ""
echo "📄 階段 1：歸檔文檔（48 個）..."
echo ""
echo "是否執行階段 1？(y/n)"
read stage1

if [ "$stage1" = "y" ]; then
    echo "正在歸檔階段性總結文檔..."
    
    # A. 階段性完成總結（18 個）
    mv -v "功能完成總結_CMT_Level3.md" "_Archive/Doc_20260211/" 2>/dev/null || echo "  跳過：功能完成總結_CMT_Level3.md"
    mv -v "數據獲取模組化完成總結.md" "_Archive/Doc_20260211/" 2>/dev/null || echo "  跳過：數據獲取模組化完成總結.md"
    mv -v "trading_alert_system重構完成.md" "_Archive/Doc_20260211/" 2>/dev/null || echo "  跳過：trading_alert_system重構完成.md"
    mv -v "數據填補功能整合完成.md" "_Archive/Doc_20260211/" 2>/dev/null || echo "  跳過：數據填補功能整合完成.md"
    mv -v "清理完成說明.md" "_Archive/Doc_20260211/" 2>/dev/null || echo "  跳過：清理完成說明.md"
    mv -v "清理完成總結.txt" "_Archive/Doc_20260211/" 2>/dev/null || echo "  跳過：清理完成總結.txt"
    mv -v "最終完成總結.md" "_Archive/Doc_20260211/" 2>/dev/null || echo "  跳過：最終完成總結.md"
    mv -v "Git推送完成說明.md" "_Archive/Doc_20260211/" 2>/dev/null || echo "  跳過：Git推送完成說明.md"
    mv -v "文件整理說明.md" "_Archive/Doc_20260211/" 2>/dev/null || echo "  跳過：文件整理說明.md"
    mv -v "數據獲取腳本整理方案.md" "_Archive/Doc_20260211/" 2>/dev/null || echo "  跳過：數據獲取腳本整理方案.md"
    mv -v "模組化實施計劃.md" "_Archive/Doc_20260211/" 2>/dev/null || echo "  跳過：模組化實施計劃.md"
    mv -v "web_dashboard_模組化方案.md" "_Archive/Doc_20260211/" 2>/dev/null || echo "  跳過：web_dashboard_模組化方案.md"
    mv -v "重構trading_alert_system影響分析.md" "_Archive/Doc_20260211/" 2>/dev/null || echo "  跳過：重構trading_alert_system影響分析.md"
    mv -v "數據管理完整架構.md" "_Archive/Doc_20260211/" 2>/dev/null || echo "  跳過：數據管理完整架構.md"
    mv -v "數據模組使用情況分析.md" "_Archive/Doc_20260211/" 2>/dev/null || echo "  跳過：數據模組使用情況分析.md"
    mv -v "數據獲取程式清單.md" "_Archive/Doc_20260211/" 2>/dev/null || echo "  跳過：數據獲取程式清單.md"
    mv -v "多時區分析更新說明_v2.md" "_Archive/Doc_20260211/" 2>/dev/null || echo "  跳過：多時區分析更新說明_v2.md"
    mv -v "新功能使用說明_2026-02-09.md" "_Archive/Doc_20260211/" 2>/dev/null || echo "  跳過：新功能使用說明_2026-02-09.md"
    
    echo ""
    echo "正在歸檔功能說明文檔..."
    
    # B. 功能說明文檔（15 個）
    mv -v "BingX_API限制_最終結論.md" "_Archive/Doc_20260211/" 2>/dev/null || echo "  跳過：BingX_API限制_最終結論.md"
    mv -v "BingX_API限制說明.md" "_Archive/Doc_20260211/" 2>/dev/null || echo "  跳過：BingX_API限制說明.md"
    mv -v "BingX不同帳戶手續費對比.md" "_Archive/Doc_20260211/" 2>/dev/null || echo "  跳過：BingX不同帳戶手續費對比.md"
    mv -v "BingX手續費完整說明.md" "_Archive/Doc_20260211/" 2>/dev/null || echo "  跳過：BingX手續費完整說明.md"
    mv -v "K線圖進出場標記說明.md" "_Archive/Doc_20260211/" 2>/dev/null || echo "  跳過：K線圖進出場標記說明.md"
    mv -v "K線圖價格顯示修正說明.md" "_Archive/Doc_20260211/" 2>/dev/null || echo "  跳過：K線圖價格顯示修正說明.md"
    mv -v "K線標記位置說明.md" "_Archive/Doc_20260211/" 2>/dev/null || echo "  跳過：K線標記位置說明.md"
    mv -v "NoneType錯誤完全修復.md" "_Archive/Doc_20260211/" 2>/dev/null || echo "  跳過：NoneType錯誤完全修復.md"
    mv -v "Tooltip功能快速參考.md" "_Archive/Doc_20260211/" 2>/dev/null || echo "  跳過：Tooltip功能快速參考.md"
    mv -v "Web界面v2功能總覽.md" "_Archive/Doc_20260211/" 2>/dev/null || echo "  跳過：Web界面v2功能總覽.md"
    mv -v "實時價格獲取邏輯說明.md" "_Archive/Doc_20260211/" 2>/dev/null || echo "  跳過：實時價格獲取邏輯說明.md"
    mv -v "智能止損計算說明.md" "_Archive/Doc_20260211/" 2>/dev/null || echo "  跳過：智能止損計算說明.md"
    mv -v "顏色調整說明.md" "_Archive/Doc_20260211/" 2>/dev/null || echo "  跳過：顏色調整說明.md"
    mv -v "狀態消息顯示優化說明.md" "_Archive/Doc_20260211/" 2>/dev/null || echo "  跳過：狀態消息顯示優化說明.md"
    mv -v "測試狀態消息流程.md" "_Archive/Doc_20260211/" 2>/dev/null || echo "  跳過：測試狀態消息流程.md"
    
    echo ""
    echo "正在歸檔技術說明文檔..."
    
    # C. 詳細技術說明（10 個）
    mv -v "交易詳細信息顯示優化說明.md" "_Archive/Doc_20260211/" 2>/dev/null || echo "  跳過：交易詳細信息顯示優化說明.md"
    mv -v "進出場標記修正說明.md" "_Archive/Doc_20260211/" 2>/dev/null || echo "  跳過：進出場標記修正說明.md"
    mv -v "進出場技術指標分析_最終報告.md" "_Archive/Doc_20260211/" 2>/dev/null || echo "  跳過：進出場技術指標分析_最終報告.md"
    mv -v "量化風險分析對比報告.md" "_Archive/Doc_20260211/" 2>/dev/null || echo "  跳過：量化風險分析對比報告.md"
    mv -v "量化風險分析整合完成說明.md" "_Archive/Doc_20260211/" 2>/dev/null || echo "  跳過：量化風險分析整合完成說明.md"
    mv -v "實際收益率顯示說明.md" "_Archive/Doc_20260211/" 2>/dev/null || echo "  跳過：實際收益率顯示說明.md"
    mv -v "盈虧比計算配置說明.md" "_Archive/Doc_20260211/" 2>/dev/null || echo "  跳過：盈虧比計算配置說明.md"
    mv -v "盈虧比計算說明.md" "_Archive/Doc_20260211/" 2>/dev/null || echo "  跳過：盈虧比計算說明.md"
    mv -v "時間週期評估報告.md" "_Archive/Doc_20260211/" 2>/dev/null || echo "  跳過：時間週期評估報告.md"
    
    echo ""
    echo "正在歸檔評分系統文檔..."
    
    # D. 評分系統文檔（8 個）
    mv -v "自動評分註記說明.md" "_Archive/Doc_20260211/" 2>/dev/null || echo "  跳過：自動評分註記說明.md"
    mv -v "自動評分邏輯詳解.md" "_Archive/Doc_20260211/" 2>/dev/null || echo "  跳過：自動評分邏輯詳解.md"
    mv -v "評分系統改進建議.md" "_Archive/Doc_20260211/" 2>/dev/null || echo "  跳過：評分系統改進建議.md"
    mv -v "評分系統最終建議.md" "_Archive/Doc_20260211/" 2>/dev/null || echo "  跳過：評分系統最終建議.md"
    mv -v "評分系統v2快速參考.md" "_Archive/Doc_20260211/" 2>/dev/null || echo "  跳過：評分系統v2快速參考.md"
    mv -v "評分依據完整分析.md" "_Archive/Doc_20260211/" 2>/dev/null || echo "  跳過：評分依據完整分析.md"
    mv -v "評分時自動下載數據流程說明.md" "_Archive/Doc_20260211/" 2>/dev/null || echo "  跳過：評分時自動下載數據流程說明.md"
    mv -v "評分註記示例.md" "_Archive/Doc_20260211/" 2>/dev/null || echo "  跳過：評分註記示例.md"
    
    echo ""
    echo "✅ 階段 1 完成：文檔已歸檔"
else
    echo "⏭️  跳過階段 1"
fi

# ==================== 階段 2：歸檔程式碼 ====================
echo ""
echo "🐍 階段 2：歸檔程式碼（15 個）..."
echo ""
echo "⚠️  注意：這將歸檔回測腳本和測試腳本"
echo "   請確保 CLI 系統功能完整"
echo ""
echo "是否執行階段 2？(y/n)"
read stage2

if [ "$stage2" = "y" ]; then
    echo "正在歸檔回測腳本..."
    
    # A. 回測腳本（9 個）
    mv -v "backtest_multi_timeframe.py" "_Archive/Code_20260211/" 2>/dev/null || echo "  跳過：backtest_multi_timeframe.py"
    mv -v "backtest_multi_strategy.py" "_Archive/Code_20260211/" 2>/dev/null || echo "  跳過：backtest_multi_strategy.py"
    mv -v "backtest_leverage_comparison.py" "_Archive/Code_20260211/" 2>/dev/null || echo "  跳過：backtest_leverage_comparison.py"
    mv -v "improved_backtest.py" "_Archive/Code_20260211/" 2>/dev/null || echo "  跳過：improved_backtest.py"
    mv -v "final_optimized_backtest.py" "_Archive/Code_20260211/" 2>/dev/null || echo "  跳過：final_optimized_backtest.py"
    mv -v "full_position_backtest.py" "_Archive/Code_20260211/" 2>/dev/null || echo "  跳過：full_position_backtest.py"
    mv -v "compare_stop_loss.py" "_Archive/Code_20260211/" 2>/dev/null || echo "  跳過：compare_stop_loss.py"
    mv -v "quantitative_risk_analysis.py" "_Archive/Code_20260211/" 2>/dev/null || echo "  跳過：quantitative_risk_analysis.py"
    mv -v "quantitative_risk_enhancements.py" "_Archive/Code_20260211/" 2>/dev/null || echo "  跳過：quantitative_risk_enhancements.py"
    
    echo ""
    echo "正在歸檔分析腳本..."
    
    # B. 數據獲取/分析腳本（3 個）
    mv -v "分析失控交易特徵.py" "_Archive/Code_20260211/" 2>/dev/null || echo "  跳過：分析失控交易特徵.py"
    mv -v "查看回測結果.py" "_Archive/Code_20260211/" 2>/dev/null || echo "  跳過：查看回測結果.py"
    mv -v "查看完整數據對比.py" "_Archive/Code_20260211/" 2>/dev/null || echo "  跳過：查看完整數據對比.py"
    
    echo ""
    echo "正在歸檔測試腳本..."
    
    # C. 測試腳本（4 個）
    mv -v "測試型態識別v2.py" "_Archive/Code_20260211/" 2>/dev/null || echo "  跳過：測試型態識別v2.py"
    mv -v "測試數據填補功能.py" "_Archive/Code_20260211/" 2>/dev/null || echo "  跳過：測試數據填補功能.py"
    mv -v "verify_fix.py" "_Archive/Code_20260211/" 2>/dev/null || echo "  跳過：verify_fix.py"
    mv -v "cleanup_temp_files.py" "_Archive/Code_20260211/" 2>/dev/null || echo "  跳過：cleanup_temp_files.py"
    
    # 歸檔深度分析腳本（如果存在）
    mv -v "深度分析進出場指標.py" "_Archive/Code_20260211/" 2>/dev/null || echo "  跳過：深度分析進出場指標.py"
    
    echo ""
    echo "✅ 階段 2 完成：程式碼已歸檔"
else
    echo "⏭️  跳過階段 2"
fi

# ==================== 階段 3：歸檔 Shell 腳本 ====================
echo ""
echo "📜 階段 3：歸檔 Shell 腳本（2 個）..."
echo ""
echo "是否執行階段 3？(y/n)"
read stage3

if [ "$stage3" = "y" ]; then
    mv -v "執行數據腳本整理.sh" "_Archive/Script_20260211/" 2>/dev/null || echo "  跳過：執行數據腳本整理.sh"
    mv -v "清理舊數據目錄.sh" "_Archive/Script_20260211/" 2>/dev/null || echo "  跳過：清理舊數據目錄.sh"
    
    echo ""
    echo "✅ 階段 3 完成：Shell 腳本已歸檔"
else
    echo "⏭️  跳過階段 3"
fi

# ==================== 階段 4：創建歸檔說明 ====================
echo ""
echo "📝 階段 4：創建歸檔說明..."

cat > _Archive/Doc_20260211/README.md << 'EOF'
# 文檔歸檔說明

## 歸檔日期
2026-02-11

## 歸檔原因
專案文檔過多（66個），造成以下問題：
1. 資訊過載，難以找到關鍵文檔
2. 大量重複內容（BingX手續費、K線圖說明等）
3. 過時的階段性總結文檔
4. 功能說明文檔與實際代碼不同步

## 歸檔內容（48 個文檔）

### A. 階段性完成總結（18 個）
- 功能完成總結_CMT_Level3.md
- 數據獲取模組化完成總結.md
- trading_alert_system重構完成.md
- 數據填補功能整合完成.md
- 清理完成說明.md
- 清理完成總結.txt
- 最終完成總結.md
- Git推送完成說明.md
- 文件整理說明.md
- 數據獲取腳本整理方案.md
- 模組化實施計劃.md
- web_dashboard_模組化方案.md
- 重構trading_alert_system影響分析.md
- 數據管理完整架構.md
- 數據模組使用情況分析.md
- 數據獲取程式清單.md
- 多時區分析更新說明_v2.md
- 新功能使用說明_2026-02-09.md

### B. 功能說明文檔（15 個）
- BingX_API限制_最終結論.md
- BingX_API限制說明.md
- BingX不同帳戶手續費對比.md
- BingX手續費完整說明.md
- K線圖進出場標記說明.md
- K線圖價格顯示修正說明.md
- K線標記位置說明.md
- NoneType錯誤完全修復.md
- Tooltip功能快速參考.md
- Web界面v2功能總覽.md
- 實時價格獲取邏輯說明.md
- 智能止損計算說明.md
- 顏色調整說明.md
- 狀態消息顯示優化說明.md
- 測試狀態消息流程.md

### C. 詳細技術說明（10 個）
- 交易詳細信息顯示優化說明.md
- 進出場標記修正說明.md
- 進出場技術指標分析_最終報告.md
- 量化風險分析對比報告.md
- 量化風險分析整合完成說明.md
- 實際收益率顯示說明.md
- 盈虧比計算配置說明.md
- 盈虧比計算說明.md
- 時間週期評估報告.md

### D. 評分系統文檔（8 個）
- 自動評分註記說明.md
- 自動評分邏輯詳解.md
- 評分系統改進建議.md
- 評分系統最終建議.md
- 評分系統v2快速參考.md
- 評分依據完整分析.md
- 評分時自動下載數據流程說明.md
- 評分註記示例.md

## 恢復方法
如需恢復任何文檔，從此目錄複製回根目錄即可：
```bash
cp _Archive/Doc_20260211/文件名.md .
```

## 保留的核心文檔
- README.md（主要說明）
- CLI_README.md（CLI 使用指南）
- 我的交易策略.md（策略核心）
- 快速開始.md（入門指南）
- 槓桿與風險管理.md（風險管理）
EOF

cat > _Archive/Code_20260211/README.md << 'EOF'
# 程式碼歸檔說明

## 歸檔日期
2026-02-11

## 歸檔原因
根目錄獨立腳本過多（31個），功能重疊嚴重：
1. 回測功能已整合到 CLI 系統（cli.py + cli_commands/）
2. 數據獲取功能已整合到 MarketAnalyzer
3. 測試腳本已完成驗證

## 歸檔內容（15 個腳本）

### A. 回測腳本（9 個）
- backtest_multi_timeframe.py
- backtest_multi_strategy.py
- backtest_leverage_comparison.py
- improved_backtest.py
- final_optimized_backtest.py
- full_position_backtest.py
- compare_stop_loss.py
- quantitative_risk_analysis.py
- quantitative_risk_enhancements.py

### B. 分析腳本（3 個）
- 分析失控交易特徵.py
- 查看回測結果.py
- 查看完整數據對比.py

### C. 測試腳本（4 個）
- 測試型態識別v2.py
- 測試數據填補功能.py
- verify_fix.py
- cleanup_temp_files.py

## 替代方案

### 回測功能
使用 CLI 系統：
```bash
python3 cli.py backtest --strategy multi-timeframe-aggressive
```

### 數據獲取
使用保留的工具：
```bash
python3 快速更新市場數據.py
python3 快速重新下載_關鍵時區.py
```

### Web 界面
```bash
python3 -m streamlit run web_dashboard_v2.py
```

## 恢復方法
如需恢復任何腳本：
```bash
cp _Archive/Code_20260211/腳本名.py .
```

## 保留的核心程式
- cli.py（CLI 主入口）
- web_dashboard_v2.py（Web 界面）
- trading_alert_system.py（交易提醒）
- 快速更新市場數據.py（數據更新）
- 快速重新下載_關鍵時區.py（數據下載）
EOF

cat > _Archive/Script_20260211/README.md << 'EOF'
# Shell 腳本歸檔說明

## 歸檔日期
2026-02-11

## 歸檔原因
一次性整理腳本，已完成任務

## 歸檔內容（2 個）
- 執行數據腳本整理.sh
- 清理舊數據目錄.sh

## 保留的 Shell 腳本
- 啟動Web界面v2.sh（啟動 Web 界面）
- start_alert.sh（啟動提醒系統）
- example_cli_usage.sh（CLI 示例）
- 清理臨時文件.sh（常用工具）

## 恢復方法
```bash
cp _Archive/Script_20260211/腳本名.sh .
chmod +x 腳本名.sh
```
EOF

echo "✅ 歸檔說明已創建"

# ==================== 完成 ====================
echo ""
echo "=========================================="
echo "✅ 清理完成！"
echo "=========================================="
echo ""
echo "📊 統計："
echo "  - 文檔歸檔：_Archive/Doc_20260211/"
echo "  - 程式碼歸檔：_Archive/Code_20260211/"
echo "  - 腳本歸檔：_Archive/Script_20260211/"
echo ""
echo "📝 下一步："
echo "  1. 驗證核心功能：python3 cli.py backtest --strategy multi-timeframe-aggressive"
echo "  2. 測試 Web 界面：python3 -m streamlit run web_dashboard_v2.py"
echo "  3. 更新 README.md 反映新結構"
echo "  4. 提交 Git 變更"
echo ""
echo "💡 提示："
echo "  - 所有檔案可從 _Archive/ 恢復"
echo "  - 查看詳細方案：cat 專案清理方案_20260211.md"
echo ""
