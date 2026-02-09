# 開發者指南 (Developer Guide)

本指南面向希望理解系統架構、開發新策略或貢獻代碼的開發者。

---

## 目錄

1. [系統架構](#系統架構)
2. [開發環境設置](#開發環境設置)
3. [策略開發](#策略開發)
4. [測試指南](#測試指南)
5. [代碼規範](#代碼規範)
6. [貢獻流程](#貢獻流程)

---

## 系統架構

### 五層架構設計

系統採用分層架構，確保各層職責清晰、解耦：

```
┌─────────────────────────────────────────────────────────────┐
│                      策略層 (Strategy Layer)                  │
│  - 策略配置文件 (JSON)                                         │
│  - 策略版本管理                                                │
│  - 策略啟用/停用控制                                           │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                     管理層 (Management Layer)                 │
│  - StrategyManager: 策略生命週期管理                          │
│  - RiskManager: 全局和策略級風險控制                          │
│  - DataManager: 統一數據接口和緩存                            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                     執行層 (Execution Layer)                  │
│  - BacktestEngine: 歷史數據回測                               │
│  - LiveTrader: 實盤交易執行                                   │
│  - MultiStrategyExecutor: 多策略協調                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                     分析層 (Analysis Layer)                   │
│  - Optimizer: 參數優化                                        │
│  - LossAnalyzer: 虧損分析                                     │
│  - PerformanceMonitor: 性能監控                               │
│  - ReviewSystem: 交易覆盤                                     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                      數據層 (Data Layer)                      │
│  - 市場數據存儲                                                │
│  - 交易歷史記錄                                                │
│  - 回測結果持久化                                              │
└─────────────────────────────────────────────────────────────┘
```

### 核心組件

#### 1. Strategy Interface (策略接口)

所有策略必須實現的標準接口：

```python
from abc import ABC, abstractmethod
from src.models.config import StrategyConfig
from src.models.trading import Signal, Position
from src.models.market_data import MarketData

class Strategy(ABC):
    """策略基類"""
    
    def __init__(self, config: StrategyConfig):
        self.config = config
        self.strategy_id = config.strategy_id
    
    @abstractmethod
    def generate_signal(self, market_data: MarketData) -> Signal:
        """生成交易信號
        
        Args:
            market_data: 市場數據（包含多週期 OHLCV 和指標）
        
        Returns:
            Signal: 交易信號（BUY/SELL/HOLD）
        """
        pass
    
    @abstractmethod
    def calculate_position_size(self, capital: float, price: float) -> float:
        """計算倉位大小"""
        pass
    
    @abstractmethod
    def calculate_stop_loss(self, entry_price: float, direction: str, atr: float) -> float:
        """計算止損價格"""
        pass
    
    @abstractmethod
    def calculate_take_profit(self, entry_price: float, direction: str, atr: float) -> float:
        """計算目標價格"""
        pass
    
    @abstractmethod
    def should_exit(self, position: Position, market_data: MarketData) -> bool:
        """判斷是否應該出場"""
        pass
```

#### 2. StrategyManager (策略管理器)

負責策略的生命週期管理：

```python
class StrategyManager:
    """策略管理器"""
    
    def __init__(self, strategies_dir: str = "strategies/"):
        self.strategies_dir = strategies_dir
        self.strategies: Dict[str, Strategy] = {}
        self.strategy_states: Dict[str, StrategyState] = {}
    
    def load_strategies(self) -> List[str]:
        """從配置文件載入所有策略"""
        pass
    
    def validate_config(self, config: dict) -> Tuple[bool, str]:
        """驗證策略配置"""
        pass
    
    def enable_strategy(self, strategy_id: str) -> bool:
        """啟用策略"""
        pass
    
    def disable_strategy(self, strategy_id: str) -> bool:
        """停用策略"""
        pass
    
    def reload_strategy(self, strategy_id: str) -> bool:
        """熱重載策略配置"""
        pass
```

#### 3. RiskManager (風險管理器)

提供系統級風險控制：

```python
class RiskManager:
    """風險管理器"""
    
    def __init__(self, config: RiskConfig):
        self.config = config
        self.global_state = GlobalRiskState()
    
    def check_global_risk(self) -> Tuple[bool, str]:
        """檢查全局風險限制"""
        pass
    
    def check_strategy_risk(self, strategy_id: str, signal: Signal) -> Tuple[bool, str]:
        """檢查策略級風險限制"""
        pass
    
    def should_halt_trading(self) -> Tuple[bool, str]:
        """判斷是否應該暫停所有交易"""
        pass
```

#### 4. BacktestEngine (回測引擎)

統一的回測引擎：

```python
class BacktestEngine:
    """回測引擎"""
    
    def __init__(self, initial_capital: float, commission: float = 0.0005):
        self.initial_capital = initial_capital
        self.commission = commission
    
    def run_single_strategy(
        self,
        strategy: Strategy,
        market_data: Dict[str, pd.DataFrame],
        start_date: datetime,
        end_date: datetime
    ) -> BacktestResult:
        """回測單個策略"""
        pass
    
    def run_multi_strategy(
        self,
        strategies: List[Strategy],
        market_data: Dict[str, pd.DataFrame],
        start_date: datetime,
        end_date: datetime,
        capital_allocation: Dict[str, float]
    ) -> MultiStrategyBacktestResult:
        """回測多策略組合"""
        pass
```

---

## 開發環境設置

### 1. 克隆倉庫

```bash
git clone <repository-url>
cd multi-strategy-trading-system
```

### 2. 創建虛擬環境

```bash
# 使用 venv
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 使用 conda
conda create -n trading python=3.9
conda activate trading
```

### 3. 安裝依賴

```bash
# 安裝生產依賴
pip install -r requirements.txt

# 安裝開發依賴
pip install -r requirements-dev.txt
```

### 4. 配置環境變數

創建 `.env` 文件：

```bash
# API Keys
BINANCE_API_KEY=your_api_key
BINANCE_API_SECRET=your_api_secret

# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# 環境
ENVIRONMENT=development
```

### 5. 運行測試

```bash
# 運行所有測試
pytest

# 運行特定測試
pytest tests/unit/test_strategy_manager.py

# 生成覆蓋率報告
pytest --cov=src --cov-report=html
```

---

## 策略開發

### 快速開始：使用腳手架工具

```bash
# 創建新策略
python tools/create_strategy.py \
  --name my-new-strategy \
  --template multi-timeframe \
  --symbol BTCUSDT
```

這將生成：
- `src/strategies/my_new_strategy.py` - 策略實現
- `strategies/my-new-strategy.json` - 策略配置
- `tests/unit/test_my_new_strategy.py` - 單元測試模板

### 手動創建策略

#### 步驟 1：創建策略類

創建 `src/strategies/my_strategy.py`：

```python
from src.execution.strategy import Strategy
from src.models.config import StrategyConfig
from src.models.trading import Signal, Position
from src.models.market_data import MarketData
import pandas as pd

class MyStrategy(Strategy):
    """我的自定義策略"""
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        # 初始化策略特定的參數
        self.param1 = config.parameters.get('param1', 10)
        self.param2 = config.parameters.get('param2', 0.5)
    
    def generate_signal(self, market_data: MarketData) -> Signal:
        """生成交易信號"""
        # 獲取最新數據
        latest_1h = market_data.get_timeframe('1h').get_latest()
        latest_15m = market_data.get_timeframe('15m').get_latest()
        
        # 實現你的信號邏輯
        if self._check_buy_conditions(latest_1h, latest_15m):
            return Signal(
                strategy_id=self.strategy_id,
                timestamp=market_data.timestamp,
                symbol=self.config.symbol,
                action='BUY',
                direction='long',
                entry_price=latest_15m['close'],
                stop_loss=self.calculate_stop_loss(
                    latest_15m['close'], 'long', latest_15m['atr']
                ),
                take_profit=self.calculate_take_profit(
                    latest_15m['close'], 'long', latest_15m['atr']
                ),
                position_size=self.calculate_position_size(
                    capital=1000,  # 這會由執行引擎提供
                    price=latest_15m['close']
                ),
                confidence=0.8,
                metadata={'reason': 'buy_condition_met'}
            )
        
        return Signal.hold(self.strategy_id, market_data.timestamp, self.config.symbol)
    
    def _check_buy_conditions(self, data_1h: dict, data_15m: dict) -> bool:
        """檢查買入條件"""
        # 實現你的條件邏輯
        return (
            data_1h['trend'] == 'Uptrend' and
            data_15m['rsi'] > 30 and
            data_15m['rsi'] < 70 and
            data_15m['volume'] > data_15m['volume_ma']
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
        
        # 可以添加其他出場條件
        return False
```

#### 步驟 2：創建策略配置

創建 `strategies/my-strategy.json`：

```json
{
  "strategy_id": "my-strategy-v1",
  "strategy_name": "我的自定義策略",
  "version": "1.0.0",
  "enabled": true,
  "symbol": "BTCUSDT",
  "timeframes": ["1h", "15m"],
  
  "parameters": {
    "param1": 10,
    "param2": 0.5,
    "stop_loss_atr": 1.5,
    "take_profit_atr": 3.0
  },
  
  "risk_management": {
    "position_size": 0.20,
    "leverage": 5,
    "max_trades_per_day": 3,
    "max_consecutive_losses": 3,
    "daily_loss_limit": 0.10
  },
  
  "notifications": {
    "telegram": true,
    "email": false
  }
}
```

#### 步驟 3：註冊策略

在 `src/managers/strategy_manager.py` 中註冊你的策略：

```python
from src.strategies.my_strategy import MyStrategy

STRATEGY_REGISTRY = {
    'multi-timeframe': MultiTimeframeStrategy,
    'breakout': BreakoutStrategy,
    'my-strategy': MyStrategy,  # 添加你的策略
}
```

#### 步驟 4：驗證策略

```bash
python tools/validate_strategy.py --strategy my-strategy-v1
```

#### 步驟 5：回測策略

```bash
python cli.py backtest \
  --strategy my-strategy-v1 \
  --start 2024-01-01 \
  --end 2024-12-31 \
  --initial-capital 1000
```

### 策略開發最佳實踐

#### 1. 信號生成

```python
def generate_signal(self, market_data: MarketData) -> Signal:
    """生成交易信號
    
    最佳實踐：
    1. 先檢查數據完整性
    2. 計算所需指標
    3. 評估多個條件
    4. 返回明確的信號
    """
    # 檢查數據
    if not self._validate_data(market_data):
        return Signal.hold(self.strategy_id, market_data.timestamp, self.config.symbol)
    
    # 計算指標
    indicators = self._calculate_indicators(market_data)
    
    # 評估條件
    if self._check_entry_conditions(indicators):
        return self._create_entry_signal(market_data, indicators)
    
    return Signal.hold(self.strategy_id, market_data.timestamp, self.config.symbol)
```

#### 2. 風險管理

```python
def calculate_position_size(self, capital: float, price: float) -> float:
    """計算倉位大小
    
    最佳實踐：
    1. 考慮賬戶風險
    2. 考慮策略配置
    3. 考慮市場波動性
    4. 設置最小/最大限制
    """
    # 基礎倉位
    position_pct = self.config.risk_management.position_size
    leverage = self.config.risk_management.leverage
    base_size = (capital * position_pct * leverage) / price
    
    # 根據波動性調整
    volatility_factor = self._calculate_volatility_factor(market_data)
    adjusted_size = base_size * volatility_factor
    
    # 應用限制
    min_size = 0.001  # 最小倉位
    max_size = (capital * 0.5) / price  # 最大倉位
    
    return max(min_size, min(adjusted_size, max_size))
```

#### 3. 錯誤處理

```python
def generate_signal(self, market_data: MarketData) -> Signal:
    """生成交易信號（帶錯誤處理）"""
    try:
        # 策略邏輯
        return self._generate_signal_impl(market_data)
    except KeyError as e:
        # 數據缺失
        logger.error(f"Missing data in {self.strategy_id}: {e}")
        return Signal.hold(self.strategy_id, market_data.timestamp, self.config.symbol)
    except Exception as e:
        # 其他錯誤
        logger.error(f"Error in {self.strategy_id}: {e}", exc_info=True)
        return Signal.hold(self.strategy_id, market_data.timestamp, self.config.symbol)
```

---

## 測試指南

### 測試結構

```
tests/
├── unit/                    # 單元測試
│   ├── test_strategy_manager.py
│   ├── test_my_strategy.py
│   └── ...
├── property/                # 屬性測試
│   ├── test_strategy_isolation.py
│   ├── test_risk_limits.py
│   └── ...
└── integration/             # 集成測試
    ├── test_multi_strategy_execution.py
    └── ...
```

### 編寫單元測試

```python
import pytest
from src.strategies.my_strategy import MyStrategy
from src.models.config import StrategyConfig

def test_my_strategy_buy_signal():
    """測試買入信號生成"""
    # 準備
    config = StrategyConfig.from_json('strategies/my-strategy.json')
    strategy = MyStrategy(config)
    market_data = create_test_market_data(trend='Uptrend', rsi=50)
    
    # 執行
    signal = strategy.generate_signal(market_data)
    
    # 驗證
    assert signal.action == 'BUY'
    assert signal.direction == 'long'
    assert signal.stop_loss < signal.entry_price
    assert signal.take_profit > signal.entry_price

def test_my_strategy_hold_signal():
    """測試持有信號"""
    config = StrategyConfig.from_json('strategies/my-strategy.json')
    strategy = MyStrategy(config)
    market_data = create_test_market_data(trend='Sideways', rsi=50)
    
    signal = strategy.generate_signal(market_data)
    
    assert signal.action == 'HOLD'
```

### 編寫屬性測試

```python
from hypothesis import given, strategies as st
import pytest

# Feature: multi-strategy-system, Property 8: 策略接口一致性
@given(st.builds(valid_strategy_config))
def test_strategy_interface_consistency(config):
    """對於任何策略配置，策略必須實現所有必需方法"""
    strategy = create_strategy_from_config(config)
    
    # 驗證所有必需方法存在
    assert hasattr(strategy, 'generate_signal')
    assert hasattr(strategy, 'calculate_position_size')
    assert hasattr(strategy, 'calculate_stop_loss')
    assert hasattr(strategy, 'calculate_take_profit')
    assert hasattr(strategy, 'should_exit')
    
    # 驗證方法可調用
    assert callable(strategy.generate_signal)
    assert callable(strategy.calculate_position_size)
```

詳細測試指南請參考：[TESTING_GUIDE.md](TESTING_GUIDE.md)

---

## 代碼規範

### Python 風格指南

遵循 PEP 8 風格指南：

```python
# 好的例子
def calculate_position_size(self, capital: float, price: float) -> float:
    """計算倉位大小
    
    Args:
        capital: 可用資金
        price: 當前價格
    
    Returns:
        float: 倉位大小（幣數）
    """
    position_pct = self.config.risk_management.position_size
    leverage = self.config.risk_management.leverage
    return (capital * position_pct * leverage) / price

# 壞的例子
def calc_pos(self,c,p):
    return (c*self.config.risk_management.position_size*self.config.risk_management.leverage)/p
```

### 命名規範

- **類名**：使用 PascalCase（如 `StrategyManager`）
- **函數名**：使用 snake_case（如 `generate_signal`）
- **常量**：使用 UPPER_CASE（如 `MAX_POSITION_SIZE`）
- **私有方法**：使用前綴 `_`（如 `_validate_data`）

### 文檔字符串

使用 Google 風格的文檔字符串：

```python
def generate_signal(self, market_data: MarketData) -> Signal:
    """生成交易信號
    
    根據市場數據和策略邏輯生成交易信號。
    
    Args:
        market_data: 市場數據對象，包含多週期 OHLCV 和指標
    
    Returns:
        Signal: 交易信號對象，包含動作、方向、價格等信息
    
    Raises:
        ValueError: 當市場數據無效時
    
    Example:
        >>> strategy = MyStrategy(config)
        >>> signal = strategy.generate_signal(market_data)
        >>> print(signal.action)
        'BUY'
    """
    pass
```

### 類型提示

使用類型提示提高代碼可讀性：

```python
from typing import List, Dict, Optional, Tuple
from datetime import datetime

def run_backtest(
    strategy: Strategy,
    start_date: datetime,
    end_date: datetime,
    initial_capital: float = 1000.0
) -> BacktestResult:
    """運行回測"""
    pass
```

---

## 貢獻流程

### 1. Fork 倉庫

在 GitHub 上 fork 項目倉庫。

### 2. 創建分支

```bash
git checkout -b feature/my-new-feature
# 或
git checkout -b fix/bug-description
```

### 3. 開發和測試

```bash
# 開發你的功能
# ...

# 運行測試
pytest

# 檢查代碼風格
flake8 src/
black src/
```

### 4. 提交更改

```bash
git add .
git commit -m "feat: add new strategy feature"
```

提交訊息格式：
- `feat:` 新功能
- `fix:` 錯誤修復
- `docs:` 文檔更新
- `test:` 測試相關
- `refactor:` 代碼重構

### 5. 推送和創建 PR

```bash
git push origin feature/my-new-feature
```

然後在 GitHub 上創建 Pull Request。

### 6. 代碼審查

等待維護者審查你的代碼。根據反饋進行修改。

---

## 常見問題

### Q: 如何調試策略？

```python
# 在策略中添加日誌
import logging
logger = logging.getLogger(__name__)

def generate_signal(self, market_data: MarketData) -> Signal:
    logger.debug(f"Generating signal for {self.strategy_id}")
    logger.debug(f"Market data: {market_data.get_latest()}")
    # ...
```

### Q: 如何處理數據缺失？

```python
def generate_signal(self, market_data: MarketData) -> Signal:
    try:
        data = market_data.get_timeframe('1h')
    except KeyError:
        logger.warning(f"Missing 1h data for {self.config.symbol}")
        return Signal.hold(self.strategy_id, market_data.timestamp, self.config.symbol)
```

### Q: 如何優化策略性能？

1. 使用向量化操作（pandas/numpy）
2. 緩存計算結果
3. 避免重複計算指標
4. 使用適當的數據結構

---

## 資源

- [API 文檔](API.md)
- [策略開發指南](STRATEGY_DEVELOPMENT.md)
- [測試指南](TESTING_GUIDE.md)
- [架構設計](ARCHITECTURE.md)

---

**祝開發順利！** 🚀
