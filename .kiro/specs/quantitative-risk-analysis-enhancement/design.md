# Design Document: Quantitative Risk Analysis Enhancement

## Overview

This design document specifies the enhancements to the quantitative risk analysis feature in the trading review system. The enhancements will improve the accuracy of risk calculations, add new detection algorithms for emotional trading behavior, provide more actionable recommendations, and enhance the visualization of risk metrics.

The system currently includes a `QuantitativeRiskOfficer` class that performs basic risk calculations. This enhancement will extend the class with new methods, improve existing algorithms, and integrate more deeply with the web dashboard and loss analysis components.

### Key Enhancement Areas

1. **Enhanced Tilt Detection**: Multi-factor algorithm with composite scoring
2. **Cooling Period Detection**: Automatic recommendation system based on loss patterns
3. **Advanced Fee Analysis**: Break-even calculations and efficiency metrics
4. **Improved Risk of Ruin**: Multiple calculation methods with confidence intervals
5. **Enhanced Visualizations**: Interactive charts and trend analysis
6. **Actionable Recommendations**: Prioritized, specific, measurable suggestions
7. **Historical Tracking**: Time-series analysis of risk metrics
8. **Market Context**: Risk analysis segmented by market conditions

## Architecture

### Component Structure

```
quantitative_risk_analysis.py (Enhanced)
├── QuantitativeRiskOfficer (Enhanced)
│   ├── Enhanced Tilt Detection Module
│   │   ├── calculate_tilt_score()
│   │   ├── detect_rapid_trading()
│   │   └── analyze_post_loss_behavior()
│   ├── Cooling Period Module (New)
│   │   ├── should_recommend_cooling_period()
│   │   ├── calculate_cooling_duration()
│   │   └── track_cooling_adherence()
│   ├── Advanced Fee Analysis Module (Enhanced)
│   │   ├── calculate_breakeven_metrics()
│   │   ├── calculate_fee_efficiency()
│   │   └── analyze_by_holding_time()
│   ├── Risk of Ruin Module (Enhanced)
│   │   ├── calculate_ror_kelly()
│   │   ├── calculate_ror_monte_carlo()
│   │   └── calculate_ror_probability()
│   ├── Recommendations Engine (New)
│   │   ├── generate_prioritized_recommendations()
│   │   ├── calculate_expected_impact()
│   │   └── track_recommendation_effectiveness()
│   ├── Historical Tracking Module (New)
│   │   ├── store_risk_snapshot()
│   │   ├── calculate_rolling_metrics()
│   │   └── detect_metric_trends()
│   └── Market Context Module (New)
│       ├── categorize_market_conditions()
│       ├── calculate_conditional_metrics()
│       └── recommend_strategy_adjustments()
│
web_dashboard_v2.py (Enhanced)
├── Risk Analysis Display (Enhanced)
│   ├── Risk Score Gauge
│   ├── Trend Charts
│   ├── Drawdown Timeline
│   └── Interactive Visualizations
│
src/analysis/loss_analyzer.py (Integration)
└── Integration with QuantitativeRiskOfficer
    ├── Cross-reference tilt with loss patterns
    └── Unified recommendation generation
```

### Data Flow

```
Trading Data (quality_scores.json)
    ↓
QuantitativeRiskOfficer.load_data()
    ↓
Risk Analysis Methods
    ├→ Enhanced Tilt Detection
    ├→ Cooling Period Detection
    ├→ Advanced Fee Analysis
    ├→ Risk of Ruin Calculations
    ├→ Historical Tracking
    └→ Market Context Analysis
    ↓
Recommendations Engine
    ↓
Dashboard Visualization
    ↓
User Actions & Feedback
    ↓
Effectiveness Tracking
```

## Components and Interfaces

### 1. Enhanced Tilt Detection Module

#### TiltScore Class

```python
@dataclass
class TiltScore:
    """Composite tilt behavior score"""
    overall_score: float  # 0-100
    severity: str  # 'none', 'low', 'medium', 'high'
    position_size_factor: float  # 0-1
    leverage_factor: float  # 0-1
    timing_factor: float  # 0-1
    frequency_factor: float  # 0-1
    contributing_factors: List[str]
    timestamp: datetime
```

#### Enhanced Detection Methods

```python
def calculate_tilt_score(self, trade_index: int) -> TiltScore:
    """
    Calculate composite tilt score for a trade
    
    Factors:
    - Position size change after loss (weight: 0.3)
    - Leverage change after loss (weight: 0.3)
    - Time to next trade after loss (weight: 0.2)
    - Trading frequency spike (weight: 0.2)
    
    Returns:
        TiltScore with overall score 0-100
    """
    
def detect_rapid_trading(self, window_minutes: int = 30) -> Dict:
    """
    Detect periods of abnormally rapid trading
    
    Args:
        window_minutes: Time window to analyze
        
    Returns:
        Dict with rapid trading periods and statistics
    """
    
def analyze_post_loss_behavior(self) -> Dict:
    """
    Analyze behavioral changes after losses
    
    Returns:
        Dict with statistics on post-loss trading patterns
    """
```

