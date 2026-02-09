# Requirements Document

## Introduction

This document specifies the requirements for enhancing the quantitative risk analysis feature in the trading review system. The system currently includes a QuantitativeRiskOfficer class that performs risk calculations and displays results in the web dashboard. This enhancement will improve accuracy, add missing features, enhance visualizations, and provide more actionable insights for traders.

## Glossary

- **System**: The trading review system including web dashboard and analysis modules
- **QuantitativeRiskOfficer**: The class responsible for performing quantitative risk calculations
- **Dashboard**: The web-based user interface (web_dashboard_v2.py)
- **Trader**: The end user who reviews their trading performance
- **Tilt**: Emotional trading behavior characterized by increased risk-taking after losses
- **Risk_of_Ruin**: The probability of losing all trading capital
- **Cooling_Period**: A mandatory waiting time after losses before allowing new trades
- **Fee_Pressure**: The impact of trading fees on overall profitability
- **Consecutive_Loss_Streak**: A sequence of losing trades without interruption
- **Recovery_Factor**: The percentage gain needed to recover from maximum drawdown

## Requirements

### Requirement 1: Enhanced Tilt Detection Algorithm

**User Story:** As a trader, I want more accurate tilt detection, so that I can identify and prevent emotional trading behavior before it causes significant losses.

#### Acceptance Criteria

1. WHEN analyzing trades after losses, THE System SHALL calculate position size changes as a percentage
2. WHEN analyzing trades after losses, THE System SHALL calculate leverage changes as a percentage
3. WHEN analyzing trades after losses, THE System SHALL calculate time-to-next-trade as a duration
4. WHEN position size increases by more than 30% after a loss, THE System SHALL flag it as potential tilt behavior
5. WHEN leverage increases by more than 30% after a loss, THE System SHALL flag it as potential tilt behavior
6. WHEN time-to-next-trade is less than 5 minutes after a loss, THE System SHALL flag it as potential tilt behavior
7. WHEN multiple tilt indicators are present, THE System SHALL calculate a composite tilt severity score from 0 to 100
8. WHEN tilt severity score exceeds 70, THE System SHALL classify it as high severity
9. WHEN tilt severity score is between 40 and 70, THE System SHALL classify it as medium severity
10. WHEN tilt severity score is below 40, THE System SHALL classify it as low severity

### Requirement 2: Cooling Period Detection and Recommendation

**User Story:** As a trader, I want the system to detect when I should take a break after losses, so that I can avoid making emotional decisions.

#### Acceptance Criteria

1. WHEN a trader has 3 or more consecutive losses, THE System SHALL recommend a cooling period
2. WHEN a trader's cumulative loss exceeds 5% in a single day, THE System SHALL recommend a cooling period
3. WHEN tilt behavior is detected with high severity, THE System SHALL recommend a cooling period
4. WHEN recommending a cooling period, THE System SHALL calculate the suggested duration based on loss severity
5. WHEN cumulative loss is between 5% and 10%, THE System SHALL recommend a 30-minute cooling period
6. WHEN cumulative loss exceeds 10%, THE System SHALL recommend a 60-minute cooling period
7. WHEN consecutive losses exceed 5, THE System SHALL recommend a 60-minute cooling period
8. THE System SHALL track whether traders actually observe cooling periods
9. WHEN a trader violates a recommended cooling period, THE System SHALL record it as a violation
10. THE System SHALL calculate the correlation between cooling period adherence and subsequent trading performance

### Requirement 3: Advanced Fee Pressure Analysis

**User Story:** As a trader, I want detailed analysis of how fees impact my profitability, so that I can optimize my trading frequency and holding times.

#### Acceptance Criteria

1. THE System SHALL calculate total fees as a percentage of gross profit
2. THE System SHALL calculate total fees as a percentage of total losses
3. THE System SHALL calculate total fees as a percentage of total trading volume
4. WHEN analyzing short-term trades, THE System SHALL support configurable time thresholds
5. THE System SHALL calculate the break-even win rate needed to overcome fee pressure
6. THE System SHALL identify the optimal minimum profit target that justifies trading costs
7. WHEN fees exceed 20% of gross profit, THE System SHALL issue a high-priority warning
8. WHEN fees exceed 40% of total losses, THE System SHALL issue a high-priority warning
9. THE System SHALL calculate fee efficiency ratio as (net profit / total fees)
10. THE System SHALL compare fee efficiency across different holding time buckets

