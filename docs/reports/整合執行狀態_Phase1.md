# Quantitative Risk Analysis 整合執行狀態

**日期**: 2026-02-11  
**階段**: Phase 1 - 創建新模組  
**狀態**: 進行中

---

## ✅ 已完成的工作

### 1. 深度了解現有架構

已完整閱讀並分析以下檔案：

#### 整合方案文檔
- `整合方案_quantitative_risk.md` (15頁完整方案)
- `整合執行清單.md` (詳細執行步驟)

#### 原始檔案
- `quantitative_risk_analysis.py` (1197行，完整實現)
  - 11個核心功能
  - 7個數據模型
  - 完整的量化分析邏輯

#### 使用方
- `pages/review/quality_scoring.py` (3263行)
  - 第1752行：`from quantitative_risk_analysis import QuantitativeRiskOfficer`
  - 使用所有11個核心功能
  - Web界面的關鍵依賴

#### 現有核心系統
- `src/analysis/__init__.py` - 當前導出
- `src/managers/risk_manager.py` - 風險管理器（缺少Kelly, Tilt）
- `src/analysis/loss_analyzer.py` - 虧損分析器（缺少Tilt檢測）
- `src/analysis/performance_monitor.py` - 性能監控器（缺少情緒分析）

### 2. 功能對比分析

| 功能 | quantitative_risk_analysis.py | 現有核心系統 | 重疊度 |
|------|------------------------------|-------------|--------|
| Kelly Criterion | ✅ | ❌ | 0% |
| Tilt Score | ✅ | ❌ | 0% |
| 情緒失控分析 | ✅ | ❌ | 0% |
| 能力維度評分 | ✅ | ❌ | 0% |
| 破產風險 | ✅ | ❌ | 0% |
| 手續費分析 | ✅ | ❌ | 0% |
| 冷靜期檢測 | ✅ | ❌ | 0% |
| 連續虧損檢測 | ✅ | ✅ | 80% |
| 回撤計算 | ✅ | ✅ | 70% |

**結論**: 大部分功能是獨特的，沒有重複開發的風險。

### 3. 整合策略確認

採用**7階段漸進式整合**：

1. ✅ Phase 1: 創建新模組（當前階段）
2. ⏳ Phase 2: 創建兼容層
3. ⏳ Phase 3: 更新 Web 界面
4. ⏳ Phase 4: 整合到核心模組
5. ⏳ Phase 6: 提供 CLI 接口
6. ⏳ Phase 6: 全面測試
7. ⏳ Phase 7: 文檔與部署

**核心原則**：
- ✅ 不影響現有功能
- ✅ 保持向後兼容
- ✅ 逐步遷移，降低風險
- ✅ 充分測試每個階段
- ✅ 隨時可以回滾

---

## 🔄 Phase 1 進度

### 目標
創建 `src/analysis/quantitative_risk.py` 新模組，提供與原始檔案相同的功能，但採用模組化架構。

### 已創建的結構

```python
# src/analysis/quantitative_risk.py (部分完成)

# 數據模型 (✅ 已定義)
- TiltScore
- KellyCriterion
- EmotionalControl
- SkillDimensions
- CoolingPeriodRecommendation
- FeeAnalysis

# 核心分析器 (🔄 進行中)
- KellyCriterionCalculator (部分完成)
- TiltDetector (開始)
- EmotionalControlAnalyzer (待實現)
- SkillDimensionScorer (待實現)
- FeeAnalyzer (待實現)
- CoolingPeriodChecker (待實現)

# 主類 (待實現)
- QuantitativeRiskAnalyzer
```

### 需要完成的工作

#### 1. 完成核心分析器實現

**TiltDetector** (傾斜行為檢測器):
```python
def detect(self, df: pd.DataFrame) -> Dict:
    # 檢測虧損後的報復性加倉
    # 分析槓桿和倉位變化
    # 計算傾斜嚴重程度
```

**EmotionalControlAnalyzer** (情緒控制分析器):
```python
def analyze(self, df: pd.DataFrame) -> Dict:
    # 分析虧損後的下單頻率
    # 計算槓桿變化
    # 評分 0-100
```

