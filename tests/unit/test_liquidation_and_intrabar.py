"""
回測引擎 Phase A2 測試：強平（爆倉）模擬 + 盤中（intrabar）止損/止盈觸發

驗證：
1. Position.liquidation_price() 公式正確。
2. 高槓桿部位當根低點觸及強平價 → 以強平價平倉、虧損約等於保證金。
3. 盤中止損：當根低點刺穿止損價、但收盤價在止損之上 → 仍觸發止損
   （舊版只看收盤價會漏掉，導致低估虧損）。
4. 盤中止盈：當根高點觸及止盈、收盤在其下 → 觸發止盈。
5. 保守順序：同一根同時觸及止損與止盈 → 以不利方向（止損）成交。
"""

import pandas as pd
from datetime import datetime, timedelta

from src.execution.backtest_engine import BacktestEngine
from src.execution.strategy import Strategy
from src.models.config import StrategyConfig, RiskManagement, ExitConditions
from src.models.trading import Signal, Position
from src.models.market_data import MarketData


# ---------------------------------------------------------------------------
# 可控策略：在第一次呼叫發一次進場訊號，止損/止盈以進場價倍數設定（None=停用）
# ---------------------------------------------------------------------------

class _ControlledStrategy(Strategy):
    def __init__(self, config, action='BUY', sl_mult=None, tp_mult=None):
        super().__init__(config)
        self._action = action
        self._sl_mult = sl_mult
        self._tp_mult = tp_mult
        self._fired = False

    def generate_signal(self, market_data: MarketData) -> Signal:
        if not self._fired:
            self._fired = True
            return Signal(
                strategy_id=self.config.strategy_id,
                timestamp=market_data.timestamp,
                symbol=self.config.symbol,
                action=self._action,
                direction='long' if self._action == 'BUY' else 'short',
                entry_price=0.0, stop_loss=0.0, take_profit=0.0,
                position_size=0.0, confidence=1.0,
            )
        return Signal.hold(self.config.strategy_id, market_data.timestamp, self.config.symbol)

    def calculate_position_size(self, capital: float, price: float) -> float:
        return (capital * self.config.risk_management.position_size) / price

    def calculate_stop_loss(self, entry_price: float, direction: str, atr: float) -> float:
        return entry_price * self._sl_mult if self._sl_mult is not None else 0.0

    def calculate_take_profit(self, entry_price: float, direction: str, atr: float) -> float:
        return entry_price * self._tp_mult if self._tp_mult is not None else 0.0

    def should_exit(self, position, market_data: MarketData) -> bool:
        return False


def _make_config(leverage: int = 1) -> StrategyConfig:
    return StrategyConfig(
        strategy_id="a2-test", strategy_name="A2 Test", version="1.0.0",
        enabled=True, symbol="BTCUSDT", timeframes=["1h"], parameters={},
        risk_management=RiskManagement(
            position_size=0.1, leverage=leverage, max_trades_per_day=100,
            max_consecutive_losses=99, daily_loss_limit=0.99,
            stop_loss_atr=1.5, take_profit_atr=3.0,
        ),
        entry_conditions=[], exit_conditions=ExitConditions(stop_loss="", take_profit=""),
    )


def _make_data(overrides: dict, n: int = 10, entry_open: float = 100.0):
    """中性 K 線（範圍 [99.5, 100.5] 圍繞 100），指定 bar 用 overrides=(o,h,l,c) 覆寫。

    BUY 在 bar0 發出、bar1 開盤成交，故 bar1 open 設為 entry_open。
    """
    rows = []
    t0 = datetime(2024, 1, 1)
    for k in range(n):
        if k in overrides:
            o, h, l, c = overrides[k]
        elif k == 1:
            o, h, l, c = entry_open, 100.5, 99.5, 100.0
        else:
            o, h, l, c = 100.0, 100.5, 99.5, 100.0
        rows.append({
            'timestamp': t0 + timedelta(hours=k),
            'open': o, 'high': h, 'low': l, 'close': c, 'volume': 1000.0,
        })
    return {"1h": pd.DataFrame(rows)}


# ---------------------------------------------------------------------------
# 1. 強平價公式
# ---------------------------------------------------------------------------

