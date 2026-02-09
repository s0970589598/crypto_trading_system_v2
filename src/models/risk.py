"""
風險管理數據模型
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List


@dataclass
class RiskConfig:
    """風險配置"""
    # 全局風險限制
    global_max_drawdown: float = 0.20  # 全局最大回撤（20%）
    daily_loss_limit: float = 0.10  # 每日虧損限制（10%）
    global_max_position: float = 0.80  # 全局最大倉位（80% 總資金）
    
    # 策略級風險限制
    strategy_max_position: float = 0.30  # 單策略最大倉位（30% 總資金）
    
    def validate(self) -> tuple[bool, str]:
        """驗證風險配置
        
        Returns:
            tuple[bool, str]: (是否有效, 錯誤訊息)
        """
        if not 0 < self.global_max_drawdown <= 1:
            return False, f"global_max_drawdown 必須在 (0, 1] 範圍內，當前值：{self.global_max_drawdown}"
        
        if not 0 < self.daily_loss_limit <= 1:
            return False, f"daily_loss_limit 必須在 (0, 1] 範圍內，當前值：{self.daily_loss_limit}"
        
        if not 0 < self.global_max_position <= 1:
            return False, f"global_max_position 必須在 (0, 1] 範圍內，當前值：{self.global_max_position}"
        
        if not 0 < self.strategy_max_position <= 1:
            return False, f"strategy_max_position 必須在 (0, 1] 範圍內，當前值：{self.strategy_max_position}"
        
        if self.strategy_max_position > self.global_max_position:
            return False, f"strategy_max_position ({self.strategy_max_position}) 不能大於 global_max_position ({self.global_max_position})"
        
        return True, ""


@dataclass
class RiskEvent:
    """風險事件記錄"""
    timestamp: datetime
    event_type: str  # 'drawdown', 'daily_loss', 'position_limit', 'consecutive_loss'
    strategy_id: str  # 觸發的策略 ID（全局事件為空字符串）
    trigger_value: float  # 觸發值
    limit_value: float  # 限制值
    action_taken: str  # 採取的行動
    
    def to_dict(self) -> Dict:
        """轉換為字典"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'event_type': self.event_type,
            'strategy_id': self.strategy_id,
            'trigger_value': self.trigger_value,
            'limit_value': self.limit_value,
            'action_taken': self.action_taken,
        }


@dataclass
class GlobalRiskState:
    """全局風險狀態"""
    initial_capital: float  # 初始資金
    current_capital: float  # 當前資金
    peak_capital: float  # 峰值資金
    
    # 今日統計
    daily_start_capital: float  # 今日開始資金
    daily_pnl: float = 0.0  # 今日損益
    
    # 倉位統計
    total_position_value: float = 0.0  # 總倉位價值（USDT）
    strategy_positions: Dict[str, float] = field(default_factory=dict)  # 策略 ID -> 倉位價值
    
    # 風險事件記錄
    risk_events: List[RiskEvent] = field(default_factory=list)
    
    # 交易暫停狀態
    trading_halted: bool = False
    halt_reason: str = ""
    
    def __post_init__(self):
        """初始化後處理"""
        if self.peak_capital == 0:
            self.peak_capital = self.initial_capital
        if self.daily_start_capital == 0:
            self.daily_start_capital = self.initial_capital
    
    def get_current_drawdown(self) -> float:
        """獲取當前回撤
        
        Returns:
            float: 回撤比例（0-1）
        """
        if self.peak_capital == 0:
            return 0.0
        return max(0.0, (self.peak_capital - self.current_capital) / self.peak_capital)
    
    def get_daily_loss_pct(self) -> float:
        """獲取今日虧損百分比
        
        Returns:
            float: 虧損比例（0-1）
        """
        if self.daily_start_capital == 0:
            return 0.0
        return max(0.0, -self.daily_pnl / self.daily_start_capital)
    
    def get_position_usage(self) -> float:
        """獲取倉位使用率
        
        Returns:
            float: 倉位使用率（0-1）
        """
        if self.current_capital == 0:
            return 0.0
        return self.total_position_value / self.current_capital
    
    def get_strategy_position_usage(self, strategy_id: str) -> float:
        """獲取策略倉位使用率
        
        Args:
            strategy_id: 策略 ID
            
        Returns:
            float: 倉位使用率（0-1）
        """
        if self.current_capital == 0:
            return 0.0
        position_value = self.strategy_positions.get(strategy_id, 0.0)
        return position_value / self.current_capital
    
    def update_capital(self, new_capital: float) -> None:
        """更新資金
        
        Args:
            new_capital: 新的資金量
        """
        self.current_capital = new_capital
        
        # 更新峰值資金
        if new_capital > self.peak_capital:
            self.peak_capital = new_capital
        
        # 更新今日損益
        self.daily_pnl = new_capital - self.daily_start_capital
    
    def reset_daily_stats(self) -> None:
        """重置每日統計"""
        self.daily_start_capital = self.current_capital
        self.daily_pnl = 0.0
    
    def add_risk_event(self, event: RiskEvent) -> None:
        """添加風險事件
        
        Args:
            event: 風險事件
        """
        self.risk_events.append(event)
    
    def halt_trading(self, reason: str) -> None:
        """暫停交易
        
        Args:
            reason: 暫停原因
        """
        self.trading_halted = True
        self.halt_reason = reason
    
    def resume_trading(self) -> None:
        """恢復交易"""
        self.trading_halted = False
        self.halt_reason = ""
    
    def to_dict(self) -> Dict:
        """轉換為字典"""
        return {
            'initial_capital': self.initial_capital,
            'current_capital': self.current_capital,
            'peak_capital': self.peak_capital,
            'daily_start_capital': self.daily_start_capital,
            'daily_pnl': self.daily_pnl,
            'total_position_value': self.total_position_value,
            'strategy_positions': self.strategy_positions,
            'current_drawdown': self.get_current_drawdown(),
            'daily_loss_pct': self.get_daily_loss_pct(),
            'position_usage': self.get_position_usage(),
            'trading_halted': self.trading_halted,
            'halt_reason': self.halt_reason,
            'risk_events_count': len(self.risk_events),
        }
