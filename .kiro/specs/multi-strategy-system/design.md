# Design Document - 多策略交易系統

## Overview

多策略交易系統是一個可擴展的交易平台，支持同時運行多個獨立的交易策略。系統採用分層架構設計，將策略邏輯、執行引擎、風險管理和數據分析完全解耦，確保各策略之間互不干擾，同時提供統一的回測、優化和分析工具。

### 設計目標

1. **策略隔離**：每個策略擁有獨立的狀態、資金池和執行環境
2. **可擴展性**：支持快速開發和部署新策略，無需修改核心系統
3. **統一標準**：所有策略使用相同的接口、數據格式和評估標準
4. **風險控制**：系統級和策略級的雙重風險管理
5. **可觀測性**：完整的監控、分析和覆盤能力

### 核心原則

- **配置驅動**：策略通過 JSON 配置文件定義，支持熱重載
- **事件驅動**：使用事件總線解耦組件之間的通信
- **數據優先**：所有決策基於數據，所有操作可追溯
- **測試友好**：回測引擎與實盤引擎共享相同的策略邏輯

---

## Architecture

系統採用五層架構設計：

```
┌─────────────────────────────────────────────────────────────┐
│                      策略層 (Strategy Layer)                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Strategy A   │  │ Strategy B   │  │ Strategy C   │      │
│  │ (JSON Config)│  │ (JSON Config)│  │ (JSON Config)│      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                     管理層 (Management Layer)                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Strategy     │  │ Risk         │  │ Data         │      │
│  │ Manager      │  │ Manager      │  │ Manager      │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                     執行層 (Execution Layer)                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Backtest     │  │ Live         │  │ Signal       │      │
│  │ Engine       │  │ Trader       │  │ Generator    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                     分析層 (Analysis Layer)                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Optimizer    │  │ Loss         │  │ Performance  │      │
│  │              │  │ Analyzer     │  │ Monitor      │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                      數據層 (Data Layer)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Market Data  │  │ Trade        │  │ Backtest     │      │
│  │ Storage      │  │ History      │  │ Results      │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

### 組件職責

**策略層**：
- 定義策略配置（進場/出場條件、風險參數）
- 策略版本管理
- 策略啟用/停用控制

**管理層**：
- Strategy Manager：載入、驗證、運行策略
- Risk Manager：全局和策略級風險控制
- Data Manager：統一數據接口和緩存

**執行層**：
- Backtest Engine：歷史數據回測
- Live Trader：實盤交易執行
- Signal Generator：根據策略生成交易信號

**分析層**：
- Optimizer：參數優化和敏感度分析
- Loss Analyzer：虧損原因分析和改進建議
- Performance Monitor：實時性能監控和警報

**數據層**：
- 市場數據存儲和管理
- 交易歷史記錄
- 回測結果持久化

---

## Components and Interfaces

### 1. Strategy Interface

所有策略必須實現標準接口：

```python
class Strategy(ABC):
    """策略基類"""
    
    @abstractmethod
    def __init__(self, config: StrategyConfig):
        """初始化策略
        
        Args:
            config: 策略配置對象
        """
        pass
    
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
        """計算倉位大小
        
        Args:
            capital: 可用資金
            price: 當前價格
        
        Returns:
            float: 倉位大小（幣數）
        """
        pass
    
    @abstractmethod
    def calculate_stop_loss(self, entry_price: float, direction: str, atr: float) -> float:
        """計算止損價格
        
        Args:
            entry_price: 進場價格
            direction: 方向（'long' 或 'short'）
            atr: ATR 值
        
        Returns:
            float: 止損價格
        """
        pass
    
    @abstractmethod
    def calculate_take_profit(self, entry_price: float, direction: str, atr: float) -> float:
        """計算目標價格
        
        Args:
            entry_price: 進場價格
            direction: 方向（'long' 或 'short'）
            atr: ATR 值
        
        Returns:
            float: 目標價格
        """
        pass
    
    @abstractmethod
    def should_exit(self, position: Position, market_data: MarketData) -> bool:
        """判斷是否應該出場
        
        Args:
            position: 當前持倉
            market_data: 市場數據
        
        Returns:
            bool: 是否應該出場
        """
        pass
