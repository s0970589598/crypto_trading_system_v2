# 策略示例 (Strategy Examples)

本文檔展示系統中的示例策略，幫助您理解不同的策略模式和實現方法。

---

## 目錄

1. [多週期共振策略](#多週期共振策略)
2. [突破策略](#突破策略)
3. [均值回歸策略](#均值回歸策略)
4. [策略對比](#策略對比)
5. [使用建議](#使用建議)

---

## 多週期共振策略

### 策略概述

**文件位置**：
- 實現：`src/strategies/multi_timeframe_strategy.py`
- 配置：`strategies/multi-timeframe-aggressive.json`、`strategies/multi-timeframe-relaxed.json`

**策略類型**：趨勢跟隨

**適用市場**：強趨勢市場（上漲或下跌）

### 核心邏輯

多週期共振策略通過分析多個時間週期的趨勢一致性來確認交易機會。只有當所有週期的趨勢方向一致時才進場。

**進場條件**：
1. 4 小時趨勢明確（Uptrend 或 Downtrend）
2. 1 小時趨勢與 4 小時一致
3. 15 分鐘 RSI 在 30-70 區間
4. 價格接近 1 小時 EMA（3% 範圍內）
5. 成交量大於 20 日平均

**出場條件**：
- 止損：1.5-2.0 ATR
- 目標：3.0-4.0 ATR
- 趨勢反轉

### 配置示例

#### 激進模式

```json
{
  "strategy_id": "multi-timeframe-aggressive",
  "parameters": {
    "stop_loss_atr": 1.5,
    "take_profit_atr": 3.0,
    "rsi_range": [30, 70],
    "ema_distance": 0.03
  },
  "risk_management": {
    "position_size": 0.20,
    "leverage": 5,
    "max_trades_per_day": 3
  }
}
```

**特點**：
- ✅ 較緊的止損（1.5 ATR）
- ✅ 較高的收益目標（3.0 ATR）
- ✅ 更多交易機會
- ⚠️ 需要更頻繁的監控

#### 輕鬆模式

```json
{
  "strategy_id": "multi-timeframe-relaxed",
  "parameters": {
    "stop_loss_atr": 2.0,
    "take_profit_atr": 4.0,
    "rsi_range": [30, 70],
    "ema_distance": 0.03
  },
  "risk_management": {
    "position_size": 0.20,
    "leverage": 5,
    "max_trades_per_day": 2
  }
}
```

**特點**：
- ✅ 較寬的止損（2.0 ATR）
- ✅ 避免過早止損
- ✅ 較少交易次數
- ⚠️ 單筆風險較大

### 回測結果

**激進模式**（2024-01-01 至 2024-12-31）：
```
初始資金：1000 USDT
最終資金：1404 USDT
總收益率：+40.42%
最大回撤：-6.68%
交易次數：33 筆
勝率：54.55%
獲利因子：1.86
```

**輕鬆模式**（2024-01-01 至 2024-12-31）：
```
初始資金：1000 USDT
最終資金：1188 USDT
總收益率：+18.82%
最大回撤：-11.24%
交易次數：22 筆
勝率：45.45%
獲利因子：1.45
```

### 使用示例

```bash
# 回測激進模式
python cli.py backtest \
  --strategy multi-timeframe-aggressive \
  --start 2024-01-01 \
  --end 2024-12-31

# 回測輕鬆模式
python cli.py backtest \
  --strategy multi-timeframe-relaxed \
  --start 2024-01-01 \
  --end 2024-12-31

# 實盤運行
python cli.py live --strategy multi-timeframe-aggressive
```

### 代碼片段

```python
def _check_entry_conditions(self, indicators: dict) -> bool:
    """檢查進場條件"""
    # 多週期趨勢一致
    trend_4h = indicators['trend_4h']
    trend_1h = indicators['trend_1h']
    
    if trend_4h != trend_1h:
        return False
    
    if trend_4h not in ['Uptrend', 'Downtrend']:
        return False
    
    # RSI 在合理範圍
    rsi = indicators['rsi_15m']
    if not (30 <= rsi <= 70):
        return False
    
    # 價格接近 EMA
    price = indicators['price']
    ema = indicators['ema_1h']
    distance = abs(price - ema) / ema
    
    if distance > 0.03:
        return False
    
    # 成交量確認
    if indicators['volume'] <= indicators['volume_ma']:
        return False
    
    return True
```

---

## 突破策略

### 策略概述

**文件位置**：
- 實現：`src/strategies/breakout_strategy.py`
- 配置：`strategies/breakout-strategy.json`

**策略類型**：突破交易

**適用市場**：盤整後的突破、新高/新低

### 核心邏輯

突破策略在價格突破關鍵阻力或支撐位時進場，預期突破後會有持續的趨勢。

**進場條件**：
1. 價格突破 20 日高點（做多）或低點（做空）
2. 突破時成交量放大（> 1.5 倍平均成交量）
3. ATR 顯示波動性增加
4. 價格遠離極端超買/超賣區域

**出場條件**：
- 止損：突破點下方/上方 2.0 ATR
- 目標：突破點上方/下方 4.0 ATR
- 假突破（價格回到突破點以下/以上）

### 配置示例

```json
{
  "strategy_id": "breakout-strategy",
  "strategy_name": "突破策略",
  "version": "1.0.0",
  "enabled": true,
  "symbol": "BTCUSDT",
  "timeframes": ["1d", "4h", "1h"],
  
  "parameters": {
    "breakout_period": 20,
    "volume_multiplier": 1.5,
    "atr_threshold": 1.2,
    "stop_loss_atr": 2.0,
    "take_profit_atr": 4.0
  },
  
  "risk_management": {
    "position_size": 0.25,
    "leverage": 4,
    "max_trades_per_day": 2,
    "max_consecutive_losses": 2,
    "daily_loss_limit": 0.10
  }
}
```

### 使用示例

```bash
# 回測突破策略
python cli.py backtest \
  --strategy breakout-strategy \
  --start 2024-01-01 \
  --end 2024-12-31

# 優化參數
python cli.py optimize \
  --strategy breakout-strategy \
  --method bayesian \
  --iterations 50

# 實盤運行
python cli.py live --strategy breakout-strategy
```

### 代碼片段

```python
def _check_breakout(self, df: pd.DataFrame) -> Tuple[bool, str]:
    """檢查突破"""
    current_price = df['close'].iloc[-1]
    
    # 計算 N 日高點和低點
    high_n = df['high'].rolling(window=self.breakout_period).max().iloc[-2]
    low_n = df['low'].rolling(window=self.breakout_period).min().iloc[-2]
    
    # 檢查向上突破
    if current_price > high_n:
        # 確認成交量
        volume = df['volume'].iloc[-1]
        volume_ma = df['volume'].rolling(window=20).mean().iloc[-1]
        
        if volume > volume_ma * self.volume_multiplier:
            return True, 'long'
    
    # 檢查向下突破
    if current_price < low_n:
        volume = df['volume'].iloc[-1]
        volume_ma = df['volume'].rolling(window=20).mean().iloc[-1]
        
        if volume > volume_ma * self.volume_multiplier:
            return True, 'short'
    
    return False, None
```

---

## 均值回歸策略

### 策略概述

**文件位置**：
- 實現：`src/strategies/mean_reversion_strategy.py`
- 配置：`strategies/mean-reversion.json`

**策略類型**：均值回歸

**適用市場**：震盪市場、低波動性環境

### 核心邏輯

均值回歸策略基於價格會回歸到其平均值的假設。當價格偏離移動平均線過遠時，預期價格會回歸到均線附近。

**進場條件**：
1. 價格偏離 20 日 SMA 超過 2%
2. RSI 顯示超買（>70）或超賣（<30）
3. 價格觸及或突破布林帶
4. 成交量正常（0.5x - 2.0x 平均成交量）

**出場條件**：
- 止損：1.5 ATR
- 目標：2.0 ATR（較小的目標）
- 價格回歸到 SMA 的 0.5% 範圍內
- RSI 回到中性區域（40-60）

### 配置示例

```json
{
  "strategy_id": "mean-reversion-v1",
  "strategy_name": "均值回歸策略",
  "version": "1.0.0",
  "enabled": true,
  "symbol": "BTCUSDT",
  "timeframes": ["1h", "15m"],
  
  "parameters": {
    "sma_period": 20,
    "deviation_threshold": 0.02,
    "rsi_period": 14,
    "rsi_oversold": 30,
    "rsi_overbought": 70,
    "bb_period": 20,
    "bb_std": 2.0,
    "reversion_threshold": 0.005,
    "stop_loss_atr": 1.5,
    "take_profit_atr": 2.0
  },
  
  "risk_management": {
    "position_size": 0.15,
    "leverage": 3,
    "max_trades_per_day": 4,
    "max_consecutive_losses": 3,
    "daily_loss_limit": 0.08
  }
}
```

### 使用示例

```bash
# 回測均值回歸策略
python cli.py backtest \
  --strategy mean-reversion-v1 \
  --start 2024-01-01 \
  --end 2024-12-31

# 優化參數
python cli.py optimize \
  --strategy mean-reversion-v1 \
  --method grid

# 實盤運行
python cli.py live --strategy mean-reversion-v1
```

### 代碼片段

```python
def _check_buy_conditions(self, indicators: Dict) -> bool:
    """檢查買入條件（做多）"""
    current_price = indicators['current_price']
    sma = indicators['sma_1h'].iloc[-1]
    deviation = indicators['deviation_1h'].iloc[-1]
    rsi = indicators['rsi_15m'].iloc[-1]
    bb_lower = indicators['bb_lower_15m'].iloc[-1]
    
    # 價格低於均線且偏離超過閾值
    price_below_sma = deviation < -self.deviation_threshold
    
    # RSI 超賣
    rsi_oversold = rsi < self.rsi_oversold
    
    # 價格觸及布林帶下軌
    price_at_lower_band = current_price <= bb_lower * 1.01
    
    # 成交量正常
    volume = indicators['volume_15m'].iloc[-1]
    volume_ma = indicators['volume_ma_15m'].iloc[-1]
    volume_normal = 0.5 * volume_ma < volume < 2.0 * volume_ma
    
    return price_below_sma and rsi_oversold and price_at_lower_band and volume_normal
```

---

## 策略對比

### 特性對比

| 特性 | 多週期共振 | 突破策略 | 均值回歸 |
|------|-----------|---------|---------|
| **策略類型** | 趨勢跟隨 | 突破交易 | 均值回歸 |
| **適用市場** | 強趨勢 | 盤整突破 | 震盪市場 |
| **交易頻率** | 中等 | 低 | 高 |
| **勝率** | 45-55% | 40-50% | 50-60% |
| **獲利因子** | 1.5-2.0 | 1.8-2.5 | 1.2-1.5 |
| **風險等級** | 中等 | 高 | 低 |
| **建議槓桿** | 5x | 4x | 3x |
| **建議倉位** | 20% | 25% | 15% |

### 性能對比

基於 2024 年回測數據：

| 指標 | 多週期共振（激進） | 突破策略 | 均值回歸 |
|------|------------------|---------|---------|
| **總收益率** | +40.42% | +35.20% | +22.15% |
| **最大回撤** | -6.68% | -12.50% | -5.30% |
| **夏普比率** | 2.34 | 1.85 | 2.10 |
| **交易次數** | 33 | 18 | 45 |
| **勝率** | 54.55% | 44.44% | 55.56% |
| **平均獲利** | +3.2% | +5.8% | +1.8% |
| **平均虧損** | -1.5% | -2.8% | -1.2% |

### 市場適應性

**牛市**：
1. 多週期共振（激進）⭐⭐⭐⭐⭐
2. 突破策略 ⭐⭐⭐⭐
3. 均值回歸 ⭐⭐

**熊市**：
1. 多週期共振（激進）⭐⭐⭐⭐⭐
2. 突破策略 ⭐⭐⭐⭐
3. 均值回歸 ⭐⭐

**震盪市**：
1. 均值回歸 ⭐⭐⭐⭐⭐
2. 多週期共振（輕鬆）⭐⭐⭐
3. 突破策略 ⭐⭐

---

## 使用建議

### 單策略使用

**新手建議**：
```bash
# 從輕鬆模式開始
python cli.py live --strategy multi-timeframe-relaxed
```

**進階交易者**：
```bash
# 使用激進模式
python cli.py live --strategy multi-timeframe-aggressive
```

**震盪市場**：
```bash
# 使用均值回歸
python cli.py live --strategy mean-reversion-v1
```

### 多策略組合

**平衡組合**（推薦）：
```bash
python cli.py live \
  --strategies multi-timeframe-aggressive,mean-reversion-v1 \
  --allocation 0.6,0.4
```

**激進組合**：
```bash
python cli.py live \
  --strategies multi-timeframe-aggressive,breakout-strategy \
  --allocation 0.5,0.5
```

**保守組合**：
```bash
python cli.py live \
  --strategies multi-timeframe-relaxed,mean-reversion-v1 \
  --allocation 0.5,0.5
```

### 參數優化

**優化多週期共振**：
```bash
python cli.py optimize \
  --strategy multi-timeframe-aggressive \
  --method bayesian \
  --iterations 50 \
  --start 2024-01-01 \
  --end 2024-12-31
```

**優化均值回歸**：
```bash
python cli.py optimize \
  --strategy mean-reversion-v1 \
  --method grid \
  --start 2024-01-01 \
  --end 2024-12-31
```

### 風險管理建議

**初學者**：
- 槓桿：3x
- 倉位：10-15%
- 每日最多：1-2 筆交易

**中級交易者**：
- 槓桿：5x
- 倉位：15-20%
- 每日最多：2-3 筆交易

**高級交易者**：
- 槓桿：5-10x
- 倉位：20-30%
- 每日最多：3-5 筆交易

---

## 創建自定義策略

基於這些示例，您可以創建自己的策略：

```bash
# 使用多週期模板
python tools/create_strategy.py \
  --name my-custom-strategy \
  --template multi-timeframe \
  --symbol ETHUSDT

# 使用突破模板
python tools/create_strategy.py \
  --name my-breakout-strategy \
  --template breakout \
  --symbol BTCUSDT

# 使用均值回歸模板
python tools/create_strategy.py \
  --name my-mean-reversion \
  --template mean-reversion \
  --symbol SOLUSDT
```

---

**通過學習這些示例，開發您自己的獲利策略！** 🚀
