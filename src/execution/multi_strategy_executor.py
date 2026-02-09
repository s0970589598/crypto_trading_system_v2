"""
多策略執行引擎

管理多個策略實例，協調策略管理器和風險管理器，處理信號生成和執行。
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging

from src.execution.strategy import Strategy
from src.managers.strategy_manager import StrategyManager
from src.managers.risk_manager import RiskManager
from src.models.market_data import MarketData
from src.models.trading import Signal, Position, Trade
from src.models.state import StrategyState


logger = logging.getLogger(__name__)


class MultiStrategyExecutor:
    """
    多策略執行引擎
    
    負責：
    1. 管理多個策略實例
    2. 協調 StrategyManager 和 RiskManager
    3. 處理信號生成和執行
    4. 維護策略隔離
    5. 處理信號衝突
    """
    
    def __init__(
        self,
        strategy_manager: StrategyManager,
        risk_manager: RiskManager,
        capital_allocation: Optional[Dict[str, float]] = None
    ):
        """
        初始化多策略執行引擎
        
        Args:
            strategy_manager: 策略管理器
            risk_manager: 風險管理器
            capital_allocation: 資金分配（策略 ID -> 比例），如果為 None 則平均分配
        """
        self.strategy_manager = strategy_manager
        self.risk_manager = risk_manager
        
        # 策略實例
        self.strategies: Dict[str, Strategy] = {}
        
        # 策略狀態
        self.strategy_states: Dict[str, StrategyState] = {}
        
        # 當前持倉
        self.positions: Dict[str, Optional[Position]] = {}
        
        # 交易歷史
        self.trade_history: Dict[str, List[Trade]] = {}
        
        # 資金分配
        self.capital_allocation = capital_allocation or {}
        
        # 信號優先級（策略 ID -> 優先級，數字越小優先級越高）
        self.signal_priority: Dict[str, int] = {}
        
        logger.info("MultiStrategyExecutor 初始化完成")
    
    def add_strategy(self, strategy: Strategy, priority: int = 100) -> None:
        """
        添加策略
        
        Args:
            strategy: 策略實例
            priority: 信號優先級（數字越小優先級越高）
        """
        strategy_id = strategy.config.strategy_id
        
        if strategy_id in self.strategies:
            logger.warning(f"策略 {strategy_id} 已存在，將被覆蓋")
        
        self.strategies[strategy_id] = strategy
        self.signal_priority[strategy_id] = priority
        
        # 初始化策略狀態
        self.strategy_states[strategy_id] = StrategyState(
            strategy_id=strategy_id,
            enabled=strategy.config.enabled,
            current_position=None,
            trades_today=0,
            pnl_today=0.0,
            consecutive_losses=0,
            total_trades=0,
            total_pnl=0.0,
            win_rate=0.0,
            last_update=datetime.now()
        )
        
        # 初始化持倉和交易歷史
        self.positions[strategy_id] = None
        self.trade_history[strategy_id] = []
        
        logger.info(f"添加策略：{strategy_id}，優先級：{priority}")
    
    def remove_strategy(self, strategy_id: str) -> bool:
        """
        移除策略
        
        Args:
            strategy_id: 策略 ID
        
        Returns:
            bool: 是否成功
        """
        if strategy_id not in self.strategies:
            logger.warning(f"策略 {strategy_id} 不存在")
            return False
        
        # 檢查是否有持倉
        if self.positions.get(strategy_id) is not None:
            logger.error(f"策略 {strategy_id} 仍有持倉，無法移除")
            return False
        
        del self.strategies[strategy_id]
        del self.strategy_states[strategy_id]
        del self.positions[strategy_id]
        del self.signal_priority[strategy_id]
        
        logger.info(f"移除策略：{strategy_id}")
        return True
    
    def get_strategy_capital(self, strategy_id: str) -> float:
        """
        獲取策略分配的資金
        
        Args:
            strategy_id: 策略 ID
        
        Returns:
            float: 分配的資金
        """
        if strategy_id not in self.strategies:
            return 0.0
        
        # 如果有明確的資金分配，使用配置的比例
        if strategy_id in self.capital_allocation:
            allocation = self.capital_allocation[strategy_id]
        else:
            # 否則平均分配
            n_strategies = len(self.strategies)
            allocation = 1.0 / n_strategies if n_strategies > 0 else 0.0
        
        # 獲取全局可用資金
        total_capital = self.risk_manager.global_state.current_capital
        
        return total_capital * allocation
    
    def generate_signals(self, market_data: MarketData) -> List[Signal]:
        """
        為所有啟用的策略生成信號
        
        Args:
            market_data: 市場數據
        
        Returns:
            List[Signal]: 信號列表
        """
        signals = []
        
        for strategy_id, strategy in self.strategies.items():
            # 檢查策略是否啟用
            state = self.strategy_states[strategy_id]
            if not state.enabled:
                logger.debug(f"策略 {strategy_id} 未啟用，跳過")
                continue
            
            try:
                # 生成信號
                signal = strategy.generate_signal(market_data)
                
                # 如果不是 HOLD 信號，添加到列表
                if signal.action != 'HOLD':
                    signals.append(signal)
                    logger.info(f"策略 {strategy_id} 生成信號：{signal.action} {signal.direction}")
            
            except Exception as e:
                logger.error(f"策略 {strategy_id} 生成信號時出錯：{e}", exc_info=True)
                # 策略錯誤不影響其他策略
                continue
        
        return signals
    
    def filter_signals(self, signals: List[Signal]) -> List[Signal]:
        """
        過濾和排序信號
        
        處理信號衝突，根據優先級和風險限制過濾信號。
        
        Args:
            signals: 原始信號列表
        
        Returns:
            List[Signal]: 過濾後的信號列表
        """
        if not signals:
            return []
        
        # 1. 檢查全局風險限制
        should_halt, halt_reason = self.risk_manager.should_halt_trading()
        if should_halt:
            logger.warning(f"全局風險限制觸發，暫停所有交易：{halt_reason}")
            return []
        
        # 2. 按優先級排序
        sorted_signals = sorted(
            signals,
            key=lambda s: self.signal_priority.get(s.strategy_id, 999)
        )
        
        # 3. 檢查每個信號的風險限制
        filtered_signals = []
        
        for signal in sorted_signals:
            # 檢查策略級風險
            strategy_state = self.strategy_states.get(signal.strategy_id)
            if strategy_state is None:
                logger.warning(f"找不到策略 {signal.strategy_id} 的狀態")
                continue
            
            passed, reason = self.risk_manager.check_strategy_risk(
                signal.strategy_id,
                signal,
                strategy_state
            )
            
            if not passed:
                logger.warning(f"策略 {signal.strategy_id} 風險檢查未通過：{reason}")
                continue
            
            # 檢查是否會超過全局倉位限制
            # 計算當前總倉位
            current_total_position = sum(
                pos.size * pos.entry_price
                for pos in self.positions.values()
                if pos is not None
            )
            
            # 計算新信號的倉位價值
            strategy_capital = self.get_strategy_capital(signal.strategy_id)
            strategy = self.strategies.get(signal.strategy_id)
            if strategy is None:
                logger.warning(f"找不到策略 {signal.strategy_id}")
                continue
            
            # 使用策略的 calculate_position_size 方法計算實際倉位
            position_size = strategy.calculate_position_size(strategy_capital, signal.entry_price)
            new_position_value = position_size * signal.entry_price
            
            # 檢查是否超過全局限制
            total_capital = self.risk_manager.global_state.current_capital
            max_global_position = total_capital * self.risk_manager.config.global_max_position
            
            if current_total_position + new_position_value > max_global_position:
                logger.warning(
                    f"策略 {signal.strategy_id} 信號會超過全局倉位限制 "
                    f"({current_total_position + new_position_value:.2f} > {max_global_position:.2f})"
                )
                continue
            
            filtered_signals.append(signal)
        
        return filtered_signals
    
    def execute_signal(self, signal: Signal, market_data: MarketData) -> Optional[Position]:
        """
        執行信號
        
        Args:
            signal: 交易信號
            market_data: 市場數據
        
        Returns:
            Optional[Position]: 創建的持倉，如果執行失敗則返回 None
        """
        strategy_id = signal.strategy_id
        
        # 檢查是否已有持倉
        if self.positions.get(strategy_id) is not None:
            logger.warning(f"策略 {strategy_id} 已有持倉，無法執行新信號")
            return None
        
        # 獲取策略資金
        strategy_capital = self.get_strategy_capital(strategy_id)
        
        # 計算倉位大小
        strategy = self.strategies[strategy_id]
        position_size = strategy.calculate_position_size(strategy_capital, signal.entry_price)
        
        # 創建持倉
        position = Position(
            strategy_id=strategy_id,
            symbol=signal.symbol,
            direction=signal.direction,
            entry_time=signal.timestamp,
            entry_price=signal.entry_price,
            size=position_size,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            leverage=strategy.config.risk_management.leverage,
            unrealized_pnl=0.0
        )
        
        # 保存持倉
        self.positions[strategy_id] = position
        
        # 更新風險管理器
        position_value = position.size * position.entry_price
        self.risk_manager.add_position(strategy_id, position_value)
        
        logger.info(
            f"執行信號：策略 {strategy_id}，{signal.action} {signal.direction}，"
            f"價格 {signal.entry_price:.2f}，大小 {position_size:.4f}"
        )
        
        return position
    
    def check_exits(self, market_data: MarketData) -> List[Trade]:
        """
        檢查所有持倉是否需要出場
        
        Args:
            market_data: 市場數據
        
        Returns:
            List[Trade]: 完成的交易列表
        """
        trades = []
        
        for strategy_id, position in list(self.positions.items()):
            if position is None:
                continue
            
            strategy = self.strategies[strategy_id]
            
            # 檢查是否應該出場
            should_exit = strategy.should_exit(position, market_data)
            
            if should_exit:
                trade = self._close_position(strategy_id, market_data, "策略出場")
                if trade:
                    trades.append(trade)
        
        return trades
    
    def _close_position(
        self,
        strategy_id: str,
        market_data: MarketData,
        exit_reason: str
    ) -> Optional[Trade]:
        """
        平倉
        
        Args:
            strategy_id: 策略 ID
            market_data: 市場數據
            exit_reason: 出場原因
        
        Returns:
            Optional[Trade]: 交易記錄
        """
        position = self.positions.get(strategy_id)
        if position is None:
            return None
        
        # 獲取當前價格
        timeframe = self.strategies[strategy_id].config.timeframes[0]
        tf_data = market_data.get_timeframe(timeframe)
        exit_price = tf_data.get_latest()['close']
        
        # 計算損益
        if position.direction == 'long':
            pnl = (exit_price - position.entry_price) * position.size * position.leverage
        else:
            pnl = (position.entry_price - exit_price) * position.size * position.leverage
        
        # 扣除手續費（假設 0.05%）
        commission = (position.entry_price + exit_price) * position.size * 0.0005
        pnl -= commission
        
        # 計算損益百分比
        position_value = position.entry_price * position.size
        pnl_pct = pnl / position_value if position_value > 0 else 0.0
        
        # 創建交易記錄
        trade = Trade(
            trade_id=f"{strategy_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            strategy_id=strategy_id,
            symbol=position.symbol,
            direction=position.direction,
            entry_time=position.entry_time,
            exit_time=market_data.timestamp,
            entry_price=position.entry_price,
            exit_price=exit_price,
            size=position.size,
            leverage=position.leverage,
            pnl=pnl,
            pnl_pct=pnl_pct,
            commission=commission,
            exit_reason=exit_reason,
            metadata={}
        )
        
        # 保存交易記錄
        self.trade_history[strategy_id].append(trade)
        
        # 更新策略狀態
        state = self.strategy_states[strategy_id]
        state.total_trades += 1
        state.trades_today += 1
        state.total_pnl += pnl
        state.pnl_today += pnl
        
        if pnl > 0:
            state.consecutive_losses = 0
        else:
            state.consecutive_losses += 1
        
        # 更新勝率
        winning_trades = sum(1 for t in self.trade_history[strategy_id] if t.pnl > 0)
        state.win_rate = winning_trades / state.total_trades if state.total_trades > 0 else 0.0
        
        state.last_update = datetime.now()
        
        # 清除持倉
        self.positions[strategy_id] = None
        
        # 更新風險管理器
        position_value = position.size * position.entry_price
        self.risk_manager.remove_position(strategy_id, position_value)
        self.risk_manager.global_state.update_capital(
            self.risk_manager.global_state.current_capital + pnl
        )
        
        logger.info(
            f"平倉：策略 {strategy_id}，{exit_reason}，"
            f"損益 {pnl:.2f} ({pnl_pct:.2%})"
        )
        
        return trade
    
    def get_strategy_state(self, strategy_id: str) -> Optional[StrategyState]:
        """
        獲取策略狀態
        
        Args:
            strategy_id: 策略 ID
        
        Returns:
            Optional[StrategyState]: 策略狀態
        """
        return self.strategy_states.get(strategy_id)
    
    def get_all_states(self) -> Dict[str, StrategyState]:
        """
        獲取所有策略狀態
        
        Returns:
            Dict[str, StrategyState]: 策略 ID -> 狀態
        """
        return self.strategy_states.copy()
    
    def get_trade_history(self, strategy_id: Optional[str] = None) -> List[Trade]:
        """
        獲取交易歷史
        
        Args:
            strategy_id: 策略 ID，如果為 None 則返回所有策略的交易
        
        Returns:
            List[Trade]: 交易列表
        """
        if strategy_id is not None:
            return self.trade_history.get(strategy_id, []).copy()
        
        # 返回所有策略的交易
        all_trades = []
        for trades in self.trade_history.values():
            all_trades.extend(trades)
        
        # 按時間排序
        all_trades.sort(key=lambda t: t.entry_time)
        
        return all_trades
    
    def reset_daily_stats(self) -> None:
        """重置所有策略的每日統計"""
        for state in self.strategy_states.values():
            state.reset_daily_stats()
        
        logger.info("重置每日統計")
