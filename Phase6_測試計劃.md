# Phase 6 測試計劃

**日期**: 2026-02-11  
**目標**: 全面測試所有整合點

---

## 📊 測試範圍

### 1. 核心模組測試（15分鐘）

**測試對象**:
- RiskManager 量化分析功能
- PerformanceMonitor 量化分析功能
- LossAnalyzer 量化分析功能

**測試內容**:
- 啟用量化分析
- 調用各個量化方法
- 驗證返回結果
- 錯誤處理

---

### 2. CLI 工具測試（10分鐘）

**測試對象**:
- `cli_commands/analyze_risk.py`

**測試內容**:
- 所有分析類型
- 輸出格式（text/json）
- 參數解析
- 錯誤處理

---

### 3. 兼容層測試（5分鐘）

**測試對象**:
- `quantitative_risk_analysis.py`

**測試內容**:
- 舊導入方式
- 棄用警告
- 功能等價性

---

### 4. 單元測試（5分鐘）

**測試對象**:
- 所有現有測試

**測試內容**:
- 運行所有單元測試
- 確認測試通過率
- 檢查代碼覆蓋率

---

### 5. 整合測試（5分鐘）

**測試對象**:
- 端到端流程

**測試內容**:
- 數據載入
- 分析執行
- 結果輸出
- 多模組協作

---

## 📋 測試清單

### 核心模組測試

#### RiskManager
- [ ] 初始化正常
- [ ] 啟用量化分析
- [ ] calculate_kelly_criterion() 正常
- [ ] detect_tilt_behavior() 正常
- [ ] calculate_risk_of_ruin() 正常
- [ ] calculate_fee_pressure() 正常
- [ ] 未啟用時返回 None

#### PerformanceMonitor
- [ ] 初始化正常
- [ ] 啟用量化分析
- [ ] calculate_recovery_factor() 正常
- [ ] analyze_emotional_control() 正常
- [ ] calculate_skill_dimensions() 正常
- [ ] calculate_max_losing_streak() 正常
- [ ] 未啟用時返回 None

#### LossAnalyzer
- [ ] 初始化正常
- [ ] 啟用量化分析
- [ ] calculate_max_losing_streak() 正常
- [ ] analyze_short_term_trades() 正常
- [ ] simulate_without_short_trades() 正常
- [ ] check_cooling_period() 正常
- [ ] 未啟用時返回 None

---

### CLI 工具測試

- [ ] 幫助信息顯示正常
- [ ] 參數解析正確
- [ ] --analysis all 正常
- [ ] --analysis kelly 正常
- [ ] --analysis tilt 正常
- [ ] --analysis ror 正常
- [ ] --analysis fee 正常
- [ ] --analysis recovery 正常
- [ ] --analysis emotional 正常
- [ ] --analysis skill 正常
- [ ] --analysis streak 正常
- [ ] --analysis short 正常
- [ ] --analysis cooling 正常
- [ ] --format text 正常
- [ ] --format json 正常
- [ ] --output 文件輸出正常
- [ ] 錯誤處理正確

---

### 兼容層測試

- [ ] 舊導入方式可用
- [ ] 棄用警告顯示
- [ ] 功能等價性
- [ ] 所有方法可用

---

### 單元測試

- [ ] test_quantitative_risk.py 通過
- [ ] test_compatibility_layer.py 通過
- [ ] test_risk_manager.py 通過
- [ ] test_performance_monitor.py 通過
- [ ] test_loss_analyzer.py 通過

---

### 整合測試

- [ ] 端到端流程正常
- [ ] 多模組協作正常
- [ ] 性能可接受
- [ ] 無內存洩漏

---

## 🎯 測試策略

### 1. 自動化測試優先

使用現有的單元測試框架，確保所有測試通過。

### 2. 手動測試補充

對於 CLI 工具和 Web 界面，進行手動測試。

### 3. 錯誤場景測試

測試各種錯誤情況，確保錯誤處理正確。

### 4. 性能測試

確保量化分析不會顯著影響性能。

---

## 📊 測試數據

### 測試數據文件

使用現有的測試數據：
- `test_trades.csv` - 測試交易數據
- 如果不存在，創建模擬數據

### 測試數據要求

- 至少 50 筆交易
- 包含獲利和虧損交易
- 包含不同持倉時間的交易
- 數據格式正確

---

## ✅ 成功標準

### 必須通過

1. ✅ 所有單元測試通過（100%）
2. ✅ 核心模組功能正常
3. ✅ CLI 工具功能正常
4. ✅ 兼容層功能正常

### 應該通過

1. ✅ 代碼覆蓋率 > 70%
2. ✅ 無明顯性能問題
3. ✅ 錯誤處理完善

### 可選通過

1. ⭕ Web 界面手動測試
2. ⭕ 壓力測試
3. ⭕ 長時間運行測試

---

## 🛡️ 風險控制

### 測試失敗處理

1. **記錄失敗原因**
2. **分析根本原因**
3. **修復問題**
4. **重新測試**
5. **如無法修復，回滾相關變更**

### 回滾計劃

所有備份檔案都已準備好，可以快速回滾。

---

## 📝 測試報告

測試完成後，創建：
- `Phase6_測試報告.md` - 詳細測試結果
- `Phase6_快速參考.md` - 快速參考
- `整合進度總結_Phase6完成.md` - 整體進度

---

**制定人**: Kiro AI Assistant  
**制定日期**: 2026-02-11  
**預計執行時間**: 40 分鐘

