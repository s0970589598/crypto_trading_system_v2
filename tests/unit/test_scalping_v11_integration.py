"""
Phase item3：真實 v11 接進誠實閉環的整合測試

證明 crypto_bot 的 ScalpingHighLeverageV11（用 pandas_ta 指標）能經 ScalpingV11 工廠
+ ScalpingAdapter 跑進 bingxHistory 的誠實引擎，產出有效回測結果。

需 pandas_ta（Python <=3.13）；無 pandas_ta 的環境（如預設 3.14）自動 skip。
"""

import pandas as pd
import pytest
from pathlib import Path

pytest.importorskip("pandas_ta")  # 3.14 無 llvmlite wheel → 跳過；3.13 + pandas_ta → 執行

from src.strategies.scalping_adapter import ScalpingV11
from src.execution.backtest_engine import BacktestEngine
from src.models.config import StrategyConfig, RiskManagement, ExitConditions


def _config():
    return StrategyConfig(
        strategy_id="scalping-v11", strategy_name="Scalping v11", version="1.0.0",
        enabled=True, symbol="BTCUSDT", timeframes=["1h"], parameters={},
        risk_management=RiskManagement(position_size=0.1, leverage=10, max_trades_per_day=999,
            max_consecutive_losses=999, daily_loss_limit=0.99, stop_loss_atr=1.5, take_profit_atr=3.0),
        entry_conditions=[], exit_conditions=ExitConditions(stop_loss="", take_profit=""))


def test_scalping_v11_runs_through_honest_engine():
    path = Path("market_data_BTCUSDT_1h.csv")
    if not path.exists():
        pytest.skip("無 BTCUSDT 1h 資料")
    df = pd.read_csv(path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.tail(500).reset_index(drop=True)  # 小切片求快
    market_data = {"1h": df}

    engine = BacktestEngine(1000, commission=0.0005, slippage=0.0005, fill_timing='next_open')
    strat = ScalpingV11(_config())
    result = engine.run_single_strategy(strat, market_data)

    assert result is not None
    assert result.total_trades >= 0  # 跑通即可（切片上可能 0 訊號）
    # 有交易的話，出場原因必來自引擎已建模的機制
    valid = {"止損", "強平", "獲利", "止盈tp1", "MFE保護", "時間停損", "策略出場", "回測結束"}
    for t in result.trades:
        assert t.exit_reason in valid, f"未預期的出場原因：{t.exit_reason}"
