"""
量化風險分析工具 (Quantitative Risk Analysis)
角色：高頻交易量化風險官

執行嚴格的數學運算，不允許模糊估算
使用 Pandas 進行精確計算
"""

import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum
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


@dataclass
@dataclass
class RiskOfRuinAnalysis:
    """破產風險綜合分析"""
    kelly_ror: float
    monte_carlo_ror: float
    probability_ror: float
    recommended_ror: float  # 最佳估計
    confidence_interval_95: Tuple[float, float]
    kelly_optimal_size: float
    prob_20pct_drawdown: float
    prob_50pct_drawdown: float
    method_used: str


@dataclass
class EmotionalControlAnalysis:
    """情緒失控係數分析"""
    frequency_increase_after_loss: float  # 虧損後下單頻率增加百分比
    leverage_increase_after_loss: float  # 虧損後槓桿增加百分比
    emotional_control_score: float  # 0-100，越高越好
    severity: str  # 'none', 'low', 'medium', 'high', 'critical'
    avg_time_between_trades_normal: float  # 正常情況下的平均交易間隔（分鐘）
    avg_time_between_trades_after_loss: float  # 虧損後的平均交易間隔（分鐘）
    cases_count: int  # 情緒失控案例數量


@dataclass
class SkillDimensionScore:
    """能力維度評分"""
    direction_judgment: float  # 方向研判力 (0-10)
    risk_management: float  # 風險控管力 (0-10)
    psychological_resilience: float  # 心理韌性 (0-10)
    execution_discipline: float  # 執行紀律 (0-10)
    cost_awareness: float  # 成本意識 (0-10)
    overall_score: float  # 總分 (0-10)
    deduction_reasons: Dict[str, List[str]]  # 各維度扣分原因


