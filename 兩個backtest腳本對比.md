# backtest_multi_timeframe.py vs backtest_leverage_comparison.py

**快速對比**

---

## 核心差異

### backtest_multi_timeframe.py
**目的**: 回測單一策略（multi-timeframe-aggressive）

**核心邏輯**:
```python
# 1. 載入一個策略配置
config_file = "strategies/multi-timeframe-aggressive.json"
config = StrategyConfig.from_dict(config_dict)
strategy = MultiTimeframeStrategy(config)

# 2. 運行一次回測
engine = BacktestEngine(1000.0, 0.0005)
result = engine.run_single_strategy(strategy, market_data)

# 3. 顯示結果
print(f"總損益：{result.total_pnl:.2f} USDT")
print(f"勝率：{result.win_rate:.2f}%")
```

**輸出**: 單一回測結果

---

### backtest_leverage_comparison.py
**目的**: 對比不同槓桿的表現（1x, 2x, 3x, 5x, 10x, 20x）

**核心邏輯**:
```python
# 1. 測試多個配置
configs = [
    ("strategies/multi-timeframe-aggressive.json", "激進模式"),
    ("strategies/multi-timeframe-relaxed.json", "輕鬆模式")
]

# 2. 測試多個槓桿
leverages = [1, 2, 3, 5, 10, 20]

# 3. 運行多次回測（2 個配置 × 6 個槓桿 = 12 次）
for config_file, mode_name in configs:
    for leverage in leverages:
        # 修改槓桿參數
        config_dict['risk_management']['leverage'] = leverage
        
        # 運行回測
        result = run_backtest_with_leverage(leverage, config_file, market_data)
        
        # 檢查爆倉
        bankrupted = result.final_capital <= 0
        
        # 計算最大連損
        max_consecutive_losses = calculate_max_consecutive_losses(result.trades)
        
        # 保存結果
        mode_results.append({
            'leverage': leverage,
            'total_return': result.total_pnl_pct,
            'max_drawdown': result.max_drawdown_pct,
            'bankrupted': bankrupted,
            'max_consecutive_losses': max_consecutive_losses
        })

# 4. 生成對比表格
print(f"{'槓桿':<8} {'收益率':<12} {'最大回撤':<12} {'最大連損':<10} {'狀態':<10}")
for r in mode_results:
    status = "爆倉 ❌" if r['bankrupted'] else "存活 ✅"
    print(f"{r['leverage']}x  {r['total_return']:+.2f}%  {r['max_drawdown']:.2f}%  {r['max_consecutive_losses']}  {status}")

# 5. 保存 CSV 報告
df = pd.DataFrame(mode_results)
df.to_csv('leverage_comparison_激進模式_1.5_ATR.csv', index=False)

# 6. 提供槓桿建議
print("建議：")
print("  - 新手：1-2x 槓桿")
print("  - 有經驗：3-5x 槓桿")
print("  - 專家：5-10x 槓桿")
```

**輸出**: 槓桿對比表格 + CSV 報告 + 建議

---

## 功能對比表

| 特性 | backtest_multi_timeframe.py | backtest_leverage_comparison.py |
|------|---------------------------|-------------------------------|
| **回測次數** | 1 次 | 12 次（2配置 × 6槓桿） |
| **測試參數** | 無（使用配置中的參數） | 槓桿（1,2,3,5,10,20） |
| **配置檔案** | 1 個（multi-timeframe-aggressive） | 2 個（aggressive + relaxed） |
| **爆倉檢測** | ❌ | ✅ |
| **最大連損** | ❌ | ✅ |
| **對比表格** | ❌ | ✅ |
| **CSV 報告** | ❌ | ✅ |
| **槓桿建議** | ❌ | ✅ |
| **執行時間** | ~10 秒 | ~2 分鐘 |

---

## 類比說明

### backtest_multi_timeframe.py
就像**拍一張照片**：
- 拍攝一個場景（一個策略配置）
- 得到一張照片（一個回測結果）

### backtest_leverage_comparison.py
就像**拍一組對比照**：
- 拍攝同一場景的多個版本（不同槓桿）
- 排列成對比圖（對比表格）
- 分析哪個版本最好（槓桿建議）

---

## 結論

### 完全不一樣！

| 維度 | 結論 |
|------|------|
| **目的** | 不同（單次回測 vs 槓桿對比） |
| **功能** | 不同（基礎回測 vs 參數分析） |
| **輸出** | 不同（單一結果 vs 對比表格） |
| **用途** | 不同（測試策略 vs 選擇槓桿） |

### 關係

```
backtest_multi_timeframe.py
    ↓ 是基礎
    ↓ 被調用多次
backtest_leverage_comparison.py
    ↓ 生成對比
    ↓ 提供建議
槓桿選擇決策
```

---

## 是否可以刪除？

### backtest_multi_timeframe.py
✅ **可以刪除** - CLI 完全替代

### backtest_leverage_comparison.py
⚠️ **建議保留** - 有獨特的槓桿分析功能

---

**總結**: 這是兩個完全不同的工具，一個是基礎回測，一個是槓桿分析。
