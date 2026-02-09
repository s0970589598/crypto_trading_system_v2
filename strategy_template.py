"""
策略模板 - 用於快速創建新策略

使用方法：
1. 複製此文件並重命名（如 my_strategy.py）
2. 修改類名（如 MyStrategy）
3. 實現所有標記為 TODO 的方法
4. 創建對應的 JSON 配置文件（strategies/my-strategy.json）
5. 運行測試確保策略正常工作

示例配置文件（strategies/my-strategy.json）：
{
  "strategy_id": "my-strategy-v1",
  "strategy_name": "我的策略",
  "version": "1.0.0",
  "enabled": true,
  "symbol": "BTCUSDT",
  "timeframes": ["1d", "4h", "1h"],
  "parameters": {
    "stop_loss_atr": 2.0,
    "take_profit_atr": 4.0,
    "custom_param": 100
  },
  "risk_management": {
    "position_size": 0.20,
    "leverage": 5,
    "max_trades_per_day": 3,
    "max_consecutive_losses": 3,
    "daily_loss_limit": 0.10,
    "stop_loss_atr": 2.0,
    "take_profit_atr": 4.0
  },
  "entry_conditions": [
    "自定義進場條件"
  ],
  "exit_conditions": {
    "stop_loss": "price - (atr * stop_loss_atr)",
    "take_profit": "price + (atr * take_profit_atr)"
  },
  "notifications": {
    "telegram": true,
    "email": false
  }
}
"""

from datetime import datetime
from src.execution.strategy import Strategy
from src.models.config import StrategyConfig
from src.models.market_data import MarketData
from src.models.trading import Signal, Position


