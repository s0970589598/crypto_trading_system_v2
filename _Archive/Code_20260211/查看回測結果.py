#!/usr/bin/env python3
"""
快速查看回測結果的工具
"""

import pandas as pd
import json
import glob
from datetime import datetime

def show_leverage_comparison():
    """顯示槓桿對比結果"""
    print("=" * 70)
    print("📊 槓桿對比結果（激進模式 - 1.5 ATR 止損）")
    print("=" * 70)
    
    df = pd.read_csv('leverage_comparison_激進模式_1.5_ATR.csv')
    
    print(f"\n{'槓桿':<8} {'收益率':<12} {'最大回撤':<12} {'勝率':<10} {'風險調整':<10} {'評級'}")
    print("-" * 70)
    
    for _, row in df.iterrows():
        leverage = int(row['leverage'])
        total_return = row['total_return']
        max_drawdown = row['max_drawdown']
        win_rate = row['win_rate']
        risk_adjusted = total_return / max_drawdown if max_drawdown > 0 else 0
        
        # 評級
        if risk_adjusted > 2.0:
            rating = "⭐⭐⭐⭐⭐"
        elif risk_adjusted > 1.7:
            rating = "⭐⭐⭐⭐"
        elif risk_adjusted > 1.5:
            rating = "⭐⭐⭐"
        elif risk_adjusted > 1.2:
            rating = "⭐⭐"
        else:
            rating = "⭐"
        
        print(f"{leverage}x{' ' * (6-len(str(leverage)))} "
              f"+{total_return:>6.2f}%{' ' * 3} "
              f"-{max_drawdown:>6.2f}%{' ' * 3} "
              f"{win_rate:>5.1f}%{' ' * 3} "
              f"{risk_adjusted:>6.2f}{' ' * 3} "
              f"{rating}")
    
    print("\n💡 建議：")
    best_idx = (df['total_return'] / df['max_drawdown']).idxmax()
    best_leverage = int(df.loc[best_idx, 'leverage'])
    best_return = df.loc[best_idx, 'total_return']
    best_drawdown = df.loc[best_idx, 'max_drawdown']
    
    print(f"   最佳風險調整收益：{best_leverage}x 槓桿")
    print(f"   收益：+{best_return:.2f}%")
    print(f"   回撤：-{best_drawdown:.2f}%")
    print()

def show_latest_backtest():
    """顯示最新的回測結果"""
    print("=" * 70)
    print("📈 最新回測結果")
    print("=" * 70)
    
    # 找最新的回測結果文件
    files = glob.glob('backtest_result_*.json')
    if not files:
        print("❌ 沒有找到回測結果文件")
        return
    
    latest_file = max(files, key=lambda x: x.split('_')[-2] + x.split('_')[-1].replace('.json', ''))
    
    with open(latest_file, 'r', encoding='utf-8') as f:
        result = json.load(f)
    
    print(f"\n策略：{result['strategy_id']}")
    print(f"時間：{result['start_date']} 至 {result['end_date']}")
    print(f"\n💰 收益表現：")
    print(f"   初始資金：{result['initial_capital']:.2f} USDT")
    print(f"   最終資金：{result['final_capital']:.2f} USDT")
    
    # 使用 total_pnl_pct 而不是 total_return
    total_return = result.get('total_pnl_pct', result.get('total_return', 0))
    print(f"   總收益：+{total_return:.2f}%")
    print(f"   淨損益：{result.get('total_pnl', 0):.2f} USDT")
    
    print(f"\n📊 交易統計：")
    print(f"   總交易數：{result['total_trades']}")
    print(f"   獲利交易：{result['winning_trades']}")
    print(f"   虧損交易：{result['losing_trades']}")
    print(f"   勝率：{result['win_rate']:.2f}%")
    print(f"   平均獲利：{result.get('avg_win', 0):.2f} USDT")
    print(f"   平均虧損：{result.get('avg_loss', 0):.2f} USDT")
    
    print(f"\n⚠️ 風險指標：")
    max_dd_pct = result.get('max_drawdown_pct', result.get('max_drawdown', 0))
    print(f"   最大回撤：-{max_dd_pct:.2f}%")
    print(f"   獲利因子：{result['profit_factor']:.2f}")
    print(f"   夏普比率：{result['sharpe_ratio']:.2f}")
    
    # 評估
    print(f"\n✅ 評估：")
    score = 0
    if total_return > 20:
        print(f"   ✅ 收益率優秀（> 20%）")
        score += 1
    else:
        print(f"   ⚠️ 收益率一般（< 20%）")
    
    if result['win_rate'] >= 50:
        print(f"   ✅ 勝率達標（>= 50%）")
        score += 1
    else:
        print(f"   ⚠️ 勝率偏低（< 50%）")
    
    if max_dd_pct < 20:
        print(f"   ✅ 回撤可控（< 20%）")
        score += 1
    else:
        print(f"   ⚠️ 回撤較大（> 20%）")
    
    if result['profit_factor'] > 1.5:
        print(f"   ✅ 獲利因子優秀（> 1.5）")
        score += 1
    elif result['profit_factor'] > 1.2:
        print(f"   ⚠️ 獲利因子一般（> 1.2）")
        score += 0.5
    else:
        print(f"   ❌ 獲利因子偏低（< 1.2）")
    
    print(f"\n總評分：{score}/4")
    if score >= 3.5:
        print("🌟 策略表現優秀！")
    elif score >= 2.5:
        print("👍 策略表現良好")
    elif score >= 1.5:
        print("⚠️ 策略需要改進")
    else:
        print("❌ 策略表現不佳")
    
    print()

def show_strategy_configs():
    """顯示可用的策略配置"""
    print("=" * 70)
    print("⚙️ 可用的策略配置")
    print("=" * 70)
    
    configs = glob.glob('strategies/*.json')
    
    for config_file in sorted(configs):
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        print(f"\n📋 {config.get('name', 'Unknown')}")
        print(f"   ID: {config.get('id', 'unknown')}")
        print(f"   類型: {config.get('class', 'Unknown')}")
        print(f"   狀態: {'✅ 啟用' if config.get('enabled', False) else '❌ 禁用'}")
        
        if 'parameters' in config:
            params = config['parameters']
            print(f"   止損: {params.get('stop_loss_atr', 'N/A')} ATR")
            print(f"   目標: {params.get('take_profit_atr', 'N/A')} ATR")
        
        if 'risk_management' in config:
            risk = config['risk_management']
            print(f"   倉位: {risk.get('position_size', 'N/A') * 100:.0f}%")
            print(f"   槓桿: {risk.get('leverage', 'N/A')}x")
    
    print()

def main():
    """主函數"""
    print("\n🚀 交易系統回測結果查看工具\n")
    
    # 顯示最新回測結果
    show_latest_backtest()
    
    # 顯示槓桿對比
    try:
        show_leverage_comparison()
    except FileNotFoundError:
        print("⚠️ 槓桿對比結果文件不存在，請先運行：")
        print("   python3 backtest_leverage_comparison.py\n")
    
    # 顯示策略配置
    show_strategy_configs()
    
    print("=" * 70)
    print("💡 提示：")
    print("   - 運行回測：python3 backtest_multi_timeframe.py")
    print("   - 槓桿對比：python3 backtest_leverage_comparison.py")
    print("   - 查看文檔：open 新手入門教學.md")
    print("=" * 70)
    print()

if __name__ == "__main__":
    main()
