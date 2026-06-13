# Quantitative Risk Analysis 整合方案

**制定日期**: 2026-02-11  
**目標**: 將 `quantitative_risk_analysis.py` 安全整合到核心系統，不影響現有功能

---

## 📊 現狀分析

### 當前使用情況

**使用方**: `pages/review/quality_scoring.py`
```python
from quantitative_risk_analysis import QuantitativeRiskOfficer
risk_officer = QuantitativeRiskOfficer()
```

**調用的功能**:
1. `calculate_max_losing_streak()` - 最長連損
2. `calculate_risk_of_ruin()` - 破產風險
3. `calculate_fee_pressure()` - 手續費壓力
4. `detect_tilt_behavior()` - 傾斜行為檢測
5. `check_cooling_period()` - 冷靜期檢測
6. `calculate_ror_kelly()` - Kelly Criterion
7. `analyze_emotional_control()` - 情緒失控分析
8. `calculate_skill_dimensions()` - 能力維度評分
9. `calculate_recovery_factor()` - 恢復係數
10. `analyze_short_term_trades()` - 短線交易分析
11. `simulate_without_short_trades()` - 模擬停止短線交易

### 現有核心系統功能

**src/managers/risk_manager.py**:
- ✅ 全局回撤限制
- ✅ 每日虧損限制
- ✅ 倉位限制
- ✅ 連續虧損限制
- ✅ 風險事件記錄
- ❌ **無 Kelly Criterion**
- ❌ **無 Tilt Score**
- ❌ **無情緒失控分析**

**src/analysis/loss_analyzer.py**:
- ✅ 虧損原因分類
- ✅ 虧損模式識別
- ✅ 改進建議生成
- ❌ **無 Tilt 檢測**
- ❌ **無情緒失控分析**

**src/analysis/performance_monitor.py**:
- ✅ 基本績效指標
- ✅ 回撤計算
- ✅ 異常檢測
- ✅ 退化檢測
- ❌ **無 Kelly Criterion**
- ❌ **無能力維度評分**

### 功能重疊分析

| 功能 | quantitative_risk_analysis.py | 現有核心系統 | 重疊度 |
|------|------------------------------|-------------|--------|
| 連續虧損檢測 | ✅ calculate_max_losing_streak | ✅ PerformanceMonitor.consecutive_losses | 80% |
| 回撤計算 | ✅ calculate_recovery_factor | ✅ PerformanceMonitor.max_drawdown | 70% |
| 破產風險 | ✅ calculate_risk_of_ruin | ❌ | 0% |
| Kelly Criterion | ✅ calculate_ror_kelly | ❌ | 0% |
| Tilt Score | ✅ detect_tilt_behavior | ❌ | 0% |
| 情緒失控 | ✅ analyze_emotional_control | ❌ | 0% |
| 能力評分 | ✅ calculate_skill_dimensions | ❌ | 0% |
| 手續費分析 | ✅ calculate_fee_pressure | ❌ | 0% |

---

## 🎯 整合策略

### 階段 1: 創建新模組（不影響現有功能）

**目標**: 將 `quantitative_risk_analysis.py` 重構為模組化架構

**步驟**:
1. 創建 `src/analysis/quantitative_risk.py`
2. 保留原始 `quantitative_risk_analysis.py`（向後兼容）
3. 新模組提供相同的 API

**優點**:
- ✅ 不影響現有 Web 界面
- ✅ 可以逐步遷移
- ✅ 保持向後兼容

### 階段 2: 整合到現有模組（增強功能）

**目標**: 將獨特功能整合到現有模組

**整合方案**:

#### 2.1 整合到 RiskManager
```python
# src/managers/risk_manager.py

from src.analysis.quantitative_risk import KellyCriterionCalculator

class RiskManager:
    def __init__(self, config, initial_capital):
        # ... 現有代碼 ...
        self.kelly_calculator = KellyCriterionCalculator()
    
    def calculate_optimal_position(self, trades: List[Trade]) -> Dict:
        """計算 Kelly 最優倉位"""
        return self.kelly_calculator.calculate(trades)
```