### Requirement 4: Improved Risk of Ruin Calculation

**User Story:** As a trader, I want more accurate bankruptcy risk calculations, so that I can understand my true risk exposure.

#### Acceptance Criteria

1. THE System SHALL calculate Risk of Ruin using the Kelly Criterion formula
2. THE System SHALL calculate Risk of Ruin using the Monte Carlo simulation method
3. THE System SHALL calculate Risk of Ruin using the simplified probability formula
4. THE System SHALL display all three Risk of Ruin calculations for comparison
5. WHEN win rate and payoff ratio data is available, THE System SHALL use Kelly Criterion as the primary method
6. WHEN historical trade sequence data is available, THE System SHALL run Monte Carlo simulation with at least 10000 iterations
7. THE System SHALL calculate the maximum safe position size using Kelly Criterion
8. THE System SHALL calculate the probability of a 20% drawdown
9. THE System SHALL calculate the probability of a 50% drawdown
10. THE System SHALL display confidence intervals for all risk calculations

### Requirement 5: Enhanced Consecutive Loss Analysis

**User Story:** As a trader, I want detailed analysis of losing streaks, so that I can understand patterns and prepare contingency plans.

#### Acceptance Criteria

1. THE System SHALL calculate the maximum consecutive loss streak
2. THE System SHALL calculate the average consecutive loss streak
3. THE System SHALL calculate the total loss amount during the maximum streak
4. THE System SHALL identify the time period when the maximum streak occurred
5. THE System SHALL calculate the recovery time after each losing streak
6. THE System SHALL identify common characteristics of trades during losing streaks
7. WHEN a losing streak exceeds 5 trades, THE System SHALL analyze market conditions during that period
8. THE System SHALL calculate the probability of experiencing a streak of N consecutive losses
9. THE System SHALL compare actual streak frequency against theoretical probability
10. THE System SHALL provide specific recommendations for each identified losing streak pattern

### Requirement 6: Recovery Factor Enhancement

**User Story:** As a trader, I want to understand how difficult it is to recover from drawdowns, so that I can set realistic expectations and adjust my risk management.

#### Acceptance Criteria

1. THE System SHALL calculate the maximum drawdown in both absolute and percentage terms
2. THE System SHALL calculate the recovery factor as percentage gain needed to break even
3. THE System SHALL calculate the average time to recover from drawdowns
4. THE System SHALL identify the longest recovery period in the trading history
5. THE System SHALL calculate the current drawdown from the equity peak
6. WHEN current drawdown exceeds 20%, THE System SHALL issue a warning
7. WHEN recovery factor exceeds 50%, THE System SHALL recommend reducing position sizes
8. THE System SHALL track multiple drawdown events and their recovery patterns
9. THE System SHALL calculate the average drawdown depth across all drawdown events
10. THE System SHALL display a drawdown timeline visualization

### Requirement 7: Actionable Recommendations Engine

**User Story:** As a trader, I want specific, actionable recommendations based on my risk analysis, so that I know exactly what changes to make.

#### Acceptance Criteria

1. WHEN Risk of Ruin exceeds 30%, THE System SHALL recommend specific win rate or payoff ratio improvements
2. WHEN fee pressure is high, THE System SHALL recommend minimum profit targets for each trade
3. WHEN tilt behavior is detected, THE System SHALL recommend specific cooling period durations
4. WHEN consecutive losses exceed threshold, THE System SHALL recommend position size reductions
5. WHEN short-term trades have negative expectancy, THE System SHALL recommend minimum holding times
6. THE System SHALL prioritize recommendations by potential impact on profitability
7. THE System SHALL calculate the expected improvement for each recommendation
8. WHEN multiple issues are detected, THE System SHALL recommend addressing them in priority order
9. THE System SHALL provide specific numerical targets for each recommendation
10. THE System SHALL track whether recommendations were followed and their effectiveness

### Requirement 8: Enhanced Visualization and Display

**User Story:** As a trader, I want clear, intuitive visualizations of risk metrics, so that I can quickly understand my risk profile.

#### Acceptance Criteria

