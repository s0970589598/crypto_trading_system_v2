"""
回測引擎

提供統一的回測接口，支持單策略和多策略回測。
"""

import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging

from src.execution.strategy import Strategy
from src.models.trading import Trade, Position, Signal
from src.models.backtest import BacktestResult
from src.models.market_data import MarketData, TimeframeData


logger = logging.getLogger(__name__)


class BacktestEngine:
    """回測引擎
    
    提供統一的回測接口，支持：
    - 單策略回測
    - 多策略組合回測
    - 績效指標計算
    - 資金曲線追蹤
    """
    
    def __init__(
        self,
        initial_capital: float,
        commission: float = 0.0005,
        slippage: float = 0.0,
        fill_timing: str = 'next_open',
    ):
        """初始化回測引擎

        Args:
            initial_capital: 初始資金
            commission: 手續費率（默認 0.05%）
            slippage: 滑點率（單邊，預設 0）。每次成交價朝不利方向偏移此比例，
                例如 0.0005 表示買進貴 0.05%、賣出便宜 0.05%。對高槓桿短線必設，
                否則回測獲利系統性高估。
            fill_timing: 成交時點。
                'next_open'（預設、正確）= 訊號在第 i 根產生、第 i+1 根開盤價成交，
                避免「看到收盤價又用收盤價成交」的同根 look-ahead；
                'close'（legacy）= 當根收盤價立即成交（舊行為，僅供前後對比）。
        """
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        self.fill_timing = fill_timing

    def _apply_slippage(self, price: float, is_buy: bool) -> float:
        """對成交價套用滑點（永遠朝不利方向偏移）

        Args:
            price: 基準成交價
            is_buy: 是否為買方成交（開多 / 平空）。買方價格上偏、賣方價格下偏。

        Returns:
            float: 加上滑點後的成交價
        """
        if is_buy:
            return price * (1 + self.slippage)
        return price * (1 - self.slippage)

    def _resolve_price_exit(self, position, high: float, low: float):
        """以當根高低點判斷盤中是否觸發 強平 / 止損 / 止盈

        保守原則：同一根 K 線內若不利方向（止損、強平）與有利方向（止盈）
        都被觸及，假設不利方向先成交（避免樂觀偏差）。止損與強平同時觸及時，
        以「價格先碰到的那個」為準（朝不利方向移動時先碰到較接近進場價的一邊）。

        Args:
            position: 當前持倉
            high: 當根最高價
            low: 當根最低價

        Returns:
            (成交基準價, 出場原因) 或 None（未觸發）
        """
        liq = position.liquidation_price()

        # stop_loss / take_profit <= 0 視為「未設/停用」
        has_sl = position.stop_loss > 0
        has_tp = position.take_profit > 0

        if position.direction == 'long':
            # 下行不利：止損與強平，朝下移動時先碰到「較高」的那個
            reached_sl = has_sl and low <= position.stop_loss
            reached_liq = low <= liq
            if reached_sl or reached_liq:
                if reached_sl and reached_liq:
                    if position.stop_loss >= liq:
                        return position.stop_loss, "止損"
                    return liq, "強平"
                if reached_sl:
                    return position.stop_loss, "止損"
                return liq, "強平"
            # 上行有利：止盈
            if has_tp and high >= position.take_profit:
                return position.take_profit, "獲利"

        elif position.direction == 'short':
            # 上行不利：止損與強平，朝上移動時先碰到「較低」的那個
            reached_sl = has_sl and high >= position.stop_loss
            reached_liq = high >= liq
            if reached_sl or reached_liq:
                if reached_sl and reached_liq:
                    if position.stop_loss <= liq:
                        return position.stop_loss, "止損"
                    return liq, "強平"
                if reached_sl:
                    return position.stop_loss, "止損"
                return liq, "強平"
            # 下行有利：止盈
            if has_tp and low <= position.take_profit:
                return position.take_profit, "獲利"

        return None

    def _reached_favorable(self, position, level: float, high: float, low: float) -> bool:
        """當根是否朝「有利方向」觸及某價位（做多看高點、做空看低點）

        用於分批止盈 tp1 判斷。level 為 None / <=0 視為未設。
        """
        if level is None or level <= 0:
            return False
        if position.direction == 'long':
            return high >= level
        elif position.direction == 'short':
            return low <= level
        return False

    def run_single_strategy(
        self,
        strategy: Strategy,
        market_data: Dict[str, pd.DataFrame],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> BacktestResult:
        """回測單個策略
        
        Args:
            strategy: 策略實例
            market_data: 市場數據（週期 -> DataFrame）
            start_date: 開始日期（可選）
            end_date: 結束日期（可選）
        
        Returns:
            BacktestResult: 回測結果
        """
        logger.info(f"開始回測策略：{strategy.get_name()}")
        
        # 初始化
        capital = self.initial_capital
        trades: List[Trade] = []
        current_position: Optional[Position] = None
        equity_curve = []
        
        # 獲取主週期數據（用於遍歷）
        # 選擇最小的週期以捕捉更多交易機會
        primary_timeframe = self._select_primary_timeframe(strategy.config.timeframes, market_data)
        if primary_timeframe not in market_data:
            raise ValueError(f"市場數據中缺少主週期：{primary_timeframe}")
        
        primary_data = market_data[primary_timeframe]
        logger.info(f"使用 {primary_timeframe} 作為主週期進行遍歷（共 {len(primary_data)} 個時間點）")
        
        # 過濾日期範圍
        if start_date:
            primary_data = primary_data[primary_data['timestamp'] >= start_date]
        if end_date:
            primary_data = primary_data[primary_data['timestamp'] <= end_date]
        
        # 找到所有週期都有數據的起始時間
        # 獲取每個週期的第一個時間戳
        first_timestamps = []
        for tf, df in market_data.items():
            if len(df) > 0:
                first_timestamps.append(df['timestamp'].iloc[0])
        
        if first_timestamps:
            # 使用最晚的第一個時間戳作為起始點
            earliest_start = max(first_timestamps)
            primary_data = primary_data[primary_data['timestamp'] >= earliest_start]
            logger.info(f"調整起始時間為 {earliest_start}，確保所有週期都有數據")
        
        # 重置索引，以便用位置存取「下一根」K 線（next-open 成交用）
        primary_data = primary_data.reset_index(drop=True)
        n = len(primary_data)

        # 待成交的進場單：第 i 根決策、第 i+1 根開盤價成交（修同根 look-ahead）
        pending_entry: Optional[Dict] = None

        # 遍歷每個時間點
        for i in range(n):
            row = primary_data.iloc[i]
            current_time = row['timestamp']
            current_price = row['close']  # 收盤價作為標記價（判斷策略出場、計算權益）
            current_open = row.get('open', current_price)  # 無 open 欄位時退回 close
            current_high = row.get('high', current_price)  # 盤中高點（判斷 TP/SL/強平）
            current_low = row.get('low', current_price)    # 盤中低點

            # 構建 MarketData 對象
            market_data_obj = self._build_market_data(
                strategy.config.symbol,
                current_time,
                market_data,
                i
            )

            # === 1. 檢查既有持倉是否平倉 ===
            #   先用當根高低點判斷「盤中」強平/止損/止盈（不利方向優先、保守），
            #   都沒觸發再檢查策略出場（以收盤價）。
            if current_position:
                # 先解析「全平」候選（SL/強平/tp2）。不利方向（止損/強平）優先，
                # 觸發時跳過分批 tp1（保守、不利先成交）。
                price_exit = self._resolve_price_exit(
                    current_position, current_high, current_low
                )
                is_adverse = price_exit is not None and price_exit[1] in ("止損", "強平")

                # === 1a. 分批止盈 tp1（非不利、未取過、本根觸及）→ 部分平倉 ===
                if (not is_adverse and current_position.tp1 is not None
                        and not current_position.tp1_taken
                        and self._reached_favorable(
                            current_position, current_position.tp1,
                            current_high, current_low)):
                    partial_size = current_position.tp1_close_pct * current_position.size
                    if partial_size > 0:
                        is_buy_to_close = current_position.direction == 'short'
                        fill = self._apply_slippage(current_position.tp1, is_buy_to_close)
                        ptrade = Trade(
                            strategy_id=strategy.get_id(),
                            symbol=current_position.symbol,
                            direction=current_position.direction,
                            entry_time=current_position.entry_time,
                            exit_time=current_time,
                            entry_price=current_position.entry_price,
                            exit_price=fill,
                            size=partial_size,
                            leverage=current_position.leverage,
                            exit_reason="止盈tp1",
                        )
                        ptrade.calculate_pnl(self.commission)
                        capital += ptrade.pnl
                        trades.append(ptrade)
                        current_position.size -= partial_size
                        current_position.tp1_taken = True
                        logger.debug(f"分批止盈 tp1：平 {partial_size:.4f}，損益 {ptrade.pnl:.2f}")
                        # tp1_close_pct≈1 等於全平 → 收掉部位
                        if current_position.size <= 1e-12:
                            current_position = None

                # === 1b. 全平剩餘：SL/強平/tp2（price_exit）或策略出場 ===
                if current_position is not None:
                    should_exit = False
                    exit_reason = ""
                    exit_base_price = current_price  # 策略出場用收盤價
                    if price_exit is not None:
                        exit_base_price, exit_reason = price_exit
                        should_exit = True
                    elif strategy.should_exit(current_position, market_data_obj):
                        should_exit = True
                        exit_reason = "策略出場"

                    if should_exit:
                        # 平倉成交價加滑點：平多=賣出(價下偏)、平空=買進(價上偏)
                        is_buy_to_close = current_position.direction == 'short'
                        exit_price = self._apply_slippage(exit_base_price, is_buy_to_close)

                        trade = Trade(
                            strategy_id=strategy.get_id(),
                            symbol=current_position.symbol,
                            direction=current_position.direction,
                            entry_time=current_position.entry_time,
                            exit_time=current_time,
                            entry_price=current_position.entry_price,
                            exit_price=exit_price,
                            size=current_position.size,
                            leverage=current_position.leverage,
                            exit_reason=exit_reason,
                        )
                        trade.calculate_pnl(self.commission)

                        # 更新資金
                        capital += trade.pnl

                        trades.append(trade)
                        current_position = None

                        logger.debug(f"平倉：{exit_reason}，損益：{trade.pnl:.2f} USDT")

            # === 2. 執行上一根掛單的進場（用本根開盤價成交，修同根 look-ahead）===
            if pending_entry and not current_position:
                direction = pending_entry['direction']
                atr = pending_entry['atr']
                # 進場成交價加滑點：開多=買進(價上偏)、開空=賣出(價下偏)
                is_buy = direction == 'long'
                entry_price = self._apply_slippage(current_open, is_buy)

                position_size = strategy.calculate_position_size(capital, entry_price)
                stop_loss = strategy.calculate_stop_loss(entry_price, direction, atr)
                take_profit = strategy.calculate_take_profit(entry_price, direction, atr)
                partial = strategy.get_partial_take_profit(entry_price, direction, atr)

                current_position = Position(
                    strategy_id=strategy.get_id(),
                    symbol=strategy.config.symbol,
                    direction=direction,
                    entry_time=current_time,
                    entry_price=entry_price,
                    size=position_size,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    leverage=strategy.config.risk_management.leverage,
                    tp1=partial['tp1'] if partial else None,
                    tp1_close_pct=partial.get('tp1_close_pct', 0.0) if partial else 0.0,
                )
                logger.debug(f"開倉：{direction}，成交價：{entry_price:.2f}，大小：{position_size:.4f}")
            pending_entry = None

            # === 3. 產生進場信號（本根決策，預設下一根開盤成交）===
            if not current_position:
                signal = strategy.generate_signal(market_data_obj)

                if signal.action in ['BUY', 'SELL']:
                    direction = 'long' if signal.action == 'BUY' else 'short'
                    atr = market_data_obj.timeframes[primary_timeframe].indicators.get('atr', pd.Series([100.0])).iloc[-1]

                    if self.fill_timing == 'close':
                        # legacy：當根收盤價立即成交（保留舊行為供前後對比）
                        is_buy = direction == 'long'
                        entry_price = self._apply_slippage(current_price, is_buy)
                        position_size = strategy.calculate_position_size(capital, entry_price)
                        stop_loss = strategy.calculate_stop_loss(entry_price, direction, atr)
                        take_profit = strategy.calculate_take_profit(entry_price, direction, atr)
                        partial = strategy.get_partial_take_profit(entry_price, direction, atr)
                        current_position = Position(
                            strategy_id=strategy.get_id(),
                            symbol=strategy.config.symbol,
                            direction=direction,
                            entry_time=current_time,
                            entry_price=entry_price,
                            size=position_size,
                            stop_loss=stop_loss,
                            take_profit=take_profit,
                            leverage=strategy.config.risk_management.leverage,
                            tp1=partial['tp1'] if partial else None,
                            tp1_close_pct=partial.get('tp1_close_pct', 0.0) if partial else 0.0,
                        )
                        logger.debug(f"開倉(legacy close)：{direction}，價格：{entry_price:.2f}")
                    else:
                        # next_open（預設）：掛單，下一根開盤成交。最後一根無下一根 → 放棄此訊號
                        pending_entry = {'direction': direction, 'atr': atr}

            # === 4. 記錄資金曲線（用當根收盤價標記）===
            equity = capital
            if current_position:
                current_position.update_pnl(current_price)
                equity += current_position.unrealized_pnl

            equity_curve.append({
                'timestamp': current_time,
                'equity': equity,
            })
        
        # 如果還有持倉，強制平倉（成交價加滑點）
        if current_position:
            last_price = primary_data.iloc[-1]['close']
            last_time = primary_data.iloc[-1]['timestamp']
            is_buy_to_close = current_position.direction == 'short'
            last_price = self._apply_slippage(last_price, is_buy_to_close)

            trade = Trade(
                strategy_id=strategy.get_id(),
                symbol=current_position.symbol,
                direction=current_position.direction,
                entry_time=current_position.entry_time,
                exit_time=last_time,
                entry_price=current_position.entry_price,
                exit_price=last_price,
                size=current_position.size,
                leverage=current_position.leverage,
                exit_reason="回測結束",
            )
            trade.calculate_pnl(self.commission)
            capital += trade.pnl
            trades.append(trade)
        
        # 創建回測結果
        result = BacktestResult(
            strategy_id=strategy.get_id(),
            start_date=primary_data.iloc[0]['timestamp'] if len(primary_data) > 0 else start_date or datetime.now(),
            end_date=primary_data.iloc[-1]['timestamp'] if len(primary_data) > 0 else end_date or datetime.now(),
            initial_capital=self.initial_capital,
            final_capital=capital,
            trades=trades,
            equity_curve=pd.DataFrame(equity_curve),
        )
        
        # 計算績效指標
        result.calculate_metrics()
        
        logger.info(f"回測完成：{len(trades)} 筆交易，最終資金：{capital:.2f} USDT")
        
        return result
    
    def _select_primary_timeframe(
        self,
        timeframes: List[str],
        market_data: Dict[str, pd.DataFrame]
    ) -> str:
        """選擇主週期用於遍歷
        
        優先選擇 1h 週期以平衡交易機會和性能
        如果沒有 1h，則選擇最小的週期
        
        Args:
            timeframes: 策略使用的週期列表
            market_data: 市場數據
        
        Returns:
            str: 主週期
        """
        # 優先使用 1h 週期（平衡性能和交易機會）
        if '1h' in timeframes and '1h' in market_data:
            return '1h'
        
        # 週期優先級（從小到大）
        timeframe_priority = {
            '1m': 1, '3m': 2, '5m': 3, '15m': 4, '30m': 5,
            '1h': 6, '2h': 7, '4h': 8, '6h': 9, '8h': 10, '12h': 11,
            '1d': 12, '3d': 13, '1w': 14, '1M': 15
        }
        
        # 找出可用的最小週期
        available_timeframes = [tf for tf in timeframes if tf in market_data]
        
        if not available_timeframes:
            raise ValueError("沒有可用的週期數據")
        
        # 按優先級排序，選擇最小的週期
        available_timeframes.sort(key=lambda x: timeframe_priority.get(x, 999))
        
        return available_timeframes[0]
    
    def _build_market_data(
        self,
        symbol: str,
        timestamp: datetime,
        market_data: Dict[str, pd.DataFrame],
        current_idx: int
    ) -> MarketData:
        """構建 MarketData 對象
        
        使用智能時間對齊：對於較大週期（如1d），使用最近的可用數據
        
        Args:
            symbol: 交易對
            timestamp: 當前時間
            market_data: 市場數據
            current_idx: 當前索引
        
        Returns:
            MarketData: 市場數據對象
        """
        timeframes = {}
        
        for timeframe, df in market_data.items():
            # 獲取到當前時間為止的所有數據
            historical_data = df[df['timestamp'] <= timestamp].copy()
            
            # 如果沒有數據，說明當前時間早於該週期的第一個數據點
            if len(historical_data) == 0:
                logger.debug(f"週期 {timeframe} 在時間 {timestamp} 之前沒有數據")
                continue
            
            # 計算指標（簡化版本，只計算 ATR）
            indicators = {}
            if len(historical_data) >= 14:
                # 計算 ATR
                high_low = historical_data['high'] - historical_data['low']
                high_close = abs(historical_data['high'] - historical_data['close'].shift())
                low_close = abs(historical_data['low'] - historical_data['close'].shift())
                true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
                atr = true_range.rolling(window=14).mean()
                indicators['atr'] = atr
            
            timeframes[timeframe] = TimeframeData(
                timeframe=timeframe,
                ohlcv=historical_data,
                indicators=indicators,
            )
        
        return MarketData(
            symbol=symbol,
            timestamp=timestamp,
            timeframes=timeframes,
        )
    
    def run_multi_strategy(
        self,
        strategies: List[Strategy],
        market_data: Dict[str, pd.DataFrame],
        capital_allocation: Dict[str, float],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, BacktestResult]:
        """回測多策略組合
        
        Args:
            strategies: 策略列表
            market_data: 市場數據
            capital_allocation: 資金分配（策略 ID -> 比例）
            start_date: 開始日期
            end_date: 結束日期
        
        Returns:
            Dict[str, BacktestResult]: 策略 ID -> 回測結果
        """
        logger.info(f"開始多策略回測：{len(strategies)} 個策略")
        
        results = {}
        
        for strategy in strategies:
            strategy_id = strategy.get_id()
            
            # 獲取該策略的資金分配
            allocation = capital_allocation.get(strategy_id, 1.0 / len(strategies))
            strategy_capital = self.initial_capital * allocation
            
            # 創建獨立的回測引擎（沿用滑點與成交時點設定）
            engine = BacktestEngine(strategy_capital, self.commission, self.slippage, self.fill_timing)
            
            # 回測該策略
            result = engine.run_single_strategy(
                strategy,
                market_data,
                start_date,
                end_date
            )
            
            results[strategy_id] = result
        
        logger.info(f"多策略回測完成")
        
        return results
    
    def calculate_metrics(self, trades: List[Trade]) -> Dict:
        """計算績效指標
        
        Args:
            trades: 交易列表
        
        Returns:
            Dict: 績效指標
        """
        if not trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'total_pnl': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'profit_factor': 0.0,
            }
        
        # 基本統計
        total_trades = len(trades)
        winning_trades = [t for t in trades if t.pnl > 0]
        losing_trades = [t for t in trades if t.pnl < 0]
        
        win_count = len(winning_trades)
        loss_count = len(losing_trades)
        
        # 勝率
        win_rate = win_count / total_trades if total_trades > 0 else 0.0
        
        # 損益統計
        total_pnl = sum(t.pnl for t in trades)
        total_win = sum(t.pnl for t in winning_trades)
        total_loss = abs(sum(t.pnl for t in losing_trades))
        
        avg_win = total_win / win_count if win_count > 0 else 0.0
        avg_loss = total_loss / loss_count if loss_count > 0 else 0.0
        
        # 獲利因子
        profit_factor = total_win / total_loss if total_loss > 0 else 0.0
        
        return {
            'total_trades': total_trades,
            'winning_trades': win_count,
            'losing_trades': loss_count,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
        }