#### 2.2 整合到 PerformanceMonitor
```python
# src/analysis/performance_monitor.py

from src.analysis.quantitative_risk import (
    TiltDetector,
    EmotionalControlAnalyzer,
    SkillDimensionScorer
)

class PerformanceMonitor:
    def __init__(self, alert_config, telegram_notifier):
        # ... 現有代碼 ...
        self.tilt_detector = TiltDetector()
        self.emotional_analyzer = EmotionalControlAnalyzer()
        self.skill_scorer = SkillDimensionScorer()
    
    def detect_tilt(self, trades: List[Trade]) -> TiltScore:
        """檢測傾斜行為"""
        return self.tilt_detector.detect(trades)
```

#### 2.3 整合到 LossAnalyzer
```python
# src/analysis/loss_analyzer.py

from src.analysis.quantitative_risk import TiltDetector

class LossAnalyzer:
    def __init__(self, custom_rules):
        # ... 現有代碼 ...
        self.tilt_detector = TiltDetector()
    
    def analyze_trade_with_tilt(self, trade: Trade, history: List[Trade]) -> LossAnalysis:
        """分析虧損交易（包含 Tilt 檢測）"""
        # 現有分析
        analysis = self.analyze_trade(trade)
        
        # 添加 Tilt 檢測
        tilt_score = self.tilt_detector.detect([trade] + history)
        if tilt_score.severity in ['high', 'critical']:
            analysis.contributing_factors.append('傾斜行為')
        
        return analysis
```

### 階段 3: 更新 Web 界面（無縫遷移）

**目標**: 將 Web 界面遷移到新模組

**步驟**:
1. 創建兼容層（Adapter Pattern）
2. 逐步替換導入
3. 測試確認功能一致

**兼容層**:
```python
# quantitative_risk_analysis.py (保留作為兼容層)

from src.analysis.quantitative_risk import QuantitativeRiskAnalyzer

# 向後兼容的別名
QuantitativeRiskOfficer = QuantitativeRiskAnalyzer

# 或者創建包裝類
class QuantitativeRiskOfficer:
    """向後兼容的包裝類"""
    def __init__(self, trades_data_path='data/review_history/quality_scores.json'):
        from src.analysis.quantitative_risk import QuantitativeRiskAnalyzer
        self._analyzer = QuantitativeRiskAnalyzer(trades_data_path)
    
    def calculate_ror_kelly(self):
        return self._analyzer.calculate_kelly_criterion()
    
    # ... 其他方法的包裝 ...
```

---

## 📁 新模組結構

### src/analysis/quantitative_risk.py

```python
"""
量化風險分析模組

提供高級定量風險分析功能：
- Kelly Criterion 最優倉位計算
- Tilt Score 傾斜行為評分
- 情緒失控係數分析
- 能力維度評分
- 破產風險分析
"""

from dataclasses import dataclass
from typing import List, Dict, Tuple
import pandas as pd

from ..models.trading import Trade


# ==================== 數據模型 ====================

@dataclass
class TiltScore:
    """傾斜行為綜合評分"""
    overall_score: float
    severity: str
    position_size_factor: float
    leverage_factor: float
    timing_factor: float
    frequency_factor: float
    contributing_factors: List[str]


@dataclass
class KellyCriterion:
    """Kelly Criterion 結果"""
    optimal_size: float
    recommended_size: float
    win_rate: float
    payoff_ratio: float
    expectancy: float
    risk_of_ruin: float


@dataclass
class EmotionalControl:
    """情緒控制分析"""
    score: float
    severity: str
    frequency_increase_after_loss: float
    leverage_increase_after_loss: float
    cases_count: int


@dataclass
class SkillDimensions:
    """能力維度評分"""
    direction_judgment: float
    risk_management: float
    psychological_resilience: float
    execution_discipline: float
    cost_awareness: float
    overall_score: float
    deduction_reasons: Dict[str, List[str]]


# ==================== 核心分析器 ====================

class KellyCriterionCalculator:
    """Kelly Criterion 計算器"""
    
    def calculate(self, trades: List[Trade]) -> KellyCriterion:
        """計算 Kelly 最優倉位"""
        # 實現邏輯（從原始代碼遷移）
        pass


class TiltDetector:
    """傾斜行為檢測器"""
    
    def detect(self, trades: List[Trade]) -> TiltScore:
        """檢測傾斜行為"""
        # 實現邏輯（從原始代碼遷移）
        pass


class EmotionalControlAnalyzer:
    """情緒控制分析器"""
    
    def analyze(self, trades: List[Trade]) -> EmotionalControl:
        """分析情緒控制"""
        # 實現邏輯（從原始代碼遷移）
        pass


class SkillDimensionScorer:
    """能力維度評分器"""
    
    def score(self, trades: List[Trade]) -> SkillDimensions:
        """計算能力維度評分"""
        # 實現邏輯（從原始代碼遷移）
        pass


class QuantitativeRiskAnalyzer:
    """量化風險分析器（主類）"""
    
    def __init__(self, trades_data_path: str = None):
        self.kelly_calculator = KellyCriterionCalculator()
        self.tilt_detector = TiltDetector()
        self.emotional_analyzer = EmotionalControlAnalyzer()
        self.skill_scorer = SkillDimensionScorer()
        
        if trades_data_path:
            self.load_data(trades_data_path)
    
    def load_data(self, path: str):
        """載入交易數據"""
        # 實現邏輯
        pass
    
    # 提供與原始 API 兼容的方法
    def calculate_ror_kelly(self) -> Dict:
        """計算 Kelly Criterion（兼容 API）"""
        result = self.kelly_calculator.calculate(self.trades)
        return result.__dict__  # 轉換為字典
    
    def detect_tilt_behavior(self) -> Dict:
        """檢測傾斜行為（兼容 API）"""
        result = self.tilt_detector.detect(self.trades)
        return result.__dict__
    
    # ... 其他兼容方法 ...
```

