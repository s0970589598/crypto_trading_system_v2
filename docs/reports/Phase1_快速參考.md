# Phase 1 快速參考

**當前狀態**: 進行中（30% 完成）  
**下一步**: 完成 `src/analysis/quantitative_risk.py` 實現

---

## 📁 已創建的檔案

1. ✅ `src/analysis/quantitative_risk.py` (部分完成)
   - 數據模型：6個 ✅
   - 核心分析器：開始實現 🔄
   - 主類：待實現 ⏳

2. ✅ `整合執行狀態_Phase1.md` (完整狀態報告)

3. ✅ `Phase1_快速參考.md` (本檔案)

---

## 🎯 Phase 1 目標

創建完整的 `src/analysis/quantitative_risk.py` 模組，包含：

### 必須實現的功能

1. **KellyCriterionCalculator** - Kelly 最優倉位計算
2. **TiltDetector** - 傾斜行為檢測
3. **EmotionalControlAnalyzer** - 情緒控制分析
4. **SkillDimensionScorer** - 能力維度評分
5. **FeeAnalyzer** - 手續費分析
6. **CoolingPeriodChecker** - 冷靜期檢測
7. **QuantitativeRiskAnalyzer** - 主類（整合所有分析器）

### 必須提供的 API（兼容原始檔案）

```python
# 11個核心方法
1. calculate_max_losing_streak()
2. calculate_risk_of_ruin()
3. calculate_fee_pressure()
4. detect_tilt_behavior()
5. check_cooling_period()
6. calculate_ror_kelly()
7. analyze_emotional_control()
8. calculate_skill_dimensions()
9. calculate_recovery_factor()
10. analyze_short_term_trades()
11. simulate_without_short_trades()
```

---

## 🔧 實現方式

### 選項 1：手動完成（推薦）

由於檔案較大，建議分批實現：

```bash
# 1. 完成 TiltDetector
# 2. 完成 EmotionalControlAnalyzer
# 3. 完成 SkillDimensionScorer
# 4. 完成 FeeAnalyzer
# 5. 完成 CoolingPeriodChecker
# 6. 完成 QuantitativeRiskAnalyzer
# 7. 更新 __init__.py
# 8. 編寫測試
```

### 選項 2：複製轉換（快速）

直接從 `quantitative_risk_analysis.py` 複製邏輯：

```bash
# 1. 打開 quantitative_risk_analysis.py
# 2. 複製每個方法的實現
# 3. 貼到對應的分析器類中
# 4. 調整參數（self.df → df）
# 5. 測試
```

---

## ✅ 完成標準

Phase 1 完成需要滿足：

1. ✅ `src/analysis/quantitative_risk.py` 完整實現
2. ✅ 所有6個分析器都能正常工作
3. ✅ QuantitativeRiskAnalyzer 提供11個兼容方法
4. ✅ `src/analysis/__init__.py` 已更新
5. ✅ 單元測試已編寫
6. ✅ 所有測試通過

---

## 🚀 快速執行命令

```bash
# 檢查當前進度
cat src/analysis/quantitative_risk.py | wc -l

# 語法檢查
python3 -m py_compile src/analysis/quantitative_risk.py

# 導入測試
python3 -c "from src.analysis.quantitative_risk import QuantitativeRiskAnalyzer"

# 運行測試
pytest tests/analysis/test_quantitative_risk.py -v

# 查看原始檔案（參考）
head -100 quantitative_risk_analysis.py
```

---

## 📞 需要幫助？

如果遇到問題，檢查：

1. **語法錯誤**: `python3 -m py_compile src/analysis/quantitative_risk.py`
2. **導入錯誤**: 確認 `src/analysis/__init__.py` 已更新
3. **邏輯錯誤**: 對比 `quantitative_risk_analysis.py` 原始實現
4. **測試失敗**: 檢查測試數據和預期結果

---

## 📊 當前檔案狀態

```
src/analysis/quantitative_risk.py
├── 數據模型 (✅ 完成)
│   ├── TiltScore
│   ├── KellyCriterion
│   ├── EmotionalControl
│   ├── SkillDimensions
│   ├── CoolingPeriodRecommendation
│   └── FeeAnalysis
│
├── 核心分析器 (🔄 進行中)
│   ├── KellyCriterionCalculator (部分完成)
│   ├── TiltDetector (開始)
│   ├── EmotionalControlAnalyzer (待實現)
│   ├── SkillDimensionScorer (待實現)
│   ├── FeeAnalyzer (待實現)
│   └── CoolingPeriodChecker (待實現)
│
└── 主類 (⏳ 待實現)
    └── QuantitativeRiskAnalyzer
```

---

**最後更新**: 2026-02-11  
**下一步**: 繼續實現核心分析器
