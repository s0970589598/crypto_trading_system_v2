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
import warnings
warnings.filterwarnings('ignore')


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
