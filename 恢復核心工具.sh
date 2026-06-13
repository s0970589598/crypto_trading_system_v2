#!/bin/bash
# 恢復被錯誤歸檔的核心工具
# 基於功能等價性檢查報告

set -e

echo "=========================================="
echo "🔄 恢復核心工具腳本"
echo "=========================================="
echo ""
echo "基於功能等價性檢查報告，以下工具被錯誤歸檔："
echo "  1. quantitative_risk_analysis.py（核心風險工具）"
echo "  2. quantitative_risk_enhancements.py（核心風險工具）"
echo "  3. backtest_leverage_comparison.py（獨特對比功能）"
echo "  4. compare_stop_loss.py（獨特對比功能）"
echo "  5. 分析失控交易特徵.py（獨特分析功能）"
echo ""
echo "⚠️  這些工具包含 CLI/Web 均未實現的獨特功能"
echo ""
echo "是否恢復這些工具？(y/n)"
read confirm

if [ "$confirm" != "y" ]; then
    echo "取消恢復"
    exit 0
fi

echo ""
echo "開始恢復..."

# 檢查歸檔目錄是否存在
if [ ! -d "_Archive/Code_20260211" ]; then
    echo "❌ 錯誤：歸檔目錄不存在"
    exit 1
fi

# 恢復核心風險分析工具
echo ""
echo "1️⃣ 恢復核心風險分析工具..."
if [ -f "_Archive/Code_20260211/quantitative_risk_analysis.py" ]; then
    cp -v "_Archive/Code_20260211/quantitative_risk_analysis.py" .
    echo "✅ quantitative_risk_analysis.py 已恢復"
else
    echo "⚠️ quantitative_risk_analysis.py 不在歸檔中"
fi

if [ -f "_Archive/Code_20260211/quantitative_risk_enhancements.py" ]; then
    cp -v "_Archive/Code_20260211/quantitative_risk_enhancements.py" .
    echo "✅ quantitative_risk_enhancements.py 已恢復"
else
    echo "⚠️ quantitative_risk_enhancements.py 不在歸檔中"
fi

# 恢復對比測試工具
echo ""
echo "2️⃣ 恢復對比測試工具..."
if [ -f "_Archive/Code_20260211/backtest_leverage_comparison.py" ]; then
    cp -v "_Archive/Code_20260211/backtest_leverage_comparison.py" .
    echo "✅ backtest_leverage_comparison.py 已恢復"
else
    echo "⚠️ backtest_leverage_comparison.py 不在歸檔中"
fi

if [ -f "_Archive/Code_20260211/compare_stop_loss.py" ]; then
    cp -v "_Archive/Code_20260211/compare_stop_loss.py" .
    echo "✅ compare_stop_loss.py 已恢復"
else
    echo "⚠️ compare_stop_loss.py 不在歸檔中"
fi

# 恢復失控交易分析工具
echo ""
echo "3️⃣ 恢復失控交易分析工具..."
if [ -f "_Archive/Code_20260211/分析失控交易特徵.py" ]; then
    cp -v "_Archive/Code_20260211/分析失控交易特徵.py" .
    echo "✅ 分析失控交易特徵.py 已恢復"
else
    echo "⚠️ 分析失控交易特徵.py 不在歸檔中"
fi

# 可選：恢復快速測試工具
echo ""
echo "=========================================="
echo "可選恢復"
echo "=========================================="
echo ""
echo "是否恢復快速測試工具？(y/n)"
echo "  - backtest_multi_timeframe.py（快速執行回測）"
read confirm_optional

if [ "$confirm_optional" = "y" ]; then
    if [ -f "_Archive/Code_20260211/backtest_multi_timeframe.py" ]; then
        cp -v "_Archive/Code_20260211/backtest_multi_timeframe.py" .
        echo "✅ backtest_multi_timeframe.py 已恢復"
    else
        echo "⚠️ backtest_multi_timeframe.py 不在歸檔中"
    fi
fi

echo ""
echo "=========================================="
echo "✅ 恢復完成"
echo "=========================================="
echo ""
echo "已恢復的工具："
ls -lh quantitative_risk*.py backtest_leverage_comparison.py compare_stop_loss.py 分析失控交易特徵.py 2>/dev/null || echo "  部分工具未找到"
echo ""
echo "📝 下一步："
echo "  1. 查看功能等價性檢查報告：cat 功能等價性檢查報告_20260211.md"
echo "  2. 驗證工具功能：python3 quantitative_risk_analysis.py --help"
echo "  3. 制定功能整合計劃（中期）"
echo ""