```

### 2. Strategy Manager

策略管理器負責策略的生命週期管理：

```python
class StrategyManager:
    """策略管理器"""
    
    def __init__(self, strategies_dir: str = "strategies/"):
        """初始化策略管理器
        
        Args:
            strategies_dir: 策略配置文件目錄
        """
        self.strategies_dir = strategies_dir
        self.strategies: Dict[str, Strategy] = {}
        self.strategy_states: Dict[str, StrategyState] = {}
    
    def load_strategies(self) -> List[str]:
        """從配置文件載入所有策略
        
        Returns:
            List[str]: 成功載入的策略 ID 列表
        """
        pass
    
    def validate_config(self, config: dict) -> Tuple[bool, str]:
        """驗證策略配置
        
        Args:
            config: 策略配置字典
        
        Returns:
            Tuple[bool, str]: (是否有效, 錯誤訊息)
        """
        pass
    
    def create_strategy(self, config: StrategyConfig) -> Strategy:
        """根據配置創建策略實例
        
        Args:
            config: 策略配置對象
        
        Returns:
            Strategy: 策略實例
        """
        pass
    
    def enable_strategy(self, strategy_id: str) -> bool:
        """啟用策略
        
        Args:
            strategy_id: 策略 ID
        
        Returns:
            bool: 是否成功
        """
        pass
    
    def disable_strategy(self, strategy_id: str) -> bool:
        """停用策略
        
        Args:
            strategy_id: 策略 ID
        
        Returns:
            bool: 是否成功
        """
        pass
    
    def get_strategy_state(self, strategy_id: str) -> StrategyState:
        """獲取策略狀態
        
        Args:
            strategy_id: 策略 ID
        
        Returns:
            StrategyState: 策略狀態對象
        """
        pass
    
    def reload_strategy(self, strategy_id: str) -> bool:
        """熱重載策略配置
        
        Args:
            strategy_id: 策略 ID
        
        Returns:
            bool: 是否成功
        """
        pass
```

### 3. Risk Manager

風險管理器提供系統級風險控制：

```python
class RiskManager:
    """風險管理器"""
    
    def __init__(self, config: RiskConfig):
        """初始化風險管理器
        
        Args:
            config: 風險配置對象
        """
        self.config = config
        self.global_state = GlobalRiskState()
    
    def check_global_risk(self) -> Tuple[bool, str]:
        """檢查全局風險限制
        
        Returns:
            Tuple[bool, str]: (是否通過, 原因)
        """
        pass
    
    def check_strategy_risk(self, strategy_id: str, signal: Signal) -> Tuple[bool, str]:
        """檢查策略級風險限制
        
        Args:
            strategy_id: 策略 ID
            signal: 交易信號
        
        Returns:
            Tuple[bool, str]: (是否通過, 原因)
        """
        pass
    
    def update_risk_state(self, trade: Trade) -> None:
        """更新風險狀態
        
        Args:
            trade: 交易記錄
        """
        pass
    
    def should_halt_trading(self) -> Tuple[bool, str]:
        """判斷是否應該暫停所有交易
        
        Returns:
            Tuple[bool, str]: (是否暫停, 原因)
        """
        pass
    
    def calculate_max_position_size(self, strategy_id: str, capital: float) -> float:
        """計算最大允許倉位
        
        Args:
            strategy_id: 策略 ID
            capital: 可用資金
        
        Returns:
            float: 最大倉位（USDT）
        """
        pass
```

### 4. Backtest Engine

統一的回測引擎：

```python
class BacktestEngine:
    """回測引擎"""
    
    def __init__(self, initial_capital: float, commission: float = 0.0005):
        """初始化回測引擎
        
        Args:
            initial_capital: 初始資金
            commission: 手續費率
        """
        self.initial_capital = initial_capital
        self.commission = commission
    
    def run_single_strategy(
        self,
        strategy: Strategy,
        market_data: Dict[str, pd.DataFrame],
        start_date: datetime,
        end_date: datetime
    ) -> BacktestResult:
        """回測單個策略
        
        Args:
            strategy: 策略實例
            market_data: 市場數據（多週期）
            start_date: 開始日期
            end_date: 結束日期
        
        Returns:
            BacktestResult: 回測結果
        """
        pass
    
    def run_multi_strategy(
        self,
        strategies: List[Strategy],
        market_data: Dict[str, pd.DataFrame],
        start_date: datetime,
        end_date: datetime,
        capital_allocation: Dict[str, float]
    ) -> MultiStrategyBacktestResult:
        """回測多策略組合
        
        Args:
            strategies: 策略列表
            market_data: 市場數據
            start_date: 開始日期
            end_date: 結束日期
            capital_allocation: 資金分配（策略 ID -> 比例）
        
        Returns:
            MultiStrategyBacktestResult: 多策略回測結果
        """
        pass
    
    def calculate_metrics(self, trades: List[Trade]) -> PerformanceMetrics:
        """計算績效指標
        
        Args:
            trades: 交易列表
        
        Returns:
            PerformanceMetrics: 績效指標對象
        """
        pass
