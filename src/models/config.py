"""
策略配置數據模型
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Tuple, Optional
import json
from pathlib import Path


@dataclass
class RiskManagement:
    """風險管理配置"""
    position_size: float  # 倉位比例（0-1）
    leverage: int  # 槓桿倍數
    max_trades_per_day: int  # 每日最大交易次數
    max_consecutive_losses: int  # 最大連續虧損次數
    daily_loss_limit: float  # 每日虧損限制（比例）
    stop_loss_atr: float  # 止損 ATR 倍數
    take_profit_atr: float  # 目標 ATR 倍數

    def validate(self) -> Tuple[bool, str]:
        """驗證風險管理配置"""
        if not 0 < self.position_size <= 1:
            return False, f"position_size 必須在 (0, 1] 範圍內，當前值：{self.position_size}"
        
        if self.leverage < 1:
            return False, f"leverage 必須 >= 1，當前值：{self.leverage}"
        
        if self.max_trades_per_day < 1:
            return False, f"max_trades_per_day 必須 >= 1，當前值：{self.max_trades_per_day}"
        
        if self.max_consecutive_losses < 1:
            return False, f"max_consecutive_losses 必須 >= 1，當前值：{self.max_consecutive_losses}"
        
        if not 0 < self.daily_loss_limit <= 1:
            return False, f"daily_loss_limit 必須在 (0, 1] 範圍內，當前值：{self.daily_loss_limit}"
        
        if self.stop_loss_atr <= 0:
            return False, f"stop_loss_atr 必須 > 0，當前值：{self.stop_loss_atr}"
        
        if self.take_profit_atr <= 0:
            return False, f"take_profit_atr 必須 > 0，當前值：{self.take_profit_atr}"
        
        return True, ""


@dataclass
class ExitConditions:
    """出場條件"""
    stop_loss: str  # 止損公式
    take_profit: str  # 目標公式


@dataclass
class NotificationConfig:
    """通知配置"""
    telegram: bool = False
    email: bool = False
    webhook: Optional[str] = None


@dataclass
class StrategyConfig:
    """策略配置"""
    strategy_id: str
    strategy_name: str
    version: str
    enabled: bool
    symbol: str
    timeframes: List[str]
    
    # 策略參數
    parameters: Dict[str, Any]
    
    # 風險管理
    risk_management: RiskManagement
    
    # 進場條件（表達式列表）
    entry_conditions: List[str]
    
    # 出場條件
    exit_conditions: ExitConditions
    
    # 通知設置
    notifications: NotificationConfig = field(default_factory=NotificationConfig)
    
    @classmethod
    def from_json(cls, json_path: str) -> 'StrategyConfig':
        """從 JSON 文件載入配置
        
        Args:
            json_path: JSON 配置文件路徑
            
        Returns:
            StrategyConfig: 策略配置對象
            
        Raises:
            FileNotFoundError: 文件不存在
            json.JSONDecodeError: JSON 格式錯誤
            ValueError: 配置格式錯誤
        """
        path = Path(json_path)
        
        if not path.exists():
            raise FileNotFoundError(f"配置文件不存在：{json_path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 解析風險管理配置
        risk_data = data.get('risk_management', {})
        risk_management = RiskManagement(
            position_size=risk_data.get('position_size', 0.2),
            leverage=risk_data.get('leverage', 5),
            max_trades_per_day=risk_data.get('max_trades_per_day', 3),
            max_consecutive_losses=risk_data.get('max_consecutive_losses', 3),
            daily_loss_limit=risk_data.get('daily_loss_limit', 0.1),
            stop_loss_atr=risk_data.get('stop_loss_atr', 1.5),
            take_profit_atr=risk_data.get('take_profit_atr', 3.0),
        )
        
        # 解析出場條件
        exit_data = data.get('exit_conditions', {})
        exit_conditions = ExitConditions(
            stop_loss=exit_data.get('stop_loss', ''),
            take_profit=exit_data.get('take_profit', ''),
        )
        
        # 解析通知配置
        notif_data = data.get('notifications', {})
        notifications = NotificationConfig(
            telegram=notif_data.get('telegram', False),
            email=notif_data.get('email', False),
            webhook=notif_data.get('webhook'),
        )
        
        return cls(
            strategy_id=data['strategy_id'],
            strategy_name=data['strategy_name'],
            version=data['version'],
            enabled=data.get('enabled', True),
            symbol=data['symbol'],
            timeframes=data['timeframes'],
            parameters=data.get('parameters', {}),
            risk_management=risk_management,
            entry_conditions=data.get('entry_conditions', []),
            exit_conditions=exit_conditions,
            notifications=notifications,
        )
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StrategyConfig':
        """從字典創建配置
        
        Args:
            data: 配置字典
            
        Returns:
            StrategyConfig: 策略配置對象
            
        Raises:
            ValueError: 配置格式錯誤
        """
        # 解析風險管理配置
        risk_data = data.get('risk_management', {})
        risk_management = RiskManagement(
            position_size=risk_data.get('position_size', 0.2),
            leverage=risk_data.get('leverage', 5),
            max_trades_per_day=risk_data.get('max_trades_per_day', 3),
            max_consecutive_losses=risk_data.get('max_consecutive_losses', 3),
            daily_loss_limit=risk_data.get('daily_loss_limit', 0.1),
            stop_loss_atr=risk_data.get('stop_loss_atr', 1.5),
            take_profit_atr=risk_data.get('take_profit_atr', 3.0),
        )
        
        # 解析出場條件
        exit_data = data.get('exit_conditions', {})
        exit_conditions = ExitConditions(
            stop_loss=exit_data.get('stop_loss', ''),
            take_profit=exit_data.get('take_profit', ''),
        )
        
        # 解析通知配置
        notif_data = data.get('notifications', {})
        notifications = NotificationConfig(
            telegram=notif_data.get('telegram', False),
            email=notif_data.get('email', False),
            webhook=notif_data.get('webhook'),
        )
        
        return cls(
            strategy_id=data['strategy_id'],
            strategy_name=data['strategy_name'],
            version=data['version'],
            enabled=data.get('enabled', True),
            symbol=data['symbol'],
            timeframes=data['timeframes'],
            parameters=data.get('parameters', {}),
            risk_management=risk_management,
            entry_conditions=data.get('entry_conditions', []),
            exit_conditions=exit_conditions,
            notifications=notifications,
        )
    
    def validate(self) -> Tuple[bool, str]:
        """驗證配置有效性
        
        Returns:
            Tuple[bool, str]: (是否有效, 錯誤訊息)
        """
        # 驗證必需字段
        if not self.strategy_id:
            return False, "strategy_id 不能為空"
        
        if not self.strategy_name:
            return False, "strategy_name 不能為空"
        
        if not self.version:
            return False, "version 不能為空"
        
        if not self.symbol:
            return False, "symbol 不能為空"
        
        if not self.timeframes:
            return False, "timeframes 不能為空"
        
        # 驗證週期格式
        valid_timeframes = ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d', '3d', '1w', '1M']
        for tf in self.timeframes:
            if tf not in valid_timeframes:
                return False, f"無效的時間週期：{tf}，有效值：{valid_timeframes}"
        
        # 驗證風險管理配置
        risk_valid, risk_msg = self.risk_management.validate()
        if not risk_valid:
            return False, f"風險管理配置錯誤：{risk_msg}"
        
        return True, ""
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典
        
        Returns:
            Dict[str, Any]: 配置字典
        """
        return {
            'strategy_id': self.strategy_id,
            'strategy_name': self.strategy_name,
            'version': self.version,
            'enabled': self.enabled,
            'symbol': self.symbol,
            'timeframes': self.timeframes,
            'parameters': self.parameters,
            'risk_management': {
                'position_size': self.risk_management.position_size,
                'leverage': self.risk_management.leverage,
                'max_trades_per_day': self.risk_management.max_trades_per_day,
                'max_consecutive_losses': self.risk_management.max_consecutive_losses,
                'daily_loss_limit': self.risk_management.daily_loss_limit,
                'stop_loss_atr': self.risk_management.stop_loss_atr,
                'take_profit_atr': self.risk_management.take_profit_atr,
            },
            'entry_conditions': self.entry_conditions,
            'exit_conditions': {
                'stop_loss': self.exit_conditions.stop_loss,
                'take_profit': self.exit_conditions.take_profit,
            },
            'notifications': {
                'telegram': self.notifications.telegram,
                'email': self.notifications.email,
                'webhook': self.notifications.webhook,
            },
        }
    
    def save(self, json_path: str) -> None:
        """保存配置到 JSON 文件
        
        Args:
            json_path: JSON 配置文件路徑
        """
        path = Path(json_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