### 2. Cooling Period Module

#### CoolingPeriodRecommendation Class

```python
@dataclass
class CoolingPeriodRecommendation:
    """Cooling period recommendation"""
    should_cool: bool
    duration_minutes: int
    reason: str
    trigger_conditions: List[str]
    severity: str  # 'low', 'medium', 'high', 'critical'
    timestamp: datetime
```

#### Cooling Period Methods

```python
def should_recommend_cooling_period(self) -> CoolingPeriodRecommendation:
    """
    Determine if cooling period should be recommended
    
    Triggers:
    - 3+ consecutive losses
    - Cumulative daily loss > 5%
    - High tilt score detected
    - Rapid trading detected
    
    Returns:
        CoolingPeriodRecommendation
    """
    
def calculate_cooling_duration(
    self,
    consecutive_losses: int,
    cumulative_loss_pct: float,
    tilt_score: float
) -> int:
    """
    Calculate recommended cooling period duration
    
    Base duration: 30 minutes
    +15 min per consecutive loss over 3
    +30 min if cumulative loss > 10%
    +30 min if tilt score > 70
    
    Returns:
        Duration in minutes
    """
    
def track_cooling_adherence(self) -> Dict:
    """
    Track whether traders observe cooling periods
    
    Returns:
        Dict with adherence statistics and correlation with performance
    """
```

### 3. Advanced Fee Analysis Module

#### FeeAnalysis Class

```python
@dataclass
class FeeAnalysis:
    """Comprehensive fee analysis results"""
    total_fees: float
    fee_to_gross_profit_pct: float
    fee_to_loss_pct: float
    fee_to_volume_pct: float
    breakeven_win_rate: float
    minimum_profit_target: float
    fee_efficiency_ratio: float
    by_holding_time: Dict[str, Dict]  # Bucketed analysis
```

#### Fee Analysis Methods

```python
def calculate_breakeven_metrics(self) -> Dict:
    """
    Calculate break-even metrics considering fees
    
    Returns:
        - breakeven_win_rate: Win rate needed to break even
        - minimum_profit_target: Minimum profit per trade to overcome fees
        - current_margin: How far above/below breakeven
    """
    
def calculate_fee_efficiency(self) -> float:
    """
    Calculate fee efficiency ratio
    
    Formula: net_profit / total_fees
    
    Interpretation:
    - > 5.0: Excellent efficiency
    - 2.0-5.0: Good efficiency
    - 1.0-2.0: Acceptable efficiency
    - < 1.0: Poor efficiency (fees eating profits)
    
    Returns:
        Fee efficiency ratio
    """
    
def analyze_by_holding_time(self) -> Dict[str, Dict]:
    """
    Analyze fee impact by holding time buckets
    
    Buckets:
    - < 5 minutes
    - 5-30 minutes
    - 30-60 minutes
    - 1-4 hours
    - 4-24 hours
    - > 24 hours
    
    Returns:
        Dict mapping bucket to fee analysis
    """
```

### 4. Enhanced Risk of Ruin Module

#### RiskOfRuinAnalysis Class

```python
@dataclass
class RiskOfRuinAnalysis:
    """Comprehensive risk of ruin analysis"""
    kelly_ror: float
    monte_carlo_ror: float
    probability_ror: float
    recommended_ror: float  # Best estimate
    confidence_interval_95: Tuple[float, float]
    kelly_optimal_size: float
    prob_20pct_drawdown: float
    prob_50pct_drawdown: float
    method_used: str
```

#### Risk of Ruin Methods

```python
def calculate_ror_kelly(self) -> Dict:
    """
    Calculate Risk of Ruin using Kelly Criterion
    
    Formula: f* = (bp - q) / b
    Where:
    - f* = optimal fraction of capital
    - b = payoff ratio (avg_win / avg_loss)
    - p = win rate
    - q = loss rate (1 - p)
    
    RoR = (q/p)^(C/A)
    Where:
    - C = current capital
    - A = average win amount
    
    Returns:
        Dict with Kelly-based RoR and optimal position size
    """
    
def calculate_ror_monte_carlo(
    self,
    iterations: int = 10000,
    initial_capital: float = 1000.0
) -> Dict:
    """
    Calculate Risk of Ruin using Monte Carlo simulation
    
    Process:
    1. For each iteration:
       - Start with initial capital
       - Simulate trade sequence using historical win/loss distribution
       - Track if capital falls below ruin threshold (20% of initial)
    2. Calculate percentage of iterations that resulted in ruin
    
    Args:
        iterations: Number of Monte Carlo iterations
        initial_capital: Starting capital for simulation
        
    Returns:
        Dict with Monte Carlo RoR and confidence intervals
    """
    
def calculate_ror_probability(self) -> Dict:
    """
    Calculate Risk of Ruin using simplified probability formula
    
    Formula: RoR = ((1-W)/W)^(C/A)
    Where:
    - W = win rate
    - C = initial capital
    - A = average win amount
    
    Returns:
        Dict with probability-based RoR
    """
    
def calculate_drawdown_probabilities(self) -> Dict:
    """
    Calculate probability of various drawdown levels
    
    Uses Monte Carlo simulation to estimate:
    - Probability of 20% drawdown
    - Probability of 50% drawdown
    - Expected maximum drawdown
    
    Returns:
        Dict with drawdown probabilities
    """
```

