# 市場分析器 EMA 更新說明

## 更新日期
2026-02-06

## 變更內容

### 從 SMA 改為 EMA

為了與主要交易策略（多時框策略）保持一致，市場分析器已更新為使用 **EMA（指數移動平均）** 作為主要趨勢指標。

### 具體變更

#### 1. 指標計算 (`calculate_indicators`)
- **新增 EMA 指標**：
  - `ema_7`：7 週期 EMA（短期）
  - `ema_20`：20 週期 EMA（中期）
  - `ema_50`：50 週期 EMA（長期）
  - `ema_12`、`ema_26`：MACD 計算用

- **保留 SMA 指標**（作為參考）：
  - `sma_7`、`sma_25`、`sma_99`

#### 2. 趨勢分析 (`_analyze_trend`)
- **改用 EMA 7、20、50** 判斷趨勢
- 多頭排列：EMA 7 > EMA 20 > EMA 50
- 空頭排列：EMA 7 < EMA 20 < EMA 50

#### 3. 趨勢強度 (`_calculate_trend_strength`)
- 基於 **EMA 7 和 EMA 20 的斜率**計算
- 更靈敏地反應市場變化

#### 4. 均線排列 (`_analyze_ma_alignment`)
- 改用 **EMA 7、20、50** 判斷排列
- bullish：EMA 7 > EMA 20 > EMA 50
- bearish：EMA 7 < EMA 20 < EMA 50
- mixed：其他情況

#### 5. 市場分析結果
返回的分析數據現在包含：
- **EMA 數據**（主要）：`ema_7`, `ema_20`, `ema_50`, `ema_12`, `ema_26`
- **SMA 數據**（參考）：`sma_7`, `sma_25`, `sma_99`

### 為什麼使用 EMA？

1. **與策略一致**：多時框策略使用 EMA 20 和 EMA 50 作為進場條件
2. **更靈敏**：EMA 對最近價格變化反應更快
3. **減少滯後**：相比 SMA，EMA 的滯後性更小
4. **業界標準**：大多數專業交易者使用 EMA

### 圖表顯示

Web 界面的市場分析圖表現在顯示：
- **K 線圖**：EMA 12 和 EMA 26（橙色和藍色線）
- **布林帶**：仍使用 SMA 20（布林帶標準做法）
- **MACD**：基於 EMA 12 和 EMA 26
- **其他指標**：RSI、ATR、成交量

### 評分系統

自動評分系統現在使用 EMA 進行：
- 趨勢方向判斷
- 趨勢強度評估
- 均線排列分析

這確保了評分邏輯與實際交易策略完全一致。

### 向後兼容

- 舊的市場分析數據仍然可以正常顯示
- SMA 數據仍然被計算和保存（作為參考）
- 不影響已有的評分記錄

## 使用建議

1. **重新評分**：建議對舊交易重新進行自動評分，以使用新的 EMA 分析
2. **策略開發**：新策略應優先使用 EMA 指標
3. **圖表分析**：查看市場分析時，關注 EMA 線的排列和交叉

## 技術細節

### EMA 計算公式
```python
df['ema_N'] = df['close'].ewm(span=N, adjust=False).mean()
```

### 趨勢判斷邏輯
```python
if ema_7 > ema_20 > ema_50:
    trend = 'strong_uptrend'  # 強勢上升
elif ema_7 > ema_20:
    trend = 'uptrend'  # 上升
elif ema_7 < ema_20 < ema_50:
    trend = 'strong_downtrend'  # 強勢下降
elif ema_7 < ema_20:
    trend = 'downtrend'  # 下降
else:
    trend = 'sideways'  # 震盪
```

## 相關文件

- `src/analysis/market_analyzer.py`：市場分析器主文件
- `web_dashboard_v2.py`：Web 界面（包含圖表顯示）
- `src/strategies/multi_timeframe_strategy.py`：多時框策略（使用 EMA）
