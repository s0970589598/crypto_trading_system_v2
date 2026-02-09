"""
均值回歸策略 (Mean Reversion Strategy)

策略邏輯：
-----------
均值回歸策略基於價格會回歸到其平均值的假設。當價格偏離移動平均線過遠時，
預期價格會回歸到均線附近。

進場條件：
1. 價格偏離 20 日 SMA 超過 2%
2. RSI 顯示超買（>70）或超賣（<30）
3. 布林帶確認：價格觸及或突破布林帶
4. 成交量正常（不要在極端成交量時交易）

出場條件：
1. 價格回歸到移動平均線附近（0.5% 範圍內）
2. 達到止損或目標
3. RSI 回到中性區域（40-60）

風險管理：
- 止損：1.5 ATR
- 目標：2.0 ATR（較小的目標，因為是回歸策略）
- 倉位：15%（較保守）
- 槓桿：3x（較低槓桿）

適用市場：
- 震盪市場（Sideways）
- 低波動性環境
- 不適合強趨勢市場

作者：Multi-Strategy Trading System
版本：1.0.0
"""

from src.execution.strategy import Strategy
from src.models.config import StrategyConfig
from src.models.trading import Signal, Position
from src.models.market_data import MarketData
import pandas as pd
import numpy as np
from typing import Dict, Tuple
import logging

logger = logging.getLogger(__name__)