### 5. Recommendations Engine

#### Recommendation Class

```python
@dataclass
class Recommendation:
    """Single recommendation"""
    id: str
    category: str  # 'risk', 'fee', 'tilt', 'loss_pattern'
    priority: int  # 1-5, 1 being highest
    title: str
    description: str
    specific_action: str
    expected_impact: float  # Expected improvement in %
    current_value: float
    target_value: float
    difficulty: str  # 'easy', 'medium', 'hard'
    related_requirements: List[str]
```

#### Recommendations Methods

```python
def generate_prioritized_recommendations(self) -> List[Recommendation]:
    """
    Generate prioritized list of recommendations
    
    Priority calculation:
    - Expected impact (40%)
    - Severity of issue (30%)
    - Ease of implementation (20%)
    - Frequency of issue (10%)
    
    Returns:
        List of Recommendation objects sorted by priority
    """
    
def calculate_expected_impact(
    self,
    recommendation_type: str,
    current_metrics: Dict
) -> float:
    """
    Calculate expected improvement from implementing recommendation
    
    Uses historical data and statistical models to estimate impact
    
    Returns:
        Expected improvement as percentage
    """
    
def track_recommendation_effectiveness(self) -> Dict:
    """
    Track which recommendations were followed and their actual impact
    
    Returns:
        Dict with recommendation tracking data
    """
```

### 6. Historical Tracking Module

#### RiskSnapshot Class

```python
@dataclass
class RiskSnapshot:
    """Point-in-time risk metrics snapshot"""
    timestamp: datetime
    risk_of_ruin: float
    max_losing_streak: int
    tilt_score: float
    fee_pressure: float
    total_trades: int
    win_rate: float
    expectancy: float
```

#### Historical Tracking Methods

```python
def store_risk_snapshot(self) -> None:
    """
    Store current risk metrics as a snapshot
    
    Snapshots stored in: data/risk_history/snapshots.json
    """
    
def calculate_rolling_metrics(
    self,
    window_days: int = 30
) -> pd.DataFrame:
    """
    Calculate rolling window risk metrics
    
    Args:
        window_days: Size of rolling window
        
    Returns:
        DataFrame with rolling metrics over time
    """
    
def detect_metric_trends(self) -> Dict:
    """
    Detect trends in risk metrics
    
    Uses linear regression to identify:
    - Improving metrics (negative slope)
    - Deteriorating metrics (positive slope)
    - Stable metrics (near-zero slope)
    
    Returns:
        Dict with trend analysis for each metric
    """
```

### 7. Market Context Module

#### MarketCondition Enum

```python
class MarketCondition(Enum):
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    RANGING = "ranging"
    UNKNOWN = "unknown"
```

#### Market Context Methods

```python
def categorize_market_conditions(
    self,
    market_data: pd.DataFrame
) -> Dict[str, MarketCondition]:
    """
    Categorize market conditions for each trade
    
    Uses:
    - ATR for volatility classification
    - Moving averages for trend classification
    
    Returns:
        Dict mapping trade_id to MarketCondition
    """
    
def calculate_conditional_metrics(self) -> Dict[MarketCondition, Dict]:
    """
    Calculate risk metrics segmented by market condition
    
    Returns:
        Dict mapping MarketCondition to risk metrics
    """
    
def recommend_strategy_adjustments(
    self,
    current_condition: MarketCondition
) -> List[str]:
    """
    Recommend strategy adjustments based on current market condition
    
    Returns:
        List of specific recommendations
    """
```

## Data Models

### Enhanced Trade Data Structure

The existing trade data structure in `quality_scores.json` will be extended with additional fields:

```python
{
    "trade_id": str,
    "symbol": str,
    "pnl": float,
    "leverage": float,
    "quantity": float,
    "fee": float,
    "open_time": str,
    "close_time": str,
    # New fields for enhanced analysis
    "position_size_usd": float,  # Position size in USD
    "time_to_next_trade_minutes": float,  # Time until next trade
    "is_post_loss_trade": bool,  # Whether this follows a loss
    "market_condition": str,  # Market condition during trade
    "tilt_score": float,  # Calculated tilt score
    "cooling_period_recommended": bool,  # Whether cooling was recommended
    "cooling_period_observed": bool  # Whether trader actually cooled
}
```

