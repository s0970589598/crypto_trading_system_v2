# 策略開發指南 (Strategy Development Guide)

本指南詳細介紹如何開發、測試和部署交易策略。

---

## 目錄

1. [策略開發流程](#策略開發流程)
2. [策略模板](#策略模板)
3. [技術指標](#技術指標)
4. [信號生成](#信號生成)
5. [風險管理](#風險管理)
6. [回測和優化](#回測和優化)
7. [最佳實踐](#最佳實踐)
8. [常見問題](#常見問題)

---

## 策略開發流程

### 完整流程

```
1. 策略構思
   ↓
2. 創建策略骨架
   ↓
3. 實現策略邏輯
   ↓
4. 編寫測試
   ↓
5. 回測驗證
   ↓
6. 參數優化
   ↓
7. 模擬盤測試
   ↓
8. 實盤部署
```

### 1. 策略構思

在開始編碼之前，明確以下問題：

**市場假設**：
- 你相信什麼樣的市場行為？
- 這種行為在什麼條件下出現？
- 如何量化這種行為？

**進場條件**：
- 什麼時候進場？
- 需要哪些確認信號？
- 如何避免假信號？

**出場條件**：
- 什麼時候止損？
- 什麼時候獲利？
- 是否需要移動止損？

**風險管理**：
- 每筆交易風險多少？
- 最大回撤容忍度？
- 如何分配資金？

### 2. 創建策略骨架

使用腳手架工具快速創建：

```bash
python tools/create_strategy.py \
  --name my-strategy \
  --template multi-timeframe \
  --symbol BTCUSDT
```

這將生成：
- `src/strategies/my_strategy.py` - 策略實現
- `strategies/my-strategy.json` - 策略配置
- `tests/unit/test_my_strategy.py` - 測試模板

---

## 策略模板

### 基礎模板

```python
from src.execution.strategy import Strategy
from src.models.config import StrategyConfig
from src.models.trading import Signal, Position
from src.models.market_data import MarketData
import pandas as pd
import numpy as np

class MyStrategy(Strategy):
    """我的自定義策略
    
    策略描述：
    - 進場條件：...
    - 出場條件：...
    - 風險管理：...
    """
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        # 初始化策略參數
        self.param1 = config.parameters.get('param1', 10)
        self.param2 = config.parameters.get('param2', 0.5)
    
    def generate_signal(self, market_data: MarketData) -> Signal:
        """生成交易信號"""
        # 1. 驗證數據
        if not self._validate_data(market_data):
            return Signal.hold(self.strategy_id, market_data.timestamp, self.config.symbol)
        
        # 2. 計算指標
        indicators = self._calculate_indicators(market_data)
        
        # 3. 檢查進場條件
        if self._check_buy_conditions(indicators):
            return self._create_buy_signal(market_data, indicators)
        elif self._check_sell_conditions(indicators):
            return self._create_sell_signal(market_data, indicators)
        
        # 4. 默認持有
        return Signal.hold(self.strategy_id, market_data.timestamp, self.config.symbol)
    
    def _validate_data(self, market_data: MarketData) -> bool:
        """驗證數據完整性"""
        try:
            for timeframe in self.config.timeframes:
                data = market_data.get_timeframe(timeframe)
                if data is None or len(data.ohlcv) < 100:
                    return False
            return True
        except Exception:
            return False
    
    def _calculate_indicators(self, market_data: MarketData) -> dict:
        """計算技術指標"""
        indicators = {}
        
        # 獲取不同週期的數據
        data_1h = market_data.get_timeframe('1h')
        data_15m = market_data.get_timeframe('15m')
        
        # 計算指標
        indicators['ema_20'] = self._calculate_ema(data_1h.ohlcv['close'], 20)
        indicators['rsi'] = self._calculate_rsi(data_15m.ohlcv['close'], 14)
        indicators['atr'] = self._calculate_atr(data_15m.ohlcv, 14)
        
        return indicators
    
    def _check_buy_conditions(self, indicators: dict) -> bool:
        """檢查買入條件"""
        # 實現你的買入邏輯
        return False
    
    def _check_sell_conditions(self, indicators: dict) -> bool:
        """檢查賣出條件"""
        # 實現你的賣出邏輯
        return False
    
    def _create_buy_signal(self, market_data: MarketData, indicators: dict) -> Signal:
        """創建買入信號"""
        latest = market_data.get_timeframe('15m').get_latest()
        entry_price = latest['close']
        atr = indicators['atr'].iloc[-1]
        
        return Signal(
            strategy_id=self.strategy_id,
            timestamp=market_data.timestamp,
            symbol=self.config.symbol,
            action='BUY',
            direction='long',
            entry_price=entry_price,
            stop_loss=self.calculate_stop_loss(entry_price, 'long', atr),
            take_profit=self.calculate_take_profit(entry_price, 'long', atr),
            position_size=0,  # 由執行引擎計算
            confidence=0.8,
            metadata={'indicators': indicators}
        )
    
    def calculate_position_size(self, capital: float, price: float) -> float:
        """計算倉位大小"""
        position_pct = self.config.risk_management.position_size
        leverage = self.config.risk_management.leverage
        return (capital * position_pct * leverage) / price
    
    def calculate_stop_loss(self, entry_price: float, direction: str, atr: float) -> float:
        """計算止損價格"""
        stop_loss_atr = self.config.parameters.get('stop_loss_atr', 1.5)
        if direction == 'long':
            return entry_price - (atr * stop_loss_atr)
        else:
            return entry_price + (atr * stop_loss_atr)
    
    def calculate_take_profit(self, entry_price: float, direction: str, atr: float) -> float:
        """計算目標價格"""
        take_profit_atr = self.config.parameters.get('take_profit_atr', 3.0)
        if direction == 'long':
            return entry_price + (atr * take_profit_atr)
        else:
            return entry_price - (atr * take_profit_atr)
    
    def should_exit(self, position: Position, market_data: MarketData) -> bool:
        """判斷是否應該出場"""
        latest = market_data.get_timeframe('15m').get_latest()
        current_price = latest['close']
        
        # 檢查止損和目標
        if position.direction == 'long':
            if current_price <= position.stop_loss:
                return True
            if current_price >= position.take_profit:
                return True
        else:
            if current_price >= position.stop_loss:
                return True
            if current_price <= position.take_profit:
                return True
        
        return False
    
    # 輔助方法
    def _calculate_ema(self, series: pd.Series, period: int) -> pd.Series:
        """計算 EMA"""
        return series.ewm(span=period, adjust=False).mean()
    
    def _calculate_rsi(self, series: pd.Series, period: int) -> pd.Series:
        """計算 RSI"""
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def _calculate_atr(self, df: pd.DataFrame, period: int) -> pd.Series:
        """計算 ATR"""
        high = df['high']
        low = df['low']
        close = df['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        return tr.rolling(window=period).mean()
```

---

## 技術指標

### 常用指標實現

#### 移動平均線 (MA)

```python
def calculate_sma(self, series: pd.Series, period: int) -> pd.Series:
    """簡單移動平均"""
    return series.rolling(window=period).mean()

def calculate_ema(self, series: pd.Series, period: int) -> pd.Series:
    """指數移動平均"""
    return series.ewm(span=period, adjust=False).mean()
```

#### 相對強弱指標 (RSI)

```python
def calculate_rsi(self, series: pd.Series, period: int = 14) -> pd.Series:
    """RSI 指標"""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))
```

#### 平均真實範圍 (ATR)

```python
def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
    """ATR 指標"""
    high = df['high']
    low = df['low']
    close = df['close']
    
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    return tr.rolling(window=period).mean()
```

#### 布林帶 (Bollinger Bands)

```python
def calculate_bollinger_bands(
    self,
    series: pd.Series,
    period: int = 20,
    std_dev: float = 2.0
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """布林帶"""
    middle = series.rolling(window=period).mean()
    std = series.rolling(window=period).std()
    upper = middle + (std * std_dev)
    lower = middle - (std * std_dev)
    return upper, middle, lower
```

#### MACD

```python
def calculate_macd(
    self,
    series: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """MACD 指標"""
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram
```

---

## 信號生成

### 信號類型

系統支持三種信號類型：

1. **BUY**: 買入信號（做多）
2. **SELL**: 賣出信號（做空）
3. **HOLD**: 持有信號（不交易）

### 信號生成模式

#### 模式 1：趨勢跟隨

```python
def _check_trend_following(self, indicators: dict) -> bool:
    """趨勢跟隨策略"""
    # 價格在均線之上
    price_above_ma = indicators['close'] > indicators['ema_50']
    
    # 短期均線在長期均線之上
    golden_cross = indicators['ema_20'] > indicators['ema_50']
    
    # RSI 不超買
    rsi_ok = indicators['rsi'] < 70
    
    return price_above_ma and golden_cross and rsi_ok
```

#### 模式 2：均值回歸

```python
def _check_mean_reversion(self, indicators: dict) -> bool:
    """均值回歸策略"""
    # 價格偏離均線
    price = indicators['close']
    ma = indicators['sma_20']
    deviation = abs(price - ma) / ma
    
    # 偏離超過閾值
    oversold = deviation > 0.02 and price < ma
    
    # RSI 超賣
    rsi_oversold = indicators['rsi'] < 30
    
    return oversold and rsi_oversold
```

#### 模式 3：突破策略

```python
def _check_breakout(self, indicators: dict) -> bool:
    """突破策略"""
    # 價格突破布林帶上軌
    price = indicators['close']
    upper_band = indicators['bb_upper']
    
    # 成交量放大
    volume = indicators['volume']
    volume_ma = indicators['volume_ma']
    volume_surge = volume > volume_ma * 1.5
    
    return price > upper_band and volume_surge
```

### 多週期確認

```python
def _check_multi_timeframe_alignment(self, market_data: MarketData) -> bool:
    """多週期趨勢一致性"""
    # 獲取不同週期的趨勢
    trend_1d = self._get_trend(market_data.get_timeframe('1d'))
    trend_4h = self._get_trend(market_data.get_timeframe('4h'))
    trend_1h = self._get_trend(market_data.get_timeframe('1h'))
    
    # 所有週期趨勢一致
    return trend_1d == trend_4h == trend_1h == 'Uptrend'

def _get_trend(self, timeframe_data) -> str:
    """判斷趨勢方向"""
    df = timeframe_data.ohlcv
    ema_20 = df['close'].ewm(span=20).mean()
    ema_50 = df['close'].ewm(span=50).mean()
    
    if ema_20.iloc[-1] > ema_50.iloc[-1]:
        return 'Uptrend'
    elif ema_20.iloc[-1] < ema_50.iloc[-1]:
        return 'Downtrend'
    else:
        return 'Sideways'
```

---

## 風險管理

### 倉位計算

#### 固定比例

```python
def calculate_position_size(self, capital: float, price: float) -> float:
    """固定比例倉位"""
    position_pct = 0.20  # 20% 資金
    leverage = 5
    return (capital * position_pct * leverage) / price
```

#### 基於波動性

```python
def calculate_position_size_volatility(
    self,
    capital: float,
    price: float,
    atr: float
) -> float:
    """基於波動性的倉位計算"""
    risk_per_trade = 0.02  # 每筆風險 2%
    stop_loss_atr = 1.5
    
    # 計算止損距離
    stop_distance = atr * stop_loss_atr
    
    # 計算倉位大小
    risk_amount = capital * risk_per_trade
    position_size = risk_amount / stop_distance
    
    return position_size
```

#### 凱利公式

```python
def calculate_position_size_kelly(
    self,
    capital: float,
    price: float,
    win_rate: float,
    avg_win: float,
    avg_loss: float
) -> float:
    """凱利公式倉位計算"""
    # 凱利比例
    kelly_pct = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
    
    # 使用半凱利（更保守）
    kelly_pct = kelly_pct * 0.5
    
    # 限制最大倉位
    kelly_pct = min(kelly_pct, 0.25)
    
    return (capital * kelly_pct) / price
```

### 止損策略

#### 固定 ATR 止損

```python
def calculate_stop_loss(self, entry_price: float, direction: str, atr: float) -> float:
    """固定 ATR 止損"""
    stop_loss_atr = 1.5
    if direction == 'long':
        return entry_price - (atr * stop_loss_atr)
    else:
        return entry_price + (atr * stop_loss_atr)
```

#### 百分比止損

```python
def calculate_stop_loss_percentage(
    self,
    entry_price: float,
    direction: str,
    stop_pct: float = 0.02
) -> float:
    """百分比止損"""
    if direction == 'long':
        return entry_price * (1 - stop_pct)
    else:
        return entry_price * (1 + stop_pct)
```

#### 支撐/阻力止損

```python
def calculate_stop_loss_support(
    self,
    entry_price: float,
    direction: str,
    market_data: MarketData
) -> float:
    """基於支撐/阻力的止損"""
    df = market_data.get_timeframe('1h').ohlcv
    
    if direction == 'long':
        # 找最近的支撐位
        recent_lows = df['low'].tail(20)
        support = recent_lows.min()
        return support * 0.99  # 略低於支撐位
    else:
        # 找最近的阻力位
        recent_highs = df['high'].tail(20)
        resistance = recent_highs.max()
        return resistance * 1.01  # 略高於阻力位
```

---

## 回測和優化

### 回測策略

```bash
# 基本回測
python cli.py backtest \
  --strategy my-strategy \
  --start 2024-01-01 \
  --end 2024-12-31

# 指定初始資金
python cli.py backtest \
  --strategy my-strategy \
  --start 2024-01-01 \
  --end 2024-12-31 \
  --initial-capital 10000

# 保存結果
python cli.py backtest \
  --strategy my-strategy \
  --start 2024-01-01 \
  --end 2024-12-31 \
  --output results.json
```

### 參數優化

```bash
# 網格搜索
python cli.py optimize \
  --strategy my-strategy \
  --method grid \
  --start 2024-01-01 \
  --end 2024-12-31

# 隨機搜索
python cli.py optimize \
  --strategy my-strategy \
  --method random \
  --iterations 100

# 貝葉斯優化
python cli.py optimize \
  --strategy my-strategy \
  --method bayesian \
  --iterations 50
```

### 優化參數定義

在策略配置中定義優化範圍：

```json
{
  "optimization": {
    "parameters": {
      "stop_loss_atr": {
        "type": "float",
        "min": 1.0,
        "max": 3.0,
        "step": 0.5
      },
      "take_profit_atr": {
        "type": "float",
        "min": 2.0,
        "max": 5.0,
        "step": 0.5
      },
      "rsi_period": {
        "type": "int",
        "min": 10,
        "max": 20,
        "step": 2
      }
    }
  }
}
```

---

## 最佳實踐

### 1. 策略設計原則

**簡單優於複雜**：
- 避免過度優化
- 使用簡單的邏輯
- 容易理解和維護

**數據驅動**：
- 基於歷史數據驗證
- 使用統計方法
- 避免主觀判斷

**風險優先**：
- 先考慮風險管理
- 再考慮收益優化
- 保護資本是第一要務

### 2. 代碼質量

**可讀性**：
```python
# 好的例子
def _check_buy_conditions(self, indicators: dict) -> bool:
    """檢查買入條件"""
    trend_ok = indicators['trend'] == 'Uptrend'
    rsi_ok = 30 < indicators['rsi'] < 70
    volume_ok = indicators['volume'] > indicators['volume_ma']
    return trend_ok and rsi_ok and volume_ok

# 壞的例子
def chk(self, i):
    return i['t']=='U' and 30<i['r']<70 and i['v']>i['vm']
```

**錯誤處理**：
```python
def generate_signal(self, market_data: MarketData) -> Signal:
    try:
        return self._generate_signal_impl(market_data)
    except KeyError as e:
        logger.error(f"Missing data: {e}")
        return Signal.hold(...)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return Signal.hold(...)
```

### 3. 測試覆蓋

**單元測試**：
- 測試每個方法
- 測試邊緣情況
- 測試錯誤處理

**回測驗證**：
- 多個時間段
- 不同市場條件
- 樣本外測試

### 4. 性能優化

**向量化操作**：
```python
# 好的例子（向量化）
df['ema'] = df['close'].ewm(span=20).mean()

# 壞的例子（循環）
ema = []
for i in range(len(df)):
    ema.append(calculate_ema_single(df['close'].iloc[i]))
```

**緩存計算**：
```python
def _calculate_indicators(self, market_data: MarketData) -> dict:
    # 緩存已計算的指標
    cache_key = f"{market_data.timestamp}_{self.strategy_id}"
    if cache_key in self._indicator_cache:
        return self._indicator_cache[cache_key]
    
    indicators = self._compute_indicators(market_data)
    self._indicator_cache[cache_key] = indicators
    return indicators
```

---

## 常見問題

### Q: 如何處理數據缺失？

```python
def _validate_data(self, market_data: MarketData) -> bool:
    """驗證數據完整性"""
    try:
        for timeframe in self.config.timeframes:
            data = market_data.get_timeframe(timeframe)
            if data is None:
                logger.warning(f"Missing {timeframe} data")
                return False
            if len(data.ohlcv) < 100:
                logger.warning(f"Insufficient {timeframe} data")
                return False
        return True
    except Exception as e:
        logger.error(f"Data validation error: {e}")
        return False
```

### Q: 如何避免過度擬合？

1. **使用樣本外測試**：
   - 訓練集：60%
   - 驗證集：20%
   - 測試集：20%

2. **限制參數數量**：
   - 少於 5 個可調參數
   - 使用簡單的邏輯

3. **交叉驗證**：
   - 多個時間段測試
   - 不同市場條件

### Q: 如何提高策略穩定性？

1. **多週期確認**：
   - 使用多個時間週期
   - 確保趨勢一致

2. **多指標確認**：
   - 使用多個技術指標
   - 避免單一指標依賴

3. **風險控制**：
   - 嚴格止損
   - 限制倉位
   - 分散交易

---

**開發出色的策略，實現穩定收益！** 🚀