```

### 5. Loss Analyzer

虧損分析器：

```python
class LossAnalyzer:
    """虧損分析器"""
    
    def __init__(self):
        """初始化虧損分析器"""
        self.loss_patterns = self._load_loss_patterns()
    
    def analyze_trade(self, trade: Trade, market_data: MarketData) -> LossAnalysis:
        """分析單筆虧損交易
        
        Args:
            trade: 交易記錄
            market_data: 市場數據
        
        Returns:
            LossAnalysis: 虧損分析結果
        """
        pass
    
    def classify_loss_reason(self, trade: Trade, market_data: MarketData) -> str:
        """分類虧損原因
        
        Args:
            trade: 交易記錄
            market_data: 市場數據
        
        Returns:
            str: 虧損原因分類
        """
        pass
    
    def find_common_patterns(self, trades: List[Trade]) -> List[LossPattern]:
        """找出虧損交易的共同模式
        
        Args:
            trades: 虧損交易列表
        
        Returns:
            List[LossPattern]: 虧損模式列表
        """
        pass
    
    def generate_recommendations(self, analysis: LossAnalysis) -> List[str]:
        """生成改進建議
        
        Args:
            analysis: 虧損分析結果
        
        Returns:
            List[str]: 改進建議列表
        """
        pass
```

### 6. Performance Monitor

性能監控器：

```python
class PerformanceMonitor:
    """性能監控器"""
    
    def __init__(self, telegram_notifier: Optional[TelegramNotifier] = None):
        """初始化性能監控器
        
        Args:
            telegram_notifier: Telegram 通知器（可選）
        """
        self.telegram_notifier = telegram_notifier
        self.metrics_history: Dict[str, List[Metric]] = {}
    
    def update_metrics(self, strategy_id: str, metrics: PerformanceMetrics) -> None:
        """更新策略指標
        
        Args:
            strategy_id: 策略 ID
            metrics: 績效指標
        """
        pass
    
    def check_anomaly(self, strategy_id: str) -> Tuple[bool, str]:
        """檢測策略異常
        
        Args:
            strategy_id: 策略 ID
        
        Returns:
            Tuple[bool, str]: (是否異常, 異常描述)
        """
        pass
    
    def detect_degradation(self, strategy_id: str) -> Tuple[bool, float]:
        """檢測策略退化
        
        Args:
            strategy_id: 策略 ID
        
        Returns:
            Tuple[bool, float]: (是否退化, 退化程度)
        """
        pass
    
    def send_alert(self, strategy_id: str, alert_type: str, message: str) -> None:
        """發送警報
        
        Args:
            strategy_id: 策略 ID
            alert_type: 警報類型
            message: 警報訊息
        """
        pass
```

---

## Data Models

### StrategyConfig

策略配置數據模型：

```python
@dataclass
class StrategyConfig:
    """策略配置"""
    strategy_id: str
    strategy_name: str
    version: str
    enabled: bool
    symbol: str
    timeframes: List[str]
    
    # 策略參數
    parameters: Dict[str, Any]
    
    # 風險管理
    risk_management: RiskManagement
    
    # 進場條件（表達式列表）
    entry_conditions: List[str]
    
    # 出場條件
    exit_conditions: ExitConditions
    
    # 通知設置
    notifications: NotificationConfig
    
    @classmethod
    def from_json(cls, json_path: str) -> 'StrategyConfig':
        """從 JSON 文件載入配置"""
        pass
    
    def validate(self) -> Tuple[bool, str]:
        """驗證配置有效性"""
        pass
```

### RiskManagement

風險管理配置：

```python
@dataclass
class RiskManagement:
    """風險管理配置"""
    position_size: float  # 倉位比例（0-1）
    leverage: int  # 槓桿倍數
    max_trades_per_day: int  # 每日最大交易次數
    max_consecutive_losses: int  # 最大連續虧損次數
    daily_loss_limit: float  # 每日虧損限制（比例）
    stop_loss_atr: float  # 止損 ATR 倍數
    take_profit_atr: float  # 目標 ATR 倍數
