#!/bin/bash
# 多策略交易系統 CLI 使用示例

echo "=========================================="
echo "多策略交易系統 CLI 使用示例"
echo "=========================================="
echo ""

# 1. 回測單個策略
echo "1. 回測單個策略（多週期共振策略）"
echo "命令：python3 cli.py backtest --strategy multi-timeframe-aggressive --capital 1000"
echo ""
python3 cli.py backtest --strategy multi-timeframe-aggressive --capital 1000
echo ""
echo "按 Enter 繼續..."
read

# 2. 回測多個策略
echo ""
echo "2. 回測多個策略（多週期 + 突破策略）"
echo "命令：python3 cli.py backtest --strategy multi-timeframe-aggressive --strategy breakout-strategy --capital 1000"
echo ""
python3 cli.py backtest --strategy multi-timeframe-aggressive --strategy breakout-strategy --capital 1000
echo ""
echo "按 Enter 繼續..."
read

# 3. 回測並保存結果
echo ""
echo "3. 回測並保存結果到文件"
echo "命令：python3 cli.py backtest --strategy multi-timeframe-aggressive --output backtest_result.json"
echo ""
python3 cli.py backtest --strategy multi-timeframe-aggressive --output backtest_result.json
echo ""
echo "結果已保存到 backtest_result.json"
echo ""
echo "按 Enter 繼續..."
read

# 4. 查看優化命令幫助
echo ""
echo "4. 查看參數優化命令幫助"
echo "命令：python3 cli.py optimize --help"
echo ""
python3 cli.py optimize --help
echo ""
echo "按 Enter 繼續..."
read

# 5. 查看實盤交易命令幫助
echo ""
echo "5. 查看實盤交易命令幫助"
echo "命令：python3 cli.py live --help"
echo ""
python3 cli.py live --help
echo ""

echo "=========================================="
echo "示例完成！"
echo "=========================================="
echo ""
echo "更多用法："
echo "  - 指定日期範圍回測："
echo "    python3 cli.py backtest --strategy <id> --start 2024-01-01 --end 2024-12-31"
echo ""
echo "  - 參數優化（網格搜索）："
echo "    python3 cli.py optimize --strategy <id> --method grid"
echo ""
echo "  - 參數優化（隨機搜索）："
echo "    python3 cli.py optimize --strategy <id> --method random --iterations 100"
echo ""
echo "  - 實盤交易（模擬模式）："
echo "    python3 cli.py live --strategies <id1>,<id2> --dry-run"
echo ""
