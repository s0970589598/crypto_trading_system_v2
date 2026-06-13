"""
量化風險分析模組 (Quantitative Risk Analysis Module)

提供高級定量風險分析功能：
- Kelly Criterion 最優倉位計算
- Tilt Score 傾斜行為評分
- 情緒失控係數分析
- 能力維度評分
- 破產風險分析
- 手續費壓力測試
- 冷靜期檢測

整合自 quantitative_risk_analysis.py，提供模組化、可重用的 API。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import json
import statistics
import warnings

warnings.filterwarnings('ignore')


# ==================== 數據模型 ====================

@dataclass
class TiltScore:
    """傾斜行為綜合評分"""
    overall_score: float  # 0-100
    severity: str  # 'none', 'low', 'medium', 'high'
    position_size_factor: float  # 0-1
    leverage_factor: float  # 0-1
    timing_factor: float  # 0-1
    frequency_factor: float  # 0-1
    contributing_factors: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


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
    score: float  # 0-100
    severity: str  # 'none', 'low', 'medium', 'high', 'critical'
    frequency_increase_after_loss: float
    leverage_increase_after_loss: float
    avg_time_between_trades_normal: float
    avg_time_between_trades_after_loss: float
    cases_count: int


@dataclass
class SkillDimensions:
    """能力維度評分"""
    direction_judgment: float  # 0-10
    risk_management: float  # 0-10
    psychological_resilience: float  # 0-10
    execution_discipline: float  # 0-10
    cost_awareness: float  # 0-10
    overall_score: float  # 0-10
    deduction_reasons: Dict[str, List[str]] = field(default_factory=dict)


@dataclass
class CoolingPeriodRecommendation:
    """冷靜期建議"""
    should_cool: bool
    duration_minutes: int
    reason: str
    severity: str  # 'low', 'medium', 'high', 'critical'
    trigger_conditions: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class FeeAnalysis:
    """手續費分析結果"""
    total_fees: float
    fee_to_gross_profit_pct: float
    fee_to_loss_pct: float
    fee_to_volume_pct: float
    breakeven_win_rate: float
    minimum_profit_target: float
    fee_efficiency_ratio: float
    by_holding_time: Dict[str, Dict] = field(default_factory=dict)


# ==================== 核心分析器 ====================

class KellyCriterionCalculator:
    """Kelly Criterion 計算器
    
    使用 Kelly 公式計算最優倉位和破產風險：
    - f* = (bp - q) / b
    - RoR = (q/p)^(C/A)
    """
    
    def calculate(self, df: pd.DataFrame, initial_capital: float = 1000.0) -> Dict:
        """計算 Kelly Criterion
        
        Args:
            df: 交易數據 DataFrame
            initial_capital: 初始資金
            
        Returns:
            Dict: Kelly 分析結果
        """
        if df is None or len(df) == 0:
            return {'kelly_ror': 1.0, 'explanation': '無數據'}
        
        # 計算勝率
        win_rate = df['is_win'].sum() / len(df)
        loss_rate = 1 - win_rate
        
        # 計算平均獲利和平均虧損
        winning_trades = df[df['is_win']]
        losing_trades = df[df['is_loss']]
        
        if len(winning_trades) == 0 or len(losing_trades) == 0:
            return {
                'kelly_ror': 1.0 if win_rate == 0 else 0.0,
                'kelly_optimal_size': 0.0,
                'win_rate': float(win_rate),
                'explanation': '數據不足以計算 Kelly Criterion'
            }
        
        avg_win = float(winning_trades['pnl'].mean())
        avg_loss = float(abs(losing_trades['pnl'].mean()))
        
        # 計算賠率 (Payoff Ratio)
        payoff_ratio = avg_win / avg_loss if avg_loss > 0 else 0
        
        # 計算 Kelly 最優倉位: f* = (bp - q) / b
        if payoff_ratio > 0:
            kelly_optimal = (payoff_ratio * win_rate - loss_rate) / payoff_ratio
        else:
            kelly_optimal = 0.0
        
        kelly_optimal = max(0.0, min(1.0, kelly_optimal))
        
        # 計算破產風險: RoR = (q/p)^(C/A)
        if win_rate > 0 and avg_win > 0:
            try:
                kelly_ror = (loss_rate / win_rate) ** (initial_capital / (avg_win * 10))
                kelly_ror = min(1.0, max(0.0, kelly_ror))
            except:
                kelly_ror = 0.5
        elif win_rate == 0:
            kelly_ror = 1.0
        else:
            kelly_ror = 0.0
        
        expectancy = win_rate * avg_win - loss_rate * avg_loss
        recommended_size = kelly_optimal * 0.5  # Half Kelly
        
        return {
            'kelly_ror': float(kelly_ror),
            'kelly_optimal_size': float(kelly_optimal),
            'recommended_size': float(recommended_size),
            'win_rate': float(win_rate),
            'loss_rate': float(loss_rate),
            'avg_win': float(avg_win),
            'avg_loss': float(avg_loss),
            'payoff_ratio': float(payoff_ratio),
            'expectancy': float(expectancy),
            'explanation': f'Kelly 最優倉位 {kelly_optimal:.2%}，建議使用 {recommended_size:.2%}（Half Kelly）'
        }


class TiltDetector:
    """傾斜行為檢測器 - 檢測虧損後的報復性加倉行為"""
    
    def detect(self, df: pd.DataFrame) -> Dict:
        """檢測傾斜行為"""
        if df is None or len(df) < 2:
            return {'has_tilt': False, 'explanation': '數據不足'}

        
        df_sorted = df.sort_values('close_time').copy()
        tilt_cases = []
        
        for i in range(len(df_sorted) - 1):
            current_trade = df_sorted.iloc[i]
            next_trade = df_sorted.iloc[i + 1]
            
            if current_trade['is_loss']:
                current_leverage = current_trade['leverage']
                next_leverage = next_trade['leverage']
                current_quantity = current_trade['quantity']
                next_quantity = next_trade['quantity']
                
                leverage_increase = (next_leverage - current_leverage) / current_leverage * 100 if current_leverage > 0 else 0
                quantity_increase = (next_quantity - current_quantity) / current_quantity * 100 if current_quantity > 0 else 0
                
                if leverage_increase > 20 or quantity_increase > 20:
                    tilt_cases.append({
                        'after_trade_id': current_trade.get('trade_id', 'N/A'),
                        'after_loss': float(current_trade['pnl']),
                        'next_trade_id': next_trade.get('trade_id', 'N/A'),
                        'leverage_increase_pct': float(leverage_increase),
                        'quantity_increase_pct': float(quantity_increase),
                        'next_pnl': float(next_trade['pnl'])
                    })
        
        if len(tilt_cases) > 0:
            tilt_pnls = [case['next_pnl'] for case in tilt_cases]
            avg_tilt_pnl = float(np.mean(tilt_pnls))
            tilt_win_rate = float(sum(1 for pnl in tilt_pnls if pnl > 0) / len(tilt_pnls))
            has_tilt = True
            severity = 'high' if len(tilt_cases) > len(df_sorted) * 0.2 else 'medium' if len(tilt_cases) > len(df_sorted) * 0.1 else 'low'
        else:
            avg_tilt_pnl = 0.0
            tilt_win_rate = 0.0
            has_tilt = False
            severity = 'none'
        
        df_sorted['prev_is_loss'] = df_sorted['is_loss'].shift(1)
        df_sorted['leverage_change'] = df_sorted['leverage'].diff()
        after_loss_leverage_change = df_sorted[df_sorted['prev_is_loss'] == True]['leverage_change'].mean()
        after_win_leverage_change = df_sorted[df_sorted['prev_is_loss'] == False]['leverage_change'].mean()
        
        return {
            'has_tilt': bool(has_tilt),
            'severity': severity,
            'tilt_cases_count': int(len(tilt_cases)),
            'tilt_cases_percentage': float(len(tilt_cases) / (len(df_sorted) - 1) * 100) if len(df_sorted) > 1 else 0.0,
            'avg_tilt_pnl': float(avg_tilt_pnl),
            'tilt_win_rate': float(tilt_win_rate),
            'avg_leverage_change_after_loss': float(after_loss_leverage_change) if not pd.isna(after_loss_leverage_change) else 0.0,
            'avg_leverage_change_after_win': float(after_win_leverage_change) if not pd.isna(after_win_leverage_change) else 0.0,
            'tilt_cases': tilt_cases[:5],
            'explanation': f'檢測到 {len(tilt_cases)} 次傾斜行為（{len(tilt_cases) / (len(df_sorted) - 1) * 100:.1f}%），嚴重程度：{severity}' if len(df_sorted) > 1 else '數據不足'
        }



class EmotionalControlAnalyzer:
    """情緒控制分析器 - 分析虧損後的下單頻率和槓桿變化"""
    
    def analyze(self, df: pd.DataFrame) -> Dict:
        """分析情緒控制"""
        if df is None or len(df) < 3:
            return {'emotional_control_score': 100.0, 'severity': 'none', 'explanation': '數據不足'}
        
        df_sorted = df.sort_values('close_time').copy()
        df_sorted['time_to_next_trade'] = df_sorted['open_time'].diff().shift(-1).dt.total_seconds() / 60
        
        after_loss_intervals = []
        after_win_intervals = []
        emotional_cases = []
        
        for i in range(len(df_sorted) - 1):
            current_trade = df_sorted.iloc[i]
            next_trade = df_sorted.iloc[i + 1]
            time_interval = current_trade['time_to_next_trade']
            
            if pd.isna(time_interval) or time_interval <= 0:
                continue
            
            if current_trade['is_loss']:
                after_loss_intervals.append(time_interval)
                leverage_increase = 0
                if current_trade['leverage'] > 0:
                    leverage_increase = (next_trade['leverage'] - current_trade['leverage']) / current_trade['leverage'] * 100
                
                if time_interval < 5 or leverage_increase > 20:
                    emotional_cases.append({
                        'after_loss': float(current_trade['pnl']),
                        'time_interval': float(time_interval),
                        'leverage_increase': float(leverage_increase),
                        'next_pnl': float(next_trade['pnl'])
                    })
            else:
                after_win_intervals.append(time_interval)
        
        avg_after_loss = float(np.mean(after_loss_intervals)) if after_loss_intervals else 0.0
        avg_after_win = float(np.mean(after_win_intervals)) if after_win_intervals else 0.0
        avg_normal = float(df_sorted['time_to_next_trade'].mean())
        
        frequency_increase = (avg_normal - avg_after_loss) / avg_normal * 100 if avg_after_loss > 0 and avg_normal > 0 else 0.0
        
        df_sorted['prev_is_loss'] = df_sorted['is_loss'].shift(1)
        df_sorted['leverage_change'] = df_sorted['leverage'].diff()
        after_loss_leverage_change = df_sorted[df_sorted['prev_is_loss'] == True]['leverage_change'].mean()
        leverage_increase_pct = float(after_loss_leverage_change / df_sorted['leverage'].mean() * 100) if not pd.isna(after_loss_leverage_change) else 0.0
        
        score = 100.0
        if frequency_increase > 50:
            score -= 30
        elif frequency_increase > 30:
            score -= 20
        elif frequency_increase > 10:
            score -= 10
        
        if leverage_increase_pct > 30:
            score -= 30
        elif leverage_increase_pct > 20:
            score -= 20
        elif leverage_increase_pct > 10:
            score -= 10
        
        if len(emotional_cases) > len(df_sorted) * 0.3:
            score -= 20
        elif len(emotional_cases) > len(df_sorted) * 0.2:
            score -= 15
        elif len(emotional_cases) > len(df_sorted) * 0.1:
            score -= 10
        
        score = max(0.0, score)
        
        if score >= 80:
            severity = 'none'
        elif score >= 60:
            severity = 'low'
        elif score >= 40:
            severity = 'medium'
        elif score >= 20:
            severity = 'high'
        else:
            severity = 'critical'
        
        return {
            'emotional_control_score': float(score),
            'severity': severity,
            'frequency_increase_after_loss': float(frequency_increase),
            'leverage_increase_after_loss': float(leverage_increase_pct),
            'avg_time_between_trades_normal': float(avg_normal),
            'avg_time_between_trades_after_loss': float(avg_after_loss),
            'avg_time_between_trades_after_win': float(avg_after_win),
            'cases_count': int(len(emotional_cases)),
            'cases_percentage': float(len(emotional_cases) / len(df_sorted) * 100),
            'emotional_cases': emotional_cases[:5],
            'explanation': f'情緒控制評分 {score:.1f}/100，嚴重程度：{severity}'
        }


class SkillDimensionScorer:
    """能力維度評分器 - 計算五大能力維度評分"""
    
    def score(self, df: pd.DataFrame) -> Dict:
        """計算能力維度評分"""
        if df is None or len(df) < 10:
            return {'overall_score': 0.0, 'explanation': '數據不足（需要至少10筆交易）'}
        
        deduction_reasons = {
            'direction_judgment': [],
            'risk_management': [],
            'psychological_resilience': [],
            'execution_discipline': [],
            'cost_awareness': []
        }
        
        # 1. 方向研判力
        win_rate = df['is_win'].sum() / len(df)
        direction_score = 10.0
        
        if win_rate < 0.3:
            direction_score = 3.0
            deduction_reasons['direction_judgment'].append(f'勝率過低（{win_rate:.1%}），嚴重低於及格線')
        elif win_rate < 0.4:
            direction_score = 5.0
            deduction_reasons['direction_judgment'].append(f'勝率偏低（{win_rate:.1%}），需要改善方向判斷')
        elif win_rate < 0.45:
            direction_score = 7.0
            deduction_reasons['direction_judgment'].append(f'勝率略低（{win_rate:.1%}），接近及格線')
        elif win_rate < 0.5:
            direction_score = 8.5
        
        # 2. 風險控管力
        winning_trades = df[df['is_win']]
        losing_trades = df[df['is_loss']]
        risk_score = 10.0
        
        if len(winning_trades) > 0 and len(losing_trades) > 0:
            avg_win = winning_trades['pnl'].mean()
            max_loss = abs(losing_trades['pnl'].min())
            loss_to_win_ratio = max_loss / avg_win if avg_win > 0 else 999
            
            if loss_to_win_ratio > 5:
                risk_score = 2.0
                deduction_reasons['risk_management'].append(f'單筆最大虧損是平均獲利的 {loss_to_win_ratio:.1f} 倍（遠超過 2 倍）')
            elif loss_to_win_ratio > 3:
                risk_score = 4.0
                deduction_reasons['risk_management'].append(f'單筆最大虧損是平均獲利的 {loss_to_win_ratio:.1f} 倍（超過 2 倍）')
            elif loss_to_win_ratio > 2:
                risk_score = 6.0
                deduction_reasons['risk_management'].append(f'單筆最大虧損是平均獲利的 {loss_to_win_ratio:.1f} 倍（略超過 2 倍）')
            elif loss_to_win_ratio > 1.5:
                risk_score = 8.0
        
        # 3. 心理韌性
        tilt_detector = TiltDetector()
        emotional_analyzer = EmotionalControlAnalyzer()
        tilt_result = tilt_detector.detect(df)
        emotional_result = emotional_analyzer.analyze(df)
        
        psychological_score = 10.0
        
        if tilt_result['severity'] == 'high':
            psychological_score -= 5
            deduction_reasons['psychological_resilience'].append(f'檢測到高度傾斜行為（{tilt_result["tilt_cases_count"]} 次）')
        elif tilt_result['severity'] == 'medium':
            psychological_score -= 3
            deduction_reasons['psychological_resilience'].append(f'檢測到中度傾斜行為（{tilt_result["tilt_cases_count"]} 次）')
        elif tilt_result['severity'] == 'low':
            psychological_score -= 1
        
        if emotional_result['severity'] == 'critical':
            psychological_score -= 5
            deduction_reasons['psychological_resilience'].append(f'情緒控制極差（評分 {emotional_result["emotional_control_score"]:.1f}/100）')
        elif emotional_result['severity'] == 'high':
            psychological_score -= 3
            deduction_reasons['psychological_resilience'].append(f'情緒控制不佳（評分 {emotional_result["emotional_control_score"]:.1f}/100）')
        elif emotional_result['severity'] == 'medium':
            psychological_score -= 2
            deduction_reasons['psychological_resilience'].append(f'情緒控制一般（評分 {emotional_result["emotional_control_score"]:.1f}/100）')
        
        psychological_score = max(0.0, psychological_score)
        
        # 4. 執行紀律
        execution_score = 10.0
        leverage_std = df['leverage'].std()
        leverage_mean = df['leverage'].mean()
        leverage_cv = leverage_std / leverage_mean if leverage_mean > 0 else 0
        
        if leverage_cv > 0.5:
            execution_score -= 3
            deduction_reasons['execution_discipline'].append(f'槓桿使用極不一致（變異係數 {leverage_cv:.2f}）')
        elif leverage_cv > 0.3:
            execution_score -= 2
            deduction_reasons['execution_discipline'].append(f'槓桿使用不夠一致（變異係數 {leverage_cv:.2f}）')
        
        execution_score = max(0.0, execution_score)
        
        # 5. 成本意識
        cost_score = 10.0
        small_trades = df[abs(df['pnl']) < 1.0]
        if len(small_trades) > len(df) * 0.3:
            cost_score -= 2
            deduction_reasons['cost_awareness'].append(f'{len(small_trades)} 筆小額交易（{len(small_trades)/len(df)*100:.1f}%），手續費效率低')
        
        cost_score = max(0.0, cost_score)
        
        overall_score = (direction_score + risk_score + psychological_score + execution_score + cost_score) / 5
        
        return {
            'direction_judgment': float(direction_score),
            'risk_management': float(risk_score),
            'psychological_resilience': float(psychological_score),
            'execution_discipline': float(execution_score),
            'cost_awareness': float(cost_score),
            'overall_score': float(overall_score),
            'deduction_reasons': deduction_reasons,
            'win_rate': float(win_rate),
            'explanation': f'綜合能力評分 {overall_score:.1f}/10'
        }


class FeeAnalyzer:
    """手續費分析器"""
    
    def analyze_fee_pressure(self, df: pd.DataFrame) -> Dict:
        """計算手續費壓力"""
        if df is None or len(df) == 0:
            return {}
        
        total_fee = float(df['fee'].sum())
        total_loss = float(abs(df[df['is_loss']]['pnl'].sum()))
        total_pnl = float(df['pnl'].sum())
        
        fee_to_loss_ratio = (total_fee / total_loss * 100) if total_loss > 0 else 0.0
        fee_to_pnl_ratio = (total_fee / abs(total_pnl) * 100) if total_pnl != 0 else 0.0
        
        return {
            'total_fee': float(total_fee),
            'total_loss': float(total_loss),
            'total_pnl': float(total_pnl),
            'fee_to_loss_ratio': float(fee_to_loss_ratio),
            'fee_to_pnl_ratio': float(fee_to_pnl_ratio),
            'explanation': f'總手續費 {total_fee:.2f} USDT，佔總虧損的 {fee_to_loss_ratio:.2f}%'
        }
    
    def analyze_short_term_trades(self, df: pd.DataFrame, threshold_minutes: float = 5.0) -> Dict:
        """分析短線交易"""
        if df is None or len(df) == 0:
            return {}
        
        short_trades = df[df['holding_minutes'] < threshold_minutes].copy()
        
        if len(short_trades) == 0:
            return {
                'count': 0,
                'explanation': f'沒有持倉時間 < {threshold_minutes} 分鐘的交易'
            }
        
        short_total_pnl = float(short_trades['pnl'].sum())
        short_total_fee = float(short_trades['fee'].sum())
        short_win_rate = float(short_trades['is_win'].sum() / len(short_trades))
        short_avg_pnl = float(short_trades['pnl'].mean())
        
        short_wins = short_trades[short_trades['is_win']]
        short_losses = short_trades[short_trades['is_loss']]
        
        if len(short_wins) > 0 and len(short_losses) > 0:
            avg_win = float(short_wins['pnl'].mean())
            avg_loss = float(abs(short_losses['pnl'].mean()))
            expectancy = short_win_rate * avg_win - (1 - short_win_rate) * avg_loss
        else:
            expectancy = short_avg_pnl
        
        return {
            'count': int(len(short_trades)),
            'percentage': float(len(short_trades) / len(df) * 100),
            'total_pnl': float(short_total_pnl),
            'total_fee': float(short_total_fee),
            'win_rate': float(short_win_rate),
            'avg_pnl': float(short_avg_pnl),
            'expectancy': float(expectancy),
            'explanation': f'{len(short_trades)} 筆短線交易，期望值 {expectancy:.2f} USDT'
        }
    
    def simulate_without_short_trades(self, df: pd.DataFrame, threshold_minutes: float = 5.0) -> Dict:
        """模擬停止短線交易的影響"""
        if df is None or len(df) == 0:
            return {}
        
        original_pnl = float(df['pnl'].sum())
        original_fee = float(df['fee'].sum())
        
        long_trades = df[df['holding_minutes'] >= threshold_minutes].copy()
        
        if len(long_trades) == 0:
            return {'explanation': '所有交易都是短線交易，無法模擬'}
        
        new_pnl = float(long_trades['pnl'].sum())
        new_fee = float(long_trades['fee'].sum())
        pnl_difference = new_pnl - original_pnl
        fee_saved = original_fee - new_fee
        
        original_win_rate = float(df['is_win'].sum() / len(df))
        new_win_rate = float(long_trades['is_win'].sum() / len(long_trades))
        
        return {
            'original_pnl': float(original_pnl),
            'new_pnl': float(new_pnl),
            'pnl_difference': float(pnl_difference),
            'pnl_improvement_pct': float((pnl_difference / abs(original_pnl) * 100) if original_pnl != 0 else 0),
            'fee_saved': float(fee_saved),
            'original_win_rate': float(original_win_rate),
            'new_win_rate': float(new_win_rate),
            'trades_eliminated': int(len(df) - len(long_trades)),
            'explanation': f'停止短線交易後，淨值變化 {pnl_difference:+.2f} USDT ({(pnl_difference / abs(original_pnl) * 100) if original_pnl != 0 else 0:+.2f}%)'
        }


class CoolingPeriodChecker:
    """冷靜期檢測器"""
    
    def check(self, df: pd.DataFrame) -> Dict:
        """檢測是否需要冷靜期"""
        if df is None or len(df) == 0:
            return {'should_cool': False, 'reason': '無數據'}
        
        df_sorted = df.sort_values('close_time').copy()
        
        # 計算連續虧損
        consecutive_losses = 0
        for i in range(len(df_sorted) - 1, -1, -1):
            if not df_sorted.iloc[i]['is_win']:
                consecutive_losses += 1
            else:
                break
        
        # 計算單日虧損
        df_sorted['date'] = pd.to_datetime(df_sorted['close_time']).dt.date
        daily_pnl = df_sorted.groupby('date')['pnl'].sum()
        initial_capital = 1000.0
        max_daily_loss_pct = (daily_pnl.min() / initial_capital * 100) if len(daily_pnl) > 0 else 0
        
        # 檢查傾斜
        tilt_detector = TiltDetector()
        tilt_result = tilt_detector.detect(df)
        tilt_severity = tilt_result.get('severity', 'none')
        
        should_cool = False
        reasons = []
        duration_minutes = 0
        severity = 'low'
        
        if consecutive_losses >= 3:
            should_cool = True
            reasons.append(f'連續虧損 {consecutive_losses} 次')
            duration_minutes += 30
            if consecutive_losses >= 5:
                duration_minutes += 30
                severity = 'high'
            elif consecutive_losses >= 4:
                severity = 'medium'
        
        if max_daily_loss_pct < -5:
            should_cool = True
            reasons.append(f'單日虧損 {abs(max_daily_loss_pct):.2f}%')
            if max_daily_loss_pct < -10:
                duration_minutes += 60
                severity = 'critical'
            else:
                duration_minutes += 30
                if severity != 'critical':
                    severity = 'high'
        
        if tilt_severity == 'high':
            should_cool = True
            reasons.append('檢測到高度傾斜行為')
            duration_minutes += 30
            if severity not in ['critical', 'high']:
                severity = 'medium'
        
        if not should_cool:
            return {
                'should_cool': False,
                'duration_minutes': 0,
                'reason': '交易狀態正常',
                'severity': 'none',
                'consecutive_losses': consecutive_losses,
                'max_daily_loss_pct': max_daily_loss_pct,
                'tilt_severity': tilt_severity
            }
        
        duration_minutes = max(30, min(120, duration_minutes))
        reason = '、'.join(reasons)
        
        return {
            'should_cool': True,
            'duration_minutes': duration_minutes,
            'reason': reason,
            'severity': severity,
            'consecutive_losses': consecutive_losses,
            'max_daily_loss_pct': max_daily_loss_pct,
            'tilt_severity': tilt_severity,
            'recommendation': f'建議休息 {duration_minutes} 分鐘後再交易'
        }




# ==================== 主類 ====================

class QuantitativeRiskAnalyzer:
    """量化風險分析器（主類）
    
    整合所有分析器，提供統一的 API 接口。
    兼容原始 QuantitativeRiskOfficer 的所有方法。
    """
    
    def __init__(self, trades_data_path: str = None, trades_df: pd.DataFrame = None):
        """初始化量化風險分析器
        
        Args:
            trades_data_path: 交易數據路徑（JSON 格式）
            trades_df: 交易數據 DataFrame（可直接傳入，優先於 trades_data_path）
        """
        self.trades_data_path = trades_data_path
        self.df = None
        
        # 初始化所有分析器
        self.kelly_calculator = KellyCriterionCalculator()
        self.tilt_detector = TiltDetector()
        self.emotional_analyzer = EmotionalControlAnalyzer()
        self.skill_scorer = SkillDimensionScorer()
        self.fee_analyzer = FeeAnalyzer()
        self.cooling_checker = CoolingPeriodChecker()
        
        # 如果直接提供了 DataFrame，使用它
        if trades_df is not None:
            self.df = trades_df.copy()
            self._prepare_dataframe()
        # 否則如果提供了數據路徑，載入它
        elif trades_data_path:
            self.load_data(trades_data_path)
    
    def load_data(self, path: str = None):
        """載入交易數據
        
        Args:
            path: 數據路徑（可選，如果不提供則使用初始化時的路徑）
        """
        if path:
            self.trades_data_path = path
        
        if not self.trades_data_path:
            raise ValueError("未提供數據路徑")
        
        try:
            with open(self.trades_data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.df = pd.DataFrame(data)
            self._prepare_dataframe()
            
            print(f"✅ 成功載入 {len(self.df)} 筆交易數據")
            
        except Exception as e:
            print(f"❌ 載入數據失敗：{e}")
            raise
    
    def _prepare_dataframe(self):
        """準備和清洗 DataFrame 數據"""
        if self.df is None or len(self.df) == 0:
            return
        
        # 數據清洗和類型轉換
        if 'pnl' in self.df.columns:
            self.df['pnl'] = pd.to_numeric(self.df['pnl'], errors='coerce')
        
        if 'leverage' in self.df.columns:
            self.df['leverage'] = pd.to_numeric(self.df['leverage'], errors='coerce')
        
        if 'quantity' in self.df.columns:
            self.df['quantity'] = pd.to_numeric(self.df['quantity'], errors='coerce')
        
        if 'fee' in self.df.columns:
            self.df['fee'] = pd.to_numeric(self.df['fee'], errors='coerce')
        
        # 轉換時間
        if 'open_time' in self.df.columns:
            self.df['open_time'] = pd.to_datetime(self.df['open_time'], errors='coerce')
        
        if 'close_time' in self.df.columns:
            self.df['close_time'] = pd.to_datetime(self.df['close_time'], errors='coerce')
        
        # 計算持倉時間（分鐘）
        if 'open_time' in self.df.columns and 'close_time' in self.df.columns:
            self.df['holding_minutes'] = (
                (self.df['close_time'] - self.df['open_time']).dt.total_seconds() / 60
            )
        
        # 判斷盈虧
        if 'pnl' in self.df.columns:
            self.df['is_win'] = self.df['pnl'] > 0
            self.df['is_loss'] = self.df['pnl'] < 0
    
    # ==================== 兼容 API 方法 ====================
    
    def calculate_ror_kelly(self) -> Dict:
        """計算 Kelly Criterion（兼容 API）"""
        return self.kelly_calculator.calculate(self.df)
    
    def detect_tilt_behavior(self) -> Dict:
        """檢測傾斜行為（兼容 API）"""
        return self.tilt_detector.detect(self.df)
    
    def analyze_emotional_control(self) -> Dict:
        """分析情緒控制（兼容 API）"""
        return self.emotional_analyzer.analyze(self.df)
    
    def calculate_skill_dimensions(self) -> Dict:
        """計算能力維度評分（兼容 API）"""
        return self.skill_scorer.score(self.df)
    
    def calculate_fee_pressure(self) -> Dict:
        """計算手續費壓力（兼容 API）"""
        return self.fee_analyzer.analyze_fee_pressure(self.df)
    
    def analyze_short_term_trades(self, threshold_minutes: float = 5.0) -> Dict:
        """分析短線交易（兼容 API）"""
        return self.fee_analyzer.analyze_short_term_trades(self.df, threshold_minutes)
    
    def simulate_without_short_trades(self, threshold_minutes: float = 5.0) -> Dict:
        """模擬停止短線交易（兼容 API）"""
        return self.fee_analyzer.simulate_without_short_trades(self.df, threshold_minutes)
    
    def check_cooling_period(self) -> Dict:
        """檢測冷靜期（兼容 API）"""
        return self.cooling_checker.check(self.df)
    
    def calculate_max_losing_streak(self) -> Dict:
        """計算最長連續虧損次數（兼容 API）"""
        if self.df is None or len(self.df) == 0:
            return {'max_streak': 0, 'total_loss_in_streak': 0.0, 'details': []}
        
        df_sorted = self.df.sort_values('close_time').copy()
        
        current_streak = 0
        max_streak = 0
        max_streak_start_idx = 0
        max_streak_end_idx = 0
        current_streak_start_idx = 0
        
        for idx, row in df_sorted.iterrows():
            if row['is_loss']:
                if current_streak == 0:
                    current_streak_start_idx = idx
                current_streak += 1
                
                if current_streak > max_streak:
                    max_streak = current_streak
                    max_streak_start_idx = current_streak_start_idx
                    max_streak_end_idx = idx
            else:
                current_streak = 0
        
        if max_streak > 0:
            streak_trades = df_sorted.loc[max_streak_start_idx:max_streak_end_idx]
            details = []
            for _, trade in streak_trades.iterrows():
                details.append({
                    'trade_id': trade.get('trade_id', 'N/A'),
                    'symbol': trade.get('symbol', 'N/A'),
                    'pnl': float(trade['pnl']),
                    'close_time': str(trade['close_time'])
                })
        else:
            details = []
        
        return {
            'max_streak': int(max_streak),
            'total_loss_in_streak': float(df_sorted.loc[max_streak_start_idx:max_streak_end_idx, 'pnl'].sum()) if max_streak > 0 else 0.0,
            'details': details
        }
    
    def calculate_risk_of_ruin(self, initial_capital: float = 1000.0) -> Dict:
        """計算破產風險（兼容 API）"""
        if self.df is None or len(self.df) == 0:
            return {'risk_of_ruin': 0.0, 'explanation': '無數據'}
        
        win_rate = self.df['is_win'].sum() / len(self.df)
        winning_trades = self.df[self.df['is_win']]
        losing_trades = self.df[self.df['is_loss']]
        
        if len(winning_trades) == 0 or len(losing_trades) == 0:
            return {
                'risk_of_ruin': 0.0 if win_rate == 1.0 else 1.0,
                'win_rate': float(win_rate),
                'explanation': '數據不足以計算破產風險'
            }
        
        avg_win = float(winning_trades['pnl'].mean())
        avg_loss = float(abs(losing_trades['pnl'].mean()))
        payoff_ratio = avg_win / avg_loss if avg_loss > 0 else 0
        
        if win_rate >= 1.0:
            risk_of_ruin = 0.0
        elif win_rate <= 0.0:
            risk_of_ruin = 1.0
        else:
            try:
                if payoff_ratio * win_rate > (1 - win_rate):
                    risk_of_ruin = ((1 - win_rate) / win_rate) ** (initial_capital / (avg_win * 10))
                else:
                    risk_of_ruin = min(1.0, ((1 - win_rate) / win_rate) / payoff_ratio)
            except:
                risk_of_ruin = 0.5
        
        return {
            'risk_of_ruin': float(min(1.0, max(0.0, risk_of_ruin))),
            'win_rate': float(win_rate),
            'avg_win': float(avg_win),
            'avg_loss': float(avg_loss),
            'payoff_ratio': float(payoff_ratio),
            'expectancy': float(win_rate * avg_win - (1 - win_rate) * avg_loss),
            'explanation': f'勝率 {win_rate:.2%}，賠率 {payoff_ratio:.2f}:1'
        }
    
    def calculate_recovery_factor(self) -> Dict:
        """計算恢復係數（兼容 API）"""
        if self.df is None or len(self.df) == 0:
            return {'recovery_factor': 0.0, 'max_drawdown_pct': 0.0}
        
        df_sorted = self.df.sort_values('close_time').copy()
        df_sorted['cumulative_pnl'] = df_sorted['pnl'].cumsum()
        df_sorted['cumulative_max'] = df_sorted['cumulative_pnl'].cummax()
        df_sorted['drawdown'] = df_sorted['cumulative_pnl'] - df_sorted['cumulative_max']
        df_sorted['drawdown_pct'] = (df_sorted['drawdown'] / (1000 + df_sorted['cumulative_max'])) * 100
        
        max_drawdown = float(df_sorted['drawdown'].min())
        max_drawdown_pct = float(df_sorted['drawdown_pct'].min())
        
        if max_drawdown_pct < 0:
            recovery_needed_pct = abs(max_drawdown_pct) / (1 + max_drawdown_pct / 100) * 100
        else:
            recovery_needed_pct = 0.0
        
        return {
            'max_drawdown': float(max_drawdown),
            'max_drawdown_pct': float(max_drawdown_pct),
            'recovery_needed_pct': float(recovery_needed_pct),
            'explanation': f'最大回撤 {abs(max_drawdown_pct):.2f}%，需要獲利 {recovery_needed_pct:.2f}% 才能回到原點'
        }