def test_liquidation_price_formula():
    long_pos = Position(strategy_id="s", symbol="BTCUSDT", direction='long',
                        entry_time=datetime(2024, 1, 1), entry_price=100.0,
                        size=1.0, stop_loss=0.0, take_profit=0.0, leverage=10)
    assert abs(long_pos.liquidation_price() - 90.0) < 1e-9  # 100*(1-1/10)

    short_pos = Position(strategy_id="s", symbol="BTCUSDT", direction='short',
                         entry_time=datetime(2024, 1, 1), entry_price=100.0,
                         size=1.0, stop_loss=0.0, take_profit=0.0, leverage=10)
    assert abs(short_pos.liquidation_price() - 110.0) < 1e-9  # 100*(1+1/10)

    # 槓桿 1：做多 0、做空 inf（實質永不強平）
    long1 = Position("s", "BTCUSDT", 'long', datetime(2024, 1, 1), 100.0, 1.0, 0.0, 0.0, 1)
    short1 = Position("s", "BTCUSDT", 'short', datetime(2024, 1, 1), 100.0, 1.0, 0.0, 0.0, 1)
    assert long1.liquidation_price() == 0.0
    assert short1.liquidation_price() == float('inf')


# ---------------------------------------------------------------------------
# 2. 強平觸發
# ---------------------------------------------------------------------------

def test_liquidation_triggers_for_high_leverage_long():
    # 10x 做多，entry=100 → 強平價 90。bar3 低點 89 < 90 → 爆倉。止損/止盈停用。
    engine = BacktestEngine(10000, commission=0.0, slippage=0.0, fill_timing='next_open')
    strat = _ControlledStrategy(_make_config(leverage=10), action='BUY')
    result = engine.run_single_strategy(strat, _make_data({3: (100.0, 100.0, 89.0, 95.0)}))

    assert len(result.trades) == 1
    t = result.trades[0]
    assert t.exit_reason == "強平"
    assert abs(t.exit_price - 90.0) < 1e-9
    assert t.pnl < 0  # 爆倉必虧


# ---------------------------------------------------------------------------
# 3. 盤中止損（收盤價在止損之上、仍觸發）
# ---------------------------------------------------------------------------

def test_intrabar_stop_loss_triggers_even_if_close_above():
    # 1x（無強平），SL=entry*0.98=98。bar3 低點 97.5 刺穿、收盤 99.5 在 SL 上。
    engine = BacktestEngine(10000, commission=0.0, slippage=0.0, fill_timing='next_open')
    strat = _ControlledStrategy(_make_config(leverage=1), action='BUY', sl_mult=0.98)
    result = engine.run_single_strategy(strat, _make_data({3: (100.0, 100.0, 97.5, 99.5)}))

    assert len(result.trades) == 1
    t = result.trades[0]
    assert t.exit_reason == "止損"
    assert abs(t.exit_price - 98.0) < 1e-9
    # 出場發生在 bar3，而非被拖到回測結束
    assert t.exit_time == datetime(2024, 1, 1) + timedelta(hours=3)


# ---------------------------------------------------------------------------
# 4. 盤中止盈
# ---------------------------------------------------------------------------

def test_intrabar_take_profit_triggers_even_if_close_below():
    # 1x，TP=entry*1.02=102。bar3 高點 102.5 觸及、收盤 100.5 在 TP 下。
    engine = BacktestEngine(10000, commission=0.0, slippage=0.0, fill_timing='next_open')
    strat = _ControlledStrategy(_make_config(leverage=1), action='BUY', tp_mult=1.02)
    result = engine.run_single_strategy(strat, _make_data({3: (100.0, 102.5, 99.5, 100.5)}))

    assert len(result.trades) == 1
    t = result.trades[0]
    assert t.exit_reason == "獲利"
    assert abs(t.exit_price - 102.0) < 1e-9


# ---------------------------------------------------------------------------
# 5. 保守順序：同根同時觸及止損與止盈 → 止損優先
# ---------------------------------------------------------------------------

def test_same_bar_sl_and_tp_takes_stop_loss_conservatively():
    # SL=98、TP=102。bar3 低 97（觸 SL）且高 103（觸 TP）→ 保守取止損。
    engine = BacktestEngine(10000, commission=0.0, slippage=0.0, fill_timing='next_open')
    strat = _ControlledStrategy(_make_config(leverage=1), action='BUY',
                                sl_mult=0.98, tp_mult=1.02)
    result = engine.run_single_strategy(strat, _make_data({3: (100.0, 103.0, 97.0, 100.0)}))

    assert len(result.trades) == 1
    assert result.trades[0].exit_reason == "止損"
    assert abs(result.trades[0].exit_price - 98.0) < 1e-9
