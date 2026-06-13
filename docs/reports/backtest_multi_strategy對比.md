# backtest_multi_strategy vs backtest_multi_timeframe 對比

**快速對比**

---

## 核心差異

### backtest_multi_timeframe.py
**目的**: 回測**單一策略**

```python
# 載入 1 個策略
config_file = "strategies/multi-timeframe-aggressive.json"
strategy = MultiTimeframeStrategy(config)

# 運行單策略回測
result = engine.run_single_strategy(strategy, market_data)

# 輸出 1 個結果
print(f"總損益：{result.total_pnl:.2f} USDT")
```

---

### backtest_multi_strategy.py
**目的**: 回測**多個策略組合**

```python
# 載入 2 個策略
strategies = [
    MultiTimeframeStrategy(config1),  # 多週期共振策略
    BreakoutStrategy(config2)         # 突破策略
]

# 定義資金分配
capital_allocation = {
    "multi-timeframe-aggressive": 0.5,  # 50%
    "breakout-strategy": 0.5            # 50%
}

# 運行多策略回測
results_dict = engine.run_multi_strategy(
    strategies,
    market_data,
    capital_allocation
)

# 輸出多個結果 + 整體結果
for strategy_id, result in results_dict.items():
    print(f"{strategy_id}: {result.total_pnl:.2f} USDT")
print(f"整體損益：{total_pnl:.2f} USDT")
```

---

## 功能對比表

| 特性 | backtest_multi_timeframe | backtest_multi_strategy |
|------|-------------------------|------------------------|
| **策略數量** | 1 個 | 2+ 個 |
| **資金分配** | 100% 單一策略 | 可配置（如 50%/50%） |
| **回測方法** | `run_single_strategy()` | `run_multi_strategy()` |
| **結果數量** | 1 個 | N 個 + 1 個整體 |
| **策略隔離** | 不適用 | ✅ 驗證策略隔離 |
| **交易標記** | 無 | ✅ 標記策略來源 |
| **整體指標** | 不適用 | ✅ 計算組合指標 |

---

## 使用場景

### backtest_multi_timeframe.py
**適用於**:
- 測試單一策略
- 快速驗證策略邏輯
- 優化單一策略參數

**示例**:
```bash
# 測試多週期共振策略
python3 backtest_multi_timeframe.py
```

---

### backtest_multi_strategy.py
**適用於**:
- 測試策略組合
- 驗證策略隔離
- 對比不同策略表現
- 測試資金分配策略

**示例**:
```bash
# 測試多週期 + 突破策略組合
python3 backtest_multi_strategy.py
```

---

## CLI 對應功能

### 單策略回測
```bash
# 替代 backtest_multi_timeframe.py
python3 cli.py backtest --strategy multi-timeframe-aggressive
```

### 多策略回測
```bash
# 替代 backtest_multi_strategy.py
python3 cli.py backtest \
  --strategy multi-timeframe-aggressive \
  --strategy breakout-strategy
```

---

## Web 界面對應功能

### 單策略回測
- web_dashboard_v2.py
- 回測系統 → 單策略回測結果

### 多策略回測
- web_dashboard_v2.py
- 回測系統 → 多策略組合回測

---

## 結論

### 完全不一樣！

| 維度 | 結論 |
|------|------|
| **目的** | 不同（單策略 vs 多策略） |
| **功能** | 不同（簡單回測 vs 組合回測） |
| **輸出** | 不同（1 個結果 vs N+1 個結果） |
| **用途** | 不同（策略測試 vs 組合測試） |

### 狀態

| 腳本 | 位置 | 狀態 |
|------|------|------|
| backtest_multi_timeframe.py | 根目錄 | ✅ 可刪除（CLI/Web 替代） |
| backtest_multi_strategy.py | _Archive/ | ✅ 已歸檔 |

---

## 建議

### backtest_multi_timeframe.py
✅ **刪除** - CLI 和 Web 完全替代

### backtest_multi_strategy.py
✅ **保持歸檔** - 已經在 _Archive/ 中

如果需要多策略回測，使用：
```bash
# CLI（推薦）
python3 cli.py backtest --strategy strategy1 --strategy strategy2

# 或 Web 界面
# 回測系統 → 多策略組合回測
```

---

**總結**: 兩個腳本功能完全不同，backtest_multi_strategy.py 已經歸檔，backtest_multi_timeframe.py 可以刪除。