```

### MarketData

市場數據模型：

```python
@dataclass
class MarketData:
    """市場數據"""
    symbol: str
    timestamp: datetime
    timeframes: Dict[str, TimeframeData]  # 週期 -> 數據
    
    def get_timeframe(self, timeframe: str) -> TimeframeData:
        """獲取指定週期的數據"""
        pass

@dataclass
class TimeframeData:
    """單週期數據"""
    timeframe: str
    ohlcv: pd.DataFrame  # OHLCV 數據
    indicators: Dict[str, pd.Series]  # 技術指標
    
    def get_latest(self) -> Dict[str, float]:
        """獲取最新數據點"""
        pass
```

### Signal

交易信號模型：

```python
@dataclass
class Signal:
    """交易信號"""
    strategy_id: str
    timestamp: datetime
    symbol: str
    action: str  # 'BUY', 'SELL', 'HOLD'
    direction: str  # 'long', 'short', None
    entry_price: float
    stop_loss: float
    take_profit: float
    position_size: float
    confidence: float  # 信號置信度（0-1）
    metadata: Dict[str, Any]  # 額外信息
```

### Position

持倉模型：

```python
@dataclass
class Position:
    """持倉"""
    strategy_id: str
    symbol: str
    direction: str  # 'long' or 'short'
    entry_time: datetime
    entry_price: float
    size: float  # 幣數
    stop_loss: float
    take_profit: float
    leverage: int
    unrealized_pnl: float
    
    def update_pnl(self, current_price: float) -> float:
        """更新未實現損益"""
        pass
```

### Trade

交易記錄模型：

```python
@dataclass
class Trade:
    """交易記錄"""
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
    pnl: float  # 淨損益（扣除手續費）
    pnl_pct: float  # 損益百分比
    commission: float  # 手續費
    exit_reason: str  # '止損', '獲利', '手動平倉'
    metadata: Dict[str, Any]
```

### BacktestResult

回測結果模型：

```python
@dataclass
class BacktestResult:
    """回測結果"""
    strategy_id: str
    start_date: datetime
    end_date: datetime
    initial_capital: float
    final_capital: float
    
    # 交易統計
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    
    # 損益統計
    total_pnl: float
    total_pnl_pct: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    
    # 風險指標
    max_drawdown: float
    max_drawdown_pct: float
    sharpe_ratio: float
    
    # 交易列表
    trades: List[Trade]
    
    # 資金曲線
    equity_curve: pd.Series
    
    def to_dict(self) -> dict:
        """轉換為字典"""
        pass
    
    def save(self, filepath: str) -> None:
        """保存結果到文件"""
        pass
```

### StrategyState

策略運行狀態：

```python
@dataclass
class StrategyState:
    """策略狀態"""
    strategy_id: str
    enabled: bool
    current_position: Optional[Position]
    
    # 今日統計
    trades_today: int
    pnl_today: float
    consecutive_losses: int
    
    # 累計統計
    total_trades: int
    total_pnl: float
    win_rate: float
    
    # 最後更新時間
    last_update: datetime
    
    def reset_daily_stats(self) -> None:
        """重置每日統計"""
        pass
