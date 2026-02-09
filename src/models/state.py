"""
策略狀態數據模型
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
from src.models.trading import Position


@dataclass
class StrategyState:
    """策略運行狀態"""
    strategy_id: str
    enabled: bool
    current_position: Optional[Position] = None
    
    # 今日統計
    trades_today: int = 0
    pnl_today: float = 0.0
    consecutive_losses: int = 0
    
    # 累計統計
    total_trades: int = 0
    total_pnl: float = 0.0
    win_rate: float = 0.0
    
    # 最後更新時間
    last_update: datetime = field(default_factory=datetime.now)
    
    def reset_daily_stats(self) -> None:
        """重置每日統計
        
        在每天開始時調用，重置當日的交易次數和損益。
        """
        self.trades_today = 0
        self.pnl_today = 0.0
        self.last_update = datetime.now()
    
    def update_from_trade(self, trade) -> None:
        """從交易記錄更新狀態
        
        Args:
            trade: Trade 對象
        """
        # 更新今日統計
        self.trades_today += 1
        self.pnl_today += trade.pnl
        
        # 更新累計統計
        self.total_trades += 1
        self.total_pnl += trade.pnl
        
        # 更新連續虧損
        if trade.pnl < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0
        
        # 更新勝率
        if self.total_trades > 0:
            # 需要統計獲利交易數（這裡簡化處理，實際應該維護獲利交易計數）
            # 暫時不更新勝率，由外部系統計算
            pass
        
        self.last_update = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典
        
        Returns:
            Dict[str, Any]: 狀態字典
        """
        return {
            'strategy_id': self.strategy_id,
            'enabled': self.enabled,
            'current_position': self.current_position.to_dict() if self.current_position else None,
            'trades_today': self.trades_today,
            'pnl_today': self.pnl_today,
            'consecutive_losses': self.consecutive_losses,
            'total_trades': self.total_trades,
            'total_pnl': self.total_pnl,
            'win_rate': self.win_rate,
            'last_update': self.last_update.isoformat(),
        }
