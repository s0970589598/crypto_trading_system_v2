# 文檔索引 (Documentation Index)

歡迎來到多策略交易系統文檔中心！本頁面幫助您快速找到所需的文檔。

---

## 📚 文檔導覽

### 🚀 快速開始

**新用戶必讀**：

1. [README.md](../README.md) - 項目概述和快速開始
2. [QUICKSTART.md](QUICKSTART.md) - 詳細的快速開始指南（如果有）

**5 分鐘快速上手**：
```bash
# 1. 安裝依賴
pip install -r requirements.txt

# 2. 配置系統
cp system_config.yaml.example system_config.yaml
# 編輯 system_config.yaml

# 3. 運行回測
python cli.py backtest --strategy multi-timeframe-aggressive --start 2024-01-01 --end 2024-12-31

# 4. 啟動實盤
python cli.py live --strategy multi-timeframe-aggressive
```

---

### 👨‍💻 開發者文檔

**開發新策略或貢獻代碼**：

1. [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) - 完整的開發者指南
   - 系統架構
   - 開發環境設置
   - 代碼規範
   - 貢獻流程

2. [API.md](API.md) - API 參考文檔
   - 策略接口
   - 管理層 API
   - 執行層 API
   - 分析層 API
   - 數據模型

3. [STRATEGY_DEVELOPMENT.md](STRATEGY_DEVELOPMENT.md) - 策略開發指南
   - 策略開發流程
   - 策略模板
   - 技術指標
   - 信號生成
   - 風險管理
   - 最佳實踐

---

### 📖 示例和教程

**學習如何使用系統**：

1. [EXAMPLES.md](EXAMPLES.md) - 策略示例
   - 多週期共振策略
   - 突破策略
   - 均值回歸策略
   - 策略對比
   - 使用建議

**示例策略**：
- `src/strategies/multi_timeframe_strategy.py` - 多週期共振策略
- `src/strategies/breakout_strategy.py` - 突破策略
- `src/strategies/mean_reversion_strategy.py` - 均值回歸策略

**配置示例**：
- `strategies/multi-timeframe-aggressive.json` - 激進模式配置
- `strategies/multi-timeframe-relaxed.json` - 輕鬆模式配置
- `strategies/breakout-strategy.json` - 突破策略配置
- `strategies/mean-reversion.json` - 均值回歸配置

---

### 🧪 測試文檔

**編寫和運行測試**：

1. [TESTING_GUIDE.md](TESTING_GUIDE.md) - 測試指南
   - 測試策略
   - 運行測試
   - 編寫單元測試
   - 編寫屬性測試
   - 測試覆蓋率
   - 持續集成

**快速測試命令**：
```bash
# 運行所有測試
pytest

# 運行單元測試
pytest tests/unit/

# 運行屬性測試
pytest tests/property/

# 生成覆蓋率報告
pytest --cov=src --cov-report=html
```

---

### 🏗️ 架構文檔

**理解系統設計**：

1. [ARCHITECTURE.md](ARCHITECTURE.md) - 架構設計（如果有）
   - 五層架構
   - 組件交互
   - 數據流
   - 設計決策

2. [.kiro/specs/multi-strategy-system/design.md](../.kiro/specs/multi-strategy-system/design.md) - 詳細設計文檔
   - 系統概述
   - 架構設計
   - 組件和接口
   - 數據模型
   - 正確性屬性
   - 錯誤處理
   - 測試策略

---

### 📋 需求文檔

**了解系統需求**：

1. [.kiro/specs/multi-strategy-system/requirements.md](../.kiro/specs/multi-strategy-system/requirements.md) - 需求文檔
   - 策略配置管理
   - 策略隔離運行
   - 策略開發流程
   - 統一回測引擎
   - 參數優化器
   - 虧損分析器
   - 交易覆盤系統
   - 策略性能監控
   - 風險管理
   - 數據管理

---

### ✅ 任務清單

**查看實施進度**：