**SkillDimensionScorer** (能力維度評分器):
```python
def score(self, df: pd.DataFrame) -> Dict:
    # 5個維度評分：
    # 1. 方向研判力
    # 2. 風險控管力
    # 3. 心理韌性
    # 4. 執行紀律
    # 5. 成本意識
```

**FeeAnalyzer** (手續費分析器):
```python
def analyze(self, df: pd.DataFrame) -> Dict:
    # 計算手續費壓力
    # 分析短線交易
    # 模擬停止短線交易的影響
```

**CoolingPeriodChecker** (冷靜期檢測器):
```python
def check(self, df: pd.DataFrame) -> Dict:
    # 檢測是否需要冷靜期
    # 觸發條件：
    # - 連續虧損 >= 3
    # - 單日虧損 > 5%
    # - 高度傾斜行為
```

#### 2. 實現主類 QuantitativeRiskAnalyzer

```python
class QuantitativeRiskAnalyzer:
    \"\"\"量化風險分析器（主類）\"\"\"
    
    def __init__(self, trades_data_path: str = None):
        self.kelly_calculator = KellyCriterionCalculator()
        self.tilt_detector = TiltDetector()
        self.emotional_analyzer = EmotionalControlAnalyzer()
        self.skill_scorer = SkillDimensionScorer()
        self.fee_analyzer = FeeAnalyzer()
        self.cooling_checker = CoolingPeriodChecker()
        
        if trades_data_path:
            self.load_data(trades_data_path)
    
    def load_data(self, path: str):
        \"\"\"載入交易數據\"\"\"
        # 從 JSON 載入並轉換為 DataFrame
    
    # 提供與原始 API 兼容的方法
    def calculate_ror_kelly(self) -> Dict:
        \"\"\"計算 Kelly Criterion（兼容 API）\"\"\"
        return self.kelly_calculator.calculate(self.df)
    
    def detect_tilt_behavior(self) -> Dict:
        \"\"\"檢測傾斜行為（兼容 API）\"\"\"
        return self.tilt_detector.detect(self.df)
    
    def analyze_emotional_control(self) -> Dict:
        \"\"\"分析情緒控制（兼容 API）\"\"\"
        return self.emotional_analyzer.analyze(self.df)
    
    def calculate_skill_dimensions(self) -> Dict:
        \"\"\"計算能力維度（兼容 API）\"\"\"
        return self.skill_scorer.score(self.df)
    
    def calculate_fee_pressure(self) -> Dict:
        \"\"\"計算手續費壓力（兼容 API）\"\"\"
        return self.fee_analyzer.analyze(self.df)
    
    def check_cooling_period(self) -> Dict:
        \"\"\"檢測冷靜期（兼容 API）\"\"\"
        return self.cooling_checker.check(self.df)
    
    # ... 其他11個方法 ...
```

#### 3. 更新 `src/analysis/__init__.py`

```python
from .quantitative_risk import (
    QuantitativeRiskAnalyzer,
    KellyCriterionCalculator,
    TiltDetector,
    EmotionalControlAnalyzer,
    SkillDimensionScorer,
    FeeAnalyzer,
    CoolingPeriodChecker,
    # 數據模型
    TiltScore,
    KellyCriterion,
    EmotionalControl,
    SkillDimensions,
    CoolingPeriodRecommendation,
    FeeAnalysis,
)

__all__ = [
    # 現有導出
    'LossAnalyzer',
    'LossAnalysis',
    'LossPattern',
    'PerformanceMonitor',
    'PerformanceMetrics',
    'AlertConfig',
    # 新增導出
    'QuantitativeRiskAnalyzer',
    'KellyCriterionCalculator',
    'TiltDetector',
    'EmotionalControlAnalyzer',
    'SkillDimensionScorer',
    'FeeAnalyzer',
    'CoolingPeriodChecker',
    'TiltScore',
    'KellyCriterion',
    'EmotionalControl',
    'SkillDimensions',
    'CoolingPeriodRecommendation',
    'FeeAnalysis',
]
```

#### 4. 編寫單元測試

```python
# tests/analysis/test_quantitative_risk.py

import pytest
from src.analysis.quantitative_risk import (
    QuantitativeRiskAnalyzer,
    KellyCriterionCalculator,
    TiltDetector,
)

class TestKellyCriterion:
    def test_calculate_optimal_size(self):
        # 測試 Kelly 最優倉位計算
        pass
    
    def test_risk_of_ruin(self):
        # 測試破產風險計算
        pass

class TestTiltDetector:
    def test_detect_tilt_behavior(self):
        # 測試傾斜行為檢測
        pass

# ... 更多測試 ...
```