class TemplateStrategy(Strategy):
    """策略模板類
    
    這是一個策略模板，展示了如何實現 Strategy 接口。
    請根據您的策略邏輯修改每個方法的實現。
    """
    
    def __init__(self, config: StrategyConfig):
        """初始化策略
        
        Args:
            config: 策略配置對象
        """
        super().__init__(config)
        
        # TODO: 在這裡初始化策略特定的參數
        # 從 config.parameters 中讀取自定義參數
        self.stop_loss_atr = config.parameters.get('stop_loss_atr', 2.0)
        self.take_profit_atr = config.parameters.get('take_profit_atr', 4.0)
        
        # 示例：讀取自定義參數
        # self.custom_param = config.parameters.get('custom_param', 100)
    
    def generate_signal(self, market_data: MarketData) -> Signal:
        """生成交易信號
        
        TODO: 實現您的信號生成邏輯
        
        步驟：
        1. 從 market_data 獲取所需週期的數據
        2. 檢查進場條件（趨勢、指標、成交量等）
        3. 決定動作（BUY/SELL/HOLD）和方向（long/short）
        4. 計算進場價格、止損、目標
        5. 返回 Signal 對象
        
        Args:
            market_data: 市場數據對象
        
        Returns:
            Signal: 交易信號
        """
        # TODO: 獲取所需週期的數據
        # 示例：獲取 1 小時數據
        # tf_1h = market_data.get_timeframe('1h')
        # latest_1h = tf_1h.get_latest()
        
        # TODO: 檢查進場條件
        # 示例：檢查趨勢
        # trend = latest_1h.get('Trend', 'Neutral')
        # rsi = latest_1h.get('RSI', 50)
        
        # TODO: 決定動作和方向
        action = 'HOLD'  # 'BUY', 'SELL', 'HOLD'
        direction = None  # 'long', 'short', None
        
        # 示例：做多條件
        # if trend == 'Uptrend' and 30 <= rsi <= 70:
        #     action = 'BUY'
        #     direction = 'long'
        
        # 示例：做空條件
        # elif trend == 'Downtrend' and 30 <= rsi <= 70:
        #     action = 'SELL'
        #     direction = 'short'
        
        # TODO: 計算進場價格、止損、目標
        price = market_data.get_latest_price()
        
        # 示例：獲取 ATR
        # atr = latest_1h.get('ATR', 0)
        atr = 0
        
        stop_loss = 0
        take_profit = 0
        
        if action in ['BUY', 'SELL']:
            stop_loss = self.calculate_stop_loss(price, direction, atr)
            take_profit = self.calculate_take_profit(price, direction, atr)
        
        # TODO: 計算倉位大小（這裡使用佔位符，實際由 calculate_position_size 計算）
        position_size = 0.0
        
        # TODO: 計算信號置信度（0-1）
        confidence = 0.5
        
        # 創建信號對象
        signal = Signal(
            strategy_id=self.strategy_id,
            timestamp=datetime.now(),
            symbol=self.symbol,
            action=action,
            direction=direction,
            entry_price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            position_size=position_size,
            confidence=confidence,
            metadata={
                # TODO: 添加額外信息（如觸發的指標值）
                # 'rsi': rsi,
                # 'trend': trend,
            }
        )
        
        return signal
    
    def calculate_position_size(self, capital: float, price: float) -> float:
        """計算倉位大小
        
        TODO: 實現您的倉位計算邏輯
        
        常見方法：
        1. 固定比例：capital * position_size_ratio / price
        2. 固定金額：fixed_amount / price
        3. 風險百分比：(capital * risk_pct) / (stop_loss_distance * price)
        
        Args:
            capital: 可用資金（USDT）
            price: 當前價格
        
        Returns:
            float: 倉位大小（幣數）
        """
        # TODO: 實現倉位計算邏輯
        
        # 示例：使用配置中的倉位比例
        position_size_ratio = self.risk_management.position_size
        leverage = self.risk_management.leverage
        
        # 計算倉位大小（幣數）
        position_value = capital * position_size_ratio * leverage
        position_size = position_value / price
        
        return position_size
    
    def calculate_stop_loss(self, entry_price: float, direction: str, atr: float) -> float:
        """計算止損價格
        
        TODO: 實現您的止損計算邏輯
        
        常見方法：
        1. ATR 止損：entry_price ± (atr * multiplier)
        2. 百分比止損：entry_price * (1 ± stop_loss_pct)
        3. 固定點數止損：entry_price ± fixed_points
        
        Args:
            entry_price: 進場價格
            direction: 交易方向（'long' 或 'short'）
            atr: ATR 值
        
        Returns:
            float: 止損價格
        """
        # TODO: 實現止損計算邏輯
        
        # 示例：使用 ATR 止損
        stop_loss_atr = self.stop_loss_atr
        
        if direction == 'long':
            # 做多：止損在下方
            stop_loss = entry_price - (atr * stop_loss_atr)
        elif direction == 'short':
            # 做空：止損在上方
            stop_loss = entry_price + (atr * stop_loss_atr)
        else:
            stop_loss = 0
        
        return stop_loss
    
    def calculate_take_profit(self, entry_price: float, direction: str, atr: float) -> float:
        """計算目標價格
        
        TODO: 實現您的目標計算邏輯
        
        常見方法：
        1. ATR 目標：entry_price ± (atr * multiplier)
        2. 風險回報比：entry_price ± (stop_loss_distance * reward_ratio)
        3. 百分比目標：entry_price * (1 ± take_profit_pct)
        
        Args:
            entry_price: 進場價格
            direction: 交易方向（'long' 或 'short'）
            atr: ATR 值
        
        Returns:
            float: 目標價格
        """
        # TODO: 實現目標計算邏輯
        
        # 示例：使用 ATR 目標
        take_profit_atr = self.take_profit_atr
        
        if direction == 'long':
            # 做多：目標在上方
            take_profit = entry_price + (atr * take_profit_atr)
        elif direction == 'short':
            # 做空：目標在下方
            take_profit = entry_price - (atr * take_profit_atr)
        else:
            take_profit = 0
        
        return take_profit
    
    def should_exit(self, position: Position, market_data: MarketData) -> tuple[bool, str]:
        """判斷是否應該出場
        
        TODO: 實現您的出場邏輯
        
        常見出場條件：
        1. 止損/目標觸發（已在 Position 類中實現）
        2. 趨勢反轉
        3. 指標背離
        4. 時間止損（持倉時間過長）
        5. 追蹤止損
        
        Args:
            position: 當前持倉
            market_data: 市場數據
        
        Returns:
            tuple[bool, str]: (是否出場, 出場原因)
        """
        # TODO: 實現出場邏輯
        
        # 獲取當前價格
        current_price = market_data.get_latest_price()
        
        # 檢查止損
        if position.should_stop_loss(current_price):
            return True, '止損'
        
        # 檢查目標
        if position.should_take_profit(current_price):
            return True, '獲利'
        
        # TODO: 添加其他出場條件
        
        # 示例：趨勢反轉出場
        # tf_1h = market_data.get_timeframe('1h')
        # latest_1h = tf_1h.get_latest()
        # trend = latest_1h.get('Trend', 'Neutral')
        
        # if position.direction == 'long' and trend == 'Downtrend':
        #     return True, '趨勢反轉'
        # elif position.direction == 'short' and trend == 'Uptrend':
        #     return True, '趨勢反轉'
        
        # 示例：時間止損（持倉超過 24 小時）
        # from datetime import datetime, timedelta
        # if datetime.now() - position.entry_time > timedelta(hours=24):
        #     return True, '時間止損'
        
        # 不出場
        return False, ''


