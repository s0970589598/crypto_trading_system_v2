#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自動交易提醒系統
實時監控市場，當符合進場條件時發送通知
"""

import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import json
import os
from pathlib import Path

class TradingAlertSystem:
    """交易提醒系統"""
    
    def __init__(self, symbol='ETHUSDT', telegram_token=None, chat_id=None, strategy_mode=None):
        self.symbol = symbol
        
        # 從環境變數或參數獲取 Telegram 配置
        self.telegram_token = telegram_token or self._load_env_var('TELEGRAM_BOT_TOKEN')
        self.chat_id = chat_id or self._load_env_var('TELEGRAM_CHAT_ID')
        
        # 策略模式配置
        self.strategy_mode = strategy_mode or self._load_env_var('STRATEGY_MODE') or 'aggressive'
        self._configure_strategy()
        # 策略模式配置
        self.strategy_mode = strategy_mode or self._load_env_var('STRATEGY_MODE') or 'aggressive'
        self._configure_strategy()
        
        # 交易狀態
        self.trades_today = 0
        self.consecutive_losses = 0
        self.last_trade_time = None
        self.daily_loss = 0
        
        # 黃金時段（UTC+8）
        self.golden_hours = [23, 10, 21, 19, 14, 11, 12, 7, 17]
        
        # 黃金日（0=週一, 6=週日）
        self.golden_days = [2, 3]  # 週三、週四
        
        # 地獄時段
        self.hell_hours = [8, 22, 2, 16, 4, 3, 13, 1, 9, 6]
        
        print("=" * 80)
        print(f"交易提醒系統已啟動（{self.strategy_name}）")
        print("=" * 80)
        print(f"監控標的：{symbol}")
        print(f"策略模式：{self.strategy_name}")
        print(f"策略版本：{self.strategy_description}")
        print(f"進場條件：4H/1H 趨勢一致 + RSI 30-70 + 價格近 EMA（3%）+ 成交量確認")
        print(f"風險管理：止損 {self.stop_loss_atr} ATR，目標 {self.take_profit_atr} ATR")
        print(f"建議配置：{self.recommended_config}")
        if self.telegram_token and self.chat_id:
            print(f"✅ Telegram 通知已啟用")
        else:
            print(f"⚠️ Telegram 通知未啟用")
        print("=" * 80)
    
    def _configure_strategy(self):
        """配置策略參數"""
        if self.strategy_mode.lower() in ['aggressive', 'a', '1', '1.5']:
            # 激進模式：1.5 ATR 止損（推薦）
            self.stop_loss_atr = 1.5
            self.take_profit_atr = 3.0
            self.strategy_name = "激進模式（推薦）"
            self.strategy_description = "勝率 54.5%，收益 +40.4%，回撤 6.7%，交易 33 筆"
            self.recommended_config = "5x 槓桿 + 20% 倉位（單筆風險 ~1.5%）"
        elif self.strategy_mode.lower() in ['relaxed', 'r', '2', '2.0']:
            # 輕鬆模式：2.0 ATR 止損
            self.stop_loss_atr = 2.0
            self.take_profit_atr = 4.0
            self.strategy_name = "輕鬆模式"
            self.strategy_description = "勝率 45.5%，收益 +18.8%，回撤 11.2%，交易 22 筆"
            self.recommended_config = "5x 槓桿 + 20% 倉位（單筆風險 ~2%）"
        else:
            # 自定義模式
            try:
                self.stop_loss_atr = float(self._load_env_var('STOP_LOSS_ATR') or 1.5)
                self.take_profit_atr = float(self._load_env_var('TAKE_PROFIT_ATR') or 3.0)
                self.strategy_name = "自定義模式"
                self.strategy_description = f"止損 {self.stop_loss_atr} ATR，目標 {self.take_profit_atr} ATR"
                self.recommended_config = "5x 槓桿 + 20% 倉位"
            except:
                # 默認使用激進模式
                self.stop_loss_atr = 1.5
                self.take_profit_atr = 3.0
                self.strategy_name = "激進模式（默認）"
                self.strategy_description = "勝率 54.5%，收益 +40.4%，回撤 6.7%"
                self.recommended_config = "5x 槓桿 + 20% 倉位（單筆風險 ~1.5%）"
    
    def _load_env_var(self, key):
        """從 .env 文件或環境變數載入配置"""
        # 先檢查環境變數
        value = os.getenv(key)
        if value:
            return value
        
        # 再檢查 .env 文件
        env_file = Path('.env')
        if env_file.exists():
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        env_key, env_value = line.split('=', 1)
                        if env_key.strip() == key:
                            return env_value.strip()
        
        return None
    
    def fetch_klines(self, interval, limit=200):
        """獲取 K 線數據"""
        url = "https://api.binance.com/api/v3/klines"
        params = {
            'symbol': self.symbol,
            'interval': interval,
            'limit': limit
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            klines = response.json()
            
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ])
            
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
            
            return df
        
        except Exception as e:
            print(f"獲取數據失敗：{e}")
            return None
    
    def calculate_indicators(self, df):
        """計算技術指標"""
        # EMA
        df['EMA_20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['EMA_50'] = df['close'].ewm(span=50, adjust=False).mean()
        df['EMA_200'] = df['close'].ewm(span=200, adjust=False).mean()
        
        # ATR
        df['high_low'] = df['high'] - df['low']
        df['high_close'] = abs(df['high'] - df['close'].shift())
        df['low_close'] = abs(df['low'] - df['close'].shift())
        df['true_range'] = df[['high_low', 'high_close', 'low_close']].max(axis=1)
        df['ATR'] = df['true_range'].rolling(window=14).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # 趨勢判斷
        df['Trend'] = 'Neutral'
        df.loc[(df['EMA_20'] > df['EMA_50']) & (df['EMA_50'] > df['EMA_200']), 'Trend'] = 'Uptrend'
        df.loc[(df['EMA_20'] < df['EMA_50']) & (df['EMA_50'] < df['EMA_200']), 'Trend'] = 'Downtrend'
        
        return df
    
    def check_trend_alignment(self):
        """檢查多週期趨勢一致性"""
        # 獲取各週期數據
        df_1d = self.fetch_klines('1d', 200)
        df_4h = self.fetch_klines('4h', 200)
        df_1h = self.fetch_klines('1h', 200)
        df_15m = self.fetch_klines('15m', 200)
        
        if any(df is None for df in [df_1d, df_4h, df_1h, df_15m]):
            return None
        
        # 計算指標
        df_1d = self.calculate_indicators(df_1d)
        df_4h = self.calculate_indicators(df_4h)
        df_1h = self.calculate_indicators(df_1h)
        df_15m = self.calculate_indicators(df_15m)
        
        # 獲取最新數據
        trend_1d = df_1d.iloc[-1]['Trend']
        trend_4h = df_4h.iloc[-1]['Trend']
        trend_1h = df_1h.iloc[-1]['Trend']
        trend_15m = df_15m.iloc[-1]['Trend']
        
        rsi_15m = df_15m.iloc[-1]['RSI']
        atr_1h = df_1h.iloc[-1]['ATR']
        
        price = df_1h.iloc[-1]['close']
        ema20_1h = df_1h.iloc[-1]['EMA_20']
        ema50_1h = df_1h.iloc[-1]['EMA_50']
        
        # 計算成交量
        volume_20d_avg = df_15m['volume'].rolling(window=20).mean().iloc[-1]
        current_volume = df_15m.iloc[-1]['volume']
        
        return {
            'trend_1d': trend_1d,
            'trend_4h': trend_4h,
            'trend_1h': trend_1h,
            'trend_15m': trend_15m,
            'rsi_15m': rsi_15m,
            'atr_1h': atr_1h,
            'price': price,
            'ema20_1h': ema20_1h,
            'ema50_1h': ema50_1h,
            'volume_ratio': current_volume / volume_20d_avg if volume_20d_avg > 0 else 0
        }
    
    def check_entry_conditions(self, market_data):
        """檢查進場條件（改進版策略）"""
        conditions = {
            'trend_aligned': False,
            'rsi_ok': False,
            'price_near_ema': False,
            'volume_ok': False,
            'trade_limit_ok': False,
            'no_consecutive_losses': False
        }
        
        reasons = []
        
        # 1. 檢查趨勢一致性（4H 和 1H）
        trend_4h = market_data['trend_4h']
        trend_1h = market_data['trend_1h']
        
        if trend_4h == trend_1h and trend_4h in ['Uptrend', 'Downtrend']:
            conditions['trend_aligned'] = True
            direction = '做多' if trend_4h == 'Uptrend' else '做空'
            reasons.append(f"✅ 週期共振：{trend_4h}（{direction}）")
        else:
            reasons.append(f"❌ 週期不一致：4H={trend_4h}, 1H={trend_1h}")
        
        # 2. 檢查 RSI（放寬到 30-70）
        if 30 <= market_data['rsi_15m'] <= 70:
            conditions['rsi_ok'] = True
            reasons.append(f"✅ RSI 正常：{market_data['rsi_15m']:.1f}")
        else:
            reasons.append(f"❌ RSI 異常：{market_data['rsi_15m']:.1f}（需要 30-70）")
        
        # 3. 檢查價格是否接近 EMA（放寬到 3%）
        price = market_data['price']
        ema20 = market_data['ema20_1h']
        ema50 = market_data['ema50_1h']
        
        near_ema20 = abs(price - ema20) / ema20 < 0.03
        near_ema50 = abs(price - ema50) / ema50 < 0.03
        
        if near_ema20 or near_ema50:
            conditions['price_near_ema'] = True
            if near_ema20:
                reasons.append(f"✅ 價格接近 EMA 20：${price:.2f} vs ${ema20:.2f}")
            else:
                reasons.append(f"✅ 價格接近 EMA 50：${price:.2f} vs ${ema50:.2f}")
        else:
            reasons.append(f"❌ 價格未回調：${price:.2f}（EMA20=${ema20:.2f}, EMA50=${ema50:.2f}）")
        
        # 4. 檢查成交量
        if market_data['volume_ratio'] > 1.0:
            conditions['volume_ok'] = True
            reasons.append(f"✅ 成交量確認：{market_data['volume_ratio']:.2f}x")
        else:
            reasons.append(f"⚠️ 成交量偏低：{market_data['volume_ratio']:.2f}x（建議 > 1.0x）")
        
        # 5. 檢查每日交易次數（放寬到 3 筆）
        if self.trades_today < 3:
            conditions['trade_limit_ok'] = True
            reasons.append(f"✅ 交易次數：{self.trades_today}/3")
        else:
            reasons.append(f"🔴 達到每日上限：{self.trades_today}/3")
        
        # 6. 檢查連續虧損
        if self.consecutive_losses < 3:
            conditions['no_consecutive_losses'] = True
            reasons.append(f"✅ 連續虧損：{self.consecutive_losses}/3")
        else:
            reasons.append(f"🔴 連續虧損過多：{self.consecutive_losses}/3（熔斷）")
        
        return conditions, reasons
    
    def send_telegram_message(self, message):
        """發送 Telegram 通知"""
        if not self.telegram_token or not self.chat_id:
            return
        
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        
        # 將 Markdown 格式轉換為純文本（Telegram 對格式要求嚴格）
        clean_message = message.replace('**', '').replace('*', '')
        
        data = {
            'chat_id': self.chat_id,
            'text': clean_message
        }
        
        try:
            response = requests.post(url, data=data, timeout=10)
            response.raise_for_status()
            print("✅ Telegram 通知已發送")
        except Exception as e:
            print(f"❌ Telegram 通知失敗：{e}")
            print(f"   Token: {self.telegram_token[:20]}...")
            print(f"   Chat ID: {self.chat_id}")
    
    def generate_alert_message(self, market_data, conditions, reasons):
        """生成提醒訊息"""
        all_conditions_met = all(conditions.values())
        
        message = f"🔔 **交易提醒 - {self.symbol}**\n\n"
        message += f"⏰ 時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        if all_conditions_met:
            message += "🟢 **所有條件符合！可以交易！**\n\n"
        else:
            message += "🟡 **部分條件不符合**\n\n"
        
        message += "**市場狀態**\n"
        message += f"• 價格：${market_data['price']:.2f}\n"
        message += f"• 1D 趨勢：{market_data['trend_1d']}\n"
        message += f"• 4H 趨勢：{market_data['trend_4h']}\n"
        message += f"• 1H 趨勢：{market_data['trend_1h']}\n"
        message += f"• 15M RSI：{market_data['rsi_15m']:.1f}\n"
        message += f"• 1H ATR：${market_data['atr_1h']:.2f}\n\n"
        
        message += "**檢查結果**\n"
        for reason in reasons:
            message += f"{reason}\n"
        
        if all_conditions_met:
            # 計算建議的止損和目標（根據策略模式）
            atr = market_data['atr_1h']
            price = market_data['price']
            trend = market_data['trend_4h']
            
            if trend == 'Uptrend':
                stop_loss = price - (atr * self.stop_loss_atr)
                take_profit = price + (atr * self.take_profit_atr)
                direction = "做多"
            else:  # Downtrend
                stop_loss = price + (atr * self.stop_loss_atr)
                take_profit = price - (atr * self.take_profit_atr)
                direction = "做空"
            
            message += f"\n**交易建議（{self.strategy_name}）**\n"
            message += f"• 方向：{direction}\n"
            message += f"• 進場：${price:.2f}\n"
            message += f"• 止損：${stop_loss:.2f}（{abs(stop_loss-price)/price*100:.2f}%）\n"
            message += f"• 目標：${take_profit:.2f}（{abs(take_profit-price)/price*100:.2f}%）\n"
            message += f"• 盈虧比：2:1\n"
            message += f"• 建議倉位：20% 資金\n"
            message += f"• 建議槓桿：5x（推薦）或 10x（激進）\n"
            
            if self.strategy_mode.lower() in ['aggressive', 'a', '1', '1.5']:
                message += f"• 預期：單筆風險 ~1.5%，收益 ~3%\n"
            else:
                message += f"• 預期：單筆風險 ~2%，收益 ~4%\n"
        
        return message, all_conditions_met
    
    def run(self, check_interval=300):
        """運行監控系統"""
        print(f"\n開始監控 {self.symbol}...")
        print(f"檢查間隔：{check_interval} 秒")
        print("按 Ctrl+C 停止\n")
        
        try:
            while True:
                print(f"\n{'='*80}")
                print(f"檢查時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"{'='*80}")
                
                # 獲取市場數據
                market_data = self.check_trend_alignment()
                
                if market_data is None:
                    print("❌ 無法獲取市場數據，等待下次檢查...")
                    time.sleep(check_interval)
                    continue
                
                # 檢查進場條件
                conditions, reasons = self.check_entry_conditions(market_data)
                
                # 生成提醒訊息
                message, all_met = self.generate_alert_message(market_data, conditions, reasons)
                
                # 打印到控制台
                print(message)
                
                # 如果所有條件符合，發送 Telegram 通知
                if all_met:
                    self.send_telegram_message(message)
                    print("\n🎯 所有條件符合！請準備交易！")
                
                # 等待下次檢查
                print(f"\n等待 {check_interval} 秒後再次檢查...")
                time.sleep(check_interval)
        
        except KeyboardInterrupt:
            print("\n\n監控系統已停止")
        except Exception as e:
            print(f"\n❌ 錯誤：{e}")


def main():
    """主函數"""
    print("=" * 80)
    print("交易提醒系統")
    print("=" * 80)
    
    # 檢查是否有 .env 文件
    env_file = Path('.env')
    if env_file.exists():
        print("✅ 找到 .env 配置文件")
        
        # 從 .env 載入配置
        symbol = os.getenv('SYMBOL', 'ETHUSDT')
        check_interval = int(os.getenv('CHECK_INTERVAL', '300'))
        
        # 載入 .env 文件中的配置
        config = {}
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip()
        
        symbol = config.get('SYMBOL', 'ETHUSDT')
        check_interval = int(config.get('CHECK_INTERVAL', '300'))
        
        print(f"交易對：{symbol}")
        print(f"檢查間隔：{check_interval} 秒")
        
        # 詢問是否使用這些配置
        print("\n使用 .env 配置？(y/n，預設 y)：")
        use_env = input().strip().lower()
        
        if use_env == '' or use_env == 'y':
            # 使用 .env 配置
            alert_system = TradingAlertSystem(symbol=symbol)
            alert_system.run(check_interval=check_interval)
            return
    
    # 手動配置
    print("\n手動配置模式")
    symbol = input("請輸入交易對（預設 ETHUSDT）：").strip() or 'ETHUSDT'
    
    print("\n是否設置 Telegram 通知？（y/n）")
    use_telegram = input().strip().lower() == 'y'
    
    telegram_token = None
    chat_id = None
    
    if use_telegram:
        print("\n請輸入 Telegram Bot Token：")
        telegram_token = input().strip()
        print("請輸入 Telegram Chat ID：")
        chat_id = input().strip()
    
    print("\n請輸入檢查間隔（秒，預設 300）：")
    interval_input = input().strip()
    check_interval = int(interval_input) if interval_input else 300
    
    # 創建提醒系統
    alert_system = TradingAlertSystem(
        symbol=symbol,
        telegram_token=telegram_token,
        chat_id=chat_id
    )
    
    # 運行
    alert_system.run(check_interval=check_interval)


if __name__ == '__main__':
    main()
