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
