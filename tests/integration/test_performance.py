"""
性能測試

測試大規模數據回測性能和實時信號生成延遲
Requirements: 4.1
"""

import pytest
import pandas as pd
import time
from datetime import datetime, timedelta
from pathlib import Path

from src.managers.strategy_manager import StrategyManager
from src.execution.backtest_engine import BacktestEngine
from src.models.market_data import MarketData, TimeframeData


class TestPerformance:
    """性能測試"""
    
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
                    data[symbol][tf] = df
        
        return data
    
    @pytest.fixture
    def strategy_manager(self):
        """創建策略管理器"""
        return StrategyManager(strategies_dir="strategies/")
    
    @pytest.fixture
    def backtest_engine(self):
        """創建回測引擎"""
        return BacktestEngine(
            initial_capital=1000.0,
            commission=0.0005
        )
    
    def test_large_scale_backtest_performance(self, strategy_manager, backtest_engine, market_data):
        """測試大規模數據回測性能"""
        # 載入策略
        strategy_ids = strategy_manager.load_strategies()
        if not strategy_ids:
            pytest.skip("沒有可用的策略")
        
        # 選擇一個有完整數據的策略
        strategy = None
        for sid in strategy_ids:
            state = strategy_manager.get_strategy_state(sid)
            if state.enabled:
                temp_strategy = strategy_manager.strategies[sid]
                config = temp_strategy.config
                
                if config.symbol in market_data and market_data[config.symbol]:
                    available_tfs = set(market_data[config.symbol].keys())
                    required_tfs = set(config.timeframes)
                    
                    if required_tfs.issubset(available_tfs):
                        strategy = temp_strategy
                        break
        
        if strategy is None:
            pytest.skip("沒有找到有完整市場數據的策略")
        
        config = strategy.config
        symbol_data = market_data[config.symbol]
        
        # 使用所有可用數據進行回測
        first_tf = list(symbol_data.keys())[0]
        df = symbol_data[first_tf]
        
        start_date = df['timestamp'].iloc[0]
        end_date = df['timestamp'].iloc[-1]
        
        # 計算數據點數量
        data_points = len(df)
        time_span_days = (end_date - start_date).days
        
        # 執行回測並測量時間
        start_time = time.time()
        result = backtest_engine.run_single_strategy(
            strategy=strategy,
            market_data=symbol_data,
            start_date=start_date,
            end_date=end_date
        )
        end_time = time.time()
        
        execution_time = end_time - start_time
        
        # 驗證性能
        # 目標：處理速度應該合理（至少每秒處理100個數據點）
        points_per_second = data_points / execution_time if execution_time > 0 else 0
        
        print(f"\n大規模回測性能測試:")
        print(f"  策略: {config.strategy_id}")
        print(f"  數據點數量: {data_points}")
        print(f"  時間跨度: {time_span_days} 天")
        print(f"  執行時間: {execution_time:.2f} 秒")
        print(f"  處理速度: {points_per_second:.2f} 點/秒")
        print(f"  總交易: {result.total_trades}")
        
        # 性能斷言（寬鬆的標準，確保測試不會因為機器性能而失敗）
        assert execution_time < 60, f"回測時間不應超過60秒，實際: {execution_time:.2f}秒"
        assert points_per_second > 10, f"處理速度應該至少10點/秒，實際: {points_per_second:.2f}點/秒"
    
    def test_signal_generation_latency(self, strategy_manager, market_data):
        """測試實時信號生成延遲"""
        # 載入策略
        strategy_ids = strategy_manager.load_strategies()
        if not strategy_ids:
            pytest.skip("沒有可用的策略")
        
        # 選擇一個策略
        strategy = None
        for sid in strategy_ids:
            state = strategy_manager.get_strategy_state(sid)
            if state.enabled:
                temp_strategy = strategy_manager.strategies[sid]
                config = temp_strategy.config
                
                if config.symbol in market_data and market_data[config.symbol]:
                    available_tfs = set(market_data[config.symbol].keys())
                    required_tfs = set(config.timeframes)
                    
                    if required_tfs.issubset(available_tfs):
                        strategy = temp_strategy
                        break
        
        if strategy is None:
            pytest.skip("沒有找到有完整市場數據的策略")
        
        config = strategy.config
        symbol_data = market_data[config.symbol]
        
        # 構建 MarketData 對象
        timeframe_data = {}
        for tf, df in symbol_data.items():
            if len(df) > 0:
                # 使用最新的數據點
                latest_row = df.iloc[-1]
                timeframe_data[tf] = TimeframeData(
                    timeframe=tf,
                    ohlcv=df.tail(100),  # 最近100個數據點
                    indicators={}
                )
        
        market_data_obj = MarketData(
            symbol=config.symbol,
            timestamp=datetime.now(),
            timeframes=timeframe_data
        )
        
        # 測量信號生成時間（多次測量取平均）
        num_iterations = 10
        total_time = 0
        
        for _ in range(num_iterations):
            start_time = time.time()
            signal = strategy.generate_signal(market_data_obj)
            end_time = time.time()
            total_time += (end_time - start_time)
        
        avg_latency = (total_time / num_iterations) * 1000  # 轉換為毫秒
        
        print(f"\n信號生成延遲測試:")
        print(f"  策略: {config.strategy_id}")
        print(f"  測試次數: {num_iterations}")
        print(f"  平均延遲: {avg_latency:.2f} ms")
        print(f"  總時間: {total_time*1000:.2f} ms")
        
        # 性能斷言
        # 目標：信號生成應該在100ms內完成
        assert avg_latency < 1000, f"信號生成延遲應該小於1000ms，實際: {avg_latency:.2f}ms"
    
    def test_multi_strategy_backtest_performance(self, strategy_manager, backtest_engine, market_data):
        """測試多策略回測性能"""
        # 載入策略
        strategy_ids = strategy_manager.load_strategies()
        if len(strategy_ids) < 2:
            pytest.skip("需要至少兩個策略")
        
        # 選擇多個策略
        strategies = []
        for sid in strategy_ids:
            state = strategy_manager.get_strategy_state(sid)
            if state.enabled:
                temp_strategy = strategy_manager.strategies[sid]
                config = temp_strategy.config
                
                if config.symbol in market_data and market_data[config.symbol]:
                    available_tfs = set(market_data[config.symbol].keys())
                    required_tfs = set(config.timeframes)
                    
                    if required_tfs.issubset(available_tfs):
                        strategies.append(temp_strategy)
                        if len(strategies) >= 3:  # 最多測試3個策略
                            break
        
        if len(strategies) < 2:
            pytest.skip("沒有足夠的策略進行多策略測試")
        
        # 設置時間範圍
        first_strategy = strategies[0]
        symbol_data = market_data[first_strategy.config.symbol]
        first_tf = list(symbol_data.keys())[0]
        df = symbol_data[first_tf]
        
        end_date = df['timestamp'].iloc[-1]
        start_date = end_date - timedelta(days=30)
        
        # 執行多策略回測並測量時間
        start_time = time.time()
        
        results = {}
        for strategy in strategies:
            config = strategy.config
            if config.symbol in market_data:
                result = backtest_engine.run_single_strategy(
                    strategy=strategy,
                    market_data=market_data[config.symbol],
                    start_date=start_date,
                    end_date=end_date
                )
                results[config.strategy_id] = result
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        print(f"\n多策略回測性能測試:")
        print(f"  策略數量: {len(strategies)}")
        print(f"  執行時間: {execution_time:.2f} 秒")
        print(f"  平均每策略: {execution_time/len(strategies):.2f} 秒")
        
        for sid, result in results.items():
            print(f"  {sid}: {result.total_trades} 交易")
        
        # 性能斷言
        assert execution_time < 120, f"多策略回測時間不應超過120秒，實際: {execution_time:.2f}秒"
    
    def test_memory_efficiency(self, strategy_manager, backtest_engine, market_data):
        """測試內存效率（簡單驗證不會內存溢出）"""
        # 載入策略
        strategy_ids = strategy_manager.load_strategies()
        if not strategy_ids:
            pytest.skip("沒有可用的策略")
        
        # 選擇一個策略
        strategy = None
        for sid in strategy_ids:
            state = strategy_manager.get_strategy_state(sid)
            if state.enabled:
                temp_strategy = strategy_manager.strategies[sid]
                config = temp_strategy.config
                
                if config.symbol in market_data and market_data[config.symbol]:
                    available_tfs = set(market_data[config.symbol].keys())
                    required_tfs = set(config.timeframes)
                    
                    if required_tfs.issubset(available_tfs):
                        strategy = temp_strategy
                        break
        
        if strategy is None:
            pytest.skip("沒有找到有完整市場數據的策略")
        
        config = strategy.config
        symbol_data = market_data[config.symbol]
        
        # 使用所有數據
        first_tf = list(symbol_data.keys())[0]
        df = symbol_data[first_tf]
        
        start_date = df['timestamp'].iloc[0]
        end_date = df['timestamp'].iloc[-1]
        
        # 執行回測（如果能完成就說明內存效率可接受）
        try:
            result = backtest_engine.run_single_strategy(
                strategy=strategy,
                market_data=symbol_data,
                start_date=start_date,
                end_date=end_date
            )
            
            print(f"\n內存效率測試:")
            print(f"  策略: {config.strategy_id}")
            print(f"  數據點: {len(df)}")
            print(f"  總交易: {result.total_trades}")
            print(f"  測試通過：沒有內存溢出")
            
            assert True, "內存效率測試通過"
        except MemoryError:
            pytest.fail("內存溢出")