### Risk History Storage

New file: `data/risk_history/snapshots.json`

```python
{
    "snapshots": [
        {
            "timestamp": "2024-01-15T10:30:00",
            "risk_of_ruin": 0.15,
            "max_losing_streak": 7,
            "tilt_score": 35.5,
            "fee_pressure": 18.2,
            "total_trades": 150,
            "win_rate": 0.58,
            "expectancy": 2.5
        },
        ...
    ]
}
```

### Recommendations History

New file: `data/risk_history/recommendations.json`

```python
{
    "recommendations": [
        {
            "id": "rec_001",
            "timestamp": "2024-01-15T10:30:00",
            "category": "tilt",
            "priority": 1,
            "title": "Implement cooling period after losses",
            "expected_impact": 15.5,
            "status": "pending",  # pending, implemented, ignored
            "actual_impact": null  # Filled after implementation
        },
        ...
    ]
}
```


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property Reflection

After analyzing all acceptance criteria, I identified several areas where properties can be consolidated:

1. **Tilt Detection Calculations (1.1-1.3)**: These three properties all test basic calculations. They can be combined into one comprehensive property that validates all tilt-related calculations.

2. **Tilt Severity Classification (1.8-1.10)**: These three properties test classification into different severity levels. They can be combined into one property that validates the entire classification logic.

3. **Cooling Period Duration Rules (2.5-2.7)**: These three properties test specific duration recommendations. They can be combined into one property that validates the duration calculation logic.

4. **Fee Percentage Calculations (3.1-3.3)**: These three properties all calculate fees as a percentage of different bases. They can be combined into one comprehensive property.

5. **Risk of Ruin Methods (4.1-4.3)**: While these test different calculation methods, they should all be tested separately as they use different algorithms. No consolidation needed.

6. **Drawdown Calculations (6.1, 6.5, 6.9)**: These properties all calculate drawdown-related metrics. They can be combined into one comprehensive property.

7. **Rolling Metrics (9.2-9.3)**: These two properties test rolling calculations with different windows. They can be combined into one property that tests rolling calculations with configurable windows.

8. **Market Condition Segmentation (10.3-10.6)**: These four properties all test conditional risk calculations. They can be combined into one property that validates segmented calculations.

9. **Configurable Thresholds (12.1-12.5)**: These five properties all test threshold configuration. They can be combined into one property that validates threshold configuration for all risk metrics.

### Tilt Detection Properties

**Property 1: Tilt Metric Calculations**
*For any* pair of consecutive trades where the first is a loss, calculating position size change percentage, leverage change percentage, and time-to-next-trade should produce valid numerical results within expected ranges (position/leverage changes: -100% to +∞, time: ≥ 0 minutes).
**Validates: Requirements 1.1, 1.2, 1.3**

**Property 2: Tilt Behavior Flagging**
*For any* trade following a loss, if position size increases by more than 30% OR leverage increases by more than 30% OR time-to-next-trade is less than 5 minutes, then the trade should be flagged as potential tilt behavior.
**Validates: Requirements 1.4, 1.5, 1.6**

**Property 3: Composite Tilt Score Calculation**
*For any* set of tilt indicators (position size change, leverage change, timing, frequency), the composite tilt severity score should be between 0 and 100, and should increase monotonically as more indicators are present or their magnitudes increase.
**Validates: Requirements 1.7**

**Property 4: Tilt Severity Classification**
*For any* tilt score, the severity classification should be: 'low' if score < 40, 'medium' if 40 ≤ score ≤ 70, 'high' if score > 70, and the classification should be consistent for the same score.
**Validates: Requirements 1.8, 1.9, 1.10**

### Cooling Period Properties

**Property 5: Cooling Period Triggers**
*For any* trading sequence, if there are 3+ consecutive losses OR cumulative daily loss > 5% OR high tilt severity is detected, then a cooling period should be recommended.
**Validates: Requirements 2.1, 2.2, 2.3**

**Property 6: Cooling Duration Calculation**
*For any* combination of consecutive losses, cumulative loss percentage, and tilt score, the recommended cooling duration should be: 30 minutes for 5-10% loss, 60 minutes for >10% loss or >5 consecutive losses, and should increase with severity.
**Validates: Requirements 2.4, 2.5, 2.6, 2.7**

**Property 7: Cooling Period Tracking**
*For any* recommended cooling period, the system should track whether it was observed, record violations when traders trade before the period ends, and calculate correlation between adherence and subsequent performance.
**Validates: Requirements 2.8, 2.9, 2.10**

### Fee Analysis Properties

