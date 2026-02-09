# 測試指南 (Testing Guide)

本指南詳細介紹系統的測試策略、如何運行測試以及如何編寫新測試。

---

## 目錄

1. [測試策略](#測試策略)
2. [運行測試](#運行測試)
3. [編寫單元測試](#編寫單元測試)
4. [編寫屬性測試](#編寫屬性測試)
5. [測試覆蓋率](#測試覆蓋率)
6. [持續集成](#持續集成)
7. [常見問題](#常見問題)

---

## 測試策略

### 雙重測試方法

系統採用**單元測試**和**基於屬性的測試（Property-Based Testing, PBT）**相結合的方法。

#### 單元測試

**用途**：
- 驗證特定示例和邊緣情況
- 測試組件之間的集成點
- 測試錯誤條件和異常處理
- 快速執行，提供即時反饋

**示例**：
```python
def test_strategy_buy_signal():
    """測試買入信號生成"""
    strategy = MyStrategy(config)
    market_data = create_test_data(trend='Uptrend')
    signal = strategy.generate_signal(market_data)
    assert signal.action == 'BUY'
```

#### 屬性測試

**用途**：
- 驗證通用屬性在所有輸入下都成立
- 通過隨機化實現全面的輸入覆蓋
- 發現意外的邊緣情況
- 每個測試最少運行 100 次迭代

**示例**：
```python
from hypothesis import given, strategies as st

@given(st.builds(valid_strategy_config))
def test_strategy_interface_consistency(config):
    """對於任何策略配置，策略必須實現所有必需方法"""
    strategy = create_strategy_from_config(config)
    assert hasattr(strategy, 'generate_signal')
    assert callable(strategy.generate_signal)
```

### 測試框架

- **單元測試**：`pytest`
- **屬性測試**：`hypothesis`
- **測試覆蓋率**：`pytest-cov`
- **Mock 工具**：`unittest.mock`

---

## 運行測試

### 基本命令

```bash
# 運行所有測試
pytest

# 運行特定目錄的測試
pytest tests/unit/
pytest tests/property/
pytest tests/integration/

# 運行特定文件的測試
pytest tests/unit/test_strategy_manager.py

# 運行特定測試函數
pytest tests/unit/test_strategy_manager.py::test_load_strategies
```


### 詳細輸出

```bash
# 顯示詳細輸出
pytest -v

# 顯示測試中的 print 語句
pytest -s

# 組合使用
pytest -v -s
```

### 測試覆蓋率

```bash
# 生成覆蓋率報告
pytest --cov=src

# 生成 HTML 報告
pytest --cov=src --cov-report=html

# 查看 HTML 報告
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### 測試標記

```bash
# 只運行單元測試
pytest -m unit

# 只運行屬性測試
pytest -m property

# 只運行快速測試
pytest -m "not slow"

# 運行特定標記的測試
pytest -m "unit and not slow"
```

### 並行測試

```bash
# 安裝 pytest-xdist
pip install pytest-xdist

# 並行運行測試（使用所有 CPU 核心）
pytest -n auto

# 使用指定數量的核心
pytest -n 4
```

---

## 編寫單元測試

### 測試結構

```python
import pytest
from src.strategies.my_strategy import MyStrategy
from src.models.config import StrategyConfig

class TestMyStrategy:
    """MyStrategy 的單元測試"""
    
    @pytest.fixture
    def config(self):
        """測試配置"""
        return StrategyConfig.from_json('strategies/my-strategy.json')
    
    @pytest.fixture
    def strategy(self, config):
        """策略實例"""
        return MyStrategy(config)
    
    def test_initialization(self, strategy, config):
        """測試策略初始化"""
        assert strategy.strategy_id == config.strategy_id
        assert strategy.config == config
    
    def test_buy_signal_generation(self, strategy):
        """測試買入信號生成"""
        market_data = create_test_market_data(trend='Uptrend', rsi=50)
        signal = strategy.generate_signal(market_data)
        
        assert signal.action == 'BUY'
        assert signal.direction == 'long'
        assert signal.stop_loss < signal.entry_price
        assert signal.take_profit > signal.entry_price
    
    def test_hold_signal_in_sideways_market(self, strategy):
        """測試震盪市場中的持有信號"""
        market_data = create_test_market_data(trend='Sideways', rsi=50)
        signal = strategy.generate_signal(market_data)
        
        assert signal.action == 'HOLD'
```

### 測試輔助函數

```python
def create_test_market_data(
    symbol: str = 'BTCUSDT',
    trend: str = 'Uptrend',
    rsi: float = 50,
    volume_ratio: float = 1.0
) -> MarketData:
    """創建測試用的市場數據"""
    # 生成測試數據
    df = pd.DataFrame({
        'timestamp': pd.date_range('2024-01-01', periods=100, freq='1h'),
        'open': np.random.uniform(50000, 51000, 100),
        'high': np.random.uniform(50500, 51500, 100),
        'low': np.random.uniform(49500, 50500, 100),
        'close': np.random.uniform(50000, 51000, 100),
        'volume': np.random.uniform(1000, 2000, 100) * volume_ratio
    })
    
    # 添加指標
    df['ema_20'] = df['close'].ewm(span=20).mean()
    df['rsi'] = rsi
    df['trend'] = trend
    
    return MarketData(
        symbol=symbol,
        timestamp=df['timestamp'].iloc[-1],
        timeframes={'1h': TimeframeData('1h', df, {})}
    )
```

### 測試邊緣情況

```python
def test_empty_data_handling(self, strategy):
    """測試空數據處理"""
    market_data = MarketData(
        symbol='BTCUSDT',
        timestamp=datetime.now(),
        timeframes={}
    )
    signal = strategy.generate_signal(market_data)
    assert signal.action == 'HOLD'

def test_missing_timeframe(self, strategy):
    """測試缺失時間週期"""
    market_data = create_test_market_data()
    # 移除必需的時間週期
    del market_data.timeframes['15m']
    
    signal = strategy.generate_signal(market_data)
    assert signal.action == 'HOLD'

def test_extreme_rsi_values(self, strategy):
    """測試極端 RSI 值"""
    # RSI = 0
    market_data = create_test_market_data(rsi=0)
    signal = strategy.generate_signal(market_data)
    # 驗證策略行為
    
    # RSI = 100
    market_data = create_test_market_data(rsi=100)
    signal = strategy.generate_signal(market_data)
    # 驗證策略行為
```

### 測試錯誤處理

```python
def test_invalid_config_handling(self):
    """測試無效配置處理"""
    with pytest.raises(ValueError):
        config = StrategyConfig(
            strategy_id='test',
            position_size=-0.5  # 無效值
        )

def test_exception_in_signal_generation(self, strategy, monkeypatch):
    """測試信號生成中的異常處理"""
    def mock_calculate_indicators(*args):
        raise RuntimeError("Test error")
    
    monkeypatch.setattr(strategy, '_calculate_indicators', mock_calculate_indicators)
    
    market_data = create_test_market_data()
    signal = strategy.generate_signal(market_data)
    
    # 應該返回 HOLD 信號而不是崩潰
    assert signal.action == 'HOLD'
```

---

## 編寫屬性測試

### 基本屬性測試

```python
from hypothesis import given, strategies as st
import pytest

# Feature: multi-strategy-system, Property 1: 策略配置載入完整性
@given(st.lists(st.builds(valid_strategy_config), min_size=1, max_size=10))
def test_strategy_loading_completeness(configs):
    """對於任何包含 N 個有效配置的目錄，應該載入 N 個策略"""
    with temp_strategy_dir(configs) as strategy_dir:
        manager = StrategyManager(strategy_dir)
        loaded_ids = manager.load_strategies()
        
        # 驗證載入數量
        assert len(loaded_ids) == len(configs)
        
        # 驗證 ID 唯一性
        assert len(set(loaded_ids)) == len(loaded_ids)
```

### 自定義策略生成器

```python
from hypothesis import strategies as st

@st.composite
def valid_strategy_config(draw):
    """生成有效的策略配置"""
    return {
        "strategy_id": draw(st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))),
        "strategy_name": draw(st.text(min_size=1)),
        "version": draw(st.text(regex=r'\d+\.\d+\.\d+')),
        "enabled": draw(st.booleans()),
        "symbol": draw(st.sampled_from(["BTCUSDT", "ETHUSDT", "SOLUSDT"])),
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

@st.composite
def market_data_generator(draw):
    """生成市場數據"""
    n_candles = draw(st.integers(min_value=100, max_value=1000))
    base_price = draw(st.floats(min_value=100, max_value=100000))
    
    # 生成價格序列
    prices = [base_price]
    for _ in range(n_candles - 1):
        change = draw(st.floats(min_value=-0.05, max_value=0.05))
        prices.append(prices[-1] * (1 + change))
    
    df = pd.DataFrame({
        'timestamp': pd.date_range('2024-01-01', periods=n_candles, freq='1h'),
        'open': prices,
        'high': [p * 1.01 for p in prices],
        'low': [p * 0.99 for p in prices],
        'close': prices,
        'volume': draw(st.lists(st.floats(min_value=1000, max_value=10000), min_size=n_candles, max_size=n_candles))
    })
    
    return df
```

### 屬性測試示例

```python
# Feature: multi-strategy-system, Property 6: 資金分配守恆
@given(
    st.floats(min_value=1000, max_value=100000),  # total_capital
    st.lists(st.floats(min_value=0.1, max_value=0.5), min_size=2, max_size=5)  # allocations
)
def test_capital_allocation_conservation(total_capital, allocations):
    """對於任何多策略系統，所有策略的已分配資金總和應該小於或等於總可用資金"""
    # 標準化分配比例
    total_allocation = sum(allocations)
    normalized_allocations = [a / total_allocation for a in allocations]
    
    # 計算分配的資金
    allocated_capitals = [total_capital * a for a in normalized_allocations]
    
    # 驗證守恆
    assert sum(allocated_capitals) <= total_capital * 1.01  # 允許小誤差
    
    # 驗證每個策略的分配
    for capital in allocated_capitals:
        assert 0 <= capital <= total_capital

# Feature: multi-strategy-system, Property 11: 績效指標計算正確性
@given(st.lists(st.builds(valid_trade), min_size=1, max_size=100))
def test_performance_metrics_correctness(trades):
    """對於任何交易列表，計算的勝率應該等於（獲利交易數 / 總交易數）"""
    engine = BacktestEngine(initial_capital=1000)
    metrics = engine.calculate_metrics(trades)
    
    # 計算預期勝率
    winning_trades = [t for t in trades if t.pnl > 0]
    expected_win_rate = len(winning_trades) / len(trades)
    
    # 驗證勝率
    assert abs(metrics.win_rate - expected_win_rate) < 0.01
    
    # 驗證獲利因子
    total_profit = sum(t.pnl for t in trades if t.pnl > 0)
    total_loss = abs(sum(t.pnl for t in trades if t.pnl < 0))
    
    if total_loss > 0:
        expected_profit_factor = total_profit / total_loss
        assert abs(metrics.profit_factor - expected_profit_factor) < 0.01
```

### 屬性測試配置

```python
# 在 pytest.ini 或 setup.cfg 中配置
[tool:pytest]
hypothesis_profile = default

[hypothesis]
max_examples = 100  # 每個測試運行 100 次
deadline = None  # 禁用超時
```

---

## 測試覆蓋率

### 覆蓋率目標

- **核心邏輯**：90%+ 覆蓋率
- **工具函數**：80%+ 覆蓋率
- **整體**：85%+ 覆蓋率

### 生成覆蓋率報告

```bash
# 生成終端報告
pytest --cov=src --cov-report=term

# 生成 HTML 報告
pytest --cov=src --cov-report=html

# 生成 XML 報告（用於 CI）
pytest --cov=src --cov-report=xml

# 組合多種報告
pytest --cov=src --cov-report=term --cov-report=html --cov-report=xml
```

### 查看覆蓋率報告

```bash
# 打開 HTML 報告
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

### 排除文件

在 `.coveragerc` 或 `pyproject.toml` 中配置：

```ini
[coverage:run]
omit =
    */tests/*
    */venv/*
    */__pycache__/*
    */site-packages/*

[coverage:report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:
```

---

## 持續集成

### GitHub Actions 配置

創建 `.github/workflows/tests.yml`：

```yaml
name: Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    strategy:
      matrix:
        python-version: [3.9, 3.10, 3.11]
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v2
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    
    - name: Run tests
      run: |
        pytest --cov=src --cov-report=xml --cov-report=term
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v2
      with:
        file: ./coverage.xml
        fail_ci_if_error: true
```

### 預提交鉤子

安裝 `pre-commit`：

```bash
pip install pre-commit
```

創建 `.pre-commit-config.yaml`：

```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.1.0
    hooks:
      - id: black
  
  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
  
  - repo: local
    hooks:
      - id: pytest
        name: pytest
        entry: pytest
        language: system
        pass_filenames: false
        always_run: true
```

安裝鉤子：

```bash
pre-commit install
```

---

## 常見問題

### Q: 測試運行很慢怎麼辦？

**A**: 使用並行測試和測試標記：

```bash
# 並行運行
pytest -n auto

# 只運行快速測試
pytest -m "not slow"

# 跳過屬性測試（開發時）
pytest -m "not property"
```

### Q: 如何調試失敗的測試？

**A**: 使用 pytest 的調試功能：

```bash
# 在第一個失敗處停止
pytest -x

# 進入 pdb 調試器
pytest --pdb

# 顯示局部變量
pytest -l

# 組合使用
pytest -x --pdb -l
```

### Q: 如何測試異步代碼？

**A**: 使用 `pytest-asyncio`：

```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    result = await my_async_function()
    assert result == expected_value
```

### Q: 如何 mock 外部依賴？

**A**: 使用 `unittest.mock` 或 `pytest-mock`：

```python
from unittest.mock import Mock, patch

def test_with_mock(monkeypatch):
    # Mock 函數
    mock_api = Mock(return_value={'price': 50000})
    monkeypatch.setattr('src.data.api.get_price', mock_api)
    
    # 測試
    result = my_function()
    assert result == expected_value
    mock_api.assert_called_once()
```

### Q: 如何測試隨機行為？

**A**: 使用固定的隨機種子：

```python
import random
import numpy as np

def test_random_behavior():
    # 設置種子
    random.seed(42)
    np.random.seed(42)
    
    # 測試
    result = function_with_randomness()
    assert result == expected_value
```

---

## 測試最佳實踐

### 1. 測試命名

```python
# 好的命名
def test_strategy_generates_buy_signal_in_uptrend():
    pass

def test_risk_manager_rejects_oversized_position():
    pass

# 壞的命名
def test_1():
    pass

def test_strategy():
    pass
```

### 2. 測試獨立性

```python
# 好的做法：每個測試獨立
def test_feature_a():
    setup_data()
    result = test_feature_a()
    assert result == expected

def test_feature_b():
    setup_data()  # 重新設置
    result = test_feature_b()
    assert result == expected

# 壞的做法：測試之間有依賴
shared_data = None

def test_feature_a():
    global shared_data
    shared_data = setup_data()
    # ...

def test_feature_b():
    # 依賴 test_feature_a 的結果
    result = use_shared_data(shared_data)
    # ...
```

### 3. 使用 Fixtures

```python
@pytest.fixture
def strategy_config():
    """可重用的配置"""
    return StrategyConfig.from_json('test_config.json')

@pytest.fixture
def market_data():
    """可重用的市場數據"""
    return create_test_market_data()

def test_with_fixtures(strategy_config, market_data):
    strategy = MyStrategy(strategy_config)
    signal = strategy.generate_signal(market_data)
    assert signal.action in ['BUY', 'SELL', 'HOLD']
```

### 4. 參數化測試

```python
@pytest.mark.parametrize("trend,expected_action", [
    ('Uptrend', 'BUY'),
    ('Downtrend', 'SELL'),
    ('Sideways', 'HOLD'),
])
def test_signal_generation_by_trend(trend, expected_action):
    market_data = create_test_market_data(trend=trend)
    signal = strategy.generate_signal(market_data)
    assert signal.action == expected_action
```

---

**完善的測試是高質量代碼的保證！** 🧪
