#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
改進版回測：平衡的多週期策略
目標：每週 2-3 筆交易，勝率 50%+，月收益 3-5%
"""

import pandas as pd
import numpy as np
from datetime import datetime

class ImprovedBacktest:
    """改進版回測引擎"""
    
    def __init__(self, initial_capital=1000, commission=0.0005):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.commission = commission
        self.position = None
        self.trades = []
        
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
    
    def run(self, df_1d, df_4h, df_1h, df_15m):
        """執行回測"""
        print("=" * 100)
        print("改進版多週期策略 - 回測")
        print("=" * 100)
        print(f"\n初始資金: {self.initial_capital:.2f} USDT")
        print(f"回測期間: {df_1h.index[0]} 至 {df_1h.index[-1]}")
        print(f"數據點數: {len(df_1h)}")
        
        # 計算指標
        print("\n計算技術指標...")
        
        # 1D 指標
        df_1d['EMA_20'] = self.calculate_ema(df_1d['close'], 20)
        df_1d['EMA_50'] = self.calculate_ema(df_1d['close'], 50)
        df_1d['EMA_200'] = self.calculate_ema(df_1d['close'], 200)
        
        # 4H 指標
        df_4h['EMA_20'] = self.calculate_ema(df_4h['close'], 20)
        df_4h['EMA_50'] = self.calculate_ema(df_4h['close'], 50)
        df_4h['EMA_200'] = self.calculate_ema(df_4h['close'], 200)
        
        # 1H 指標
        df_1h['EMA_20'] = self.calculate_ema(df_1h['close'], 20)
        df_1h['EMA_50'] = self.calculate_ema(df_1h['close'], 50)
        df_1h['EMA_200'] = self.calculate_ema(df_1h['close'], 200)
        df_1h['ATR'] = self.calculate_atr(df_1h, 14)
        
        # 15M 指標
        df_15m['RSI'] = self.calculate_rsi(df_15m['close'], 14)
        df_15m['volume_ma'] = df_15m['volume'].rolling(window=20).mean()
        
        # 回測邏輯
        print("\n開始回測...")
        print("\n策略參數:")
        print("  進場條件:")
        print("    1. 4H 趨勢明確（Uptrend 或 Downtrend）")
        print("    2. 1H 趨勢與 4H 一致")
        print("    3. RSI 30-70（放寬範圍）")
        print("    4. 價格接近 1H EMA 20/50（3% 範圍）")
        print("    5. 成交量 > 20 日平均")
        print("  風險管理:")
        print("    止損: 1.5 ATR")
        print("    目標: 3 ATR")
        print("    倉位: 15% 資金")
        print("    支持做多和做空")
        
        trades_count = 0
        wins = 0
        losses = 0
        signal_count = 0
        
        for i in range(200, len(df_1h)):
            timestamp = df_1h.index[i]
            price = df_1h['close'].iloc[i]
            
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
            
            # 獲取 15M RSI 和成交量
            idx_15m = min(i * 4, len(df_15m) - 1)
            rsi_15m = df_15m['RSI'].iloc[idx_15m]
            volume = df_15m['volume'].iloc[idx_15m]
            volume_ma = df_15m['volume_ma'].iloc[idx_15m]
            
            # 獲取 ATR
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
                        pnl = (price - entry_price) * self.position['size']
                        pnl_pct = (price / entry_price - 1) * 100
                        commission_cost = price * self.position['size'] * self.commission * 2
                        net_pnl = pnl - commission_cost
                        
                        self.capital += net_pnl
                        
                        self.trades.append({
                            'entry_time': self.position['entry_time'],
                            'exit_time': timestamp,
                            'direction': direction,
                            'entry_price': entry_price,
                            'exit_price': price,
                            'pnl': net_pnl,
                            'pnl_pct': pnl_pct,
                            'reason': '止損'
                        })
                        
                        losses += 1
                        self.position = None
                        continue
                    
                    if price >= take_profit:
                        pnl = (price - entry_price) * self.position['size']
                        pnl_pct = (price / entry_price - 1) * 100
                        commission_cost = price * self.position['size'] * self.commission * 2
                        net_pnl = pnl - commission_cost
                        
                        self.capital += net_pnl
                        
                        self.trades.append({
                            'entry_time': self.position['entry_time'],
                            'exit_time': timestamp,
                            'direction': direction,
                            'entry_price': entry_price,
                            'exit_price': price,
                            'pnl': net_pnl,
                            'pnl_pct': pnl_pct,
                            'reason': '獲利'
                        })
                        
                        wins += 1
                        self.position = None
                        continue
                
                # 做空的止損和目標
                elif direction == 'short':
                    if price >= stop_loss:
                        pnl = (entry_price - price) * self.position['size']
                        pnl_pct = (entry_price / price - 1) * 100
                        commission_cost = price * self.position['size'] * self.commission * 2
                        net_pnl = pnl - commission_cost
                        
                        self.capital += net_pnl
                        
                        self.trades.append({
                            'entry_time': self.position['entry_time'],
                            'exit_time': timestamp,
                            'direction': direction,
                            'entry_price': entry_price,
                            'exit_price': price,
                            'pnl': net_pnl,
                            'pnl_pct': pnl_pct,
                            'reason': '止損'
                        })
                        
                        losses += 1
                        self.position = None
                        continue
                    
                    if price <= take_profit:
                        pnl = (entry_price - price) * self.position['size']
                        pnl_pct = (entry_price / price - 1) * 100
                        commission_cost = price * self.position['size'] * self.commission * 2
                        net_pnl = pnl - commission_cost
                        
                        self.capital += net_pnl
                        
                        self.trades.append({
                            'entry_time': self.position['entry_time'],
                            'exit_time': timestamp,
                            'direction': direction,
                            'entry_price': entry_price,
                            'exit_price': price,
                            'pnl': net_pnl,
                            'pnl_pct': pnl_pct,
                            'reason': '獲利'
                        })
                        
                        wins += 1
                        self.position = None
                        continue
            
            # 如果沒有持倉，檢查進場條件
            if not self.position:
                # 條件 1：4H 趨勢明確
                if trend_4h in ['Uptrend', 'Downtrend']:
                    # 條件 2：1H 趨勢與 4H 一致
                    if trend_1h == trend_4h:
                        # 條件 3：RSI 正常（放寬）
                        if 30 <= rsi_15m <= 70:
                            # 條件 4：成交量確認
                            if volume > volume_ma:
                                # 條件 5：價格接近 EMA（放寬到 3%）
                                ema20 = df_1h['EMA_20'].iloc[i]
                                ema50 = df_1h['EMA_50'].iloc[i]
                                
                                near_ema20 = abs(price - ema20) / ema20 < 0.03
                                near_ema50 = abs(price - ema50) / ema50 < 0.03
                                
                                if near_ema20 or near_ema50:
                                    signal_count += 1
                                    
                                    # 決定方向
                                    direction = 'long' if trend_4h == 'Uptrend' else 'short'
                                    
                                    # 進場！
                                    size = (self.capital * 0.15) / price  # 使用 15% 資金
                                    
                                    if direction == 'long':
                                        stop_loss = price - (atr * 1.5)
                                        take_profit = price + (atr * 3)
                                    else:  # short
                                        stop_loss = price + (atr * 1.5)
                                        take_profit = price - (atr * 3)
                                    
                                    self.position = {
                                        'entry_time': timestamp,
                                        'entry_price': price,
                                        'size': size,
                                        'stop_loss': stop_loss,
                                        'take_profit': take_profit,
                                        'direction': direction
                                    }
                                    
                                    trades_count += 1
                                    
                                    if trades_count <= 15:  # 打印前 15 筆
                                        print(f"\n交易 #{trades_count}")
                                        print(f"  時間: {timestamp}")
                                        print(f"  方向: {'做多' if direction == 'long' else '做空'}")
                                        print(f"  進場: ${price:.2f}")
                                        if direction == 'long':
                                            print(f"  止損: ${stop_loss:.2f} (-{(1-stop_loss/price)*100:.2f}%)")
                                            print(f"  目標: ${take_profit:.2f} (+{(take_profit/price-1)*100:.2f}%)")
                                        else:
                                            print(f"  止損: ${stop_loss:.2f} (+{(stop_loss/price-1)*100:.2f}%)")
                                            print(f"  目標: ${take_profit:.2f} (-{(1-take_profit/price)*100:.2f}%)")
                                        print(f"  RSI: {rsi_15m:.1f}")
                                        print(f"  趨勢: 4H={trend_4h}, 1H={trend_1h}")
        
        # 如果還有持倉，以最後價格平倉
        if self.position:
            price = df_1h['close'].iloc[-1]
            entry_price = self.position['entry_price']
            direction = self.position['direction']
            
            if direction == 'long':
                pnl = (price - entry_price) * self.position['size']
                pnl_pct = (price / entry_price - 1) * 100
            else:
                pnl = (entry_price - price) * self.position['size']
                pnl_pct = (entry_price / price - 1) * 100
            
            commission_cost = price * self.position['size'] * self.commission * 2
            net_pnl = pnl - commission_cost
            
            self.capital += net_pnl
            
            self.trades.append({
                'entry_time': self.position['entry_time'],
                'exit_time': df_1h.index[-1],
                'direction': direction,
                'entry_price': entry_price,
                'exit_price': price,
                'pnl': net_pnl,
                'pnl_pct': pnl_pct,
                'reason': '強制平倉'
            })
            
            if net_pnl > 0:
                wins += 1
            else:
                losses += 1
        
        # 打印結果
        print("\n" + "=" * 100)
        print("回測結果")
        print("=" * 100)
        
        print(f"\n檢測到的信號數: {signal_count}")
        print(f"總交易次數: {len(self.trades)}")
        print(f"獲利交易: {wins} 次")
        print(f"虧損交易: {losses} 次")
        print(f"勝率: {wins/len(self.trades)*100 if len(self.trades) > 0 else 0:.2f}%")
        
        if len(self.trades) > 0:
            total_pnl = sum([t['pnl'] for t in self.trades])
            avg_pnl = total_pnl / len(self.trades)
            
            win_trades = [t for t in self.trades if t['pnl'] > 0]
            loss_trades = [t for t in self.trades if t['pnl'] < 0]
            
            avg_win = sum([t['pnl'] for t in win_trades]) / len(win_trades) if win_trades else 0
            avg_loss = sum([t['pnl'] for t in loss_trades]) / len(loss_trades) if loss_trades else 0
            
            profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else 0
            
            # 計算每週交易次數
            days = (df_1h.index[-1] - df_1h.index[200]).days
            weeks = days / 7
            trades_per_week = len(self.trades) / weeks if weeks > 0 else 0
            
            print(f"\n總損益: {total_pnl:.2f} USDT")
            print(f"平均損益: {avg_pnl:.2f} USDT")
            print(f"平均獲利: {avg_win:.2f} USDT")
            print(f"平均虧損: {avg_loss:.2f} USDT")
            print(f"獲利因子: {profit_factor:.2f}")
            
            print(f"\n最終資金: {self.capital:.2f} USDT")
            print(f"總收益: {self.capital - self.initial_capital:.2f} USDT")
            print(f"收益率: {(self.capital/self.initial_capital - 1)*100:.2f}%")
            
            print(f"\n交易頻率: {trades_per_week:.2f} 筆/週")
            print(f"回測天數: {days} 天")
            
            # 打印交易詳情
            print("\n" + "=" * 100)
            print("交易詳情")
            print("=" * 100)
            
            for i, trade in enumerate(self.trades):
                direction_text = '做多' if trade['direction'] == 'long' else '做空'
                result_text = '✅ 獲利' if trade['pnl'] > 0 else '❌ 虧損'
                print(f"\n交易 #{i+1} {result_text}")
                print(f"  時間: {trade['entry_time']} → {trade['exit_time']}")
                print(f"  方向: {direction_text}")
                print(f"  進場: ${trade['entry_price']:.2f}")
                print(f"  出場: ${trade['exit_price']:.2f}")
                print(f"  損益: {trade['pnl']:.2f} USDT ({trade['pnl_pct']:.2f}%)")
                print(f"  原因: {trade['reason']}")
        
        return self.trades


def main():
    """主函數"""
    # 讀取數據
    print("讀取市場數據...")
    df_1d = pd.read_csv('market_data_ETHUSDT_1d.csv')
    df_4h = pd.read_csv('market_data_ETHUSDT_4h.csv')
    df_1h = pd.read_csv('market_data_ETHUSDT_1h.csv')
    df_15m = pd.read_csv('market_data_ETHUSDT_15m.csv')
    
    # 轉換時間戳
    for df in [df_1d, df_4h, df_1h, df_15m]:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
    
    # 創建回測引擎
    backtest = ImprovedBacktest(initial_capital=1000, commission=0.0005)
    
    # 執行回測
    trades = backtest.run(df_1d, df_4h, df_1h, df_15m)
    
    # 保存結果
    if trades:
        trades_df = pd.DataFrame(trades)
        trades_df.to_csv('improved_backtest_results.csv', index=False)
        print(f"\n交易記錄已保存至 improved_backtest_results.csv")


if __name__ == '__main__':
    main()
