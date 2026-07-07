"""Phase G：ConfluenceStrategy — 需 ≥min_confirm 個確認來源同向才進場。"""
from datetime import datetime

from src.strategies.confluence import ConfluenceStrategy
from src.execution.strategy import Strategy
from src.models.config import StrategyConfig, RiskManagement, ExitConditions
from src.models.trading import Signal
from src.models.market_data import MarketData


class _Fake(Strategy):
    def __init__(self, config, action):
        super().__init__(config)
        self._action = action

    def generate_signal(self, md):
        if self._action == 'HOLD':
            return Signal.hold(self.strategy_id, md.timestamp, self.symbol)
        direction = 'long' if self._action == 'BUY' else 'short'
        return Signal(self.strategy_id, md.timestamp, self.symbol, self._action,
                      direction, 0.0, 0.0, 0.0, 0.0, 1.0)

    def calculate_position_size(self, capital, price):
        return 0.01

    def calculate_stop_loss(self, entry, direction, atr):
        return entry * 0.98

    def calculate_take_profit(self, entry, direction, atr):
        return entry * 1.02

    def should_exit(self, position, md):
        return False


def _cfg():
    return StrategyConfig(strategy_id="conf", strategy_name="c", version="1.0.0", enabled=True,
        symbol="BTCUSDT", timeframes=["1m"], parameters={},
        risk_management=RiskManagement(position_size=0.1, leverage=1, max_trades_per_day=9,
            max_consecutive_losses=9, daily_loss_limit=0.9, stop_loss_atr=1.5, take_profit_atr=3.0),
        entry_conditions=[], exit_conditions=ExitConditions(stop_loss="", take_profit=""))


def _md():
    return MarketData(symbol="BTCUSDT", timestamp=datetime(2024, 1, 1), timeframes={})


def test_confluence_requires_min_confirm():
    cfg = _cfg()
    primary = _Fake(cfg, 'BUY')
    # 2 確認都同向 + min_confirm=2 → 進場
    c2 = ConfluenceStrategy(cfg, primary, [_Fake(cfg, 'BUY'), _Fake(cfg, 'BUY')], min_confirm=2)
    assert c2.generate_signal(_md()).action == 'BUY'
    # 只 1 個確認 → 不足門檻 → HOLD
    c1 = ConfluenceStrategy(cfg, primary, [_Fake(cfg, 'BUY'), _Fake(cfg, 'HOLD')], min_confirm=2)
    assert c1.generate_signal(_md()).action == 'HOLD'
    # min_confirm=0 → 主來源單獨 → BUY
    c0 = ConfluenceStrategy(cfg, primary, [_Fake(cfg, 'HOLD')], min_confirm=0)
    assert c0.generate_signal(_md()).action == 'BUY'


def test_confluence_primary_hold_stays_hold():
    cfg = _cfg()
    conf = ConfluenceStrategy(cfg, _Fake(cfg, 'HOLD'),
                              [_Fake(cfg, 'BUY'), _Fake(cfg, 'BUY')], min_confirm=1)
    assert conf.generate_signal(_md()).action == 'HOLD'  # 主來源沒訊號就不進


def test_confluence_delegates_exits_to_primary():
    cfg = _cfg()
    conf = ConfluenceStrategy(cfg, _Fake(cfg, 'BUY'), [], min_confirm=0)
    assert conf.calculate_stop_loss(100.0, 'long', 1.0) == 98.0
    assert conf.calculate_take_profit(100.0, 'long', 1.0) == 102.0
