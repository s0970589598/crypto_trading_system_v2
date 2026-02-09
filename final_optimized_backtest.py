#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最終優化回測：平衡收益與回撤
- 5x 槓桿，20% 倉位
- 2 ATR 止損，4 ATR 目標
- 改進的熔斷機制（有恢復）
- 30% 獲利保護
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

class FinalOptimizedBacktest:
    """最終優化回測引擎"""
    
    def __init__(self, initial_capital=10, leverage=5, position_pct=0.2, 
                 stop_loss_atr=2.0, take_profit_atr=4.0, commission=0.0005):
        self.initial_capital = initial_capital
        self.leverage = leverage
        self.position_pct = position_pct
        self.stop_loss_atr = stop_loss_atr
        self.take_profit_atr = take_profit_atr
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
        self.consecutive_losses = 0
        self.withdrawn_profit = 0
        self.pause_until = None  # 暫停交易直到此時間
        
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
                'capital': self.capital,
                'total_value': self.capital + self.withdrawn_profit
            })
            
            # 更新最大資金和回撤
            if self.capital > self.max_capital:
                # 達到新高，提取 30% 利潤
                profit = self.capital - self.max_capital
                withdraw = profit * 0.3
                self.withdrawn_profit += withdraw
                self.capital -= withdraw
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
                
                # 做多的止損和目標
                if direction == 'long':
                    if price <= stop_loss:
                        pnl_pct = (price / entry_price - 1) * self.leverage
                        pnl = self.position['capital_used'] * pnl_pct
                        commission_cost = self.position['capital_used'] * self.leverage * self.commission * 2
                        net_pnl = pnl - commission_cost
                        
                        self.capital += net_pnl
                        
                        self.trades.append({
                            'entry_time': self.position['entry_time'],
                            'exit_time': timestamp,
                            'direction': direction,
                            'entry_price': entry_price,
                            'exit_price': price,
                            'capital_before': self.position['capital_before'],
                            'capital_after': self.capital,
                            'pnl': net_pnl,
                            'pnl_pct': (self.capital / self.position['capital_before'] - 1) * 100,
                            'reason': '止損'
                        })
                        
                        # 更新連續虧損
                        self.consecutive_losses += 1
                        
                        # 連損 3 次，暫停 4 小時（不是永久）
                        if self.consecutive_losses >= 3:
                            self.pause_until = timestamp + timedelta(hours=4)
                            self.consecutive_losses = 0  # 重置計數
                        
                        self.position = None
                        continue
                    
                    if price >= take_profit:
                        pnl_pct = (price / entry_price - 1) * self.leverage
                        pnl = self.position['capital_used'] * pnl_pct
                        commission_cost = self.position['capital_used'] * self.leverage * self.commission * 2
                        net_pnl = pnl - commission_cost
                        
                        self.capital += net_pnl
                        
                        self.trades.append({
                            'entry_time': self.position['entry_time'],
                            'exit_time': timestamp,
                            'direction': direction,
                            'entry_price': entry_price,
                            'exit_price': price,
                            'capital_before': self.position['capital_before'],
                            'capital_after': self.capital,
                            'pnl': net_pnl,
                            'pnl_pct': (self.capital / self.position['capital_before'] - 1) * 100,
                            'reason': '獲利'
                        })
                        
                        # 重置連續虧損
                        self.consecutive_losses = 0
                        self.position = None
                        continue
                
                # 做空的止損和目標
                elif direction == 'short':
                    if price >= stop_loss:
                        pnl_pct = (entry_price / price - 1) * self.leverage
                        pnl = self.position['capital_used'] * pnl_pct
                        commission_cost = self.position['capital_used'] * self.leverage * self.commission * 2
                        net_pnl = pnl - commission_cost
                        
                        self.capital += net_pnl
                        
                        self.trades.append({
                            'entry_time': self.position['entry_time'],
                            'exit_time': timestamp,
                            'direction': direction,
                            'entry_price': entry_price,
                            'exit_price': price,
                            'capital_before': self.position['capital_before'],
                            'capital_after': self.capital,
                            'pnl': net_pnl,
                            'pnl_pct': (self.capital / self.position['capital_before'] - 1) * 100,
                            'reason': '止損'
                        })
                        
                        self.consecutive_losses += 1
                        
                        if self.consecutive_losses >= 3:
                            self.pause_until = timestamp + timedelta(hours=4)
                            self.consecutive_losses = 0
                        
                        self.position = None
                        continue
                    
                    if price <= take_profit:
                        pnl_pct = (entry_price / price - 1) * self.leverage
                        pnl = self.position['capital_used'] * pnl_pct
                        commission_cost = self.position['capital_used'] * self.leverage * self.commission * 2
                        net_pnl = pnl - commission_cost
                        
                        self.capital += net_pnl
                        
                        self.trades.append({
                            'entry_time': self.position['entry_time'],
                            'exit_time': timestamp,
                            'direction': direction,
                            'entry_price': entry_price,
                            'exit_price': price,
                            'capital_before': self.position['capital_before'],
                            'capital_after': self.capital,
                            'pnl': net_pnl,
                            'pnl_pct': (self.capital / self.position['capital_before'] - 1) * 100,
                            'reason': '獲利'
                        })
                        
                        self.consecutive_losses = 0
                        self.position = None
                        continue
            
            # 檢查是否在暫停期
            if self.pause_until and timestamp < self.pause_until:
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
                                # 進場！使用部分資金
                                direction = 'long' if trend_4h == 'Uptrend' else 'short'
                                capital_used = self.capital * self.position_pct
                                
                                if direction == 'long':
                                    stop_loss = price - (atr * self.stop_loss_atr)
                                    take_profit = price + (atr * self.take_profit_atr)
                                else:
                                    stop_loss = price + (atr * self.stop_loss_atr)
                                    take_profit = price - (atr * self.take_profit_atr)
                                
                                self.position = {
                                    'entry_time': timestamp,
                                    'entry_price': price,
                                    'capital_before': self.capital,
                                    'capital_used': capital_used,
                                    'stop_loss': stop_loss,
                                    'take_profit': take_profit,
                                    'direction': direction
                                }
        
        return self.trades, self.equity_curve


