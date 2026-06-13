# 量化風險分析 API 文檔

**版本**: 1.0.0  
**日期**: 2026-02-11

---

## 📚 目錄

- [概述](#概述)
- [核心類別](#核心類別)
- [使用方式](#使用方式)
- [API 參考](#api-參考)
- [數據模型](#數據模型)
- [使用示例](#使用示例)

---

## 概述

量化風險分析模組提供了一套完整的交易風險評估工具，包括 11 種核心分析方法，幫助交易者科學地評估和管理風險。

### 主要功能

- Kelly Criterion 最優倉位計算
- 傾斜行為（情緒化交易）檢測
- 破產風險評估
- 手續費壓力分析
- 恢復係數計算
- 情緒控制分析
- 能力維度評分
- 最長連損分析
- 短線交易效果評估
- 冷靜期建議

---

## 核心類別

### QuantitativeRiskAnalyzer

主要的量化風險分析器類別。

```python
from src.analysis.quantitative_risk import QuantitativeRiskAnalyzer

# 初始化
analyzer = QuantitativeRiskAnalyzer(trades_data_path='trades.json')

# 或者先初始化，後載入數據
analyzer = QuantitativeRiskAnalyzer()
analyzer.load_data('trades.json')
```

---

## 使用方式

### 1. Web 界面

在交易評分頁面自動顯示所有量化風險指標。

**訪問路徑**: Web 界面 → 交易評分 → 量化風險指標

### 2. CLI 工具

```bash
# 顯示所有分析
python -m cli_commands.analyze_risk --data trades.json

# 只顯示 Kelly Criterion
python -m cli_commands.analyze_risk --data trades.json --analysis kelly

# 輸出到 JSON 文件
python -m cli_commands.analyze_risk --data trades.json --output result.json
```

### 3. 核心模組整合

#### RiskManager

```python
from src.managers.risk_manager import RiskManager
from src.models.risk import RiskConfig

config = RiskConfig()
rm = RiskManager(config, 10000.0)

# 啟用量化分析
rm.enable_quantitative_analysis('trades.json')

# 使用量化分析功能
kelly = rm.calculate_kelly_criterion()
tilt = rm.detect_tilt_behavior()
ror = rm.calculate_risk_of_ruin()
fee = rm.calculate_fee_pressure()
```

#### PerformanceMonitor

```python
from src.analysis.performance_monitor import PerformanceMonitor

pm = PerformanceMonitor()

# 啟用量化分析
pm.enable_quantitative_analysis('trades.json')

# 使用量化分析功能
recovery = pm.calculate_recovery_factor()
emotional = pm.analyze_emotional_control()
skills = pm.calculate_skill_dimensions()
streak = pm.calculate_max_losing_streak()
```

#### LossAnalyzer

```python
from src.analysis.loss_analyzer import LossAnalyzer

la = LossAnalyzer()

# 啟用量化分析
la.enable_quantitative_analysis('trades.json')

# 使用量化分析功能
streak = la.calculate_max_losing_streak()
short_trades = la.analyze_short_term_trades(5.0)
simulation = la.simulate_without_short_trades(5.0)
cooling = la.check_cooling_period()
```

### 4. 直接 API 調用

```python
from src.analysis.quantitative_risk import QuantitativeRiskAnalyzer

# 初始化並載入數據
analyzer = QuantitativeRiskAnalyzer('trades.json')

# 執行各種分析
kelly = analyzer.calculate_ror_kelly()
tilt = analyzer.detect_tilt_behavior()
ror = analyzer.calculate_risk_of_ruin()
fee = analyzer.calculate_fee_pressure()
recovery = analyzer.calculate_recovery_factor()
emotional = analyzer.analyze_emotional_control()
skills = analyzer.calculate_skill_dimensions()
streak = analyzer.calculate_max_losing_streak()
short_trades = analyzer.analyze_short_term_trades(5.0)
simulation = analyzer.simulate_without_short_trades(5.0)
cooling = analyzer.check_cooling_period()
```

---

## API 參考

### QuantitativeRiskAnalyzer

#### `__init__(trades_data_path: str = None)`

初始化量化風險分析器。

**參數**:
- `trades_data_path` (str, 可選): 交易數據文件路徑（JSON 格式）

**示例**:
```python
analyzer = QuantitativeRiskAnalyzer('trades.json')
```

---

#### `load_data(path: str = None)`

載入交易數據。

**參數**:
- `path` (str, 可選): 數據路徑

**示例**:
```python
analyzer.load_data('trades.json')
```

---

#### `calculate_ror_kelly() -> Dict`

計算 Kelly Criterion 最優倉位。

**返回**:
```python
{
    'kelly_ror': float,              # 破產風險
    'kelly_optimal_size': float,     # 最優倉位（0-1）
    'recommended_size': float,       # 建議倉位（Half Kelly）
    'win_rate': float,               # 勝率
    'loss_rate': float,              # 敗率
    'avg_win': float,                # 平均獲利
    'avg_loss': float,               # 平均虧損
    'payoff_ratio': float,           # 盈虧比
    'expectancy': float,             # 期望值
    'explanation': str               # 說明
}
```

**示例**:
```python
kelly = analyzer.calculate_ror_kelly()
print(f"最優倉位: {kelly['kelly_optimal_size']:.2%}")
print(f"建議倉位: {kelly['recommended_size']:.2%}")
```

---

#### `detect_tilt_behavior() -> Dict`

檢測傾斜行為（情緒化交易）。

**返回**:
```python
{
    'has_tilt': bool,                    # 是否有傾斜行為
    'severity': str,                     # 嚴重程度（low/medium/high）
    'tilt_cases_count': int,             # 傾斜案例數
    'tilt_cases_percentage': float,      # 傾斜案例百分比
    'avg_tilt_pnl': float,              # 傾斜交易平均損益
    'tilt_win_rate': float,             # 傾斜交易勝率
    'avg_leverage_change_after_loss': float,  # 虧損後槓桿變化
    'avg_leverage_change_after_win': float,   # 獲利後槓桿變化
    'tilt_cases': List[Dict]            # 傾斜案例詳情
}
```

**示例**:
```python
tilt = analyzer.detect_tilt_behavior()
if tilt['has_tilt']:
    print(f"檢測到傾斜行為，嚴重程度: {tilt['severity']}")
    print(f"傾斜案例: {tilt['tilt_cases_count']} 次")
```

---

#### `calculate_risk_of_ruin() -> Dict`

計算破產風險。

**返回**:
```python
{
    'risk_of_ruin': float,           # 破產風險（0-1）
    'consecutive_losses_prob': Dict  # 連續虧損概率
}
```

**示例**:
```python
ror = analyzer.calculate_risk_of_ruin()
print(f"破產風險: {ror['risk_of_ruin']:.2%}")
```

---

#### `calculate_fee_pressure() -> Dict`

計算手續費壓力。

**返回**:
```python
{
    'total_fee': float,              # 總手續費
    'fee_to_pnl_ratio': float,       # 手續費/損益比
    'fee_to_loss_ratio': float,      # 手續費/虧損比
    'avg_fee_per_trade': float       # 平均每筆手續費
}
```

**示例**:
```python
fee = analyzer.calculate_fee_pressure()
print(f"手續費壓力: {fee['fee_to_loss_ratio']:.2f}%")
```

---

#### `calculate_recovery_factor() -> Dict`

計算恢復係數。

**返回**:
```python
{
    'recovery_factor': float,        # 恢復係數
    'total_pnl': float,             # 總損益
    'max_drawdown': float           # 最大回撤
}
```

**示例**:
```python
recovery = analyzer.calculate_recovery_factor()
print(f"恢復係數: {recovery['recovery_factor']:.2f}")
```

---

#### `analyze_emotional_control() -> Dict`

分析情緒控制。

**返回**:
```python
{
    'score': float,                      # 情緒控制評分（0-10）
    'severity': str,                     # 嚴重程度
    'frequency_increase_after_loss': float,  # 虧損後交易頻率增加
    'leverage_increase_after_loss': float,   # 虧損後槓桿增加
    'cases_count': int                   # 情緒失控案例數
}
```

**示例**:
```python
emotional = analyzer.analyze_emotional_control()
print(f"情緒控制評分: {emotional['score']:.1f}/10")
```

---

#### `calculate_skill_dimensions() -> Dict`

計算能力維度評分。

**返回**:
```python
{
    'direction_judgment': float,     # 方向判斷（0-10）
    'risk_management': float,        # 風險管理（0-10）
    'psychological_resilience': float,  # 心理韌性（0-10）
    'execution_discipline': float,   # 執行紀律（0-10）
    'cost_awareness': float,         # 成本意識（0-10）
    'overall_score': float,          # 綜合評分（0-10）
    'deduction_reasons': Dict        # 扣分原因
}
```

**示例**:
```python
skills = analyzer.calculate_skill_dimensions()
print(f"綜合評分: {skills['overall_score']:.1f}/10")
print(f"方向判斷: {skills['direction_judgment']:.1f}/10")
```

---

#### `calculate_max_losing_streak() -> Dict`

計算最長連損。

**返回**:
```python
{
    'max_streak': int,               # 最長連損次數
    'total_loss_in_streak': float,   # 連損期間總虧損
    'start_index': int,              # 開始位置
    'end_index': int                 # 結束位置
}
```

**示例**:
```python
streak = analyzer.calculate_max_losing_streak()
print(f"最長連損: {streak['max_streak']} 次")
print(f"連損虧損: {streak['total_loss_in_streak']:.2f} USDT")
```

---

#### `analyze_short_term_trades(minutes: float = 5.0) -> Dict`

分析短線交易。

**參數**:
- `minutes` (float): 短線交易時間閾值（分鐘）

**返回**:
```python
{
    'count': int,                    # 短線交易數量
    'percentage': float,             # 短線交易佔比
    'win_rate': float,              # 短線交易勝率
    'avg_pnl': float,               # 短線交易平均損益
    'total_pnl': float,             # 短線交易總損益
    'expectancy': float             # 短線交易期望值
}
```

**示例**:
```python
short_trades = analyzer.analyze_short_term_trades(5.0)
print(f"短線交易: {short_trades['count']} 次")
print(f"短線勝率: {short_trades['win_rate']:.2%}")
```

---

#### `simulate_without_short_trades(minutes: float = 5.0) -> Dict`

模擬停止短線交易的效果。

**參數**:
- `minutes` (float): 短線交易時間閾值（分鐘）

**返回**:
```python
{
    'original_pnl': float,           # 原始總損益
    'simulated_pnl': float,          # 模擬總損益
    'pnl_difference': float,         # 損益差異
    'pnl_improvement_pct': float,    # 改善百分比
    'removed_trades_count': int      # 移除的交易數
}
```

**示例**:
```python
simulation = analyzer.simulate_without_short_trades(5.0)
if simulation['pnl_improvement_pct'] > 0:
    print(f"停止短線交易可改善 {simulation['pnl_improvement_pct']:.1f}%")
```

---

#### `check_cooling_period() -> Dict`

檢查冷靜期建議。

**返回**:
```python
{
    'should_cool': bool,             # 是否需要冷靜
    'recommended_days': int,         # 建議冷靜天數
    'reason': str,                   # 原因
    'recent_performance': Dict       # 近期表現
}
```

**示例**:
```python
cooling = analyzer.check_cooling_period()
if cooling['should_cool']:
    print(f"建議休息 {cooling['recommended_days']} 天")
    print(f"原因: {cooling['reason']}")
```

---

## 數據模型

### 交易數據格式

交易數據應為 JSON 格式，包含以下欄位：

```json
[
  {
    "trade_id": "T0001",
    "symbol": "ETHUSDT",
    "side": "LONG",
    "open_time": "2024-01-01 00:00:00",
    "close_time": "2024-01-01 01:30:00",
    "entry_price": 2000.0,
    "exit_price": 2050.0,
    "quantity": 1.0,
    "leverage": 5,
    "pnl": 50.0,
    "fee": 0.5,
    "status": "CLOSED"
  }
]
```

**必需欄位**:
- `trade_id`: 交易 ID
- `open_time`: 開倉時間
- `close_time`: 平倉時間
- `pnl`: 損益
- `leverage`: 槓桿
- `quantity`: 數量
- `fee`: 手續費

---

## 使用示例

### 完整分析流程

```python
from src.analysis.quantitative_risk import QuantitativeRiskAnalyzer

# 1. 初始化並載入數據
analyzer = QuantitativeRiskAnalyzer('trades.json')

# 2. 執行所有分析
print("=" * 80)
print("量化風險分析報告")
print("=" * 80)

# Kelly Criterion
kelly = analyzer.calculate_ror_kelly()
print(f"\n【Kelly Criterion】")
print(f"最優倉位: {kelly['kelly_optimal_size']:.2%}")
print(f"建議倉位: {kelly['recommended_size']:.2%}")
print(f"期望值: {kelly['expectancy']:.4f}")

# 傾斜行為
tilt = analyzer.detect_tilt_behavior()
print(f"\n【傾斜行為】")
print(f"嚴重程度: {tilt['severity']}")
print(f"傾斜案例: {tilt['tilt_cases_count']} 次")

# 破產風險
ror = analyzer.calculate_risk_of_ruin()
print(f"\n【破產風險】")
print(f"破產風險: {ror['risk_of_ruin']:.2%}")

# 手續費壓力
fee = analyzer.calculate_fee_pressure()
print(f"\n【手續費壓力】")
print(f"手續費/虧損比: {fee['fee_to_loss_ratio']:.2f}%")

# 恢復係數
recovery = analyzer.calculate_recovery_factor()
print(f"\n【恢復係數】")
print(f"恢復係數: {recovery['recovery_factor']:.2f}")

# 情緒控制
emotional = analyzer.analyze_emotional_control()
print(f"\n【情緒控制】")
print(f"評分: {emotional['score']:.1f}/10")

# 能力評分
skills = analyzer.calculate_skill_dimensions()
print(f"\n【能力評分】")
print(f"綜合評分: {skills['overall_score']:.1f}/10")
print(f"方向判斷: {skills['direction_judgment']:.1f}/10")
print(f"風險管理: {skills['risk_management']:.1f}/10")

# 最長連損
streak = analyzer.calculate_max_losing_streak()
print(f"\n【最長連損】")
print(f"連損次數: {streak['max_streak']} 次")
print(f"連損虧損: {streak['total_loss_in_streak']:.2f} USDT")

# 短線交易
short_trades = analyzer.analyze_short_term_trades(5.0)
print(f"\n【短線交易】")
print(f"短線交易: {short_trades['count']} 次")
print(f"短線勝率: {short_trades['win_rate']:.2%}")

# 模擬停止短線
simulation = analyzer.simulate_without_short_trades(5.0)
if simulation['pnl_improvement_pct'] > 0:
    print(f"停止短線可改善: {simulation['pnl_improvement_pct']:.1f}%")

# 冷靜期建議
cooling = analyzer.check_cooling_period()
if cooling['should_cool']:
    print(f"\n【冷靜期建議】")
    print(f"建議休息: {cooling['recommended_days']} 天")
    print(f"原因: {cooling['reason']}")

print("\n" + "=" * 80)
```

---

## 相關文檔

- [CLI 使用指南](CLI_README.md#3-量化風險分析命令-analyze_risk)
- [遷移指南](遷移指南_量化風險分析.md)
- [發布說明](RELEASE_NOTES_量化風險分析.md)
- [整合方案](整合方案_quantitative_risk.md)

---

**版本**: 1.0.0  
**最後更新**: 2026-02-11  
**維護者**: Kiro AI Assistant