# 使用示例
if __name__ == '__main__':
    """
    測試策略模板
    
    運行此腳本可以快速測試策略是否正常工作。
    """
    from src.models.config import StrategyConfig, RiskManagement, ExitConditions, NotificationConfig
    import pandas as pd
    from src.models.market_data import TimeframeData
    
    # 創建測試配置
    config = StrategyConfig(
        strategy_id='template-test',
        strategy_name='模板測試',
        version='1.0.0',
        enabled=True,
        symbol='BTCUSDT',
        timeframes=['1h'],
        parameters={
            'stop_loss_atr': 2.0,
            'take_profit_atr': 4.0,
        },
        risk_management=RiskManagement(
            position_size=0.20,
            leverage=5,
            max_trades_per_day=3,
            max_consecutive_losses=3,
            daily_loss_limit=0.10,
            stop_loss_atr=2.0,
            take_profit_atr=4.0,
        ),
        entry_conditions=[],
        exit_conditions=ExitConditions(
            stop_loss='price - (atr * 2.0)',
            take_profit='price + (atr * 4.0)',
        ),
        notifications=NotificationConfig(telegram=False),
    )
    
    # 創建策略實例
    strategy = TemplateStrategy(config)
    
    # 創建測試市場數據
    df = pd.DataFrame({
        'timestamp': [datetime.now()],
        'open': [50000.0],
        'high': [51000.0],
        'low': [49000.0],
        'close': [50500.0],
        'volume': [100.0],
    })
    
    tf_data = TimeframeData(
        timeframe='1h',
        ohlcv=df,
        indicators={}
    )
    
    market_data = MarketData(
        symbol='BTCUSDT',
        timestamp=datetime.now(),
        timeframes={'1h': tf_data}
    )
    
    # 測試信號生成
    signal = strategy.generate_signal(market_data)
    print(f"信號：{signal.action}, 方向：{signal.direction}")
    
    # 測試倉位計算
    position_size = strategy.calculate_position_size(capital=1000, price=50000)
    print(f"倉位大小：{position_size} BTC")
    
    # 測試止損計算
    stop_loss = strategy.calculate_stop_loss(entry_price=50000, direction='long', atr=1000)
    print(f"止損價格：{stop_loss}")
    
    # 測試目標計算
    take_profit = strategy.calculate_take_profit(entry_price=50000, direction='long', atr=1000)
    print(f"目標價格：{take_profit}")
    
    print("\n✅ 策略模板測試完成！")