```

---

## Correctness Properties

*屬性（Property）是系統在所有有效執行中都應該保持為真的特徵或行為。屬性是人類可讀規範與機器可驗證正確性保證之間的橋樑。*

### Property 1: 策略配置載入完整性

*對於任何* 包含 N 個有效 JSON 配置文件的 `strategies/` 目錄，系統啟動後應該成功載入 N 個策略，且每個策略都有唯一的 ID。

**Validates: Requirements 1.1, 1.2, 1.7**

### Property 2: 配置錯誤隔離

*對於任何* 包含有效和無效配置文件的混合目錄，系統應該載入所有有效配置，記錄所有無效配置的錯誤，且不會因為無效配置而崩潰。

**Validates: Requirements 1.3**

### Property 3: 配置熱重載一致性

*對於任何* 已載入的策略配置，修改配置文件並觸發重載後，策略的新實例應該反映修改後的參數，且重載過程不影響其他策略。

**Validates: Requirements 1.6, 2.2**

### Property 4: 策略狀態隔離

*對於任何* 同時運行的多個策略，修改一個策略的狀態（如持倉、資金、交易次數）不應該影響其他策略的狀態。

**Validates: Requirements 2.1, 2.4**

### Property 5: 策略錯誤隔離

*對於任何* 運行中的策略集合，當其中一個策略拋出異常時，其他策略應該繼續正常運行，且異常策略的錯誤被記錄。

**Validates: Requirements 2.3**

### Property 6: 資金分配守恆

*對於任何* 多策略系統，所有策略的已分配資金總和應該小於或等於總可用資金，且每個策略只能使用其分配的資金。

**Validates: Requirements 2.4, 2.7, 2.8**

### Property 7: 交易記錄完整性

*對於任何* 策略執行的交易，該交易應該被記錄在該策略的交易歷史中，且不會出現在其他策略的歷史中。

**Validates: Requirements 2.5, 7.1**

### Property 8: 策略接口一致性

*對於任何* 實現 Strategy 接口的策略類，該類必須實現所有必需的方法（generate_signal, calculate_position_size, calculate_stop_loss, calculate_take_profit, should_exit）。

**Validates: Requirements 3.2**

### Property 9: 回測數據一致性

*對於任何* 在同一時間範圍內對多個策略執行的回測，所有策略應該使用相同的市場數據、手續費率和滑點設置。

**Validates: Requirements 4.2, 4.3**

### Property 10: 回測結果持久化往返

*對於任何* 回測結果，將結果保存到文件後再載入，應該得到等價的結果對象（所有關鍵字段相同）。

**Validates: Requirements 4.7**

### Property 11: 績效指標計算正確性

*對於任何* 交易列表，計算的勝率應該等於（獲利交易數 / 總交易數），且獲利因子應該等於（總獲利 / 總虧損的絕對值）。

**Validates: Requirements 4.6**

### Property 12: 參數優化數據分離

*對於任何* 參數優化過程，訓練集和驗證集不應該有重疊的數據點。

**Validates: Requirements 5.4**

### Property 13: 網格搜索完整性

*對於任何* 定義的參數網格，網格搜索應該測試所有可能的參數組合。

**Validates: Requirements 5.1**

### Property 14: 優化報告完整性

*對於任何* 完成的參數優化，生成的報告應該包含最佳參數、訓練集性能、驗證集性能和參數敏感度分析。

**Validates: Requirements 5.6, 5.7**

### Property 15: 虧損分類完整性

*對於任何* 虧損交易，系統應該自動分配至少一個虧損原因分類。

**Validates: Requirements 6.1**

### Property 16: 虧損佔比總和

*對於任何* 虧損分析結果，所有虧損原因的佔比總和應該等於 100%。

**Validates: Requirements 6.4**

### Property 17: 交易註記往返

*對於任何* 交易，添加註記和標籤後，查詢該交易應該返回相同的註記和標籤。

**Validates: Requirements 7.2**

### Property 18: 覆盤報告時間範圍

*對於任何* 覆盤報告（每日/每週/每月），報告中包含的交易時間應該都在指定的時間範圍內。

**Validates: Requirements 7.6**

### Property 19: 覆盤數據導出往返

*對於任何* 覆盤數據，導出到文件後再導入，應該得到等價的數據（所有關鍵字段相同）。

**Validates: Requirements 7.8**

### Property 20: 實時收益率計算正確性

*對於任何* 策略，實時收益率應該等於（當前資金 - 初始資金）/ 初始資金。

**Validates: Requirements 8.2**

### Property 21: 異常警報觸發

*對於任何* 策略，當其性能指標超出預定義的異常閾值時，系統應該發送警報。

**Validates: Requirements 8.3**

### Property 22: 策略退化檢測

*對於任何* 策略，當其最近 N 筆交易的勝率顯著低於歷史平均勝率時，系統應該檢測到性能退化。

**Validates: Requirements 8.5**

### Property 23: 連續虧損自動暫停

*對於任何* 策略，當連續虧損次數達到配置的閾值時，系統應該自動暫停該策略。

**Validates: Requirements 8.6**

### Property 24: 全局回撤限制觸發

*對於任何* 多策略系統，當總回撤超過全局限制時，系統應該暫停所有策略。

**Validates: Requirements 9.2**

### Property 25: 單策略倉位限制

*對於任何* 策略的交易信號，如果執行該信號會導致倉位超過該策略的最大倉位限制，系統應該拒絕該信號。

**Validates: Requirements 9.4**

### Property 26: 全局倉位限制

*對於任何* 多策略系統的交易信號，如果執行該信號會導致所有策略的總倉位超過全局限制，系統應該拒絕該信號。

**Validates: Requirements 9.5**

### Property 27: 風險事件記錄完整性

*對於任何* 觸發的風險限制（回撤、虧損、倉位），系統應該記錄該風險事件，包括時間、類型、觸發值和採取的行動。

**Validates: Requirements 9.8**

### Property 28: 數據源容錯切換

*對於任何* 數據請求，當主數據源失敗時，系統應該自動嘗試備用數據源，且最終返回有效數據或明確的錯誤。

**Validates: Requirements 10.3**

### Property 29: 數據緩存效率

*對於任何* 在緩存有效期內的重複數據請求，系統應該從緩存返回數據，而不是重新調用 API。

**Validates: Requirements 10.4**

### Property 30: 數據完整性驗證

*對於任何* 獲取的市場數據，系統應該驗證數據包含所有必需字段（timestamp, open, high, low, close, volume），且數值在合理範圍內。

**Validates: Requirements 10.6**

### Property 31: 數據導出往返

*對於任何* 市場數據或交易數據，導出到文件後再導入，應該得到等價的數據（所有字段相同）。

**Validates: Requirements 10.7**

---

## Error Handling

### 策略載入錯誤

**錯誤類型**：
- 配置文件不存在
- JSON 格式錯誤
- 必需字段缺失
- 參數值無效（如負數倉位、無效的週期）

**處理策略**：
1. 記錄詳細錯誤訊息（文件路徑、錯誤原因）
2. 跳過該策略，繼續載入其他策略
3. 在系統啟動日誌中標記失敗的策略
4. 不因單個策略載入失敗而終止系統

### 策略執行錯誤

**錯誤類型**：
- 策略邏輯拋出異常
- 信號生成失敗
- 倉位計算錯誤

**處理策略**：
1. 捕獲異常，記錄完整堆棧追蹤
2. 將策略標記為錯誤狀態
3. 不影響其他策略的運行
4. 發送警報通知管理員
5. 可選：自動暫停出錯的策略

### 數據獲取錯誤

**錯誤類型**：
- API 請求超時
- API 返回錯誤（429 限流、500 服務器錯誤）
- 網絡連接失敗
- 數據格式異常

**處理策略**：
1. 實施指數退避重試（最多 3 次）
2. 切換到備用數據源
3. 使用緩存的歷史數據（如果可用）
4. 如果所有數據源都失敗，記錄錯誤並跳過本次檢查
5. 不因數據獲取失敗而終止系統

### 風險限制觸發

**錯誤類型**：
- 全局回撤超限
- 單日虧損超限
- 倉位超限
- 連續虧損超限

**處理策略**：
1. 立即暫停相關策略或所有策略
2. 記錄風險事件到數據庫
3. 發送緊急通知（Telegram + 日誌）
4. 平倉所有持倉（可選，根據配置）
5. 需要手動干預才能恢復交易

### 回測錯誤

**錯誤類型**：
- 數據不足（時間範圍內數據缺失）
- 策略邏輯錯誤
- 內存不足

**處理策略**：
1. 驗證數據完整性，提前檢測數據缺失
2. 在回測開始前驗證策略邏輯
3. 提供清晰的錯誤訊息和修復建議
4. 保存部分回測結果（如果已執行部分交易）

### 文件 I/O 錯誤

**錯誤類型**：
- 文件不存在
- 權限不足
- 磁盤空間不足
- 文件損壞

**處理策略**：
1. 檢查文件存在性和權限
2. 提供清晰的錯誤訊息
3. 對於關鍵數據，實施備份機制
4. 對於損壞的文件，嘗試從備份恢復

---

## Testing Strategy

### 雙重測試方法

系統將採用**單元測試**和**基於屬性的測試（Property-Based Testing, PBT）**相結合的方法，確保全面的測試覆蓋。

**單元測試**：
- 驗證特定示例和邊緣情況
- 測試組件之間的集成點
- 測試錯誤條件和異常處理
- 快速執行，提供即時反饋

**基於屬性的測試**：
- 驗證通用屬性在所有輸入下都成立
- 通過隨機化實現全面的輸入覆蓋
- 發現意外的邊緣情況
- 每個測試最少運行 100 次迭代

### 測試框架選擇

**Python 生態系統**：
- 單元測試：`pytest`
- 基於屬性的測試：`hypothesis`
- 測試覆蓋率：`pytest-cov`
- Mock 工具：`unittest.mock`

### 屬性測試配置

每個屬性測試必須：
1. 運行最少 100 次迭代（由於隨機化）
2. 使用註釋引用設計文檔中的屬性
3. 標籤格式：`# Feature: multi-strategy-system, Property {number}: {property_text}`

