"""
回測結果數據模型
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path
import json
import pandas as pd

from .trading import Trade


@dataclass
class BacktestResult:
    """回測結果"""
    strategy_id: str  # 策略 ID
    start_date: datetime  # 開始日期
    end_date: datetime  # 結束日期
    initial_capital: float  # 初始資金
    final_capital: float  # 最終資金
    
    # 交易統計
    total_trades: int = 0  # 總交易次數
    winning_trades: int = 0  # 獲利交易次數
    losing_trades: int = 0  # 虧損交易次數
    win_rate: float = 0.0  # 勝率
    
    # 損益統計
    total_pnl: float = 0.0  # 總損益
    total_pnl_pct: float = 0.0  # 總損益百分比
    avg_win: float = 0.0  # 平均獲利
    avg_loss: float = 0.0  # 平均虧損
    profit_factor: float = 0.0  # 獲利因子
    
    # 風險指標
    max_drawdown: float = 0.0  # 最大回撤（USDT）
    max_drawdown_pct: float = 0.0  # 最大回撤百分比
    sharpe_ratio: float = 0.0  # 夏普比率
    
    # 交易列表
    trades: List[Trade] = field(default_factory=list)
    
    # 資金曲線
    equity_curve: pd.Series = field(default_factory=pd.Series)
    
    def calculate_metrics(self) -> None:
        """計算所有績效指標"""
        if not self.trades:
            return
        
        # 基本統計
        self.total_trades = len(self.trades)
        self.winning_trades = sum(1 for t in self.trades if t.is_winning())
        self.losing_trades = self.total_trades - self.winning_trades
        self.win_rate = (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0.0
        
        # 損益統計
        self.total_pnl = sum(t.pnl for t in self.trades)
        self.total_pnl_pct = ((self.final_capital / self.initial_capital) - 1) * 100
        
        winning_pnls = [t.pnl for t in self.trades if t.is_winning()]
        losing_pnls = [t.pnl for t in self.trades if not t.is_winning()]
        
        self.avg_win = sum(winning_pnls) / len(winning_pnls) if winning_pnls else 0.0
        self.avg_loss = sum(losing_pnls) / len(losing_pnls) if losing_pnls else 0.0
        
        # 獲利因子
        total_wins = sum(winning_pnls) if winning_pnls else 0.0
        total_losses = abs(sum(losing_pnls)) if losing_pnls else 0.0
        self.profit_factor = (total_wins / total_losses) if total_losses > 0 else 0.0
        
        # 計算資金曲線和回撤
        self._calculate_equity_curve()
        self._calculate_drawdown()
        self._calculate_sharpe_ratio()
    
    def _calculate_equity_curve(self) -> None:
        """計算資金曲線"""
        if not self.trades:
            self.equity_curve = pd.Series([self.initial_capital])
            return
        
        equity = [self.initial_capital]
        current_capital = self.initial_capital
        
        for trade in self.trades:
            current_capital += trade.pnl
            equity.append(current_capital)
        
        # 使用交易時間作為索引
        timestamps = [self.start_date] + [t.exit_time for t in self.trades]
        self.equity_curve = pd.Series(equity, index=timestamps)
    
    def _calculate_drawdown(self) -> None:
        """計算最大回撤"""
        if self.equity_curve.empty:
            return
        
        # 計算累計最高點
        cumulative_max = self.equity_curve.cummax()
        
        # 計算回撤
        drawdown = self.equity_curve - cumulative_max
        drawdown_pct = (drawdown / cumulative_max) * 100
        
        # 最大回撤
        self.max_drawdown = abs(drawdown.min())
        self.max_drawdown_pct = abs(drawdown_pct.min())
    
    def _calculate_sharpe_ratio(self) -> None:
        """計算夏普比率"""
        if len(self.trades) < 2:
            self.sharpe_ratio = 0.0
            return
        
        # 計算每筆交易的收益率
        returns = [t.pnl_pct for t in self.trades]
        
        # 計算平均收益率和標準差
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        std_return = variance ** 0.5
        
        # 夏普比率（假設無風險利率為 0）
        self.sharpe_ratio = (mean_return / std_return) if std_return > 0 else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典
        
        Returns:
            Dict[str, Any]: 回測結果字典
        """
        return {
            'strategy_id': self.strategy_id,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'initial_capital': self.initial_capital,
            'final_capital': self.final_capital,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': self.win_rate,
            'total_pnl': self.total_pnl,
            'total_pnl_pct': self.total_pnl_pct,
            'avg_win': self.avg_win,
            'avg_loss': self.avg_loss,
            'profit_factor': self.profit_factor,
            'max_drawdown': self.max_drawdown,
            'max_drawdown_pct': self.max_drawdown_pct,
            'sharpe_ratio': self.sharpe_ratio,
            'trades': [t.to_dict() for t in self.trades],
            'equity_curve': self.equity_curve.to_dict() if not self.equity_curve.empty else {},
        }
    
    def save(self, filepath: str) -> None:
        """保存結果到文件
        
        Args:
            filepath: 文件路徑（JSON 格式）
        """
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # 轉換為可序列化的格式
        data = self.to_dict()
        
        # 轉換 equity_curve 的時間戳
        if data['equity_curve']:
            data['equity_curve'] = {
                k.isoformat() if isinstance(k, datetime) else str(k): v
                for k, v in data['equity_curve'].items()
            }
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    @classmethod
    def load(cls, filepath: str) -> 'BacktestResult':
        """從文件載入結果
        
        Args:
            filepath: 文件路徑（JSON 格式）
            
        Returns:
            BacktestResult: 回測結果對象
        """
        path = Path(filepath)
        
        if not path.exists():
            raise FileNotFoundError(f"文件不存在：{filepath}")
        
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 重建 Trade 對象
        trades = []
        for trade_data in data.get('trades', []):
            trade = Trade(
                trade_id=trade_data['trade_id'],
                strategy_id=trade_data['strategy_id'],
                symbol=trade_data['symbol'],
                direction=trade_data['direction'],
                entry_time=datetime.fromisoformat(trade_data['entry_time']),
                exit_time=datetime.fromisoformat(trade_data['exit_time']),
                entry_price=trade_data['entry_price'],
                exit_price=trade_data['exit_price'],
                size=trade_data['size'],
                leverage=trade_data['leverage'],
                pnl=trade_data['pnl'],
                pnl_pct=trade_data['pnl_pct'],
                commission=trade_data['commission'],
                exit_reason=trade_data['exit_reason'],
                metadata=trade_data.get('metadata', {}),
            )
            trades.append(trade)
        
        # 重建 equity_curve
        equity_data = data.get('equity_curve', {})
        if equity_data:
            timestamps = [datetime.fromisoformat(k) for k in equity_data.keys()]
            values = list(equity_data.values())
            equity_curve = pd.Series(values, index=timestamps)
        else:
            equity_curve = pd.Series()
        
        result = cls(
            strategy_id=data['strategy_id'],
            start_date=datetime.fromisoformat(data['start_date']),
            end_date=datetime.fromisoformat(data['end_date']),
            initial_capital=data['initial_capital'],
            final_capital=data['final_capital'],
            total_trades=data['total_trades'],
            winning_trades=data['winning_trades'],
            losing_trades=data['losing_trades'],
            win_rate=data['win_rate'],
            total_pnl=data['total_pnl'],
            total_pnl_pct=data['total_pnl_pct'],
            avg_win=data['avg_win'],
            avg_loss=data['avg_loss'],
            profit_factor=data['profit_factor'],
            max_drawdown=data['max_drawdown'],
            max_drawdown_pct=data['max_drawdown_pct'],
            sharpe_ratio=data['sharpe_ratio'],
            trades=trades,
            equity_curve=equity_curve,
        )
        
        return result
    
    def print_summary(self) -> None:
        """打印回測摘要"""
        print("=" * 80)
        print(f"回測結果 - {self.strategy_id}")
        print("=" * 80)
        print(f"\n期間：{self.start_date.date()} 至 {self.end_date.date()}")
        print(f"初始資金：{self.initial_capital:.2f} USDT")
        print(f"最終資金：{self.final_capital:.2f} USDT")
        print(f"總收益：{self.total_pnl:.2f} USDT ({self.total_pnl_pct:.2f}%)")
        print(f"\n交易統計：")
        print(f"  總交易次數：{self.total_trades}")
        print(f"  獲利交易：{self.winning_trades} 次")
        print(f"  虧損交易：{self.losing_trades} 次")
        print(f"  勝率：{self.win_rate:.2f}%")
        print(f"\n損益分析：")
        print(f"  平均獲利：{self.avg_win:.2f} USDT")
        print(f"  平均虧損：{self.avg_loss:.2f} USDT")
        print(f"  獲利因子：{self.profit_factor:.2f}")
        print(f"\n風險指標：")
        print(f"  最大回撤：{self.max_drawdown:.2f} USDT ({self.max_drawdown_pct:.2f}%)")
        print(f"  夏普比率：{self.sharpe_ratio:.2f}")
        print("=" * 80)
