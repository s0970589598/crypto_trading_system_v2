"""
ScalpingAdapter（Phase B3）：把向量化 scalping 策略接進逐根 Strategy(ABC) 閉環

crypto_bot 的 scalping（如 v11）是「向量化、一次吃整段 df」的介面：
- generate_signals(df) -> df（加 long_signal/short_signal/regime/atr/position_scale 欄位）
- get_exit_levels(entry_price, direction, atr, regime) -> dict（stop_loss/tp1/tp2/
  tp1_close_pct/use_mfe_protection/mfe_trigger_pct/mfe_protection_floor_pct）

本 adapter 以 duck-typing 包裝「任何符合上述介面的物件」（不直接 import v11，
避免跨 repo 與 pandas_ta 依賴；真實 v11 的接線於 repo 合併時用 from-config 工廠完成）。

橋接方式：
- prepare()：迴圈前一次跑完 generate_signals、依 timestamp 快取訊號（避免逐根 O(n²)）。
  已驗證 v11 指標皆向後 rolling，無 look-ahead，故預算整段安全。
- generate_signal()：逐根查表回 BUY/SELL/HOLD，並暫存該訊號根的 regime/atr/scale。
- 出場/部位：用 get_exit_levels 以「實際成交價」算 SL / tp2 / tp1（分批，走 B1）/
  MFE（走 B2），對齊 scalping 實盤行為。

未建模（標「估計偏樂觀」，需跨交易狀態，待後續 stateful 機制）：時間停損、
權益守護者 gating、部位的權益縮放（此處權益縮放固定為 1.0，僅保留波動縮放）。
"""

from typing import Optional, Any

import pandas as pd

from src.execution.strategy import Strategy
from src.models.config import StrategyConfig
from src.models.market_data import MarketData
from src.models.trading import Signal


