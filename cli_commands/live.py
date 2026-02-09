"""
實盤交易命令實現
"""

import time
import logging
from datetime import datetime
from pathlib import Path

from src.execution.multi_strategy_executor import MultiStrategyExecutor
from src.managers.strategy_manager import StrategyManager
from src.managers.risk_manager import RiskManager
from src.models.risk import RiskConfig, GlobalRiskState
from src.strategies.multi_timeframe_strategy import MultiTimeframeStrategy
from src.strategies.breakout_strategy import BreakoutStrategy


logger = logging.getLogger(__name__)


def load_strategy_instance(strategy_id: str):
    """
    載入策略實例
    
    Args:
        strategy_id: 策略 ID
    
    Returns:
        Strategy: 策略實例
    """
    from src.models.config import StrategyConfig
    
    # 查找配置文件
    config_file = Path(f"strategies/{strategy_id}.json")
    
    if not config_file.exists():
        raise FileNotFoundError(f"策略配置文件不存在：{config_file}")
    
    # 載入配置
    config = StrategyConfig.from_json(str(config_file))
    
    # 根據策略 ID 推斷策略類
    if 'multi-timeframe' in strategy_id.lower() or 'multi_timeframe' in strategy_id.lower():
        strategy_class = MultiTimeframeStrategy
    elif 'breakout' in strategy_id.lower():
        strategy_class = BreakoutStrategy
    else:
        logger.warning(f"無法推斷策略類型，使用默認的 MultiTimeframeStrategy")
        strategy_class = MultiTimeframeStrategy
    
    # 創建策略實例
    strategy = strategy_class(config)
    
    logger.info(f"載入策略：{strategy_id} ({strategy_class.__name__})")
    
    return strategy