**Property 8: Fee Percentage Calculations**
*For any* set of trades with fees, gross profit, losses, and volume, calculating fees as a percentage of each should produce consistent results where: fee_pct_of_profit + fee_pct_of_loss ≈ fee_pct_of_volume (within rounding).
**Validates: Requirements 3.1, 3.2, 3.3**

**Property 9: Configurable Time Threshold Analysis**
*For any* configurable time threshold T, filtering trades by holding time < T and analyzing them should produce the same results as using a fixed threshold, demonstrating that the threshold is truly configurable.
**Validates: Requirements 3.4**

**Property 10: Break-Even Calculations**
*For any* fee structure and payoff ratio, the calculated break-even win rate should be the minimum win rate where expected value equals zero, and the minimum profit target should be the minimum profit per trade that overcomes fees.
**Validates: Requirements 3.5, 3.6**

**Property 11: Fee Warning Thresholds**
*For any* trading data, if fees exceed 20% of gross profit OR fees exceed 40% of total losses, then a high-priority warning should be issued.
**Validates: Requirements 3.7, 3.8**

**Property 12: Fee Efficiency Ratio**
*For any* trading data with net profit and total fees, the fee efficiency ratio (net profit / total fees) should be positive when profitable and should increase as profitability improves relative to fees.
**Validates: Requirements 3.9**

**Property 13: Fee Efficiency by Holding Time**
*For any* set of trades bucketed by holding time, comparing fee efficiency across buckets should show that longer holding times generally have better fee efficiency (fewer fees per unit profit).
**Validates: Requirements 3.10**

### Risk of Ruin Properties

**Property 14: Kelly Criterion Risk of Ruin**
*For any* win rate W and payoff ratio B, the Kelly Criterion Risk of Ruin should be calculated as RoR = (q/p)^(C/A) where q = 1-W, p = W, and should decrease as win rate or payoff ratio increases.
**Validates: Requirements 4.1**

**Property 15: Monte Carlo Risk of Ruin**
*For any* trading data, running Monte Carlo simulation with at least 10,000 iterations should produce a Risk of Ruin estimate with confidence intervals, and repeated simulations should produce results within those confidence intervals.
**Validates: Requirements 4.2, 4.6**

**Property 16: Probability-Based Risk of Ruin**
*For any* win rate and average win amount, the simplified probability formula RoR = ((1-W)/W)^(C/A) should produce a value between 0 and 1, and should decrease as win rate increases.
**Validates: Requirements 4.3**

**Property 17: Risk of Ruin Display and Selection**
*For any* trading data, all three Risk of Ruin calculations (Kelly, Monte Carlo, Probability) should be displayed, and when win rate and payoff ratio are available, Kelly Criterion should be marked as the primary method.
**Validates: Requirements 4.4, 4.5**

**Property 18: Kelly Optimal Position Size**
*For any* win rate W and payoff ratio B, the Kelly optimal position size f* = (B*W - (1-W)) / B should be between 0 and 1 for positive expectancy systems, and should be 0 or negative for negative expectancy systems.
**Validates: Requirements 4.7**

**Property 19: Drawdown Probability Calculations**
*For any* trading data, the calculated probabilities of 20% and 50% drawdowns should be between 0 and 1, with P(50% drawdown) ≤ P(20% drawdown), and both should be displayed with confidence intervals.
**Validates: Requirements 4.8, 4.9, 4.10**

### Consecutive Loss Properties

**Property 20: Consecutive Loss Streak Calculations**
*For any* sequence of trades, the maximum consecutive loss streak should be ≥ the average consecutive loss streak, and the total loss during the maximum streak should equal the sum of PnL for those trades.
**Validates: Requirements 5.1, 5.2, 5.3**

**Property 21: Streak Time Period Identification**
*For any* trading sequence with a maximum losing streak, the identified time period should span from the first trade's open time to the last trade's close time in that streak.
**Validates: Requirements 5.4**

**Property 22: Recovery Time Calculation**
*For any* losing streak, the recovery time should be the duration from the end of the streak until cumulative PnL returns to the pre-streak level, and should be ≥ 0.
**Validates: Requirements 5.5**

**Property 23: Losing Streak Analysis Trigger**
*For any* losing streak exceeding 5 trades, market condition analysis should be performed for that period, and the analysis should include volatility and trend metrics.
**Validates: Requirements 5.7**

**Property 24: Streak Probability Calculations**
*For any* win rate W and streak length N, the theoretical probability of N consecutive losses should be (1-W)^N, and the actual frequency should be compared against this theoretical value.
**Validates: Requirements 5.8, 5.9**

**Property 25: Streak Pattern Recommendations**
*For any* identified losing streak pattern, specific recommendations should be generated that address the pattern's characteristics (e.g., if streaks occur in high volatility, recommend reducing position size during volatility spikes).
**Validates: Requirements 5.10**