示例：
```python
from hypothesis import given, strategies as st
import pytest

# Feature: multi-strategy-system, Property 1: 策略配置載入完整性
@given(st.lists(st.builds(valid_strategy_config), min_size=1, max_size=10))
def test_strategy_loading_completeness(configs):
    """對於任何包含 N 個有效配置的目錄，應該載入 N 個策略"""
    # 創建臨時目錄並寫入配置文件
    with temp_strategy_dir(configs) as strategy_dir:
        manager = StrategyManager(strategy_dir)
        loaded_ids = manager.load_strategies()
        
        # 驗證載入數量
        assert len(loaded_ids) == len(configs)
        
        # 驗證 ID 唯一性
        assert len(set(loaded_ids)) == len(loaded_ids)
```

### 測試組織

**按層級組織測試**：

```
tests/
├── unit/
│   ├── test_strategy_manager.py
│   ├── test_risk_manager.py
│   ├── test_backtest_engine.py
│   ├── test_loss_analyzer.py
│   └── test_data_manager.py
├── property/
│   ├── test_strategy_isolation.py
│   ├── test_risk_limits.py
│   ├── test_data_consistency.py
│   └── test_backtest_correctness.py
├── integration/
│   ├── test_multi_strategy_execution.py
│   ├── test_end_to_end_backtest.py
│   └── test_live_trading_simulation.py
└── fixtures/
    ├── sample_strategies.py
    ├── market_data.py
    └── trade_history.py
```

