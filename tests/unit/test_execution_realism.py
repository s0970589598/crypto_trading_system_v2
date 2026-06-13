"""
回測引擎執行真實性測試（Phase A1：滑點 + next-open 成交、修同根 look-ahead）

驗證 BacktestEngine 的兩項修正：
1. 滑點（slippage）：每次成交價朝不利方向偏移，使回測獲利不再系統性高估。
2. next-open 成交：訊號在第 i 根產生、第 i+1 根「開盤價」成交，
   而非舊行為「看到第 i 根收盤價又用該收盤價成交」（同根 look-ahead）。
"""

import pandas as pd
from datetime import datetime, timedelta

from src.execution.backtest_engine import BacktestEngine
from src.execution.strategy import Strategy
from src.models.config import StrategyConfig, RiskManagement, ExitConditions
from src.models.trading import Signal
from src.models.market_data import MarketData


# ---------------------------------------------------------------------------
# 可控測試策略：在指定 index 發一次 BUY，永不主動出場，止損/目標設到永不觸發
# ---------------------------------------------------------------------------

class _BuyOnceStrategy(Strategy):
    def __init__(self, config: StrategyConfig, signal_index: int):
        super().__init__(config)
        self._signal_index = signal_index
        self._bar = -1

    def generate_signal(self, market_data: MarketData) -> Signal:
        self._bar += 1
        if self._bar == self._signal_index:
            return Signal(
                strategy_id=self.config.strategy_id,
                timestamp=market_data.timestamp,
                symbol=self.config.symbol,
                action='BUY',
                direction='long',
                entry_price=0.0,
                stop_loss=0.0,
                take_profit=0.0,
                position_size=0.0,
                confidence=1.0,
            )
        return Signal.hold(self.config.strategy_id, market_data.timestamp, self.config.symbol)

    def calculate_position_size(self, capital: float, price: float) -> float:
        return (capital * self.config.risk_management.position_size) / price

    def calculate_stop_loss(self, entry_price: float, direction: str, atr: float) -> float:
        return 0.0  # 做多時 price <= 0 永不止損

    def calculate_take_profit(self, entry_price: float, direction: str, atr: float) -> float:
        return 1e12  # 做多時 price >= 1e12 永不獲利了結

    def should_exit(self, position, market_data: MarketData) -> bool:
        return False


def _make_config() -> StrategyConfig:
    return StrategyConfig(
        strategy_id="exec-realism-test",
        strategy_name="Exec Realism Test",
        version="1.0.0",
        enabled=True,
        symbol="BTCUSDT",
        timeframes=["1h"],
        parameters={},
        risk_management=RiskManagement(
            position_size=0.1,
            leverage=1,
            max_trades_per_day=100,
            max_consecutive_losses=99,
            daily_loss_limit=0.99,
            stop_loss_atr=1.5,
            take_profit_atr=3.0,
        ),
        entry_conditions=[],
        exit_conditions=ExitConditions(stop_loss="", take_profit=""),
    )


def _make_market_data(n: int = 30):
    """每根 open 與 close 刻意不同，才能分辨『下一根 open 成交』vs『當根 close 成交』。

    open[k]  = 2000 + k
    close[k] = 1000 + k
    """
    rows = []
    t0 = datetime(2024, 1, 1)
    for k in range(n):
        open_p = 2000.0 + k
        close_p = 1000.0 + k
        high = max(open_p, close_p) + 5
        low = min(open_p, close_p) - 5
        rows.append({
            'timestamp': t0 + timedelta(hours=k),
            'open': open_p,
            'high': high,
            'low': low,
            'close': close_p,
            'volume': 1000.0,
        })
    return {"1h": pd.DataFrame(rows)}


# ---------------------------------------------------------------------------
# 測試
# ---------------------------------------------------------------------------

def test_next_open_fill_uses_next_bar_open_not_current_close():
    """next_open（預設）：第 i 根訊號 → 第 i+1 根 open 成交，不是第 i 根 close。"""
    signal_idx = 5
    engine = BacktestEngine(initial_capital=10000, commission=0.0, slippage=0.0,
                            fill_timing='next_open')
    result = engine.run_single_strategy(_BuyOnceStrategy(_make_config(), signal_idx),
                                        _make_market_data())
    assert len(result.trades) == 1
    # 第 i+1 根的 open = 2000 + (signal_idx + 1)
    assert result.trades[0].entry_price == 2000.0 + (signal_idx + 1)
    # 不應等於第 i 根的 close（舊 look-ahead 行為）
    assert result.trades[0].entry_price != 1000.0 + signal_idx


def test_legacy_close_fill_uses_current_bar_close():
    """fill_timing='close'（legacy）：第 i 根 close 立即成交，重現舊行為供對比。"""
    signal_idx = 5
    engine = BacktestEngine(initial_capital=10000, commission=0.0, slippage=0.0,
                            fill_timing='close')
    result = engine.run_single_strategy(_BuyOnceStrategy(_make_config(), signal_idx),
                                        _make_market_data())
    assert len(result.trades) == 1
    assert result.trades[0].entry_price == 1000.0 + signal_idx


def test_slippage_makes_long_entry_more_expensive():
    """滑點讓做多進場價變貴（朝不利方向）。"""
    signal_idx = 5
    base = BacktestEngine(10000, commission=0.0, slippage=0.0, fill_timing='next_open')
    slipped = BacktestEngine(10000, commission=0.0, slippage=0.001, fill_timing='next_open')

    r0 = base.run_single_strategy(_BuyOnceStrategy(_make_config(), signal_idx), _make_market_data())
    r1 = slipped.run_single_strategy(_BuyOnceStrategy(_make_config(), signal_idx), _make_market_data())

    fill = 2000.0 + (signal_idx + 1)
    assert r0.trades[0].entry_price == fill
    # 做多買進貴 0.1%
    assert abs(r1.trades[0].entry_price - fill * 1.001) < 1e-9
    assert r1.trades[0].entry_price > r0.trades[0].entry_price


def test_slippage_reduces_final_capital():
    """有滑點的最終資金應低於無滑點（驗收標準：滑點讓回測獲利下降）。"""
    signal_idx = 5
    no_slip = BacktestEngine(10000, commission=0.0, slippage=0.0, fill_timing='next_open')
    with_slip = BacktestEngine(10000, commission=0.0, slippage=0.001, fill_timing='next_open')

    r0 = no_slip.run_single_strategy(_BuyOnceStrategy(_make_config(), signal_idx), _make_market_data())
    r1 = with_slip.run_single_strategy(_BuyOnceStrategy(_make_config(), signal_idx), _make_market_data())

    assert r1.final_capital < r0.final_capital


def test_signal_on_last_bar_has_no_fill():
    """next_open 模式下，最後一根的訊號無下一根可成交 → 不應產生交易。"""
    n = 30
    engine = BacktestEngine(10000, commission=0.0, slippage=0.0, fill_timing='next_open')
    result = engine.run_single_strategy(_BuyOnceStrategy(_make_config(), n - 1),
                                        _make_market_data(n))
    assert len(result.trades) == 0