### Recovery Factor Properties

**Property 26: Drawdown Calculations**
*For any* equity curve, the maximum drawdown in absolute terms should equal the maximum difference between a peak and subsequent trough, and the percentage drawdown should equal (absolute_drawdown / peak_equity) * 100.
**Validates: Requirements 6.1**

**Property 27: Recovery Factor Formula**
*For any* drawdown percentage D, the recovery factor (percentage gain needed to break even) should equal D / (100 - D) * 100, which is always greater than D for D > 0.
**Validates: Requirements 6.2**

**Property 28: Recovery Time Metrics**
*For any* set of drawdown events, the average recovery time should be the mean of all recovery durations, and the longest recovery period should be the maximum of all recovery durations.
**Validates: Requirements 6.3, 6.4**

**Property 29: Current Drawdown Calculation**
*For any* equity curve, the current drawdown should equal (current_equity - peak_equity) / peak_equity * 100, and should be ≤ 0 (negative or zero).
**Validates: Requirements 6.5**

**Property 30: Drawdown Warnings and Recommendations**
*For any* current drawdown, if it exceeds 20%, a warning should be issued; if recovery factor exceeds 50%, a recommendation to reduce position sizes should be generated.
**Validates: Requirements 6.6, 6.7**

**Property 31: Drawdown Event Tracking**
*For any* equity curve, all drawdown events should be tracked with their depths and recovery times, and the average drawdown depth should equal the mean of all event depths.
**Validates: Requirements 6.8, 6.9**

**Property 32: Drawdown Timeline Visualization**
*For any* equity curve, the drawdown timeline visualization data should include timestamps, drawdown values, and recovery periods for all drawdown events.
**Validates: Requirements 6.10**

### Recommendations Engine Properties

**Property 33: Conditional Recommendations**
*For any* risk analysis results, if Risk of Ruin > 30%, recommendations for win rate/payoff improvements should be generated; if fee pressure is high, minimum profit targets should be recommended; if tilt is detected, cooling periods should be recommended; if consecutive losses exceed threshold, position size reductions should be recommended; if short-term trades have negative expectancy, minimum holding times should be recommended.
**Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5**

**Property 34: Recommendation Prioritization**
*For any* set of recommendations, they should be ordered by priority calculated from expected impact (40%), severity (30%), ease of implementation (20%), and frequency (10%), with higher priority recommendations appearing first.
**Validates: Requirements 7.6, 7.8**

**Property 35: Expected Impact Calculation**
*For any* recommendation, the expected improvement should be calculated based on historical data and statistical models, and should be expressed as a percentage improvement in profitability.
**Validates: Requirements 7.7**

**Property 36: Recommendation Specificity**
*For any* recommendation, it should include specific numerical targets (e.g., "increase win rate from 55% to 60%" rather than "improve win rate"), making it actionable and measurable.
**Validates: Requirements 7.9**

**Property 37: Recommendation Effectiveness Tracking**
*For any* recommendation, the system should track whether it was followed (implemented, ignored, or pending) and if implemented, calculate the actual impact on performance metrics.
**Validates: Requirements 7.10**

### Visualization Properties

**Property 38: Risk Score Gauge**
*For any* risk analysis results, the risk score gauge should display a value between 0 and 100, calculated as a weighted combination of Risk of Ruin, tilt score, fee pressure, and consecutive loss metrics.
**Validates: Requirements 8.1**

**Property 39: Risk Level Color Coding**
*For any* risk metric, the color coding should be: green for low risk (score < 30), yellow for medium risk (30 ≤ score ≤ 70), red for high risk (score > 70).
**Validates: Requirements 8.2**

**Property 40: Trend Chart Data Generation**
*For any* risk metric with historical data, trend chart data should include timestamps and values for all data points, sorted chronologically.
**Validates: Requirements 8.3, 8.8**

**Property 41: Visualization Data Completeness**
*For any* risk analysis, visualization data should be generated for: drawdown timeline, tilt frequency chart, fee pressure breakdown by duration, and correlation matrix between risk factors.
**Validates: Requirements 8.4, 8.5, 8.6, 8.9**

**Property 42: Threshold Comparison Display**
*For any* displayed metric, the comparison to safe thresholds should show: current value, threshold value, and whether current exceeds threshold.
**Validates: Requirements 8.7**

### Historical Tracking Properties

**Property 43: Risk Snapshot Storage**
*For any* risk analysis execution, a snapshot should be stored with timestamp and all key metrics (Risk of Ruin, max losing streak, tilt score, fee pressure, win rate, expectancy), and should be retrievable by timestamp.
**Validates: Requirements 9.1**

**Property 44: Rolling Metrics Calculation**
*For any* time series of risk snapshots and window size W (7 or 30 days), rolling metrics should be calculated using a sliding window, with each point representing the average of the previous W days.
**Validates: Requirements 9.2, 9.3**