1. [.kiro/specs/multi-strategy-system/tasks.md](../.kiro/specs/multi-strategy-system/tasks.md) - 實施任務清單
   - 階段 1：核心基礎設施
   - 階段 2：策略遷移
   - 階段 3：分析工具
   - 階段 4：優化工具

---

## 🎯 按角色查找文檔

### 我是新用戶

**推薦閱讀順序**：
1. [README.md](../README.md) - 了解項目
2. [EXAMPLES.md](EXAMPLES.md) - 查看示例
3. 運行回測 - 實踐操作
4. [STRATEGY_DEVELOPMENT.md](STRATEGY_DEVELOPMENT.md) - 學習開發

### 我是策略開發者

**推薦閱讀順序**：
1. [STRATEGY_DEVELOPMENT.md](STRATEGY_DEVELOPMENT.md) - 策略開發指南
2. [EXAMPLES.md](EXAMPLES.md) - 學習示例
3. [API.md](API.md) - API 參考
4. [TESTING_GUIDE.md](TESTING_GUIDE.md) - 編寫測試

### 我是系統開發者

**推薦閱讀順序**：
1. [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) - 開發者指南
2. [.kiro/specs/multi-strategy-system/design.md](../.kiro/specs/multi-strategy-system/design.md) - 設計文檔
3. [API.md](API.md) - API 參考
4. [TESTING_GUIDE.md](TESTING_GUIDE.md) - 測試指南

### 我是測試工程師

**推薦閱讀順序**：
1. [TESTING_GUIDE.md](TESTING_GUIDE.md) - 測試指南
2. [.kiro/specs/multi-strategy-system/design.md](../.kiro/specs/multi-strategy-system/design.md) - 正確性屬性
3. 查看現有測試 - `tests/` 目錄

---

## 🔍 按主題查找文檔

### 策略相關

- **創建策略**：[STRATEGY_DEVELOPMENT.md](STRATEGY_DEVELOPMENT.md) → 策略開發流程
- **策略示例**：[EXAMPLES.md](EXAMPLES.md)
- **策略接口**：[API.md](API.md) → 策略接口
- **策略配置**：[DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) → 配置管理

### 回測相關

- **運行回測**：[README.md](../README.md) → 使用示例
- **回測引擎**：[API.md](API.md) → BacktestEngine
- **回測結果**：[API.md](API.md) → BacktestResult

### 優化相關

- **參數優化**：[API.md](API.md) → Optimizer
- **優化方法**：[STRATEGY_DEVELOPMENT.md](STRATEGY_DEVELOPMENT.md) → 回測和優化

### 測試相關

- **運行測試**：[TESTING_GUIDE.md](TESTING_GUIDE.md) → 運行測試
- **編寫測試**：[TESTING_GUIDE.md](TESTING_GUIDE.md) → 編寫單元測試
- **屬性測試**：[TESTING_GUIDE.md](TESTING_GUIDE.md) → 編寫屬性測試

### 風險管理

- **風險管理器**：[API.md](API.md) → RiskManager
- **風險策略**：[STRATEGY_DEVELOPMENT.md](STRATEGY_DEVELOPMENT.md) → 風險管理
- **風險需求**：[.kiro/specs/multi-strategy-system/requirements.md](../.kiro/specs/multi-strategy-system/requirements.md) → Requirement 9

---

## 📞 獲取幫助

### 常見問題

查看各文檔的「常見問題」部分：
- [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) → 常見問題
- [STRATEGY_DEVELOPMENT.md](STRATEGY_DEVELOPMENT.md) → 常見問題
- [TESTING_GUIDE.md](TESTING_GUIDE.md) → 常見問題

### 問題反饋

- **GitHub Issues**：報告 bug 或請求功能
- **GitHub Discussions**：討論和提問

### 貢獻

查看 [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) → 貢獻流程

---

## 📝 文檔更新

**最後更新**：2024-01-22

**文檔版本**：1.0.0

**系統版本**：1.0.0

---

**祝您使用愉快！** 🚀