1. THE Dashboard SHALL display a risk score gauge from 0 to 100
2. THE Dashboard SHALL use color coding for risk levels (green, yellow, red)
3. THE Dashboard SHALL display trend charts for key risk metrics over time
4. THE Dashboard SHALL display a drawdown timeline chart
5. THE Dashboard SHALL display a tilt behavior frequency chart
6. THE Dashboard SHALL display a fee pressure breakdown by trade duration
7. WHEN displaying metrics, THE Dashboard SHALL show comparison to safe thresholds
8. THE Dashboard SHALL display historical trends for Risk of Ruin
9. THE Dashboard SHALL display a correlation matrix between risk factors
10. THE Dashboard SHALL support exporting risk analysis reports as PDF

### Requirement 9: Historical Risk Tracking

**User Story:** As a trader, I want to track how my risk metrics change over time, so that I can measure improvement and identify deterioration early.

#### Acceptance Criteria

1. THE System SHALL store risk analysis results with timestamps
2. THE System SHALL calculate rolling 30-day risk metrics
3. THE System SHALL calculate rolling 7-day risk metrics
4. THE System SHALL detect when risk metrics are trending worse
5. WHEN Risk of Ruin increases by more than 10% in 7 days, THE System SHALL issue an alert
6. WHEN tilt frequency increases by more than 20% in 7 days, THE System SHALL issue an alert
7. THE System SHALL calculate the rate of change for each risk metric
8. THE System SHALL identify the best and worst risk periods in trading history
9. THE System SHALL compare current risk metrics to historical averages
10. THE System SHALL display risk metric trends in the dashboard

### Requirement 10: Market Condition Context

**User Story:** As a trader, I want to understand how market conditions affect my risk metrics, so that I can adjust my strategy for different market environments.

#### Acceptance Criteria

1. WHEN analyzing risk metrics, THE System SHALL categorize trades by market volatility level
2. WHEN analyzing risk metrics, THE System SHALL categorize trades by market trend direction
3. THE System SHALL calculate separate risk metrics for high volatility periods
4. THE System SHALL calculate separate risk metrics for low volatility periods
5. THE System SHALL calculate separate risk metrics for trending markets
6. THE System SHALL calculate separate risk metrics for ranging markets
7. THE System SHALL identify which market conditions produce the highest risk
8. THE System SHALL identify which market conditions produce the best risk-adjusted returns
9. WHEN current market conditions match high-risk historical patterns, THE System SHALL issue a warning
10. THE System SHALL recommend strategy adjustments based on current market conditions

### Requirement 11: Integration with Loss Analyzer

**User Story:** As a trader, I want quantitative risk analysis integrated with loss pattern analysis, so that I get a complete picture of my trading weaknesses.

#### Acceptance Criteria

1. THE System SHALL cross-reference tilt behavior with loss reasons from LossAnalyzer
2. THE System SHALL identify if tilt behavior correlates with specific loss patterns
3. THE System SHALL calculate the percentage of losses attributable to tilt behavior
4. THE System SHALL calculate the percentage of losses attributable to fee pressure
5. THE System SHALL combine recommendations from both risk analysis and loss analysis
6. THE System SHALL prioritize combined recommendations by total potential impact
7. WHEN a loss pattern correlates with high risk behavior, THE System SHALL highlight this connection
8. THE System SHALL calculate the overlap between high-risk trades and specific loss categories
9. THE System SHALL display a unified view of risk factors and loss patterns
10. THE System SHALL generate a comprehensive improvement plan addressing both risk and loss issues

### Requirement 12: Configurable Risk Thresholds

**User Story:** As a trader, I want to customize risk thresholds based on my risk tolerance, so that alerts and recommendations match my trading style.

#### Acceptance Criteria

1. THE System SHALL support user-configurable thresholds for Risk of Ruin warnings
2. THE System SHALL support user-configurable thresholds for maximum consecutive losses
3. THE System SHALL support user-configurable thresholds for tilt detection sensitivity
4. THE System SHALL support user-configurable thresholds for fee pressure warnings
5. THE System SHALL support user-configurable thresholds for cooling period triggers
6. THE System SHALL validate that configured thresholds are within reasonable ranges
7. WHEN thresholds are modified, THE System SHALL recalculate all risk assessments
8. THE System SHALL store threshold configurations per user or trading account
9. THE System SHALL provide preset threshold profiles for conservative, moderate, and aggressive traders
10. THE System SHALL display which thresholds are currently active in the dashboard