**Property 45: Trend Detection**
*For any* risk metric time series, trend detection should identify: improving trends (negative slope), deteriorating trends (positive slope), and stable trends (near-zero slope) using linear regression.
**Validates: Requirements 9.4**

**Property 46: Risk Metric Alerts**
*For any* 7-day period, if Risk of Ruin increases by more than 10% OR tilt frequency increases by more than 20%, an alert should be issued.
**Validates: Requirements 9.5, 9.6**

**Property 47: Rate of Change Calculation**
*For any* risk metric time series, the rate of change should be calculated as (current_value - previous_value) / time_delta, expressed in units per day.
**Validates: Requirements 9.7**

**Property 48: Historical Period Identification**
*For any* risk history, the best period should have the lowest average risk score, and the worst period should have the highest average risk score.
**Validates: Requirements 9.8**

**Property 49: Historical Comparison**
*For any* current risk metric value, the comparison to historical average should show: current value, historical mean, historical standard deviation, and z-score.
**Validates: Requirements 9.9**

**Property 50: Risk Trend Visualization**
*For any* risk metric with historical data, trend visualization data should include: timestamps, values, moving averages, and trend lines.
**Validates: Requirements 9.10**

### Market Context Properties

**Property 51: Market Condition Categorization**
*For any* trade with market data, it should be categorized by both volatility level (high/low based on ATR) and trend direction (trending up/down/ranging based on moving averages).
**Validates: Requirements 10.1, 10.2**

**Property 52: Conditional Risk Metrics**
*For any* set of trades categorized by market conditions, separate risk metrics should be calculated for each condition (high volatility, low volatility, trending, ranging), and each should use only trades from that condition.
**Validates: Requirements 10.3, 10.4, 10.5, 10.6**

**Property 53: Market Condition Risk Identification**
*For any* set of conditional risk metrics, the highest risk condition should be the one with the highest average risk score, and the best risk-adjusted returns should be the condition with the highest Sharpe ratio.
**Validates: Requirements 10.7, 10.8**

**Property 54: Market Condition Warning**
*For any* current market condition, if it matches a historical pattern that produced high risk (risk score > 70), a warning should be issued.
**Validates: Requirements 10.9**

**Property 55: Strategy Adjustment Recommendations**
*For any* current market condition, specific strategy adjustments should be recommended based on historical performance in that condition (e.g., reduce position size in high volatility, avoid counter-trend trades in strong trends).
**Validates: Requirements 10.10**

### Integration Properties

**Property 56: Tilt and Loss Pattern Cross-Reference**
*For any* trade flagged as tilt behavior, it should be cross-referenced with loss reasons from LossAnalyzer, and the correlation between tilt and specific loss patterns should be calculated.
**Validates: Requirements 11.1, 11.2**

**Property 57: Loss Attribution Calculations**
*For any* set of losing trades, the percentage attributable to tilt behavior and the percentage attributable to fee pressure should be calculated, and their sum should be ≤ 100%.
**Validates: Requirements 11.3, 11.4**

**Property 58: Combined Recommendations**
*For any* analysis run, recommendations from both QuantitativeRiskOfficer and LossAnalyzer should be combined into a single list, prioritized by total potential impact.
**Validates: Requirements 11.5, 11.6**

**Property 59: Risk-Loss Pattern Correlation Highlighting**
*For any* loss pattern that correlates with high risk behavior (correlation > 0.5), the connection should be highlighted in the analysis output.
**Validates: Requirements 11.7**

**Property 60: High-Risk Trade Overlap**
*For any* set of trades, the overlap between high-risk trades (tilt score > 70) and specific loss categories should be calculated as the percentage of high-risk trades in each category.
**Validates: Requirements 11.8**

**Property 61: Unified Risk-Loss View**
*For any* analysis run, the unified view should include: risk factors (RoR, tilt, fees), loss patterns (from LossAnalyzer), and their correlations.
**Validates: Requirements 11.9**

**Property 62: Comprehensive Improvement Plan**
*For any* analysis run, the improvement plan should include recommendations addressing both risk issues (from QuantitativeRiskOfficer) and loss issues (from LossAnalyzer), ordered by priority.
**Validates: Requirements 11.10**

### Configuration Properties

**Property 63: Threshold Configuration**
*For any* risk metric (Risk of Ruin, consecutive losses, tilt sensitivity, fee pressure, cooling period triggers), user-configurable thresholds should be supported, and custom values should be applied in all calculations.
**Validates: Requirements 12.1, 12.2, 12.3, 12.4, 12.5**

**Property 64: Threshold Validation**
*For any* configured threshold, it should be validated to be within reasonable ranges (e.g., Risk of Ruin threshold: 0-1, consecutive losses: 1-100, tilt sensitivity: 0-100), and invalid values should be rejected.
**Validates: Requirements 12.6**