### 關鍵測試場景

**策略隔離測試**：
- 多個策略同時運行，驗證狀態隔離
- 一個策略崩潰，其他策略繼續運行
- 資金分配獨立性

**風險管理測試**：
- 全局回撤限制觸發
- 單策略倉位限制
- 連續虧損自動暫停
- 風險事件記錄

**回測正確性測試**：
- 數據一致性（所有策略使用相同數據）
- 績效指標計算正確性
- 結果持久化往返

**數據管理測試**：
- 數據源容錯切換
- 緩存效率
- 數據完整性驗證

### 測試數據生成

使用 `hypothesis` 的策略（strategies）生成測試數據：

```python
from hypothesis import strategies as st

# 策略配置生成器
@st.composite
def strategy_config(draw):
    return {
        "strategy_id": draw(st.text(min_size=1, max_size=20)),
        "strategy_name": draw(st.text(min_size=1)),
        "version": draw(st.text(regex=r'\d+\.\d+\.\d+')),
        "enabled": draw(st.booleans()),
        "symbol": draw(st.sampled_from(["BTCUSDT", "ETHUSDT"])),
        "timeframes": draw(st.lists(
            st.sampled_from(["1m", "5m", "15m", "1h", "4h", "1d"]),
            min_size=1, max_size=4, unique=True
        )),
        "parameters": {
            "stop_loss_atr": draw(st.floats(min_value=0.5, max_value=5.0)),
            "take_profit_atr": draw(st.floats(min_value=1.0, max_value=10.0)),
        },
        "risk_management": {
            "position_size": draw(st.floats(min_value=0.01, max_value=1.0)),
            "leverage": draw(st.integers(min_value=1, max_value=20)),
        }
    }

# 市場數據生成器
@st.composite
def market_data(draw):
    n_candles = draw(st.integers(min_value=100, max_value=1000))
    base_price = draw(st.floats(min_value=100, max_value=100000))
    
    # 生成 OHLCV 數據
    # ... (實現細節)
    
    return df
```

### 持續集成

**CI/CD 流程**：
1. 每次提交觸發測試
2. 運行所有單元測試（快速反饋）
3. 運行屬性測試（更多迭代）
4. 生成測試覆蓋率報告
5. 只有所有測試通過才允許合併

