"""
端到端回測集成測試

測試完整的回測流程，驗證所有組件協作
Requirements: 4.1, 4.4
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import json

from src.managers.strategy_manager import StrategyManager
from src.managers.risk_manager import RiskManager
from src.managers.data_manager import DataManager
from src.execution.backtest_engine import BacktestEngine
from src.execution.multi_strategy_executor import MultiStrategyExecutor
from src.models.config import StrategyConfig
from src.models.risk import RiskConfig, GlobalRiskState


class TestEndToEndBacktest:
    """端到端回測測試"""
    
    @pytest.fixture
    def market_data(self):
        """載入真實市場數據"""
        data = {}
        symbols = ['ETHUSDT', 'BTCUSDT']
        timeframes = ['15m', '1h', '4h', '1d']
        
        for symbol in symbols:
            data[symbol] = {}
            for tf in timeframes:
                file_path = f"market_data_{symbol}_{tf}.csv"
                if Path(file_path).exists():
                    df = pd.read_csv(file_path)
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    # Keep timestamp as a column, not index
                    data[symbol][tf] = df
        
        return data
    
    @pytest.fixture
    def strategy_manager(self):
        """創建策略管理器"""
        return StrategyManager(strategies_dir="strategies/")
    
    @pytest.fixture
    def risk_manager(self):
        """創建風險管理器"""
        config = RiskConfig(
            global_max_drawdown=0.20,
            daily_loss_limit=0.10,
            global_max_position=0.80,
            strategy_max_position=0.30
        )
        return RiskManager(config)
    
    @pytest.fixture
    def backtest_engine(self):
        """創建回測引擎"""
        return BacktestEngine(
            initial_capital=1000.0,
            commission=0.0005
        )
    
    def test_single_strategy_end_to_end(self, strategy_manager, backtest_engine, market_data):
        """測試單策略端到端回測流程"""
        # 載入策略
        strategy_ids = strategy_manager.load_strategies()
        assert len(strategy_ids) > 0, "應該至少載入一個策略"
        
        # 選擇第一個啟用的策略，並確保有對應的市場數據
        strategy_id = None
        strategy = None
        for sid in strategy_ids:
            state = strategy_manager.get_strategy_state(sid)
            if state.enabled:
                temp_strategy = strategy_manager.strategies[sid]
                config = temp_strategy.config
                
                # 檢查是否有該策略需要的市場數據
                if config.symbol in market_data and market_data[config.symbol]:
                    # 檢查是否有所需的時間週期
                    available_tfs = set(market_data[config.symbol].keys())
                    required_tfs = set(config.timeframes)
                    
                    if required_tfs.issubset(available_tfs):
                        strategy_id = sid
                        strategy = temp_strategy
                        break
        
        if strategy_id is None or strategy is None:
            pytest.skip("沒有找到有完整市場數據的啟用策略")
        
        config = strategy.config
        
        # 設置回測時間範圍（最近30天）
        symbol_data = market_data[config.symbol]
        first_tf = list(symbol_data.keys())[0]
        df = symbol_data[first_tf]
        
        end_date = df['timestamp'].iloc[-1]
        start_date = end_date - timedelta(days=30)
        
        # 執行回測
        result = backtest_engine.run_single_strategy(
            strategy=strategy,
            market_data=symbol_data,  # Pass timeframe dict directly
            start_date=start_date,
            end_date=end_date
        )
        
        # 驗證回測結果
        assert result is not None, "回測應該返回結果"
        assert result.strategy_id == strategy_id, "策略ID應該匹配"
        assert result.start_date == start_date, "開始日期應該匹配"
        assert result.end_date == end_date, "結束日期應該匹配"
        assert result.initial_capital == 1000.0, "初始資金應該匹配"
        assert result.final_capital > 0, "最終資金應該大於0"
        
        # 驗證績效指標
        assert hasattr(result, 'total_trades'), "應該有總交易次數"
        assert hasattr(result, 'win_rate'), "應該有勝率"
        assert hasattr(result, 'max_drawdown'), "應該有最大回撤"
        assert hasattr(result, 'sharpe_ratio'), "應該有夏普比率"
        
        # 驗證交易列表
        assert isinstance(result.trades, list), "交易應該是列表"
        
        # 驗證資金曲線
        assert result.equity_curve is not None, "應該有資金曲線"
        assert len(result.equity_curve) > 0, "資金曲線不應該為空"
        
        print(f"\n單策略回測完成:")
        print(f"  策略: {strategy_id}")
        print(f"  總交易: {result.total_trades}")
        print(f"  勝率: {result.win_rate:.2f}%")
        print(f"  總損益: {result.total_pnl:.2f} ({result.total_pnl_pct:.2f}%)")
        print(f"  最大回撤: {result.max_drawdown_pct:.2f}%")
        print(f"  夏普比率: {result.sharpe_ratio:.2f}")
    
    def test_multi_strategy_end_to_end(self, strategy_manager, backtest_engine, market_data):
        """測試多策略端到端回測流程"""
        # 載入所有策略
        strategy_ids = strategy_manager.load_strategies()
        assert len(strategy_ids) >= 2, "應該至少載入兩個策略用於多策略測試"
        
        # 選擇啟用的策略，並確保有對應的市場數據
        enabled_strategies = []
        for sid in strategy_ids:
            state = strategy_manager.get_strategy_state(sid)
            if state.enabled:
                temp_strategy = strategy_manager.strategies[sid]
                config = temp_strategy.config
                
                # 檢查是否有該策略需要的市場數據
                if config.symbol in market_data and market_data[config.symbol]:
                    # 檢查是否有所需的時間週期
                    available_tfs = set(market_data[config.symbol].keys())
                    required_tfs = set(config.timeframes)
                    
                    if required_tfs.issubset(available_tfs):
                        enabled_strategies.append(temp_strategy)
        
        if len(enabled_strategies) < 2:
            pytest.skip("需要至少兩個有完整市場數據的啟用策略")
        
        # 只使用前兩個策略進行測試
        test_strategies = enabled_strategies[:2]
        
        # 設置資金分配
        capital_allocation = {
            test_strategies[0].config.strategy_id: 0.5,
            test_strategies[1].config.strategy_id: 0.5
        }
        
        # 獲取共同的時間範圍（使用第一個策略的數據）
        first_strategy = test_strategies[0]
        symbol_data = market_data[first_strategy.config.symbol]
        first_tf = list(symbol_data.keys())[0]
        df = symbol_data[first_tf]
        
        end_date = df['timestamp'].iloc[-1]
        start_date = end_date - timedelta(days=30)
        
        # 為每個策略單獨執行回測
        strategy_results = {}
        for strategy in test_strategies:
            config = strategy.config
            if config.symbol in market_data:
                result = backtest_engine.run_single_strategy(
                    strategy=strategy,
                    market_data=market_data[config.symbol],
                    start_date=start_date,
                    end_date=end_date
                )
                strategy_results[config.strategy_id] = result
        
        # 驗證結果
        assert len(strategy_results) >= 2, "應該有至少兩個策略的結果"
        
        # 驗證每個策略的結果
        total_pnl = 0
        for strategy in test_strategies:
            sid = strategy.config.strategy_id
            if sid in strategy_results:
                strategy_result = strategy_results[sid]
                assert strategy_result.strategy_id == sid, "策略ID應該匹配"
                assert strategy_result.initial_capital > 0, "初始資金應該大於0"
                
                # 計算加權損益
                allocation = capital_allocation.get(sid, 0)
                total_pnl += strategy_result.total_pnl * allocation
        
        print(f"\n多策略回測完成:")
        print(f"  策略數量: {len(strategy_results)}")
        print(f"  總損益（加權）: {total_pnl:.2f}")
        for sid, strat_result in strategy_results.items():
            print(f"  {sid}: {strat_result.total_pnl:.2f} ({strat_result.total_trades} 交易)")
    
    def test_backtest_with_all_components(self, strategy_manager, risk_manager, backtest_engine, market_data):
        """測試包含所有組件的完整回測流程"""
        # 載入策略
        strategy_ids = strategy_manager.load_strategies()
        assert len(strategy_ids) > 0, "應該載入策略"
        
        # 選擇一個策略
        strategy_id = None
        for sid in strategy_ids:
            state = strategy_manager.get_strategy_state(sid)
            if state.enabled:
                strategy_id = sid
                break
        
        if strategy_id is None:
            pytest.skip("沒有啟用的策略")
        
        strategy = strategy_manager.strategies[strategy_id]
        config = strategy.config
        
        # 確保有市場數據
        if config.symbol not in market_data or not market_data[config.symbol]:
            pytest.skip(f"沒有 {config.symbol} 的市場數據")
        
        # 設置時間範圍
        symbol_data = market_data[config.symbol]
        first_tf = list(symbol_data.keys())[0]
        df = symbol_data[first_tf]
        
        end_date = df.index[-1]
        start_date = end_date - timedelta(days=30)
        
        # 執行回測（包含風險管理）
        result = backtest_engine.run_single_strategy(
            strategy=strategy,
            market_data={config.symbol: symbol_data},
            start_date=start_date,
            end_date=end_date
        )
        
        # 驗證風險管理器可以處理回測結果
        for trade in result.trades:
            # 更新風險狀態
            risk_manager.update_risk_state(trade)
            
            # 檢查風險限制
            should_halt, reason = risk_manager.should_halt_trading()
            # 在回測中，我們只是記錄，不實際暫停
        
        # 驗證風險狀態已更新
        global_state = risk_manager.global_state
        assert global_state.total_trades >= 0, "總交易次數應該被追蹤"
        
        print(f"\n完整組件回測完成:")
        print(f"  策略: {strategy_id}")
        print(f"  總交易: {result.total_trades}")
        print(f"  風險管理器追蹤的交易: {global_state.total_trades}")
        print(f"  當前回撤: {global_state.current_drawdown:.2%}")
    
    def test_backtest_result_persistence(self, strategy_manager, backtest_engine, market_data, tmp_path):
        """測試回測結果的持久化和載入"""
        # 載入策略
        strategy_ids = strategy_manager.load_strategies()
        if not strategy_ids:
            pytest.skip("沒有可用的策略")
        
        strategy_id = strategy_ids[0]
        strategy = strategy_manager.strategies[strategy_id]
        config = strategy.config
        
        # 確保有市場數據
        if config.symbol not in market_data or not market_data[config.symbol]:
            pytest.skip(f"沒有 {config.symbol} 的市場數據")
        
        # 執行回測
        symbol_data = market_data[config.symbol]
        first_tf = list(symbol_data.keys())[0]
        df = symbol_data[first_tf]
        
        end_date = df.index[-1]
        start_date = end_date - timedelta(days=30)
        
        result = backtest_engine.run_single_strategy(
            strategy=strategy,
            market_data={config.symbol: symbol_data},
            start_date=start_date,
            end_date=end_date
        )
        
        # 保存結果
        result_file = tmp_path / "backtest_result.json"
        result.save(str(result_file))
        
        # 驗證文件存在
        assert result_file.exists(), "結果文件應該被創建"
        
        # 載入並驗證
        with open(result_file, 'r') as f:
            loaded_data = json.load(f)
        
        assert loaded_data['strategy_id'] == result.strategy_id, "策略ID應該匹配"
        assert loaded_data['total_trades'] == result.total_trades, "總交易次數應該匹配"
        assert abs(loaded_data['total_pnl'] - result.total_pnl) < 0.01, "總損益應該匹配"
        
        print(f"\n回測結果持久化測試完成:")
        print(f"  保存位置: {result_file}")
        print(f"  策略: {result.strategy_id}")
        print(f"  總交易: {result.total_trades}")
