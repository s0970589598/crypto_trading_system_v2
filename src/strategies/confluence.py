"""
訊號共振策略（Phase G）

只在「主來源進場訊號」+「≥min_confirm 個確認來源同向」時才進場——測試
「多訊號齊發時勝率是否較高」。出場/部位全委派主來源（primary）。

用法：
    conf = ConfluenceStrategy(config, primary=v11, confirmations=[v9, v10], min_confirm=2)
min_confirm=0 等於「主來源單獨」（無共振），方便對照。

來源可以是任何 Strategy（不同策略、或同策略不同時框的包裝）；confirmations 只取其
generate_signal 的方向當「票」，不用它們的出場。
"""

from typing import List, Optional

from src.execution.strategy import Strategy
from src.models.config import StrategyConfig
from src.models.market_data import MarketData
from src.models.trading import Signal


class ConfluenceStrategy(Strategy):
    def __init__(
        self,
        config: StrategyConfig,
        primary: Strategy,
        confirmations: Optional[List[Strategy]] = None,
        min_confirm: int = 1,
    ):
        super().__init__(config)
        self._primary = primary
        self._confirmations = confirmations or []
        self._min_confirm = min_confirm

    def prepare(self, market_data: dict) -> None:
        self._primary.prepare(market_data)
        for c in self._confirmations:
            c.prepare(market_data)

    def generate_signal(self, market_data: MarketData) -> Signal:
        sig = self._primary.generate_signal(market_data)  # 同時 stash 主來源出場脈絡
        if sig.action not in ('BUY', 'SELL'):
            return sig
        # 數確認來源同向票數
        agree = sum(
            1 for c in self._confirmations
            if c.generate_signal(market_data).action == sig.action
        )
        if agree >= self._min_confirm:
            return sig
        return Signal.hold(self.strategy_id, market_data.timestamp, self.symbol)

    # ---- 出場 / 部位 / gating 全委派主來源 ----
    def calculate_position_size(self, capital: float, price: float) -> float:
        return self._primary.calculate_position_size(capital, price)

    def calculate_stop_loss(self, entry_price: float, direction: str, atr: float) -> float:
        return self._primary.calculate_stop_loss(entry_price, direction, atr)

    def calculate_take_profit(self, entry_price: float, direction: str, atr: float) -> float:
        return self._primary.calculate_take_profit(entry_price, direction, atr)

    def get_partial_take_profit(self, entry_price: float, direction: str, atr: float) -> Optional[dict]:
        return self._primary.get_partial_take_profit(entry_price, direction, atr)

    def get_mfe_protection(self, entry_price: float, direction: str, atr: float) -> Optional[dict]:
        return self._primary.get_mfe_protection(entry_price, direction, atr)

    def get_time_stop(self, entry_price: float, direction: str, atr: float) -> Optional[dict]:
        return self._primary.get_time_stop(entry_price, direction, atr)

    def should_exit(self, position, market_data: MarketData) -> bool:
        return self._primary.should_exit(position, market_data)

    def on_trade_closed(self, trade, bar_index: int) -> None:
        self._primary.on_trade_closed(trade, bar_index)

    def can_enter(self, bar_index: int) -> bool:
        return self._primary.can_enter(bar_index)