---

## 🔄 遷移步驟

### Step 1: 創建新模組（第 1 週）

```bash
# 1. 創建新檔案
touch src/analysis/quantitative_risk.py

# 2. 複製核心邏輯
# 從 quantitative_risk_analysis.py 遷移代碼

# 3. 更新 __init__.py
# src/analysis/__init__.py 添加導出
```

**測試**:
```python
# tests/test_quantitative_risk.py
from src.analysis.quantitative_risk import QuantitativeRiskAnalyzer

def test_kelly_criterion():
    analyzer = QuantitativeRiskAnalyzer()
    # ... 測試邏輯 ...
```

### Step 2: 創建兼容層（第 2 週）

```python
# quantitative_risk_analysis.py (修改為兼容層)

"""
向後兼容層

此檔案保留用於向後兼容，新代碼請使用：
from src.analysis.quantitative_risk import QuantitativeRiskAnalyzer
"""

import warnings
from src.analysis.quantitative_risk import QuantitativeRiskAnalyzer

# 發出棄用警告
warnings.warn(
    "直接導入 quantitative_risk_analysis 已棄用，"
    "請使用 from src.analysis.quantitative_risk import QuantitativeRiskAnalyzer",
    DeprecationWarning,
    stacklevel=2
)

# 向後兼容的別名
QuantitativeRiskOfficer = QuantitativeRiskAnalyzer
```

**測試**:
```python
# 確保舊代碼仍能運行
from quantitative_risk_analysis import QuantitativeRiskOfficer
risk_officer = QuantitativeRiskOfficer()
result = risk_officer.calculate_ror_kelly()
```

### Step 3: 更新 Web 界面（第 3 週）

```python
# pages/review/quality_scoring.py

# 舊代碼（保留註釋）
# from quantitative_risk_analysis import QuantitativeRiskOfficer

# 新代碼
from src.analysis.quantitative_risk import QuantitativeRiskAnalyzer

# 使用新 API
risk_analyzer = QuantitativeRiskAnalyzer()
kelly = risk_analyzer.calculate_kelly_criterion()  # 新方法名
# 或使用兼容方法
kelly = risk_analyzer.calculate_ror_kelly()  # 兼容舊 API
```

**測試**:
- ✅ Web 界面功能正常
- ✅ 所有指標顯示正確
- ✅ 無錯誤或警告

### Step 4: 整合到核心模組（第 4-5 週）

```python
# src/managers/risk_manager.py
from src.analysis.quantitative_risk import KellyCriterionCalculator

class RiskManager:
    def __init__(self, config, initial_capital):
        # ... 現有代碼 ...
        self.kelly_calculator = KellyCriterionCalculator()
```

