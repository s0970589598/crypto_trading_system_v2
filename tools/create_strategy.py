#!/usr/bin/env python3
"""
策略腳手架生成器

根據模板自動生成新策略代碼和配置文件。

使用方法：
    python tools/create_strategy.py --id my-strategy --name "我的策略" --symbol BTCUSDT

選項：
    --id: 策略 ID（必需，使用 kebab-case 格式）
    --name: 策略名稱（必需）
    --symbol: 交易對（必需，如 BTCUSDT）
    --timeframes: 時間週期（可選，默認 1d,4h,1h）
    --output-dir: 輸出目錄（可選，默認 src/strategies/）
    --config-dir: 配置文件目錄（可選，默認 strategies/）
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime


# 策略代碼模板
STRATEGY_CODE_TEMPLATE = '''"""
{strategy_name} - 自動生成於 {timestamp}

策略 ID: {strategy_id}
交易對: {symbol}
時間週期: {timeframes}

TODO: 實現策略邏輯
"""

from datetime import datetime
from src.execution.strategy import Strategy
from src.models.config import StrategyConfig
from src.models.market_data import MarketData
from src.models.trading import Signal, Position


class {class_name}(Strategy):
    """{strategy_name}
    
    TODO: 添加策略描述
    """
    
    def __init__(self, config: StrategyConfig):
        """初始化策略
        
        Args:
            config: 策略配置對象
        """
        super().__init__(config)
        
        # 從配置中讀取參數
        self.stop_loss_atr = config.parameters.get('stop_loss_atr', 2.0)
        self.take_profit_atr = config.parameters.get('take_profit_atr', 4.0)
        
        # TODO: 添加其他自定義參數
        # self.custom_param = config.parameters.get('custom_param', default_value)
    
    def generate_signal(self, market_data: MarketData) -> Signal:
        """生成交易信號
        
        TODO: 實現信號生成邏輯
        
        Args:
            market_data: 市場數據對象
        
        Returns:
            Signal: 交易信號
        """
        # 獲取當前價格
        price = market_data.get_latest_price()
        
        # TODO: 實現進場邏輯
        # 示例：獲取指定週期的數據
        # tf_1h = market_data.get_timeframe('1h')
        # latest_1h = tf_1h.get_latest()
        # trend = latest_1h.get('Trend', 'Neutral')
        # rsi = latest_1h.get('RSI', 50)
        
        # 默認持有
        action = 'HOLD'
        direction = None
        
        # TODO: 根據條件決定進場
        # if <進場條件>:
        #     action = 'BUY'
        #     direction = 'long'
        # elif <做空條件>:
        #     action = 'SELL'
        #     direction = 'short'
        
        # 計算止損和目標
        atr = 0  # TODO: 從市場數據獲取 ATR
        stop_loss = 0
        take_profit = 0
        
        if action in ['BUY', 'SELL']:
            stop_loss = self.calculate_stop_loss(price, direction, atr)
            take_profit = self.calculate_take_profit(price, direction, atr)
        
        # 創建信號
        signal = Signal(
            strategy_id=self.strategy_id,
            timestamp=datetime.now(),
            symbol=self.symbol,
            action=action,
            direction=direction,
            entry_price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            position_size=0.0,
            confidence=0.5,  # TODO: 計算信號置信度
            metadata={{}}
        )
        
        return signal
    
    def calculate_position_size(self, capital: float, price: float) -> float:
        """計算倉位大小
        
        TODO: 實現倉位計算邏輯
        
        Args:
            capital: 可用資金（USDT）
            price: 當前價格
        
        Returns:
            float: 倉位大小（幣數）
        """
        # 使用配置中的倉位比例
        position_size_ratio = self.risk_management.position_size
        leverage = self.risk_management.leverage
        
        # 計算倉位大小
        position_value = capital * position_size_ratio * leverage
        position_size = position_value / price
        
        return position_size
    
    def calculate_stop_loss(self, entry_price: float, direction: str, atr: float) -> float:
        """計算止損價格
        
        TODO: 實現止損計算邏輯
        
        Args:
            entry_price: 進場價格
            direction: 交易方向（'long' 或 'short'）
            atr: ATR 值
        
        Returns:
            float: 止損價格
        """
        stop_loss_atr = self.stop_loss_atr
        
        if direction == 'long':
            stop_loss = entry_price - (atr * stop_loss_atr)
        elif direction == 'short':
            stop_loss = entry_price + (atr * stop_loss_atr)
        else:
            stop_loss = 0
        
        return stop_loss
    
    def calculate_take_profit(self, entry_price: float, direction: str, atr: float) -> float:
        """計算目標價格
        
        TODO: 實現目標計算邏輯
        
        Args:
            entry_price: 進場價格
            direction: 交易方向（'long' 或 'short'）
            atr: ATR 值
        
        Returns:
            float: 目標價格
        """
        take_profit_atr = self.take_profit_atr
        
        if direction == 'long':
            take_profit = entry_price + (atr * take_profit_atr)
        elif direction == 'short':
            take_profit = entry_price - (atr * take_profit_atr)
        else:
            take_profit = 0
        
        return take_profit
    
    def should_exit(self, position: Position, market_data: MarketData) -> tuple[bool, str]:
        """判斷是否應該出場
        
        TODO: 實現出場邏輯
        
        Args:
            position: 當前持倉
            market_data: 市場數據
        
        Returns:
            tuple[bool, str]: (是否出場, 出場原因)
        """
        current_price = market_data.get_latest_price()
        
        # 檢查止損
        if position.should_stop_loss(current_price):
            return True, '止損'
        
        # 檢查目標
        if position.should_take_profit(current_price):
            return True, '獲利'
        
        # TODO: 添加其他出場條件
        # 示例：趨勢反轉
        # tf_1h = market_data.get_timeframe('1h')
        # latest_1h = tf_1h.get_latest()
        # trend = latest_1h.get('Trend', 'Neutral')
        # if position.direction == 'long' and trend == 'Downtrend':
        #     return True, '趨勢反轉'
        
        return False, ''
'''


# 配置文件模板
CONFIG_TEMPLATE = {
    "strategy_id": "",
    "strategy_name": "",
    "version": "1.0.0",
    "enabled": True,
    "symbol": "",
    "timeframes": [],
    "parameters": {
        "stop_loss_atr": 2.0,
        "take_profit_atr": 4.0,
    },
    "risk_management": {
        "position_size": 0.20,
        "leverage": 5,
        "max_trades_per_day": 3,
        "max_consecutive_losses": 3,
        "daily_loss_limit": 0.10,
        "stop_loss_atr": 2.0,
        "take_profit_atr": 4.0,
    },
    "entry_conditions": [
        "TODO: 添加進場條件"
    ],
    "exit_conditions": {
        "stop_loss": "entry_price - (atr * 2.0)",
        "take_profit": "entry_price + (atr * 4.0)"
    },
    "notifications": {
        "telegram": True,
        "email": False
    }
}


def kebab_to_pascal(kebab_str: str) -> str:
    """將 kebab-case 轉換為 PascalCase
    
    Args:
        kebab_str: kebab-case 字符串（如 my-strategy）
    
    Returns:
        str: PascalCase 字符串（如 MyStrategy）
    """
    return ''.join(word.capitalize() for word in kebab_str.split('-'))


def validate_strategy_id(strategy_id: str) -> bool:
    """驗證策略 ID 格式
    
    Args:
        strategy_id: 策略 ID
    
    Returns:
        bool: 是否有效
    """
    # 檢查是否為 kebab-case 格式
    if not strategy_id:
        return False
    
    # 只允許小寫字母、數字和連字符
    import re
    pattern = r'^[a-z0-9]+(-[a-z0-9]+)*$'
    return bool(re.match(pattern, strategy_id))


def create_strategy(
    strategy_id: str,
    strategy_name: str,
    symbol: str,
    timeframes: list,
    output_dir: str,
    config_dir: str
) -> tuple[bool, str]:
    """創建策略腳手架
    
    Args:
        strategy_id: 策略 ID（kebab-case）
        strategy_name: 策略名稱
        symbol: 交易對
        timeframes: 時間週期列表
        output_dir: 代碼輸出目錄
        config_dir: 配置文件輸出目錄
    
    Returns:
        tuple[bool, str]: (是否成功, 訊息)
    """
    # 驗證策略 ID
    if not validate_strategy_id(strategy_id):
        return False, f"無效的策略 ID：{strategy_id}。必須使用 kebab-case 格式（如 my-strategy）"
    
    # 生成類名
    class_name = kebab_to_pascal(strategy_id) + 'Strategy'
    
    # 生成文件名
    code_filename = f"{strategy_id.replace('-', '_')}_strategy.py"
    config_filename = f"{strategy_id}.json"
    
    # 創建輸出目錄
    output_path = Path(output_dir)
    config_path = Path(config_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    config_path.mkdir(parents=True, exist_ok=True)
    
    # 檢查文件是否已存在
    code_file = output_path / code_filename
    config_file = config_path / config_filename
    
    if code_file.exists():
        return False, f"策略代碼文件已存在：{code_file}"
    
    if config_file.exists():
        return False, f"配置文件已存在：{config_file}"
    
    # 生成策略代碼
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    code_content = STRATEGY_CODE_TEMPLATE.format(
        strategy_name=strategy_name,
        timestamp=timestamp,
        strategy_id=strategy_id,
        symbol=symbol,
        timeframes=', '.join(timeframes),
        class_name=class_name,
    )
    
    # 生成配置文件
    config = CONFIG_TEMPLATE.copy()
    config['strategy_id'] = strategy_id
    config['strategy_name'] = strategy_name
    config['symbol'] = symbol
    config['timeframes'] = timeframes
    
    # 寫入文件
    try:
        # 寫入策略代碼
        with open(code_file, 'w', encoding='utf-8') as f:
            f.write(code_content)
        
        # 寫入配置文件
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        return True, f"✅ 策略腳手架創建成功！\n\n代碼文件：{code_file}\n配置文件：{config_file}\n\n下一步：\n1. 編輯 {code_file} 實現策略邏輯\n2. 編輯 {config_file} 調整參數\n3. 運行測試驗證策略"
        
    except Exception as e:
        return False, f"創建策略腳手架時發生錯誤：{e}"


def main():
    """主函數"""
    parser = argparse.ArgumentParser(
        description='策略腳手架生成器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例：
  # 創建基本策略
  python tools/create_strategy.py --id my-strategy --name "我的策略" --symbol BTCUSDT
  
  # 指定時間週期
  python tools/create_strategy.py --id trend-follow --name "趨勢跟蹤" --symbol ETHUSDT --timeframes 1d,4h,1h
  
  # 指定輸出目錄
  python tools/create_strategy.py --id scalping --name "剝頭皮" --symbol BTCUSDT --output-dir custom/strategies/
        '''
    )
    
    parser.add_argument(
        '--id',
        required=True,
        help='策略 ID（使用 kebab-case 格式，如 my-strategy）'
    )
    
    parser.add_argument(
        '--name',
        required=True,
        help='策略名稱（如 "我的策略"）'
    )
    
    parser.add_argument(
        '--symbol',
        required=True,
        help='交易對（如 BTCUSDT）'
    )
    
    parser.add_argument(
        '--timeframes',
        default='1d,4h,1h',
        help='時間週期，逗號分隔（默認：1d,4h,1h）'
    )
    
    parser.add_argument(
        '--output-dir',
        default='src/strategies/',
        help='代碼輸出目錄（默認：src/strategies/）'
    )
    
    parser.add_argument(
        '--config-dir',
        default='strategies/',
        help='配置文件輸出目錄（默認：strategies/）'
    )
    
    args = parser.parse_args()
    
    # 解析時間週期
    timeframes = [tf.strip() for tf in args.timeframes.split(',')]
    
    # 創建策略
    success, message = create_strategy(
        strategy_id=args.id,
        strategy_name=args.name,
        symbol=args.symbol,
        timeframes=timeframes,
        output_dir=args.output_dir,
        config_dir=args.config_dir,
    )
    
    print(message)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