**測試覆蓋率目標**：
- 核心邏輯：90%+ 覆蓋率
- 工具函數：80%+ 覆蓋率
- 整體：85%+ 覆蓋率

### 性能測試

**回測性能**：
- 測試大規模數據集（1 年+ 的分鐘級數據）
- 測試多策略並行回測
- 目標：1 年數據回測 < 1 分鐘

**實時性能**：
- 測試信號生成延遲
- 測試多策略並發執行
- 目標：信號生成 < 100ms

---

## Implementation Notes

### 技術棧建議

**核心語言**：Python 3.9+
- 豐富的數據分析生態系統（pandas, numpy）
- 優秀的測試工具（pytest, hypothesis）
- 易於快速開發和迭代

**關鍵依賴**：
- `pandas`: 數據處理
- `numpy`: 數值計算
- `requests`: API 調用
- `pytest`: 單元測試
- `hypothesis`: 屬性測試
- `pydantic`: 數據驗證
- `python-telegram-bot`: Telegram 通知

### 開發優先級

**階段 1：核心基礎設施（P0）**
1. Strategy Interface 定義
2. StrategyManager 實現
3. RiskManager 實現
4. BacktestEngine 實現
5. 基礎測試框架

**階段 2：策略遷移（P0）**
1. 將現有單策略遷移到新架構
2. 創建策略配置文件
3. 驗證多策略運行

**階段 3：分析工具（P1）**
1. LossAnalyzer 實現
2. PerformanceMonitor 實現
3. 覆盤系統基礎功能

**階段 4：優化工具（P2）**
1. Optimizer 實現
2. 策略開發工具
3. 完善文檔

### 遷移策略

從現有單策略系統遷移到多策略系統：

1. **保持向後兼容**：現有的 `trading_alert_system.py` 可以作為第一個策略
2. **逐步遷移**：先實現核心框架，再遷移現有策略
3. **並行運行**：在遷移期間，新舊系統可以並行運行
4. **數據遷移**：將現有的交易歷史導入新系統

### 配置管理

**環境變數**：
- 敏感信息（API keys, Telegram tokens）
- 環境特定配置（開發/生產）

**配置文件**：
- 策略配置（JSON）
- 系統配置（YAML）
- 風險參數（JSON）

**配置優先級**：
環境變數 > 配置文件 > 默認值

---

## 附錄：配置文件示例

### 系統配置（system_config.yaml）

```yaml
system:
  name: "Multi-Strategy Trading System"
  version: "1.0.0"
  
data:
  primary_source: "binance"
  backup_sources: ["bingx"]
  cache_ttl: 300  # 秒
  
risk:
  global_max_drawdown: 0.20  # 20%
  daily_loss_limit: 0.10  # 10%
  global_max_position: 0.80  # 80% 總資金
  
notifications:
  telegram:
    enabled: true
    bot_token: "${TELEGRAM_BOT_TOKEN}"
    chat_id: "${TELEGRAM_CHAT_ID}"
  
backtest:
  commission: 0.0005
  slippage: 0.0001
  initial_capital: 1000
```

### 策略配置（strategies/multi-timeframe-v1.json）

```json
{
  "strategy_id": "multi-timeframe-v1",
  "strategy_name": "多週期共振策略",
  "version": "1.0.0",
  "enabled": true,
  "symbol": "ETHUSDT",
  "timeframes": ["1d", "4h", "1h", "15m"],
  
  "parameters": {
    "stop_loss_atr": 1.5,
    "take_profit_atr": 3.0,
    "rsi_range": [30, 70],
    "ema_distance": 0.03,
    "volume_threshold": 1.0
  },
  
  "risk_management": {
    "position_size": 0.20,
    "leverage": 5,
    "max_trades_per_day": 3,
    "max_consecutive_losses": 3,
    "daily_loss_limit": 0.10
  },
  
  "entry_conditions": [
    "trend_4h == trend_1h",
    "trend_4h in ['Uptrend', 'Downtrend']",
    "30 <= rsi_15m <= 70",
    "price_near_ema(0.03)",
    "volume > volume_ma"
  ],
  
  "exit_conditions": {
    "stop_loss": "price - (atr * stop_loss_atr)",
    "take_profit": "price + (atr * take_profit_atr)"
  },
  
  "notifications": {
    "telegram": true,
    "email": false
  }
}
```