class MeanReversionStrategy(Strategy):
    """均值回歸策略
    
    這是一個示例策略，展示如何實現均值回歸交易邏輯。
    適合在震盪市場中使用。
    """
    
    def __init__(self, config: StrategyConfig):
        """初始化策略
        
        Args:
            config: 策略配置對象
        """
        super().__init__(config)
        
        # 從配置中讀取參數
        self.sma_period = config.parameters.get('sma_period', 20)
        self.deviation_threshold = config.parameters.get('deviation_threshold', 0.02)
        self.rsi_period = config.parameters.get('rsi_period', 14)
        self.rsi_oversold = config.parameters.get('rsi_oversold', 30)
        self.rsi_overbought = config.parameters.get('rsi_overbought', 70)
        self.bb_period = config.parameters.get('bb_period', 20)
        self.bb_std = config.parameters.get('bb_std', 2.0)
        self.reversion_threshold = config.parameters.get('reversion_threshold', 0.005)
        
        logger.info(f"Initialized {self.strategy_id} with parameters: "
                   f"SMA={self.sma_period}, deviation={self.deviation_threshold}, "
                   f"RSI={self.rsi_period}")
    
    def generate_signal(self, market_data: MarketData) -> Signal:
        """生成交易信號
        
        Args:
            market_data: 市場數據對象
        
        Returns:
            Signal: 交易信號（BUY/SELL/HOLD）
        """
        try:
            # 1. 驗證數據完整性
            if not self._validate_data(market_data):
                logger.debug(f"{self.strategy_id}: Data validation failed")
                return Signal.hold(self.strategy_id, market_data.timestamp, self.config.symbol)
            
            # 2. 計算技術指標
            indicators = self._calculate_indicators(market_data)
            
            # 3. 檢查進場條件
            if self._check_buy_conditions(indicators):
                logger.info(f"{self.strategy_id}: Buy signal generated")
                return self._create_buy_signal(market_data, indicators)
            
            if self._check_sell_conditions(indicators):
                logger.info(f"{self.strategy_id}: Sell signal generated")
                return self._create_sell_signal(market_data, indicators)
            
            # 4. 默認持有
            return Signal.hold(self.strategy_id, market_data.timestamp, self.config.symbol)
            
        except Exception as e:
            logger.error(f"{self.strategy_id}: Error generating signal: {e}", exc_info=True)
            return Signal.hold(self.strategy_id, market_data.timestamp, self.config.symbol)
    
    def _validate_data(self, market_data: MarketData) -> bool:
        """驗證數據完整性
        
        Args:
            market_data: 市場數據對象
        
        Returns:
            bool: 數據是否有效
        """
        try:
            # 檢查所需的時間週期
            for timeframe in ['1h', '15m']:
                data = market_data.get_timeframe(timeframe)
                if data is None:
                    logger.warning(f"{self.strategy_id}: Missing {timeframe} data")
                    return False
                
                # 確保有足夠的數據點
                min_required = max(self.sma_period, self.rsi_period, self.bb_period) + 10
                if len(data.ohlcv) < min_required:
                    logger.warning(f"{self.strategy_id}: Insufficient {timeframe} data "
                                 f"(need {min_required}, got {len(data.ohlcv)})")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"{self.strategy_id}: Data validation error: {e}")
            return False
    
    def _calculate_indicators(self, market_data: MarketData) -> Dict:
        """計算技術指標
        
        Args:
            market_data: 市場數據對象
        
        Returns:
            Dict: 包含所有計算指標的字典
        """
        # 獲取 1 小時數據（用於趨勢判斷）
        data_1h = market_data.get_timeframe('1h')
        df_1h = data_1h.ohlcv
        
        # 獲取 15 分鐘數據（用於進場時機）
        data_15m = market_data.get_timeframe('15m')
        df_15m = data_15m.ohlcv
        
        indicators = {}
        
        # === 1 小時指標（趨勢判斷）===
        # 簡單移動平均線
        indicators['sma_1h'] = df_1h['close'].rolling(window=self.sma_period).mean()
        
        # 價格偏離度
        indicators['deviation_1h'] = (df_1h['close'] - indicators['sma_1h']) / indicators['sma_1h']
        
        # === 15 分鐘指標（進場時機）===
        # RSI
        indicators['rsi_15m'] = self._calculate_rsi(df_15m['close'], self.rsi_period)
        
        # 布林帶
        bb_upper, bb_middle, bb_lower = self._calculate_bollinger_bands(
            df_15m['close'], self.bb_period, self.bb_std
        )
        indicators['bb_upper_15m'] = bb_upper
        indicators['bb_middle_15m'] = bb_middle
        indicators['bb_lower_15m'] = bb_lower
        
        # ATR（用於止損和目標）
        indicators['atr_15m'] = self._calculate_atr(df_15m, 14)
        
        # 成交量
        indicators['volume_15m'] = df_15m['volume']
        indicators['volume_ma_15m'] = df_15m['volume'].rolling(window=20).mean()
        
        # 當前價格
        indicators['current_price'] = df_15m['close'].iloc[-1]
        
        return indicators
    
    def _check_buy_conditions(self, indicators: Dict) -> bool:
        """檢查買入條件（做多）
        
        當價格超賣時買入，預期價格會回歸到均線。
        
        Args:
            indicators: 技術指標字典
        
        Returns:
            bool: 是否滿足買入條件
        """
        # 獲取最新值
        current_price = indicators['current_price']
        sma = indicators['sma_1h'].iloc[-1]
        deviation = indicators['deviation_1h'].iloc[-1]
        rsi = indicators['rsi_15m'].iloc[-1]
        bb_lower = indicators['bb_lower_15m'].iloc[-1]
        volume = indicators['volume_15m'].iloc[-1]
        volume_ma = indicators['volume_ma_15m'].iloc[-1]
        
        # 條件 1：價格低於均線且偏離超過閾值
        price_below_sma = deviation < -self.deviation_threshold
        
        # 條件 2：RSI 超賣
        rsi_oversold = rsi < self.rsi_oversold
        
        # 條件 3：價格觸及或低於布林帶下軌
        price_at_lower_band = current_price <= bb_lower * 1.01
        
        # 條件 4：成交量正常（不要在極端成交量時交易）
        volume_normal = 0.5 * volume_ma < volume < 2.0 * volume_ma
        
        # 記錄條件檢查結果
        logger.debug(f"{self.strategy_id} Buy conditions: "
                    f"price_below_sma={price_below_sma}, "
                    f"rsi_oversold={rsi_oversold}, "
                    f"price_at_lower_band={price_at_lower_band}, "
                    f"volume_normal={volume_normal}")
        
        # 所有條件都滿足才買入
        return price_below_sma and rsi_oversold and price_at_lower_band and volume_normal
    
    def _check_sell_conditions(self, indicators: Dict) -> bool:
        """檢查賣出條件（做空）
        
        當價格超買時賣出，預期價格會回歸到均線。
        
        Args:
            indicators: 技術指標字典
        
        Returns:
            bool: 是否滿足賣出條件
        """
        # 獲取最新值
        current_price = indicators['current_price']
        sma = indicators['sma_1h'].iloc[-1]
        deviation = indicators['deviation_1h'].iloc[-1]
        rsi = indicators['rsi_15m'].iloc[-1]
        bb_upper = indicators['bb_upper_15m'].iloc[-1]
        volume = indicators['volume_15m'].iloc[-1]
        volume_ma = indicators['volume_ma_15m'].iloc[-1]
        
        # 條件 1：價格高於均線且偏離超過閾值
        price_above_sma = deviation > self.deviation_threshold
        
        # 條件 2：RSI 超買
        rsi_overbought = rsi > self.rsi_overbought
        
        # 條件 3：價格觸及或高於布林帶上軌
        price_at_upper_band = current_price >= bb_upper * 0.99
        
        # 條件 4：成交量正常
        volume_normal = 0.5 * volume_ma < volume < 2.0 * volume_ma
        
        # 記錄條件檢查結果
        logger.debug(f"{self.strategy_id} Sell conditions: "
                    f"price_above_sma={price_above_sma}, "
                    f"rsi_overbought={rsi_overbought}, "
                    f"price_at_upper_band={price_at_upper_band}, "
                    f"volume_normal={volume_normal}")
        
        # 所有條件都滿足才賣出
        return price_above_sma and rsi_overbought and price_at_upper_band and volume_normal
    
    def _create_buy_signal(self, market_data: MarketData, indicators: Dict) -> Signal:
        """創建買入信號
        
        Args:
            market_data: 市場數據對象
            indicators: 技術指標字典
        
        Returns:
            Signal: 買入信號對象
        """
        current_price = indicators['current_price']
        atr = indicators['atr_15m'].iloc[-1]
        
        return Signal(
            strategy_id=self.strategy_id,
            timestamp=market_data.timestamp,
            symbol=self.config.symbol,
            action='BUY',
            direction='long',
            entry_price=current_price,
            stop_loss=self.calculate_stop_loss(current_price, 'long', atr),
            take_profit=self.calculate_take_profit(current_price, 'long', atr),
            position_size=0,  # 由執行引擎計算
            confidence=0.75,  # 均值回歸策略的置信度通常較低
            metadata={
                'strategy_type': 'mean_reversion',
                'rsi': float(indicators['rsi_15m'].iloc[-1]),
                'deviation': float(indicators['deviation_1h'].iloc[-1]),
                'reason': 'oversold_mean_reversion'
            }
        )
    
    def _create_sell_signal(self, market_data: MarketData, indicators: Dict) -> Signal:
        """創建賣出信號
        
        Args:
            market_data: 市場數據對象
            indicators: 技術指標字典
        
        Returns:
            Signal: 賣出信號對象
        """
        current_price = indicators['current_price']
        atr = indicators['atr_15m'].iloc[-1]
        
        return Signal(
            strategy_id=self.strategy_id,
            timestamp=market_data.timestamp,
            symbol=self.config.symbol,
            action='SELL',
            direction='short',
            entry_price=current_price,
            stop_loss=self.calculate_stop_loss(current_price, 'short', atr),
            take_profit=self.calculate_take_profit(current_price, 'short', atr),
            position_size=0,  # 由執行引擎計算
            confidence=0.75,
            metadata={
                'strategy_type': 'mean_reversion',
                'rsi': float(indicators['rsi_15m'].iloc[-1]),
                'deviation': float(indicators['deviation_1h'].iloc[-1]),
                'reason': 'overbought_mean_reversion'
            }
        )
    
    def calculate_position_size(self, capital: float, price: float) -> float:
        """計算倉位大小
        
        均值回歸策略使用較保守的倉位。
        
        Args:
            capital: 可用資金（USDT）
            price: 當前價格
        
        Returns:
            float: 倉位大小（幣數）
        """
        position_pct = self.config.risk_management.position_size
        leverage = self.config.risk_management.leverage
        
        # 計算基礎倉位
        position_value = capital * position_pct * leverage
        position_size = position_value / price
        
        return position_size
    
    def calculate_stop_loss(self, entry_price: float, direction: str, atr: float) -> float:
        """計算止損價格
        
        Args:
            entry_price: 進場價格
            direction: 方向（'long' 或 'short'）
            atr: ATR 值
        
        Returns:
            float: 止損價格
        """
        stop_loss_atr = self.config.parameters.get('stop_loss_atr', 1.5)
        
        if direction == 'long':
            return entry_price - (atr * stop_loss_atr)
        else:
            return entry_price + (atr * stop_loss_atr)
    
    def calculate_take_profit(self, entry_price: float, direction: str, atr: float) -> float:
        """計算目標價格
        
        均值回歸策略的目標較小，因為預期價格只會回歸到均線附近。
        
        Args:
            entry_price: 進場價格
            direction: 方向（'long' 或 'short'）
            atr: ATR 值
        
        Returns:
            float: 目標價格
        """
        take_profit_atr = self.config.parameters.get('take_profit_atr', 2.0)
        
        if direction == 'long':
            return entry_price + (atr * take_profit_atr)
        else:
            return entry_price - (atr * take_profit_atr)
    
    def should_exit(self, position: Position, market_data: MarketData) -> bool:
        """判斷是否應該出場
        
        均值回歸策略的出場條件：
        1. 價格回歸到均線附近
        2. RSI 回到中性區域
        3. 達到止損或目標
        
        Args:
            position: 當前持倉
            market_data: 市場數據
        
        Returns:
            bool: 是否應該出場
        """
        try:
            # 獲取當前數據
            data_15m = market_data.get_timeframe('15m')
            data_1h = market_data.get_timeframe('1h')
            
            current_price = data_15m.ohlcv['close'].iloc[-1]
            sma = data_1h.ohlcv['close'].rolling(window=self.sma_period).mean().iloc[-1]
            rsi = self._calculate_rsi(data_15m.ohlcv['close'], self.rsi_period).iloc[-1]
            
            # 檢查止損和目標
            if position.direction == 'long':
                if current_price <= position.stop_loss:
                    logger.info(f"{self.strategy_id}: Exit long - stop loss hit")
                    return True
                if current_price >= position.take_profit:
                    logger.info(f"{self.strategy_id}: Exit long - take profit hit")
                    return True
            else:
                if current_price >= position.stop_loss:
                    logger.info(f"{self.strategy_id}: Exit short - stop loss hit")
                    return True
                if current_price <= position.take_profit:
                    logger.info(f"{self.strategy_id}: Exit short - take profit hit")
                    return True
            
            # 檢查價格是否回歸到均線
            deviation = abs(current_price - sma) / sma
            if deviation < self.reversion_threshold:
                logger.info(f"{self.strategy_id}: Exit - price reverted to mean")
                return True
            
            # 檢查 RSI 是否回到中性區域
            if 40 < rsi < 60:
                logger.info(f"{self.strategy_id}: Exit - RSI neutral")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"{self.strategy_id}: Error in should_exit: {e}")
            return False
    
    # === 輔助方法：技術指標計算 ===
    
    def _calculate_rsi(self, series: pd.Series, period: int) -> pd.Series:
        """計算 RSI 指標
        
        Args:
            series: 價格序列
            period: 週期
        
        Returns:
            pd.Series: RSI 值
        """
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_bollinger_bands(
        self,
        series: pd.Series,
        period: int,
        std_dev: float
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """計算布林帶
        
        Args:
            series: 價格序列
            period: 週期
            std_dev: 標準差倍數
        
        Returns:
            Tuple[pd.Series, pd.Series, pd.Series]: (上軌, 中軌, 下軌)
        """
        middle = series.rolling(window=period).mean()
        std = series.rolling(window=period).std()
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        return upper, middle, lower
    
    def _calculate_atr(self, df: pd.DataFrame, period: int) -> pd.Series:
        """計算 ATR 指標
        
        Args:
            df: OHLCV 數據框
            period: 週期
        
        Returns:
            pd.Series: ATR 值
        """
        high = df['high']
        low = df['low']
        close = df['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        atr = tr.rolling(window=period).mean()
        return atr