---

## 📋 下一步行動

### 立即執行（Phase 1 完成）

1. **完成 `src/analysis/quantitative_risk.py` 實現**
   - 實現所有核心分析器
   - 實現主類 QuantitativeRiskAnalyzer
   - 確保所有11個方法都有實現

2. **更新 `src/analysis/__init__.py`**
   - 添加新模組的導出

3. **編寫單元測試**
   - 創建 `tests/analysis/test_quantitative_risk.py`
   - 測試所有核心功能

4. **運行測試**
   ```bash
   pytest tests/analysis/test_quantitative_risk.py -v
   ```

### Phase 2 準備

一旦 Phase 1 完成並測試通過，立即進入 Phase 2：

1. **修改 `quantitative_risk_analysis.py` 為兼容層**
   ```python
   import warnings
   from src.analysis.quantitative_risk import QuantitativeRiskAnalyzer
   
   warnings.warn("...", DeprecationWarning)
   QuantitativeRiskOfficer = QuantitativeRiskAnalyzer
   ```

2. **測試向後兼容性**
   - 確保舊代碼仍能運行
   - 確保 Web 界面不受影響

---

## 🚨 風險控制

### 回滾計劃

如果 Phase 1 出現問題：

1. **刪除新檔案**
   ```bash
   rm src/analysis/quantitative_risk.py
   rm tests/analysis/test_quantitative_risk.py
   ```

2. **恢復 `src/analysis/__init__.py`**
   ```bash
   git checkout src/analysis/__init__.py
   ```

3. **確認原始檔案未受影響**
   ```bash
   ls -la quantitative_risk_analysis.py
   ls -la pages/review/quality_scoring.py
   ```

### 測試檢查點

在每個步驟後運行：

```bash
# 1. 語法檢查
python3 -m py_compile src/analysis/quantitative_risk.py

# 2. 導入測試
python3 -c "from src.analysis.quantitative_risk import QuantitativeRiskAnalyzer"

# 3. 單元測試
pytest tests/analysis/test_quantitative_risk.py -v

# 4. Web 界面測試（Phase 2 後）
./啟動Web界面v2.sh
```

---

## 📊 進度追蹤

| 任務 | 狀態 | 完成度 | 備註 |
|------|------|--------|------|
| 閱讀整合方案 | ✅ 完成 | 100% | 已完整理解 |
| 閱讀原始檔案 | ✅ 完成 | 100% | 1197行全部閱讀 |
| 閱讀使用方 | ✅ 完成 | 100% | 確認第1752行使用 |
| 閱讀核心系統 | ✅ 完成 | 100% | 4個核心檔案 |
| 創建數據模型 | ✅ 完成 | 100% | 6個模型 |
| 創建分析器 | 🔄 進行中 | 20% | 6個分析器 |
| 創建主類 | ⏳ 待開始 | 0% | QuantitativeRiskAnalyzer |
| 更新 __init__ | ⏳ 待開始 | 0% | 添加導出 |
| 編寫測試 | ⏳ 待開始 | 0% | 單元測試 |
| 運行測試 | ⏳ 待開始 | 0% | pytest |

**總體進度**: Phase 1 約 30% 完成

---

## 💡 建議

### 繼續執行 Phase 1

由於檔案較大（1197行），建議：

1. **分批實現**：每次實現1-2個分析器，立即測試
2. **保持簡單**：先實現核心邏輯，優化可以後續進行
3. **頻繁測試**：每完成一個分析器就測試一次
4. **參考原始**：直接從 `quantitative_risk_analysis.py` 複製邏輯，確保功能一致

### 時間估算

- 完成 Phase 1：2-3 小時
- 完成 Phase 2：30 分鐘
- 完成 Phase 3：1 小時
- 完成 Phase 4-7：3-4 小時

**總計**：約 7-9 小時完成整個整合

---

**制定人**: Kiro AI Assistant  
**最後更新**: 2026-02-11  
**下一步**: 完成 `src/analysis/quantitative_risk.py` 實現
