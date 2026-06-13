"""
策略選擇器（閉環第 5 站：選最佳 + 把關）

吃多個候選策略的 walk-forward 結果，套用「成功定義」門檻，吐出通過、可部署的贏家。
門檻對應 ProposalOS / 量化北極星：
- out-of-sample Sharpe ≥ 1（扣手續費 + 滑點，由 Optimizer 帶 slippage 跑出）
- 累計 OOS 交易 ≥ 100（否則樣本無意義）
- OOS 最大回撤 ≤ 上限
- OOS 報酬贏過單純抱 BTC（buy-and-hold 基準）

達不到門檻就「不選」——這道閘門的價值在於阻止把過擬合 / 沒 edge 的策略推上實盤。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
import logging

import pandas as pd

from src.analysis.optimizer import Optimizer, WalkForwardResult


logger = logging.getLogger(__name__)


@dataclass
class SuccessCriteria:
    """成功門檻（對應成功定義；達不到就不部署）"""
    min_oos_sharpe: float = 1.0
    min_oos_trades: int = 100
    max_drawdown_pct: float = 20.0
    must_beat_benchmark: bool = True


@dataclass
class CandidateResult:
    """單一候選策略的評估結果"""
    name: str
    walk_forward: WalkForwardResult
    oos_cumulative_return_pct: float      # 各 OOS 窗複利後的累計報酬
    benchmark_return_pct: float           # 同 OOS 區段買入持有報酬
    worst_drawdown_pct: float             # 各 OOS 窗最大回撤中的最差者
    passed: bool
    failures: List[str] = field(default_factory=list)  # 未過的門檻說明

    @property
    def oos_sharpe(self) -> float:
        return self.walk_forward.mean_oos_score

    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'passed': self.passed,
            'failures': self.failures,
            'oos_sharpe': self.oos_sharpe,
            'oos_cumulative_return_pct': self.oos_cumulative_return_pct,
            'benchmark_return_pct': self.benchmark_return_pct,
            'worst_drawdown_pct': self.worst_drawdown_pct,
            'total_oos_trades': self.walk_forward.total_oos_trades,
            'overfit_gap': self.walk_forward.overfit_gap,
        }


@dataclass
class SelectionResult:
    """選擇結果"""
    criteria: SuccessCriteria
    results: List[CandidateResult]            # 依 OOS Sharpe 由高到低排序
    winner: Optional[CandidateResult]         # 通過門檻且 OOS Sharpe 最高者；無則 None

    def to_dict(self) -> dict:
        return {
            'criteria': self.criteria.__dict__,
            'winner': self.winner.name if self.winner else None,
            'results': [r.to_dict() for r in self.results],
        }


class StrategySelector:
    """策略選擇器：跑 walk-forward → 套成功門檻 → 選贏家"""

    def __init__(
        self,
        market_data: Dict[str, pd.DataFrame],
        criteria: Optional[SuccessCriteria] = None,
        initial_capital: float = 1000.0,
        commission: float = 0.0005,
        slippage: float = 0.0005,
        fill_timing: str = 'next_open',
        benchmark_timeframe: Optional[str] = None,
    ):
        """初始化

        Args:
            market_data: 市場數據（週期 -> DataFrame）
            criteria: 成功門檻（None 用預設）
            initial_capital / commission / slippage / fill_timing: 傳給 Optimizer/引擎
                （slippage 預設 0.0005，讓選擇基於誠實回測）
            benchmark_timeframe: 計算買入持有基準用的週期（None 取 market_data 第一個）
        """
        if not market_data:
            raise ValueError("market_data 不可為空")
        self.market_data = market_data
        self.criteria = criteria or SuccessCriteria()
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        self.fill_timing = fill_timing
        self.benchmark_timeframe = benchmark_timeframe or list(market_data.keys())[0]

    def _benchmark_return_pct(self, initial_train_ratio: float) -> float:
        """OOS 區段（initial_train_ratio 之後）的買入持有報酬%（贏過 BTC 的基準）"""
        df = self.market_data[self.benchmark_timeframe]
        split_idx = int(len(df) * initial_train_ratio)
        oos = df.iloc[split_idx:]
        if len(oos) < 2:
            return 0.0
        first_close = oos.iloc[0]['close']
        last_close = oos.iloc[-1]['close']
        if first_close <= 0:
            return 0.0
        return (last_close / first_close - 1) * 100

    @staticmethod
    def _compound_oos_return_pct(wf: WalkForwardResult) -> float:
        """各 OOS 窗報酬複利後的累計報酬%"""
        cumulative = 1.0
        for w in wf.window_results:
            cumulative *= (1 + w.get('oos_pnl_pct', 0.0) / 100)
        return (cumulative - 1) * 100

    @staticmethod
    def _worst_drawdown_pct(wf: WalkForwardResult) -> float:
        """各 OOS 窗最大回撤中的最差者"""
        dds = [w.get('oos_max_drawdown_pct', 0.0) for w in wf.window_results]
        return max(dds) if dds else 0.0

    def _check(self, wf: WalkForwardResult, cum_return: float,
               benchmark: float, worst_dd: float) -> List[str]:
        """套用門檻，回傳未過的項目（空 = 全過）"""
        c = self.criteria
        failures = []
        if wf.mean_oos_score < c.min_oos_sharpe:
            failures.append(f"OOS Sharpe {wf.mean_oos_score:.2f} < 門檻 {c.min_oos_sharpe}")
        if wf.total_oos_trades < c.min_oos_trades:
            failures.append(f"OOS 交易數 {wf.total_oos_trades} < 門檻 {c.min_oos_trades}")
        if worst_dd > c.max_drawdown_pct:
            failures.append(f"OOS 最大回撤 {worst_dd:.1f}% > 門檻 {c.max_drawdown_pct}%")
        if c.must_beat_benchmark and cum_return <= benchmark:
            failures.append(f"OOS 報酬 {cum_return:.1f}% 未贏過抱 BTC {benchmark:.1f}%")
        return failures

    def evaluate(
        self,
        candidates: List[Dict[str, Any]],
        param_grid: Dict[str, List[Any]],
        n_windows: int = 4,
        initial_train_ratio: float = 0.5,
        max_combinations: Optional[int] = None,
    ) -> SelectionResult:
        """評估候選策略並選出贏家

        Args:
            candidates: [{'name': str, 'strategy_class': type, 'base_config': dict}, ...]
            param_grid: 參數網格（傳給每個候選的 walk_forward）
            n_windows / initial_train_ratio / max_combinations: walk_forward 參數

        Returns:
            SelectionResult（依 OOS Sharpe 排序、含贏家或 None）
        """
        benchmark = self._benchmark_return_pct(initial_train_ratio)
        logger.info(f"OOS 買入持有基準報酬：{benchmark:.2f}%")

        results: List[CandidateResult] = []
        for cand in candidates:
            name = cand['name']
            logger.info(f"評估候選策略：{name}")
            optimizer = Optimizer(
                strategy_class=cand['strategy_class'],
                base_config=cand['base_config'],
                market_data=self.market_data,
                initial_capital=self.initial_capital,
                commission=self.commission,
                optimization_metric='sharpe_ratio',   # 以 OOS Sharpe 為準
                slippage=self.slippage,
                fill_timing=self.fill_timing,
            )
            wf = optimizer.walk_forward(
                param_grid,
                n_windows=n_windows,
                initial_train_ratio=initial_train_ratio,
                max_combinations=max_combinations,
            )
            cum_return = self._compound_oos_return_pct(wf)
            worst_dd = self._worst_drawdown_pct(wf)
            failures = self._check(wf, cum_return, benchmark, worst_dd)
            results.append(CandidateResult(
                name=name,
                walk_forward=wf,
                oos_cumulative_return_pct=cum_return,
                benchmark_return_pct=benchmark,
                worst_drawdown_pct=worst_dd,
                passed=len(failures) == 0,
                failures=failures,
            ))

        # 依 OOS Sharpe 由高到低排序
        results.sort(key=lambda r: r.walk_forward.mean_oos_score, reverse=True)
        # 贏家 = 通過門檻、OOS Sharpe 最高者
        winner = next((r for r in results if r.passed), None)

        logger.info(f"選擇完成：{len(results)} 個候選，"
                    f"贏家：{winner.name if winner else '無（皆未過門檻）'}")
        return SelectionResult(criteria=self.criteria, results=results, winner=winner)
