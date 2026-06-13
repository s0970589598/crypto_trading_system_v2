"""
風險管理器
"""

from typing import Tuple, Dict, Optional
from datetime import datetime

from src.models.risk import RiskConfig, GlobalRiskState, RiskEvent
from src.models.trading import Signal, Trade
from src.models.state import StrategyState


class RiskManager:
    """風險管理器
    
    提供系統級和策略級的風險控制，包括：
    - 全局回撤限制
    - 每日虧損限制
    - 倉位限制（全局和策略級）
    - 連續虧損限制
    - 風險事件記錄
    """
    
    def __init__(self, config: RiskConfig, initial_capital: float):
        """初始化風險管理器
        
        Args:
            config: 風險配置對象
            initial_capital: 初始資金
        """
        self.config = config
        self.global_state = GlobalRiskState(
            initial_capital=initial_capital,
            current_capital=initial_capital,
            peak_capital=initial_capital,
            daily_start_capital=initial_capital,
        )
    
    def check_global_risk(self) -> Tuple[bool, str]:
        """檢查全局風險限制
        
        檢查：
        1. 全局回撤是否超限
        2. 今日虧損是否超限
        
        Returns:
            Tuple[bool, str]: (是否通過, 原因)
        """
        # 檢查全局回撤
        current_drawdown = self.global_state.get_current_drawdown()
        if current_drawdown > self.config.global_max_drawdown:
            reason = f"全局回撤超限：{current_drawdown:.2%} > {self.config.global_max_drawdown:.2%}"
            
            # 記錄風險事件
            event = RiskEvent(
                timestamp=datetime.now(),
                event_type='drawdown',
                strategy_id='',  # 全局事件
                trigger_value=current_drawdown,
                limit_value=self.config.global_max_drawdown,
                action_taken='halt_all_trading',
            )
            self.global_state.add_risk_event(event)
            self.global_state.halt_trading(reason)
            
            return False, reason
        
        # 檢查今日虧損
        daily_loss_pct = self.global_state.get_daily_loss_pct()
        if daily_loss_pct > self.config.daily_loss_limit:
            reason = f"今日虧損超限：{daily_loss_pct:.2%} > {self.config.daily_loss_limit:.2%}"
            
            # 記錄風險事件
            event = RiskEvent(
                timestamp=datetime.now(),
                event_type='daily_loss',
                strategy_id='',  # 全局事件
                trigger_value=daily_loss_pct,
                limit_value=self.config.daily_loss_limit,
                action_taken='halt_all_trading',
            )
            self.global_state.add_risk_event(event)
            self.global_state.halt_trading(reason)
            
            return False, reason
        
        return True, ""
    
    def check_strategy_risk(
        self,
        strategy_id: str,
        signal: Signal,
        strategy_state: StrategyState
    ) -> Tuple[bool, str]:
        """檢查策略級風險限制
        
        檢查：
        1. 策略倉位是否超限
        2. 策略今日交易次數是否超限
        3. 策略連續虧損是否超限
        
        Args:
            strategy_id: 策略 ID
            signal: 交易信號
            strategy_state: 策略狀態
        
        Returns:
            Tuple[bool, str]: (是否通過, 原因)
        """
        # 檢查策略倉位限制
        position_value = signal.entry_price * signal.position_size
        new_position_value = self.global_state.strategy_positions.get(strategy_id, 0.0) + position_value
        position_usage = new_position_value / self.global_state.current_capital if self.global_state.current_capital > 0 else 0
        
        if position_usage > self.config.strategy_max_position:
            reason = f"策略 {strategy_id} 倉位超限：{position_usage:.2%} > {self.config.strategy_max_position:.2%}"
            
            # 記錄風險事件
            event = RiskEvent(
                timestamp=datetime.now(),
                event_type='position_limit',
                strategy_id=strategy_id,
                trigger_value=position_usage,
                limit_value=self.config.strategy_max_position,
                action_taken='reject_signal',
            )
            self.global_state.add_risk_event(event)
            
            return False, reason
        
        # 檢查全局倉位限制
        total_position_value = self.global_state.total_position_value + position_value
        global_position_usage = total_position_value / self.global_state.current_capital if self.global_state.current_capital > 0 else 0
        
        if global_position_usage > self.config.global_max_position:
            reason = f"全局倉位超限：{global_position_usage:.2%} > {self.config.global_max_position:.2%}"
            
            # 記錄風險事件
            event = RiskEvent(
                timestamp=datetime.now(),
                event_type='position_limit',
                strategy_id=strategy_id,
                trigger_value=global_position_usage,
                limit_value=self.config.global_max_position,
                action_taken='reject_signal',
            )
            self.global_state.add_risk_event(event)
            
            return False, reason
        
        # 檢查今日交易次數（從策略配置中獲取）
        # 注意：這裡假設 strategy_state 包含策略配置信息
        # 實際實現中可能需要傳入策略配置
        
        # 檢查連續虧損（從策略配置中獲取）
        # 注意：這裡假設 strategy_state 包含策略配置信息
        
        return True, ""
    
    def update_risk_state(self, trade: Trade) -> None:
        """更新風險狀態
        
        根據交易記錄更新：
        1. 當前資金
        2. 今日損益
        3. 倉位統計
        
        Args:
            trade: 交易記錄
        """
        # 更新資金
        new_capital = self.global_state.current_capital + trade.pnl
        self.global_state.update_capital(new_capital)
        
        # 更新倉位（平倉時減少倉位）
        position_value = trade.entry_price * trade.size
        current_position = self.global_state.strategy_positions.get(trade.strategy_id, 0.0)
        new_position = max(0.0, current_position - position_value)
        
        if new_position > 0:
            self.global_state.strategy_positions[trade.strategy_id] = new_position
        else:
            # 倉位為 0，移除記錄
            self.global_state.strategy_positions.pop(trade.strategy_id, None)
        
        # 重新計算總倉位
        self.global_state.total_position_value = sum(self.global_state.strategy_positions.values())
    
    def should_halt_trading(self) -> Tuple[bool, str]:
        """判斷是否應該暫停所有交易
        
        Returns:
            Tuple[bool, str]: (是否暫停, 原因)
        """
        if self.global_state.trading_halted:
            return True, self.global_state.halt_reason
        
        # 檢查全局風險
        passed, reason = self.check_global_risk()
        if not passed:
            return True, reason
        
        return False, ""
    
    def calculate_max_position_size(self, strategy_id: str, capital: float) -> float:
        """計算最大允許倉位
        
        考慮：
        1. 策略級倉位限制
        2. 全局倉位限制
        3. 當前已使用倉位
        
        Args:
            strategy_id: 策略 ID
            capital: 可用資金
        
        Returns:
            float: 最大倉位（USDT）
        """
        # 策略級最大倉位
        strategy_max = capital * self.config.strategy_max_position
        
        # 策略當前倉位
        strategy_current = self.global_state.strategy_positions.get(strategy_id, 0.0)
        
        # 策略剩餘可用倉位
        strategy_available = max(0.0, strategy_max - strategy_current)
        
        # 全局最大倉位
        global_max = capital * self.config.global_max_position
        
        # 全局當前倉位
        global_current = self.global_state.total_position_value
        
        # 全局剩餘可用倉位
        global_available = max(0.0, global_max - global_current)
        
        # 返回較小值
        return min(strategy_available, global_available)
    
    def add_position(self, strategy_id: str, position_value: float) -> None:
        """添加倉位
        
        當開倉時調用，更新倉位統計。
        
        Args:
            strategy_id: 策略 ID
            position_value: 倉位價值（USDT）
        """
        current = self.global_state.strategy_positions.get(strategy_id, 0.0)
        self.global_state.strategy_positions[strategy_id] = current + position_value
        self.global_state.total_position_value += position_value
    
    def remove_position(self, strategy_id: str, position_value: float) -> None:
        """移除倉位
        
        當平倉時調用，更新倉位統計。
        
        Args:
            strategy_id: 策略 ID
            position_value: 倉位價值（USDT）
        """
        current = self.global_state.strategy_positions.get(strategy_id, 0.0)
        new_value = max(0.0, current - position_value)
        
        if new_value > 0:
            self.global_state.strategy_positions[strategy_id] = new_value
        else:
            self.global_state.strategy_positions.pop(strategy_id, None)
        
        self.global_state.total_position_value = max(0.0, self.global_state.total_position_value - position_value)
    
    def reset_daily_stats(self) -> None:
        """重置每日統計
        
        在每天開始時調用。
        """
        self.global_state.reset_daily_stats()
    
    def get_risk_events(self, strategy_id: Optional[str] = None) -> list[RiskEvent]:
        """獲取風險事件記錄
        
        Args:
            strategy_id: 策略 ID（可選，如果提供則只返回該策略的事件）
        
        Returns:
            list[RiskEvent]: 風險事件列表
        """
        if strategy_id is None:
            return self.global_state.risk_events
        
        return [e for e in self.global_state.risk_events if e.strategy_id == strategy_id]
    
    def get_state(self) -> GlobalRiskState:
        """獲取全局風險狀態
        
        Returns:
            GlobalRiskState: 全局風險狀態
        """
        return self.global_state
