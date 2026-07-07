"""
在 BingX 真實資料上，用誠實閉環(引擎+walk-forward+成功門檻)驗證一支策略。

取代先前散落的一次性驗證腳本。抓 BingX OHLCV → 經 adapter 接進 StrategySelector →
印出樣本外(OOS)結果與是否過關。不下單、只抓公開行情。

需 Python <=3.13 + pandas_ta + ccxt(+ scipy for harmonic)：
    uv run --python 3.13 --with pandas_ta --with ccxt --with scipy \\
        python tools/validate_on_bingx.py --strategy v11 --timeframe 1m --bars 15000

策略名見 REGISTRY（scalping 家族 / adx / harmonic / demigod / multifactor）。
"""
import argparse
import os
import sys
import time
from importlib import import_module

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ccxt
import pandas as pd

from src.strategies.scalping_adapter import ScalpingAdapter, DataFrameSignalAdapter
from src.analysis.strategy_selector import StrategySelector, SuccessCriteria
from src.models.config import StrategyConfig, RiskManagement, ExitConditions

# name -> (adapter_kind, module, classname)。scalping=有 get_exit_levels；df=出場寫在欄位
REGISTRY = {
    'scalping':    ('scalping', 'scalping_high_leverage', 'ScalpingHighLeverage'),
    'v8_5':        ('scalping', 'scalping_high_leverage_v8_5', 'ScalpingHighLeverageV85'),
    'v8_6':        ('scalping', 'scalping_high_leverage_v8_6', 'ScalpingHighLeverageV86'),
    'v9':          ('scalping', 'scalping_high_leverage_v9', 'ScalpingHighLeverage'),
    'v10':         ('scalping', 'scalping_high_leverage_v10', 'ScalpingHighLeverageV10'),
    'v11':         ('scalping', 'scalping_high_leverage_v11', 'ScalpingHighLeverageV11'),
    'adx':         ('df', 'adx_volatility_1m', 'ADXVolatility1M'),
    'harmonic':    ('df', 'harmonic_advanced', 'HarmonicAdvancedStrategy'),
    'demigod':     ('df', 'demigod_macd', 'DemigodMacdStrategy'),
    'multifactor': ('df', 'multi_factor_short', 'MultiFactorShort'),
}


def fetch_bingx(symbol, timeframe, n):
    ex = ccxt.bingx()
    ex.load_markets()
    if symbol not in ex.markets:
        symbol = 'BTC/USDT'
    tf_ms = ex.parse_timeframe(timeframe) * 1000
    rows, cur = [], ex.milliseconds() - n * tf_ms
    while len(rows) < n:
        batch = ex.fetch_ohlcv(symbol, timeframe, since=cur, limit=1000)
        if not batch:
            break
        rows += batch
        cur = batch[-1][0] + tf_ms
        if len(batch) < 1000:
            break
        time.sleep(ex.rateLimit / 1000)
    df = pd.DataFrame(rows, columns=['ts', 'open', 'high', 'low', 'close', 'volume']).drop_duplicates('ts')
    df['timestamp'] = pd.to_datetime(df['ts'], unit='ms')
    return df.drop(columns='ts').reset_index(drop=True)


def make_strategy_class(name, timeframe):
    kind, module, classname = REGISTRY[name]
    vec_class = getattr(import_module(f'src.strategies.{module}'), classname)
    base = ScalpingAdapter if kind == 'scalping' else DataFrameSignalAdapter

    class _S(base):
        def __init__(self, config):
            base.__init__(self, config, vec_class(**(config.parameters or {})),
                          timeframe=timeframe)
    _S.__name__ = classname
    return _S


def config_for(timeframe, leverage):
    return StrategyConfig(
        strategy_id="validate", strategy_name="validate", version="1.0.0", enabled=True,
        symbol="BTCUSDT", timeframes=[timeframe], parameters={},
        risk_management=RiskManagement(position_size=0.2, leverage=leverage, max_trades_per_day=9999,
            max_consecutive_losses=9999, daily_loss_limit=0.99, stop_loss_atr=1.5, take_profit_atr=3.0),
        entry_conditions=[], exit_conditions=ExitConditions(stop_loss="", take_profit=""))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--strategy', required=True, choices=list(REGISTRY))
    p.add_argument('--timeframe', default='1m')
    p.add_argument('--bars', type=int, default=15000)
    p.add_argument('--leverage', type=int, default=10)
    p.add_argument('--windows', type=int, default=4)
    p.add_argument('--symbol', default='BTC/USDT:USDT')
    a = p.parse_args()

    df = fetch_bingx(a.symbol, a.timeframe, a.bars)
    print(f"{a.strategy} @ {a.timeframe}: {len(df)} 根 "
          f"({df['timestamp'].iloc[0]} ~ {df['timestamp'].iloc[-1]})")

    sel = StrategySelector({a.timeframe: df}, criteria=SuccessCriteria(),
                           slippage=0.0005, benchmark_timeframe=a.timeframe)
    cand = [{'name': a.strategy,
             'strategy_class': make_strategy_class(a.strategy, a.timeframe),
             'base_config': config_for(a.timeframe, a.leverage).to_dict()}]
    res = sel.evaluate(cand, {}, n_windows=a.windows, initial_train_ratio=0.4)
    r = res.results[0]
    print(f"  過關: {'✅' if r.passed else '❌'}")
    print(f"  OOS Sharpe: {r.oos_sharpe:.3f}  (門檻 >= {res.criteria.min_oos_sharpe})")
    print(f"  OOS 報酬: {r.oos_cumulative_return_pct:.2f}%   抱 BTC: {r.benchmark_return_pct:.2f}%")
    print(f"  OOS 交易數: {r.walk_forward.total_oos_trades}   最差回撤: {r.worst_drawdown_pct:.2f}%")
    if r.failures:
        print("  未過:", "; ".join(r.failures))


if __name__ == '__main__':
    main()
