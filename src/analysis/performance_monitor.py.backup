"""
性能監控器
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from collections import deque
import statistics

from src.models.trading import Trade
from src.models.backtest import BacktestResult


@dataclass
class PerformanceMetrics:
    """績效指標"""
    strategy_id: str
    timestamp: datetime
    
    # 基本指標
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    
    # 損益指標
    total_pnl: float = 0.0
    total_pnl_pct: float = 0.0
    current_capital: float = 0.0
    initial_capital: float = 0.0
    
    # 風險指標
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    sharpe_ratio: float = 0.0
    
    # 近期表現
    recent_win_rate: float = 0.0  # 最近 N 筆交易的勝率
    recent_pnl: float = 0.0  # 最近 N 筆交易的損益
    consecutive_losses: int = 0  # 連續虧損次數
    
    def calculate_return_rate(self) -> float:
        """計算實時收益率
        
        Returns:
            float: 收益率百分比
        """
        if self.initial_capital <= 0:
            return 0.0
        return ((self.current_capital - self.initial_capital) / self.initial_capital) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            'strategy_id': self.strategy_id,
            'timestamp': self.timestamp.isoformat(),
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': self.win_rate,
            'total_pnl': self.total_pnl,
            'total_pnl_pct': self.total_pnl_pct,
            'current_capital': self.current_capital,
            'initial_capital': self.initial_capital,
            'max_drawdown': self.max_drawdown,
            'max_drawdown_pct': self.max_drawdown_pct,
            'sharpe_ratio': self.sharpe_ratio,
            'recent_win_rate': self.recent_win_rate,
            'recent_pnl': self.recent_pnl,
            'consecutive_losses': self.consecutive_losses,
        }


@dataclass
class AlertConfig:
    """警報配置"""
    # 異常檢測閾值
    win_rate_drop_threshold: float = 20.0  # 勝率下降超過 20%
    drawdown_threshold: float = 15.0  # 回撤超過 15%
    consecutive_loss_threshold: int = 5  # 連續虧損 5 次
    
    # 退化檢測閾值
    degradation_window: int = 20  # 檢測最近 20 筆交易
    degradation_threshold: float = 15.0  # 勝率下降超過 15%
    
    # 自動暫停閾值
    auto_halt_consecutive_losses: int = 5  # 連續虧損 5 次自動暫停
    auto_halt_drawdown: float = 20.0  # 回撤超過 20% 自動暫停


class PerformanceMonitor:
    """性能監控器
    
    實時追蹤策略性能，檢測異常和退化，發送警報。
    """
    
    def __init__(
        self,
        alert_config: Optional[AlertConfig] = None,
        telegram_notifier: Optional[Any] = None
    ):
        """初始化性能監控器
        
        Args:
            alert_config: 警報配置（可選）
            telegram_notifier: Telegram 通知器（可選）
        """
        self.alert_config = alert_config or AlertConfig()
        self.telegram_notifier = telegram_notifier
        
        # 指標歷史記錄：strategy_id -> List[PerformanceMetrics]
        self.metrics_history: Dict[str, List[PerformanceMetrics]] = {}
        
        # 交易歷史記錄：strategy_id -> deque[Trade]
        self.trade_history: Dict[str, deque] = {}
        
        # 回測基準：strategy_id -> BacktestResult
        self.backtest_baseline: Dict[str, BacktestResult] = {}
        
        # 資金曲線：strategy_id -> List[Tuple[datetime, float]]
        self.equity_curves: Dict[str, List[Tuple[datetime, float]]] = {}
        
        # 初始資金：strategy_id -> float
        self.initial_capitals: Dict[str, float] = {}
        
        # 策略狀態：strategy_id -> bool (是否已暫停)
        self.strategy_halted: Dict[str, bool] = {}
    
    def set_backtest_baseline(self, strategy_id: str, backtest_result: BacktestResult) -> None:
        """設置回測基準
        
        Args:
            strategy_id: 策略 ID
            backtest_result: 回測結果
        """
        self.backtest_baseline[strategy_id] = backtest_result
    
    def set_initial_capital(self, strategy_id: str, capital: float) -> None:
        """設置初始資金
        
        Args:
            strategy_id: 策略 ID
            capital: 初始資金
        """
        self.initial_capitals[strategy_id] = capital
        
        # 初始化資金曲線
        if strategy_id not in self.equity_curves:
            self.equity_curves[strategy_id] = [(datetime.now(), capital)]
    
    def update_metrics(self, strategy_id: str, trade: Trade) -> PerformanceMetrics:
        """更新策略指標
        
        Args:
            strategy_id: 策略 ID
            trade: 新的交易記錄
            
        Returns:
            PerformanceMetrics: 更新後的績效指標
        """
        # 初始化交易歷史
        if strategy_id not in self.trade_history:
            self.trade_history[strategy_id] = deque(maxlen=100)  # 保留最近 100 筆交易
        
        # 添加交易到歷史
        self.trade_history[strategy_id].append(trade)
        
        # 獲取所有交易
        all_trades = list(self.trade_history[strategy_id])
        
        # 計算基本指標
        total_trades = len(all_trades)
        winning_trades = sum(1 for t in all_trades if t.is_winning())
        losing_trades = total_trades - winning_trades
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0
        
        # 計算損益
        total_pnl = sum(t.pnl for t in all_trades)
        initial_capital = self.initial_capitals.get(strategy_id, 1000.0)
        current_capital = initial_capital + total_pnl
        total_pnl_pct = ((current_capital / initial_capital) - 1) * 100
        
        # 更新資金曲線
        if strategy_id not in self.equity_curves:
            self.equity_curves[strategy_id] = [(datetime.now(), initial_capital)]
        self.equity_curves[strategy_id].append((trade.exit_time, current_capital))
        
        # 計算回撤
        max_drawdown, max_drawdown_pct = self._calculate_drawdown(strategy_id)
        
        # 計算夏普比率
        sharpe_ratio = self._calculate_sharpe_ratio(all_trades)
        
        # 計算近期表現（最近 20 筆交易）
        recent_trades = all_trades[-20:] if len(all_trades) >= 20 else all_trades
        recent_winning = sum(1 for t in recent_trades if t.is_winning())
        recent_win_rate = (recent_winning / len(recent_trades) * 100) if recent_trades else 0.0
        recent_pnl = sum(t.pnl for t in recent_trades)
        
        # 計算連續虧損
        consecutive_losses = 0
        for t in reversed(all_trades):
            if not t.is_winning():
                consecutive_losses += 1
            else:
                break
        
        # 創建績效指標
        metrics = PerformanceMetrics(
            strategy_id=strategy_id,
            timestamp=datetime.now(),
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            total_pnl=total_pnl,
            total_pnl_pct=total_pnl_pct,
            current_capital=current_capital,
            initial_capital=initial_capital,
            max_drawdown=max_drawdown,
            max_drawdown_pct=max_drawdown_pct,
            sharpe_ratio=sharpe_ratio,
            recent_win_rate=recent_win_rate,
            recent_pnl=recent_pnl,
            consecutive_losses=consecutive_losses,
        )
        
        # 保存到歷史
        if strategy_id not in self.metrics_history:
            self.metrics_history[strategy_id] = []
        self.metrics_history[strategy_id].append(metrics)
        
        return metrics
    
    def _calculate_drawdown(self, strategy_id: str) -> Tuple[float, float]:
        """計算最大回撤
        
        Args:
            strategy_id: 策略 ID
            
        Returns:
            Tuple[float, float]: (最大回撤 USDT, 最大回撤百分比)
        """
        equity_curve = self.equity_curves.get(strategy_id, [])
        if len(equity_curve) < 2:
            return 0.0, 0.0
        
        # 提取資金值
        equity_values = [capital for _, capital in equity_curve]
        
        # 計算累計最高點
        max_drawdown = 0.0
        max_drawdown_pct = 0.0
        peak = equity_values[0]
        
        for capital in equity_values:
            if capital > peak:
                peak = capital
            
            drawdown = peak - capital
            drawdown_pct = (drawdown / peak * 100) if peak > 0 else 0.0
            
            if drawdown > max_drawdown:
                max_drawdown = drawdown
                max_drawdown_pct = drawdown_pct
        
        return max_drawdown, max_drawdown_pct
    
    def _calculate_sharpe_ratio(self, trades: List[Trade]) -> float:
        """計算夏普比率
        
        Args:
            trades: 交易列表
            
        Returns:
            float: 夏普比率
        """
        if len(trades) < 2:
            return 0.0
        
        # 計算每筆交易的收益率
        returns = [t.pnl_pct for t in trades]
        
        # 計算平均收益率和標準差
        mean_return = statistics.mean(returns)
        
        try:
            std_return = statistics.stdev(returns)
        except statistics.StatisticsError:
            return 0.0
        
        # 夏普比率（假設無風險利率為 0）
        sharpe_ratio = (mean_return / std_return) if std_return > 0 else 0.0
        
        return sharpe_ratio
    
    def get_latest_metrics(self, strategy_id: str) -> Optional[PerformanceMetrics]:
        """獲取最新指標
        
        Args:
            strategy_id: 策略 ID
            
        Returns:
            Optional[PerformanceMetrics]: 最新指標，如果不存在則返回 None
        """
        history = self.metrics_history.get(strategy_id, [])
        return history[-1] if history else None
    
    def get_metrics_history(
        self,
        strategy_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[PerformanceMetrics]:
        """獲取指標歷史
        
        Args:
            strategy_id: 策略 ID
            start_time: 開始時間（可選）
            end_time: 結束時間（可選）
            
        Returns:
            List[PerformanceMetrics]: 指標歷史列表
        """
        history = self.metrics_history.get(strategy_id, [])
        
        if not start_time and not end_time:
            return history
        
        filtered = []
        for metrics in history:
            if start_time and metrics.timestamp < start_time:
                continue
            if end_time and metrics.timestamp > end_time:
                continue
            filtered.append(metrics)
        
        return filtered
    
    def check_anomaly(self, strategy_id: str) -> Tuple[bool, str]:
        """檢測策略異常
        
        檢測策略表現是否異常，包括：
        1. 勝率大幅下降
        2. 回撤超過閾值
        3. 連續虧損超過閾值
        4. 實際表現與回測表現差異過大
        
        Args:
            strategy_id: 策略 ID
            
        Returns:
            Tuple[bool, str]: (是否異常, 異常描述)
        """
        # 獲取最新指標
        latest_metrics = self.get_latest_metrics(strategy_id)
        if not latest_metrics:
            return False, "無指標數據"
        
        anomalies = []
        
        # 檢查 1: 勝率大幅下降
        if strategy_id in self.backtest_baseline:
            baseline = self.backtest_baseline[strategy_id]
            win_rate_drop = baseline.win_rate - latest_metrics.win_rate
            
            if win_rate_drop > self.alert_config.win_rate_drop_threshold:
                anomalies.append(
                    f"勝率下降 {win_rate_drop:.1f}% "
                    f"(回測: {baseline.win_rate:.1f}%, 實際: {latest_metrics.win_rate:.1f}%)"
                )
        
        # 檢查 2: 回撤超過閾值
        if latest_metrics.max_drawdown_pct > self.alert_config.drawdown_threshold:
            anomalies.append(
                f"回撤超過閾值 {latest_metrics.max_drawdown_pct:.1f}% "
                f"(閾值: {self.alert_config.drawdown_threshold:.1f}%)"
            )
        
        # 檢查 3: 連續虧損超過閾值
        if latest_metrics.consecutive_losses >= self.alert_config.consecutive_loss_threshold:
            anomalies.append(
                f"連續虧損 {latest_metrics.consecutive_losses} 次 "
                f"(閾值: {self.alert_config.consecutive_loss_threshold})"
            )
        
        # 檢查 4: 近期勝率與整體勝率差異過大
        if latest_metrics.total_trades >= 20:
            win_rate_diff = latest_metrics.win_rate - latest_metrics.recent_win_rate
            if win_rate_diff > self.alert_config.win_rate_drop_threshold:
                anomalies.append(
                    f"近期勝率下降 {win_rate_diff:.1f}% "
                    f"(整體: {latest_metrics.win_rate:.1f}%, 近期: {latest_metrics.recent_win_rate:.1f}%)"
                )
        
        if anomalies:
            return True, "; ".join(anomalies)
        
        return False, "正常"
    
    def compare_with_backtest(self, strategy_id: str) -> Dict[str, Any]:
        """比較實際表現與回測表現
        
        Args:
            strategy_id: 策略 ID
            
        Returns:
            Dict[str, Any]: 比較結果
        """
        latest_metrics = self.get_latest_metrics(strategy_id)
        baseline = self.backtest_baseline.get(strategy_id)
        
        if not latest_metrics or not baseline:
            return {
                'available': False,
                'reason': '缺少指標或回測基準'
            }
        
        # 計算差異
        win_rate_diff = latest_metrics.win_rate - baseline.win_rate
        pnl_pct_diff = latest_metrics.total_pnl_pct - baseline.total_pnl_pct
        drawdown_diff = latest_metrics.max_drawdown_pct - baseline.max_drawdown_pct
        sharpe_diff = latest_metrics.sharpe_ratio - baseline.sharpe_ratio
        
        return {
            'available': True,
            'backtest': {
                'win_rate': baseline.win_rate,
                'total_pnl_pct': baseline.total_pnl_pct,
                'max_drawdown_pct': baseline.max_drawdown_pct,
                'sharpe_ratio': baseline.sharpe_ratio,
            },
            'actual': {
                'win_rate': latest_metrics.win_rate,
                'total_pnl_pct': latest_metrics.total_pnl_pct,
                'max_drawdown_pct': latest_metrics.max_drawdown_pct,
                'sharpe_ratio': latest_metrics.sharpe_ratio,
            },
            'difference': {
                'win_rate': win_rate_diff,
                'total_pnl_pct': pnl_pct_diff,
                'max_drawdown_pct': drawdown_diff,
                'sharpe_ratio': sharpe_diff,
            },
            'performance_grade': self._grade_performance(
                win_rate_diff, pnl_pct_diff, drawdown_diff
            )
        }

    
    def _grade_performance(
        self,
        win_rate_diff: float,
        pnl_diff: float,
        drawdown_diff: float
    ) -> str:
        """評估性能等級
        
        Args:
            win_rate_diff: 勝率差異
            pnl_diff: 收益率差異
            drawdown_diff: 回撤差異
            
        Returns:
            str: 性能等級 (優秀/良好/一般/差)
        """
        # 計算綜合得分
        score = 0
        
        # 勝率評分
        if win_rate_diff >= 0:
            score += 2
        elif win_rate_diff >= -5:
            score += 1
        elif win_rate_diff >= -10:
            score += 0
        else:
            score -= 1
        
        # 收益率評分
        if pnl_diff >= 0:
            score += 2
        elif pnl_diff >= -5:
            score += 1
        elif pnl_diff >= -10:
            score += 0
        else:
            score -= 1
        
        # 回撤評分（回撤越小越好）
        if drawdown_diff <= 0:
            score += 2
        elif drawdown_diff <= 5:
            score += 1
        elif drawdown_diff <= 10:
            score += 0
        else:
            score -= 1
        
        # 根據得分返回等級
        if score >= 5:
            return "優秀"
        elif score >= 3:
            return "良好"
        elif score >= 0:
            return "一般"
        else:
            return "差"

    
    def detect_degradation(self, strategy_id: str) -> Tuple[bool, float]:
        """檢測策略退化
        
        檢測策略性能是否出現退化，通過比較：
        1. 最近 N 筆交易的勝率與歷史平均勝率
        2. 最近 N 筆交易的平均收益與歷史平均收益
        3. 趨勢分析（性能是否持續下降）
        
        Args:
            strategy_id: 策略 ID
            
        Returns:
            Tuple[bool, float]: (是否退化, 退化程度 0-100)
        """
        trades = list(self.trade_history.get(strategy_id, []))
        
        if len(trades) < self.alert_config.degradation_window:
            return False, 0.0
        
        # 獲取最近 N 筆交易
        window_size = self.alert_config.degradation_window
        recent_trades = trades[-window_size:]
        historical_trades = trades[:-window_size] if len(trades) > window_size else trades
        
        # 計算最近勝率
        recent_wins = sum(1 for t in recent_trades if t.is_winning())
        recent_win_rate = (recent_wins / len(recent_trades) * 100) if recent_trades else 0.0
        
        # 計算歷史勝率
        if historical_trades:
            historical_wins = sum(1 for t in historical_trades if t.is_winning())
            historical_win_rate = (historical_wins / len(historical_trades) * 100)
        else:
            # 如果沒有歷史數據，使用回測基準
            baseline = self.backtest_baseline.get(strategy_id)
            historical_win_rate = baseline.win_rate if baseline else 50.0
        
        # 計算勝率下降
        win_rate_drop = historical_win_rate - recent_win_rate
        
        # 計算最近平均收益
        recent_avg_pnl = statistics.mean([t.pnl for t in recent_trades]) if recent_trades else 0.0
        
        # 計算歷史平均收益
        if historical_trades:
            historical_avg_pnl = statistics.mean([t.pnl for t in historical_trades])
        else:
            baseline = self.backtest_baseline.get(strategy_id)
            if baseline and baseline.total_trades > 0:
                historical_avg_pnl = baseline.total_pnl / baseline.total_trades
            else:
                historical_avg_pnl = 0.0
        
        # 計算收益下降百分比
        if historical_avg_pnl != 0:
            pnl_drop_pct = ((historical_avg_pnl - recent_avg_pnl) / abs(historical_avg_pnl)) * 100
        else:
            pnl_drop_pct = 0.0
        
        # 計算退化程度（0-100）
        degradation_score = 0.0
        
        # 勝率退化貢獻（最多 50 分）
        if win_rate_drop > 0:
            degradation_score += min(win_rate_drop, 50.0)
        
        # 收益退化貢獻（最多 50 分）
        if pnl_drop_pct > 0:
            degradation_score += min(pnl_drop_pct / 2, 50.0)
        
        # 判斷是否退化
        is_degraded = win_rate_drop > self.alert_config.degradation_threshold
        
        return is_degraded, min(degradation_score, 100.0)
    
    def should_auto_halt(self, strategy_id: str) -> Tuple[bool, str]:
        """判斷是否應該自動暫停策略
        
        根據以下條件判斷：
        1. 連續虧損超過閾值
        2. 回撤超過閾值
        3. 檢測到嚴重退化
        
        Args:
            strategy_id: 策略 ID
            
        Returns:
            Tuple[bool, str]: (是否應該暫停, 原因)
        """
        # 檢查是否已經暫停
        if self.strategy_halted.get(strategy_id, False):
            return True, "策略已暫停"
        
        latest_metrics = self.get_latest_metrics(strategy_id)
        if not latest_metrics:
            return False, "無指標數據"
        
        reasons = []
        
        # 檢查 1: 連續虧損
        if latest_metrics.consecutive_losses >= self.alert_config.auto_halt_consecutive_losses:
            reasons.append(
                f"連續虧損 {latest_metrics.consecutive_losses} 次 "
                f"(閾值: {self.alert_config.auto_halt_consecutive_losses})"
            )
        
        # 檢查 2: 回撤過大
        if latest_metrics.max_drawdown_pct >= self.alert_config.auto_halt_drawdown:
            reasons.append(
                f"回撤 {latest_metrics.max_drawdown_pct:.1f}% "
                f"(閾值: {self.alert_config.auto_halt_drawdown:.1f}%)"
            )
        
        # 檢查 3: 嚴重退化
        is_degraded, degradation_score = self.detect_degradation(strategy_id)
        if is_degraded and degradation_score >= 50.0:
            reasons.append(
                f"策略嚴重退化 (退化程度: {degradation_score:.1f})"
            )
        
        if reasons:
            # 標記為已暫停
            self.strategy_halted[strategy_id] = True
            return True, "; ".join(reasons)
        
        return False, "正常"
    
    def resume_strategy(self, strategy_id: str) -> None:
        """恢復策略運行
        
        Args:
            strategy_id: 策略 ID
        """
        self.strategy_halted[strategy_id] = False

    
    def send_alert(
        self,
        strategy_id: str,
        alert_type: str,
        message: str,
        level: str = "WARNING"
    ) -> None:
        """發送警報
        
        支持不同級別的警報：
        - INFO: 信息性警報
        - WARNING: 警告性警報
        - CRITICAL: 嚴重警報
        
        Args:
            strategy_id: 策略 ID
            alert_type: 警報類型（anomaly/degradation/auto_halt）
            message: 警報訊息
            level: 警報級別（INFO/WARNING/CRITICAL）
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 格式化警報訊息
        alert_message = (
            f"[{level}] 策略警報\n"
            f"時間: {timestamp}\n"
            f"策略: {strategy_id}\n"
            f"類型: {alert_type}\n"
            f"訊息: {message}"
        )
        
        # 打印到控制台
        print("=" * 80)
        print(alert_message)
        print("=" * 80)
        
        # 發送 Telegram 通知
        if self.telegram_notifier:
            try:
                self.telegram_notifier.send_message(alert_message)
            except Exception as e:
                print(f"Telegram 通知發送失敗: {e}")
    
    def monitor_strategy(self, strategy_id: str, trade: Trade) -> Dict[str, Any]:
        """監控策略並發送必要的警報
        
        這是一個便捷方法，會：
        1. 更新指標
        2. 檢測異常
        3. 檢測退化
        4. 檢查是否需要自動暫停
        5. 發送相應的警報
        
        Args:
            strategy_id: 策略 ID
            trade: 新的交易記錄
            
        Returns:
            Dict[str, Any]: 監控結果
        """
        # 更新指標
        metrics = self.update_metrics(strategy_id, trade)
        
        result = {
            'strategy_id': strategy_id,
            'metrics': metrics.to_dict(),
            'alerts': []
        }
        
        # 檢測異常
        is_anomaly, anomaly_msg = self.check_anomaly(strategy_id)
        if is_anomaly:
            self.send_alert(strategy_id, "anomaly", anomaly_msg, "WARNING")
            result['alerts'].append({
                'type': 'anomaly',
                'level': 'WARNING',
                'message': anomaly_msg
            })
        
        # 檢測退化
        is_degraded, degradation_score = self.detect_degradation(strategy_id)
        if is_degraded:
            degradation_msg = f"策略性能退化，退化程度: {degradation_score:.1f}"
            self.send_alert(strategy_id, "degradation", degradation_msg, "WARNING")
            result['alerts'].append({
                'type': 'degradation',
                'level': 'WARNING',
                'message': degradation_msg,
                'score': degradation_score
            })
        
        # 檢查是否需要自動暫停
        should_halt, halt_reason = self.should_auto_halt(strategy_id)
        if should_halt and not self.strategy_halted.get(strategy_id, False):
            # 只在首次暫停時發送警報
            halt_msg = f"策略已自動暫停: {halt_reason}"
            self.send_alert(strategy_id, "auto_halt", halt_msg, "CRITICAL")
            result['alerts'].append({
                'type': 'auto_halt',
                'level': 'CRITICAL',
                'message': halt_msg
            })
            result['halted'] = True
        else:
            result['halted'] = self.strategy_halted.get(strategy_id, False)
        
        return result
    
    def generate_performance_report(self, strategy_id: str) -> str:
        """生成性能報告
        
        Args:
            strategy_id: 策略 ID
            
        Returns:
            str: 性能報告文本
        """
        latest_metrics = self.get_latest_metrics(strategy_id)
        if not latest_metrics:
            return f"策略 {strategy_id} 無性能數據"
        
        # 檢測狀態
        is_anomaly, anomaly_msg = self.check_anomaly(strategy_id)
        is_degraded, degradation_score = self.detect_degradation(strategy_id)
        should_halt, halt_reason = self.should_auto_halt(strategy_id)
        
        # 與回測比較
        comparison = self.compare_with_backtest(strategy_id)
        
        report = []
        report.append("=" * 80)
        report.append(f"性能報告 - {strategy_id}")
        report.append("=" * 80)
        report.append(f"\n時間: {latest_metrics.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        
        report.append(f"\n基本指標:")
        report.append(f"  總交易次數: {latest_metrics.total_trades}")
        report.append(f"  獲利交易: {latest_metrics.winning_trades}")
        report.append(f"  虧損交易: {latest_metrics.losing_trades}")
        report.append(f"  勝率: {latest_metrics.win_rate:.2f}%")
        
        report.append(f"\n損益指標:")
        report.append(f"  總損益: {latest_metrics.total_pnl:.2f} USDT ({latest_metrics.total_pnl_pct:.2f}%)")
        report.append(f"  當前資金: {latest_metrics.current_capital:.2f} USDT")
        report.append(f"  初始資金: {latest_metrics.initial_capital:.2f} USDT")
        
        report.append(f"\n風險指標:")
        report.append(f"  最大回撤: {latest_metrics.max_drawdown:.2f} USDT ({latest_metrics.max_drawdown_pct:.2f}%)")
        report.append(f"  夏普比率: {latest_metrics.sharpe_ratio:.2f}")
        
        report.append(f"\n近期表現:")
        report.append(f"  近期勝率: {latest_metrics.recent_win_rate:.2f}%")
        report.append(f"  近期損益: {latest_metrics.recent_pnl:.2f} USDT")
        report.append(f"  連續虧損: {latest_metrics.consecutive_losses} 次")
        
        if comparison['available']:
            report.append(f"\n與回測比較:")
            report.append(f"  性能等級: {comparison['performance_grade']}")
            report.append(f"  勝率差異: {comparison['difference']['win_rate']:+.2f}%")
            report.append(f"  收益率差異: {comparison['difference']['total_pnl_pct']:+.2f}%")
            report.append(f"  回撤差異: {comparison['difference']['max_drawdown_pct']:+.2f}%")
        
        report.append(f"\n狀態檢測:")
        report.append(f"  異常: {'是' if is_anomaly else '否'}")
        if is_anomaly:
            report.append(f"    {anomaly_msg}")
        
        report.append(f"  退化: {'是' if is_degraded else '否'}")
        if is_degraded:
            report.append(f"    退化程度: {degradation_score:.1f}")
        
        report.append(f"  暫停: {'是' if should_halt else '否'}")
        if should_halt:
            report.append(f"    原因: {halt_reason}")
        
        report.append("=" * 80)
        
        return "\n".join(report)
