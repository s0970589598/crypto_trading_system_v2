"""
虧損分析器 (Loss Analyzer)

根據 Requirement 6 實現虧損交易的自動分析和改進建議生成。
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import pandas as pd

from ..models.trading import Trade


@dataclass
class LossPattern:
    """虧損模式"""
    pattern_name: str  # 模式名稱
    description: str  # 模式描述
    occurrence_count: int  # 出現次數
    total_loss: float  # 總虧損金額
    percentage: float  # 佔比
    examples: List[str] = field(default_factory=list)  # 示例交易 ID


@dataclass
class LossAnalysis:
    """虧損分析結果"""
    trade_id: str  # 交易 ID
    loss_reason: str  # 虧損原因分類
    confidence: float  # 分類置信度 (0-1)
    contributing_factors: List[str] = field(default_factory=list)  # 貢獻因素
    recommendations: List[str] = field(default_factory=list)  # 改進建議
    metadata: Dict[str, Any] = field(default_factory=dict)  # 額外信息


class LossAnalyzer:
    """虧損分析器
    
    實現 Requirement 6 的所有功能：
    - 自動記錄虧損原因分類
    - 分析虧損交易的共同特徵
    - 識別虧損模式
    - 計算每種虧損原因的佔比
    - 生成改進建議
    - 支持自定義虧損分類規則
    """
    
    # 預定義的虧損原因分類
    LOSS_REASONS = {
        'STOP_LOSS_TOO_TIGHT': '止損太緊',
        'TREND_MISJUDGMENT': '趨勢判斷錯誤',
        'PREMATURE_ENTRY': '過早進場',
        'LATE_ENTRY': '進場太晚',
        'MARKET_REVERSAL': '市場反轉',
        'VOLATILITY_SPIKE': '波動率突增',
        'HOLDING_TOO_LONG': '持倉時間過長',
        'HOLDING_TOO_SHORT': '持倉時間過短',
        'POOR_RISK_REWARD': '風險回報比不佳',
        'UNKNOWN': '未知原因',
    }
    
    def __init__(self, custom_rules: Optional[Dict[str, Any]] = None):
        """初始化虧損分析器
        
        Args:
            custom_rules: 自定義虧損分類規則（可選）
        """
        self.custom_rules = custom_rules or {}
        self.loss_history: List[LossAnalysis] = []
    
    def analyze_trade(
        self,
        trade: Trade,
        market_data: Optional[pd.DataFrame] = None
    ) -> LossAnalysis:
        """分析單筆虧損交易
        
        Args:
            trade: 交易記錄
            market_data: 市場數據（可選，用於更精確的分析）
        
        Returns:
            LossAnalysis: 虧損分析結果
        """
        if trade.is_winning():
            raise ValueError(f"交易 {trade.trade_id} 不是虧損交易")
        
        # 分類虧損原因
        loss_reason, confidence = self.classify_loss_reason(trade, market_data)
        
        # 識別貢獻因素
        contributing_factors = self._identify_contributing_factors(trade, market_data)
        
        # 生成改進建議
        recommendations = self.generate_recommendations(loss_reason, trade, market_data)
        
        # 創建分析結果
        analysis = LossAnalysis(
            trade_id=trade.trade_id,
            loss_reason=loss_reason,
            confidence=confidence,
            contributing_factors=contributing_factors,
            recommendations=recommendations,
            metadata={
                'pnl': trade.pnl,
                'pnl_pct': trade.pnl_pct,
                'duration_hours': trade.get_duration_hours(),
                'exit_reason': trade.exit_reason,
            }
        )
        
        # 記錄到歷史
        self.loss_history.append(analysis)
        
        return analysis
    
    def classify_loss_reason(
        self,
        trade: Trade,
        market_data: Optional[pd.DataFrame] = None
    ) -> Tuple[str, float]:
        """分類虧損原因
        
        Args:
            trade: 交易記錄
            market_data: 市場數據（可選）
        
        Returns:
            Tuple[str, float]: (虧損原因, 置信度)
        """
        # 首先檢查自定義規則
        if self.custom_rules:
            custom_result = self._apply_custom_rules(trade, market_data)
            if custom_result:
                return custom_result
        
        # 基於出場原因的初步分類
        if trade.exit_reason == '止損':
            return self._classify_stop_loss(trade, market_data)
        elif trade.exit_reason == '獲利':
            # 雖然觸發獲利但仍虧損（可能是手續費導致）
            return ('POOR_RISK_REWARD', 0.8)
        else:
            return self._classify_other_exit(trade, market_data)
    
    def _classify_stop_loss(
        self,
        trade: Trade,
        market_data: Optional[pd.DataFrame]
    ) -> Tuple[str, float]:
        """分類止損類型的虧損
        
        Args:
            trade: 交易記錄
            market_data: 市場數據
        
        Returns:
            Tuple[str, float]: (虧損原因, 置信度)
        """
        # 從 metadata 中獲取止損價格（如果有）
        stop_loss = trade.metadata.get('stop_loss')
        
        # 如果持倉時間很短（< 1小時），可能是過早進場或波動率突增
        duration_hours = trade.get_duration_hours()
        if duration_hours < 1.0:
            if market_data is not None:
                # 檢查是否有波動率突增
                if self._detect_volatility_spike(trade, market_data):
                    return ('VOLATILITY_SPIKE', 0.85)
            return ('PREMATURE_ENTRY', 0.75)
        
        if stop_loss is not None:
            # 計算止損距離（相對於進場價）
            if trade.direction == 'long':
                stop_distance_pct = abs((stop_loss - trade.entry_price) / trade.entry_price * 100)
            else:
                stop_distance_pct = abs((trade.entry_price - stop_loss) / trade.entry_price * 100)
            
            # 如果止損距離很小（< 1%），可能是止損太緊
            if stop_distance_pct < 1.0:
                return ('STOP_LOSS_TOO_TIGHT', 0.9)
            
            # 如果虧損百分比接近止損距離，可能是趨勢判斷錯誤
            if abs(trade.pnl_pct) >= stop_distance_pct * 0.8:
                return ('TREND_MISJUDGMENT', 0.8)
        
        # 默認分類
        return ('MARKET_REVERSAL', 0.6)
    
    def _classify_other_exit(
        self,
        trade: Trade,
        market_data: Optional[pd.DataFrame]
    ) -> Tuple[str, float]:
        """分類其他出場原因的虧損
        
        Args:
            trade: 交易記錄
            market_data: 市場數據
        
        Returns:
            Tuple[str, float]: (虧損原因, 置信度)
        """
        duration_hours = trade.get_duration_hours()
        
        # 持倉時間過長（> 24小時）
        if duration_hours > 24.0:
            return ('HOLDING_TOO_LONG', 0.75)
        
        # 持倉時間過短（< 0.5小時）
        if duration_hours < 0.5:
            return ('HOLDING_TOO_SHORT', 0.7)
        
        # 進場太晚（價格已經移動較多）
        if market_data is not None:
            if self._detect_late_entry(trade, market_data):
                return ('LATE_ENTRY', 0.7)
        
        return ('UNKNOWN', 0.5)
    
    def _identify_contributing_factors(
        self,
        trade: Trade,
        market_data: Optional[pd.DataFrame]
    ) -> List[str]:
        """識別虧損的貢獻因素
        
        Args:
            trade: 交易記錄
            market_data: 市場數據
        
        Returns:
            List[str]: 貢獻因素列表
        """
        factors = []
        
        # 檢查槓桿使用
        if trade.leverage > 5:
            factors.append(f'高槓桿使用 ({trade.leverage}x)')
        
        # 檢查虧損幅度
        if abs(trade.pnl_pct) > 5.0:
            factors.append(f'大幅虧損 ({trade.pnl_pct:.2f}%)')
        
        # 檢查持倉時間
        duration_hours = trade.get_duration_hours()
        if duration_hours < 0.5:
            factors.append('極短持倉時間')
        elif duration_hours > 48:
            factors.append('過長持倉時間')
        
        # 檢查手續費影響
        if abs(trade.commission) > abs(trade.pnl) * 0.3:
            factors.append('手續費佔比過高')
        
        return factors
    
    def find_common_patterns(self, trades: List[Trade]) -> List[LossPattern]:
        """找出虧損交易的共同模式
        
        Args:
            trades: 虧損交易列表
        
        Returns:
            List[LossPattern]: 虧損模式列表
        """
        if not trades:
            return []
        
        # 過濾出虧損交易
        losing_trades = [t for t in trades if not t.is_winning()]
        
        if not losing_trades:
            return []
        
        # 按虧損原因分組
        reason_groups: Dict[str, List[Trade]] = {}
        for trade in losing_trades:
            # 如果已經分析過，使用歷史記錄
            analysis = next(
                (a for a in self.loss_history if a.trade_id == trade.trade_id),
                None
            )
            
            if analysis:
                reason = analysis.loss_reason
            else:
                # 否則進行分析
                reason, _ = self.classify_loss_reason(trade)
            
            if reason not in reason_groups:
                reason_groups[reason] = []
            reason_groups[reason].append(trade)
        
        # 計算總虧損
        total_loss = sum(abs(t.pnl) for t in losing_trades)
        
        # 創建虧損模式
        patterns = []
        for reason, group_trades in reason_groups.items():
            group_loss = sum(abs(t.pnl) for t in group_trades)
            percentage = (group_loss / total_loss * 100) if total_loss > 0 else 0.0
            
            pattern = LossPattern(
                pattern_name=reason,
                description=self.LOSS_REASONS.get(reason, '未知原因'),
                occurrence_count=len(group_trades),
                total_loss=group_loss,
                percentage=percentage,
                examples=[t.trade_id for t in group_trades[:3]]  # 最多3個示例
            )
            patterns.append(pattern)
        
        # 按虧損金額排序
        patterns.sort(key=lambda p: p.total_loss, reverse=True)
        
        return patterns
    
    def generate_recommendations(
        self,
        loss_reason: str,
        trade: Trade,
        market_data: Optional[pd.DataFrame] = None
    ) -> List[str]:
        """生成改進建議
        
        Args:
            loss_reason: 虧損原因
            trade: 交易記錄
            market_data: 市場數據
        
        Returns:
            List[str]: 改進建議列表
        """
        recommendations = []
        
        if loss_reason == 'STOP_LOSS_TOO_TIGHT':
            recommendations.extend([
                '考慮放寬止損距離，建議至少 1.5-2 倍 ATR',
                '在波動較大的市場環境中，適當增加止損空間',
                '使用移動止損而非固定止損',
            ])
        
        elif loss_reason == 'TREND_MISJUDGMENT':
            recommendations.extend([
                '加強趨勢確認，等待更多確認信號',
                '使用多週期分析確認趨勢方向',
                '避免在震盪市場中追趨勢',
            ])
        
        elif loss_reason == 'PREMATURE_ENTRY':
            recommendations.extend([
                '等待更明確的進場信號',
                '使用回調進場而非突破進場',
                '確認支撐/阻力位後再進場',
            ])
        
        elif loss_reason == 'LATE_ENTRY':
            recommendations.extend([
                '避免追高/追低，等待回調機會',
                '設置價格警報，及時捕捉進場時機',
                '如果錯過最佳進場點，放棄該次機會',
            ])
        
        elif loss_reason == 'MARKET_REVERSAL':
            recommendations.extend([
                '注意市場反轉信號（如背離、吞沒形態）',
                '在關鍵支撐/阻力位附近提高警惕',
                '使用移動止損保護利潤',
            ])
        
        elif loss_reason == 'VOLATILITY_SPIKE':
            recommendations.extend([
                '避免在重大新聞發布前後交易',
                '在高波動期間減少倉位',
                '使用更寬的止損或暫停交易',
            ])
        
        elif loss_reason == 'HOLDING_TOO_LONG':
            recommendations.extend([
                '設置時間止損，避免過度持倉',
                '定期檢查持倉理由是否仍然成立',
                '使用移動止損鎖定利潤',
            ])
        
        elif loss_reason == 'HOLDING_TOO_SHORT':
            recommendations.extend([
                '給交易更多時間發展',
                '避免因小幅波動而過早出場',
                '設置合理的目標價位',
            ])
        
        elif loss_reason == 'POOR_RISK_REWARD':
            recommendations.extend([
                '確保風險回報比至少 1:2',
                '重新評估進場點和止損/目標位設置',
                '考慮手續費對小額交易的影響',
            ])
        
        elif loss_reason == 'UNKNOWN':
            recommendations.extend([
                '詳細記錄交易過程，以便後續分析',
                '檢查是否有遺漏的市場信號或條件',
                '考慮增加更多的技術指標輔助判斷',
                '回顧交易計劃，確保執行一致性',
            ])
        
        # 添加基於槓桿的建議
        if trade.leverage > 5:
            recommendations.append(f'當前槓桿 {trade.leverage}x 較高，考慮降低槓桿以減少風險')
        
        # 添加基於虧損幅度的建議
        if abs(trade.pnl_pct) > 5.0:
            recommendations.append('虧損幅度較大，建議檢查風險管理設置')
        
        return recommendations
    
    def calculate_loss_distribution(self, trades: List[Trade]) -> Dict[str, float]:
        """計算每種虧損原因的佔比
        
        Args:
            trades: 交易列表
        
        Returns:
            Dict[str, float]: 虧損原因 -> 佔比（百分比）
        """
        patterns = self.find_common_patterns(trades)
        
        distribution = {}
        for pattern in patterns:
            distribution[pattern.pattern_name] = pattern.percentage
        
        return distribution
    
    def track_improvement_trend(
        self,
        trades: List[Trade],
        window_size: int = 20
    ) -> pd.DataFrame:
        """追蹤虧損改善趨勢
        
        Args:
            trades: 交易列表（按時間排序）
            window_size: 滑動窗口大小
        
        Returns:
            pd.DataFrame: 趨勢數據
        """
        if len(trades) < window_size:
            return pd.DataFrame()
        
        # 計算滑動窗口的虧損率
        loss_rates = []
        avg_losses = []
        timestamps = []
        
        for i in range(window_size, len(trades) + 1):
            window_trades = trades[i - window_size:i]
            losing_trades = [t for t in window_trades if not t.is_winning()]
            
            loss_rate = len(losing_trades) / len(window_trades) * 100
            avg_loss = sum(t.pnl for t in losing_trades) / len(losing_trades) if losing_trades else 0.0
            
            loss_rates.append(loss_rate)
            avg_losses.append(avg_loss)
            timestamps.append(window_trades[-1].exit_time)
        
        return pd.DataFrame({
            'timestamp': timestamps,
            'loss_rate': loss_rates,
            'avg_loss': avg_losses,
        })
    
    def _apply_custom_rules(
        self,
        trade: Trade,
        market_data: Optional[pd.DataFrame]
    ) -> Optional[Tuple[str, float]]:
        """應用自定義虧損分類規則
        
        Args:
            trade: 交易記錄
            market_data: 市場數據
        
        Returns:
            Optional[Tuple[str, float]]: (虧損原因, 置信度) 或 None
        """
        # 這裡可以實現自定義規則的邏輯
        # 例如：基於特定的市場條件或策略參數
        return None
    
    def _detect_volatility_spike(
        self,
        trade: Trade,
        market_data: pd.DataFrame
    ) -> bool:
        """檢測波動率突增
        
        Args:
            trade: 交易記錄
            market_data: 市場數據
        
        Returns:
            bool: 是否檢測到波動率突增
        """
        # 簡化實現：檢查交易期間的價格波動
        # 實際應用中可以使用 ATR 或其他波動率指標
        return False
    
    def _detect_late_entry(
        self,
        trade: Trade,
        market_data: pd.DataFrame
    ) -> bool:
        """檢測進場太晚
        
        Args:
            trade: 交易記錄
            market_data: 市場數據
        
        Returns:
            bool: 是否進場太晚
        """
        # 簡化實現：檢查進場前的價格移動
        # 實際應用中可以分析趨勢的發展階段
        return False
    
    def generate_report(self, trades: List[Trade]) -> str:
        """生成虧損分析報告
        
        Args:
            trades: 交易列表
        
        Returns:
            str: 報告文本
        """
        losing_trades = [t for t in trades if not t.is_winning()]
        
        if not losing_trades:
            return "沒有虧損交易需要分析。"
        
        patterns = self.find_common_patterns(trades)
        distribution = self.calculate_loss_distribution(trades)
        
        report = []
        report.append("=" * 80)
        report.append("虧損分析報告")
        report.append("=" * 80)
        report.append(f"\n總交易數：{len(trades)}")
        report.append(f"虧損交易數：{len(losing_trades)}")
        report.append(f"虧損率：{len(losing_trades) / len(trades) * 100:.2f}%")
        report.append(f"\n虧損原因分布：")
        
        for pattern in patterns:
            report.append(f"\n{pattern.description} ({pattern.pattern_name}):")
            report.append(f"  出現次數：{pattern.occurrence_count}")
            report.append(f"  總虧損：{pattern.total_loss:.2f} USDT")
            report.append(f"  佔比：{pattern.percentage:.2f}%")
        
        report.append("\n" + "=" * 80)
        
        return "\n".join(report)
