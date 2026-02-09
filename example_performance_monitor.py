"""
PerformanceMonitor 使用示例

展示如何使用 PerformanceMonitor 監控策略性能
"""

from datetime import datetime, timedelta
from src.analysis.performance_monitor import PerformanceMonitor, AlertConfig
from src.models.trading import Trade
from src.models.backtest import BacktestResult


def main():
    """主函數"""
    print("=" * 80)
    print("PerformanceMonitor 使用示例")
    print("=" * 80)
    
    # 1. 創建性能監控器
    alert_config = AlertConfig(
        win_rate_drop_threshold=20.0,
        drawdown_threshold=15.0,
        consecutive_loss_threshold=5,
        degradation_window=20,
        degradation_threshold=15.0,
        auto_halt_consecutive_losses=5,
        auto_halt_drawdown=20.0
    )
    
    monitor = PerformanceMonitor(alert_config=alert_config)
    
    # 2. 設置策略初始資金
    strategy_id = "multi-timeframe-v1"
    initial_capital = 10000.0
    monitor.set_initial_capital(strategy_id, initial_capital)
    
    # 3. 設置回測基準（可選）
    backtest_result = BacktestResult(
        strategy_id=strategy_id,
        start_date=datetime.now() - timedelta(days=90),
        end_date=datetime.now() - timedelta(days=1),
        initial_capital=initial_capital,
        final_capital=12000.0,
        win_rate=65.0,
        total_pnl_pct=20.0,
        max_drawdown_pct=8.0,
        sharpe_ratio=1.8
    )
    monitor.set_backtest_baseline(strategy_id, backtest_result)
    
    print(f"\n策略 ID: {strategy_id}")
    print(f"初始資金: {initial_capital:.2f} USDT")
    print(f"回測基準勝率: {backtest_result.win_rate:.2f}%")
    
    # 4. 模擬一些交易
    print("\n" + "=" * 80)
    print("模擬交易執行")
    print("=" * 80)
    
    # 前 10 筆交易：表現良好
    print("\n階段 1: 前 10 筆交易（表現良好）")
    for i in range(10):
        is_win = i < 7  # 70% 勝率
        trade = Trade(
            strategy_id=strategy_id,
            symbol="ETHUSDT",
            direction="long",
            entry_time=datetime.now() - timedelta(hours=20-i),
            exit_time=datetime.now() - timedelta(hours=19-i),
            entry_price=2000.0,
            exit_price=2100.0 if is_win else 1950.0,
            size=0.5,
            leverage=5,
        )
        trade.calculate_pnl()
        
        # 監控策略
        result = monitor.monitor_strategy(strategy_id, trade)
        
        print(f"  交易 {i+1}: {'獲利' if is_win else '虧損'} {trade.pnl:.2f} USDT")
        if result['alerts']:
            for alert in result['alerts']:
                print(f"    警報: [{alert['level']}] {alert['message']}")
    
    # 顯示當前指標
    metrics = monitor.get_latest_metrics(strategy_id)
    print(f"\n當前指標:")
    print(f"  總交易: {metrics.total_trades}")
    print(f"  勝率: {metrics.win_rate:.2f}%")
    print(f"  總損益: {metrics.total_pnl:.2f} USDT ({metrics.total_pnl_pct:.2f}%)")
    print(f"  當前資金: {metrics.current_capital:.2f} USDT")
    
    # 後 10 筆交易：表現退化
    print("\n階段 2: 後 10 筆交易（表現退化）")
    for i in range(10):
        is_win = i < 3  # 30% 勝率
        trade = Trade(
            strategy_id=strategy_id,
            symbol="ETHUSDT",
            direction="long",
            entry_time=datetime.now() - timedelta(hours=10-i),
            exit_time=datetime.now() - timedelta(hours=9-i),
            entry_price=2000.0,
            exit_price=2100.0 if is_win else 1950.0,
            size=0.5,
            leverage=5,
        )
        trade.calculate_pnl()
        
        # 監控策略
        result = monitor.monitor_strategy(strategy_id, trade)
        
        print(f"  交易 {i+11}: {'獲利' if is_win else '虧損'} {trade.pnl:.2f} USDT")
        if result['alerts']:
            for alert in result['alerts']:
                print(f"    警報: [{alert['level']}] {alert['message']}")
        
        if result.get('halted'):
            print(f"  ⚠️  策略已自動暫停！")
            break
    
    # 5. 生成性能報告
    print("\n" + "=" * 80)
    print("性能報告")
    print("=" * 80)
    report = monitor.generate_performance_report(strategy_id)
    print(report)
    
    # 6. 與回測比較
    print("\n" + "=" * 80)
    print("與回測比較")
    print("=" * 80)
    comparison = monitor.compare_with_backtest(strategy_id)
    if comparison['available']:
        print(f"\n性能等級: {comparison['performance_grade']}")
        print(f"\n回測基準:")
        print(f"  勝率: {comparison['backtest']['win_rate']:.2f}%")
        print(f"  收益率: {comparison['backtest']['total_pnl_pct']:.2f}%")
        print(f"  最大回撤: {comparison['backtest']['max_drawdown_pct']:.2f}%")
        print(f"\n實際表現:")
        print(f"  勝率: {comparison['actual']['win_rate']:.2f}%")
        print(f"  收益率: {comparison['actual']['total_pnl_pct']:.2f}%")
        print(f"  最大回撤: {comparison['actual']['max_drawdown_pct']:.2f}%")
        print(f"\n差異:")
        print(f"  勝率: {comparison['difference']['win_rate']:+.2f}%")
        print(f"  收益率: {comparison['difference']['total_pnl_pct']:+.2f}%")
        print(f"  最大回撤: {comparison['difference']['max_drawdown_pct']:+.2f}%")
    
    print("\n" + "=" * 80)
    print("示例完成")
    print("=" * 80)


if __name__ == "__main__":
    main()
