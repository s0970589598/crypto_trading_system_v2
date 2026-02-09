# API 文檔 (API Documentation)

本文檔詳細描述系統的所有公共 API 接口。

---

## 目錄

1. [策略接口](#策略接口)
2. [管理層 API](#管理層-api)
3. [執行層 API](#執行層-api)
4. [分析層 API](#分析層-api)
5. [數據模型](#數據模型)

---

## 策略接口

### Strategy (抽象基類)

所有策略必須繼承此基類並實現所有抽象方法。

```python
from abc import ABC, abstractmethod
from src.models.config import StrategyConfig
from src.models.trading import Signal, Position
from src.models.market_data import MarketData

class Strategy(ABC):
    """策略基類"""
```

#### 構造函數

```python
def __init__(self, config: StrategyConfig)
```

**參數：**
- `config` (StrategyConfig): 策略配置對象

**示例：**
```python
config = StrategyConfig.from_json('strategies/my-strategy.json')
strategy = MyStrategy(config)
```

#### generate_signal

```python
@abstractmethod
def generate_signal(self, market_data: MarketData) -> Signal
```

生成交易信號。

**參數：**
- `market_data` (MarketData): 市場數據對象

**返回：**
- `Signal`: 交易信號對象

**示例：**
```python
signal = strategy.generate_signal(market_data)
if signal.action == 'BUY':
    print(f"Buy signal at {signal.entry_price}")
```

#### calculate_position_size

```python
@abstractmethod
def calculate_position_size(self, capital: float, price: float) -> float
```

計算倉位大小。

**參數：**
- `capital` (float): 可用資金（USDT）
- `price` (float): 當前價格

**返回：**
- `float`: 倉位大小（幣數）

**示例：**
```python
size = strategy.calculate_position_size(capital=1000, price=50000)
print(f"Position size: {size} BTC")
```

#### calculate_stop_loss

```python
@abstractmethod
def calculate_stop_loss(self, entry_price: float, direction: str, atr: float) -> float
```

計算止損價格。

**參數：**
- `entry_price` (float): 進場價格
- `direction` (str): 方向（'long' 或 'short'）
- `atr` (float): ATR 值

**返回：**
- `float`: 止損價格

**示例：**
```python
stop_loss = strategy.calculate_stop_loss(
    entry_price=50000,
    direction='long',
    atr=500
)
```

#### calculate_take_profit

```python
@abstractmethod
def calculate_take_profit(self, entry_price: float, direction: str, atr: float) -> float
```

計算目標價格。

**參數：**
- `entry_price` (float): 進場價格
- `direction` (str): 方向（'long' 或 'short'）
- `atr` (float): ATR 值

**返回：**
- `float`: 目標價格

#### should_exit

```python
@abstractmethod
def should_exit(self, position: Position, market_data: MarketData) -> bool
```

判斷是否應該出場。

**參數：**
- `position` (Position): 當前持倉
- `market_data` (MarketData): 市場數據

**返回：**
- `bool`: 是否應該出場

---

## 管理層 API

### StrategyManager

策略管理器，負責策略的生命週期管理。

```python
from src.managers.strategy_manager import StrategyManager

manager = StrategyManager(strategies_dir="strategies/")
```

#### load_strategies

```python
def load_strategies(self) -> List[str]
```

從配置文件載入所有策略。

**返回：**
- `List[str]`: 成功載入的策略 ID 列表

**示例：**
```python
loaded_ids = manager.load_strategies()
print(f"Loaded {len(loaded_ids)} strategies")
```

#### validate_config

```python
def validate_config(self, config: dict) -> Tuple[bool, str]
```

驗證策略配置。

**參數：**
- `config` (dict): 策略配置字典

**返回：**
- `Tuple[bool, str]`: (是否有效, 錯誤訊息)

**示例：**
```python
is_valid, error_msg = manager.validate_config(config)
if not is_valid:
    print(f"Invalid config: {error_msg}")
```

#### enable_strategy

```python
def enable_strategy(self, strategy_id: str) -> bool
```

啟用策略。

**參數：**
- `strategy_id` (str): 策略 ID

**返回：**
- `bool`: 是否成功

#### disable_strategy

```python
def disable_strategy(self, strategy_id: str) -> bool
```

停用策略。

**參數：**
- `strategy_id` (str): 策略 ID

**返回：**
- `bool`: 是否成功

#### get_strategy_state

```python
def get_strategy_state(self, strategy_id: str) -> StrategyState
```

獲取策略狀態。

**參數：**
- `strategy_id` (str): 策略 ID

**返回：**
- `StrategyState`: 策略狀態對象

#### reload_strategy

```python
def reload_strategy(self, strategy_id: str) -> bool
```

熱重載策略配置。

**參數：**
- `strategy_id` (str): 策略 ID

**返回：**
- `bool`: 是否成功

---

### RiskManager

風險管理器，提供系統級風險控制。

```python
from src.managers.risk_manager import RiskManager
from src.models.risk import RiskConfig

config = RiskConfig(
    global_max_drawdown=0.20,
    daily_loss_limit=0.10,
    global_max_position=0.80
)
risk_manager = RiskManager(config)
```

#### check_global_risk

```python
def check_global_risk(self) -> Tuple[bool, str]
```

檢查全局風險限制。

**返回：**
- `Tuple[bool, str]`: (是否通過, 原因)

**示例：**
```python
passed, reason = risk_manager.check_global_risk()
if not passed:
    print(f"Risk check failed: {reason}")
```

#### check_strategy_risk

```python
def check_strategy_risk(self, strategy_id: str, signal: Signal) -> Tuple[bool, str]
```

檢查策略級風險限制。

**參數：**
- `strategy_id` (str): 策略 ID
- `signal` (Signal): 交易信號

**返回：**
- `Tuple[bool, str]`: (是否通過, 原因)

#### should_halt_trading

```python
def should_halt_trading(self) -> Tuple[bool, str]
```

判斷是否應該暫停所有交易。

**返回：**
- `Tuple[bool, str]`: (是否暫停, 原因)

#### calculate_max_position_size

```python
def calculate_max_position_size(self, strategy_id: str, capital: float) -> float
```

計算最大允許倉位。

**參數：**
- `strategy_id` (str): 策略 ID
- `capital` (float): 可用資金

**返回：**
- `float`: 最大倉位（USDT）

---

### DataManager

數據管理器，提供統一的數據接口。

```python
from src.managers.data_manager import DataManager

data_manager = DataManager(
    primary_source='binance',
    backup_sources=['bingx'],
    cache_ttl=300
)
```

#### get_market_data

```python
def get_market_data(
    self,
    symbol: str,
    timeframes: List[str],
    limit: int = 500
) -> MarketData
```

獲取市場數據。

**參數：**
- `symbol` (str): 交易對（如 'BTCUSDT'）
- `timeframes` (List[str]): 時間週期列表（如 ['1h', '15m']）
- `limit` (int): 數據條數

**返回：**
- `MarketData`: 市場數據對象

**示例：**
```python
market_data = data_manager.get_market_data(
    symbol='BTCUSDT',
    timeframes=['1h', '15m'],
    limit=500
)
```

#### export_data

```python
def export_data(self, filepath: str, format: str = 'csv') -> None
```

導出數據到文件。

**參數：**
- `filepath` (str): 文件路徑
- `format` (str): 格式（'csv' 或 'json'）

---

## 執行層 API

### BacktestEngine

回測引擎，用於歷史數據回測。

```python
from src.execution.backtest_engine import BacktestEngine

engine = BacktestEngine(
    initial_capital=1000,
    commission=0.0005
)
```

#### run_single_strategy

```python
def run_single_strategy(
    self,
    strategy: Strategy,
    market_data: Dict[str, pd.DataFrame],
    start_date: datetime,
    end_date: datetime
) -> BacktestResult
```

回測單個策略。

**參數：**
- `strategy` (Strategy): 策略實例
- `market_data` (Dict[str, pd.DataFrame]): 市場數據
- `start_date` (datetime): 開始日期
- `end_date` (datetime): 結束日期

**返回：**
- `BacktestResult`: 回測結果

**示例：**
```python
result = engine.run_single_strategy(
    strategy=my_strategy,
    market_data=data,
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 12, 31)
)
print(f"Total return: {result.total_pnl_pct:.2f}%")
```

#### run_multi_strategy

```python
def run_multi_strategy(
    self,
    strategies: List[Strategy],
    market_data: Dict[str, pd.DataFrame],
    start_date: datetime,
    end_date: datetime,
    capital_allocation: Dict[str, float]
) -> MultiStrategyBacktestResult
```

回測多策略組合。

**參數：**
- `strategies` (List[Strategy]): 策略列表
- `market_data` (Dict[str, pd.DataFrame]): 市場數據
- `start_date` (datetime): 開始日期
- `end_date` (datetime): 結束日期
- `capital_allocation` (Dict[str, float]): 資金分配

**返回：**
- `MultiStrategyBacktestResult`: 多策略回測結果

#### calculate_metrics

```python
def calculate_metrics(self, trades: List[Trade]) -> PerformanceMetrics
```

計算績效指標。

**參數：**
- `trades` (List[Trade]): 交易列表

**返回：**
- `PerformanceMetrics`: 績效指標對象

---

### MultiStrategyExecutor

多策略執行器，協調多個策略的運行。

```python
from src.execution.multi_strategy_executor import MultiStrategyExecutor

executor = MultiStrategyExecutor(
    strategy_manager=strategy_manager,
    risk_manager=risk_manager,
    data_manager=data_manager
)
```

#### execute_strategies

```python
def execute_strategies(self, strategy_ids: List[str]) -> None
```

執行多個策略。

**參數：**
- `strategy_ids` (List[str]): 策略 ID 列表

#### get_all_positions

```python
def get_all_positions(self) -> Dict[str, List[Position]]
```

獲取所有策略的持倉。

**返回：**
- `Dict[str, List[Position]]`: 策略 ID -> 持倉列表

---

## 分析層 API

### Optimizer

參數優化器，用於自動尋找最佳策略參數。

```python
from src.analysis.optimizer import Optimizer

optimizer = Optimizer(
    strategy=my_strategy,
    backtest_engine=engine,
    market_data=data
)
```

#### grid_search

```python
def grid_search(
    self,
    param_grid: Dict[str, List[Any]],
    start_date: datetime,
    end_date: datetime
) -> OptimizationResult
```

網格搜索參數優化。

**參數：**
- `param_grid` (Dict[str, List[Any]]): 參數網格
- `start_date` (datetime): 開始日期
- `end_date` (datetime): 結束日期

**返回：**
- `OptimizationResult`: 優化結果

**示例：**
```python
param_grid = {
    'stop_loss_atr': [1.0, 1.5, 2.0],
    'take_profit_atr': [2.0, 3.0, 4.0]
}
result = optimizer.grid_search(
    param_grid=param_grid,
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 12, 31)
)
print(f"Best params: {result.best_params}")
```

#### random_search

```python
def random_search(
    self,
    param_distributions: Dict[str, Any],
    n_iterations: int,
    start_date: datetime,
    end_date: datetime
) -> OptimizationResult
```

隨機搜索參數優化。

#### bayesian_optimization

```python
def bayesian_optimization(
    self,
    param_bounds: Dict[str, Tuple[float, float]],
    n_iterations: int,
    start_date: datetime,
    end_date: datetime
) -> OptimizationResult
```

貝葉斯優化。

---

### LossAnalyzer

虧損分析器，分析虧損交易的原因。

```python
from src.analysis.loss_analyzer import LossAnalyzer

analyzer = LossAnalyzer()
```

#### analyze_trade

```python
def analyze_trade(self, trade: Trade, market_data: MarketData) -> LossAnalysis
```

分析單筆虧損交易。

**參數：**
- `trade` (Trade): 交易記錄
- `market_data` (MarketData): 市場數據

**返回：**
- `LossAnalysis`: 虧損分析結果

#### classify_loss_reason

```python
def classify_loss_reason(self, trade: Trade, market_data: MarketData) -> str
```

分類虧損原因。

**返回：**
- `str`: 虧損原因分類

#### generate_recommendations

```python
def generate_recommendations(self, analysis: LossAnalysis) -> List[str]
```

生成改進建議。

**返回：**
- `List[str]`: 改進建議列表

---

### PerformanceMonitor

性能監控器，實時監控策略表現。

```python
from src.analysis.performance_monitor import PerformanceMonitor

monitor = PerformanceMonitor(telegram_notifier=notifier)
```

#### update_metrics

```python
def update_metrics(self, strategy_id: str, metrics: PerformanceMetrics) -> None
```

更新策略指標。

#### check_anomaly

```python
def check_anomaly(self, strategy_id: str) -> Tuple[bool, str]
```

檢測策略異常。

**返回：**
- `Tuple[bool, str]`: (是否異常, 異常描述)

#### detect_degradation

```python
def detect_degradation(self, strategy_id: str) -> Tuple[bool, float]
```

檢測策略退化。

**返回：**
- `Tuple[bool, float]`: (是否退化, 退化程度)

---

### ReviewSystem

交易覆盤系統，記錄和分析每筆交易。

```python
from src.analysis.review_system import ReviewSystem

review_system = ReviewSystem(data_dir='data/review_history')
```

#### add_trade_note

```python
def add_trade_note(self, trade_id: str, note: str, tags: List[str] = None) -> None
```

為交易添加註記。

**參數：**
- `trade_id` (str): 交易 ID
- `note` (str): 註記內容
- `tags` (List[str]): 標籤列表

#### calculate_execution_quality

```python
def calculate_execution_quality(self, trade: Trade) -> float
```

計算執行質量評分。

**返回：**
- `float`: 質量評分（0-100）

#### generate_review_report

```python
def generate_review_report(
    self,
    start_date: datetime,
    end_date: datetime,
    period: str = 'weekly'
) -> ReviewReport
```

生成覆盤報告。

**參數：**
- `start_date` (datetime): 開始日期
- `end_date` (datetime): 結束日期
- `period` (str): 週期（'daily', 'weekly', 'monthly'）

**返回：**
- `ReviewReport`: 覆盤報告

---

## 數據模型

### StrategyConfig

策略配置數據模型。

```python
from dataclasses import dataclass
from typing import Dict, List, Any

@dataclass
class StrategyConfig:
    strategy_id: str
    strategy_name: str
    version: str
    enabled: bool
    symbol: str
    timeframes: List[str]
    parameters: Dict[str, Any]
    risk_management: RiskManagement
    notifications: NotificationConfig
    
    @classmethod
    def from_json(cls, json_path: str) -> 'StrategyConfig':
        """從 JSON 文件載入配置"""
        pass
```

### Signal

交易信號模型。

```python
@dataclass
class Signal:
    strategy_id: str
    timestamp: datetime
    symbol: str
    action: str  # 'BUY', 'SELL', 'HOLD'
    direction: str  # 'long', 'short', None
    entry_price: float
    stop_loss: float
    take_profit: float
    position_size: float
    confidence: float
    metadata: Dict[str, Any]
```

### Position

持倉模型。

```python
@dataclass
class Position:
    strategy_id: str
    symbol: str
    direction: str
    entry_time: datetime
    entry_price: float
    size: float
    stop_loss: float
    take_profit: float
    leverage: int
    unrealized_pnl: float
```

### Trade

交易記錄模型。

```python
@dataclass
class Trade:
    trade_id: str
    strategy_id: str
    symbol: str
    direction: str
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    size: float
    leverage: int
    pnl: float
    pnl_pct: float
    commission: float
    exit_reason: str
    metadata: Dict[str, Any]
```

### BacktestResult

回測結果模型。

```python
@dataclass
class BacktestResult:
    strategy_id: str
    start_date: datetime
    end_date: datetime
    initial_capital: float
    final_capital: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    total_pnl_pct: float
    max_drawdown: float
    sharpe_ratio: float
    trades: List[Trade]
    equity_curve: pd.Series
```

---

## 錯誤處理

所有 API 方法都可能拋出以下異常：

- `ValueError`: 參數無效
- `KeyError`: 數據缺失
- `RuntimeError`: 運行時錯誤
- `ConfigError`: 配置錯誤
- `DataError`: 數據錯誤

**示例：**
```python
try:
    result = engine.run_single_strategy(strategy, data, start, end)
except ValueError as e:
    print(f"Invalid parameter: {e}")
except DataError as e:
    print(f"Data error: {e}")
```

---

## 版本兼容性

- **當前版本**: 1.0.0
- **Python 版本**: 3.9+
- **API 穩定性**: 穩定

---

**完整的 API 參考，助您快速開發！** 🚀
