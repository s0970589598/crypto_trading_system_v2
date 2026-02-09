"""
Quality Scoring Module
"""

import streamlit as st
import pandas as pd
import json
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
from datetime import datetime
import sys
import traceback
import numpy as np

# 添加當前目錄到路徑
sys.path.insert(0, ".")

def render():
    """渲染quality scoring頁面"""
    # 確保 Path 可用
    from pathlib import Path as PathClass
    
    st.subheader("⭐ 執行質量評分")
    
    # 檢查是否有交易記錄
    orders_dir = PathClass("data/review_history/bingx/orders")
    
    if not orders_dir.exists():
        st.warning("⚠️ 請先上傳交易記錄")
        st.info("請到「交易記錄管理」上傳 BingX Order History 文件")
    else:
        # 載入所有交易記錄
        all_orders = []
        for json_file in orders_dir.rglob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    orders = json.load(f)
                    all_orders.extend(orders)
            except:
                pass
        
        if not all_orders:
            st.warning("⚠️ 沒有找到交易記錄")
        else:
            df = pd.DataFrame(all_orders)
            
            # 轉換時間
            df['close_time'] = pd.to_datetime(df['close_time'], errors='coerce')
            df = df.sort_values('close_time', ascending=False)
            
            st.write(f"**總交易數**：{len(df)} 筆")
            
            # 選擇要評分的交易
            st.subheader("📝 選擇交易進行評分")
            
            # 篩選選項
            col1, col2, col3 = st.columns(3)
            
            with col1:
                show_count = st.selectbox(
                    "顯示筆數",
                    [20, 50, 100, 200, "全部"],
                    index=2
                )
            
            with col2:
                filter_direction = st.selectbox(
                    "方向篩選",
                    ["全部", "Long", "Short"]
                )
            
            with col3:
                filter_pnl = st.selectbox(
                    "盈虧篩選",
                    ["全部", "獲利", "虧損"]
                )
            
            # 應用篩選
            filtered_df = df.copy()
            
            if filter_direction != "全部":
                filtered_df = filtered_df[filtered_df['direction'] == filter_direction]
            
            if filter_pnl == "獲利":
                filtered_df = filtered_df[filtered_df['pnl'] > 0]
            elif filter_pnl == "虧損":
                filtered_df = filtered_df[filtered_df['pnl'] < 0]
            
            # 顯示筆數
            if show_count == "全部":
                recent_trades = filtered_df
            else:
                recent_trades = filtered_df.head(show_count)
            
            st.write(f"**顯示 {len(recent_trades)} 筆交易**")
            
            # 重置索引以避免索引錯誤
            recent_trades = recent_trades.reset_index(drop=True)
            
            # 創建顯示用的 DataFrame（增加更多欄位）
            display_cols = ['open_time', 'close_time', 'symbol', 'direction', 'leverage', 
                           'entry_price', 'exit_price', 'pnl', 'fee', 'close_type']
            available_cols = [col for col in display_cols if col in recent_trades.columns]
            
            display_df = recent_trades[available_cols].copy()
            
            # 重命名欄位
            col_names = {
                'open_time': '開倉時間',
                'close_time': '平倉時間',
                'symbol': '交易對',
                'direction': '方向',
                'leverage': '槓桿',
                'entry_price': '進場價',
                'exit_price': '出場價',
                'pnl': '盈虧',
                'fee': '手續費',
                'close_type': '平倉類型'
            }
            display_df.columns = [col_names.get(col, col) for col in display_df.columns]
            
            # 載入已評分的交易 ID
            quality_file = PathClass("data/review_history/quality_scores.json")
            scored_trade_ids = set()
            
            if quality_file.exists():
                try:
                    with open(quality_file, 'r', encoding='utf-8') as f:
                        scores_data = json.load(f)
                    
                    # 轉換舊格式（字典）為新格式（列表）
                    if isinstance(scores_data, dict):
                        existing_scores = list(scores_data.values())
                    else:
                        existing_scores = scores_data
                    
                    # 收集已評分的交易 ID
                    for score in existing_scores:
                        if 'trade_id' in score:
                            scored_trade_ids.add(score['trade_id'])
                except:
                    pass
            
            # 添加評分狀態欄位
            display_df.insert(0, '狀態', recent_trades['trade_id'].apply(
                lambda x: '✅ 已評分' if x in scored_trade_ids else '⭕ 未評分'
            ))
            
            # 添加選擇欄位
            display_df.insert(0, '選擇', False)
            
            # 格式化數值
            if '盈虧' in display_df.columns:
                display_df['盈虧'] = display_df['盈虧'].apply(lambda x: f"{x:.2f}")
            if '手續費' in display_df.columns:
                display_df['手續費'] = display_df['手續費'].apply(lambda x: f"{x:.4f}")
            if '進場價' in display_df.columns:
                display_df['進場價'] = display_df['進場價'].apply(lambda x: f"{x:.2f}" if pd.notna(x) and x > 0 else "N/A")
            if '出場價' in display_df.columns:
                display_df['出場價'] = display_df['出場價'].apply(lambda x: f"{x:.2f}" if pd.notna(x) and x > 0 else "N/A")
            
            # 全選功能
            col1, col2 = st.columns([1, 4])
            with col1:
                select_all = st.checkbox("全選", key="select_all_trades")
            
            if select_all:
                display_df['選擇'] = True
            
            # 使用 data_editor 讓用戶選擇
            edited_df = st.data_editor(
                display_df,
                column_config={
                    "選擇": st.column_config.CheckboxColumn(
                        "選擇",
                        help="選擇要評分的交易",
                        default=False,
                    )
                },
                disabled=[col for col in display_df.columns if col != '選擇'],
                hide_index=True,
                use_container_width=True,
                height=400
            )
            
            # 獲取選中的交易
            selected_indices = edited_df[edited_df['選擇']].index.tolist()
            
            if len(selected_indices) > 0:
                st.write(f"**已選擇 {len(selected_indices)} 筆交易**")
                
                # 評分方式選擇
                scoring_mode = st.radio(
                    "評分方式",
                    ["手動評分", "自動評分"],
                    horizontal=True
                )
                
                if scoring_mode == "自動評分":
                    st.info("💡 系統將根據交易表現和市場數據自動計算評分")
                    
                    # 市場分析選項
                    use_market_analysis = st.checkbox(
                        "🔬 啟用市場數據分析（分析進場時的市場環境和技術指標）",
                        value=True,
                        help="需要市場數據文件（market_data_*.csv）"
                    )
                    
                    if st.button("🤖 執行自動評分", type="primary"):
                        # 初始化市場分析器
                        market_analyzer = None
                        if use_market_analysis:
                            try:
                                market_analyzer = MarketAnalyzer()
                                st.info("✅ 市場分析器已啟用")
                            except Exception as e:
                                st.warning(f"⚠️ 市場分析器初始化失敗：{e}")
                                market_analyzer = None
                        
                        # 載入現有評分
                        quality_file = PathClass("data/review_history/quality_scores.json")
                        quality_file.parent.mkdir(parents=True, exist_ok=True)
                        
                        existing_scores = []
                        if quality_file.exists():
                            try:
                                with open(quality_file, 'r', encoding='utf-8') as f:
                                    scores_data = json.load(f)
                                
                                # 轉換舊格式（字典）為新格式（列表）
                                if isinstance(scores_data, dict):
                                    existing_scores = list(scores_data.values())
                                else:
                                    existing_scores = scores_data
                            except:
                                existing_scores = []
                        
                        # 進度條
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        # 為每個選中的交易自動評分
                        for i, idx in enumerate(selected_indices):
                            status_text.text(f"正在評分第 {i+1}/{len(selected_indices)} 筆交易...")
                            trade = recent_trades.iloc[idx]
                            
                            # 自動評分邏輯（改進版 v2.1）
                            # 從 70 分開始（及格分），需要做對事情才能加分
                            entry_score = 70.0
                            exit_score = 70.0
                            risk_score = 70.0
                            discipline_score = 70.0
                            errors = []
                            
                            # 計算持倉時間
                            if pd.notna(trade.get('open_time')) and pd.notna(trade.get('close_time')):
                                open_time = pd.to_datetime(trade['open_time'])
                                close_time = pd.to_datetime(trade['close_time'])
                                holding_hours = (close_time - open_time).total_seconds() / 3600
                            else:
                                holding_hours = 0
                            
                            # 識別交易風格
                            if holding_hours < 1:
                                trading_style = 'scalping'  # 超短線
                                style_name = '超短線'
                                min_profit_pct = 0.2
                                max_loss_pct = 0.5
                                min_rr_ratio = 1.0
                            elif holding_hours < 4:
                                trading_style = 'day_trading'  # 日內交易
                                style_name = '日內'
                                min_profit_pct = 0.5
                                max_loss_pct = 1.0
                                min_rr_ratio = 1.5
                            elif holding_hours < 24:
                                trading_style = 'swing'  # 短線波段
                                style_name = '短線'
                                min_profit_pct = 1.0
                                max_loss_pct = 2.0
                                min_rr_ratio = 2.0
                            else:
                                trading_style = 'position'  # 中長線
                                style_name = '中長線'
                                min_profit_pct = 2.0
                                max_loss_pct = 3.0
                                min_rr_ratio = 3.0
                            
                            # 計算盈虧百分比和實際收益率
                            entry_price = trade.get('entry_price', 0)
                            exit_price = trade.get('exit_price', 0)
                            leverage = trade.get('leverage', 1)
                            
                            if entry_price > 0 and exit_price > 0:
                                if trade['direction'] == 'Long':
                                    pnl_pct = ((exit_price - entry_price) / entry_price) * 100
                                else:  # Short
                                    pnl_pct = ((entry_price - exit_price) / entry_price) * 100
                                
                                # 計算實際收益率（考慮槓桿）
                                actual_return = pnl_pct * leverage
                            else:
                                pnl_pct = 0
                                actual_return = 0
                            
                            # 市場分析（如果啟用）
                            market_analysis = None
                            if market_analyzer and pd.notna(trade.get('open_time')):
                                try:
                                    # 提取交易對並轉換為 Binance 格式
                                    raw_symbol = str(trade['symbol']).strip()
                                    
                                    # 處理不同格式的交易對
                                    if raw_symbol.lower() in ['btc', 'bitcoin']:
                                        symbol = 'BTCUSDT'
                                    elif raw_symbol.lower() in ['eth', 'ethereum']:
                                        symbol = 'ETHUSDT'
                                    elif raw_symbol.lower() in ['bnb']:
                                        symbol = 'BNBUSDT'
                                    elif raw_symbol.lower() in ['sol', 'solana']:
                                        symbol = 'SOLUSDT'
                                    elif raw_symbol.lower() in ['xrp', 'ripple']:
                                        symbol = 'XRPUSDT'
                                    elif raw_symbol.lower() in ['doge', 'dogecoin']:
                                        symbol = 'DOGEUSDT'
                                    elif raw_symbol.lower() in ['ada', 'cardano']:
                                        symbol = 'ADAUSDT'
                                    elif raw_symbol.lower() in ['avax', 'avalanche']:
                                        symbol = 'AVAXUSDT'
                                    elif raw_symbol.lower() in ['dot', 'polkadot']:
                                        symbol = 'DOTUSDT'
                                    elif raw_symbol.lower() in ['matic', 'polygon']:
                                        symbol = 'MATICUSDT'
                                    elif raw_symbol.lower() in ['link', 'chainlink']:
                                        symbol = 'LINKUSDT'
                                    elif raw_symbol.lower() in ['uni', 'uniswap']:
                                        symbol = 'UNIUSDT'
                                    elif raw_symbol.lower() in ['atom', 'cosmos']:
                                        symbol = 'ATOMUSDT'
                                    elif raw_symbol.lower() in ['ltc', 'litecoin']:
                                        symbol = 'LTCUSDT'
                                    elif raw_symbol.lower() in ['etc', 'ethereum classic']:
                                        symbol = 'ETCUSDT'
                                    elif raw_symbol.lower() in ['bch', 'bitcoin cash']:
                                        symbol = 'BCHUSDT'
                                    elif raw_symbol.lower() in ['xlm', 'stellar']:
                                        symbol = 'XLMUSDT'
                                    elif raw_symbol.lower() in ['trx', 'tron']:
                                        symbol = 'TRXUSDT'
                                    elif raw_symbol.lower() in ['near']:
                                        symbol = 'NEARUSDT'
                                    elif raw_symbol.lower() in ['algo', 'algorand']:
                                        symbol = 'ALGOUSDT'
                                    elif raw_symbol.lower() in ['vet', 'vechain']:
                                        symbol = 'VETUSDT'
                                    elif raw_symbol.lower() in ['icp', 'internet computer']:
                                        symbol = 'ICPUSDT'
                                    elif raw_symbol.lower() in ['fil', 'filecoin']:
                                        symbol = 'FILUSDT'
                                    elif raw_symbol.lower() in ['apt', 'aptos']:
                                        symbol = 'APTUSDT'
                                    elif raw_symbol.lower() in ['arb', 'arbitrum']:
                                        symbol = 'ARBUSDT'
                                    elif raw_symbol.lower() in ['op', 'optimism']:
                                        symbol = 'OPUSDT'
                                    elif raw_symbol.lower() in ['sui']:
                                        symbol = 'SUIUSDT'
                                    else:
                                        # 通用處理：移除連字符，轉大寫
                                        symbol = raw_symbol.replace('-', '').upper()
                                        # 如果不是以 USDT 結尾，添加 USDT
                                        if not symbol.endswith('USDT'):
                                            # 移除可能的 USD 後綴
                                            if symbol.endswith('USD'):
                                                symbol = symbol[:-3] + 'USDT'
                                            else:
                                                symbol = symbol + 'USDT'
                                    
                                    status_text.text(f"正在評分第 {i+1}/{len(selected_indices)} 筆交易... (分析 {symbol} 市場數據)")
                                    
                                    # 分析進場時的市場狀態（多時區）
                                    market_analysis = market_analyzer.analyze_market_at_time(
                                        symbol=symbol,
                                        timestamp=open_time,
                                        intervals=['15m', '1h', '4h', '1d']
                                    )
                                    
                                    if market_analysis:
                                        status_text.text(f"正在評分第 {i+1}/{len(selected_indices)} 筆交易... (市場分析完成)")
                                    else:
                                        st.warning(f"⚠️ {trade['symbol']} 在 {open_time} 的市場數據不足")
                                except Exception as e:
                                    st.error(f"❌ 市場分析失敗（{trade['symbol']} at {open_time}）：{str(e)}")
                                    import traceback
                                    st.code(traceback.format_exc())
                                    market_analysis = None
                            
                            # 計算盈虧比（在評分之前）
                            risk_reward_ratio = None
                            estimated_stop_loss = None
                            risk_amount = None
                            stop_loss_method = None
                            
                            # 智能調整：根據實際持倉時間動態決定看幾根 K 線
                            if holding_hours < 1:
                                # 超短線（< 1 小時）：看前 1-2 根 K 線
                                LOOKBACK_CANDLES = 2
                                lookback_desc = "前1-2根"
                            elif holding_hours < 3:
                                # 短線（1-3 小時）：看前 5-8 根 K 線
                                LOOKBACK_CANDLES = 8
                                lookback_desc = "前8根"
                            elif holding_hours < 12:
                                # 日內（3-12 小時）：看前 15 根 K 線
                                LOOKBACK_CANDLES = 15
                                lookback_desc = "前15根"
                            elif holding_hours < 48:
                                # 波段（12-48 小時）：看前 20 根 K 線
                                LOOKBACK_CANDLES = 20
                                lookback_desc = "前20根"
                            else:
                                # 長線（> 48 小時）：看前 30 根 K 線
                                LOOKBACK_CANDLES = 30
                                lookback_desc = "前30根"
                            
                            if market_analysis and entry_price > 0:
                                # 獲取市場數據
                                atr = market_analysis.get('atr', 0)
                                sr = market_analysis.get('support_resistance', {})
                                
                                # 嘗試獲取 15 分鐘 K 線數據來找前低/前高
                                swing_high_low = None
                                try:
                                    if market_analyzer:
                                        # 提取交易對
                                        raw_symbol = str(trade['symbol']).strip()
                                        if raw_symbol.lower() in ['btc', 'bitcoin']:
                                            symbol = 'BTCUSDT'
                                        elif raw_symbol.lower() in ['eth', 'ethereum']:
                                            symbol = 'ETHUSDT'
                                        else:
                                            symbol = raw_symbol.upper()
                                            if not symbol.endswith('USDT'):
                                                symbol = symbol + 'USDT'
                                        
                                        # 載入 15 分鐘數據
                                        df_15m = market_analyzer.load_market_data(symbol, '15m')
                                        
                                        if df_15m is not None and len(df_15m) > 0:
                                            # 找到進場時間點
                                            df_15m['time_diff'] = abs((df_15m['timestamp'] - open_time).dt.total_seconds())
                                            entry_idx = df_15m['time_diff'].idxmin()
                                            
                                            # 往前看 N 根 K 線找前低/前高
                                            if entry_idx >= LOOKBACK_CANDLES:
                                                lookback_data = df_15m.loc[entry_idx-LOOKBACK_CANDLES:entry_idx-1]
                                                
                                                if trade['direction'] == 'Long':
                                                    # 做多：找前低
                                                    swing_high_low = lookback_data['low'].min()
                                                else:  # Short
                                                    # 做空：找前高
                                                    swing_high_low = lookback_data['high'].max()
                                except Exception as e:
                                    # 如果獲取失敗，繼續使用其他方法
                                    pass
                                
                                # 方法 1：使用前低/前高（優先）
                                if swing_high_low:
                                    if trade['direction'] == 'Long' and swing_high_low < entry_price:
                                        estimated_stop_loss = swing_high_low
                                        risk_amount = entry_price - estimated_stop_loss
                                        stop_loss_method = f"15分{lookback_desc}前低"
                                    elif trade['direction'] == 'Short' and swing_high_low > entry_price:
                                        estimated_stop_loss = swing_high_low
                                        risk_amount = estimated_stop_loss - entry_price
                                        stop_loss_method = f"15分{lookback_desc}前高"
                                
                                # 方法 2：使用支撐/阻力位
                                if not estimated_stop_loss:
                                    if trade['direction'] == 'Long':
                                        support = sr.get('support')
                                        if support and support < entry_price:
                                            estimated_stop_loss = support
                                            risk_amount = entry_price - estimated_stop_loss
                                            stop_loss_method = "支撐位"
                                    else:  # Short
                                        resistance = sr.get('resistance')
                                        if resistance and resistance > entry_price:
                                            estimated_stop_loss = resistance
                                            risk_amount = estimated_stop_loss - entry_price
                                            stop_loss_method = "阻力位"
                                
                                # 方法 3：使用 1.5 ATR（最後備用）
                                if not estimated_stop_loss and atr > 0:
                                    if trade['direction'] == 'Long':
                                        estimated_stop_loss = entry_price - (1.5 * atr)
                                        risk_amount = 1.5 * atr
                                    else:  # Short
                                        estimated_stop_loss = entry_price + (1.5 * atr)
                                        risk_amount = 1.5 * atr
                                    stop_loss_method = "1.5 ATR"
                                
                                # 計算盈虧比
                                if risk_amount and risk_amount > 0:
                                    actual_profit = abs(exit_price - entry_price)
                                    risk_reward_ratio = actual_profit / risk_amount
                            
                            # 1. 進場質量評分（改進版）
                            # 只評估槓桿與市場環境的匹配，不重複扣分
                            
                            # 市場環境分析（如果有數據）
                            if market_analysis:
                                # 趨勢方向與交易方向是否一致
                                trend = market_analysis.get('trend', 'unknown')
                                direction = trade['direction']
                                
                                # 計算確認信號數量
                                confirmations = 0
                                
                                # 趨勢確認
                                if direction == 'Long':
                                    if trend in ['strong_downtrend', 'downtrend']:
                                        errors.append(f"逆勢做多（市場{trend}）")
                                        entry_score -= 25
                                    elif trend == 'sideways':
                                        errors.append("震盪市做多，趨勢不明")
                                        entry_score -= 10
                                    elif trend in ['strong_uptrend', 'uptrend']:
                                        confirmations += 1
                                else:  # Short
                                    if trend in ['strong_uptrend', 'uptrend']:
                                        errors.append(f"逆勢做空（市場{trend}）")
                                        entry_score -= 25
                                    elif trend == 'sideways':
                                        errors.append("震盪市做空，趨勢不明")
                                        entry_score -= 10
                                    elif trend in ['strong_downtrend', 'downtrend']:
                                        confirmations += 1
                                
                                # RSI 確認（優化版：結合趨勢判斷）
                                rsi_state = market_analysis.get('rsi_state', 'unknown')
                                rsi = market_analysis.get('rsi', 50)
                                
                                if direction == 'Long':
                                    if rsi_state == 'overbought':
                                        if trend in ['strong_uptrend', 'uptrend']:
                                            # 強趨勢中的超買是正常的
                                            entry_score -= 5
                                            errors.append(f"RSI超買但趨勢強勁（RSI={rsi:.1f}）")
                                        else:
                                            entry_score -= 20
                                            errors.append(f"RSI超買時做多（RSI={rsi:.1f}）")
                                    elif rsi_state == 'neutral':
                                        confirmations += 1
                                    elif rsi_state == 'oversold':
                                        confirmations += 1  # 超賣時做多是好信號
                                else:  # Short
                                    if rsi_state == 'oversold':
                                        if trend in ['strong_downtrend', 'downtrend']:
                                            entry_score -= 5
                                            errors.append(f"RSI超賣但趨勢弱勢（RSI={rsi:.1f}）")
                                        else:
                                            entry_score -= 20
                                            errors.append(f"RSI超賣時做空（RSI={rsi:.1f}）")
                                    elif rsi_state == 'neutral':
                                        confirmations += 1
                                    elif rsi_state == 'overbought':
                                        confirmations += 1  # 超買時做空是好信號
                                
                                # MACD 確認
                                macd_state = market_analysis.get('macd_state', 'unknown')
                                
                                if direction == 'Long':
                                    if macd_state in ['death_cross', 'bearish']:
                                        errors.append(f"MACD看空時做多（{macd_state}）")
                                        entry_score -= 15
                                    elif macd_state in ['golden_cross', 'bullish']:
                                        confirmations += 1
                                else:  # Short
                                    if macd_state in ['golden_cross', 'bullish']:
                                        errors.append(f"MACD看多時做空（{macd_state}）")
                                        entry_score -= 15
                                    elif macd_state in ['death_cross', 'bearish']:
                                        confirmations += 1
                                
                                # 多重確認加分（減少加分幅度）
                                if confirmations >= 3:
                                    entry_score = min(100, entry_score + 10)
                                    errors.append("✅ 多重信號確認（3+）")
                                elif confirmations == 2:
                                    entry_score = min(100, entry_score + 5)
                                    errors.append("✅ 雙重信號確認")
                                
                                # 波動率與槓桿匹配（只在這裡評估槓桿）
                                volatility = market_analysis.get('volatility', 'normal')
                                
                                if volatility == 'very_high' and leverage > 20:
                                    errors.append("高波動市場使用高槓桿")
                                    entry_score -= 15
                                elif volatility == 'high' and leverage > 50:
                                    errors.append("波動市場使用極高槓桿")
                                    entry_score -= 10
                                
                                # 布林帶位置（優化版：結合趨勢和成交量）
                                bb_position = market_analysis.get('bb_position', 'unknown')
                                volume_state = market_analysis.get('volume_state', 'unknown')
                                
                                if direction == 'Long' and bb_position == 'above_upper':
                                    if trend == 'strong_uptrend' and volume_state == 'high':
                                        # 強勢突破，加分
                                        entry_score = min(100, entry_score + 5)
                                        errors.append("✅ 強勢突破布林上軌")
                                    else:
                                        errors.append("價格在布林帶上軌之上做多")
                                        entry_score -= 10
                                elif direction == 'Short' and bb_position == 'below_lower':
                                    if trend == 'strong_downtrend' and volume_state == 'high':
                                        entry_score = min(100, entry_score + 5)
                                        errors.append("✅ 強勢跌破布林下軌")
                                    else:
                                        errors.append("價格在布林帶下軌之下做空")
                                        entry_score -= 10
                            
                            # 2. 出場質量評分（改進版：使用實際收益率）
                            if trade['pnl'] > 0:
                                # 獲利交易
                                # 使用實際收益率評估（考慮槓桿）
                                if actual_return < min_profit_pct * leverage:
                                    errors.append(f"實際收益偏低（{actual_return:.2f}%，{style_name}交易建議>{min_profit_pct * leverage:.1f}%）")
                                    exit_score -= 20
                                elif actual_return < min_profit_pct * leverage * 2:
                                    errors.append(f"實際收益一般（{actual_return:.2f}%）")
                                    exit_score -= 10
                                
                                # 優秀收益加分（減少加分幅度）
                                if actual_return >= 20:
                                    exit_score = min(100, exit_score + 10)
                                    errors.append(f"✅ 優秀收益（{actual_return:.2f}%）")
                                elif actual_return >= 10:
                                    exit_score = min(100, exit_score + 5)
                                    errors.append(f"✅ 良好收益（{actual_return:.2f}%）")
                                # 移除 >= 5% 的加分（這是應該做到的）
                                
                            else:
                                # 虧損交易
                                # 使用實際虧損率評估
                                actual_loss = abs(actual_return)
                                
                                if actual_loss > max_loss_pct * leverage * 2:
                                    errors.append(f"實際虧損過大（{actual_loss:.2f}%，{style_name}交易建議<{max_loss_pct * leverage * 2:.1f}%）")
                                    exit_score -= 35
                                elif actual_loss > max_loss_pct * leverage:
                                    errors.append(f"實際虧損較大（{actual_loss:.2f}%）")
                                    exit_score -= 25
                                elif actual_loss > max_loss_pct * leverage * 0.5:
                                    errors.append(f"實際虧損超標（{actual_loss:.2f}%）")
                                    exit_score -= 15
                            
                            # 盈虧比評估（如果能計算）
                            if risk_reward_ratio:
                                if trade['pnl'] > 0:
                                    # 獲利交易的盈虧比評估
                                    if risk_reward_ratio >= min_rr_ratio * 1.5:
                                        # 優秀的盈虧比，加分（減少幅度）
                                        exit_score = min(100, exit_score + 5)
                                        errors.append(f"✅ 優秀盈虧比（1:{risk_reward_ratio:.2f}）")
                                    elif risk_reward_ratio >= min_rr_ratio:
                                        # 良好的盈虧比，不加分（這是應該做到的）
                                        errors.append(f"✅ 良好盈虧比（1:{risk_reward_ratio:.2f}）")
                                    elif risk_reward_ratio < min_rr_ratio * 0.5:
                                        # 盈虧比不佳
                                        errors.append(f"盈虧比不佳（1:{risk_reward_ratio:.2f}，{style_name}建議>{min_rr_ratio:.1f}）")
                                        exit_score -= 15
                                else:
                                    # 虧損交易，檢查是否超過預期風險
                                    actual_loss_price = abs(exit_price - entry_price)
                                    if risk_amount and actual_loss_price > risk_amount * 1.2:
                                        errors.append(f"虧損超過預期風險 {((actual_loss_price/risk_amount - 1) * 100):.1f}%")
                                        exit_score -= 20
                                    elif risk_amount and actual_loss_price <= risk_amount:
                                        # 嚴格止損，加分（減少幅度）
                                        exit_score = min(100, exit_score + 5)
                                        errors.append("✅ 嚴格執行止損")
                            
                            # 3. 風險管理評分（改進版：移除重複扣分）
                            # 3. 風險管理評分（改進版：移除重複扣分，增加正面激勵）
                            
                            # 槓桿合理性（根據倉位大小評估）
                            # 保守槓桿加分
                            if leverage <= 5:
                                risk_score = min(100, risk_score + 10)
                                errors.append("✅ 保守槓桿（≤5x）")
                            elif leverage <= 10:
                                risk_score = min(100, risk_score + 5)
                                errors.append("✅ 適中槓桿（≤10x）")
                            elif leverage > 100:
                                risk_score -= 40
                                errors.append("槓桿極高（>100x），風險過大")
                            elif leverage > 50:
                                risk_score -= 30
                                errors.append("槓桿過高（>50x）")
                            elif leverage > 20:
                                risk_score -= 20
                                errors.append("槓桿偏高（>20x）")
                            
                            # 手續費佔比
                            fee = abs(trade.get('fee', 0))
                            if abs(trade['pnl']) > 0:
                                fee_ratio = fee / abs(trade['pnl']) * 100
                                if fee_ratio > 50:
                                    errors.append(f"手續費佔盈虧{fee_ratio:.1f}%，過度交易")
                                    risk_score -= 15
                                elif fee_ratio > 30:
                                    errors.append(f"手續費佔盈虧{fee_ratio:.1f}%，偏高")
                                    risk_score -= 10
                                elif fee_ratio < 10:
                                    risk_score = min(100, risk_score + 5)
                                    errors.append(f"✅ 手續費控制良好（{fee_ratio:.1f}%）")
                            
                            # 4. 紀律遵守評分（改進版：移除重複扣分，增加正面激勵）
                            # 4. 紀律遵守評分（改進版：移除重複扣分，增加正面激勵）
                            
                            # 爆倉嚴懲
                            if trade['close_type'] == '爆倉':
                                errors.append("❌ 爆倉！嚴重違反風險管理原則")
                                discipline_score = 0
                                risk_score = min(risk_score, 20)
                                exit_score = min(exit_score, 20)
                            
                            # 自動止損/止盈加分（減少幅度）
                            elif trade['close_type'] in ['止損', '止盈', '自動平倉']:
                                discipline_score = min(100, discipline_score + 10)
                                errors.append("✅ 遵守交易計劃（自動平倉）")
                            
                            # 手動平倉評估（不重複扣分）
                            elif trade['close_type'] == '手動平倉':
                                if trade['pnl'] < 0:
                                    # 虧損手動平倉
                                    if holding_hours < 0.5:
                                        errors.append("虧損快速手動平倉，可能是情緒化交易")
                                        discipline_score -= 30
                                    elif holding_hours < 2:
                                        errors.append("虧損較快手動平倉")
                                        discipline_score -= 15
                                    else:
                                        # 長時間後手動止損，可能是主動風控
                                        discipline_score -= 5
                                else:
                                    # 獲利手動平倉
                                    if actual_return < min_profit_pct * leverage * 0.5:
                                        errors.append("獲利太少即手動平倉，缺乏耐心")
                                        discipline_score -= 15
                            
                            # 持倉時間合理性（只在極端情況扣分，移除加分）
                            if holding_hours < 0.1:  # < 6 分鐘
                                errors.append("持倉時間極短（<6分鐘），可能是衝動交易")
                                discipline_score -= 10
                            
                            # 確保分數不低於0
                            entry_score = max(0, entry_score)
                            exit_score = max(0, exit_score)
                            risk_score = max(0, risk_score)
                            discipline_score = max(0, discipline_score)
                            
                            # 計算總分
                            total_score = (entry_score + exit_score + risk_score + discipline_score) / 4
                            
                            # 生成自動註記
                            # 格式化時間
                            open_time_str = open_time.strftime('%Y-%m-%d %H:%M:%S') if pd.notna(trade.get('open_time')) else 'N/A'
                            close_time_str = close_time.strftime('%Y-%m-%d %H:%M:%S') if pd.notna(trade.get('close_time')) else 'N/A'
                            
                            auto_note = f"【交易概況】\n"
                            auto_note += f"• 交易對：{trade['symbol']}\n"
                            auto_note += f"• 方向：{trade['direction']}\n"
                            auto_note += f"• 進場時間：{open_time_str}\n"
                            auto_note += f"• 出場時間：{close_time_str}\n"
                            auto_note += f"• 進場價：{entry_price:.2f}\n"
                            auto_note += f"• 出場價：{exit_price:.2f}\n"
                            
                            # 顯示估算的止損位和盈虧比
                            if estimated_stop_loss:
                                auto_note += f"• 估算止損位：{estimated_stop_loss:.2f}"
                                if stop_loss_method:
                                    auto_note += f" (基於{stop_loss_method})\n"
                                else:
                                    auto_note += "\n"
                                
                                if risk_reward_ratio:
                                    auto_note += f"• 盈虧比：1:{risk_reward_ratio:.2f}"
                                    if risk_reward_ratio >= 2:
                                        auto_note += " ✅ 優秀\n"
                                    elif risk_reward_ratio >= 1:
                                        auto_note += " ⚠️ 一般\n"
                                    else:
                                        auto_note += " ❌ 不佳\n"
                            
                            auto_note += f"• 持倉時間：{holding_hours:.1f} 小時\n"
                            auto_note += f"• 盈虧：{trade['pnl']:.2f} USDT ({pnl_pct:+.2f}%)\n"
                            auto_note += f"• 槓桿：{leverage}x"
                            
                            # 添加多時區詳細分析
                            if market_analysis:
                                multi_tf = market_analysis.get('multi_timeframe', {})
                                
                                # 為每個時區生成詳細報告
                                for tf_interval in ['15m', '1h', '4h', '1d']:
                                    tf_data = multi_tf.get(tf_interval)
                                    if not tf_data:
                                        continue
                                    
                                    # 時區標題
                                    tf_name_map = {
                                        '15m': '15分鐘',
                                        '1h': '1小時',
                                        '4h': '4小時',
                                        '1d': '1天'
                                    }
                                    auto_note += f"\n\n{'='*40}"
                                    auto_note += f"\n【{tf_name_map[tf_interval]}時區分析】"
                                    auto_note += f"\n{'='*40}"
                                    
                                    # 市場數據
                                    auto_note += f"\n\n▸ 市場數據"
                                    auto_note += f"\n• 價格：{tf_data.get('price', 0):.2f}"
                                    auto_note += f"\n• 開盤：{tf_data.get('open', 0):.2f}"
                                    auto_note += f"\n• 最高：{tf_data.get('high', 0):.2f}"
                                    auto_note += f"\n• 最低：{tf_data.get('low', 0):.2f}"
                                    
                                    # 技術指標
                                    auto_note += f"\n\n▸ 技術指標"
                                    
                                    # EMA
                                    ema_7 = tf_data.get('ema_7', 0)
                                    ema_20 = tf_data.get('ema_20', 0)
                                    ema_50 = tf_data.get('ema_50', 0)
                                    if ema_7 > 0:
                                        auto_note += f"\n• EMA7: {ema_7:.2f}"
                                    if ema_20 > 0:
                                        auto_note += f"\n• EMA20: {ema_20:.2f}"
                                    if ema_50 > 0:
                                        auto_note += f"\n• EMA50: {ema_50:.2f}"
                                    
                                    # 均線排列
                                    ma_alignment = tf_data.get('ma_alignment', 'unknown')
                                    if ma_alignment != 'unknown':
                                        auto_note += f"\n• 均線排列: {ma_alignment}"
                                    
                                    # RSI
                                    rsi = tf_data.get('rsi', 0)
                                    rsi_state = tf_data.get('rsi_state', 'unknown')
                                    if rsi > 0:
                                        auto_note += f"\n• RSI: {rsi:.1f} ({rsi_state})"
                                    
                                    # MACD
                                    macd = tf_data.get('macd', 0)
                                    macd_signal = tf_data.get('macd_signal', 0)
                                    macd_state = tf_data.get('macd_state', 'unknown')
                                    if macd != 0:
                                        auto_note += f"\n• MACD: {macd:.2f} / Signal: {macd_signal:.2f} ({macd_state})"
                                    
                                    # ATR
                                    atr = tf_data.get('atr', 0)
                                    atr_pct = tf_data.get('atr_pct', 0)
                                    volatility = tf_data.get('volatility', 'unknown')
                                    if atr > 0:
                                        auto_note += f"\n• ATR: {atr:.2f} ({atr_pct:.2f}%, {volatility})"
                                    
                                    # 布林帶
                                    bb_position = tf_data.get('bb_position', 'unknown')
                                    if bb_position != 'unknown':
                                        auto_note += f"\n• 布林帶位置: {bb_position}"
                                    
                                    # 成交量
                                    volume = tf_data.get('volume', 0)
                                    volume_ratio = tf_data.get('volume_ratio', 0)
                                    volume_state = tf_data.get('volume_state', 'unknown')
                                    if volume > 0:
                                        auto_note += f"\n• 成交量: {volume:.2f} (比率: {volume_ratio:.2f}x, {volume_state})"
                                    
                                    # 市場分析
                                    auto_note += f"\n\n▸ 市場分析"
                                    
                                    # 趨勢
                                    trend = tf_data.get('trend', 'unknown')
                                    trend_strength = tf_data.get('trend_strength', 50)
                                    auto_note += f"\n• 趨勢：{trend}（強度：{trend_strength:.1f}/100）"
                                    
                                    # 支撐阻力
                                    sr = tf_data.get('support_resistance', {})
                                    support = sr.get('support')
                                    resistance = sr.get('resistance')
                                    dist_support = sr.get('distance_to_support')
                                    dist_resistance = sr.get('distance_to_resistance')
                                    
                                    if support:
                                        auto_note += f"\n• 支撐位：{support:.2f}"
                                        if dist_support:
                                            auto_note += f" (距離：{dist_support:.2f}%)"
                                    
                                    if resistance:
                                        auto_note += f"\n• 阻力位：{resistance:.2f}"
                                        if dist_resistance:
                                            auto_note += f" (距離：{dist_resistance:.2f}%)"
                                
                                # 多時區趨勢對比總結
                                if multi_tf and len(multi_tf) > 1:
                                    auto_note += f"\n\n{'='*40}"
                                    auto_note += "\n【多時區趨勢對比】"
                                    auto_note += f"\n{'='*40}\n"
                                    
                                    for tf_interval in ['15m', '1h', '4h', '1d']:
                                        tf_data = multi_tf.get(tf_interval)
                                        if tf_data:
                                            tf_trend = tf_data.get('trend', 'unknown')
                                            tf_rsi = tf_data.get('rsi', 0)
                                            tf_macd_state = tf_data.get('macd_state', 'unknown')
                                            
                                            auto_note += f"\n• {tf_interval}: {tf_trend}"
                                            if tf_rsi > 0:
                                                auto_note += f", RSI={tf_rsi:.1f}"
                                            if tf_macd_state != 'unknown':
                                                auto_note += f", MACD={tf_macd_state}"
                            
                            # 添加問題列表
                            if errors:
                                auto_note += "\n\n【發現問題】"
                                for err_idx, error in enumerate(errors, 1):
                                    auto_note += f"\n{err_idx}. {error}"
                            else:
                                auto_note += "\n\n【評估結果】執行良好，未發現明顯問題。"
                            
                            # 轉換 market_analysis 為可序列化的格式
                            serializable_market_analysis = None
                            if market_analysis:
                                serializable_market_analysis = make_json_serializable(market_analysis)
                            
                            score_record = {
                                'trade_id': trade['trade_id'],
                                'order_no': trade['order_no'],
                                'date': trade['close_time'].strftime('%Y-%m-%d'),
                                'symbol': trade['symbol'],
                                'direction': trade['direction'],
                                'pnl': float(trade['pnl']),
                                'open_time': str(trade['open_time']) if pd.notna(trade.get('open_time')) else None,
                                'close_time': str(trade['close_time']) if pd.notna(trade.get('close_time')) else None,
                                'entry_price': float(trade.get('entry_price', 0)),
                                'exit_price': float(trade.get('exit_price', 0)),
                                'quantity': float(trade.get('quantity', 0)),  # 添加交易數量
                                'leverage': float(trade.get('leverage', 1)),  # 添加槓桿
                                'fee': float(trade.get('fee', 0)),  # 添加手續費
                                'close_type': str(trade.get('close_type', '')),  # 添加平倉類型
                                'entry_score': entry_score,
                                'exit_score': exit_score,
                                'risk_score': risk_score,
                                'discipline_score': discipline_score,
                                'total_score': total_score,
                                'note': auto_note,
                                'tags': ['auto_scored'] + errors,
                                'scored_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                'scoring_mode': 'auto',
                                'market_analysis': serializable_market_analysis  # 保存市場分析結果
                            }
                            
                            # 檢查是否已存在該交易的評分（避免重複）
                            trade_id = trade['trade_id']
                            existing_index = None
                            for idx_score, existing_score in enumerate(existing_scores):
                                if existing_score.get('trade_id') == trade_id:
                                    existing_index = idx_score
                                    break
                            
                            if existing_index is not None:
                                # 更新現有評分
                                existing_scores[existing_index] = score_record
                            else:
                                # 添加新評分
                                existing_scores.append(score_record)
                            
                            # 更新進度條（確保值在 0-1 之間）
                            progress_value = min(1.0, (i + 1) / len(selected_indices))
                            progress_bar.progress(progress_value)
                        
                        # 清除進度顯示
                        progress_bar.empty()
                        status_text.empty()
                        
                        # 安全保存（先保存到臨時文件）
                        try:
                            temp_file = quality_file.parent / f"{quality_file.name}.tmp"
                            with open(temp_file, 'w', encoding='utf-8') as f:
                                json.dump(existing_scores, f, indent=2, ensure_ascii=False)
                            
                            # 驗證 JSON 是否有效
                            with open(temp_file, 'r', encoding='utf-8') as f:
                                json.load(f)
                            
                            # 替換原文件
                            temp_file.replace(quality_file)
                            
                            st.success(f"✅ 已自動評分 {len(selected_indices)} 筆交易！")
                            if market_analyzer:
                                st.info("📊 已整合市場數據分析")
                            st.balloons()
                        except Exception as e:
                            st.error(f"❌ 保存失敗：{e}")
                            if temp_file.exists():
                                temp_file.unlink()
                
                else:  # 手動評分
                    # 評分表單
                    st.subheader("⭐ 執行質量評分")
                    
                    with st.form("quality_scoring_form"):
                        st.write("**評分標準（0-100 分）**")
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            entry_score = st.slider(
                                "進場質量",
                                0, 100, 70,
                                help="進場時機、價格、信號確認等"
                            )
                            
                            exit_score = st.slider(
                                "出場質量",
                                0, 100, 70,
                                help="出場時機、是否達到目標、止損執行等"
                            )
                        
                        with col2:
                            risk_score = st.slider(
                                "風險管理",
                                0, 100, 70,
                                help="倉位大小、止損設置、槓桿使用等"
                            )
                            
                            discipline_score = st.slider(
                                "紀律遵守",
                                0, 100, 70,
                                help="是否遵守交易計劃、情緒控制等"
                            )
                        
                        # 註記
                        note = st.text_area(
                            "交易註記 ⭐ 建議填寫",
                            placeholder="記錄這筆交易的觀察、學習和改進點...\n例如：\n- 進場原因和依據\n- 市場環境分析\n- 執行過程中的問題\n- 學到的經驗教訓\n- 下次可以改進的地方",
                            height=150,
                            help="詳細的註記有助於日後覆盤和改進"
                        )
                        
                        if not note or len(note.strip()) < 10:
                            st.warning("💡 提示：建議填寫至少 10 個字的註記，這對覆盤很有幫助！")
                        
                        # 標籤
                        tags = st.text_input(
                            "標籤（用逗號分隔）",
                            placeholder="例如：good_entry, early_exit, needs_improvement"
                        )
                        
                        submitted = st.form_submit_button("💾 保存評分", type="primary")
                        
                        if submitted:
                            # 計算總分
                            total_score = (entry_score + exit_score + risk_score + discipline_score) / 4
                            
                            # 保存評分
                            quality_file = PathClass("data/review_history/quality_scores.json")
                            quality_file.parent.mkdir(parents=True, exist_ok=True)
                            
                            # 載入現有評分
                            existing_scores = []
                            if quality_file.exists():
                                try:
                                    with open(quality_file, 'r', encoding='utf-8') as f:
                                        scores_data = json.load(f)
                                    
                                    # 轉換舊格式（字典）為新格式（列表）
                                    if isinstance(scores_data, dict):
                                        existing_scores = list(scores_data.values())
                                    else:
                                        existing_scores = scores_data
                                except:
                                    existing_scores = []
                            
                            # 為每個選中的交易添加評分
                            for idx in selected_indices:
                                trade = recent_trades.iloc[idx]
                                
                                score_record = {
                                    'trade_id': trade['trade_id'],
                                    'order_no': trade['order_no'],
                                    'date': trade['close_time'].strftime('%Y-%m-%d'),
                                    'symbol': trade['symbol'],
                                    'direction': trade['direction'],
                                    'pnl': float(trade['pnl']),
                                    'open_time': str(trade['open_time']) if pd.notna(trade.get('open_time')) else None,
                                    'close_time': str(trade['close_time']) if pd.notna(trade.get('close_time')) else None,
                                    'entry_price': float(trade.get('entry_price', 0)),
                                    'exit_price': float(trade.get('exit_price', 0)),
                                    'entry_score': entry_score,
                                    'exit_score': exit_score,
                                    'risk_score': risk_score,
                                    'discipline_score': discipline_score,
                                    'total_score': total_score,
                                    'note': note,
                                    'tags': [t.strip() for t in tags.split(',') if t.strip()],
                                    'scored_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                    'scoring_mode': 'manual'
                                }
                                
                                # 檢查是否已存在該交易的評分（避免重複）
                                trade_id = trade['trade_id']
                                existing_index = None
                                for idx_score, existing_score in enumerate(existing_scores):
                                    if existing_score.get('trade_id') == trade_id:
                                        existing_index = idx_score
                                        break
                                
                                if existing_index is not None:
                                    # 更新現有評分
                                    existing_scores[existing_index] = score_record
                                else:
                                    # 添加新評分
                                    existing_scores.append(score_record)
                            
                            # 安全保存（先保存到臨時文件）
                            try:
                                temp_file = quality_file.parent / f"{quality_file.name}.tmp"
                                with open(temp_file, 'w', encoding='utf-8') as f:
                                    json.dump(existing_scores, f, indent=2, ensure_ascii=False)
                                
                                # 驗證 JSON 是否有效
                                with open(temp_file, 'r', encoding='utf-8') as f:
                                    json.load(f)
                                
                                # 替換原文件
                                temp_file.replace(quality_file)
                                
                                st.success(f"✅ 已保存 {len(selected_indices)} 筆交易的評分！")
                                st.balloons()
                            except Exception as e:
                                st.error(f"❌ 保存失敗：{e}")
                                if temp_file.exists():
                                    temp_file.unlink()
            
            # 顯示已有的評分
            st.subheader("📊 已評分的交易")
            
            quality_file = PathClass("data/review_history/quality_scores.json")
            
            if quality_file.exists():
                try:
                    with open(quality_file, 'r', encoding='utf-8') as f:
                        scores_data = json.load(f)
                    
                    # 處理不同的數據格式
                    if isinstance(scores_data, dict):
                        # 舊格式：字典 {trade_id: {...}}
                        scores = list(scores_data.values())
                    else:
                        # 新格式：列表 [{...}, {...}]
                        scores = scores_data
                    
                    if scores:
                        scores_df = pd.DataFrame(scores)
                        
                        # 欄位名稱映射（兼容舊格式）
                        column_mapping = {
                            'entry_quality': 'entry_score',
                            'exit_quality': 'exit_score',
                            'risk_management': 'risk_score',
                            'overall_score': 'total_score'
                        }
                        
                        # 重命名欄位
                        for old_name, new_name in column_mapping.items():
                            if old_name in scores_df.columns and new_name not in scores_df.columns:
                                scores_df[new_name] = scores_df[old_name]
                        
                        # 如果缺少 discipline_score，設為與 risk_score 相同
                        if 'discipline_score' not in scores_df.columns:
                            if 'risk_score' in scores_df.columns:
                                scores_df['discipline_score'] = scores_df['risk_score']
                            else:
                                scores_df['discipline_score'] = 100.0
                        
                        # 如果缺少 total_score，計算總分
                        if 'total_score' not in scores_df.columns:
                            scores_df['total_score'] = (
                                scores_df.get('entry_score', 100) + 
                                scores_df.get('exit_score', 100) + 
                                scores_df.get('risk_score', 100) + 
                                scores_df.get('discipline_score', 100)
                            ) / 4
                        
                        # 如果缺少 date，從 scored_at 或使用當前日期
                        if 'date' not in scores_df.columns:
                            if 'scored_at' in scores_df.columns:
                                scores_df['date'] = pd.to_datetime(scores_df['scored_at']).dt.strftime('%Y-%m-%d')
                            else:
                                scores_df['date'] = datetime.now().strftime('%Y-%m-%d')
                        
                        # 如果缺少其他必要欄位，填充預設值
                        if 'symbol' not in scores_df.columns:
                            scores_df['symbol'] = 'N/A'
                        if 'direction' not in scores_df.columns:
                            scores_df['direction'] = 'N/A'
                        if 'pnl' not in scores_df.columns:
                            scores_df['pnl'] = 0.0
                        if 'note' not in scores_df.columns:
                            scores_df['note'] = ''
                        
                        # 統計
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            st.metric("已評分交易", f"{len(scores)} 筆")
                        
                        with col2:
                            avg_total = scores_df['total_score'].mean()
                            st.metric("平均總分", f"{avg_total:.1f}")
                        
                        with col3:
                            avg_entry = scores_df['entry_score'].mean()
                            st.metric("平均進場分", f"{avg_entry:.1f}")
                        
                        with col4:
                            avg_exit = scores_df['exit_score'].mean()
                            st.metric("平均出場分", f"{avg_exit:.1f}")
                        
                        # 評分趨勢
                        st.subheader("📈 評分趨勢")
                        
                        # 按日期排序
                        scores_df_sorted = scores_df.sort_values('date')
                        
                        fig = px.line(scores_df_sorted, x='date', y='total_score',
                                     title='執行質量評分趨勢',
                                     labels={'date': '日期', 'total_score': '總分'})
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # ========== 新增：實際收益率分析 ==========
                        st.subheader("💰 實際收益率分析")
                        
                        # 計算實際收益率
                        if 'entry_price' in scores_df.columns and 'exit_price' in scores_df.columns and 'leverage' in scores_df.columns:
                            def calculate_actual_return(row):
                                try:
                                    entry_price = float(row.get('entry_price', 0))
                                    exit_price = float(row.get('exit_price', 0))
                                    leverage = float(row.get('leverage', 1))
                                    direction = row.get('direction', 'Long')
                                    
                                    if entry_price > 0 and exit_price > 0:
                                        if direction == 'Long':
                                            pnl_pct = ((exit_price - entry_price) / entry_price) * 100
                                        else:
                                            pnl_pct = ((entry_price - exit_price) / entry_price) * 100
                                        return pnl_pct * leverage
                                    return 0
                                except:
                                    return 0
                            
                            scores_df['actual_return'] = scores_df.apply(calculate_actual_return, axis=1)
                            
                            # 分組統計
                            def categorize_return(ret):
                                if ret >= 50:
                                    return '大賺 (≥50%)'
                                elif ret >= 20:
                                    return '獲利 (20-50%)'
                                elif ret >= 5:
                                    return '小賺 (5-20%)'
                                elif ret >= -5:
                                    return '持平 (±5%)'
                                elif ret >= -20:
                                    return '小虧 (-5~-20%)'
                                elif ret >= -50:
                                    return '虧損 (-20~-50%)'
                                else:
                                    return '大虧 (<-50%)'
                            
                            scores_df['return_category'] = scores_df['actual_return'].apply(categorize_return)
                            
                            # 統計各區間
                            return_stats = scores_df.groupby('return_category').agg({
                                'actual_return': ['count', 'mean'],
                                'pnl': 'sum'
                            }).round(2)
                            
                            # 計算勝率
                            winning_trades = scores_df[scores_df['actual_return'] > 0]
                            losing_trades = scores_df[scores_df['actual_return'] < 0]
                            win_rate = len(winning_trades) / len(scores_df) * 100 if len(scores_df) > 0 else 0
                            
                            # 顯示統計
                            ret_col1, ret_col2, ret_col3, ret_col4 = st.columns(4)
                            
                            with ret_col1:
                                avg_return = scores_df['actual_return'].mean()
                                st.metric("平均實際收益率", f"{avg_return:+.2f}%")
                            
                            with ret_col2:
                                st.metric("勝率", f"{win_rate:.1f}%")
                            
                            with ret_col3:
                                if len(winning_trades) > 0:
                                    avg_win = winning_trades['actual_return'].mean()
                                    st.metric("平均獲利", f"+{avg_win:.2f}%")
                                else:
                                    st.metric("平均獲利", "N/A")
                            
                            with ret_col4:
                                if len(losing_trades) > 0:
                                    avg_loss = losing_trades['actual_return'].mean()
                                    st.metric("平均虧損", f"{avg_loss:.2f}%")
                                else:
                                    st.metric("平均虧損", "N/A")
                            
                            # 顯示分組統計表
                            st.write("**實際收益率區間分析**")
                            
                            # 重新整理數據以便顯示
                            category_order = ['大賺 (≥50%)', '獲利 (20-50%)', '小賺 (5-20%)', '持平 (±5%)', 
                                             '小虧 (-5~-20%)', '虧損 (-20~-50%)', '大虧 (<-50%)']
                            
                            display_data = []
                            for category in category_order:
                                category_data = scores_df[scores_df['return_category'] == category]
                                if len(category_data) > 0:
                                    count = len(category_data)
                                    avg_ret = category_data['actual_return'].mean()
                                    total_pnl = category_data['pnl'].sum()
                                    percentage = (count / len(scores_df)) * 100
                                    
                                    display_data.append({
                                        '區間': category,
                                        '交易數': count,
                                        '佔比': f"{percentage:.1f}%",
                                        '平均收益率': f"{avg_ret:+.2f}%",
                                        '總盈虧': f"{total_pnl:+.2f} USDT"
                                    })
                            
                            if display_data:
                                st.dataframe(pd.DataFrame(display_data), use_container_width=True, hide_index=True)
                        else:
                            st.info("💡 需要重新評分才能看到實際收益率分析（需要 entry_price、exit_price、leverage 字段）")
                        
                        # ========== 新增：持倉時間分析 ==========
                        st.subheader("⏱️ 持倉時間分析")
                        
                        # 計算持倉時間
                        if 'open_time' in scores_df.columns and 'close_time' in scores_df.columns:
                            def calculate_holding_hours(row):
                                try:
                                    open_time = pd.to_datetime(row.get('open_time'))
                                    close_time = pd.to_datetime(row.get('close_time'))
                                    if pd.notna(open_time) and pd.notna(close_time):
                                        return (close_time - open_time).total_seconds() / 3600
                                    return 0
                                except:
                                    return 0
                            
                            scores_df['holding_hours'] = scores_df.apply(calculate_holding_hours, axis=1)
                            
                            # 分組統計
                            def categorize_holding_time(hours):
                                if hours < 0.1:
                                    return '極短 (<6分鐘)'
                                elif hours < 1:
                                    return '超短線 (<1小時)'
                                elif hours < 4:
                                    return '日內 (1-4小時)'
                                elif hours < 24:
                                    return '短線 (4-24小時)'
                                elif hours < 72:
                                    return '波段 (1-3天)'
                                else:
                                    return '長線 (>3天)'
                            
                            scores_df['holding_category'] = scores_df['holding_hours'].apply(categorize_holding_time)
                            
                            # 統計各區間
                            holding_stats = []
                            category_order = ['極短 (<6分鐘)', '超短線 (<1小時)', '日內 (1-4小時)', 
                                             '短線 (4-24小時)', '波段 (1-3天)', '長線 (>3天)']
                            
                            for category in category_order:
                                category_data = scores_df[scores_df['holding_category'] == category]
                                if len(category_data) > 0:
                                    count = len(category_data)
                                    winning = len(category_data[category_data['pnl'] > 0])
                                    win_rate = (winning / count) * 100 if count > 0 else 0
                                    avg_pnl = category_data['pnl'].mean()
                                    total_pnl = category_data['pnl'].sum()
                                    percentage = (count / len(scores_df)) * 100
                                    
                                    # 計算平均實際收益率（如果有）
                                    if 'actual_return' in category_data.columns:
                                        avg_return = category_data['actual_return'].mean()
                                        return_str = f"{avg_return:+.2f}%"
                                    else:
                                        return_str = "N/A"
                                    
                                    holding_stats.append({
                                        '持倉時間': category,
                                        '交易數': count,
                                        '佔比': f"{percentage:.1f}%",
                                        '勝率': f"{win_rate:.1f}%",
                                        '平均盈虧': f"{avg_pnl:+.2f} USDT",
                                        '平均收益率': return_str,
                                        '總盈虧': f"{total_pnl:+.2f} USDT"
                                    })
                            
                            if holding_stats:
                                st.dataframe(pd.DataFrame(holding_stats), use_container_width=True, hide_index=True)
                                
                                # 視覺化
                                st.write("**持倉時間分布**")
                                holding_dist = scores_df['holding_category'].value_counts().reindex(category_order, fill_value=0)
                                fig_holding = px.bar(
                                    x=holding_dist.index,
                                    y=holding_dist.values,
                                    title='持倉時間分布',
                                    labels={'x': '持倉時間', 'y': '交易數'}
                                )
                                st.plotly_chart(fig_holding, use_container_width=True)
                        else:
                            st.info("💡 需要重新評分才能看到持倉時間分析（需要 open_time、close_time 字段）")
                        
                        # ========== 新增：智能分析建議 ==========
                        st.subheader("🤖 智能分析建議")
                        
                        # 確保有足夠的數據進行分析
                        if len(scores_df) >= 10 and 'holding_hours' in scores_df.columns and 'actual_return' in scores_df.columns:
                            # 1. 識別交易者類型
                            st.write("**📊 交易者類型分析**")
                            
                            # 計算主要持倉時間區間
                            holding_dist = scores_df['holding_category'].value_counts()
                            main_category = holding_dist.index[0] if len(holding_dist) > 0 else None
                            main_percentage = (holding_dist.iloc[0] / len(scores_df)) * 100 if len(holding_dist) > 0 else 0
                            
                            # 計算平均持倉時間
                            avg_holding = scores_df['holding_hours'].mean()
                            
                            # 識別交易者類型
                            trader_type = ""
                            trader_desc = ""
                            if avg_holding < 0.5:
                                trader_type = "🔥 超短線交易者（剝頭皮）"
                                trader_desc = "主要進行極短時間的快速交易，追求小幅價格波動的利潤"
                            elif avg_holding < 2:
                                trader_type = "⚡ 短線交易者"
                                trader_desc = "主要進行小時級別的交易，捕捉日內價格波動"
                            elif avg_holding < 12:
                                trader_type = "📈 日內交易者"
                                trader_desc = "主要在一天內完成交易，避免隔夜風險"
                            elif avg_holding < 48:
                                trader_type = "🌊 波段交易者"
                                trader_desc = "持倉數天，捕捉較大的價格波動"
                            else:
                                trader_type = "🎯 趨勢交易者"
                                trader_desc = "長期持倉，跟隨主要趨勢"
                            
                            st.info(f"**{trader_type}**\n\n{trader_desc}\n\n平均持倉時間：{avg_holding:.1f} 小時")
                            
                            # 2. 分析表現
                            st.write("**📈 表現分析**")
                            
                            analysis_cols = st.columns(3)
                            
                            with analysis_cols[0]:
                                win_rate = len(scores_df[scores_df['pnl'] > 0]) / len(scores_df) * 100
                                if win_rate >= 60:
                                    st.success(f"✅ 勝率優秀：{win_rate:.1f}%")
                                elif win_rate >= 50:
                                    st.info(f"⚠️ 勝率一般：{win_rate:.1f}%")
                                else:
                                    st.error(f"❌ 勝率偏低：{win_rate:.1f}%")
                            
                            with analysis_cols[1]:
                                avg_return = scores_df['actual_return'].mean()
                                if avg_return > 10:
                                    st.success(f"✅ 平均收益優秀：{avg_return:+.2f}%")
                                elif avg_return > 0:
                                    st.info(f"⚠️ 平均收益一般：{avg_return:+.2f}%")
                                else:
                                    st.error(f"❌ 平均收益為負：{avg_return:+.2f}%")
                            
                            with analysis_cols[2]:
                                avg_leverage = scores_df['leverage'].mean() if 'leverage' in scores_df.columns else 0
                                if avg_leverage > 50:
                                    st.error(f"❌ 槓桿過高：{avg_leverage:.0f}x")
                                elif avg_leverage > 20:
                                    st.warning(f"⚠️ 槓桿偏高：{avg_leverage:.0f}x")
                                else:
                                    st.success(f"✅ 槓桿合理：{avg_leverage:.0f}x")
                            
                            # 3. 找出最佳和最差持倉時間
                            st.write("**🎯 最佳持倉時間**")
                            
                            best_category = None
                            best_win_rate = 0
                            worst_category = None
                            worst_win_rate = 100
                            
                            for category in category_order:
                                category_data = scores_df[scores_df['holding_category'] == category]
                                if len(category_data) >= 3:  # 至少3筆交易才有參考價值
                                    winning = len(category_data[category_data['pnl'] > 0])
                                    category_win_rate = (winning / len(category_data)) * 100
                                    
                                    if category_win_rate > best_win_rate:
                                        best_win_rate = category_win_rate
                                        best_category = category
                                    
                                    if category_win_rate < worst_win_rate:
                                        worst_win_rate = category_win_rate
                                        worst_category = category
                            
                            if best_category:
                                best_data = scores_df[scores_df['holding_category'] == best_category]
                                best_avg_pnl = best_data['pnl'].mean()
                                best_count = len(best_data)
                                st.success(f"✅ **{best_category}** 表現最佳\n\n勝率：{best_win_rate:.1f}% | 平均盈虧：{best_avg_pnl:+.2f} USDT | 交易數：{best_count} 筆")
                            
                            if worst_category and worst_category != best_category:
                                worst_data = scores_df[scores_df['holding_category'] == worst_category]
                                worst_avg_pnl = worst_data['pnl'].mean()
                                worst_count = len(worst_data)
                                st.error(f"❌ **{worst_category}** 表現最差\n\n勝率：{worst_win_rate:.1f}% | 平均盈虧：{worst_avg_pnl:+.2f} USDT | 交易數：{worst_count} 筆")
                            
                            # 4. 智能建議
                            st.write("**💡 改進建議**")
                            
                            suggestions = []
                            
                            # 建議 1：持倉時間優化
                            if worst_category and best_category:
                                if '極短' in worst_category or '超短線' in worst_category:
                                    suggestions.append({
                                        'type': 'warning',
                                        'title': '減少極短線交易',
                                        'content': f'你的{worst_category}交易勝率只有 {worst_win_rate:.1f}%，建議減少這類交易。\n\n**行動方案**：\n- 設置最小持倉時間（如 30 分鐘）\n- 提高進場標準，避免衝動交易\n- 專注於{best_category}交易（勝率 {best_win_rate:.1f}%）'
                                    })
                                
                                if best_win_rate > 65 and main_category != best_category:
                                    suggestions.append({
                                        'type': 'success',
                                        'title': f'增加{best_category}交易',
                                        'content': f'你的{best_category}交易表現優秀（勝率 {best_win_rate:.1f}%），但佔比不高。\n\n**行動方案**：\n- 增加{best_category}的交易頻率\n- 總結這類交易的成功模式\n- 制定專門的交易計劃'
                                    })
                            
                            # 建議 2：槓桿優化
                            if avg_leverage > 50:
                                high_leverage_trades = scores_df[scores_df['leverage'] > 50]
                                high_leverage_loss = len(high_leverage_trades[high_leverage_trades['pnl'] < 0])
                                high_leverage_loss_rate = (high_leverage_loss / len(high_leverage_trades)) * 100 if len(high_leverage_trades) > 0 else 0
                                
                                suggestions.append({
                                    'type': 'error',
                                    'title': '降低槓桿使用',
                                    'content': f'你的平均槓桿為 {avg_leverage:.0f}x，屬於高風險。高槓桿交易（>50x）的虧損率為 {high_leverage_loss_rate:.1f}%。\n\n**行動方案**：\n- 將最大槓桿限制在 20x 以內\n- 根據波動率調整槓桿（高波動用低槓桿）\n- 優先保護本金，而非追求高收益'
                                })
                            elif avg_leverage > 20:
                                suggestions.append({
                                    'type': 'warning',
                                    'title': '適度降低槓桿',
                                    'content': f'你的平均槓桿為 {avg_leverage:.0f}x，建議降低至 10-20x 之間。\n\n**行動方案**：\n- 評估每筆交易的風險承受度\n- 在高波動市場降低槓桿\n- 設置更嚴格的止損'
                                })
                            
                            # 建議 3：勝率優化
                            if win_rate < 50:
                                suggestions.append({
                                    'type': 'error',
                                    'title': '提高勝率',
                                    'content': f'你的勝率為 {win_rate:.1f}%，低於 50%。\n\n**行動方案**：\n- 提高進場標準（等待更明確的信號）\n- 加強市場分析（多時區確認）\n- 避免逆勢交易\n- 減少交易頻率，提高質量'
                                })
                            elif win_rate < 55:
                                suggestions.append({
                                    'type': 'warning',
                                    'title': '繼續提升勝率',
                                    'content': f'你的勝率為 {win_rate:.1f}%，還有提升空間。\n\n**行動方案**：\n- 總結獲利交易的共同特徵\n- 避免虧損交易的錯誤模式\n- 使用評分系統篩選高質量交易'
                                })
                            
                            # 建議 4：收益優化
                            if avg_return < 0:
                                total_pnl = scores_df['pnl'].sum()
                                suggestions.append({
                                    'type': 'error',
                                    'title': '扭轉虧損局面',
                                    'content': f'你的平均收益率為負（{avg_return:+.2f}%），總盈虧 {total_pnl:+.2f} USDT。\n\n**緊急行動**：\n- 暫停交易，重新評估策略\n- 降低槓桿至 5x 以內\n- 只做最有把握的交易\n- 嚴格執行止損\n- 考慮模擬交易練習'
                                })
                            elif avg_return < 5:
                                suggestions.append({
                                    'type': 'warning',
                                    'title': '提高收益率',
                                    'content': f'你的平均收益率較低（{avg_return:+.2f}%）。\n\n**行動方案**：\n- 讓利潤奔跑（避免過早止盈）\n- 提高盈虧比（目標 > 2:1）\n- 減少小賺即走的交易\n- 專注於高質量交易機會'
                                })
                            
                            # 建議 5：過度交易
                            very_short_trades = scores_df[scores_df['holding_hours'] < 0.1]
                            if len(very_short_trades) > len(scores_df) * 0.3:  # 超過30%是極短線
                                very_short_win_rate = len(very_short_trades[very_short_trades['pnl'] > 0]) / len(very_short_trades) * 100 if len(very_short_trades) > 0 else 0
                                suggestions.append({
                                    'type': 'warning',
                                    'title': '避免過度交易',
                                    'content': f'你有 {len(very_short_trades)} 筆極短線交易（<6分鐘），佔比 {len(very_short_trades)/len(scores_df)*100:.1f}%，勝率 {very_short_win_rate:.1f}%。\n\n**行動方案**：\n- 設置交易冷靜期（每筆交易間隔至少 30 分鐘）\n- 避免情緒化交易\n- 制定交易計劃並嚴格執行\n- 記錄每筆交易的理由'
                                })
                            
                            # 顯示建議
                            if suggestions:
                                for i, suggestion in enumerate(suggestions, 1):
                                    if suggestion['type'] == 'error':
                                        st.error(f"**{i}. {suggestion['title']}**\n\n{suggestion['content']}")
                                    elif suggestion['type'] == 'warning':
                                        st.warning(f"**{i}. {suggestion['title']}**\n\n{suggestion['content']}")
                                    else:
                                        st.success(f"**{i}. {suggestion['title']}**\n\n{suggestion['content']}")
                            else:
                                st.success("🎉 **表現優秀！**\n\n你的交易表現良好，繼續保持當前的交易策略和紀律。")
                            
                            # 5. 推薦交易風格
                            st.write("**🎯 推薦交易風格**")
                            
                            if best_category and best_win_rate > 60:
                                recommended_style = ""
                                if '日內' in best_category:
                                    recommended_style = "**日內交易**\n\n- 持倉時間：1-4 小時\n- 目標收益：5-15%\n- 建議槓桿：10-20x\n- 適合市場：趨勢明確的日內波動"
                                elif '短線' in best_category:
                                    recommended_style = "**短線波段**\n\n- 持倉時間：4-24 小時\n- 目標收益：10-30%\n- 建議槓桿：5-15x\n- 適合市場：中期趨勢和波段行情"
                                elif '超短線' in best_category:
                                    recommended_style = "**超短線交易**\n\n- 持倉時間：10分鐘-1小時\n- 目標收益：2-8%\n- 建議槓桿：15-30x\n- 適合市場：高波動的快速行情"
                                elif '波段' in best_category:
                                    recommended_style = "**波段交易**\n\n- 持倉時間：1-3 天\n- 目標收益：20-50%\n- 建議槓桿：3-10x\n- 適合市場：明確的中期趨勢"
                                
                                if recommended_style:
                                    st.info(f"根據你的表現，推薦以下交易風格：\n\n{recommended_style}")
                            
                        elif len(scores_df) < 10:
                            st.info("💡 需要至少 10 筆已評分的交易才能進行智能分析。請繼續交易並評分。")
                        else:
                            st.info("💡 需要重新評分才能看到智能分析建議（需要完整的交易數據）")
                        
                        # ========== 新增：量化風險分析 ==========
                        st.subheader("🔍 量化風險分析")
                        
                        if len(scores_df) >= 10:
                            try:
                                # 導入量化風險分析工具
                                import sys
                                from pathlib import Path as PathClass
                                
                                # 添加當前目錄到 Python 路徑
                                current_dir = PathClass(__file__).parent
                                if str(current_dir) not in sys.path:
                                    sys.path.insert(0, str(current_dir))
                                
                                from quantitative_risk_analysis import QuantitativeRiskOfficer
                                
                                # 創建風險官實例
                                risk_officer = QuantitativeRiskOfficer()
                                
                                # 顯示關鍵指標
                                st.write("**🎯 關鍵風險指標**")
                                
                                risk_col1, risk_col2, risk_col3, risk_col4 = st.columns(4)
                                
                                # 1. 最長連損
                                max_streak = risk_officer.calculate_max_losing_streak()
                                with risk_col1:
                                    streak_color = "🔴" if max_streak['max_streak'] > 10 else "🟡" if max_streak['max_streak'] > 5 else "🟢"
                                    st.metric(
                                        "最長連損",
                                        f"{max_streak['max_streak']} 次",
                                        delta=f"{max_streak['total_loss_in_streak']:.2f} USDT",
                                        delta_color="inverse"
                                    )
                                    st.caption(f"{streak_color} {'極高風險' if max_streak['max_streak'] > 10 else '需注意' if max_streak['max_streak'] > 5 else '正常'}")
                                
                                # 2. 破產風險
                                ror = risk_officer.calculate_risk_of_ruin()
                                with risk_col2:
                                    ror_color = "🔴" if ror['risk_of_ruin'] > 0.5 else "🟡" if ror['risk_of_ruin'] > 0.2 else "🟢"
                                    st.metric(
                                        "破產風險",
                                        f"{ror['risk_of_ruin']:.1%}",
                                        delta=f"期望值 {ror['expectancy']:.2f}",
                                        delta_color="normal" if ror['expectancy'] > 0 else "inverse"
                                    )
                                    st.caption(f"{ror_color} {'必然破產' if ror['risk_of_ruin'] > 0.9 else '極高風險' if ror['risk_of_ruin'] > 0.5 else '高風險' if ror['risk_of_ruin'] > 0.2 else '可控'}")
                                
                                # 3. 手續費壓力
                                fee_pressure = risk_officer.calculate_fee_pressure()
                                with risk_col3:
                                    fee_color = "🔴" if fee_pressure['fee_to_loss_ratio'] > 30 else "🟡" if fee_pressure['fee_to_loss_ratio'] > 10 else "🟢"
                                    st.metric(
                                        "手續費壓力",
                                        f"{fee_pressure['fee_to_loss_ratio']:.1f}%",
                                        delta=f"{fee_pressure['total_fee']:.2f} USDT",
                                        delta_color="inverse"
                                    )
                                    st.caption(f"{fee_color} 佔總虧損")
                                
                                # 4. 傾斜行為
                                tilt = risk_officer.detect_tilt_behavior()
                                with risk_col4:
                                    tilt_color = "🔴" if tilt['severity'] == 'high' else "🟡" if tilt['severity'] == 'medium' else "🟢"
                                    st.metric(
                                        "傾斜行為",
                                        f"{tilt['tilt_cases_count']} 次",
                                        delta=f"{tilt['tilt_cases_percentage']:.1f}%",
                                        delta_color="inverse" if tilt['has_tilt'] else "normal"
                                    )
                                    st.caption(f"{tilt_color} {tilt['severity']}")
                                
                                # 新增：冷靜期和 Kelly Criterion
                                st.write("")  # 空行
                                st.write("**🆕 進階風險指標**")
                                
                                risk_col5, risk_col6 = st.columns(2)
                                
                                # 5. 冷靜期檢測
                                cooling = risk_officer.check_cooling_period()
                                with risk_col5:
                                    if cooling['should_cool']:
                                        severity_color = "🔴" if cooling['severity'] == 'critical' else "🟠" if cooling['severity'] == 'high' else "🟡"
                                        st.metric(
                                            "冷靜期建議",
                                            f"需要休息",
                                            delta=f"{cooling['duration_minutes']} 分鐘",
                                            delta_color="inverse"
                                        )
                                        st.caption(f"{severity_color} {cooling['reason']}")
                                    else:
                                        st.metric(
                                            "冷靜期建議",
                                            "狀態正常",
                                            delta="無需休息",
                                            delta_color="normal"
                                        )
                                        st.caption("🟢 可以繼續交易")
                                
                                # 6. Kelly Criterion
                                kelly = risk_officer.calculate_ror_kelly()
                                with risk_col6:
                                    kelly_color = "🔴" if kelly['kelly_optimal_size'] <= 0 else "🟡" if kelly['kelly_optimal_size'] < 0.1 else "🟢"
                                    st.metric(
                                        "Kelly 最優倉位",
                                        f"{kelly['kelly_optimal_size']:.1%}",
                                        delta=f"建議 {kelly['recommended_size']:.1%}",
                                        delta_color="normal" if kelly['kelly_optimal_size'] > 0 else "inverse"
                                    )
                                    st.caption(f"{kelly_color} Half Kelly")
                                
                                # 詳細分析（可展開）
                                with st.expander("📊 查看詳細量化分析", expanded=False):
                                    # Tab 分頁
                                    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(["💀 破產風險", "💰 手續費分析", "🎰 傾斜檢測", "🧘 冷靜期", "📐 Kelly 分析", "😤 情緒失控", "🎯 能力評分"])
                                    
                                    with tab1:
                                        st.write("**破產風險詳細分析**")
                                        
                                        # 破產風險說明
                                        st.info(f"""
                                        **當前狀態**：
                                        - 勝率：{ror['win_rate']:.2%}
                                        - 平均獲利：{ror['avg_win']:.2f} USDT
                                        - 平均虧損：{ror['avg_loss']:.2f} USDT
                                        - 賠率：{ror['payoff_ratio']:.2f}:1
                                        - 期望值：{ror['expectancy']:.2f} USDT/筆
                                        
                                        **破產風險**：{ror['risk_of_ruin']:.2%}
                                        """)
                                        
                                        if ror['risk_of_ruin'] > 0.5:
                                            st.error("⚠️ 破產風險極高！建議立即暫停交易並優化策略。")
                                        elif ror['risk_of_ruin'] > 0.2:
                                            st.warning("⚠️ 破產風險偏高，需要改善勝率或賠率。")
                                        else:
                                            st.success("✅ 破產風險在可控範圍內。")
                                        
                                        # 恢復係數
                                        recovery = risk_officer.calculate_recovery_factor()
                                        st.write("**恢復係數**")
                                        st.metric(
                                            "需要獲利",
                                            f"{recovery['recovery_needed_pct']:.1f}%",
                                            delta=f"最大回撤 {recovery['max_drawdown_pct']:.2f}%"
                                        )
                                        
                                        if recovery['recovery_needed_pct'] > 100:
                                            st.error(f"⚠️ 需要獲利 {recovery['recovery_needed_pct']:.1f}% 才能回本，幾乎不可能！")
                                    
                                    with tab2:
                                        st.write("**手續費壓力測試**")
                                        
                                        # 短線交易分析
                                        short_trades = risk_officer.analyze_short_term_trades(5.0)
                                        
                                        if short_trades.get('count', 0) > 0:
                                            st.write("**短線交易（<5分鐘）分析**")
                                            
                                            short_col1, short_col2, short_col3 = st.columns(3)
                                            
                                            with short_col1:
                                                st.metric("短線交易數", f"{short_trades['count']} 筆")
                                                st.caption(f"{short_trades['percentage']:.1f}% 的交易")
                                            
                                            with short_col2:
                                                st.metric("短線勝率", f"{short_trades['win_rate']:.1%}")
                                                st.caption(f"期望值 {short_trades['expectancy']:.2f}")
                                            
                                            with short_col3:
                                                st.metric("短線盈虧", f"{short_trades['total_pnl']:.2f} USDT")
                                                st.caption(f"手續費 {short_trades['total_fee']:.2f}")
                                            
                                            # 模擬停止短線交易
                                            simulation = risk_officer.simulate_without_short_trades(5.0)
                                            
                                            if 'pnl_difference' in simulation:
                                                st.write("**💡 模擬：停止所有短線交易**")
                                                
                                                sim_col1, sim_col2, sim_col3 = st.columns(3)
                                                
                                                with sim_col1:
                                                    st.metric(
                                                        "淨值改善",
                                                        f"{simulation['pnl_difference']:+.2f} USDT",
                                                        delta=f"{simulation['pnl_improvement_pct']:+.1f}%"
                                                    )
                                                
                                                with sim_col2:
                                                    st.metric(
                                                        "節省手續費",
                                                        f"{simulation['fee_saved']:.2f} USDT"
                                                    )
                                                
                                                with sim_col3:
                                                    st.metric(
                                                        "勝率提升",
                                                        f"{simulation['new_win_rate']:.1%}",
                                                        delta=f"{(simulation['new_win_rate'] - simulation['original_win_rate']) * 100:+.1f}%"
                                                    )
                                                
                                                if simulation['pnl_improvement_pct'] > 10:
                                                    st.success(f"✅ 停止短線交易可改善淨值 {simulation['pnl_improvement_pct']:.1f}%！強烈建議執行。")
                                                elif simulation['pnl_improvement_pct'] > 0:
                                                    st.info(f"💡 停止短線交易可改善淨值 {simulation['pnl_improvement_pct']:.1f}%。")
                                        else:
                                            st.info("沒有短線交易（<5分鐘）。")
                                    
                                    with tab3:
                                        st.write("**傾斜行為檢測**")
                                        
                                        if tilt['has_tilt']:
                                            st.warning(f"⚠️ 檢測到 {tilt['tilt_cases_count']} 次傾斜行為（{tilt['tilt_cases_percentage']:.1f}%）")
                                            
                                            tilt_col1, tilt_col2 = st.columns(2)
                                            
                                            with tilt_col1:
                                                st.metric(
                                                    "虧損後槓桿變化",
                                                    f"{tilt['avg_leverage_change_after_loss']:+.2f}x",
                                                    delta="報復性加倉" if tilt['avg_leverage_change_after_loss'] > 5 else "正常"
                                                )
                                            
                                            with tilt_col2:
                                                st.metric(
                                                    "獲利後槓桿變化",
                                                    f"{tilt['avg_leverage_change_after_win']:+.2f}x"
                                                )
                                            
                                            # 顯示傾斜案例
                                            if tilt['tilt_cases']:
                                                st.write("**典型傾斜案例**")
                                                for i, case in enumerate(tilt['tilt_cases'][:3], 1):
                                                    with st.container():
                                                        st.write(f"**案例 {i}**")
                                                        st.write(f"- 虧損 {case['after_loss']:.2f} USDT 後")
                                                        st.write(f"- 槓桿增加 {case['leverage_increase_pct']:+.1f}%")
                                                        st.write(f"- 倉位增加 {case['quantity_increase_pct']:+.1f}%")
                                                        st.write(f"- 結果：{case['next_pnl']:+.2f} USDT")
                                                        st.divider()
                                            
                                            st.error("""
                                            **建議**：
                                            - 虧損後禁止增加槓桿
                                            - 設置「冷靜期」（虧損後 30 分鐘內不交易）
                                            - 限制連續虧損後的交易次數
                                            """)
                                        else:
                                            st.success("✅ 未檢測到明顯的傾斜行為。")
                                    
                                    with tab4:
                                        st.write("**冷靜期檢測**")
                                        
                                        if cooling['should_cool']:
                                            # 顯示警告
                                            if cooling['severity'] == 'critical':
                                                st.error(f"🔴 **緊急警告**：{cooling['reason']}")
                                            elif cooling['severity'] == 'high':
                                                st.warning(f"🟠 **高度警告**：{cooling['reason']}")
                                            else:
                                                st.warning(f"🟡 **注意**：{cooling['reason']}")
                                            
                                            # 顯示詳細信息
                                            cool_col1, cool_col2, cool_col3 = st.columns(3)
                                            
                                            with cool_col1:
                                                st.metric("建議休息時間", f"{cooling['duration_minutes']} 分鐘")
                                            
                                            with cool_col2:
                                                st.metric("連續虧損", f"{cooling['consecutive_losses']} 次")
                                            
                                            with cool_col3:
                                                if cooling['max_daily_loss_pct'] < 0:
                                                    st.metric("最大單日虧損", f"{abs(cooling['max_daily_loss_pct']):.2f}%")
                                                else:
                                                    st.metric("傾斜嚴重度", cooling['tilt_severity'])
                                            
                                            # 建議
                                            st.info(f"""
                                            **💡 建議行動**：
                                            - {cooling['recommendation']}
                                            - 檢視最近的虧損交易，找出問題所在
                                            - 考慮調整策略參數或暫停該策略
                                            - 避免情緒化交易，保持冷靜
                                            """)
                                        else:
                                            st.success("✅ 交易狀態正常，無需冷靜期")
                                            
                                            cool_col1, cool_col2 = st.columns(2)
                                            
                                            with cool_col1:
                                                st.metric("連續虧損", f"{cooling['consecutive_losses']} 次")
                                            
                                            with cool_col2:
                                                st.metric("傾斜嚴重度", cooling['tilt_severity'])
                                    
                                    with tab5:
                                        st.write("**Kelly Criterion 分析**")
                                        
                                        # Kelly 指標
                                        kelly_col1, kelly_col2, kelly_col3 = st.columns(3)
                                        
                                        with kelly_col1:
                                            st.metric(
                                                "Kelly 破產風險",
                                                f"{kelly['kelly_ror']:.2%}",
                                                delta="基於 Kelly 公式"
                                            )
                                        
                                        with kelly_col2:
                                            st.metric(
                                                "Kelly 最優倉位",
                                                f"{kelly['kelly_optimal_size']:.2%}",
                                                delta=f"期望值 {kelly['expectancy']:.2f}"
                                            )
                                        
                                        with kelly_col3:
                                            st.metric(
                                                "建議倉位",
                                                f"{kelly['recommended_size']:.2%}",
                                                delta="Half Kelly（更保守）"
                                            )
                                        
                                        # Kelly 公式說明
                                        st.write("**📐 Kelly 公式**")
                                        st.latex(r"f^* = \frac{bp - q}{b}")
                                        
                                        st.write("""
                                        其中：
                                        - f* = 最優倉位比例
                                        - b = 賠率（平均獲利/平均虧損）
                                        - p = 勝率
                                        - q = 敗率（1 - p）
                                        """)
                                        
                                        # 當前數據
                                        st.write("**📊 當前數據**")
                                        st.info(f"""
                                        - 勝率：{kelly['win_rate']:.2%}
                                        - 敗率：{kelly['loss_rate']:.2%}
                                        - 平均獲利：{kelly['avg_win']:.2f} USDT
                                        - 平均虧損：{kelly['avg_loss']:.2f} USDT
                                        - 賠率：{kelly['payoff_ratio']:.2f}:1
                                        - 期望值：{kelly['expectancy']:.2f} USDT/筆
                                        """)
                                        
                                        # 建議
                                        if kelly['kelly_optimal_size'] <= 0:
                                            st.error("""
                                            ⚠️ **警告**：Kelly 最優倉位 ≤ 0
                                            
                                            這表示當前策略的期望值為負，不建議交易！
                                            
                                            **建議**：
                                            - 立即暫停交易
                                            - 優化策略以提高勝率或賠率
                                            - 重新評估風險管理規則
                                            """)
                                        elif kelly['kelly_optimal_size'] < 0.1:
                                            st.warning(f"""
                                            💡 **注意**：Kelly 最優倉位很小（{kelly['kelly_optimal_size']:.2%}）
                                            
                                            **建議**：
                                            - 降低每筆交易的風險
                                            - 改善策略以提高期望值
                                            - 考慮使用更保守的倉位（Half Kelly: {kelly['recommended_size']:.2%}）
                                            """)
                                        else:
                                            st.success(f"""
                                            ✅ Kelly 最優倉位：{kelly['kelly_optimal_size']:.2%}
                                            
                                            **建議使用 Half Kelly**：{kelly['recommended_size']:.2%}
                                            
                                            Half Kelly 提供更好的風險控制，同時保持良好的增長潛力。
                                            """)
                                    
                                    with tab6:
                                        st.write("**情緒失控係數分析**")
                                        
                                        # 獲取情緒控制分析
                                        emotional = risk_officer.analyze_emotional_control()
                                        
                                        # 情緒控制評分
                                        emo_col1, emo_col2, emo_col3 = st.columns(3)
                                        
                                        with emo_col1:
                                            score_color = "🔴" if emotional['emotional_control_score'] < 40 else "🟡" if emotional['emotional_control_score'] < 70 else "🟢"
                                            st.metric(
                                                "情緒控制評分",
                                                f"{emotional['emotional_control_score']:.1f}/100",
                                                delta=f"{emotional['severity']}"
                                            )
                                            st.caption(f"{score_color} {emotional['severity']}")
                                        
                                        with emo_col2:
                                            st.metric(
                                                "虧損後頻率增加",
                                                f"{emotional['frequency_increase_after_loss']:+.1f}%",
                                                delta="下單更頻繁" if emotional['frequency_increase_after_loss'] > 20 else "正常"
                                            )
                                        
                                        with emo_col3:
                                            st.metric(
                                                "虧損後槓桿增加",
                                                f"{emotional['leverage_increase_after_loss']:+.1f}%",
                                                delta="報復性加倉" if emotional['leverage_increase_after_loss'] > 20 else "正常"
                                            )
                                        
                                        # 交易間隔分析
                                        st.write("**⏱️ 交易間隔分析**")
                                        
                                        interval_col1, interval_col2, interval_col3 = st.columns(3)
                                        
                                        with interval_col1:
                                            st.metric("正常交易間隔", f"{emotional['avg_time_between_trades_normal']:.1f} 分鐘")
                                        
                                        with interval_col2:
                                            st.metric(
                                                "虧損後交易間隔",
                                                f"{emotional['avg_time_between_trades_after_loss']:.1f} 分鐘",
                                                delta=f"{emotional['avg_time_between_trades_after_loss'] - emotional['avg_time_between_trades_normal']:.1f} 分鐘",
                                                delta_color="inverse" if emotional['avg_time_between_trades_after_loss'] < emotional['avg_time_between_trades_normal'] else "normal"
                                            )
                                        
                                        with interval_col3:
                                            st.metric("獲利後交易間隔", f"{emotional['avg_time_between_trades_after_win']:.1f} 分鐘")
                                        
                                        # 情緒失控案例
                                        st.write(f"**🚨 情緒失控案例：{emotional['cases_count']} 次 ({emotional['cases_percentage']:.1f}%)**")
                                        
                                        if emotional['cases_count'] > 0 and 'emotional_cases' in emotional:
                                            for i, case in enumerate(emotional['emotional_cases'][:3], 1):
                                                with st.container():
                                                    st.write(f"**案例 {i}**")
                                                    st.write(f"- 虧損 {case['after_loss']:.2f} USDT 後")
                                                    st.write(f"- 交易間隔：{case['time_interval']:.1f} 分鐘")
                                                    st.write(f"- 槓桿增加：{case['leverage_increase']:+.1f}%")
                                                    st.write(f"- 結果：{case['next_pnl']:+.2f} USDT")
                                                    st.divider()
                                        
                                        # 建議
                                        if emotional['severity'] in ['critical', 'high']:
                                            st.error("""
                                            ⚠️ **警告：檢測到明顯的情緒失控跡象！**
                                            
                                            **問題**：
                                            - 虧損後下單頻率明顯增加
                                            - 虧損後槓桿明顯增加
                                            - 交易間隔明顯縮短
                                            
                                            **建議**：
                                            - 設置冷靜期：虧損後強制休息 30-60 分鐘
                                            - 限制虧損後的槓桿：不允許增加槓桿
                                            - 使用交易日誌：記錄每筆交易的情緒狀態
                                            - 考慮尋求專業心理輔導
                                            """)
                                        elif emotional['severity'] == 'medium':
                                            st.warning("""
                                            💡 **建議：情緒控制有待改善**
                                            
                                            - 注意虧損後的交易行為
                                            - 設置交易規則並嚴格執行
                                            - 虧損後休息 15-30 分鐘再交易
                                            """)
                                        else:
                                            st.success("✅ 情緒控制良好，保持冷靜交易！")
                                    
                                    with tab7:
                                        st.write("**能力維度評分 (0-10分)**")
                                        
                                        # 獲取能力評分
                                        skills = risk_officer.calculate_skill_dimensions()
                                        
                                        # 綜合評分
                                        st.metric(
                                            "綜合能力評分",
                                            f"{skills['overall_score']:.1f}/10",
                                            delta="優秀" if skills['overall_score'] >= 8 else "良好" if skills['overall_score'] >= 7 else "及格" if skills['overall_score'] >= 6 else "不及格"
                                        )
                                        
                                        # 五大維度評分
                                        st.write("**📊 五大能力維度**")
                                        
                                        # 創建雷達圖數據
                                        import plotly.graph_objects as go
                                        
                                        categories = ['方向研判力', '風險控管力', '心理韌性', '執行紀律', '成本意識']
                                        values = [
                                            skills['direction_judgment'],
                                            skills['risk_management'],
                                            skills['psychological_resilience'],
                                            skills['execution_discipline'],
                                            skills['cost_awareness']
                                        ]
                                        
                                        fig = go.Figure()
                                        
                                        fig.add_trace(go.Scatterpolar(
                                            r=values,
                                            theta=categories,
                                            fill='toself',
                                            name='當前能力'
                                        ))
                                        
                                        fig.update_layout(
                                            polar=dict(
                                                radialaxis=dict(
                                                    visible=True,
                                                    range=[0, 10]
                                                )
                                            ),
                                            showlegend=False,
                                            height=400
                                        )
                                        
                                        st.plotly_chart(fig, use_container_width=True)
                                        
                                        # 詳細評分和扣分原因
                                        st.write("**📋 詳細評分**")
                                        
                                        # 1. 方向研判力
                                        with st.expander(f"1️⃣ 方向研判力：{skills['direction_judgment']:.1f}/10", expanded=False):
                                            st.write(f"**勝率**：{skills['win_rate']:.1%}")
                                            if skills['deduction_reasons']['direction_judgment']:
                                                st.write("**扣分原因**：")
                                                for reason in skills['deduction_reasons']['direction_judgment']:
                                                    st.write(f"❌ {reason}")
                                            else:
                                                st.success("✅ 勝率達標，方向判斷良好")
                                        
                                        # 2. 風險控管力
                                        with st.expander(f"2️⃣ 風險控管力：{skills['risk_management']:.1f}/10", expanded=False):
                                            if skills['deduction_reasons']['risk_management']:
                                                st.write("**扣分原因**：")
                                                for reason in skills['deduction_reasons']['risk_management']:
                                                    st.write(f"❌ {reason}")
                                            else:
                                                st.success("✅ 風險控制良好，單筆虧損在合理範圍內")
                                        
                                        # 3. 心理韌性
                                        with st.expander(f"3️⃣ 心理韌性：{skills['psychological_resilience']:.1f}/10", expanded=False):
                                            if skills['deduction_reasons']['psychological_resilience']:
                                                st.write("**扣分原因**：")
                                                for reason in skills['deduction_reasons']['psychological_resilience']:
                                                    st.write(f"❌ {reason}")
                                            else:
                                                st.success("✅ 心理素質良好，無報復性交易跡象")
                                        
                                        # 4. 執行紀律
                                        with st.expander(f"4️⃣ 執行紀律：{skills['execution_discipline']:.1f}/10", expanded=False):
                                            if skills['deduction_reasons']['execution_discipline']:
                                                st.write("**扣分原因**：")
                                                for reason in skills['deduction_reasons']['execution_discipline']:
                                                    st.write(f"❌ {reason}")
                                            else:
                                                st.success("✅ 執行紀律良好，交易一致性高")
                                        
                                        # 5. 成本意識
                                        with st.expander(f"5️⃣ 成本意識：{skills['cost_awareness']:.1f}/10", expanded=False):
                                            if skills['deduction_reasons']['cost_awareness']:
                                                st.write("**扣分原因**：")
                                                for reason in skills['deduction_reasons']['cost_awareness']:
                                                    st.write(f"❌ {reason}")
                                            else:
                                                st.success("✅ 成本控制良好，手續費效率高")
                                        
                                        # 總體建議
                                        st.write("**💡 總體建議**")
                                        if skills['overall_score'] < 5:
                                            st.error("""
                                            ⚠️ **綜合能力評分較低**
                                            
                                            建議：
                                            - 暫停實盤交易
                                            - 回到模擬盤練習
                                            - 重點改善評分最低的維度
                                            - 學習交易心理學和風險管理
                                            """)
                                        elif skills['overall_score'] < 7:
                                            st.warning("""
                                            💡 **綜合能力有待提升**
                                            
                                            建議：
                                            - 重點改善評分最低的維度
                                            - 降低交易頻率和倉位
                                            - 嚴格執行交易計劃
                                            """)
                                        else:
                                            st.success("""
                                            ✅ **綜合能力良好**
                                            
                                            建議：
                                            - 繼續保持並精進
                                            - 關注評分較低的維度
                                            - 持續學習和改進
                                            """)
                                
                                # 快速建議
                                st.write("**⚡ 快速改進建議**")
                                
                                suggestions = []
                                
                                # 根據分析結果生成建議
                                if ror['risk_of_ruin'] > 0.5:
                                    suggestions.append("🔴 **緊急**：破產風險極高，立即暫停交易並優化策略")
                                
                                if max_streak['max_streak'] > 10:
                                    suggestions.append("🔴 **緊急**：連續虧損過多，策略可能在某些市場環境下失效")
                                
                                short_trades = risk_officer.analyze_short_term_trades(5.0)
                                if short_trades.get('count', 0) > 0 and short_trades.get('expectancy', 0) < 0:
                                    simulation = risk_officer.simulate_without_short_trades(5.0)
                                    if simulation.get('pnl_improvement_pct', 0) > 10:
                                        suggestions.append(f"🟡 **建議**：停止所有 5 分鐘內的短線交易，可改善淨值 {simulation['pnl_improvement_pct']:.1f}%")
                                
                                if tilt['has_tilt'] and tilt['severity'] in ['high', 'medium']:
                                    suggestions.append("🟡 **建議**：實施傾斜檢測機制，虧損後禁止增加槓桿")
                                
                                if fee_pressure['fee_to_loss_ratio'] > 30:
                                    suggestions.append("🟡 **建議**：手續費壓力過大，減少交易頻率或增加每筆交易的目標利潤")
                                
                                # 冷靜期建議
                                if cooling['should_cool']:
                                    if cooling['severity'] == 'critical':
                                        suggestions.append(f"🔴 **緊急**：{cooling['reason']}，建議休息 {cooling['duration_minutes']} 分鐘")
                                    elif cooling['severity'] == 'high':
                                        suggestions.append(f"🟠 **警告**：{cooling['reason']}，建議休息 {cooling['duration_minutes']} 分鐘")
                                    else:
                                        suggestions.append(f"🟡 **建議**：{cooling['reason']}，建議休息 {cooling['duration_minutes']} 分鐘")
                                
                                # Kelly Criterion 建議
                                if kelly['kelly_optimal_size'] <= 0:
                                    suggestions.append("🔴 **緊急**：Kelly 最優倉位 ≤ 0，策略期望值為負，立即暫停交易")
                                elif kelly['kelly_optimal_size'] < 0.05:
                                    suggestions.append(f"🟡 **建議**：Kelly 最優倉位很小（{kelly['kelly_optimal_size']:.2%}），建議降低風險或改善策略")
                                
                                if suggestions:
                                    for suggestion in suggestions:
                                        st.write(suggestion)
                                else:
                                    st.success("✅ 當前風險指標在可控範圍內，繼續保持！")
                                
                            except ImportError:
                                st.warning("⚠️ 量化風險分析模組未安裝。請確保 quantitative_risk_analysis.py 在同一目錄下。")
                            except Exception as e:
                                st.error(f"❌ 量化風險分析失敗：{e}")
                                import traceback
                                with st.expander("查看錯誤詳情"):
                                    st.code(traceback.format_exc())
                        else:
                            st.info("💡 需要至少 10 筆已評分的交易才能進行量化風險分析。")
                        
                        # 評分方式統計
                        if 'scoring_mode' in scores_df.columns:
                            st.subheader("📊 評分方式統計")
                            
                            # 計算評分方式統計
                            mode_counts = scores_df['scoring_mode'].value_counts().to_dict()
                            
                            mode_col1, mode_col2, mode_col3 = st.columns(3)
                            
                            with mode_col1:
                                manual_count = mode_counts.get('manual', 0)
                                st.metric("手動評分", f"{manual_count} 筆")
                            
                            with mode_col2:
                                auto_count = mode_counts.get('auto', 0)
                                st.metric("自動評分", f"{auto_count} 筆")
                            
                            with mode_col3:
                                # 清除全部評分按鈕
                                st.write("")  # 空行對齊
                                
                                # 顯示確認對話框
                                if st.session_state.get('confirm_clear_scores', False):
                                    st.warning("⚠️ 確定要清除所有評分嗎？")
                                    confirm_col1, confirm_col2 = st.columns(2)
                                    with confirm_col1:
                                        if st.button("✅ 確定清除", key="confirm_yes", type="primary", use_container_width=True):
                                            # 執行清除
                                            try:
                                                quality_file = PathClass("data/review_history/quality_scores.json")
                                                if quality_file.exists():
                                                    # 備份
                                                    backup_file = quality_file.parent / f"quality_scores_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                                                    import shutil
                                                    shutil.copy(quality_file, backup_file)
                                                    
                                                    # 清空文件
                                                    with open(quality_file, 'w', encoding='utf-8') as f:
                                                        json.dump([], f)
                                                    
                                                    st.success(f"✅ 已清除所有評分！備份已保存至：{backup_file.name}")
                                                    st.session_state.confirm_clear_scores = False
                                                    time.sleep(1)
                                                    st.rerun()
                                            except Exception as e:
                                                st.error(f"❌ 清除失敗：{e}")
                                                st.session_state.confirm_clear_scores = False
                                    with confirm_col2:
                                        if st.button("❌ 取消", key="confirm_no", use_container_width=True):
                                            st.session_state.confirm_clear_scores = False
                                            st.rerun()
                                else:
                                    if st.button("🗑️ 清除全部評分", type="secondary", use_container_width=True):
                                        st.session_state.confirm_clear_scores = True
                                        st.rerun()
                        
                        # 詳細評分與註記
                        st.subheader("📋 詳細評分")
                        
                        # 準備顯示數據
                        display_cols = ['date', 'symbol', 'direction', 'pnl', 
                                       'entry_score', 'exit_score', 'risk_score', 
                                       'discipline_score', 'total_score']
                        
                        # 只選擇存在的欄位
                        available_cols = [col for col in display_cols if col in scores_df.columns]
                        display_scores = scores_df[available_cols].copy()
                        
                        # 處理 NaN 值 - 替換為 0
                        numeric_cols = ['entry_score', 'exit_score', 'risk_score', 'discipline_score', 'total_score']
                        for col in numeric_cols:
                            if col in display_scores.columns:
                                display_scores[col] = display_scores[col].fillna(0)
                        
                        # 重命名欄位
                        col_names = {
                            'date': '日期',
                            'symbol': '交易對',
                            'direction': '方向',
                            'pnl': '盈虧',
                            'entry_score': '進場',
                            'exit_score': '出場',
                            'risk_score': '風險',
                            'discipline_score': '紀律',
                            'total_score': '總分'
                        }
                        display_scores.columns = [col_names.get(col, col) for col in display_scores.columns]
                        
                        # 初始化 session state
                        if 'selected_trade_idx' not in st.session_state:
                            st.session_state.selected_trade_idx = None
                        
                        # 顯示表格和操作按鈕
                        st.write("**點擊「查看詳細」查看完整註記與分析**")
                        
                        # 表頭
                        header_cols = st.columns([1.2, 1.2, 0.8, 0.8, 0.7, 0.7, 0.7, 0.7, 0.8, 1])
                        headers = ['日期', '交易對', '方向', '盈虧', '進場', '出場', '風險', '紀律', '總分', '操作']
                        for col, header in zip(header_cols, headers):
                            with col:
                                st.markdown(f"**{header}**")
                        
                        st.markdown("---")
                        
                        # 為每一行創建按鈕
                        for idx, row in display_scores.iterrows():
                            cols = st.columns([1.2, 1.2, 0.8, 0.8, 0.7, 0.7, 0.7, 0.7, 0.8, 1])
                            
                            with cols[0]:
                                st.text(row['日期'])
                            with cols[1]:
                                st.text(row['交易對'])
                            with cols[2]:
                                st.text(row['方向'])
                            with cols[3]:
                                pnl_val = float(row['盈虧'])
                                if pnl_val > 0:
                                    st.markdown(f"<span style='color: green;'>{pnl_val:.2f}</span>", unsafe_allow_html=True)
                                else:
                                    st.markdown(f"<span style='color: red;'>{pnl_val:.2f}</span>", unsafe_allow_html=True)
                            with cols[4]:
                                st.text(f"{float(row['進場']):.0f}")
                            with cols[5]:
                                st.text(f"{float(row['出場']):.0f}")
                            with cols[6]:
                                st.text(f"{float(row['風險']):.0f}")
                            with cols[7]:
                                st.text(f"{float(row['紀律']):.0f}")
                            with cols[8]:
                                # 總分帶顏色和圖標
                                total = float(row['總分'])
                                if total >= 80:
                                    st.markdown(f"<span style='color: green; font-weight: bold;'>🌟 {total:.0f}</span>", unsafe_allow_html=True)
                                elif total >= 60:
                                    st.markdown(f"<span style='color: blue; font-weight: bold;'>✅ {total:.0f}</span>", unsafe_allow_html=True)
                                elif total >= 40:
                                    st.markdown(f"<span style='color: orange; font-weight: bold;'>⚠️ {total:.0f}</span>", unsafe_allow_html=True)
                                else:
                                    st.markdown(f"<span style='color: red; font-weight: bold;'>❌ {total:.0f}</span>", unsafe_allow_html=True)
                            with cols[9]:
                                if st.button("🔍 查看", key=f"view_{idx}", use_container_width=True):
                                    st.session_state.selected_trade_idx = idx
                                    st.rerun()
                            
                            # 如果這一行被選中，立即在下方顯示詳細信息（使用 expander）
                            if st.session_state.get('selected_trade_idx') == idx:
                                selected_row = scores_df.loc[idx]
                                
                                with st.expander("📊 交易詳細信息", expanded=True):
                                    # 交易基本信息（擴展版 - 添加數量、槓桿和實際收益率）
                                    info_row1_col1, info_row1_col2, info_row1_col3, info_row1_col4 = st.columns(4)
                                    info_row2_col1, info_row2_col2, info_row2_col3, info_row2_col4, info_row2_col5 = st.columns(5)
                                    
                                    # 第一行
                                    with info_row1_col1:
                                        st.metric("交易對", selected_row['symbol'])
                                    with info_row1_col2:
                                        st.metric("方向", selected_row['direction'])
                                    with info_row1_col3:
                                        # 顯示交易數量
                                        quantity = selected_row.get('quantity', 0)
                                        if pd.notna(quantity) and quantity > 0:
                                            st.metric("數量", f"{quantity:.4f}")
                                        else:
                                            st.metric("數量", "N/A")
                                    with info_row1_col4:
                                        # 顯示槓桿
                                        leverage = selected_row.get('leverage', 1)
                                        if pd.notna(leverage) and leverage > 0:
                                            st.metric("槓桿", f"{leverage:.0f}x")
                                        else:
                                            st.metric("槓桿", "N/A")
                                    
                                    # 第二行
                                    with info_row2_col1:
                                        pnl_delta = "盈利" if selected_row['pnl'] > 0 else "虧損"
                                        st.metric("盈虧", f"{selected_row['pnl']:.2f} USDT", delta=pnl_delta)
                                    with info_row2_col2:
                                        # 計算盈虧百分比（價格變動）
                                        entry_price = selected_row.get('entry_price', 0)
                                        exit_price = selected_row.get('exit_price', 0)
                                        pnl_pct = 0
                                        if entry_price > 0 and exit_price > 0:
                                            if selected_row['direction'] == 'Long':
                                                pnl_pct = ((exit_price - entry_price) / entry_price) * 100
                                            else:
                                                pnl_pct = ((entry_price - exit_price) / entry_price) * 100
                                            st.metric("價格變動%", f"{pnl_pct:+.2f}%", help="價格變動百分比（不考慮槓桿）")
                                        else:
                                            st.metric("價格變動%", "N/A")
                                    with info_row2_col3:
                                        # 計算實際收益率（考慮槓桿）
                                        leverage = selected_row.get('leverage', 1)
                                        if pd.notna(leverage) and leverage > 0 and entry_price > 0 and exit_price > 0:
                                            actual_return = pnl_pct * leverage
                                            # 根據收益率顯示不同顏色
                                            if actual_return > 0:
                                                st.metric("實際收益率", f"{actual_return:+.2f}%", 
                                                         delta="盈利", delta_color="normal",
                                                         help="價格變動% × 槓桿")
                                            else:
                                                st.metric("實際收益率", f"{actual_return:+.2f}%", 
                                                         delta="虧損", delta_color="inverse",
                                                         help="價格變動% × 槓桿")
                                        else:
                                            st.metric("實際收益率", "N/A", help="價格變動% × 槓桿")
                                    with info_row2_col4:
                                        total_score = selected_row.get('total_score', 0)
                                        if pd.isna(total_score):
                                            total_score = 0
                                        st.metric("總分", f"{total_score:.0f}/100")
                                    with info_row2_col5:
                                        scoring_mode = selected_row.get('scoring_mode', 'manual')
                                        mode_text = "🤖 自動" if scoring_mode == 'auto' else "✍️ 手動"
                                        st.metric("評分方式", mode_text)
                                    
                                    # 各項評分（緊湊版）
                                    with st.expander("📊 評分明細", expanded=False):
                                        score_col1, score_col2, score_col3, score_col4 = st.columns(4)
                                        
                                        # 獲取評分原因（從 tags 中提取，排除 'auto_scored'）
                                        tags = selected_row.get('tags', [])
                                        if isinstance(tags, list):
                                            scoring_reasons = [tag for tag in tags if tag != 'auto_scored']
                                        else:
                                            scoring_reasons = []
                                        
                                        # 分類評分原因
                                        entry_reasons = []
                                        exit_reasons = []
                                        risk_reasons = []
                                        discipline_reasons = []
                                        
                                        for reason in scoring_reasons:
                                            reason_lower = reason.lower()
                                            # 進場相關
                                            if any(keyword in reason_lower for keyword in ['逆勢', '震盪', 'rsi', 'macd', '信號', '確認', '波動', '布林']):
                                                entry_reasons.append(reason)
                                            # 出場相關
                                            elif any(keyword in reason_lower for keyword in ['收益', '虧損', '盈虧比', '止損']):
                                                exit_reasons.append(reason)
                                            # 風險相關
                                            elif any(keyword in reason_lower for keyword in ['槓桿', '手續費']):
                                                risk_reasons.append(reason)
                                            # 紀律相關
                                            elif any(keyword in reason_lower for keyword in ['爆倉', '平倉', '持倉', '交易計劃']):
                                                discipline_reasons.append(reason)
                                            else:
                                                # 默認歸類到紀律
                                                discipline_reasons.append(reason)
                                        
                                        with score_col1:
                                            entry_score = selected_row.get('entry_score', 0)
                                            if pd.isna(entry_score):
                                                entry_score = 0
                                            
                                            # 生成 tooltip 內容
                                            entry_help = "進場質量評分\n\n"
                                            if entry_reasons:
                                                entry_help += "評分原因：\n" + "\n".join(f"• {r}" for r in entry_reasons)
                                            else:
                                                entry_help += "無特別註記"
                                            
                                            st.metric("進場", f"{entry_score:.0f}/25", help=entry_help)
                                            st.progress(max(0.0, min(1.0, entry_score / 25)))
                                        
                                        with score_col2:
                                            exit_score = selected_row.get('exit_score', 0)
                                            if pd.isna(exit_score):
                                                exit_score = 0
                                            
                                            # 生成 tooltip 內容
                                            exit_help = "出場質量評分\n\n"
                                            if exit_reasons:
                                                exit_help += "評分原因：\n" + "\n".join(f"• {r}" for r in exit_reasons)
                                            else:
                                                exit_help += "無特別註記"
                                            
                                            st.metric("出場", f"{exit_score:.0f}/25", help=exit_help)
                                            st.progress(max(0.0, min(1.0, exit_score / 25)))
                                        
                                        with score_col3:
                                            risk_score = selected_row.get('risk_score', 0)
                                            if pd.isna(risk_score):
                                                risk_score = 0
                                            
                                            # 生成 tooltip 內容
                                            risk_help = "風險控制評分\n\n"
                                            if risk_reasons:
                                                risk_help += "評分原因：\n" + "\n".join(f"• {r}" for r in risk_reasons)
                                            else:
                                                risk_help += "無特別註記"
                                            
                                            st.metric("風險", f"{risk_score:.0f}/25", help=risk_help)
                                            st.progress(max(0.0, min(1.0, risk_score / 25)))
                                        
                                        with score_col4:
                                            discipline_score = selected_row.get('discipline_score', 0)
                                            if pd.isna(discipline_score):
                                                discipline_score = 0
                                            
                                            # 生成 tooltip 內容
                                            discipline_help = "紀律遵守評分\n\n"
                                            if discipline_reasons:
                                                discipline_help += "評分原因：\n" + "\n".join(f"• {r}" for r in discipline_reasons)
                                            else:
                                                discipline_help += "無特別註記"
                                            
                                            st.metric("紀律", f"{discipline_score:.0f}/25", help=discipline_help)
                                            st.progress(max(0.0, min(1.0, discipline_score / 25)))
                                    
                                    # 註記與分析（使用 tabs）
                                    tab1, tab2, tab3 = st.tabs(["📝 註記", "🔬 市場分析", "📊 原始數據"])
                                    
                                    with tab1:
                                        note_content = selected_row.get('note', '無註記')
                                        if not note_content or note_content.strip() == '':
                                            st.info("此交易沒有註記")
                                        else:
                                            st.text_area(
                                                "註記內容",
                                                value=note_content,
                                                height=300,
                                                disabled=True,
                                                label_visibility="collapsed"
                                            )
                                    
                                    with tab2:
                                        if 'market_analysis' in selected_row and selected_row['market_analysis']:
                                            analysis = selected_row['market_analysis']
                                            
                                            # 顯示關鍵指標
                                            if isinstance(analysis, dict):
                                                st.write("**關鍵市場指標**")
                                                
                                                # 提取常見指標
                                                key_metrics = {}
                                                for key in ['trend', 'trend_strength', 'rsi', 'rsi_state', 'volatility', 'volume_state']:
                                                    if key in analysis:
                                                        key_metrics[key] = analysis[key]
                                                
                                                if key_metrics:
                                                    metric_col1, metric_col2, metric_col3 = st.columns(3)
                                                    
                                                    with metric_col1:
                                                        if 'trend' in key_metrics:
                                                            st.metric("趨勢", key_metrics['trend'])
                                                        if 'trend_strength' in key_metrics:
                                                            st.metric("趨勢強度", f"{key_metrics['trend_strength']:.1f}")
                                                    
                                                    with metric_col2:
                                                        if 'rsi' in key_metrics:
                                                            st.metric("RSI", f"{key_metrics['rsi']:.1f}")
                                                        if 'rsi_state' in key_metrics:
                                                            st.metric("RSI 狀態", key_metrics['rsi_state'])
                                                    
                                                    with metric_col3:
                                                        if 'volatility' in key_metrics:
                                                            st.metric("波動率", key_metrics['volatility'])
                                                        if 'volume_state' in key_metrics:
                                                            st.metric("成交量", key_metrics['volume_state'])
                                                
                                                st.divider()
                                                
                                                # 多時區圖表分析
                                                if 'multi_timeframe' in analysis:
                                                    st.write("**📊 多時區技術分析**")
                                                    
                                                    # 獲取交易信息並轉換交易對格式
                                                    raw_symbol = str(selected_row.get('symbol', 'btc')).strip()
                                                    
                                                    # 處理不同格式的交易對（與評分邏輯一致）
                                                    if raw_symbol.lower() in ['btc', 'bitcoin']:
                                                        symbol = 'BTCUSDT'
                                                    elif raw_symbol.lower() in ['eth', 'ethereum']:
                                                        symbol = 'ETHUSDT'
                                                    elif raw_symbol.lower() in ['bnb']:
                                                        symbol = 'BNBUSDT'
                                                    elif raw_symbol.lower() in ['sol', 'solana']:
                                                        symbol = 'SOLUSDT'
                                                    elif raw_symbol.lower() in ['xrp', 'ripple']:
                                                        symbol = 'XRPUSDT'
                                                    elif raw_symbol.lower() in ['doge', 'dogecoin']:
                                                        symbol = 'DOGEUSDT'
                                                    elif raw_symbol.lower() in ['ada', 'cardano']:
                                                        symbol = 'ADAUSDT'
                                                    elif raw_symbol.lower() in ['avax', 'avalanche']:
                                                        symbol = 'AVAXUSDT'
                                                    elif raw_symbol.lower() in ['dot', 'polkadot']:
                                                        symbol = 'DOTUSDT'
                                                    elif raw_symbol.lower() in ['matic', 'polygon']:
                                                        symbol = 'MATICUSDT'
                                                    elif raw_symbol.lower() in ['link', 'chainlink']:
                                                        symbol = 'LINKUSDT'
                                                    elif raw_symbol.lower() in ['uni', 'uniswap']:
                                                        symbol = 'UNIUSDT'
                                                    elif raw_symbol.lower() in ['atom', 'cosmos']:
                                                        symbol = 'ATOMUSDT'
                                                    elif raw_symbol.lower() in ['ltc', 'litecoin']:
                                                        symbol = 'LTCUSDT'
                                                    elif raw_symbol.lower() in ['etc', 'ethereum classic']:
                                                        symbol = 'ETCUSDT'
                                                    elif raw_symbol.lower() in ['bch', 'bitcoin cash']:
                                                        symbol = 'BCHUSDT'
                                                    elif raw_symbol.lower() in ['xlm', 'stellar']:
                                                        symbol = 'XLMUSDT'
                                                    elif raw_symbol.lower() in ['trx', 'tron']:
                                                        symbol = 'TRXUSDT'
                                                    elif raw_symbol.lower() in ['near']:
                                                        symbol = 'NEARUSDT'
                                                    elif raw_symbol.lower() in ['algo', 'algorand']:
                                                        symbol = 'ALGOUSDT'
                                                    elif raw_symbol.lower() in ['vet', 'vechain']:
                                                        symbol = 'VETUSDT'
                                                    elif raw_symbol.lower() in ['icp', 'internet computer']:
                                                        symbol = 'ICPUSDT'
                                                    elif raw_symbol.lower() in ['fil', 'filecoin']:
                                                        symbol = 'FILUSDT'
                                                    elif raw_symbol.lower() in ['apt', 'aptos']:
                                                        symbol = 'APTUSDT'
                                                    elif raw_symbol.lower() in ['arb', 'arbitrum']:
                                                        symbol = 'ARBUSDT'
                                                    elif raw_symbol.lower() in ['op', 'optimism']:
                                                        symbol = 'OPUSDT'
                                                    elif raw_symbol.lower() in ['sui']:
                                                        symbol = 'SUIUSDT'
                                                    else:
                                                        # 通用處理
                                                        symbol = raw_symbol.replace('-', '').upper()
                                                        if not symbol.endswith('USDT'):
                                                            if symbol.endswith('USD'):
                                                                symbol = symbol[:-3] + 'USDT'
                                                            else:
                                                                symbol = symbol + 'USDT'
                                                    
                                                    trade_time = selected_row.get('entry_time') or selected_row.get('date')
                                                    
                                                    if trade_time:
                                                        try:
                                                            from src.analysis.market_analyzer import MarketAnalyzer
                                                            import plotly.graph_objects as go
                                                            from plotly.subplots import make_subplots
                                                            
                                                            analyzer = MarketAnalyzer()
                                                            
                                                            # 獲取進場和出場時間
                                                            entry_time = selected_row.get('open_time') or selected_row.get('entry_time') or selected_row.get('date')
                                                            exit_time = selected_row.get('close_time') or selected_row.get('exit_time')
                                                            
                                                            # 時區選擇
                                                            available_intervals = list(analysis['multi_timeframe'].keys())
                                                            
                                                            # 在時區選擇器上方顯示一次調試信息
                                                            st.info(f"🔍 **交易時間**\n\n進場：{entry_time} | 出場：{exit_time if exit_time else '無'}\n\n💡 提示：標記顯示在包含該時間的K線上（例如：8:50的交易會標記在8:45-9:00的K線）")
                                                            
                                                            selected_interval = st.selectbox(
                                                                "選擇時區",
                                                                available_intervals,
                                                                index=available_intervals.index('1h') if '1h' in available_intervals else 0,
                                                                key=f"interval_select_{idx}"
                                                            )
                                                            
                                                            # 載入該時區的市場數據
                                                            df = analyzer.load_market_data(symbol, selected_interval)
                                                            
                                                            if df is not None and len(df) > 0:
                                                                # 計算指標
                                                                df = analyzer.calculate_indicators(df)
                                                                
                                                                # 找到進場時間點附近的數據
                                                                if not entry_time or pd.isna(entry_time):
                                                                    st.warning("⚠️ 無法獲取進場時間")
                                                                else:
                                                                    entry_timestamp = pd.to_datetime(entry_time)
                                                                    df['time_diff'] = abs((df['timestamp'] - entry_timestamp).dt.total_seconds())
                                                                    entry_idx = df['time_diff'].idxmin()
                                                                    
                                                                    # 找到出場時間點
                                                                    exit_idx = None
                                                                    exit_timestamp = None
                                                                    if exit_time and pd.notna(exit_time):
                                                                        try:
                                                                            exit_timestamp = pd.to_datetime(exit_time)
                                                                            df['exit_time_diff'] = abs((df['timestamp'] - exit_timestamp).dt.total_seconds())
                                                                            exit_idx = df['exit_time_diff'].idxmin()
                                                                        except Exception as e:
                                                                            st.warning(f"⚠️ 出場時間解析失敗：{e}")
                                                                    
                                                                    # 確定顯示範圍（包含進場和出場）
                                                                    if exit_idx is not None:
                                                                        # 如果有出場時間，確保兩個點都在顯示範圍內
                                                                        min_idx = min(entry_idx, exit_idx)
                                                                        max_idx = max(entry_idx, exit_idx)
                                                                        start_idx = max(0, min_idx - 30)
                                                                        end_idx = min(len(df), max_idx + 30)
                                                                    else:
                                                                        # 只有進場時間
                                                                        start_idx = max(0, entry_idx - 50)
                                                                        end_idx = min(len(df), entry_idx + 50)
                                                                    
                                                                    df_display = df.iloc[start_idx:end_idx].copy()
                                                                    
                                                                    # 創建子圖：K線 + 指標
                                                                    fig = make_subplots(
                                                                        rows=5, cols=1,
                                                                        shared_xaxes=True,
                                                                        vertical_spacing=0.03,
                                                                        row_heights=[0.4, 0.15, 0.15, 0.15, 0.15],
                                                                        subplot_titles=(
                                                                            f'{symbol} {selected_interval} K線圖 + EMA + 布林帶',
                                                                            'MACD',
                                                                            'RSI',
                                                                            'ATR',
                                                                            '成交量'
                                                                        )
                                                                    )
                                                                    
                                                                    # 1. K線圖
                                                                    fig.add_trace(
                                                                        go.Candlestick(
                                                                            x=df_display['timestamp'],
                                                                            open=df_display['open'],
                                                                            high=df_display['high'],
                                                                            low=df_display['low'],
                                                                            close=df_display['close'],
                                                                            name='K線',
                                                                            increasing_line_color='#26a69a',
                                                                            decreasing_line_color='#ef5350'
                                                                        ),
                                                                        row=1, col=1
                                                                        )
                                                                    
                                                                    # EMA 12, 26
                                                                    fig.add_trace(
                                                                        go.Scatter(
                                                                            x=df_display['timestamp'],
                                                                            y=df_display['ema_12'],
                                                                            name='EMA 12',
                                                                            line=dict(color='orange', width=1)
                                                                        ),
                                                                        row=1, col=1
                                                                    )
                                                                    
                                                                    fig.add_trace(
                                                                        go.Scatter(
                                                                            x=df_display['timestamp'],
                                                                            y=df_display['ema_26'],
                                                                            name='EMA 26',
                                                                            line=dict(color='blue', width=1)
                                                                        ),
                                                                        row=1, col=1
                                                                    )
                                                                    
                                                                    # 布林帶
                                                                    fig.add_trace(
                                                                        go.Scatter(
                                                                            x=df_display['timestamp'],
                                                                            y=df_display['bb_upper'],
                                                                            name='布林上軌',
                                                                            line=dict(color='gray', width=1, dash='dash'),
                                                                            showlegend=False
                                                                        ),
                                                                        row=1, col=1
                                                                    )
                                                                    
                                                                    fig.add_trace(
                                                                        go.Scatter(
                                                                            x=df_display['timestamp'],
                                                                            y=df_display['bb_middle'],
                                                                            name='布林中軌',
                                                                            line=dict(color='gray', width=1),
                                                                            showlegend=False
                                                                        ),
                                                                        row=1, col=1
                                                                    )
                                                                    
                                                                    fig.add_trace(
                                                                        go.Scatter(
                                                                            x=df_display['timestamp'],
                                                                            y=df_display['bb_lower'],
                                                                            name='布林下軌',
                                                                            line=dict(color='gray', width=1, dash='dash'),
                                                                            fill='tonexty',
                                                                            fillcolor='rgba(128,128,128,0.1)',
                                                                            showlegend=False
                                                                        ),
                                                                        row=1, col=1
                                                                    )
                                                                    
                                                                    # 標記進場點
                                                                    # 使用實際進場價格，而不是K線收盤價
                                                                    entry_price = selected_row.get('entry_price', df.loc[entry_idx, 'close'])
                                                                    entry_high = df.loc[entry_idx, 'high']
                                                                    entry_low = df.loc[entry_idx, 'low']
                                                                    direction = selected_row.get('direction', 'Long')
                                                                    
                                                                    # 計算標記位置（避免遮擋K線）
                                                                    price_range = entry_high - entry_low
                                                                    if direction == 'Long':
                                                                        # 做多：標記在K線下方
                                                                        marker_y = entry_low - price_range * 0.5
                                                                        text_position = 'bottom center'
                                                                    else:
                                                                        # 做空：標記在K線上方
                                                                        marker_y = entry_high + price_range * 0.5
                                                                        text_position = 'top center'
                                                                    
                                                                    fig.add_trace(
                                                                        go.Scatter(
                                                                            x=[df.loc[entry_idx, 'timestamp']],
                                                                            y=[marker_y],
                                                                            mode='markers+text',
                                                                            name='進場',
                                                                            text=[f'進場<br>{entry_time[11:19]}<br>${entry_price:.2f}'],  # 顯示時間和價格
                                                                            textposition=text_position,
                                                                            marker=dict(
                                                                                size=15,
                                                                                color='#00ff00' if direction == 'Long' else '#ff0000',
                                                                                symbol='triangle-up' if direction == 'Long' else 'triangle-down',
                                                                                line=dict(color='white', width=2)
                                                                            ),
                                                                            textfont=dict(
                                                                                size=10,
                                                                                color='#00ff00' if direction == 'Long' else '#ff0000',
                                                                                family='Arial'
                                                                            ),
                                                                            showlegend=True
                                                                        ),
                                                                        row=1, col=1
                                                                    )
                                                                    
                                                                    # 標記出場點（如果有）
                                                                    if exit_idx is not None:
                                                                        # 使用實際出場價格，而不是K線收盤價
                                                                        exit_price = selected_row.get('exit_price', df.loc[exit_idx, 'close'])
                                                                        exit_high = df.loc[exit_idx, 'high']
                                                                        exit_low = df.loc[exit_idx, 'low']
                                                                        pnl = selected_row.get('pnl', 0)
                                                                        is_profit = pnl > 0
                                                                        
                                                                        # 計算標記位置（避免遮擋K線）
                                                                        exit_price_range = exit_high - exit_low
                                                                        if is_profit:
                                                                            # 獲利：標記在K線上方
                                                                            exit_marker_y = exit_high + exit_price_range * 0.5
                                                                            exit_text_position = 'top center'
                                                                        else:
                                                                            # 虧損：標記在K線下方
                                                                            exit_marker_y = exit_low - exit_price_range * 0.5
                                                                            exit_text_position = 'bottom center'
                                                                        
                                                                        fig.add_trace(
                                                                            go.Scatter(
                                                                                x=[df.loc[exit_idx, 'timestamp']],
                                                                                y=[exit_marker_y],
                                                                                mode='markers+text',
                                                                                name='出場',
                                                                                text=[f'出場<br>{exit_time[11:19]}<br>${exit_price:.2f}'],  # 顯示時間和價格
                                                                                textposition=exit_text_position,
                                                                                marker=dict(
                                                                                    size=15,
                                                                                    color='#ffd700' if is_profit else '#ff6347',
                                                                                    symbol='x',
                                                                                    line=dict(color='white', width=2)
                                                                                ),
                                                                                textfont=dict(
                                                                                    size=10,
                                                                                    color='#ffd700' if is_profit else '#ff6347',
                                                                                    family='Arial'
                                                                                ),
                                                                                showlegend=True
                                                                            ),
                                                                            row=1, col=1
                                                                        )
                                                                        
                                                                        # 繪製進場到出場的連線（使用實際價格）
                                                                        fig.add_trace(
                                                                            go.Scatter(
                                                                                x=[df.loc[entry_idx, 'timestamp'], df.loc[exit_idx, 'timestamp']],
                                                                                y=[entry_price, exit_price],
                                                                                mode='lines',
                                                                                name='持倉期間',
                                                                                line=dict(
                                                                                    color='#00ff00' if is_profit else '#ff0000',
                                                                                    width=2,
                                                                                    dash='dash'
                                                                                ),
                                                                                showlegend=True
                                                                            ),
                                                                            row=1, col=1
                                                                        )
                                                                    
                                                                    # 2. MACD
                                                                    fig.add_trace(
                                                                        go.Scatter(
                                                                            x=df_display['timestamp'],
                                                                            y=df_display['macd'],
                                                                            name='MACD',
                                                                            line=dict(color='blue', width=1)
                                                                        ),
                                                                        row=2, col=1
                                                                    )
                                                                    
                                                                    fig.add_trace(
                                                                        go.Scatter(
                                                                            x=df_display['timestamp'],
                                                                            y=df_display['macd_signal'],
                                                                            name='Signal',
                                                                            line=dict(color='orange', width=1)
                                                                        ),
                                                                        row=2, col=1
                                                                    )
                                                                    
                                                                    # MACD 柱狀圖
                                                                    colors = ['green' if val >= 0 else 'red' for val in df_display['macd_hist']]
                                                                    fig.add_trace(
                                                                        go.Bar(
                                                                            x=df_display['timestamp'],
                                                                            y=df_display['macd_hist'],
                                                                            name='MACD Hist',
                                                                            marker_color=colors,
                                                                            showlegend=False
                                                                        ),
                                                                        row=2, col=1
                                                                    )
                                                                    
                                                                    # 3. RSI
                                                                    fig.add_trace(
                                                                        go.Scatter(
                                                                            x=df_display['timestamp'],
                                                                            y=df_display['rsi'],
                                                                            name='RSI',
                                                                            line=dict(color='purple', width=2)
                                                                        ),
                                                                        row=3, col=1
                                                                    )
                                                                    
                                                                    # RSI 超買超賣線
                                                                    fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1, opacity=0.5)
                                                                    fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1, opacity=0.5)
                                                                    
                                                                    # 4. ATR
                                                                    fig.add_trace(
                                                                        go.Scatter(
                                                                            x=df_display['timestamp'],
                                                                            y=df_display['atr'],
                                                                            name='ATR',
                                                                            line=dict(color='brown', width=2),
                                                                            fill='tozeroy',
                                                                            fillcolor='rgba(165,42,42,0.2)'
                                                                        ),
                                                                        row=4, col=1
                                                                    )
                                                                    
                                                                    # 5. 成交量
                                                                    volume_colors = ['green' if df_display['close'].iloc[i] >= df_display['open'].iloc[i] 
                                                                                   else 'red' for i in range(len(df_display))]
                                                                    
                                                                    fig.add_trace(
                                                                        go.Bar(
                                                                            x=df_display['timestamp'],
                                                                            y=df_display['volume'],
                                                                            name='成交量',
                                                                            marker_color=volume_colors,
                                                                            showlegend=False
                                                                        ),
                                                                        row=5, col=1
                                                                    )
                                                                    
                                                                    # 成交量均線
                                                                    fig.add_trace(
                                                                        go.Scatter(
                                                                            x=df_display['timestamp'],
                                                                            y=df_display['volume_sma'],
                                                                            name='成交量均線',
                                                                            line=dict(color='orange', width=1)
                                                                        ),
                                                                        row=5, col=1
                                                                    )
                                                                    
                                                                    # 更新布局
                                                                    fig.update_layout(
                                                                        height=1200,
                                                                        showlegend=True,
                                                                        xaxis_rangeslider_visible=False,
                                                                        hovermode='x unified',
                                                                        legend=dict(
                                                                            orientation="h",
                                                                            yanchor="bottom",
                                                                            y=1.02,
                                                                            xanchor="right",
                                                                            x=1
                                                                        )
                                                                    )
                                                                    
                                                                    # 更新 Y 軸標籤
                                                                    fig.update_yaxes(title_text="價格", row=1, col=1)
                                                                    fig.update_yaxes(title_text="MACD", row=2, col=1)
                                                                    fig.update_yaxes(title_text="RSI", row=3, col=1)
                                                                    fig.update_yaxes(title_text="ATR", row=4, col=1)
                                                                    fig.update_yaxes(title_text="成交量", row=5, col=1)
                                                                    
                                                                    st.plotly_chart(fig, use_container_width=True)
                                                                    
                                                                    # 顯示該時區的關鍵指標
                                                                    st.write(f"**{selected_interval} 時區關鍵數據**")
                                                                    
                                                                    tf_analysis = analysis['multi_timeframe'].get(selected_interval, {})
                                                                    if tf_analysis:
                                                                        ind_col1, ind_col2, ind_col3, ind_col4 = st.columns(4)
                                                                        
                                                                        with ind_col1:
                                                                            st.metric("趨勢", tf_analysis.get('trend', 'N/A'))
                                                                            st.metric("RSI", f"{tf_analysis.get('rsi', 0):.1f}")
                                                                        
                                                                        with ind_col2:
                                                                            st.metric("MACD 狀態", tf_analysis.get('macd_state', 'N/A'))
                                                                            st.metric("波動率", tf_analysis.get('volatility', 'N/A'))
                                                                        
                                                                        with ind_col3:
                                                                            st.metric("均線排列", tf_analysis.get('ma_alignment', 'N/A'))
                                                                            st.metric("布林帶位置", tf_analysis.get('bb_position', 'N/A'))
                                                                        
                                                                        with ind_col4:
                                                                            st.metric("成交量", tf_analysis.get('volume_state', 'N/A'))
                                                                            st.metric("ATR %", f"{tf_analysis.get('atr_pct', 0):.2f}%")
                                                            
                                                            else:
                                                                st.warning(f"⚠️ 無法載入 {symbol} {selected_interval} 的市場數據")
                                                        
                                                        except Exception as e:
                                                            st.error(f"❌ 載入圖表失敗：{str(e)}")
                                                            import traceback
                                                            with st.expander("查看錯誤詳情"):
                                                                st.code(traceback.format_exc())
                                                    else:
                                                        st.info("此交易缺少時間信息，無法顯示圖表")
                                                
                                                st.divider()
                                            
                                            # 完整 JSON
                                            with st.expander("查看完整分析數據"):
                                                st.json(analysis)
                                        else:
                                            st.info("此交易沒有市場分析數據")
                                    
                                    with tab3:
                                        # 顯示原始交易數據
                                        trade_data = selected_row.to_dict()
                                        # 簡化顯示
                                        if 'note' in trade_data and len(str(trade_data['note'])) > 100:
                                            trade_data['note'] = f"{str(trade_data['note'])[:100]}... (已截斷)"
                                        if 'market_analysis' in trade_data:
                                            trade_data['market_analysis'] = "<請查看市場分析標籤>"
                                        
                                        st.json(trade_data)
                                    
                                    # 關閉按鈕
                                    if st.button("❌ 關閉", key=f"close_{idx}", use_container_width=True):
                                        st.session_state.selected_trade_idx = None
                                        st.rerun()
                
                except Exception as e:
                    st.error(f"❌ 讀取評分失敗：{str(e)}")
                    import traceback
                    st.write("錯誤詳情：")
                    st.code(traceback.format_exc())
            else:
                st.info("✅ 目前沒有評分記錄，請先為交易評分")

