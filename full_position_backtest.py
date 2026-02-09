#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
滿倉回測：對比不同槓桿的真實表現
起始資金：10 USDT
每次使用：100% 資金（滿倉）
"""

import pandas as pd
import numpy as np
from datetime import datetime

class FullPositionBacktest:
    """滿倉回測引擎"""
    
    def __init__(self, initial_capital=10, leverage=5, commission=0.0005):
        self.initial_capital = initial_capital
        self.leverage = leverage
        self.commission = commission
        self.reset()
        
    def reset(self):
        """重置回測狀態"""
        self.capital = self.initial_capital
        self.position = None
        self.trades = []
        self.equity_curve = []
        self.max_capital = self.initial_capital
        self.max_drawdown = 0
        
    def calculate_ema(self, data, period):
        """計算 EMA"""
        return data.ewm(span=period, adjust=False).mean()
    
    def calculate_atr(self, df, period=14):
        """計算 ATR"""
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return true_range.rolling(window=period).mean()
    
    def calculate_rsi(self, data, period=14):
        """計算 RSI"""
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def check_trend(self, ema20, ema50, ema200):
        """判斷趨勢"""
        if ema20 > ema50 > ema200:
            return 'Uptrend'
        elif ema20 < ema50 < ema200:
            return 'Downtrend'
        else:
            return 'Neutral'
    
    def run(self, df_4h, df_1h, df_15m):
        """執行回測"""
        # 計算指標
        df_4h['EMA_20'] = self.calculate_ema(df_4h['close'], 20)
        df_4h['EMA_50'] = self.calculate_ema(df_4h['close'], 50)
        df_4h['EMA_200'] = self.calculate_ema(df_4h['close'], 200)
        
        df_1h['EMA_20'] = self.calculate_ema(df_1h['close'], 20)
        df_1h['EMA_50'] = self.calculate_ema(df_1h['close'], 50)
        df_1h['EMA_200'] = self.calculate_ema(df_1h['close'], 200)
        df_1h['ATR'] = self.calculate_atr(df_1h, 14)
        
        df_15m['RSI'] = self.calculate_rsi(df_15m['close'], 14)
        df_15m['volume_ma'] = df_15m['volume'].rolling(window=20).mean()
        
        # 回測邏輯
        for i in range(200, len(df_1h)):
            if self.capital <= 0:
                break
                
            timestamp = df_1h.index[i]
            price = df_1h['close'].iloc[i]
            
            # 記錄資金曲線
            self.equity_curve.append({
                'timestamp': timestamp,
                'capital': self.capital
            })
            
            # 更新最大資金和回撤
            if self.capital > self.max_capital:
                self.max_capital = self.capital
            
            drawdown = (self.max_capital - self.capital) / self.max_capital * 100
            if drawdown > self.max_drawdown:
                self.max_drawdown = drawdown
            
            # 獲取各週期趨勢
            idx_4h = min(i // 4, len(df_4h) - 1)
            trend_4h = self.check_trend(
                df_4h['EMA_20'].iloc[idx_4h],
                df_4h['EMA_50'].iloc[idx_4h],
                df_4h['EMA_200'].iloc[idx_4h]
            )
            
            trend_1h = self.check_trend(
                df_1h['EMA_20'].iloc[i],
                df_1h['EMA_50'].iloc[i],
                df_1h['EMA_200'].iloc[i]
            )
            
            idx_15m = min(i * 4, len(df_15m) - 1)
            rsi_15m = df_15m['RSI'].iloc[idx_15m]
            volume = df_15m['volume'].iloc[idx_15m]
            volume_ma = df_15m['volume_ma'].iloc[idx_15m]
            
            atr = df_1h['ATR'].iloc[i]
            
            # 如果有持倉，檢查止損和目標
            if self.position:
                entry_price = self.position['entry_price']
                stop_loss = self.position['stop_loss']
                take_profit = self.position['take_profit']
                direction = self.position['direction']
                size = self.position['size']
                
                # 做多的止損和目標
                if direction == 'long':
                    if price <= stop_loss:
                        # 止損
                        pnl_pct = (price / entry_price - 1) * self.leverage
                        pnl = self.position['capital'] * pnl_pct
                        commission_cost = self.position['capital'] * self.leverage * self.commission * 2
                        net_pnl = pnl - commission_cost
                        
                        self.capital += net_pnl
                        
                        self.trades.append({
                            'entry_time': self.position['entry_time'],
                            'exit_time': timestamp,
                            'direction': direction,
                            'entry_price': entry_price,
                            'exit_price': price,
                            'capital_before': self.position['capital'],
                            'capital_after': self.capital,
                            'pnl': net_pnl,
                            'pnl_pct': (self.capital / self.position['capital'] - 1) * 100,
                            'reason': '止損'
                        })
                        
                        self.position = None
                        continue
                    
                    if price >= take_profit:
                        # 獲利
                        pnl_pct = (price / entry_price - 1) * self.leverage
                        pnl = self.position['capital'] * pnl_pct
                        commission_cost = self.position['capital'] * self.leverage * self.commission * 2
                        net_pnl = pnl - commission_cost
                        
                        self.capital += net_pnl
                        
                        self.trades.append({
                            'entry_time': self.position['entry_time'],
                            'exit_time': timestamp,
                            'direction': direction,
                            'entry_price': entry_price,
                            'exit_price': price,
                            'capital_before': self.position['capital'],
                            'capital_after': self.capital,
                            'pnl': net_pnl,
                            'pnl_pct': (self.capital / self.position['capital'] - 1) * 100,
                            'reason': '獲利'
                        })
                        
                        self.position = None
                        continue
                
                # 做空的止損和目標
                elif direction == 'short':
                    if price >= stop_loss:
                        # 止損
                        pnl_pct = (entry_price / price - 1) * self.leverage
                        pnl = self.position['capital'] * pnl_pct
                        commission_cost = self.position['capital'] * self.leverage * self.commission * 2
                        net_pnl = pnl - commission_cost
                        
                        self.capital += net_pnl
                        
                        self.trades.append({
                            'entry_time': self.position['entry_time'],
                            'exit_time': timestamp,
                            'direction': direction,
                            'entry_price': entry_price,
                            'exit_price': price,
                            'capital_before': self.position['capital'],
                            'capital_after': self.capital,
                            'pnl': net_pnl,
                            'pnl_pct': (self.capital / self.position['capital'] - 1) * 100,
                            'reason': '止損'
                        })
                        
                        self.position = None
                        continue
                    
                    if price <= take_profit:
                        # 獲利
                        pnl_pct = (entry_price / price - 1) * self.leverage
                        pnl = self.position['capital'] * pnl_pct
                        commission_cost = self.position['capital'] * self.leverage * self.commission * 2
                        net_pnl = pnl - commission_cost
                        
                        self.capital += net_pnl
                        
                        self.trades.append({
                            'entry_time': self.position['entry_time'],
                            'exit_time': timestamp,
                            'direction': direction,
                            'entry_price': entry_price,
                            'exit_price': price,
                            'capital_before': self.position['capital'],
                            'capital_after': self.capital,
                            'pnl': net_pnl,
                            'pnl_pct': (self.capital / self.position['capital'] - 1) * 100,
                            'reason': '獲利'
                        })
                        
                        self.position = None
                        continue
            
            # 如果沒有持倉，檢查進場條件
            if not self.position and self.capital > 0:
                if trend_4h == trend_1h and trend_4h in ['Uptrend', 'Downtrend']:
                    if 30 <= rsi_15m <= 70:
                        if volume > volume_ma:
                            ema20 = df_1h['EMA_20'].iloc[i]
                            ema50 = df_1h['EMA_50'].iloc[i]
                            
                            near_ema20 = abs(price - ema20) / ema20 < 0.03
                            near_ema50 = abs(price - ema50) / ema50 < 0.03
                            
                            if near_ema20 or near_ema50:
                                # 進場！使用全部資金
                                direction = 'long' if trend_4h == 'Uptrend' else 'short'
                                
                                if direction == 'long':
                                    stop_loss = price - (atr * 1.5)
                                    take_profit = price + (atr * 3)
                                else:
                                    stop_loss = price + (atr * 1.5)
                                    take_profit = price - (atr * 3)
                                
                                self.position = {
                                    'entry_time': timestamp,
                                    'entry_price': price,
                                    'capital': self.capital,
                                    'size': (self.capital * self.leverage) / price,
                                    'stop_loss': stop_loss,
                                    'take_profit': take_profit,
                                    'direction': direction
                                }
        
        return self.trades, self.equity_curve


def main():
    """主函數"""
    print("=" * 100)
    print("滿倉回測 - 對比不同槓桿")
    print("=" * 100)
    print("\n配置：")
    print("  起始資金：10 USDT")
    print("  倉位：100%（滿倉）")
    print("  止損：1.5 ATR")
    print("  目標：3 ATR")
    print("  手續費：0.05%")
    
    # 讀取數據
    print("\n讀取市場數據...")
    df_4h = pd.read_csv('market_data_ETHUSDT_4h.csv')
    df_1h = pd.read_csv('market_data_ETHUSDT_1h.csv')
    df_15m = pd.read_csv('market_data_ETHUSDT_15m.csv')
    
    for df in [df_4h, df_1h, df_15m]:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
    
    # 測試不同槓桿
    leverages = [1, 2, 3, 5, 10, 20, 50, 100]
    results = []
    
    for leverage in leverages:
        print(f"\n{'='*100}")
        print(f"回測 {leverage}x 槓桿")
        print(f"{'='*100}")
        
        backtest = FullPositionBacktest(initial_capital=10, leverage=leverage)
        trades, equity_curve = backtest.run(df_4h, df_1h, df_15m)
        
        if len(trades) > 0:
            wins = len([t for t in trades if t['pnl'] > 0])
            losses = len([t for t in trades if t['pnl'] < 0])
            win_rate = wins / len(trades) * 100
            
            final_capital = backtest.capital
            total_return = (final_capital / 10 - 1) * 100
            
            # 計算最大連續虧損
            max_consecutive_losses = 0
            current_consecutive_losses = 0
            for trade in trades:
                if trade['pnl'] < 0:
                    current_consecutive_losses += 1
                    max_consecutive_losses = max(max_consecutive_losses, current_consecutive_losses)
                else:
                    current_consecutive_losses = 0
            
            # 檢查是否爆倉
            bankrupted = final_capital <= 0
            
            result = {
                'leverage': leverage,
                'trades': len(trades),
                'wins': wins,
                'losses': losses,
                'win_rate': win_rate,
                'final_capital': final_capital,
                'total_return': total_return,
                'max_drawdown': backtest.max_drawdown,
                'max_consecutive_losses': max_consecutive_losses,
                'bankrupted': bankrupted
            }
            results.append(result)
            
            print(f"\n總交易次數：{len(trades)}")
            print(f"獲利交易：{wins} 次")
            print(f"虧損交易：{losses} 次")
            print(f"勝率：{win_rate:.2f}%")
            print(f"最終資金：{final_capital:.2f} USDT")
            print(f"總收益率：{total_return:.2f}%")
            print(f"最大回撤：{backtest.max_drawdown:.2f}%")
            print(f"最大連續虧損：{max_consecutive_losses} 次")
            
            if bankrupted:
                print(f"⚠️ 爆倉！")
            
            # 打印前 5 筆交易
            print(f"\n前 5 筆交易：")
            for i, trade in enumerate(trades[:5]):
                result_text = '✅' if trade['pnl'] > 0 else '❌'
                print(f"  {i+1}. {result_text} {trade['direction']}: "
                      f"${trade['entry_price']:.2f} → ${trade['exit_price']:.2f}, "
                      f"{trade['capital_before']:.2f} → {trade['capital_after']:.2f} USDT "
                      f"({trade['pnl_pct']:+.2f}%), {trade['reason']}")
        else:
            print("沒有交易")
    
    # 打印對比表
    print("\n" + "=" * 100)
    print("槓桿對比總結")
    print("=" * 100)
    print(f"\n{'槓桿':<8} {'交易數':<8} {'勝率':<10} {'最終資金':<12} {'收益率':<12} {'最大回撤':<12} {'最大連損':<10} {'狀態':<10}")
    print("-" * 100)
    
    for r in results:
        status = "爆倉 ❌" if r['bankrupted'] else "存活 ✅"
        print(f"{r['leverage']}x{'':<6} {r['trades']:<8} {r['win_rate']:<9.2f}% "
              f"{r['final_capital']:<11.2f} {r['total_return']:+11.2f}% "
              f"{r['max_drawdown']:<11.2f}% {r['max_consecutive_losses']:<10} {status}")
    
    # 保存結果
    results_df = pd.DataFrame(results)
    results_df.to_csv('leverage_comparison.csv', index=False)
    print(f"\n結果已保存至 leverage_comparison.csv")


if __name__ == '__main__':
    main()
