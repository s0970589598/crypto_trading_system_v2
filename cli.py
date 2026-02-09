#!/usr/bin/env python3
"""
多策略交易系統 - 命令行界面

支持的模式：
- backtest: 回測模式
- live: 實盤交易模式
- optimize: 參數優化模式
"""

import argparse
import sys
import logging
from datetime import datetime
from pathlib import Path

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """主程序入口"""
    parser = argparse.ArgumentParser(
        description='多策略交易系統 - 命令行界面',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  # 回測單個策略
  python cli.py backtest --strategy multi-timeframe-aggressive --start 2024-01-01 --end 2024-12-31
  
  # 回測多個策略
  python cli.py backtest --strategy multi-timeframe-aggressive --strategy breakout-strategy
  
  # 實盤交易
  python cli.py live --strategies multi-timeframe-aggressive,breakout-strategy
  
  # 參數優化
  python cli.py optimize --strategy multi-timeframe-aggressive --method grid
        """
    )
    
    # 創建子命令
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 回測命令
    backtest_parser = subparsers.add_parser('backtest', help='回測策略')
    backtest_parser.add_argument(
        '--strategy',
        action='append',
        required=True,
        help='策略 ID（可以多次指定以回測多個策略）'
    )
    backtest_parser.add_argument(
        '--start',
        type=str,
        help='開始日期（格式：YYYY-MM-DD）'
    )
    backtest_parser.add_argument(
        '--end',
        type=str,
        help='結束日期（格式：YYYY-MM-DD）'
    )
    backtest_parser.add_argument(
        '--capital',
        type=float,
        default=1000.0,
        help='初始資金（默認：1000 USDT）'
    )
    backtest_parser.add_argument(
        '--commission',
        type=float,
        default=0.0005,
        help='手續費率（默認：0.0005）'
    )
    backtest_parser.add_argument(
        '--output',
        type=str,
        help='輸出文件路徑（可選）'
    )
    
    # 實盤交易命令
    live_parser = subparsers.add_parser('live', help='實盤交易')
    live_parser.add_argument(
        '--strategies',
        type=str,
        required=True,
        help='策略 ID 列表（逗號分隔）'
    )
    live_parser.add_argument(
        '--capital',
        type=float,
        default=1000.0,
        help='初始資金（默認：1000 USDT）'
    )
    live_parser.add_argument(
        '--dry-run',
        action='store_true',
        help='模擬模式（不執行真實交易）'
    )
    
    # 參數優化命令
    optimize_parser = subparsers.add_parser('optimize', help='參數優化')
    optimize_parser.add_argument(
        '--strategy',
        type=str,
        required=True,
        help='策略 ID'
    )
    optimize_parser.add_argument(
        '--method',
        type=str,
        choices=['grid', 'random', 'bayesian'],
        default='grid',
        help='優化方法（默認：grid）'
    )
    optimize_parser.add_argument(
        '--iterations',
        type=int,
        default=100,
        help='迭代次數（用於 random 和 bayesian 方法，默認：100）'
    )
    optimize_parser.add_argument(
        '--metric',
        type=str,
        default='sharpe_ratio',
        choices=['sharpe_ratio', 'profit_factor', 'win_rate', 'total_pnl'],
        help='優化指標（默認：sharpe_ratio）'
    )
    optimize_parser.add_argument(
        '--output',
        type=str,
        help='輸出報告路徑（可選）'
    )
    
    # 解析參數
    args = parser.parse_args()
    
    # 如果沒有指定命令，顯示幫助
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # 執行對應的命令
    try:
        if args.command == 'backtest':
            from cli_commands.backtest import run_backtest
            run_backtest(args)
        elif args.command == 'live':
            from cli_commands.live import run_live
            run_live(args)
        elif args.command == 'optimize':
            from cli_commands.optimize import run_optimize
            run_optimize(args)
        else:
            parser.print_help()
            sys.exit(1)
    
    except KeyboardInterrupt:
        logger.info("\n程序被用戶中斷")
        sys.exit(0)
    except Exception as e:
        logger.error(f"執行命令時發生錯誤：{e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