**測試**:
- ✅ CLI 工具可以使用 Kelly Criterion
- ✅ 回測引擎可以使用 Kelly Criterion
- ✅ 實盤交易可以使用 Kelly Criterion

### Step 5: 移除舊檔案（第 6 週，可選）

```bash
# 確認所有功能正常後
mv quantitative_risk_analysis.py _Archive/Code_20260211/

# 或保留作為兼容層（推薦）
# 保持 quantitative_risk_analysis.py 作為兼容層
```

---

## ✅ 測試計劃

### 單元測試

```python
# tests/analysis/test_quantitative_risk.py

import pytest
from src.analysis.quantitative_risk import (
    QuantitativeRiskAnalyzer,
    KellyCriterionCalculator,
    TiltDetector,
    EmotionalControlAnalyzer,
    SkillDimensionScorer
)

class TestKellyCriterion:
    def test_calculate_optimal_size(self):
        """測試 Kelly 最優倉位計算"""
        calculator = KellyCriterionCalculator()
        # ... 測試邏輯 ...
    
    def test_risk_of_ruin(self):
        """測試破產風險計算"""
        # ... 測試邏輯 ...

class TestTiltDetector:
    def test_detect_tilt_behavior(self):
        """測試傾斜行為檢測"""
        detector = TiltDetector()
        # ... 測試邏輯 ...

# ... 其他測試 ...
```

### 整合測試

```python
# tests/integration/test_risk_integration.py

def test_risk_manager_with_kelly():
    """測試 RiskManager 整合 Kelly Criterion"""
    # ... 測試邏輯 ...

def test_performance_monitor_with_tilt():
    """測試 PerformanceMonitor 整合 Tilt 檢測"""
    # ... 測試邏輯 ...
```

### Web 界面測試

```bash
# 手動測試清單
- [ ] 打開 Web 界面
- [ ] 進入「交易評分」頁面
- [ ] 確認「量化風險分析」區塊顯示正常
- [ ] 確認所有指標（Kelly, Tilt, 情緒失控等）顯示正確
- [ ] 確認無錯誤或警告
```

---

## 🚨 風險控制

### 回滾計劃

如果整合出現問題：

1. **立即回滾**:
   ```bash
   git revert <commit-hash>
   ```

2. **恢復舊檔案**:
   ```bash
   cp _Archive/Code_20260211/quantitative_risk_analysis.py .
   ```

3. **重啟服務**:
   ```bash
   ./啟動Web界面v2.sh
   ```

### 監控指標

整合後需要監控：
- ✅ Web 界面載入時間（不應增加）
- ✅ 記憶體使用（不應顯著增加）
- ✅ 錯誤日誌（不應有新錯誤）
- ✅ 功能完整性（所有指標正常顯示）

---

## 📅 時間表

| 階段 | 任務 | 時間 | 負責人 |
|------|------|------|--------|
| 1 | 創建新模組 | 第 1 週 | 開發團隊 |
| 2 | 創建兼容層 | 第 2 週 | 開發團隊 |
| 3 | 更新 Web 界面 | 第 3 週 | 開發團隊 |
| 4 | 整合到核心模組 | 第 4-5 週 | 開發團隊 |
| 5 | 全面測試 | 第 6 週 | QA 團隊 |
| 6 | 上線部署 | 第 7 週 | DevOps |

---

## 📝 總結

### 整合優點

1. ✅ **模組化**: 代碼結構更清晰
2. ✅ **可重用**: CLI/Web/實盤都可使用
3. ✅ **可測試**: 單元測試更容易
4. ✅ **可維護**: 統一管理，避免重複
5. ✅ **向後兼容**: 不影響現有功能

### 整合原則

1. ✅ **不影響現有功能**: 保持向後兼容
2. ✅ **逐步遷移**: 分階段進行，降低風險
3. ✅ **充分測試**: 每個階段都要測試
4. ✅ **保留回滾**: 隨時可以回滾
5. ✅ **文檔完整**: 記錄所有變更

---

**制定人**: Kiro AI Assistant  
**審核狀態**: 待審核  
**下一步**: 開始 Step 1 - 創建新模組
