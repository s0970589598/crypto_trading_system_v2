# Backtest 腳本功能對比報告

**日期**: 2026-02-11  
**目的**: 確認 backtest_leverage_comparison.py 和 backtest_multi_timeframe.py 是否可以刪除

---

## 1. backtest_multi_timeframe.py

### 功能描述
- 快速回測多週期共振策略
- 載入策略配置和市場數據
- 運行單一策略回測
- 顯示回測結果和交易明細
- 保存結果到 JSON 檔案

### 現有系統對應功能

#### CLI 系統
```bash
# 舊腳本
python3 backtest_multi_timeframe.py

# 新 CLI（完全等價）
python3 -m cli_commands.backtest --strategy multi-timeframe-aggressive
```

**功能對比**:
| 功能 | backtest_multi_timeframe.py | CLI backtest | 結論 |
|------|---------------------------|--------------|------|
| 載入策略配置 | ✅ | ✅ | 等價 |
| 載入市場數據 | ✅ | ✅ | 等價 |
| 運行回測 | ✅ | ✅ | 等價 |
| 顯示結果 | ✅ | ✅ | 等價 |
| 保存結果 | ✅ | ✅ | 等價 |
| 交易明細 | ✅ | ✅ | 等價 |

#### Web 界面
- `web_dashboard.py` 和 `web_dashboard_v2.py` 都有回測結果查看功能
- 可以查看所有保存的回測結果
- 提供圖表和詳細分析

### 結論
✅ **可以安全刪除**
- CLI 系統完全覆蓋所有功能
- Web 界面提供更好的結果查看體驗
- 沒有獨特功能

---

## 2. backtest_leverage_comparison.py

### 功能描述
- 槓桿對比測試（1x, 2x, 3x, 5x, 10x, 20x）
- 爆倉檢測（final_capital <= 0）
- 最大連續虧損計算
- 風險調整收益計算
- 與原始滿倉回測對比
- 生成槓桿對比 CSV 報告
- 提供槓桿建議

### 現有系統對應功能

#### CLI Optimizer
```bash
# CLI 優化器可以優化槓桿參數
python3 -m cli_commands.optimize --strategy multi-timeframe-aggressive --method grid
```

**CLI Optimizer 參數網格**:
```python
param_grid = {
    'risk_management.leverage': [3, 5, 7, 10],  # 可以優化槓桿
    # ... 其他參數
}
```

**功能對比**:
| 功能 | backtest_leverage_comparison.py | CLI Optimizer | 差異 |
|------|-------------------------------|---------------|------|
| 測試多個槓桿 | ✅ (1,2,3,5,10,20) | ✅ (3,5,7,10) | 槓桿範圍不同 |
| 爆倉檢測 | ✅ 專門檢測 | ❌ 無 | **獨特功能** |
| 最大連損 | ✅ 計算 | ❌ 無 | **獨特功能** |
| 風險調整收益 | ✅ 計算 | ✅ 有類似指標 | 部分重疊 |
| 對比表格 | ✅ 詳細對比 | ❌ 無 | **獨特功能** |
| 槓桿建議 | ✅ 明確建議 | ❌ 無 | **獨特功能** |
| CSV 報告 | ✅ | ❌ 無 | **獨特功能** |

### 獨特功能分析

#### 1. 爆倉檢測
```python
# backtest_leverage_comparison.py 特有
bankrupted = result.final_capital <= 0

if bankrupted:
    print(f"  ⚠️ 爆倉！")
```
- **價值**: 高槓桿風險評估的關鍵指標
- **現有系統**: 無此功能

#### 2. 最大連續虧損
```python
# backtest_leverage_comparison.py 特有
max_consecutive_losses = 0
current_consecutive_losses = 0
for trade in result.trades:
    if trade.pnl < 0:
        current_consecutive_losses += 1
        max_consecutive_losses = max(max_consecutive_losses, current_consecutive_losses)
    else:
        current_consecutive_losses = 0
```
- **價值**: 心理壓力評估的重要指標
- **現有系統**: 無此功能

#### 3. 槓桿對比表格
```python
# 生成詳細的槓桿對比表
print(f"{'槓桿':<8} {'交易數':<8} {'勝率':<10} {'最終資金':<12} {'收益率':<12} "
      f"{'最大回撤':<12} {'夏普比率':<10} {'獲利因子':<10} {'最大連損':<10} {'狀態':<10}")
```
- **價值**: 一目了然的槓桿選擇參考
- **現有系統**: Optimizer 只輸出最佳參數，無對比表

#### 4. 槓桿建議
```python
print("\n建議：")
print("  - 新手：1-2x 槓桿（安全穩健）")
print("  - 有經驗：3-5x 槓桿（平衡收益風險）")
print("  - 專家：5-10x 槓桿（高收益高風險）")
print("  - ⚠️ 不建議超過 10x 槓桿（極易爆倉）")
```
- **價值**: 實用的風險管理建議
- **現有系統**: 無此功能

### Web 界面
- 搜索結果：**無槓桿對比功能**
- `web_dashboard.py` 和 `web_dashboard_v2.py` 都沒有槓桿分析功能
- 只有提示訊息引用這個腳本

### 結論
⚠️ **建議保留或整合**

**原因**:
1. 有多個獨特功能（爆倉檢測、最大連損、對比表格、槓桿建議）
2. CLI Optimizer 雖然可以優化槓桿，但缺少專門的槓桿分析功能
3. 對於風險管理和槓桿選擇有實用價值

**建議方案**:

#### 方案 A: 保留腳本（最簡單）
- 保持現狀，作為獨立工具使用
- 優點：無需開發，立即可用
- 缺點：與系統架構不一致

#### 方案 B: 整合到 CLI（推薦）
創建新的 CLI 命令：
```bash
python3 -m cli_commands.leverage_analysis --strategy multi-timeframe-aggressive
```
- 優點：與系統架構一致，功能更完整
- 缺點：需要開發時間

#### 方案 C: 整合到 Web 界面
在 Web 界面添加「槓桿分析」頁面
- 優點：更好的用戶體驗
- 缺點：需要更多開發時間

---

## 總結

| 腳本 | 功能覆蓋度 | 獨特功能 | 建議 |
|------|-----------|---------|------|
| backtest_multi_timeframe.py | 100% | 無 | ✅ **刪除** |
| backtest_leverage_comparison.py | 40% | 4個 | ⚠️ **保留或整合** |

### 立即行動
1. ✅ 刪除 `backtest_multi_timeframe.py`
2. ⚠️ 保留 `backtest_leverage_comparison.py`（短期）
3. 📋 計劃將槓桿分析功能整合到 CLI 或 Web（長期）

---

**報告生成時間**: 2026-02-11
