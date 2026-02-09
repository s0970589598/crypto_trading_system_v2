"""
交易相關數據模型
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional
import uuid


@dataclass
class Signal:
    """交易信號"""
    strategy_id: str  # 策略 ID
    timestamp: datetime  # 時間戳
    symbol: str  # 交易對
    action: str  # 'BUY', 'SELL', 'HOLD'
    direction: Optional[str]  # 'long', 'short', None
    entry_price: float  # 進場價格
    stop_loss: float  # 止損價格
    take_profit: float  # 目標價格
    position_size: float  # 倉位大小（幣數）
    confidence: float  # 信號置信度（0-1）
    metadata: Dict[str, Any] = field(default_factory=dict)  # 額外信息
    
    @classmethod
    def hold(cls, strategy_id: str, timestamp: datetime, symbol: str) -> 'Signal':
        """創建持有信號
        
        Args:
            strategy_id: 策略ID
            timestamp: 時間戳
            symbol: 交易對
            
        Returns:
            Signal: 持有信號
        """
        return cls(
            strategy_id=strategy_id,
            timestamp=timestamp,
            symbol=symbol,
            action='HOLD',
            direction=None,
            entry_price=0.0,
            stop_loss=0.0,
            take_profit=0.0,
            position_size=0.0,
            confidence=0.0,
            metadata={}
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            'strategy_id': self.strategy_id,
            'timestamp': self.timestamp.isoformat(),
            'symbol': self.symbol,
            'action': self.action,
            'direction': self.direction,
            'entry_price': self.entry_price,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'position_size': self.position_size,
            'confidence': self.confidence,
            'metadata': self.metadata,
        }


@dataclass
class Position:
    """持倉"""
    strategy_id: str  # 策略 ID
    symbol: str  # 交易對
    direction: str  # 'long' or 'short'
    entry_time: datetime  # 進場時間
    entry_price: float  # 進場價格
    size: float  # 倉位大小（幣數）
    stop_loss: float  # 止損價格
    take_profit: float  # 目標價格
    leverage: int  # 槓桿倍數
    unrealized_pnl: float = 0.0  # 未實現損益
    
    def update_pnl(self, current_price: float) -> float:
        """更新未實現損益
        
        Args:
            current_price: 當前價格
            
        Returns:
            float: 未實現損益
        """
        if self.direction == 'long':
            # 做多：(當前價 - 進場價) * 倉位大小
            self.unrealized_pnl = (current_price - self.entry_price) * self.size
        elif self.direction == 'short':
            # 做空：(進場價 - 當前價) * 倉位大小
            self.unrealized_pnl = (self.entry_price - current_price) * self.size
        else:
            self.unrealized_pnl = 0.0
        
        return self.unrealized_pnl
    
    def get_pnl_percentage(self, current_price: float) -> float:
        """獲取損益百分比
        
        Args:
            current_price: 當前價格
            
        Returns:
            float: 損益百分比
        """
        if self.direction == 'long':
            return ((current_price / self.entry_price) - 1) * 100
        elif self.direction == 'short':
            return ((self.entry_price / current_price) - 1) * 100
        return 0.0
    
    def should_stop_loss(self, current_price: float) -> bool:
        """判斷是否應該止損
        
        Args:
            current_price: 當前價格
            
        Returns:
            bool: 是否應該止損
        """
        if self.direction == 'long':
            return current_price <= self.stop_loss
        elif self.direction == 'short':
            return current_price >= self.stop_loss
        return False
    
    def should_take_profit(self, current_price: float) -> bool:
        """判斷是否應該獲利了結
        
        Args:
            current_price: 當前價格
            
        Returns:
            bool: 是否應該獲利
        """
        if self.direction == 'long':
            return current_price >= self.take_profit
        elif self.direction == 'short':
            return current_price <= self.take_profit
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            'strategy_id': self.strategy_id,
            'symbol': self.symbol,
            'direction': self.direction,
            'entry_time': self.entry_time.isoformat(),
            'entry_price': self.entry_price,
            'size': self.size,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'leverage': self.leverage,
            'unrealized_pnl': self.unrealized_pnl,
        }


@dataclass
class Trade:
    """交易記錄"""
    trade_id: str = field(default_factory=lambda: str(uuid.uuid4()))  # 交易 ID
    strategy_id: str = ""  # 策略 ID
    symbol: str = ""  # 交易對
    direction: str = ""  # 'long' or 'short'
    entry_time: datetime = field(default_factory=datetime.now)  # 進場時間
    exit_time: datetime = field(default_factory=datetime.now)  # 出場時間
    entry_price: float = 0.0  # 進場價格
    exit_price: float = 0.0  # 出場價格
    size: float = 0.0  # 倉位大小（幣數）
    leverage: int = 1  # 槓桿倍數
    pnl: float = 0.0  # 淨損益（扣除手續費）
    pnl_pct: float = 0.0  # 損益百分比
    commission: float = 0.0  # 手續費
    exit_reason: str = ""  # '止損', '獲利', '手動平倉'
    metadata: Dict[str, Any] = field(default_factory=dict)  # 額外信息
    
    def calculate_pnl(self, commission_rate: float = 0.0005) -> None:
        """計算損益
        
        Args:
            commission_rate: 手續費率（默認 0.05%）
        """
        # 計算原始損益
        if self.direction == 'long':
            raw_pnl = (self.exit_price - self.entry_price) * self.size
            self.pnl_pct = ((self.exit_price / self.entry_price) - 1) * 100
        elif self.direction == 'short':
            raw_pnl = (self.entry_price - self.exit_price) * self.size
            self.pnl_pct = ((self.entry_price / self.exit_price) - 1) * 100
        else:
            raw_pnl = 0.0
            self.pnl_pct = 0.0
        
        # 計算手續費（進場 + 出場）
        self.commission = (self.entry_price + self.exit_price) * self.size * commission_rate
        
        # 淨損益
        self.pnl = raw_pnl - self.commission
    
    def is_winning(self) -> bool:
        """是否為獲利交易"""
        return self.pnl > 0
    
    def get_duration_seconds(self) -> float:
        """獲取交易持續時間（秒）"""
        return (self.exit_time - self.entry_time).total_seconds()
    
    def get_duration_hours(self) -> float:
        """獲取交易持續時間（小時）"""
        return self.get_duration_seconds() / 3600
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            'trade_id': self.trade_id,
            'strategy_id': self.strategy_id,
            'symbol': self.symbol,
            'direction': self.direction,
            'entry_time': self.entry_time.isoformat(),
            'exit_time': self.exit_time.isoformat(),
            'entry_price': self.entry_price,
            'exit_price': self.exit_price,
            'size': self.size,
            'leverage': self.leverage,
            'pnl': self.pnl,
            'pnl_pct': self.pnl_pct,
            'commission': self.commission,
            'exit_reason': self.exit_reason,
            'metadata': self.metadata,
        }
