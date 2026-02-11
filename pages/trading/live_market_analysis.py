"""
實時市場分析 - 機構級技術分析

提供當前價格在各時區的表現分析和交易建議
作為 CMT Level 3 技術分析師，提供專業的交易決策支持
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from pathlib import Path
import sys
import os
import time

# 添加項目根目錄到路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

try:
    from src.analysis.market_analyzer import MarketAnalyzer
    MARKET_ANALYZER_AVAILABLE = True
except Exception as e:
    MARKET_ANALYZER_AVAILABLE = False
    IMPORT_ERROR = str(e)


def calculate_trading_recommendation(analysis: dict, symbol: str) -> dict:
    """
    基於多時區分析生成交易建議
    
    作為 CMT Level 3 分析師，綜合考慮：
    - 多時區趨勢一致性
    - 技術指標信號
    - 支撐阻力位
    - 風險回報比
    """
    
    if not analysis or 'multi_timeframe' not in analysis:
        return None
    
    multi_tf = analysis['multi_timeframe']
    
    # 獲取最實時的價格（優先使用最短時區）
    # 優先順序：1m > 3m > 5m > 15m > 1h
    current_price = None
    price_source = None
    for tf in ['1m', '3m', '5m', '15m', '1h', '4h', '1d']:
        if tf in multi_tf and multi_tf[tf].get('price'):
            current_price = multi_tf[tf].get('price')
            price_source = tf
            break
    
    # 如果沒有找到，使用主分析的價格
    if not current_price:
        current_price = analysis.get('price', 0)
        price_source = '主時區'
    
    # 分析各時區趨勢
    timeframes = ['1d', '4h', '1h', '15m', '5m', '3m', '1m']  # 所有時區
    trends = {}
    rsi_values = {}
    macd_states = {}
    
    for tf in timeframes:
        if tf in multi_tf:
            tf_data = multi_tf[tf]
            trends[tf] = tf_data.get('trend', 'unknown')
            rsi_values[tf] = tf_data.get('rsi', 50)
            macd_states[tf] = tf_data.get('macd_state', 'unknown')
    
    # 判斷主要趨勢方向
    bullish_count = sum(1 for t in trends.values() if 'uptrend' in t)
    bearish_count = sum(1 for t in trends.values() if 'downtrend' in t)
    
    # 獲取關鍵時區數據（1h 為主）
    primary_tf = '1h'
    if primary_tf not in multi_tf:
        primary_tf = '4h' if '4h' in multi_tf else list(multi_tf.keys())[0]
    
    primary_data = multi_tf[primary_tf]
    
    # 獲取技術指標
    atr = primary_data.get('atr', 0)
    atr_pct = primary_data.get('atr_pct', 0)
    support = primary_data.get('support_resistance', {}).get('support')
    resistance = primary_data.get('support_resistance', {}).get('resistance')
    rsi = primary_data.get('rsi', 50)
    macd_state = primary_data.get('macd_state', 'unknown')
    
    # 決策邏輯
    recommendation = {
        'symbol': symbol,
        'current_price': current_price,
        'price_source': price_source,  # 新增：記錄價格來源
        'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'primary_timeframe': primary_tf
    }
    
    # 1. 判斷方向（改進邏輯：考慮多空力量對比）
    # 計算多空力量差距
    net_bullish = bullish_count - bearish_count
    
    # 決策邏輯：
    # - 如果多空力量差距明顯（>=2），跟隨主要趨勢
    # - 如果多空力量接近（差距<2），結合 RSI 判斷
    if net_bullish >= 2 and rsi < 70:
        # 明顯看多（多頭時區比空頭多 2 個以上）
        direction = '做多 (Long)'
        confidence = 'high' if net_bullish >= 3 else 'medium'
    elif net_bullish <= -2 and rsi > 30:
        # 明顯看空（空頭時區比多頭多 2 個以上）
        direction = '做空 (Short)'
        confidence = 'high' if net_bullish <= -3 else 'medium'
    elif net_bullish >= 1 and rsi < 40:
        # 輕微看多 + RSI 超賣
        direction = '做多 (Long)'
        confidence = 'medium'
    elif net_bullish <= -1 and rsi > 60:
        # 輕微看空 + RSI 超買
        direction = '做空 (Short)'
        confidence = 'medium'
    else:
        # 多空力量均衡或信號不明確
        direction = '觀望 (Wait)'
        confidence = 'low'
    
    recommendation['direction'] = direction
    recommendation['confidence'] = confidence
    recommendation['net_bullish'] = net_bullish  # 記錄多空力量差距
    
    # 2. 建議進場價位
    if direction == '做多 (Long)':
        if rsi < 40:
            entry_suggestion = f"現價 {current_price:.2f} (RSI 超賣)"
        elif support and current_price > support:
            pullback_price = support * 1.002  # 支撐位上方 0.2%
            entry_suggestion = f"等待回調至 {pullback_price:.2f} (支撐位附近)"
        else:
            entry_suggestion = f"現價 {current_price:.2f}"
    
    elif direction == '做空 (Short)':
        if rsi > 60:
            entry_suggestion = f"現價 {current_price:.2f} (RSI 超買)"
        elif resistance and current_price < resistance:
            pullback_price = resistance * 0.998  # 阻力位下方 0.2%
            entry_suggestion = f"等待反彈至 {pullback_price:.2f} (阻力位附近)"
        else:
            entry_suggestion = f"現價 {current_price:.2f}"
    
    else:
        entry_suggestion = "等待明確信號"
    
    recommendation['entry_suggestion'] = entry_suggestion
    
    # 3. 止損位 (基於 ATR 和支撐阻力)
    if direction == '做多 (Long)':
        # 使用支撐位或 ATR
        if support:
            stop_loss = support * 0.995  # 支撐位下方 0.5%
            stop_method = "支撐位下方"
        else:
            stop_loss = current_price - (atr * 1.5)
            stop_method = "1.5 ATR"
    
    elif direction == '做空 (Short)':
        # 使用阻力位或 ATR
        if resistance:
            stop_loss = resistance * 1.005  # 阻力位上方 0.5%
            stop_method = "阻力位上方"
        else:
            stop_loss = current_price + (atr * 1.5)
            stop_method = "1.5 ATR"
    
    else:
        stop_loss = None
        stop_method = "N/A"
    
    recommendation['stop_loss'] = stop_loss
    recommendation['stop_method'] = stop_method
    
    # 4. 止盈位 (下一個流動性區域)
    if direction == '做多 (Long)':
        if resistance:
            take_profit = resistance * 0.998  # 阻力位前
            tp_method = "阻力位前"
        else:
            take_profit = current_price + (atr * 3)
            tp_method = "3 ATR"
    
    elif direction == '做空 (Short)':
        if support:
            take_profit = support * 1.002  # 支撐位前
            tp_method = "支撐位前"
        else:
            take_profit = current_price - (atr * 3)
            tp_method = "3 ATR"
    
    else:
        take_profit = None
        tp_method = "N/A"
    
    recommendation['take_profit'] = take_profit
    recommendation['tp_method'] = tp_method
    
    # 5. 計算盈虧比
    if stop_loss and take_profit and direction != '觀望 (Wait)':
        risk = abs(current_price - stop_loss)
        reward = abs(take_profit - current_price)
        risk_reward = reward / risk if risk > 0 else 0
        
        recommendation['risk_reward'] = risk_reward
        recommendation['risk_amount'] = risk
        recommendation['reward_amount'] = reward
    else:
        recommendation['risk_reward'] = None
    
    # 6. 多時區趨勢一致性
    recommendation['trend_alignment'] = {
        'bullish_count': bullish_count,
        'bearish_count': bearish_count,
        'total_timeframes': len(trends),
        'trends': trends
    }
    
    # 7. 關鍵技術指標
    recommendation['key_indicators'] = {
        'rsi': rsi,
        'rsi_state': primary_data.get('rsi_state', 'unknown'),
        'macd_state': macd_state,
        'atr': atr,
        'atr_pct': atr_pct,
        'volatility': primary_data.get('volatility', 'unknown')
    }
    
    # 8. 支撐阻力
    recommendation['support_resistance'] = {
        'support': support,
        'resistance': resistance,
        'distance_to_support': primary_data.get('support_resistance', {}).get('distance_to_support'),
        'distance_to_resistance': primary_data.get('support_resistance', {}).get('distance_to_resistance')
    }
    
    # 9. CMT Level 3 專業分析
    recommendation['professional_analysis'] = generate_cmt_analysis(
        multi_tf, current_price, primary_data, trends, rsi, macd_state
    )
    
    return recommendation


def generate_cmt_analysis(multi_tf: dict, current_price: float, primary_data: dict, 
                          trends: dict, rsi: float, macd_state: str) -> dict:
    """
    生成 CMT Level 3 專業分析
    
    包含：
    1. 大級別趨勢判斷（1H/4H）
    2. 市場結構分析（Higher Highs/Lower Lows）
    3. K線反轉信號識別
    4. 進場理由評估（順勢/逆勢）
    5. 具體進場計劃
    """
    
    analysis = {}
    
    # 1. 大級別趨勢判斷（1H/4H）
    h4_trend = trends.get('4h', 'unknown')
    h1_trend = trends.get('1h', 'unknown')
    
    if 'strong_uptrend' in h4_trend or 'strong_uptrend' in h1_trend:
        major_trend = "強勢上漲"
        major_trend_desc = "EMA 多頭排列，價格持續創新高"
        trend_type = "uptrend"
    elif 'uptrend' in h4_trend or 'uptrend' in h1_trend:
        major_trend = "上漲趨勢"
        major_trend_desc = "價格在主要均線上方運行"
        trend_type = "uptrend"
    elif 'strong_downtrend' in h4_trend or 'strong_downtrend' in h1_trend:
        major_trend = "強勢下跌"
        major_trend_desc = "EMA 空頭排列，價格持續創新低"
        trend_type = "downtrend"
    elif 'downtrend' in h4_trend or 'downtrend' in h1_trend:
        major_trend = "下跌趨勢"
        major_trend_desc = "價格在主要均線下方運行"
        trend_type = "downtrend"
    else:
        major_trend = "區間震盪"
        major_trend_desc = "價格在支撐阻力區間內來回波動"
        trend_type = "sideways"
    
    analysis['major_trend'] = major_trend
    analysis['major_trend_desc'] = major_trend_desc
    analysis['trend_type'] = trend_type
    
    # 2. 開倉理由判斷
    m15_trend = trends.get('15m', 'unknown')
    m5_trend = trends.get('5m', 'unknown')
    
    # 判斷是順勢還是逆勢
    if trend_type == "uptrend":
        if 'uptrend' in m15_trend or 'uptrend' in m5_trend:
            entry_reason = "順勢回調"
            entry_reason_desc = "大級別上漲，小級別回調後繼續做多"
            entry_validity = "有效"
        elif 'downtrend' in m15_trend or 'downtrend' in m5_trend:
            entry_reason = "逆勢摸頂"
            entry_reason_desc = "⚠️ 大級別上漲時做空，風險較高"
            entry_validity = "高風險"
        else:
            entry_reason = "等待信號"
            entry_reason_desc = "小級別未出現明確方向"
            entry_validity = "觀望"
    elif trend_type == "downtrend":
        if 'downtrend' in m15_trend or 'downtrend' in m5_trend:
            entry_reason = "順勢回調"
            entry_reason_desc = "大級別下跌，小級別反彈後繼續做空"
            entry_validity = "有效"
        elif 'uptrend' in m15_trend or 'uptrend' in m5_trend:
            entry_reason = "逆勢摸底"
            entry_reason_desc = "⚠️ 大級別下跌時做多，風險較高"
            entry_validity = "高風險"
        else:
            entry_reason = "等待信號"
            entry_reason_desc = "小級別未出現明確方向"
            entry_validity = "觀望"
    else:
        entry_reason = "區間交易"
        entry_reason_desc = "在支撐買入，在阻力賣出"
        entry_validity = "中性"
    
    analysis['entry_reason'] = entry_reason
    analysis['entry_reason_desc'] = entry_reason_desc
    analysis['entry_validity'] = entry_validity
    
    # 3. K線反轉信號（基於 RSI 和 MACD）
    reversal_signals = []
    
    # RSI 超買超賣
    if rsi > 70:
        reversal_signals.append("RSI 超買 (>70)")
    elif rsi < 30:
        reversal_signals.append("RSI 超賣 (<30)")
    
    # MACD 金叉死叉
    if 'golden_cross' in macd_state:
        reversal_signals.append("MACD 金叉（看多信號）")
    elif 'death_cross' in macd_state:
        reversal_signals.append("MACD 死叉（看空信號）")
    
    # 判斷是否有明確信號
    if len(reversal_signals) > 0:
        has_reversal = True
        reversal_desc = "、".join(reversal_signals)
    else:
        has_reversal = False
        reversal_desc = "⚠️ 無明確反轉信號，建議空倉等待"
    
    analysis['has_reversal_signal'] = has_reversal
    analysis['reversal_signals'] = reversal_desc
    
    # 4. 市場結構分析
    if trend_type == "uptrend":
        market_structure = "Higher Highs (多頭結構)"
        structure_desc = "價格持續創新高，回調不破前低"
    elif trend_type == "downtrend":
        market_structure = "Lower Lows (空頭結構)"
        structure_desc = "價格持續創新低，反彈不破前高"
    else:
        market_structure = "區間震盪 (Range)"
        structure_desc = "價格在支撐阻力區間內波動"
    
    analysis['market_structure'] = market_structure
    analysis['structure_desc'] = structure_desc
    
    # 5. 布林帶分析
    bb_position = primary_data.get('bb_position', 'unknown')
    
    if bb_position == 'above_upper':
        bb_analysis = "價格突破上軌，可能超買"
        bb_signal = "警惕回調"
    elif bb_position == 'below_lower':
        bb_analysis = "價格跌破下軌，可能超賣"
        bb_signal = "警惕反彈"
    elif bb_position == 'upper_half':
        bb_analysis = "價格在上半部，偏強勢"
        bb_signal = "可持有多單"
    elif bb_position == 'lower_half':
        bb_analysis = "價格在下半部，偏弱勢"
        bb_signal = "可持有空單"
    else:
        bb_analysis = "價格在中軌附近"
        bb_signal = "等待方向選擇"
    
    analysis['bb_analysis'] = bb_analysis
    analysis['bb_signal'] = bb_signal
    
    # 6. 動能分析
    if 'bullish' in macd_state or 'golden' in macd_state:
        momentum = "動能增強（看多）"
    elif 'bearish' in macd_state or 'death' in macd_state:
        momentum = "動能減弱（看空）"
    else:
        momentum = "動能中性"
    
    analysis['momentum'] = momentum
    
    # 7. 綜合評估
    if entry_validity == "有效" and has_reversal:
        overall_assessment = "✅ 符合進場條件"
        assessment_color = "success"
    elif entry_validity == "高風險":
        overall_assessment = "⚠️ 逆勢交易，風險極高，建議空倉"
        assessment_color = "warning"
    elif not has_reversal:
        overall_assessment = "❌ 無明確信號，建議空倉等待"
        assessment_color = "error"
    else:
        overall_assessment = "⏸️ 觀望，等待更好機會"
        assessment_color = "info"
    
    analysis['overall_assessment'] = overall_assessment
    analysis['assessment_color'] = assessment_color
    
    return analysis


def render_timeframe_analysis(timeframe: str, tf_data: dict, symbol: str):
    """渲染單個時區的詳細分析"""
    
    # 獲取數據
    price = tf_data.get('price', 0)
    trend = tf_data.get('trend', 'unknown')
    rsi = tf_data.get('rsi', 50)
    rsi_state = tf_data.get('rsi_state', 'unknown')
    macd_state = tf_data.get('macd_state', 'unknown')
    atr = tf_data.get('atr', 0)
    atr_pct = tf_data.get('atr_pct', 0)
    volatility = tf_data.get('volatility', 'unknown')
    support_resistance = tf_data.get('support_resistance', {})
    
    # 獲取型態識別數據
    patterns = tf_data.get('patterns', [])
    pattern_alerts = tf_data.get('pattern_alerts', [])
    
    # 趨勢顏色
    if 'uptrend' in trend:
        trend_color = '🟢'
        trend_bg = '#d4edda'  # 綠色背景（更深）
    elif 'downtrend' in trend:
        trend_color = '🔴'
        trend_bg = '#f8d7da'  # 紅色背景（更深，更容易看清）
    else:
        trend_color = '⚪'
        trend_bg = '#e2e3e5'  # 灰色背景（更深）
    
    # 顯示趨勢
    st.markdown(f"""
    <div style="background-color: {trend_bg}; padding: 15px; border-radius: 8px; margin-bottom: 15px;">
        <h3>{trend_color} 趨勢：{trend}</h3>
        <p style="margin: 0;"><strong>價格：</strong>${price:.2f}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 顯示型態警報（如果有）
    if pattern_alerts:
        st.markdown("### 🚨 K線型態警報")
        for alert in pattern_alerts:
            # 根據型態類型選擇顏色
            if '避雷針' in alert or '假突破' in alert:
                st.warning(alert)
            elif '頭肩' in alert or '雙頂' in alert or '雙底' in alert:
                st.info(alert)
            else:
                st.success(alert)
    
    # 添加K線圖和技術指標
    st.markdown("---")
    st.subheader(f"📊 {timeframe} K線圖與技術指標")
    
    try:
        from src.analysis.market_analyzer import MarketAnalyzer
        from plotly.subplots import make_subplots
        import plotly.graph_objects as go
        
        analyzer = MarketAnalyzer()
        df = analyzer.load_market_data(symbol, timeframe)
        
        if df is not None and len(df) > 0:
            # 確保有技術指標
            if 'ema_12' not in df.columns:
                df = analyzer.calculate_indicators(df)
            
            # 只顯示最近100根K線
            df_display = df.tail(100).copy()
            
            # 調試信息
            st.caption(f"數據範圍：{df_display['timestamp'].min()} 至 {df_display['timestamp'].max()}，共 {len(df_display)} 根K線")
            
            # 創建子圖
            fig = make_subplots(
                rows=5, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.03,
                row_heights=[0.4, 0.15, 0.15, 0.15, 0.15],
                subplot_titles=(
                    f'{symbol} {timeframe} K線圖 + EMA + 布林帶',
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
            
            # 標記型態（如果有）
            if patterns:
                for pattern in patterns:
                    # 找到對應的K線索引
                    pattern_idx = df_display[df_display['timestamp'] == pattern.timestamp].index
                    if len(pattern_idx) > 0:
                        idx = pattern_idx[0]
                        
                        # 根據型態類型決定顏色和位置
                        if '避雷針' in pattern.description or '假突破' in pattern.description:
                            marker_color = '#ff0000'
                            # 避雷針和假突破標記在高點上方
                            marker_y = df_display.loc[idx, 'high'] * 1.002  # 高點上方 0.2%
                            text_position = 'top center'
                        elif '倒錘子' in pattern.description or '假跌破' in pattern.description:
                            marker_color = '#00ff00'
                            # 倒錘子和假跌破標記在低點下方
                            marker_y = df_display.loc[idx, 'low'] * 0.998  # 低點下方 0.2%
                            text_position = 'bottom center'
                        else:
                            marker_color = '#ffa500'
                            marker_y = pattern.price
                            text_position = 'top center'
                        
                        fig.add_trace(
                            go.Scatter(
                                x=[df_display.loc[idx, 'timestamp']],
                                y=[marker_y],
                                mode='text',  # 只顯示文字，不顯示標記點
                                name=pattern.pattern_type.value,
                                text=[pattern.emoji],
                                textposition=text_position,
                                textfont=dict(
                                    size=16,
                                    color=marker_color
                                ),
                                showlegend=True,
                                hovertemplate=f"<b>{pattern.description}</b><br>強度: {pattern.strength:.0f}<extra></extra>"
                            ),
                            row=1, col=1
                        )
            
            # 繪製支撐阻力線
            if support_resistance.get('support'):
                support_price = support_resistance['support']
                # 繪製支撐線（帶標註）
                fig.add_hline(
                    y=support_price,
                    line_dash="dash",
                    line_color="green",
                    line_width=2,
                    annotation_text=f"支撐 ${support_price:.2f}",
                    annotation_position="right",
                    annotation_font_size=10,
                    annotation_font_color="green",
                    annotation_bgcolor="rgba(255,255,255,0.8)",
                    row=1, col=1,
                    opacity=0.7
                )
            
            if support_resistance.get('resistance'):
                resistance_price = support_resistance['resistance']
                # 繪製阻力線（帶標註）
                fig.add_hline(
                    y=resistance_price,
                    line_dash="dash",
                    line_color="red",
                    line_width=2,
                    annotation_text=f"阻力 ${resistance_price:.2f}",
                    annotation_position="right",
                    annotation_font_size=10,
                    annotation_font_color="red",
                    annotation_bgcolor="rgba(255,255,255,0.8)",
                    row=1, col=1,
                    opacity=0.7
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
            if 'volume_sma' in df_display.columns:
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
            
        else:
            st.warning(f"⚠️ 無法載入 {symbol} {timeframe} 的K線數據")
    
    except Exception as e:
        st.error(f"❌ 載入圖表失敗：{str(e)}")
        import traceback
        with st.expander("查看錯誤詳情"):
            st.code(traceback.format_exc())
    
    st.markdown("---")
    
    # 進場計劃
    st.subheader("📍 進場計劃")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # 基於趨勢的進場建議
        if 'uptrend' in trend:
            if rsi < 40:
                entry_plan = f"現價 ${price:.2f} (RSI 超賣，反彈機會)"
            elif support_resistance.get('support'):
                support = support_resistance['support']
                entry_plan = f"等待回調至 ${support * 1.002:.2f} (支撐位附近)"
            else:
                entry_plan = f"現價 ${price:.2f} (上升趨勢)"
        elif 'downtrend' in trend:
            if rsi > 60:
                entry_plan = f"現價 ${price:.2f} (RSI 超買，回調機會)"
            elif support_resistance.get('resistance'):
                resistance = support_resistance['resistance']
                entry_plan = f"等待反彈至 ${resistance * 0.998:.2f} (阻力位附近)"
            else:
                entry_plan = f"現價 ${price:.2f} (下降趨勢)"
        else:
            entry_plan = "觀望，等待明確趨勢"
        
        st.info(f"**建議：** {entry_plan}")
    
    with col2:
        # 止損建議
        if 'uptrend' in trend:
            if support_resistance.get('support'):
                stop_loss = support_resistance['support'] * 0.995
                stop_method = "支撐位下方"
            else:
                stop_loss = price - (atr * 1.5)
                stop_method = "1.5 ATR"
            st.warning(f"**止損：** ${stop_loss:.2f}\n\n({stop_method})")
        elif 'downtrend' in trend:
            if support_resistance.get('resistance'):
                stop_loss = support_resistance['resistance'] * 1.005
                stop_method = "阻力位上方"
            else:
                stop_loss = price + (atr * 1.5)
                stop_method = "1.5 ATR"
            st.warning(f"**止損：** ${stop_loss:.2f}\n\n({stop_method})")
        else:
            st.info("**止損：** 等待信號")
    
    # 關鍵技術指標
    st.subheader("📈 關鍵技術指標")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        rsi_color = 'inverse' if rsi > 70 or rsi < 30 else 'off'
        st.metric("RSI", f"{rsi:.1f}", delta=rsi_state, delta_color=rsi_color)
    
    with col2:
        macd_emoji = '🟢' if 'bullish' in macd_state or 'golden' in macd_state else '🔴' if 'bearish' in macd_state or 'death' in macd_state else '⚪'
        st.metric("MACD", macd_emoji, delta=macd_state)
    
    with col3:
        st.metric("ATR", f"{atr:.2f}", delta=f"{atr_pct:.2f}%")
    
    with col4:
        st.metric("波動率", volatility)
    
    # 支撐與阻力
    if support_resistance.get('support') or support_resistance.get('resistance'):
        st.subheader("🎯 支撐與阻力")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if support_resistance.get('support'):
                support = support_resistance['support']
                dist = support_resistance.get('distance_to_support')
                st.metric(
                    "支撐位", 
                    f"${support:.2f}",
                    delta=f"距離 {dist:.2f}%" if dist is not None else None
                )
        
        with col2:
            if support_resistance.get('resistance'):
                resistance = support_resistance['resistance']
                dist = support_resistance.get('distance_to_resistance')
                st.metric(
                    "阻力位", 
                    f"${resistance:.2f}",
                    delta=f"距離 {dist:.2f}%" if dist is not None else None
                )
        
        # 顯示支撐阻力有效性分析
        try:
            from src.analysis.market_analyzer import MarketAnalyzer
            analyzer = MarketAnalyzer()
            sr_analysis = analyzer.analyze_support_resistance_strength(symbol, timeframe)
            
            if sr_analysis:
                with st.expander("📊 支撐阻力有效性分析"):
                    st.markdown("### 支撐位強度")
                    for sr_info in sr_analysis.get('supports', [])[:3]:  # 顯示前3個
                        strength_bar = "🟢" * int(sr_info['strength'] / 20)
                        st.markdown(f"""
                        **${sr_info['level']:.2f}**
                        - 觸碰次數：{sr_info['touches']} 次
                        - 強度：{strength_bar} {sr_info['strength']:.0f}/100
                        - 距離：{sr_info['distance_pct']:.2f}%
                        """)
                    
                    st.markdown("### 阻力位強度")
                    for sr_info in sr_analysis.get('resistances', [])[:3]:  # 顯示前3個
                        strength_bar = "🔴" * int(sr_info['strength'] / 20)
                        st.markdown(f"""
                        **${sr_info['level']:.2f}**
                        - 觸碰次數：{sr_info['touches']} 次
                        - 強度：{strength_bar} {sr_info['strength']:.0f}/100
                        - 距離：{sr_info['distance_pct']:.2f}%
                        """)
        except Exception as e:
            pass  # 如果分析失敗，不顯示
    
    # 詳細技術指標
    with st.expander("🔍 查看更多技術指標"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**移動平均線 (EMA)**")
            ema_7 = tf_data.get('ema_7', 0)
            ema_20 = tf_data.get('ema_20', 0)
            ema_50 = tf_data.get('ema_50', 0)
            if ema_7 > 0:
                st.text(f"EMA7:  ${ema_7:.2f}")
            if ema_20 > 0:
                st.text(f"EMA20: ${ema_20:.2f}")
            if ema_50 > 0:
                st.text(f"EMA50: ${ema_50:.2f}")
            
            ma_alignment = tf_data.get('ma_alignment', 'unknown')
            if ma_alignment != 'unknown':
                st.text(f"排列: {ma_alignment}")
        
        with col2:
            st.markdown("**MACD 詳細**")
            macd = tf_data.get('macd', 0)
            macd_signal = tf_data.get('macd_signal', 0)
            macd_hist = tf_data.get('macd_hist', 0)
            if macd != 0:
                st.text(f"MACD:   {macd:.2f}")
                st.text(f"Signal: {macd_signal:.2f}")
                st.text(f"Hist:   {macd_hist:.2f}")
        
        st.markdown("**成交量**")
        volume = tf_data.get('volume', 0)
        volume_ratio = tf_data.get('volume_ratio', 0)
        volume_state = tf_data.get('volume_state', 'unknown')
        if volume > 0:
            st.text(f"成交量: {volume:.2f}")
            st.text(f"比率: {volume_ratio:.2f}x ({volume_state})")
        
        st.markdown("**布林帶**")
        bb_position = tf_data.get('bb_position', 'unknown')
        if bb_position != 'unknown':
            st.text(f"位置: {bb_position}")


def render_recommendation_card(rec: dict):
    """渲染綜合交易建議卡片（簡化版）"""
    
    # 當前價格（來自 1m）
    current_price = rec['current_price']
    price_source = rec.get('price_source', '1m')
    
    st.markdown(f"""
    <div style="background-color: #e3f2fd; padding: 20px; border-radius: 10px; border-left: 5px solid #2196f3;">
        <h2>💰 當前價格：${current_price:.2f}</h2>
        <p><strong>價格來源：</strong>{price_source} 時區（最即時）</p>
        <p><strong>分析時間：</strong>{rec['analysis_time']}</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # 方向顏色
    if '做多' in rec['direction']:
        direction_color = '🟢'
        bg_color = '#d4edda'  # 綠色背景（更深）
        border_color = '#28a745'
    elif '做空' in rec['direction']:
        direction_color = '🔴'
        bg_color = '#f8d7da'  # 紅色背景（更深，更容易看清）
        border_color = '#dc3545'
    else:
        direction_color = '⚪'
        bg_color = '#e2e3e5'  # 灰色背景（更深）
        border_color = '#6c757d'
    
    # 信心度
    confidence_map = {
        'high': '⭐⭐⭐ 高',
        'medium': '⭐⭐ 中',
        'low': '⭐ 低'
    }
    confidence_text = confidence_map.get(rec['confidence'], rec['confidence'])
    
    # 獲取多空力量差距
    net_bullish = rec.get('net_bullish', 0)
    if net_bullish > 0:
        force_text = f"多頭優勢 +{net_bullish}"
        force_color = "#28a745"
    elif net_bullish < 0:
        force_text = f"空頭優勢 {net_bullish}"
        force_color = "#dc3545"
    else:
        force_text = "多空均衡"
        force_color = "#6c757d"
    
    st.markdown(f"""
    <div style="background-color: {bg_color}; padding: 20px; border-radius: 10px; border-left: 5px solid {border_color};">
        <h2>{direction_color} 綜合建議：{rec['direction']}</h2>
        <p><strong>信心度：</strong>{confidence_text}</p>
        <p><strong>多空力量：</strong><span style="color: {force_color}; font-weight: bold;">{force_text}</span></p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # 多時區趨勢一致性
    st.subheader("📊 多時區趨勢一致性")
    
    trend_align = rec['trend_alignment']
    trends = trend_align['trends']
    
    # 趨勢表格
    trend_data = []
    for tf, trend in trends.items():
        emoji = '🟢' if 'uptrend' in trend else '🔴' if 'downtrend' in trend else '⚪'
        trend_data.append({
            '時區': tf,
            '趨勢': f"{emoji} {trend}",
        })
    
    if trend_data:
        df_trends = pd.DataFrame(trend_data)
        st.dataframe(df_trends, use_container_width=True, hide_index=True)
    
    # 一致性指標
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("看多時區", f"{trend_align['bullish_count']}/{trend_align['total_timeframes']}")
    with col2:
        st.metric("看空時區", f"{trend_align['bearish_count']}/{trend_align['total_timeframes']}")
    with col3:
        # 顯示多空力量差距
        delta_color = "normal" if net_bullish > 0 else "inverse" if net_bullish < 0 else "off"
        st.metric("力量差距", f"{net_bullish:+d}", delta_color=delta_color)
    with col4:
        alignment_pct = max(trend_align['bullish_count'], trend_align['bearish_count']) / trend_align['total_timeframes'] * 100
        st.metric("一致性", f"{alignment_pct:.0f}%")
    
    st.markdown("---")
    
    # CMT Level 3 專業分析
    if 'professional_analysis' in rec:
        st.subheader("🎓 CMT Level 3 專業分析")
        
        prof = rec['professional_analysis']
        
        # 1. 大級別趨勢
        st.markdown("### 📊 1H/4H 大級別趨勢")
        
        trend_color = "#28a745" if prof['trend_type'] == "uptrend" else "#dc3545" if prof['trend_type'] == "downtrend" else "#6c757d"
        
        st.markdown(f"""
        <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 4px solid {trend_color};">
            <p style="margin: 0;"><strong>趨勢判斷：</strong><span style="color: {trend_color}; font-weight: bold;">{prof['major_trend']}</span></p>
            <p style="margin: 5px 0 0 0; color: #6c757d;">{prof['major_trend_desc']}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # 2. 開倉理由
        st.markdown("### 🎯 開倉理由評估")
        
        validity_color = "#28a745" if prof['entry_validity'] == "有效" else "#dc3545" if prof['entry_validity'] == "高風險" else "#ffc107"
        
        col1, col2 = st.columns([1, 2])
        with col1:
            st.metric("進場類型", prof['entry_reason'])
        with col2:
            st.markdown(f"""
            <div style="background-color: #f8f9fa; padding: 10px; border-radius: 5px; border-left: 3px solid {validity_color};">
                <p style="margin: 0; color: {validity_color}; font-weight: bold;">評估：{prof['entry_validity']}</p>
                <p style="margin: 5px 0 0 0; font-size: 0.9em;">{prof['entry_reason_desc']}</p>
            </div>
            """, unsafe_allow_html=True)
        
        # 3. K線反轉信號
        st.markdown("### 📈 15m/5m 入場級別信號")
        
        if prof['has_reversal_signal']:
            st.success(f"✅ 發現反轉信號：{prof['reversal_signals']}")
        else:
            st.error(f"❌ {prof['reversal_signals']}")
        
        # 4. 市場結構
        st.markdown("### 🏗️ 市場結構分析")
        
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"**結構類型**\n\n{prof['market_structure']}")
        with col2:
            st.info(f"**結構描述**\n\n{prof['structure_desc']}")
        
        # 5. 技術指標分析
        st.markdown("### 📉 技術指標分析")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"""
            **布林帶位置**
            
            {prof['bb_analysis']}
            
            💡 {prof['bb_signal']}
            """)
        with col2:
            st.markdown(f"""
            **動能分析**
            
            {prof['momentum']}
            """)
        with col3:
            # 顯示 RSI 和 MACD 狀態
            key_indicators = rec.get('key_indicators', {})
            st.markdown(f"""
            **關鍵指標**
            
            RSI: {key_indicators.get('rsi', 0):.1f}
            
            MACD: {key_indicators.get('macd_state', 'unknown')}
            """)
        
        # 6. 綜合評估
        st.markdown("### ✅ 綜合評估")
        
        assessment_color_map = {
            'success': 'success',
            'warning': 'warning',
            'error': 'error',
            'info': 'info'
        }
        
        assessment_func = getattr(st, assessment_color_map.get(prof['assessment_color'], 'info'))
        assessment_func(prof['overall_assessment'])
        
        # 7. 專業交易計劃
        st.markdown("### 📋 專業交易計劃")
        
        support = rec['support_resistance'].get('support')
        resistance = rec['support_resistance'].get('resistance')
        stop_loss = rec.get('stop_loss')
        take_profit = rec.get('take_profit')
        risk_reward = rec.get('risk_reward')
        
        # 安全獲取值，確保不為 None
        current_price = rec.get('current_price') or 0
        entry_suggestion = rec.get('entry_suggestion') or '等待信號'
        stop_method = rec.get('stop_method') or 'N/A'
        tp_method = rec.get('tp_method') or 'N/A'
        
        # 格式化價格（None 顯示為 N/A）
        def format_price(value):
            return f"${value:.2f}" if value is not None else "N/A"
        
        def format_percentage(value):
            return f"{value:.2f}%" if value is not None else "N/A"
        
        def format_number(value, decimals=2):
            return f"{value:.{decimals}f}" if value is not None else "N/A"
        
        # 計算止損距離
        if stop_loss and current_price:
            stop_distance = abs(current_price - stop_loss)
            stop_distance_pct = stop_distance / current_price * 100
        else:
            stop_distance = None
            stop_distance_pct = None
        
        # 計算建議倉位
        if stop_loss and current_price and stop_distance and stop_distance > 0:
            position_size = 200 / stop_distance
        else:
            position_size = None
        
        # 獲取距離值
        dist_to_support = rec['support_resistance'].get('distance_to_support')
        dist_to_resistance = rec['support_resistance'].get('distance_to_resistance')
        
        # 盈虧比評估
        if risk_reward and risk_reward > 2:
            rr_assessment = '✅ 優秀 (>2.0)'
        elif risk_reward and risk_reward > 1.5:
            rr_assessment = '✅ 良好 (>1.5)'
        elif risk_reward:
            rr_assessment = '⚠️ 一般 (<1.5)'
        else:
            rr_assessment = 'N/A'
        
        st.markdown(f"""
        **進場區間**：
        - 當前價格：${current_price:.2f}
        - 建議進場：{entry_suggestion}
        
        **止損價格** (觸發後必須無條件執行)：
        - 止損位：{format_price(stop_loss)} ({stop_method})
        - 止損距離：{format_price(stop_distance)} ({format_percentage(stop_distance_pct)})
        
        **止盈價格**：
        - 第一止盈位（平倉 50%）：{format_price(take_profit)} ({tp_method})
        - 第二止盈位（推保護止損）：建議在第一止盈後，將止損移至成本價
        
        **盈虧比 (R/R)**：
        - 盈虧比：{format_number(risk_reward)}
        - 評估：{rr_assessment}
        
        **關鍵價位**：
        - 支撐位：{format_price(support)} (距離 {format_percentage(dist_to_support)})
        - 阻力位：{format_price(resistance)} (距離 {format_percentage(dist_to_resistance)})
        
        **建議倉位**：
        - 基於 2% 風險管理原則
        - 單筆最大虧損 = 總資金 × 2%
        - 建議倉位 = (總資金 × 2%) ÷ 止損金額
        - 例如：10,000 USDT 本金 → 最大虧損 200 USDT → 倉位 = 200 ÷ {format_price(stop_distance)} = {format_number(position_size, 4)} 單位
        """)


def render():
    """渲染實時市場分析頁面"""
    
    st.title("📊 實時市場分析")
    st.caption("機構級技術分析 (CMT Level 3)")
    
    if not MARKET_ANALYZER_AVAILABLE:
        st.error(f"❌ 無法載入 MarketAnalyzer：{IMPORT_ERROR}")
        return
    
    # 輸入區域
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    
    with col1:
        symbol = st.text_input(
            "交易對",
            value="BTCUSDT",
            help="輸入交易對，例如：BTCUSDT, ETHUSDT"
        ).upper()
    
    with col2:
        auto_refresh = st.checkbox("自動刷新", value=False)
        if auto_refresh:
            auto_update_data = st.checkbox(
                "同時更新數據",
                value=False,
                help="勾選後每次刷新時會先更新所有 7 個時區數據（1m, 3m, 5m, 15m, 1h, 4h, 1d）"
            )
    
    with col3:
        if auto_refresh:
            refresh_interval = st.number_input("刷新間隔(秒)", min_value=10, max_value=300, value=60)
    
    with col4:
        # 一鍵更新數據按鈕
        if st.button("🔄 更新數據", help="強制更新所有時區的市場數據到最新"):
            with st.spinner("正在更新數據..."):
                try:
                    analyzer = MarketAnalyzer()
                    # 強制更新所有時區（包括 1m）
                    intervals = ['1d', '4h', '1h', '15m', '5m', '3m', '1m']
                    
                    update_results = []
                    for interval in intervals:
                        try:
                            # 獲取現有數據
                            normalized_symbol = symbol.replace('-', '').upper()
                            filename = Path(f'market_data_{normalized_symbol}_{interval}.csv')
                            
                            # 讀取現有數據以獲取最後時間
                            if filename.exists():
                                df_old = pd.read_csv(filename)
                                df_old['timestamp'] = pd.to_datetime(df_old['timestamp'])
                                last_time = df_old['timestamp'].max()
                            else:
                                # 如果文件不存在，從 90 天前開始
                                last_time = datetime.now() - timedelta(days=90)
                            
                            # 強制更新：從最後時間到現在
                            end_time = datetime.now()
                            
                            # 調用內部方法強制下載新數據
                            new_data = analyzer._fetch_binance_klines(
                                normalized_symbol,
                                interval,
                                last_time,
                                end_time
                            )
                            
                            if new_data is not None and len(new_data) > 0:
                                # 合併數據
                                if filename.exists():
                                    df_combined = pd.concat([df_old, new_data], ignore_index=True)
                                    df_combined = df_combined.drop_duplicates(subset=['timestamp'], keep='last')
                                    df_combined = df_combined.sort_values('timestamp').reset_index(drop=True)
                                else:
                                    df_combined = new_data
                                
                                # 保存
                                df_combined.to_csv(filename, index=False)
                                
                                latest_time = df_combined['timestamp'].max()
                                update_results.append(f"✅ {interval}: {latest_time}")
                            else:
                                update_results.append(f"⚠️ {interval}: 無新數據")
                        except Exception as e:
                            update_results.append(f"❌ {interval}: {str(e)[:50]}")
                    
                    # 顯示結果
                    st.success("✅ 數據更新完成！")
                    with st.expander("查看更新結果"):
                        for result in update_results:
                            st.text(result)
                    
                    # 自動重新分析
                    st.info("💡 數據已更新，請點擊「開始分析」查看最新結果")
                    
                except Exception as e:
                    st.error(f"❌ 更新失敗：{e}")
                    import traceback
                    with st.expander("查看錯誤詳情"):
                        st.code(traceback.format_exc())
    
    # 分析按鈕
    if st.button("🔍 開始分析", type="primary", use_container_width=True) or auto_refresh:
        
        # 如果啟用了自動更新數據
        if auto_refresh and 'auto_update_data' in locals() and auto_update_data:
            update_status = st.empty()
            update_status.info("🔄 正在更新數據...")
            
            try:
                analyzer_temp = MarketAnalyzer()
                
                # 快速更新所有時區
                intervals_to_update = ['1d', '4h', '1h', '15m', '5m', '3m', '1m']
                for interval in intervals_to_update:
                    try:
                        # 獲取現有數據
                        normalized_symbol = symbol.replace('-', '').upper()
                        filename = Path(f'market_data_{normalized_symbol}_{interval}.csv')
                        
                        # 讀取現有數據
                        if filename.exists():
                            df_old = pd.read_csv(filename)
                            df_old['timestamp'] = pd.to_datetime(df_old['timestamp'])
                            last_time = df_old['timestamp'].max()
                        else:
                            last_time = datetime.now() - timedelta(days=90)
                        
                        # 強制下載新數據
                        end_time = datetime.now()
                        new_data = analyzer_temp._fetch_binance_klines(
                            normalized_symbol,
                            interval,
                            last_time,
                            end_time
                        )
                        
                        if new_data is not None and len(new_data) > 0:
                            # 合併並保存
                            if filename.exists():
                                df_combined = pd.concat([df_old, new_data], ignore_index=True)
                                df_combined = df_combined.drop_duplicates(subset=['timestamp'], keep='last')
                                df_combined = df_combined.sort_values('timestamp').reset_index(drop=True)
                            else:
                                df_combined = new_data
                            
                            df_combined.to_csv(filename, index=False)
                    except:
                        pass  # 忽略錯誤，繼續更新其他時區
                
                update_status.success("✅ 數據已更新")
                time.sleep(0.5)  # 短暫顯示成功消息
                update_status.empty()  # 清除消息
            except Exception as e:
                update_status.warning(f"⚠️ 數據更新失敗：{e}")
                time.sleep(1)
                update_status.empty()
        
        # 分析狀態
        analysis_status = st.empty()
        
        try:
            # 創建分析器
            analyzer = MarketAnalyzer()
            
            # 獲取當前時間的市場分析
            current_time = datetime.now()
            
            # 分析所有時區（從長到短）
            intervals = ['1d', '4h', '1h', '15m', '5m', '3m', '1m']
            
            # 使用臨時狀態顯示分析進度
            analysis_status.info(f"📊 正在分析 {symbol} 的 {len(intervals)} 個時區：{', '.join(intervals)}")
            
            # 分析多個時區
            analysis = analyzer.analyze_market_at_time(
                symbol=symbol,
                timestamp=current_time,
                intervals=intervals
            )
            
            if not analysis:
                analysis_status.empty()  # 清除分析狀態
                st.error(f"❌ 無法獲取 {symbol} 的市場數據")
                st.info("""
                請確認：
                1. 交易對名稱正確
                2. 已下載市場數據
                3. 數據是最新的（建議更新數據）
                
                **更新數據方式**：
                - 方式 1：重新運行分析（系統會自動更新）
                - 方式 2：使用「數據管理」功能更新
                """)
                return
            
            # 生成交易建議
            recommendation = calculate_trading_recommendation(analysis, symbol)
            
            if not recommendation:
                analysis_status.empty()  # 清除分析狀態
                st.error("❌ 無法生成交易建議")
                return
            
            # 清除分析狀態消息
            analysis_status.empty()
            
            # 顯示交易建議
            render_recommendation_card(recommendation)
            
            st.markdown("---")
            st.markdown("## 📊 各時區詳細分析")
            st.caption("從長期到短期，每個時區的獨立分析")
            
            # 為每個時區創建獨立的分析卡片
            multi_tf = analysis.get('multi_timeframe', {})
            
            # 檢查哪些時區有數據
            available_timeframes = list(multi_tf.keys())
            all_timeframes = ['1d', '4h', '1h', '15m', '5m', '3m', '1m']
            missing_timeframes = [tf for tf in all_timeframes if tf not in available_timeframes]
            
            # 顯示數據狀態
            col1, col2 = st.columns(2)
            with col1:
                st.success(f"✅ 可用時區：{', '.join(available_timeframes)}")
            with col2:
                if missing_timeframes:
                    st.warning(f"⚠️ 缺少時區：{', '.join(missing_timeframes)}")
                    with st.expander("💡 如何獲取缺少的時區數據？"):
                        st.info("""
                        **方式 1：自動更新（推薦）**
                        - 重新點擊「開始分析」按鈕
                        - 系統會自動下載缺少的數據
                        
                        **方式 2：手動下載**
                        - 進入「數據管理」→「歷史數據下載」
                        - 選擇缺少的時區
                        - 點擊「開始下載」
                        
                        **方式 3：命令行**
                        ```bash
                        python3 重新下載市場數據_修正時區.py
                        ```
                        """)
                else:
                    st.success("✅ 所有時區數據完整")
            
            st.markdown("---")
            
            # 按時區順序顯示（從長到短）
            timeframe_order = ['1d', '4h', '1h', '15m', '5m', '3m', '1m']
            timeframe_names = {
                '1d': '📅 日線 (1D)',
                '4h': '🕐 4小時 (4H)',
                '1h': '⏰ 1小時 (1H)',
                '15m': '⏱️ 15分鐘 (15M)',
                '5m': '⚡ 5分鐘 (5M)',
                '3m': '⚡ 3分鐘 (3M)',
                '1m': '⚡ 1分鐘 (1M)'
            }
            
            for tf in timeframe_order:
                if tf not in multi_tf:
                    continue
                
                tf_data = multi_tf[tf]
                
                with st.expander(f"{timeframe_names[tf]} - 點擊查看詳細分析", expanded=(tf == '1h')):
                    render_timeframe_analysis(tf, tf_data, symbol)
            
            # 自動刷新
            if auto_refresh:
                time.sleep(refresh_interval)
                st.rerun()
        
        except Exception as e:
            analysis_status.empty()  # 清除分析狀態
            st.error(f"❌ 分析失敗：{e}")
            import traceback
            with st.expander("查看錯誤詳情"):
                st.code(traceback.format_exc())
    
    # 使用說明
    with st.expander("ℹ️ 使用說明"):
        st.markdown("""
        ### 功能說明
        
        本功能作為 **CMT Level 3 機構級技術分析師**，提供專業的交易決策支持。
        
        #### 分析內容
        
        1. **方向判斷**
           - 基於多時區趨勢一致性
           - 結合 RSI、MACD 等技術指標
           - 給出做多/做空/觀望建議
        
        2. **進場價位**
           - 現價進場或等待回調
           - 基於支撐阻力位
           - 考慮 RSI 超買超賣
        
        3. **止損位 (Stop Loss)**
           - 基於支撐阻力位
           - 或使用 1.5 ATR
           - 確保風險可控
        
        4. **止盈位 (Take Profit)**
           - 下一個流動性區域
           - 阻力位/支撐位前
           - 或使用 3 ATR
        
        5. **盈虧比 (R/R)**
           - 計算風險回報比
           - 建議 R/R ≥ 1.5
           - 評估交易價值
        
        #### 注意事項
        
        - ⚠️ 本分析僅供參考，不構成投資建議
        - ⚠️ 請結合自己的交易策略和風險承受能力
        - ⚠️ 建議在模擬環境中測試後再實盤使用
        - ⚠️ 市場有風險，投資需謹慎
        
        #### 數據要求
        
        - 需要先下載市場數據（15m, 1h, 4h, 1d）
        - 使用「數據管理」功能下載
        - 或運行：`python3 快速重新下載_關鍵時區.py`
        """)


if __name__ == "__main__":
    render()