def main():
    """主函數"""
    print("=" * 100)
    print("最終優化回測 - 5x 槓桿 + 20% 倉位 + 2 ATR 止損")
    print("=" * 100)
    
    # 讀取數據
    print("\n讀取市場數據...")
    df_4h = pd.read_csv('market_data_ETHUSDT_4h.csv')
    df_1h = pd.read_csv('market_data_ETHUSDT_1h.csv')
    df_15m = pd.read_csv('market_data_ETHUSDT_15m.csv')
    
    for df in [df_4h, df_1h, df_15m]:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
    
    print(f"數據期間：{df_1h.index[0]} 至 {df_1h.index[-1]}")
    print(f"總天數：{(df_1h.index[-1] - df_1h.index[0]).days} 天")
    
    # 執行回測
    backtest = FinalOptimizedBacktest(
        initial_capital=10,
        leverage=5,
        position_pct=0.20,
        stop_loss_atr=2.0,
        take_profit_atr=4.0
    )
    
    trades, equity_curve = backtest.run(df_4h, df_1h, df_15m)
    
    print(f"\n{'='*100}")
    print("回測結果")
    print(f"{'='*100}")
    
    if len(trades) > 0:
        wins = [t for t in trades if t['pnl'] > 0]
        losses = [t for t in trades if t['pnl'] < 0]
        
        win_rate = len(wins) / len(trades) * 100
        
        avg_win = sum([t['pnl'] for t in wins]) / len(wins) if wins else 0
        avg_loss = sum([t['pnl'] for t in losses]) / len(losses) if losses else 0
        profit_factor = abs(sum([t['pnl'] for t in wins]) / sum([t['pnl'] for t in losses])) if losses else float('inf')
        
        final_capital = backtest.capital
        total_value = final_capital + backtest.withdrawn_profit
        total_return = (total_value / 10 - 1) * 100
        
        print(f"\n📊 交易統計")
        print(f"總交易次數：{len(trades)} 筆")
        print(f"獲利交易：{len(wins)} 筆")
        print(f"虧損交易：{len(losses)} 筆")
        print(f"勝率：{win_rate:.2f}%")
        print(f"平均獲利：{avg_win:.2f} USDT")
        print(f"平均虧損：{avg_loss:.2f} USDT")
        print(f"獲利因子：{profit_factor:.2f}")
        
        print(f"\n💰 資金表現")
        print(f"起始資金：{backtest.initial_capital:.2f} USDT")
        print(f"最終資金：{final_capital:.2f} USDT")
        print(f"提取利潤：{backtest.withdrawn_profit:.2f} USDT")
        print(f"總價值：{total_value:.2f} USDT")
        print(f"總收益率：{total_return:+.2f}%")
        print(f"最大回撤：{backtest.max_drawdown:.2f}%")
        
        # 打印前 10 筆交易
        print(f"\n📝 交易明細（前 10 筆）")
        print(f"{'#':<4} {'進場時間':<20} {'方向':<6} {'進場價':<10} {'出場價':<10} {'損益':<10} {'損益%':<10} {'原因':<6}")
        print("-" * 100)
        
        for i, trade in enumerate(trades[:10], 1):
            print(f"{i:<4} {str(trade['entry_time']):<20} {trade['direction']:<6} "
                  f"{trade['entry_price']:<10.2f} {trade['exit_price']:<10.2f} "
                  f"{trade['pnl']:+9.2f} {trade['pnl_pct']:+9.2f}% {trade['reason']:<6}")
        
        if len(trades) > 10:
            print(f"... 還有 {len(trades) - 10} 筆交易")
        
        # 資金曲線分析
        if equity_curve:
            df_equity = pd.DataFrame(equity_curve)
            max_value = df_equity['total_value'].max()
            min_value = df_equity['total_value'].min()
            
            print(f"\n📈 資金曲線")
            print(f"最高點：{max_value:.2f} USDT")
            print(f"最低點：{min_value:.2f} USDT")
            print(f"波動範圍：{max_value - min_value:.2f} USDT")
    
    else:
        print("\n⚠️ 沒有產生任何交易")
    
    print(f"\n{'='*100}")
    print("回測完成")
    print(f"{'='*100}")


if __name__ == '__main__':
    main()