class QuantitativeRiskOfficer:
    """量化風險官 - 執行嚴格的交易數據審計"""
    
    def __init__(self, trades_data_path: str = 'data/review_history/quality_scores.json'):
        """初始化量化風險官
        
        Args:
            trades_data_path: 交易數據路徑
        """
        self.trades_data_path = trades_data_path
        self.df = None
        self.load_data()
    
    def load_data(self):
        """載入交易數據"""
        try:
            with open(self.trades_data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.df = pd.DataFrame(data)
            
            # 數據清洗和類型轉換
            self.df['pnl'] = pd.to_numeric(self.df['pnl'], errors='coerce')
            self.df['leverage'] = pd.to_numeric(self.df['leverage'], errors='coerce')
            self.df['quantity'] = pd.to_numeric(self.df['quantity'], errors='coerce')
            self.df['fee'] = pd.to_numeric(self.df['fee'], errors='coerce')
            
            # 轉換時間
            self.df['open_time'] = pd.to_datetime(self.df['open_time'], errors='coerce')
            self.df['close_time'] = pd.to_datetime(self.df['close_time'], errors='coerce')
            
            # 計算持倉時間（分鐘）
            self.df['holding_minutes'] = (
                (self.df['close_time'] - self.df['open_time']).dt.total_seconds() / 60
            )
            
            # 判斷盈虧
            self.df['is_win'] = self.df['pnl'] > 0
            self.df['is_loss'] = self.df['pnl'] < 0
            
            print(f"✅ 成功載入 {len(self.df)} 筆交易數據")
            
        except Exception as e:
            print(f"❌ 載入數據失敗：{e}")
            raise

    
    # ==================== 1. 連損與破產風險計算 ====================
    
    def calculate_max_losing_streak(self) -> Dict:
        """計算最長連續虧損次數"""
        if self.df is None or len(self.df) == 0:
            return {'max_streak': 0, 'details': []}
        
        # 按時間排序
        df_sorted = self.df.sort_values('close_time').copy()
        
        # 計算連續虧損
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
        
        # 獲取最長連損的詳細信息
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
        """計算破產風險 (Risk of Ruin)
        
        使用公式：RoR = ((1-W)/W)^(C/A)
        其中：
        - W = 勝率
        - C = 初始資金
        - A = 平均獲利金額
        
        Args:
            initial_capital: 初始資金
        """
        if self.df is None or len(self.df) == 0:
            return {'risk_of_ruin': 0.0, 'explanation': '無數據'}
        
        # 計算勝率
        win_rate = self.df['is_win'].sum() / len(self.df)
        
        # 計算平均獲利和平均虧損
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
        
        # 計算賠率 (Payoff Ratio)
        payoff_ratio = avg_win / avg_loss if avg_loss > 0 else 0
        
        # 計算破產風險
        # 使用簡化的破產風險公式
        if win_rate >= 1.0:
            risk_of_ruin = 0.0
        elif win_rate <= 0.0:
            risk_of_ruin = 1.0
        else:
            # RoR = ((1-W)/W)^(C/(A*W))
            # 其中 A 是平均獲利，W 是勝率
            try:
                if payoff_ratio * win_rate > (1 - win_rate):
                    # 正期望值，破產風險較低
                    risk_of_ruin = ((1 - win_rate) / win_rate) ** (initial_capital / (avg_win * 10))
                else:
                    # 負期望值，破產風險較高
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
        """計算恢復係數：在經歷最大回撤後，需要多少%的獲利才能回到原點"""
        if self.df is None or len(self.df) == 0:
            return {'recovery_factor': 0.0, 'max_drawdown_pct': 0.0}
        
        # 按時間排序並計算累積盈虧
        df_sorted = self.df.sort_values('close_time').copy()
        df_sorted['cumulative_pnl'] = df_sorted['pnl'].cumsum()
        
        # 計算累積最高點
        df_sorted['cumulative_max'] = df_sorted['cumulative_pnl'].cummax()
        
        # 計算回撤
        df_sorted['drawdown'] = df_sorted['cumulative_pnl'] - df_sorted['cumulative_max']
        df_sorted['drawdown_pct'] = (df_sorted['drawdown'] / (1000 + df_sorted['cumulative_max'])) * 100
        
        # 找出最大回撤
        max_drawdown = float(df_sorted['drawdown'].min())
        max_drawdown_pct = float(df_sorted['drawdown_pct'].min())
        
        # 計算恢復係數
        # 如果虧損 X%，需要獲利 X/(1-X) 才能回到原點
        # 例如：虧損 20%，需要獲利 20%/(1-0.2) = 25%
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
    
    # ==================== 2. 手續費壓力測試 ====================
    
    def calculate_fee_pressure(self) -> Dict:
        """計算手續費壓力"""
        if self.df is None or len(self.df) == 0:
            return {}
        
        # 計算總手續費
        total_fee = float(self.df['fee'].sum())
        
        # 計算總虧損（只計算虧損交易）
        total_loss = float(abs(self.df[self.df['is_loss']]['pnl'].sum()))
        
        # 手續費佔總虧損的百分比
        fee_to_loss_ratio = (total_fee / total_loss * 100) if total_loss > 0 else 0.0
        
        # 計算手續費佔總盈虧的百分比
        total_pnl = float(self.df['pnl'].sum())
        fee_to_pnl_ratio = (total_fee / abs(total_pnl) * 100) if total_pnl != 0 else 0.0
        
        return {
            'total_fee': float(total_fee),
            'total_loss': float(total_loss),
            'total_pnl': float(total_pnl),
            'fee_to_loss_ratio': float(fee_to_loss_ratio),
            'fee_to_pnl_ratio': float(fee_to_pnl_ratio),
            'explanation': f'總手續費 {total_fee:.2f} USDT，佔總虧損的 {fee_to_loss_ratio:.2f}%'
        }

    
    def analyze_short_term_trades(self, threshold_minutes: float = 5.0) -> Dict:
        """分析短線交易（持倉時間 < 5分鐘）"""
        if self.df is None or len(self.df) == 0:
            return {}
        
        # 篩選短線交易
        short_trades = self.df[self.df['holding_minutes'] < threshold_minutes].copy()
        
        if len(short_trades) == 0:
            return {
                'count': 0,
                'explanation': f'沒有持倉時間 < {threshold_minutes} 分鐘的交易'
            }
        
        # 計算短線交易的統計數據
        short_total_pnl = float(short_trades['pnl'].sum())
        short_total_fee = float(short_trades['fee'].sum())
        short_win_rate = float(short_trades['is_win'].sum() / len(short_trades))
        short_avg_pnl = float(short_trades['pnl'].mean())
        
        # 計算期望值
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
            'percentage': float(len(short_trades) / len(self.df) * 100),
            'total_pnl': float(short_total_pnl),
            'total_fee': float(short_total_fee),
            'win_rate': float(short_win_rate),
            'avg_pnl': float(short_avg_pnl),
            'expectancy': float(expectancy),
            'explanation': f'{len(short_trades)} 筆短線交易，期望值 {expectancy:.2f} USDT'
        }
    
    def simulate_without_short_trades(self, threshold_minutes: float = 5.0) -> Dict:
        """模擬：如果停止所有短線交易，淨值會有什麼變化"""
        if self.df is None or len(self.df) == 0:
            return {}
        
        # 原始淨值變化
        original_pnl = float(self.df['pnl'].sum())
        original_fee = float(self.df['fee'].sum())
        
        # 排除短線交易後的淨值變化
        long_trades = self.df[self.df['holding_minutes'] >= threshold_minutes].copy()
        
        if len(long_trades) == 0:
            return {
                'explanation': '所有交易都是短線交易，無法模擬'
            }
        
        new_pnl = float(long_trades['pnl'].sum())
        new_fee = float(long_trades['fee'].sum())
        
        # 計算差異
        pnl_difference = new_pnl - original_pnl
        fee_saved = original_fee - new_fee
        
        # 計算勝率變化
        original_win_rate = float(self.df['is_win'].sum() / len(self.df))
        new_win_rate = float(long_trades['is_win'].sum() / len(long_trades))
        
        return {
            'original_pnl': float(original_pnl),
            'new_pnl': float(new_pnl),
            'pnl_difference': float(pnl_difference),
            'pnl_improvement_pct': float((pnl_difference / abs(original_pnl) * 100) if original_pnl != 0 else 0),
            'fee_saved': float(fee_saved),
            'original_win_rate': float(original_win_rate),
            'new_win_rate': float(new_win_rate),
            'trades_eliminated': int(len(self.df) - len(long_trades)),
            'explanation': f'停止短線交易後，淨值變化 {pnl_difference:+.2f} USDT ({(pnl_difference / abs(original_pnl) * 100) if original_pnl != 0 else 0:+.2f}%)'
        }

    
    # ==================== 3. 傾斜 (Tilt) 檢測 ====================
    
    def detect_tilt_behavior(self) -> Dict:
        """檢測傾斜行為：虧損後是否有報復性加倉"""
        if self.df is None or len(self.df) < 2:
            return {'has_tilt': False, 'explanation': '數據不足'}
        
        # 按時間排序
        df_sorted = self.df.sort_values('close_time').copy()
        
        # 分析虧損後的下一筆交易
        tilt_cases = []
        
        for i in range(len(df_sorted) - 1):
            current_trade = df_sorted.iloc[i]
            next_trade = df_sorted.iloc[i + 1]
            
            # 如果當前交易虧損
            if current_trade['is_loss']:
                current_leverage = current_trade['leverage']
                next_leverage = next_trade['leverage']
                
                current_quantity = current_trade['quantity']
                next_quantity = next_trade['quantity']
                
                # 檢查槓桿是否放大
                leverage_increase = (next_leverage - current_leverage) / current_leverage * 100 if current_leverage > 0 else 0
                
                # 檢查倉位是否放大
                quantity_increase = (next_quantity - current_quantity) / current_quantity * 100 if current_quantity > 0 else 0
                
                # 如果槓桿或倉位顯著放大（>20%），記錄為傾斜行為
                if leverage_increase > 20 or quantity_increase > 20:
                    tilt_cases.append({
                        'after_trade_id': current_trade.get('trade_id', 'N/A'),
                        'after_loss': float(current_trade['pnl']),
                        'next_trade_id': next_trade.get('trade_id', 'N/A'),
                        'leverage_increase_pct': float(leverage_increase),
                        'quantity_increase_pct': float(quantity_increase),
                        'next_pnl': float(next_trade['pnl'])
                    })
        
        # 統計分析
        if len(tilt_cases) > 0:
            # 計算傾斜交易的平均結果
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
        
        # 計算虧損後的平均槓桿變化
        df_sorted['prev_is_loss'] = df_sorted['is_loss'].shift(1)
        df_sorted['leverage_change'] = df_sorted['leverage'].diff()
        
        after_loss_leverage_change = df_sorted[df_sorted['prev_is_loss'] == True]['leverage_change'].mean()
        after_win_leverage_change = df_sorted[df_sorted['prev_is_loss'] == False]['leverage_change'].mean()
        
        return {
            'has_tilt': bool(has_tilt),
            'severity': severity,
            'tilt_cases_count': int(len(tilt_cases)),
            'tilt_cases_percentage': float(len(tilt_cases) / (len(df_sorted) - 1) * 100),
            'avg_tilt_pnl': float(avg_tilt_pnl),
            'tilt_win_rate': float(tilt_win_rate),
            'avg_leverage_change_after_loss': float(after_loss_leverage_change) if not pd.isna(after_loss_leverage_change) else 0.0,
            'avg_leverage_change_after_win': float(after_win_leverage_change) if not pd.isna(after_win_leverage_change) else 0.0,
            'tilt_cases': tilt_cases[:5],  # 只返回前5個案例
            'explanation': f'檢測到 {len(tilt_cases)} 次傾斜行為（{len(tilt_cases) / (len(df_sorted) - 1) * 100:.1f}%），嚴重程度：{severity}'
        }

    
    # ==================== 4. 冷靜期檢測（新增）====================
    
    def check_cooling_period(self) -> Dict:
        """檢測是否需要冷靜期
        
        觸發條件：
        - 3次以上連續虧損
        - 單日累積虧損 > 5%
        - 檢測到高度傾斜行為
        
        Returns:
            Dict: 冷靜期建議
        """
        if self.df is None or len(self.df) == 0:
            return {'should_cool': False, 'reason': '無數據'}
        
        # 按時間排序
        df_sorted = self.df.sort_values('close_time').copy()
        
        # 檢查連續虧損
        max_streak_result = self.calculate_max_losing_streak()
        consecutive_losses = max_streak_result['max_streak']
        
        # 檢查單日累積虧損
        df_sorted['date'] = pd.to_datetime(df_sorted['close_time']).dt.date
        daily_pnl = df_sorted.groupby('date')['pnl'].sum()
        
        # 計算初始資金（假設1000 USDT）
        initial_capital = 1000.0
        max_daily_loss_pct = (daily_pnl.min() / initial_capital * 100) if len(daily_pnl) > 0 else 0
        
        # 檢查傾斜行為
        tilt_result = self.detect_tilt_behavior()
        tilt_severity = tilt_result.get('severity', 'none')
        
        # 判斷是否需要冷靜期
        should_cool = False
        reasons = []
        duration_minutes = 0
        severity = 'low'
        
        # 觸發條件 1：連續虧損 >= 3
        if consecutive_losses >= 3:
            should_cool = True
            reasons.append(f'連續虧損 {consecutive_losses} 次')
            duration_minutes += 30  # 基礎30分鐘
            
            if consecutive_losses >= 5:
                duration_minutes += 30  # 超過5次再加30分鐘
                severity = 'high'
            elif consecutive_losses >= 4:
                severity = 'medium'
        
        # 觸發條件 2：單日虧損 > 5%
        if max_daily_loss_pct < -5:
            should_cool = True
            reasons.append(f'單日虧損 {abs(max_daily_loss_pct):.2f}%')
            
            if max_daily_loss_pct < -10:
                duration_minutes += 60  # 超過10%加60分鐘
                severity = 'critical'
            else:
                duration_minutes += 30  # 5-10%加30分鐘
                if severity != 'critical':
                    severity = 'high'
        
        # 觸發條件 3：高度傾斜
        if tilt_severity == 'high':
            should_cool = True
            reasons.append('檢測到高度傾斜行為')
            duration_minutes += 30
            if severity not in ['critical', 'high']:
                severity = 'medium'
        
        # 如果沒有觸發任何條件
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
        
        # 最少30分鐘，最多120分鐘
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
    
    # ==================== 5. Kelly Criterion 破產風險（新增）====================
    
    def calculate_ror_kelly(self) -> Dict:
        """使用 Kelly Criterion 計算破產風險和最優倉位
        
        Kelly 公式：f* = (bp - q) / b
        其中：
        - f* = 最優倉位比例
        - b = 賠率 (平均獲利/平均虧損)
        - p = 勝率
        - q = 敗率 (1 - p)
        
        破產風險：RoR = (q/p)^(C/A)
        其中：
        - C = 當前資金
        - A = 平均獲利金額
        
        Returns:
            Dict: Kelly 分析結果
        """
        if self.df is None or len(self.df) == 0:
            return {'kelly_ror': 1.0, 'explanation': '無數據'}
        
        # 計算勝率
        win_rate = self.df['is_win'].sum() / len(self.df)
        loss_rate = 1 - win_rate
        
        # 計算平均獲利和平均虧損
        winning_trades = self.df[self.df['is_win']]
        losing_trades = self.df[self.df['is_loss']]
        
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
        
        # 計算 Kelly 最優倉位
        # f* = (bp - q) / b = (賠率 * 勝率 - 敗率) / 賠率
        if payoff_ratio > 0:
            kelly_optimal = (payoff_ratio * win_rate - loss_rate) / payoff_ratio
        else:
            kelly_optimal = 0.0
        
        # Kelly 最優倉位應該在 0-1 之間
        kelly_optimal = max(0.0, min(1.0, kelly_optimal))
        
        # 計算破產風險
        # RoR = (q/p)^(C/A)
        initial_capital = 1000.0  # 假設初始資金
        
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
        
        # 計算期望值
        expectancy = win_rate * avg_win - loss_rate * avg_loss
        
        # 建議倉位（Kelly 的一半，更保守）
        recommended_size = kelly_optimal * 0.5
        
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
    
    # ==================== 6. 情緒失控係數分析（新增）====================
    
    def analyze_emotional_control(self) -> Dict:
        """分析虧損後的下單頻率和槓桿變化，檢測情緒失控
        
        Returns:
            Dict: 情緒控制分析結果
        """
        if self.df is None or len(self.df) < 3:
            return {'emotional_control_score': 100.0, 'severity': 'none', 'explanation': '數據不足'}
        
        # 按時間排序
        df_sorted = self.df.sort_values('close_time').copy()
        
        # 計算交易間隔時間（分鐘）
        df_sorted['time_to_next_trade'] = df_sorted['open_time'].diff().shift(-1).dt.total_seconds() / 60
        
        # 分析虧損後的交易間隔
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
                
                # 檢查是否有情緒失控跡象
                # 1. 交易間隔明顯縮短（< 5分鐘）
                # 2. 槓桿增加 > 20%
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
        
        # 計算平均交易間隔
        avg_after_loss = float(np.mean(after_loss_intervals)) if after_loss_intervals else 0.0
        avg_after_win = float(np.mean(after_win_intervals)) if after_win_intervals else 0.0
        avg_normal = float(df_sorted['time_to_next_trade'].mean())
        
        # 計算頻率增加百分比
        if avg_after_loss > 0 and avg_normal > 0:
            frequency_increase = (avg_normal - avg_after_loss) / avg_normal * 100
        else:
            frequency_increase = 0.0
        
        # 計算槓桿增加
        df_sorted['prev_is_loss'] = df_sorted['is_loss'].shift(1)
        df_sorted['leverage_change'] = df_sorted['leverage'].diff()
        
        after_loss_leverage_change = df_sorted[df_sorted['prev_is_loss'] == True]['leverage_change'].mean()
        leverage_increase_pct = float(after_loss_leverage_change / df_sorted['leverage'].mean() * 100) if not pd.isna(after_loss_leverage_change) else 0.0
        
        # 計算情緒控制評分 (0-100)
        score = 100.0
        
        # 扣分項目
        if frequency_increase > 50:  # 虧損後下單頻率增加 > 50%
            score -= 30
        elif frequency_increase > 30:
            score -= 20
        elif frequency_increase > 10:
            score -= 10
        
        if leverage_increase_pct > 30:  # 虧損後槓桿增加 > 30%
            score -= 30
        elif leverage_increase_pct > 20:
            score -= 20
        elif leverage_increase_pct > 10:
            score -= 10
        
        if len(emotional_cases) > len(df_sorted) * 0.3:  # 情緒失控案例 > 30%
            score -= 20
        elif len(emotional_cases) > len(df_sorted) * 0.2:
            score -= 15
        elif len(emotional_cases) > len(df_sorted) * 0.1:
            score -= 10
        
        score = max(0.0, score)
        
        # 判斷嚴重程度
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
            'emotional_cases': emotional_cases[:5],  # 前5個案例
            'explanation': f'情緒控制評分 {score:.1f}/100，嚴重程度：{severity}'
        }
    
    # ==================== 7. 能力維度評分（新增）====================
    
    def calculate_skill_dimensions(self) -> Dict:
        """計算五大能力維度評分
        
        Returns:
            Dict: 能力維度評分結果
        """
        if self.df is None or len(self.df) < 10:
            return {'overall_score': 0.0, 'explanation': '數據不足（需要至少10筆交易）'}
        
        deduction_reasons = {
            'direction_judgment': [],
            'risk_management': [],
            'psychological_resilience': [],
            'execution_discipline': [],
            'cost_awareness': []
        }
        
        # 1. 方向研判力 (Direction Judgment) - 基於勝率
        win_rate = self.df['is_win'].sum() / len(self.df)
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
        else:
            direction_score = 10.0
        
        # 2. 風險控管力 (Risk Management) - 基於最大虧損 vs 平均獲利
        winning_trades = self.df[self.df['is_win']]
        losing_trades = self.df[self.df['is_loss']]
        
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
            else:
                risk_score = 10.0
        
        # 3. 心理韌性 (Psychological Resilience) - 基於報復性交易
        tilt_result = self.detect_tilt_behavior()
        emotional_result = self.analyze_emotional_control()
        
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
        
        # 4. 執行紀律 (Execution Discipline) - 基於交易一致性
        execution_score = 10.0
        
        # 檢查槓桿使用的一致性
        leverage_std = self.df['leverage'].std()
        leverage_mean = self.df['leverage'].mean()
        leverage_cv = leverage_std / leverage_mean if leverage_mean > 0 else 0  # 變異係數
        
        if leverage_cv > 0.5:
            execution_score -= 3
            deduction_reasons['execution_discipline'].append(f'槓桿使用極不一致（變異係數 {leverage_cv:.2f}）')
        elif leverage_cv > 0.3:
            execution_score -= 2
            deduction_reasons['execution_discipline'].append(f'槓桿使用不夠一致（變異係數 {leverage_cv:.2f}）')
        
        # 檢查持倉時間的一致性
        holding_std = self.df['holding_minutes'].std()
        holding_mean = self.df['holding_minutes'].mean()
        holding_cv = holding_std / holding_mean if holding_mean > 0 else 0
        
        if holding_cv > 2.0:
            execution_score -= 3
            deduction_reasons['execution_discipline'].append(f'持倉時間極不一致（變異係數 {holding_cv:.2f}），可能存在隨機下單')
        elif holding_cv > 1.5:
            execution_score -= 2
            deduction_reasons['execution_discipline'].append(f'持倉時間不夠一致（變異係數 {holding_cv:.2f}）')
        
        # 檢查連續虧損後是否停止交易
        max_streak = self.calculate_max_losing_streak()
        if max_streak['max_streak'] > 10:
            execution_score -= 2
            deduction_reasons['execution_discipline'].append(f'連續虧損 {max_streak["max_streak"]} 次仍未停止，缺乏紀律')
        
        execution_score = max(0.0, execution_score)
        
        # 5. 成本意識 (Cost Awareness) - 基於手續費效率
        cost_score = 10.0
        
        # 短線交易分析
        short_trades = self.analyze_short_term_trades(5.0)
        if short_trades.get('count', 0) > 0:
            if short_trades.get('expectancy', 0) < -0.5:
                cost_score -= 4
                deduction_reasons['cost_awareness'].append(f'頻繁短線交易（{short_trades["count"]} 筆），期望值為負（{short_trades["expectancy"]:.2f}）')
            elif short_trades.get('expectancy', 0) < 0:
                cost_score -= 2
                deduction_reasons['cost_awareness'].append(f'短線交易期望值為負（{short_trades["expectancy"]:.2f}）')
        
        # 手續費壓力
        fee_pressure = self.calculate_fee_pressure()
        if fee_pressure.get('fee_to_loss_ratio', 0) > 40:
            cost_score -= 3
            deduction_reasons['cost_awareness'].append(f'手續費佔總虧損 {fee_pressure["fee_to_loss_ratio"]:.1f}%，嚴重侵蝕利潤')
        elif fee_pressure.get('fee_to_loss_ratio', 0) > 30:
            cost_score -= 2
            deduction_reasons['cost_awareness'].append(f'手續費佔總虧損 {fee_pressure["fee_to_loss_ratio"]:.1f}%，成本過高')
        elif fee_pressure.get('fee_to_loss_ratio', 0) > 20:
            cost_score -= 1
        
        # 檢查是否有大量小額交易
        small_trades = self.df[abs(self.df['pnl']) < 1.0]  # 盈虧 < 1 USDT
        if len(small_trades) > len(self.df) * 0.3:
            cost_score -= 2
            deduction_reasons['cost_awareness'].append(f'{len(small_trades)} 筆小額交易（{len(small_trades)/len(self.df)*100:.1f}%），手續費效率低')
        
        cost_score = max(0.0, cost_score)
        
        # 計算總分
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

    
    # ==================== 生成完整報告 ====================
    
    def generate_full_report(self) -> str:
        """生成完整的量化風險分析報告"""
        print("\n" + "="*80)
        print("量化風險分析報告 (Quantitative Risk Analysis Report)")
        print("="*80)
        print(f"分析時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"數據來源：{self.trades_data_path}")
        print(f"總交易數：{len(self.df)}")
        print("="*80)
        
        # 1. 連損與破產風險
        print("\n【1. 連損與破產風險計算】")
        print("-" * 80)
        
        max_streak = self.calculate_max_losing_streak()
        print(f"\n▸ 最長連續虧損次數：{max_streak['max_streak']} 次")
        print(f"▸ 連損期間總虧損：{max_streak['total_loss_in_streak']:.2f} USDT")
        if max_streak['details']:
            print(f"\n連損詳情（前3筆）：")
            for i, trade in enumerate(max_streak['details'][:3], 1):
                print(f"  {i}. {trade['symbol']} | 虧損：{trade['pnl']:.2f} USDT | 時間：{trade['close_time']}")
        
        ror = self.calculate_risk_of_ruin()
        print(f"\n▸ 破產風險 (Risk of Ruin)：{ror['risk_of_ruin']:.2%}")
        print(f"▸ 勝率：{ror['win_rate']:.2%}")
        print(f"▸ 平均獲利：{ror['avg_win']:.2f} USDT")
        print(f"▸ 平均虧損：{ror['avg_loss']:.2f} USDT")
        print(f"▸ 賠率 (Payoff Ratio)：{ror['payoff_ratio']:.2f}:1")
        print(f"▸ 期望值 (Expectancy)：{ror['expectancy']:.2f} USDT")
        print(f"▸ 說明：{ror['explanation']}")
        
        recovery = self.calculate_recovery_factor()
        print(f"\n▸ 最大回撤：{recovery['max_drawdown']:.2f} USDT ({recovery['max_drawdown_pct']:.2f}%)")
        print(f"▸ 恢復係數：需要獲利 {recovery['recovery_needed_pct']:.2f}% 才能回到原點")
        print(f"▸ 說明：{recovery['explanation']}")
        
        # 2. 手續費壓力測試
        print("\n【2. 手續費壓力測試】")
        print("-" * 80)
        
        fee_pressure = self.calculate_fee_pressure()
        print(f"\n▸ 總手續費：{fee_pressure['total_fee']:.2f} USDT")
        print(f"▸ 總虧損：{fee_pressure['total_loss']:.2f} USDT")
        print(f"▸ 總盈虧：{fee_pressure['total_pnl']:.2f} USDT")
        print(f"▸ 手續費佔總虧損：{fee_pressure['fee_to_loss_ratio']:.2f}%")
        print(f"▸ 手續費佔總盈虧：{fee_pressure['fee_to_pnl_ratio']:.2f}%")
        
        short_trades = self.analyze_short_term_trades(5.0)
        if short_trades.get('count', 0) > 0:
            print(f"\n▸ 短線交易（<5分鐘）數量：{short_trades['count']} 筆 ({short_trades['percentage']:.1f}%)")
            print(f"▸ 短線交易總盈虧：{short_trades['total_pnl']:.2f} USDT")
            print(f"▸ 短線交易總手續費：{short_trades['total_fee']:.2f} USDT")
            print(f"▸ 短線交易勝率：{short_trades['win_rate']:.2%}")
            print(f"▸ 短線交易平均盈虧：{short_trades['avg_pnl']:.2f} USDT")
            print(f"▸ 短線交易期望值：{short_trades['expectancy']:.2f} USDT")
        
        simulation = self.simulate_without_short_trades(5.0)
        if 'pnl_difference' in simulation:
            print(f"\n▸ 【模擬】停止所有5分鐘內的短線交易：")
            print(f"  - 原始淨值：{simulation['original_pnl']:.2f} USDT")
            print(f"  - 新淨值：{simulation['new_pnl']:.2f} USDT")
            print(f"  - 淨值變化：{simulation['pnl_difference']:+.2f} USDT ({simulation['pnl_improvement_pct']:+.2f}%)")
            print(f"  - 節省手續費：{simulation['fee_saved']:.2f} USDT")
            print(f"  - 原始勝率：{simulation['original_win_rate']:.2%}")
            print(f"  - 新勝率：{simulation['new_win_rate']:.2%}")
            print(f"  - 減少交易數：{simulation['trades_eliminated']} 筆")
        
        # 3. 傾斜檢測
        print("\n【3. 傾斜 (Tilt) 檢測】")
        print("-" * 80)
        
        tilt = self.detect_tilt_behavior()
        print(f"\n▸ 是否檢測到傾斜行為：{'是' if tilt['has_tilt'] else '否'}")
        print(f"▸ 嚴重程度：{tilt['severity']}")
        print(f"▸ 傾斜案例數量：{tilt['tilt_cases_count']} 次 ({tilt['tilt_cases_percentage']:.1f}%)")
        
        if tilt['has_tilt']:
            print(f"▸ 傾斜交易平均盈虧：{tilt['avg_tilt_pnl']:.2f} USDT")
            print(f"▸ 傾斜交易勝率：{tilt['tilt_win_rate']:.2%}")
            print(f"▸ 虧損後平均槓桿變化：{tilt['avg_leverage_change_after_loss']:+.2f}x")
            print(f"▸ 獲利後平均槓桿變化：{tilt['avg_leverage_change_after_win']:+.2f}x")
            
            if tilt['tilt_cases']:
                print(f"\n傾斜案例（前3個）：")
                for i, case in enumerate(tilt['tilt_cases'][:3], 1):
                    print(f"  {i}. 虧損 {case['after_loss']:.2f} USDT 後")
                    print(f"     → 槓桿增加 {case['leverage_increase_pct']:+.1f}%")
                    print(f"     → 倉位增加 {case['quantity_increase_pct']:+.1f}%")
                    print(f"     → 結果：{case['next_pnl']:+.2f} USDT")
        
        # 4. 冷靜期檢測（新增）
        print("\n【4. 冷靜期檢測】")
        print("-" * 80)
        
        cooling = self.check_cooling_period()
        print(f"\n▸ 是否需要冷靜期：{'是' if cooling['should_cool'] else '否'}")
        
        if cooling['should_cool']:
            print(f"▸ 嚴重程度：{cooling['severity']}")
            print(f"▸ 建議休息時間：{cooling['duration_minutes']} 分鐘")
            print(f"▸ 觸發原因：{cooling['reason']}")
            print(f"▸ 連續虧損：{cooling['consecutive_losses']} 次")
            if cooling['max_daily_loss_pct'] < 0:
                print(f"▸ 最大單日虧損：{abs(cooling['max_daily_loss_pct']):.2f}%")
            print(f"\n💡 {cooling['recommendation']}")
        else:
            print(f"▸ 狀態：{cooling['reason']}")
            print(f"▸ 連續虧損：{cooling['consecutive_losses']} 次")
        
        # 5. Kelly Criterion 分析（新增）
        print("\n【5. Kelly Criterion 破產風險分析】")
        print("-" * 80)
        
        kelly = self.calculate_ror_kelly()
        print(f"\n▸ Kelly 破產風險：{kelly['kelly_ror']:.2%}")
        print(f"▸ Kelly 最優倉位：{kelly['kelly_optimal_size']:.2%}")
        print(f"▸ 建議倉位（Half Kelly）：{kelly['recommended_size']:.2%}")
        print(f"▸ 勝率：{kelly['win_rate']:.2%}")
        print(f"▸ 賠率：{kelly['payoff_ratio']:.2f}:1")
        print(f"▸ 期望值：{kelly['expectancy']:.2f} USDT")
        print(f"▸ 說明：{kelly['explanation']}")
        
        if kelly['kelly_optimal_size'] <= 0:
            print(f"\n⚠️ 警告：Kelly 最優倉位 ≤ 0，表示當前策略期望值為負，不建議交易！")
        elif kelly['kelly_optimal_size'] < 0.1:
            print(f"\n💡 建議：Kelly 最優倉位很小（{kelly['kelly_optimal_size']:.2%}），建議降低風險或改善策略")
        
        # 6. 情緒失控係數分析（新增）
        print("\n【6. 情緒失控係數分析】")
        print("-" * 80)
        
        emotional = self.analyze_emotional_control()
        print(f"\n▸ 情緒控制評分：{emotional['emotional_control_score']:.1f}/100")
        print(f"▸ 嚴重程度：{emotional['severity']}")
        print(f"▸ 虧損後下單頻率增加：{emotional['frequency_increase_after_loss']:+.1f}%")
        print(f"▸ 虧損後槓桿增加：{emotional['leverage_increase_after_loss']:+.1f}%")
        print(f"▸ 正常交易間隔：{emotional['avg_time_between_trades_normal']:.1f} 分鐘")
        print(f"▸ 虧損後交易間隔：{emotional['avg_time_between_trades_after_loss']:.1f} 分鐘")
        print(f"▸ 獲利後交易間隔：{emotional['avg_time_between_trades_after_win']:.1f} 分鐘")
        print(f"▸ 情緒失控案例：{emotional['cases_count']} 次 ({emotional['cases_percentage']:.1f}%)")
        
        if emotional['severity'] in ['critical', 'high']:
            print(f"\n⚠️ 警告：檢測到明顯的情緒失控跡象！")
            print("  - 虧損後下單頻率明顯增加")
            print("  - 虧損後槓桿明顯增加")
            print("  - 建議：設置冷靜期，虧損後強制休息 30-60 分鐘")
        elif emotional['severity'] == 'medium':
            print(f"\n💡 建議：情緒控制有待改善，注意虧損後的交易行為")
        else:
            print(f"\n✅ 情緒控制良好，保持冷靜交易")
        
        # 7. 能力維度評分（新增）
        print("\n【7. 能力維度評分】")
        print("-" * 80)
        
        skills = self.calculate_skill_dimensions()
        print(f"\n▸ 綜合能力評分：{skills['overall_score']:.1f}/10")
        print(f"\n各維度評分：")
        print(f"  1. 方向研判力：{skills['direction_judgment']:.1f}/10")
        if skills['deduction_reasons']['direction_judgment']:
            for reason in skills['deduction_reasons']['direction_judgment']:
                print(f"     ❌ {reason}")
        else:
            print(f"     ✅ 勝率達標")
        
        print(f"\n  2. 風險控管力：{skills['risk_management']:.1f}/10")
        if skills['deduction_reasons']['risk_management']:
            for reason in skills['deduction_reasons']['risk_management']:
                print(f"     ❌ {reason}")
        else:
            print(f"     ✅ 風險控制良好")
        
        print(f"\n  3. 心理韌性：{skills['psychological_resilience']:.1f}/10")
        if skills['deduction_reasons']['psychological_resilience']:
            for reason in skills['deduction_reasons']['psychological_resilience']:
                print(f"     ❌ {reason}")
        else:
            print(f"     ✅ 心理素質良好")
        
        print(f"\n  4. 執行紀律：{skills['execution_discipline']:.1f}/10")
        if skills['deduction_reasons']['execution_discipline']:
            for reason in skills['deduction_reasons']['execution_discipline']:
                print(f"     ❌ {reason}")
        else:
            print(f"     ✅ 執行紀律良好")
        
        print(f"\n  5. 成本意識：{skills['cost_awareness']:.1f}/10")
        if skills['deduction_reasons']['cost_awareness']:
            for reason in skills['deduction_reasons']['cost_awareness']:
                print(f"     ❌ {reason}")
        else:
            print(f"     ✅ 成本控制良好")
        
        # 總體建議
        print(f"\n💡 總體建議：")
        if skills['overall_score'] < 5:
            print("  ⚠️ 綜合能力評分較低，建議暫停實盤交易，回到模擬盤練習")
        elif skills['overall_score'] < 7:
            print("  💡 綜合能力有待提升，重點改善評分最低的維度")
        else:
            print("  ✅ 綜合能力良好，繼續保持並精進")
        
        print("\n" + "="*80)
        print("報告結束")
        print("="*80 + "\n")
        
        return "報告生成完成"


# 主程序
if __name__ == "__main__":
    print("🔍 啟動量化風險分析...")
    
    try:
        # 創建量化風險官實例
        risk_officer = QuantitativeRiskOfficer()
        
        # 生成完整報告
        risk_officer.generate_full_report()
        
    except Exception as e:
        print(f"\n❌ 分析過程中發生錯誤：{e}")
        import traceback
        traceback.print_exc()
