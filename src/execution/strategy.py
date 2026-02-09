"""
策略基類和接口定義
"""

from abc import ABC, abstractmethod
from typing import Optional
from src.models.config import StrategyConfig
from src.models.market_data import MarketData
from src.models.trading import Signal, Position


class Strategy(ABC):
    """策略抽象基類
    
    所有交易策略必須繼承此類並實現所有抽象方法。
    這確保了所有策略都有統一的接口，可以被系統統一管理和執行。
    """
    
    def __init__(self, config: StrategyConfig):
        """初始化策略
        
        Args:
            config: 策略配置對象，包含策略參數、風險管理設置等
        """
        self.config = config
        self.strategy_id = config.strategy_id
        self.strategy_name = config.strategy_name
        self.symbol = config.symbol
        self.timeframes = config.timeframes
        self.parameters = config.parameters
        self.risk_management = config.risk_management
    
    @abstractmethod
    def generate_signal(self, market_data: MarketData) -> Signal:
        """生成交易信號
        
        根據當前市場數據和策略邏輯，生成交易信號。
        這是策略的核心方法，決定何時進場、做多還是做空。
        
        Args:
            market_data: 市場數據對象，包含多週期 OHLCV 數據和技術指標
        
        Returns:
            Signal: 交易信號對象，包含動作（BUY/SELL/HOLD）、方向、價格等信息
        
        Example:
            >>> signal = strategy.generate_signal(market_data)
            >>> if signal.action == 'BUY':
            >>>     print(f"做多信號：進場價 {signal.entry_price}")
        """
        pass
    
    @abstractmethod
    def calculate_position_size(self, capital: float, price: float) -> float:
        """計算倉位大小
        
        根據可用資金、當前價格和風險管理規則，計算應該開倉的數量。
        
        Args:
            capital: 可用資金（USDT）
            price: 當前價格
        
        Returns:
            float: 倉位大小（幣數），例如 0.5 表示 0.5 個 BTC
        
        Example:
            >>> size = strategy.calculate_position_size(capital=1000, price=50000)
            >>> print(f"建議倉位：{size} BTC")
        """
        pass
    
    @abstractmethod
    def calculate_stop_loss(self, entry_price: float, direction: str, atr: float) -> float:
        """計算止損價格
        
        根據進場價格、交易方向和 ATR，計算止損價格。
        
        Args:
            entry_price: 進場價格
            direction: 交易方向（'long' 做多 或 'short' 做空）
            atr: ATR（Average True Range）值，用於動態止損
        
        Returns:
            float: 止損價格
        
        Example:
            >>> stop_loss = strategy.calculate_stop_loss(
            >>>     entry_price=50000, 
            >>>     direction='long', 
            >>>     atr=1000
            >>> )
            >>> print(f"止損價格：{stop_loss}")
        """
        pass
    
    @abstractmethod
    def calculate_take_profit(self, entry_price: float, direction: str, atr: float) -> float:
        """計算目標價格（獲利了結）
        
        根據進場價格、交易方向和 ATR，計算目標價格。
        
        Args:
            entry_price: 進場價格
            direction: 交易方向（'long' 做多 或 'short' 做空）
            atr: ATR 值，用於動態目標
        
        Returns:
            float: 目標價格
        
        Example:
            >>> take_profit = strategy.calculate_take_profit(
            >>>     entry_price=50000, 
            >>>     direction='long', 
            >>>     atr=1000
            >>> )
            >>> print(f"目標價格：{take_profit}")
        """
        pass
    
    @abstractmethod
    def should_exit(self, position: Position, market_data: MarketData) -> tuple[bool, str]:
        """判斷是否應該出場
        
        根據當前持倉和市場數據，判斷是否應該平倉。
        除了止損和目標價格，還可以根據其他條件（如趨勢反轉）決定出場。
        
        Args:
            position: 當前持倉對象
            market_data: 市場數據對象
        
        Returns:
            tuple[bool, str]: (是否應該出場, 出場原因)
            
        Example:
            >>> should_exit, reason = strategy.should_exit(position, market_data)
            >>> if should_exit:
            >>>     print(f"出場原因：{reason}")
        """
        pass
    
    def get_name(self) -> str:
        """獲取策略名稱
        
        Returns:
            str: 策略名稱
        """
        return self.strategy_name
    
    def get_id(self) -> str:
        """獲取策略 ID
        
        Returns:
            str: 策略 ID
        """
        return self.strategy_id
    
    def is_enabled(self) -> bool:
        """檢查策略是否啟用
        
        Returns:
            bool: 是否啟用
        """
        return self.config.enabled
    
    def __repr__(self) -> str:
        """字符串表示
        
        Returns:
            str: 策略的字符串表示
        """
        return f"Strategy(id={self.strategy_id}, name={self.strategy_name}, symbol={self.symbol})"