def run_live(args):
    """
    執行實盤交易命令
    
    Args:
        args: 命令行參數
    """
    logger.info("啟動實盤交易系統")
    
    # 解析策略列表
    strategy_ids = [s.strip() for s in args.strategies.split(',')]
    
    if not strategy_ids:
        logger.error("未指定策略")
        return
    
    # 檢查是否為模擬模式
    if args.dry_run:
        logger.info("⚠️  模擬模式（Dry Run）- 不會執行真實交易")
    else:
        logger.warning("⚠️  實盤模式 - 將執行真實交易！")
        
        # 要求用戶確認
        response = input("確認要啟動實盤交易嗎？(yes/no): ")
        if response.lower() != 'yes':
            logger.info("用戶取消操作")
            return
    
    # 創建風險管理器
    risk_config = RiskConfig(
        global_max_drawdown=0.20,  # 20% 最大回撤
        daily_loss_limit=0.10,  # 10% 每日虧損限制
        global_max_position=0.80,  # 80% 最大倉位
        max_trades_per_day=10,  # 每日最大交易次數
    )
    
    global_state = GlobalRiskState(
        initial_capital=args.capital,
        current_capital=args.capital,
    )
    
    risk_manager = RiskManager(risk_config, global_state)
    
    # 創建策略管理器
    strategy_manager = StrategyManager()
    
    # 創建多策略執行器
    executor = MultiStrategyExecutor(
        strategy_manager=strategy_manager,
        risk_manager=risk_manager,
    )
    
    # 載入策略
    for i, strategy_id in enumerate(strategy_ids):
        try:
            strategy = load_strategy_instance(strategy_id)
            
            # 添加到執行器（優先級按順序遞增）
            executor.add_strategy(strategy, priority=i)
            
            logger.info(f"✅ 添加策略：{strategy_id}")
        
        except Exception as e:
            logger.error(f"載入策略 {strategy_id} 失敗：{e}")
            continue
    
    if not executor.strategies:
        logger.error("沒有成功載入任何策略")
        return
    
    # 打印系統信息
    print("\n" + "=" * 80)
    print("多策略交易系統")
    print("=" * 80)
    print(f"\n模式：{'模擬模式 (Dry Run)' if args.dry_run else '實盤模式'}")
    print(f"初始資金：{args.capital:.2f} USDT")
    print(f"策略數量：{len(executor.strategies)}")
    print(f"\n策略列表：")
    for strategy_id in executor.strategies.keys():
        state = executor.get_strategy_state(strategy_id)
        print(f"  - {strategy_id} ({'啟用' if state.enabled else '停用'})")
    
    print(f"\n風險限制：")
    print(f"  - 全局最大回撤：{risk_config.global_max_drawdown:.0%}")
    print(f"  - 每日虧損限制：{risk_config.daily_loss_limit:.0%}")
    print(f"  - 全局最大倉位：{risk_config.global_max_position:.0%}")
    
    print("\n" + "=" * 80)
    print("\n按 Ctrl+C 停止交易系統\n")
    
    # 主循環
    try:
        iteration = 0
        
        while True:
            iteration += 1
            current_time = datetime.now()
            
            logger.info(f"迭代 {iteration} - {current_time}")
            
            # TODO: 實際實現中，這裡應該：
            # 1. 從交易所獲取最新市場數據
            # 2. 為每個策略生成信號
            # 3. 過濾信號（風險檢查）
            # 4. 執行信號（下單）
            # 5. 檢查持倉是否需要出場
            # 6. 更新策略狀態
            
            # 目前只是一個框架，實際實現需要集成交易所 API
            logger.info("⚠️  實盤交易功能尚未完全實現")
            logger.info("需要集成交易所 API（Binance/BingX）來獲取市場數據和執行交易")
            
            # 打印當前狀態
            print(f"\n[{current_time.strftime('%Y-%m-%d %H:%M:%S')}] 系統狀態：")
            print(f"  當前資金：{global_state.current_capital:.2f} USDT")
            print(f"  總損益：{global_state.current_capital - global_state.initial_capital:.2f} USDT")
            
            for strategy_id, state in executor.get_all_states().items():
                print(f"\n  策略：{strategy_id}")
                print(f"    狀態：{'啟用' if state.enabled else '停用'}")
                print(f"    今日交易：{state.trades_today}")
                print(f"    今日損益：{state.pnl_today:.2f} USDT")
                print(f"    總交易：{state.total_trades}")
                print(f"    總損益：{state.total_pnl:.2f} USDT")
                print(f"    勝率：{state.win_rate:.2%}")
            
            # 檢查是否需要暫停交易
            should_halt, halt_reason = risk_manager.should_halt_trading()
            if should_halt:
                logger.warning(f"⚠️  觸發風險限制，暫停交易：{halt_reason}")
                print(f"\n⚠️  觸發風險限制：{halt_reason}")
                print("系統已暫停交易，請檢查風險狀態")
                break
            
            # 等待下一次迭代（實際應用中應該根據策略的時間週期調整）
            logger.info("等待 60 秒...")
            time.sleep(60)
    
    except KeyboardInterrupt:
        logger.info("\n收到停止信號，正在關閉系統...")
        
        # 打印最終統計
        print("\n" + "=" * 80)
        print("交易統計")
        print("=" * 80)
        
        print(f"\n初始資金：{global_state.initial_capital:.2f} USDT")
        print(f"最終資金：{global_state.current_capital:.2f} USDT")
        print(f"總損益：{global_state.current_capital - global_state.initial_capital:.2f} USDT")
        
        for strategy_id, state in executor.get_all_states().items():
            print(f"\n策略：{strategy_id}")
            print(f"  總交易：{state.total_trades}")
            print(f"  總損益：{state.total_pnl:.2f} USDT")
            print(f"  勝率：{state.win_rate:.2%}")
        
        print("\n" + "=" * 80)
        
        logger.info("系統已關閉")
    
    except Exception as e:
        logger.error(f"系統運行時發生錯誤：{e}", exc_info=True)
        raise