**Property 65: Threshold Modification Recalculation**
*For any* threshold modification, all risk assessments should be recalculated using the new thresholds, and results should differ from previous calculations if thresholds changed.
**Validates: Requirements 12.7**

**Property 66: Threshold Persistence**
*For any* user or trading account, threshold configurations should be stored persistently and retrieved correctly when the user logs in or the account is accessed.
**Validates: Requirements 12.8**

**Property 67: Preset Threshold Profiles**
*For any* trader type (conservative, moderate, aggressive), preset threshold profiles should exist with appropriate values (conservative: lower risk tolerance, aggressive: higher risk tolerance).
**Validates: Requirements 12.9**

**Property 68: Active Threshold Display**
*For any* dashboard view, the currently active thresholds should be displayed, showing which values are in use for each risk metric.
**Validates: Requirements 12.10**

## Error Handling

### Input Validation

1. **Trade Data Validation**
   - Validate that all required fields are present (trade_id, pnl, leverage, quantity, fee, timestamps)
   - Validate that numerical fields are valid numbers (not NaN or Inf)
   - Validate that timestamps are valid and in chronological order
   - Validate that leverage is positive
   - Handle missing or corrupted data gracefully with clear error messages

2. **Configuration Validation**
   - Validate threshold values are within acceptable ranges
   - Validate time window parameters are positive
   - Validate Monte Carlo iteration count is reasonable (1000-100000)
   - Provide default values for missing configuration

3. **Market Data Validation**
   - Validate market data timestamps align with trade timestamps
   - Validate price data is positive
   - Handle missing market data by falling back to trade-only analysis

### Calculation Error Handling

1. **Division by Zero**
   - Handle cases where denominators might be zero (e.g., no winning trades, no losing trades)
   - Return appropriate default values or None with clear indication

2. **Numerical Stability**
   - Handle very large or very small numbers in calculations
   - Use appropriate numerical precision for financial calculations
   - Avoid overflow/underflow in exponential calculations

3. **Statistical Edge Cases**
   - Handle cases with insufficient data (< 10 trades)
   - Handle cases with 100% win rate or 0% win rate
   - Handle cases with no variance in data

### User-Facing Errors

1. **Insufficient Data Errors**
   - Display clear message when < 10 trades available
   - Suggest actions to gather more data
   - Disable features that require minimum data

2. **Calculation Failures**
   - Display user-friendly error messages
   - Log detailed technical errors for debugging
   - Provide fallback values or skip failed calculations

3. **Integration Errors**
   - Handle cases where LossAnalyzer is not available
   - Handle cases where market data is not available
   - Gracefully degrade functionality

## Testing Strategy

### Dual Testing Approach

This feature will use both unit tests and property-based tests to ensure comprehensive coverage:

- **Unit tests**: Verify specific examples, edge cases, and error conditions
- **Property tests**: Verify universal properties across all inputs

### Unit Testing Focus

Unit tests should focus on:
- Specific examples that demonstrate correct behavior (e.g., known tilt scenarios)
- Integration points between QuantitativeRiskOfficer and LossAnalyzer
- Edge cases (empty data, single trade, 100% win rate, etc.)
- Error conditions (invalid data, missing fields, etc.)
- Dashboard rendering with various risk levels

### Property-Based Testing Focus

Property tests should focus on:
- Universal properties that hold for all inputs (see Correctness Properties section)
- Comprehensive input coverage through randomization
- Invariants that must be maintained (e.g., risk scores always 0-100)
- Relationships between metrics (e.g., max streak ≥ avg streak)

### Property Test Configuration

- **Minimum iterations**: 100 per property test (due to randomization)
- **Test framework**: Use `hypothesis` library for Python
- **Tag format**: Each property test must include a comment:
  ```python
  # Feature: quantitative-risk-analysis-enhancement, Property N: [property text]
  ```
- **Single property per test**: Each correctness property must be implemented by exactly ONE property-based test

### Test Data Generation

For property-based tests, generate:
- Random trade sequences with varying win/loss patterns
- Random position sizes and leverage values
- Random timestamps with realistic intervals
- Random fee structures
- Edge cases: empty sequences, single trades, all wins, all losses

### Integration Testing

Test integration with:
- LossAnalyzer for cross-referencing tilt and loss patterns
- Web dashboard for visualization rendering
- File system for snapshot storage and retrieval
- Configuration system for threshold management

### Performance Testing

- Test Monte Carlo simulation performance with 10,000 iterations
- Test rolling metrics calculation with large datasets (1000+ trades)
- Test dashboard rendering with large datasets
- Ensure all calculations complete within reasonable time (< 5 seconds for typical dataset)

### Regression Testing

- Maintain test suite for existing functionality
- Ensure enhancements don't break current features
- Test backward compatibility with existing data files
