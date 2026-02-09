"""
覆盤系統 (Review System)

提供交易記錄管理、執行質量評分和覆盤報告生成功能。
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import json
import os
from pathlib import Path

from src.models.trading import Trade


@dataclass
class TradeNote:
    """交易註記"""
    trade_id: str
    timestamp: datetime
    note: str
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            'trade_id': self.trade_id,
            'timestamp': self.timestamp.isoformat(),
            'note': self.note,
            'tags': self.tags,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TradeNote':
        """從字典創建"""
        return cls(
            trade_id=data['trade_id'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            note=data['note'],
            tags=data.get('tags', []),
        )


@dataclass
class ExecutionQuality:
    """執行質量評分"""
    trade_id: str
    overall_score: float  # 總體評分 (0-100)
    entry_quality: float  # 進場質量 (0-100)
    exit_quality: float  # 出場質量 (0-100)
    risk_management: float  # 風險管理 (0-100)
    errors: List[str] = field(default_factory=list)  # 識別的錯誤
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            'trade_id': self.trade_id,
            'overall_score': self.overall_score,
            'entry_quality': self.entry_quality,
            'exit_quality': self.exit_quality,
            'risk_management': self.risk_management,
            'errors': self.errors,
        }


@dataclass
class ReviewReport:
    """覆盤報告"""
    report_id: str
    period_start: datetime
    period_end: datetime
    trades: List[Trade]
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    avg_quality_score: float
    common_errors: List[Tuple[str, int]]  # (錯誤類型, 出現次數)
    improvement_trend: Optional[float] = None  # 改善趨勢 (-1 to 1)
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            'report_id': self.report_id,
            'period_start': self.period_start.isoformat(),
            'period_end': self.period_end.isoformat(),
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': self.win_rate,
            'total_pnl': self.total_pnl,
            'avg_quality_score': self.avg_quality_score,
            'common_errors': self.common_errors,
            'improvement_trend': self.improvement_trend,
            'trades': [t.to_dict() for t in self.trades],
        }


class ReviewSystem:
    """覆盤系統"""
    
    def __init__(self, storage_dir: str = "data/review_history"):
        """初始化覆盤系統
        
        Args:
            storage_dir: 存儲目錄
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # 交易記錄存儲
        self.trades: Dict[str, Trade] = {}
        
        # 交易註記存儲
        self.notes: Dict[str, List[TradeNote]] = {}  # trade_id -> notes
        
        # 執行質量評分存儲
        self.quality_scores: Dict[str, ExecutionQuality] = {}  # trade_id -> quality
        
        # 載入已存在的數據
        self._load_data()
    
    def _load_data(self) -> None:
        """載入已存在的數據"""
        # 載入交易記錄
        trades_file = self.storage_dir / "trades.json"
        if trades_file.exists():
            with open(trades_file, 'r', encoding='utf-8') as f:
                trades_data = json.load(f)
                for trade_dict in trades_data:
                    trade = self._trade_from_dict(trade_dict)
                    self.trades[trade.trade_id] = trade
        
        # 載入註記
        notes_file = self.storage_dir / "notes.json"
        if notes_file.exists():
            with open(notes_file, 'r', encoding='utf-8') as f:
                notes_data = json.load(f)
                for trade_id, notes_list in notes_data.items():
                    self.notes[trade_id] = [TradeNote.from_dict(n) for n in notes_list]
        
        # 載入質量評分
        quality_file = self.storage_dir / "quality_scores.json"
        if quality_file.exists():
            with open(quality_file, 'r', encoding='utf-8') as f:
                quality_data = json.load(f)
                for trade_id, quality_dict in quality_data.items():
                    self.quality_scores[trade_id] = ExecutionQuality(**quality_dict)
    
    def _save_data(self) -> None:
        """保存數據到文件"""
        # 保存交易記錄
        trades_file = self.storage_dir / "trades.json"
        with open(trades_file, 'w', encoding='utf-8') as f:
            json.dump([t.to_dict() for t in self.trades.values()], f, indent=2, ensure_ascii=False)
        
        # 保存註記
        notes_file = self.storage_dir / "notes.json"
        notes_data = {
            trade_id: [n.to_dict() for n in notes]
            for trade_id, notes in self.notes.items()
        }
        with open(notes_file, 'w', encoding='utf-8') as f:
            json.dump(notes_data, f, indent=2, ensure_ascii=False)
        
        # 保存質量評分
        quality_file = self.storage_dir / "quality_scores.json"
        quality_data = {
            trade_id: quality.to_dict()
            for trade_id, quality in self.quality_scores.items()
        }
        with open(quality_file, 'w', encoding='utf-8') as f:
            json.dump(quality_data, f, indent=2, ensure_ascii=False)
    
    def _trade_from_dict(self, data: Dict[str, Any]) -> Trade:
        """從字典創建 Trade 對象"""
        return Trade(
            trade_id=data['trade_id'],
            strategy_id=data['strategy_id'],
            symbol=data['symbol'],
            direction=data['direction'],
            entry_time=datetime.fromisoformat(data['entry_time']),
            exit_time=datetime.fromisoformat(data['exit_time']),
            entry_price=data['entry_price'],
            exit_price=data['exit_price'],
            size=data['size'],
            leverage=data['leverage'],
            pnl=data['pnl'],
            pnl_pct=data['pnl_pct'],
            commission=data['commission'],
            exit_reason=data['exit_reason'],
            metadata=data.get('metadata', {}),
        )
    
    # ========== 交易記錄管理 ==========
    
    def record_trade(self, trade: Trade) -> None:
        """記錄交易
        
        Args:
            trade: 交易記錄
        """
        self.trades[trade.trade_id] = trade
        self._save_data()
    
    def get_trade(self, trade_id: str) -> Optional[Trade]:
        """獲取交易記錄
        
        Args:
            trade_id: 交易 ID
            
        Returns:
            Optional[Trade]: 交易記錄，如果不存在則返回 None
        """
        return self.trades.get(trade_id)
    
    def add_note(self, trade_id: str, note: str, tags: Optional[List[str]] = None) -> None:
        """為交易添加註記
        
        Args:
            trade_id: 交易 ID
            note: 註記內容
            tags: 標籤列表
        """
        if trade_id not in self.trades:
            raise ValueError(f"Trade {trade_id} not found")
        
        trade_note = TradeNote(
            trade_id=trade_id,
            timestamp=datetime.now(),
            note=note,
            tags=tags or [],
        )
        
        if trade_id not in self.notes:
            self.notes[trade_id] = []
        
        self.notes[trade_id].append(trade_note)
        self._save_data()
    
    def get_notes(self, trade_id: str) -> List[TradeNote]:
        """獲取交易的所有註記
        
        Args:
            trade_id: 交易 ID
            
        Returns:
            List[TradeNote]: 註記列表
        """
        return self.notes.get(trade_id, [])
    
    def get_trades_by_period(
        self,
        start_date: datetime,
        end_date: datetime,
        strategy_id: Optional[str] = None
    ) -> List[Trade]:
        """獲取指定時間範圍內的交易
        
        Args:
            start_date: 開始日期
            end_date: 結束日期
            strategy_id: 策略 ID（可選）
            
        Returns:
            List[Trade]: 交易列表
        """
        trades = []
        for trade in self.trades.values():
            # 檢查時間範圍
            if not (start_date <= trade.entry_time <= end_date):
                continue
            
            # 檢查策略 ID
            if strategy_id and trade.strategy_id != strategy_id:
                continue
            
            trades.append(trade)
        
        return sorted(trades, key=lambda t: t.entry_time)
    
    # ========== 執行質量評分 ==========
    
    def calculate_execution_quality(self, trade: Trade) -> ExecutionQuality:
        """計算執行質量評分
        
        Args:
            trade: 交易記錄
            
        Returns:
            ExecutionQuality: 執行質量評分
        """
        errors = []
        
        # 1. 進場質量評分 (0-100)
        entry_quality = 100.0
        
        # 檢查是否在合理的價格範圍內進場
        # (這裡簡化處理，實際應該結合市場數據)
        
        # 2. 出場質量評分 (0-100)
        exit_quality = 100.0
        
        # 檢查是否過早出場
        if trade.is_winning() and trade.pnl_pct < 1.0:
            errors.append("過早獲利了結")
            exit_quality -= 20
        
        # 檢查是否未執行止損
        if not trade.is_winning() and trade.pnl_pct < -5.0:
            errors.append("未及時止損")
            exit_quality -= 30
        
        # 檢查是否讓獲利變成虧損
        if not trade.is_winning() and trade.exit_reason == "手動平倉":
            errors.append("可能讓獲利變成虧損")
            exit_quality -= 25
        
        # 3. 風險管理評分 (0-100)
        risk_management = 100.0
        
        # 檢查止損設置是否合理
        if trade.direction == 'long':
            stop_loss_pct = abs((trade.entry_price - trade.metadata.get('stop_loss', trade.entry_price)) / trade.entry_price * 100)
        else:
            stop_loss_pct = abs((trade.metadata.get('stop_loss', trade.entry_price) - trade.entry_price) / trade.entry_price * 100)
        
        if stop_loss_pct > 5.0:
            errors.append("止損設置過寬")
            risk_management -= 20
        elif stop_loss_pct < 0.5:
            errors.append("止損設置過緊")
            risk_management -= 15
        
        # 檢查槓桿使用是否合理
        if trade.leverage > 10:
            errors.append("槓桿過高")
            risk_management -= 25
        
        # 4. 計算總體評分
        overall_score = (entry_quality + exit_quality + risk_management) / 3
        
        quality = ExecutionQuality(
            trade_id=trade.trade_id,
            overall_score=overall_score,
            entry_quality=entry_quality,
            exit_quality=exit_quality,
            risk_management=risk_management,
            errors=errors,
        )
        
        # 保存評分
        self.quality_scores[trade.trade_id] = quality
        self._save_data()
        
        return quality
    
    def get_execution_quality(self, trade_id: str) -> Optional[ExecutionQuality]:
        """獲取執行質量評分
        
        Args:
            trade_id: 交易 ID
            
        Returns:
            Optional[ExecutionQuality]: 執行質量評分
        """
        return self.quality_scores.get(trade_id)
    
    # ========== 覆盤報告生成 ==========
    
    def generate_daily_report(self, date: datetime) -> ReviewReport:
        """生成每日覆盤報告
        
        Args:
            date: 日期
            
        Returns:
            ReviewReport: 覆盤報告
        """
        start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)
        
        return self._generate_report(start_date, end_date, "daily")
    
    def generate_weekly_report(self, start_date: datetime) -> ReviewReport:
        """生成每週覆盤報告
        
        Args:
            start_date: 週開始日期
            
        Returns:
            ReviewReport: 覆盤報告
        """
        end_date = start_date + timedelta(days=7)
        return self._generate_report(start_date, end_date, "weekly")
    
    def generate_monthly_report(self, year: int, month: int) -> ReviewReport:
        """生成每月覆盤報告
        
        Args:
            year: 年份
            month: 月份
            
        Returns:
            ReviewReport: 覆盤報告
        """
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
        
        return self._generate_report(start_date, end_date, "monthly")
    
    def _generate_report(
        self,
        start_date: datetime,
        end_date: datetime,
        period_type: str
    ) -> ReviewReport:
        """生成覆盤報告
        
        Args:
            start_date: 開始日期
            end_date: 結束日期
            period_type: 週期類型 (daily/weekly/monthly)
            
        Returns:
            ReviewReport: 覆盤報告
        """
        # 獲取時間範圍內的交易
        trades = self.get_trades_by_period(start_date, end_date)
        
        # 計算統計數據
        total_trades = len(trades)
        winning_trades = sum(1 for t in trades if t.is_winning())
        losing_trades = total_trades - winning_trades
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0
        total_pnl = sum(t.pnl for t in trades)
        
        # 計算平均質量評分
        quality_scores = []
        for trade in trades:
            if trade.trade_id in self.quality_scores:
                quality_scores.append(self.quality_scores[trade.trade_id].overall_score)
            else:
                # 如果沒有評分，計算一個
                quality = self.calculate_execution_quality(trade)
                quality_scores.append(quality.overall_score)
        
        avg_quality_score = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
        
        # 統計常見錯誤
        error_counts: Dict[str, int] = {}
        for trade in trades:
            if trade.trade_id in self.quality_scores:
                for error in self.quality_scores[trade.trade_id].errors:
                    error_counts[error] = error_counts.get(error, 0) + 1
        
        common_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)
        
        # 計算改善趨勢
        improvement_trend = self._calculate_improvement_trend(trades)
        
        # 生成報告 ID
        report_id = f"{period_type}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
        
        report = ReviewReport(
            report_id=report_id,
            period_start=start_date,
            period_end=end_date,
            trades=trades,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            total_pnl=total_pnl,
            avg_quality_score=avg_quality_score,
            common_errors=common_errors,
            improvement_trend=improvement_trend,
        )
        
        return report
    
    def _calculate_improvement_trend(self, trades: List[Trade]) -> Optional[float]:
        """計算改善趨勢
        
        Args:
            trades: 交易列表
            
        Returns:
            Optional[float]: 改善趨勢 (-1 to 1)，None 表示數據不足
        """
        if len(trades) < 10:
            return None
        
        # 將交易分為前半和後半
        mid_point = len(trades) // 2
        first_half = trades[:mid_point]
        second_half = trades[mid_point:]
        
        # 計算前半和後半的平均質量評分
        first_half_scores = []
        for trade in first_half:
            if trade.trade_id in self.quality_scores:
                first_half_scores.append(self.quality_scores[trade.trade_id].overall_score)
        
        second_half_scores = []
        for trade in second_half:
            if trade.trade_id in self.quality_scores:
                second_half_scores.append(self.quality_scores[trade.trade_id].overall_score)
        
        if not first_half_scores or not second_half_scores:
            return None
        
        first_avg = sum(first_half_scores) / len(first_half_scores)
        second_avg = sum(second_half_scores) / len(second_half_scores)
        
        # 計算改善趨勢 (-1 to 1)
        # 正值表示改善，負值表示退步
        improvement = (second_avg - first_avg) / 100.0
        return max(-1.0, min(1.0, improvement))
    
    def save_report(self, report: ReviewReport, filepath: Optional[str] = None) -> str:
        """保存覆盤報告
        
        Args:
            report: 覆盤報告
            filepath: 文件路徑（可選）
            
        Returns:
            str: 保存的文件路徑
        """
        if filepath is None:
            reports_dir = self.storage_dir / "reports"
            reports_dir.mkdir(exist_ok=True)
            filepath = str(reports_dir / f"{report.report_id}.json")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)
        
        return filepath
    
    def export_data(self, filepath: str, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> None:
        """導出覆盤數據
        
        Args:
            filepath: 導出文件路徑
            start_date: 開始日期（可選）
            end_date: 結束日期（可選）
        """
        # 獲取要導出的交易
        if start_date and end_date:
            trades = self.get_trades_by_period(start_date, end_date)
        else:
            trades = list(self.trades.values())
        
        # 準備導出數據
        export_data = {
            'trades': [t.to_dict() for t in trades],
            'notes': {
                trade_id: [n.to_dict() for n in notes]
                for trade_id, notes in self.notes.items()
                if trade_id in [t.trade_id for t in trades]
            },
            'quality_scores': {
                trade_id: quality.to_dict()
                for trade_id, quality in self.quality_scores.items()
                if trade_id in [t.trade_id for t in trades]
            },
        }
        
        # 保存到文件
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
    
    def import_data(self, filepath: str) -> None:
        """導入覆盤數據
        
        Args:
            filepath: 導入文件路徑
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            import_data = json.load(f)
        
        # 導入交易
        for trade_dict in import_data.get('trades', []):
            trade = self._trade_from_dict(trade_dict)
            self.trades[trade.trade_id] = trade
        
        # 導入註記
        for trade_id, notes_list in import_data.get('notes', {}).items():
            self.notes[trade_id] = [TradeNote.from_dict(n) for n in notes_list]
        
        # 導入質量評分
        for trade_id, quality_dict in import_data.get('quality_scores', {}).items():
            self.quality_scores[trade_id] = ExecutionQuality(**quality_dict)
        
        # 保存數據
        self._save_data()