class ScalpingAdapter(Strategy):
    """把向量化 scalping 策略包成逐根 Strategy(ABC)"""

    def __init__(
        self,
        config: StrategyConfig,
        vectorized_strategy: Any,
        timeframe: Optional[str] = None,
        base_position_pct: Optional[float] = None,
    ):
        """初始化

        Args:
            config: 策略配置
            vectorized_strategy: 具 generate_signals(df) 與 get_exit_levels(...) 的物件
            timeframe: 主週期（None 取 config.timeframes[0]，需與引擎選的主週期一致）
            base_position_pct: 基礎倉位比例（None 取 config.risk_management.position_size）
        """
        super().__init__(config)
        self._vec = vectorized_strategy
        self._timeframe = timeframe or (config.timeframes[0] if config.timeframes else None)
        self._base_pct = (base_position_pct if base_position_pct is not None
                          else config.risk_management.position_size)
        self._signals = {}        # timestamp -> {'action','direction','regime','atr','scale'}
        # 暫存當前訊號根脈絡（fill 在下一根，出場/部位計算用）
        self._cur_regime = 'mid'
        self._cur_atr = 0.0
        self._cur_scale = 1.0

    def prepare(self, market_data: dict) -> None:
        """迴圈前一次算完整段訊號並依 timestamp 快取"""
        if self._timeframe is None or self._timeframe not in market_data:
            return
        df = market_data[self._timeframe].copy()
        # v11 的時段過濾用 df.index.hour，需 datetime index；保留 timestamp 欄位對齊用
        if 'timestamp' in df.columns:
            df = df.set_index('timestamp', drop=False)

        out = self._vec.generate_signals(df)
        has_ts = 'timestamp' in out.columns
        for idx, row in out.iterrows():
            key = row['timestamp'] if has_ts else idx
            if bool(row.get('long_signal', False)):
                action, direction = 'BUY', 'long'
            elif bool(row.get('short_signal', False)):
                action, direction = 'SELL', 'short'
            else:
                action, direction = 'HOLD', None
            atr_val = row.get('atr', None)
            self._signals[key] = {
                'action': action,
                'direction': direction,
                'regime': row.get('regime', 'mid'),
                'atr': float(atr_val) if pd.notna(atr_val) else 0.0,
                'scale': float(row.get('position_scale', 1.0)),
            }

    def generate_signal(self, market_data: MarketData) -> Signal:
        ts = market_data.timestamp
        info = self._signals.get(ts)
        if info is None or info['action'] == 'HOLD':
            return Signal.hold(self.strategy_id, ts, self.symbol)
        # 暫存訊號根脈絡（成交在下一根，屆時 calculate_* 會用到）
        self._cur_regime = info['regime']
        self._cur_atr = info['atr']
        self._cur_scale = info['scale']
        return Signal(
            strategy_id=self.strategy_id, timestamp=ts, symbol=self.symbol,
            action=info['action'], direction=info['direction'],
            entry_price=0.0, stop_loss=0.0, take_profit=0.0,
            position_size=0.0, confidence=1.0,
        )

    def _exit_levels(self, entry_price: float, direction: str) -> dict:
        # 不同 scalping 版本 get_exit_levels 簽章有別：v10/v11 吃 regime、v8~v9 不吃。
        # 先試帶 regime，簽章不合(TypeError)再退回不帶。
        try:
            return self._vec.get_exit_levels(
                entry_price, direction, self._cur_atr, self._cur_regime)
        except TypeError:
            return self._vec.get_exit_levels(entry_price, direction, self._cur_atr)

    def calculate_position_size(self, capital: float, price: float) -> float:
        # 波動縮放（position_scale）；權益縮放延後（固定 1.0）
        if price <= 0:
            return 0.0
        return (capital * self._base_pct * self._cur_scale) / price

    def calculate_stop_loss(self, entry_price: float, direction: str, atr: float) -> float:
        return self._exit_levels(entry_price, direction)['stop_loss']

    def calculate_take_profit(self, entry_price: float, direction: str, atr: float) -> float:
        return self._exit_levels(entry_price, direction)['tp2']

    def get_partial_take_profit(self, entry_price: float, direction: str, atr: float) -> Optional[dict]:
        lv = self._exit_levels(entry_price, direction)
        if lv.get('tp1') is None:
            return None
        return {'tp1': lv['tp1'], 'tp1_close_pct': lv.get('tp1_close_pct', 0.0)}

    def get_mfe_protection(self, entry_price: float, direction: str, atr: float) -> Optional[dict]:
        lv = self._exit_levels(entry_price, direction)
        if not lv.get('use_mfe_protection', False):
            return None
        return {
            'mfe_trigger_pct': lv.get('mfe_trigger_pct', 0.0),
            'mfe_protection_floor_pct': lv.get('mfe_protection_floor_pct', 0.0),
        }

    def get_time_stop(self, entry_price: float, direction: str, atr: float) -> Optional[dict]:
        lv = self._exit_levels(entry_price, direction)
        if not lv.get('use_time_stop', False):
            return None
        return {
            'start': lv.get('time_stop_start', 0),
            'end': lv.get('time_stop_end', 0),
            'cost_zone_pct': lv.get('cost_zone_pct', 0.0),
        }

    def should_exit(self, position, market_data: MarketData) -> bool:
        # scalping 出場由 SL/tp1/tp2/MFE 處理，無額外收盤出場
        return False


class ScalpingV11(ScalpingAdapter):
    """真實 v11 的 from-config 版：可直接當 strategy_class 給 Optimizer/StrategyManager。

    config.parameters 覆寫 v11 預設（全部參數皆有預設，空 dict = 全預設）。
    v11 import 放在 __init__ 內，故本模組在無 pandas_ta 的環境仍可 import，
    只有實例化 ScalpingV11 時才需要 pandas_ta（需 Python <=3.13）。
    """
    def __init__(self, config: StrategyConfig):
        from src.strategies.scalping_high_leverage_v11 import ScalpingHighLeverageV11
        v11 = ScalpingHighLeverageV11(**(config.parameters or {}))
        super().__init__(config, v11)

    def on_trade_closed(self, trade, bar_index: int) -> None:
        guardian = getattr(self._vec, 'equity_guardian', None)
        if guardian is not None:
            guardian.record_trade(trade.pnl, bar_index)

    def can_enter(self, bar_index: int) -> bool:
        # 權益守護者連虧/連勝冷卻 gating（equity_scale 部位縮放未建模，維持 v11 預設 1.0）
        guardian = getattr(self._vec, 'equity_guardian', None)
        return guardian.can_trade(bar_index) if guardian is not None else True
