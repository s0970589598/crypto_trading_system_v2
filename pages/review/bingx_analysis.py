"""
Bingx Analysis Module
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

# 添加當前目錄到路徑
sys.path.insert(0, ".")

def render():
    """渲染bingx analysis頁面"""
    
    # 檢查是否有保存的交易記錄
    orders_dir = Path("data/review_history/bingx/orders")
    
    if not orders_dir.exists():
        st.warning("⚠️ 沒有找到交易記錄")
        st.info("""
        請先使用「交易記錄管理」功能上傳 BingX 的 Order_History 文件。
        
        上傳後，系統會自動轉換並保存為標準格式，然後就可以在這裡查看分析結果。
        """)
    else:
        try:
            # 讀取所有 JSON 文件
            json_files = list(orders_dir.rglob("*.json"))
            
            if not json_files:
                st.info("還沒有交易記錄，請先上傳數據")
            else:
                # 載入所有訂單
                all_orders = []
                for json_file in json_files:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        orders = json.load(f)
                        all_orders.extend(orders)
                
                if not all_orders:
                    st.info("沒有交易數據")
                else:
                    # 轉換為 DataFrame
                    df = pd.DataFrame(all_orders)
                    
                    # 預先處理時間欄位
                    df['close_time_dt'] = pd.to_datetime(df['close_time'], errors='coerce')
                    df['open_time_dt'] = pd.to_datetime(df['open_time'], errors='coerce')
                    df['date'] = df['close_time_dt'].dt.date
                    df['hour'] = df['close_time_dt'].dt.hour
                    
                    # 基本統計
                    st.subheader("📊 總體統計")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("總訂單數", len(df))
                    
                    with col2:
                        winning_trades = len(df[df['pnl'] > 0])
                        total_trades = len(df[df['pnl'] != 0])
                        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
                        st.metric("勝率", f"{win_rate:.2f}%",
                                 delta="優秀" if win_rate >= 50 else "需改進",
                                 delta_color="normal" if win_rate >= 50 else "inverse")
                    
                    with col3:
                        total_pnl = df['pnl'].sum()
                        st.metric("總盈虧（未扣手續費）", f"{total_pnl:.2f} USDT",
                                 delta_color="normal" if total_pnl >= 0 else "inverse")
                    
                    with col4:
                        total_fees = df['fee'].sum()
                        st.metric("總手續費", f"{total_fees:.2f} USDT",
                                 delta_color="inverse")
                    
                    # 淨收益（扣除手續費後）
                    net_profit = total_pnl - total_fees
                    st.info(f"💰 **淨收益（扣除手續費）**：{net_profit:.2f} USDT")
                    
                    # 按帳戶類型分析
                    st.subheader("💼 按帳戶類型分析")
                    
                    account_stats = []
                    for account_type in df['account_type'].unique():
                        acc_df = df[df['account_type'] == account_type]
                        
                        winning = len(acc_df[acc_df['pnl'] > 0])
                        total = len(acc_df[acc_df['pnl'] != 0])
                        win_rate = (winning / total * 100) if total > 0 else 0
                        
                        account_stats.append({
                            '帳戶類型': account_type,
                            '訂單數': len(acc_df),
                            '獲利訂單': winning,
                            '虧損訂單': len(acc_df[acc_df['pnl'] < 0]),
                            '勝率(%)': f"{win_rate:.2f}",
                            '總盈虧(USDT)': f"{acc_df['pnl'].sum():.2f}",
                            '總手續費(USDT)': f"{acc_df['fee'].sum():.2f}",
                            '平均槓桿': f"{acc_df['leverage'].mean():.1f}x"
                        })
                    
                    stats_df = pd.DataFrame(account_stats)
                    st.dataframe(stats_df, use_container_width=True)
                    
                    # 損益分析
                    st.subheader("💰 損益分析")
                    
                    winning_df = df[df['pnl'] > 0]
                    losing_df = df[df['pnl'] < 0]
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.write("**獲利訂單**")
                        st.metric("數量", f"{len(winning_df)} 筆")
                        if len(winning_df) > 0:
                            st.metric("平均獲利", f"{winning_df['pnl'].mean():.2f} USDT")
                            st.metric("最大獲利", f"{winning_df['pnl'].max():.2f} USDT")
                    
                    with col2:
                        st.write("**虧損訂單**")
                        st.metric("數量", f"{len(losing_df)} 筆")
                        if len(losing_df) > 0:
                            st.metric("平均虧損", f"{losing_df['pnl'].mean():.2f} USDT")
                            st.metric("最大虧損", f"{losing_df['pnl'].min():.2f} USDT")
                    
                    with col3:
                        st.write("**績效指標**")
                        if len(winning_df) > 0 and len(losing_df) > 0:
                            profit_loss_ratio = abs(winning_df['pnl'].mean() / losing_df['pnl'].mean())
                            st.metric("盈虧比", f"{profit_loss_ratio:.2f}")
                            
                            total_profit = winning_df['pnl'].sum()
                            total_loss = abs(losing_df['pnl'].sum())
                            profit_factor = total_profit / total_loss if total_loss > 0 else 0
                            st.metric("獲利因子", f"{profit_factor:.2f}")
                        
                        # ROI 計算（假設初始資金）
                        if 'quantity' in df.columns:
                            # 使用平均倉位估算初始資金
                            avg_position = df['quantity'].mean()
                            if avg_position > 0:
                                roi = (total_pnl / (avg_position * 100)) * 100
                                st.metric("ROI", f"{roi:.2f}%")
                    
                    # 交易習慣
                    st.subheader("📊 交易習慣")
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        # 計算平均持倉時間
                        df['duration'] = (df['close_time_dt'] - df['open_time_dt']).dt.total_seconds() / 60
                        avg_duration = df['duration'].mean()
                        
                        if pd.notna(avg_duration):
                            if avg_duration < 60:
                                st.metric("平均持倉時間", f"{avg_duration:.1f} 分鐘")
                            else:
                                st.metric("平均持倉時間", f"{avg_duration/60:.1f} 小時")
                        else:
                            st.metric("平均持倉時間", "N/A")
                    
                    with col2:
                        avg_leverage = df['leverage'].mean()
                        st.metric("平均槓桿", f"{avg_leverage:.1f}x")
                    
                    with col3:
                        total_fees = df['fee'].sum()
                        st.metric("總手續費", f"{total_fees:.2f} USDT")
                    
                    # 按方向分析
                    st.subheader("🔄 按方向分析")
                    
                    # 統計做多/做空（使用 direction 欄位）
                    side_stats = []
                    for direction in df['direction'].unique():
                        if direction and direction != '' and direction not in ['nan', 'None']:
                            dir_df = df[df['direction'] == direction]
                            
                            winning = len(dir_df[dir_df['pnl'] > 0])
                            total = len(dir_df[dir_df['pnl'] != 0])
                            win_rate = (winning / total * 100) if total > 0 else 0
                            
                            side_stats.append({
                                '方向': direction,
                                '訂單數': len(dir_df),
                                '勝率(%)': f"{win_rate:.2f}",
                                '總盈虧(USDT)': f"{dir_df['pnl'].sum():.2f}",
                                '平均盈虧(USDT)': f"{dir_df['pnl'].mean():.2f}"
                            })
                    
                    if side_stats:
                        side_df_display = pd.DataFrame(side_stats)
                        st.dataframe(side_df_display, use_container_width=True)
                        
                        # 做多做空分佈圖
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            direction_counts = df['direction'].value_counts()
                            fig_side = px.pie(values=direction_counts.values, names=direction_counts.index,
                                             title='做多做空分佈')
                            st.plotly_chart(fig_side, use_container_width=True)
                        
                        with col2:
                            direction_pnl = df.groupby('direction')['pnl'].sum().reset_index()
                            fig_side_pnl = px.bar(direction_pnl, x='direction', y='pnl',
                                                 title='各方向總盈虧',
                                                 labels={'direction': '方向', 'pnl': '盈虧 (USDT)'})
                            st.plotly_chart(fig_side_pnl, use_container_width=True)
                    
                    # 按平倉類型分析
                    st.subheader("🎯 按平倉類型分析")
                    
                    if 'close_type' in df.columns:
                        # 過濾掉「未知」類型（通常是 Perpetual 帳戶沒有此信息）
                        df_with_close_type = df[df['close_type'] != '未知']
                        
                        if len(df_with_close_type) > 0:
                            close_type_stats = []
                            for close_type in df_with_close_type['close_type'].unique():
                                if close_type and close_type != '' and pd.notna(close_type):
                                    ct_df = df_with_close_type[df_with_close_type['close_type'] == close_type]
                                    
                                    winning = len(ct_df[ct_df['pnl'] > 0])
                                    total = len(ct_df[ct_df['pnl'] != 0])
                                    win_rate = (winning / total * 100) if total > 0 else 0
                                    
                                    close_type_stats.append({
                                        '平倉類型': close_type,
                                        '訂單數': len(ct_df),
                                        '勝率(%)': f"{win_rate:.2f}",
                                        '總盈虧(USDT)': f"{ct_df['pnl'].sum():.2f}",
                                        '平均盈虧(USDT)': f"{ct_df['pnl'].mean():.2f}"
                                    })
                            
                            if close_type_stats:
                                close_type_df = pd.DataFrame(close_type_stats)
                                st.dataframe(close_type_df, use_container_width=True)
                                
                                # 平倉類型分佈圖
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    close_counts = df_with_close_type['close_type'].value_counts()
                                    fig_close = px.pie(values=close_counts.values, names=close_counts.index,
                                                      title='平倉類型分佈')
                                    st.plotly_chart(fig_close, use_container_width=True)
                                
                                with col2:
                                    close_pnl = df_with_close_type.groupby('close_type')['pnl'].sum().reset_index()
                                    fig_close_pnl = px.bar(close_pnl, x='close_type', y='pnl',
                                                          title='各平倉類型總盈虧',
                                                          labels={'close_type': '平倉類型', 'pnl': '盈虧 (USDT)'})
                                    st.plotly_chart(fig_close_pnl, use_container_width=True)
                                
                                # 說明
                                unknown_count = len(df[df['close_type'] == '未知'])
                                if unknown_count > 0:
                                    st.info(f"ℹ️ 另有 {unknown_count} 筆訂單沒有平倉類型信息（來自 Perpetual 帳戶，該帳戶類型不提供此信息）")
                            else:
                                st.info("沒有平倉類型數據")
                        else:
                            st.info("所有訂單都沒有平倉類型信息（可能全部來自 Perpetual 帳戶）")
                    else:
                        st.info("此數據源不包含平倉類型信息")
                    
                    # 按交易對分析
                    st.subheader("📈 按交易對分析")
                    
                    symbol_stats = []
                    for symbol in df['symbol'].unique():
                        if symbol and symbol != '':
                            sym_df = df[df['symbol'] == symbol]
                            
                            winning = len(sym_df[sym_df['pnl'] > 0])
                            total = len(sym_df[sym_df['pnl'] != 0])
                            win_rate = (winning / total * 100) if total > 0 else 0
                            
                            symbol_stats.append({
                                '交易對': symbol,
                                '訂單數': len(sym_df),
                                '勝率(%)': f"{win_rate:.2f}",
                                '總盈虧(USDT)': f"{sym_df['pnl'].sum():.2f}",
                                '平均盈虧(USDT)': f"{sym_df['pnl'].mean():.2f}"
                            })
                    
                    if symbol_stats:
                        symbol_df = pd.DataFrame(symbol_stats)
                        # 按總盈虧排序
                        symbol_df['_sort'] = symbol_df['總盈虧(USDT)'].astype(float)
                        symbol_df = symbol_df.sort_values('_sort', ascending=False).drop('_sort', axis=1)
                        st.dataframe(symbol_df, use_container_width=True, height=300)
                    
                    # 時間分析
                    st.subheader("📅 時間分析")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # 每日交易數量
                        daily_counts = df.groupby('date').size().reset_index(name='訂單數')
                        fig_daily = px.line(daily_counts, x='date', y='訂單數',
                                          title='每日交易數量',
                                          labels={'date': '日期'})
                        st.plotly_chart(fig_daily, use_container_width=True)
                    
                    with col2:
                        # 每日盈虧
                        daily_pnl = df.groupby('date')['pnl'].sum().reset_index()
                        fig_daily_pnl = px.bar(daily_pnl, x='date', y='pnl',
                                              title='每日盈虧',
                                              labels={'date': '日期', 'pnl': '盈虧 (USDT)'})
                        st.plotly_chart(fig_daily_pnl, use_container_width=True)
                    
                    # 按小時分析
                    st.write("**按小時分析**")
                    hourly_stats = df.groupby('hour').agg({
                        'pnl': ['sum', 'count', 'mean']
                    }).reset_index()
                    hourly_stats.columns = ['小時', '總盈虧', '訂單數', '平均盈虧']
                    
                    fig_hourly = px.bar(hourly_stats, x='小時', y='總盈虧',
                                       title='各時段盈虧分佈',
                                       labels={'小時': '小時 (UTC+8)', '總盈虧': '盈虧 (USDT)'})
                    st.plotly_chart(fig_hourly, use_container_width=True)
                    
                    # 按日統計表格
                    daily_stats = df.groupby('date').agg({
                        'pnl': ['sum', 'count'],
                        'fee': 'sum'
                    }).reset_index()
                    
                    daily_stats.columns = ['日期', '盈虧', '訂單數', '手續費']
                    daily_stats = daily_stats.sort_values('日期', ascending=False)
                    
                    with st.expander("📊 查看每日詳細數據"):
                        st.dataframe(daily_stats, use_container_width=True)
                    
                    # 每日交易頻率分析
                    st.subheader("📊 每日交易頻率分析")
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        avg_daily_trades = daily_stats['訂單數'].mean()
                        st.metric("平均每日訂單", f"{avg_daily_trades:.1f} 筆")
                    
                    with col2:
                        max_daily_trades = daily_stats['訂單數'].max()
                        st.metric("最多一天", f"{max_daily_trades:.0f} 筆")
                    
                    with col3:
                        trading_days = len(daily_stats)
                        st.metric("交易天數", f"{trading_days} 天")
                    
                    # 交易頻率評估
                    if avg_daily_trades > 10:
                        st.warning("⚠️ 平均每日交易超過 10 筆，可能存在過度交易")
                    elif avg_daily_trades > 5:
                        st.info("ℹ️ 平均每日交易 5-10 筆，交易頻率適中")
                    else:
                        st.success("✅ 平均每日交易少於 5 筆，交易頻率良好")
                    
                    # ROI 計算
                    st.subheader("💹 投資回報率（ROI）")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # 方法 1：基於平均倉位估算
                        if 'quantity' in df.columns and 'entry_price' in df.columns:
                            df_with_values = df[(df['quantity'] > 0) & (df['entry_price'] > 0)]
                            if len(df_with_values) > 0:
                                avg_position_value = (df_with_values['quantity'] * df_with_values['entry_price']).mean()
                                if avg_position_value > 0:
                                    roi_estimate = (total_pnl / avg_position_value) * 100
                                    st.metric("ROI（基於平均倉位）", f"{roi_estimate:.2f}%")
                                    st.caption(f"估算初始資金：{avg_position_value:.2f} USDT")
                    
                    with col2:
                        # 方法 2：手動輸入初始資金
                        initial_capital = st.number_input(
                            "輸入初始資金（USDT）",
                            min_value=0.0,
                            value=1000.0,
                            step=100.0,
                            help="輸入你的初始投入資金來計算準確的 ROI"
                        )
                        
                        if initial_capital > 0:
                            roi_actual = (total_pnl / initial_capital) * 100
                            net_roi = ((total_pnl - total_fees) / initial_capital) * 100
                            
                            st.metric("ROI（未扣手續費）", f"{roi_actual:.2f}%")
                            st.metric("淨 ROI（扣除手續費）", f"{net_roi:.2f}%")
                    
                    # 手續費分析
                    st.subheader("💸 手續費詳細分析")
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("總手續費", f"{total_fees:.2f} USDT")
                        avg_fee_per_trade = total_fees / len(df) if len(df) > 0 else 0
                        st.metric("平均每筆手續費", f"{avg_fee_per_trade:.4f} USDT")
                    
                    with col2:
                        # 手續費佔盈虧比例
                        if total_pnl != 0:
                            fee_ratio = (total_fees / abs(total_pnl)) * 100
                            st.metric("手續費佔盈虧比", f"{fee_ratio:.1f}%")
                        
                        # 手續費佔交易額比例（估算）
                        if 'quantity' in df.columns and 'entry_price' in df.columns:
                            df_with_values = df[(df['quantity'] > 0) & (df['entry_price'] > 0)]
                            if len(df_with_values) > 0:
                                total_volume = (df_with_values['quantity'] * df_with_values['entry_price']).sum()
                                if total_volume > 0:
                                    fee_rate = (total_fees / total_volume) * 100
                                    st.metric("實際手續費率", f"{fee_rate:.4f}%")
                    
                    with col3:
                        # 按帳戶類型分析手續費
                        fee_by_account = df.groupby('account_type')['fee'].sum()
                        st.write("**按帳戶類型**")
                        for acc_type, fee in fee_by_account.items():
                            st.write(f"{acc_type}: {fee:.2f} USDT")
                    
                    # 手續費優化建議
                    st.write("**💡 手續費優化建議**")
                    
                    suggestions = []
                    
                    if total_fees > abs(total_pnl) * 0.5:
                        suggestions.append("❌ 手續費過高（超過盈虧的 50%），嚴重影響獲利")
                        suggestions.append("   建議：大幅降低交易頻率，每天最多 2-3 筆")
                    elif total_fees > abs(total_pnl) * 0.3:
                        suggestions.append("⚠️ 手續費偏高（超過盈虧的 30%）")
                        suggestions.append("   建議：減少交易頻率，提高每筆交易質量")
                    else:
                        suggestions.append("✅ 手續費比例合理")
                    
                    if avg_daily_trades > 5:
                        daily_fee = total_fees / trading_days if trading_days > 0 else 0
                        suggestions.append(f"   每日平均手續費：{daily_fee:.2f} USDT")
                        suggestions.append("   建議：使用系統輔助，只在高質量信號時交易")
                    
                    # 計算如果減少交易頻率可以節省的手續費
                    if avg_daily_trades > 3:
                        target_trades = 3
                        potential_savings = total_fees * (1 - target_trades / avg_daily_trades)
                        suggestions.append(f"   如果每天只交易 {target_trades} 筆，可節省約 {potential_savings:.2f} USDT 手續費")
                    
                    for suggestion in suggestions:
                        st.write(suggestion)
                    
                    # 綜合分析與建議
                    st.subheader("🎯 綜合分析與建議")
                    
                    # 重新計算統計數據（確保使用正確的數據）
                    winning_trades_count = len(df[df['pnl'] > 0])
                    losing_trades_count = len(df[df['pnl'] < 0])
                    total_trades_count = len(df[df['pnl'] != 0])
                    current_win_rate = (winning_trades_count / total_trades_count * 100) if total_trades_count > 0 else 0
                    
                    winning_df = df[df['pnl'] > 0]
                    losing_df = df[df['pnl'] < 0]
                    
                    # 問題診斷
                    problems = []
                    suggestions = []
                    
                    # 1. 勝率分析
                    if current_win_rate < 40:
                        problems.append(f"⚠️ 勝率偏低 ({current_win_rate:.2f}%)")
                        suggestions.append("建議：提高進場條件的嚴格度，等待更明確的信號")
                    elif current_win_rate > 60:
                        problems.append(f"✅ 勝率良好 ({current_win_rate:.2f}%)")
                    else:
                        problems.append(f"📊 勝率中等 ({current_win_rate:.2f}%)")
                    
                    # 2. 盈虧比分析
                    if len(winning_df) > 0 and len(losing_df) > 0:
                        profit_loss_ratio = abs(winning_df['pnl'].mean() / losing_df['pnl'].mean())
                        if profit_loss_ratio < 1.5:
                            problems.append(f"⚠️ 盈虧比偏低 ({profit_loss_ratio:.2f})")
                            suggestions.append("建議：讓獲利單跑得更遠，或更早止損")
                        else:
                            problems.append(f"✅ 盈虧比良好 ({profit_loss_ratio:.2f})")
                    
                    # 3. 獲利因子分析
                    if len(winning_df) > 0 and len(losing_df) > 0:
                        total_profit = winning_df['pnl'].sum()
                        total_loss = abs(losing_df['pnl'].sum())
                        profit_factor = total_profit / total_loss if total_loss > 0 else 0
                        
                        if profit_factor < 1.0:
                            problems.append(f"❌ 獲利因子 < 1.0 ({profit_factor:.2f}) - 整體虧損")
                            suggestions.append("建議：暫停交易，重新檢視策略")
                        elif profit_factor < 1.5:
                            problems.append(f"⚠️ 獲利因子偏低 ({profit_factor:.2f})")
                            suggestions.append("建議：優化進出場策略，提高整體表現")
                        else:
                            problems.append(f"✅ 獲利因子良好 ({profit_factor:.2f})")
                    
                    # 4. 手續費分析（修正顯示方式）
                    if total_pnl != 0:
                        fee_ratio = (total_fees / abs(total_pnl)) * 100
                        if fee_ratio > 50:
                            problems.append(f"⚠️ 手續費過高 ({total_fees:.2f} USDT)，佔盈虧 {fee_ratio:.1f}%")
                            suggestions.append("建議：減少交易頻率，或使用更低手續費的帳戶")
                        elif fee_ratio > 30:
                            problems.append(f"⚠️ 手續費偏高 ({total_fees:.2f} USDT)，佔盈虧 {fee_ratio:.1f}%")
                    
                    # 5. 槓桿分析
                    avg_leverage = df['leverage'].mean()
                    if avg_leverage > 50:
                        problems.append(f"⚠️ 平均槓桿過高 ({avg_leverage:.1f}x)")
                        suggestions.append("建議：降低槓桿倍數，減少爆倉風險")
                    
                    # 6. 持倉時間分析
                    df['duration'] = (df['close_time_dt'] - df['open_time_dt']).dt.total_seconds() / 60
                    avg_duration = df['duration'].mean()
                    if pd.notna(avg_duration) and avg_duration < 5:
                        problems.append(f"⚠️ 平均持倉時間過短 ({avg_duration:.1f} 分鐘)")
                        suggestions.append("建議：避免過度頻繁交易，給趨勢更多發展空間")
                    
                    # 顯示診斷結果
                    st.subheader("📋 問題診斷")
                    
                    # 重新組織問題診斷，更清晰
                    diagnostic_items = []
                    
                    # 1. 勝率診斷
                    if current_win_rate < 30:
                        diagnostic_items.append(f"❌ 勝率過低（{current_win_rate:.1f}%），建議 > 50%")
                    elif current_win_rate < 50:
                        diagnostic_items.append(f"⚠️ 勝率偏低（{current_win_rate:.1f}%），建議 > 50%")
                    else:
                        diagnostic_items.append(f"✅ 勝率良好（{current_win_rate:.1f}%）")
                    
                    # 2. 盈虧診斷
                    if total_pnl < 0:
                        diagnostic_items.append(f"❌ 總體虧損（{total_pnl:.2f} USDT）")
                    elif total_pnl < 100:
                        diagnostic_items.append(f"⚠️ 盈利較少（{total_pnl:.2f} USDT）")
                    else:
                        diagnostic_items.append(f"✅ 盈利良好（{total_pnl:.2f} USDT）")
                    
                    # 3. 手續費診斷
                    if total_pnl != 0:
                        fee_ratio = (total_fees / abs(total_pnl)) * 100
                        if fee_ratio > 80:
                            diagnostic_items.append(f"❌ 手續費過高（{total_fees:.2f} USDT），佔盈虧 {fee_ratio:.1f}%")
                        elif fee_ratio > 50:
                            diagnostic_items.append(f"⚠️ 手續費偏高（{total_fees:.2f} USDT），佔盈虧 {fee_ratio:.1f}%")
                    
                    # 4. 持倉時間診斷
                    if pd.notna(avg_duration):
                        if avg_duration < 60:
                            hours = avg_duration / 60
                            if hours < 1:
                                diagnostic_items.append(f"⚠️ 平均持倉時間過短（{hours:.1f} 小時），可能過度交易")
                        else:
                            hours = avg_duration / 60
                            diagnostic_items.append(f"✅ 平均持倉時間適中（{hours:.1f} 小時）")
                    
                    # 5. 槓桿診斷
                    if avg_leverage > 50:
                        diagnostic_items.append(f"⚠️ 平均槓桿過高（{avg_leverage:.1f}x），風險較大")
                    elif avg_leverage > 20:
                        diagnostic_items.append(f"⚠️ 平均槓桿偏高（{avg_leverage:.1f}x）")
                    else:
                        diagnostic_items.append(f"✅ 槓桿使用合理（{avg_leverage:.1f}x）")
                    
                    # 6. 盈虧比診斷
                    if len(winning_df) > 0 and len(losing_df) > 0:
                        profit_loss_ratio = abs(winning_df['pnl'].mean() / losing_df['pnl'].mean())
                        if profit_loss_ratio < 1.0:
                            diagnostic_items.append(f"❌ 盈虧比過低（{profit_loss_ratio:.2f}），平均虧損大於平均獲利")
                        elif profit_loss_ratio < 1.5:
                            diagnostic_items.append(f"⚠️ 盈虧比偏低（{profit_loss_ratio:.2f}），建議 > 1.5")
                        else:
                            diagnostic_items.append(f"✅ 盈虧比良好（{profit_loss_ratio:.2f}）")
                    
                    # 顯示診斷項目
                    for item in diagnostic_items:
                        st.write(item)
                    
                    # 改進建議
                    st.subheader("💡 改進建議")
                    
                    suggestions_list = []
                    
                    # 根據診斷結果給出具體建議
                    if current_win_rate < 50:
                        suggestions_list.append("**提高勝率**：使用系統輔助，只在高質量信號時交易")
                    
                    if total_pnl != 0 and (total_fees / abs(total_pnl)) * 100 > 50:
                        suggestions_list.append("**減少手續費**：降低交易頻率，每天 1-2 筆即可")
                    
                    if total_pnl < 0:
                        suggestions_list.append("**扭虧為盈**：嚴格執行止損，使用系統風險管理")
                    
                    if pd.notna(avg_duration) and avg_duration < 60:
                        suggestions_list.append("**延長持倉**：避免頻繁進出，給趨勢時間發展")
                    
                    if avg_leverage > 20:
                        suggestions_list.append("**降低槓桿**：建議使用 3-5x 槓桿，降低風險")
                    
                    if len(winning_df) > 0 and len(losing_df) > 0:
                        profit_loss_ratio = abs(winning_df['pnl'].mean() / losing_df['pnl'].mean())
                        if profit_loss_ratio < 1.5:
                            suggestions_list.append("**改善盈虧比**：讓獲利單跑得更遠，虧損單更早止損")
                    
                    # 總是顯示系統使用建議
                    suggestions_list.append("**使用系統**：運行 `python3 cli.py live --strategy multi-timeframe-aggressive`")
                    
                    # 顯示建議
                    for suggestion in suggestions_list:
                        st.write(f"• {suggestion}")
                    
                    # 移除舊的顯示方式
                    # col1, col2 = st.columns(2)
                    # with col1:
                    #     st.write("**問題診斷**")
                    #     for problem in problems:
                    #         st.write(problem)
                    # with col2:
                    #     st.write("**改進建議**")
                    #     if suggestions:
                    #         for suggestion in suggestions:
                    #             st.write(suggestion)
                    #     else:
                    #         st.write("✅ 目前表現良好，繼續保持！")
                    
                    # 總結指標
                    st.divider()
                    
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("總盈虧", f"{total_pnl:.2f} USDT",
                                 delta_color="normal" if total_pnl >= 0 else "inverse")
                    
                    with col2:
                        if 'quantity' in df.columns and df['quantity'].mean() > 0:
                            roi = (total_pnl / (df['quantity'].mean() * 100)) * 100
                            st.metric("ROI", f"{roi:.2f}%",
                                     delta_color="normal" if roi >= 0 else "inverse")
                    
                    with col3:
                        st.metric("總交易次數", len(df))
                    
                    with col4:
                        st.metric("淨收益", f"{total_pnl - total_fees:.2f} USDT",
                                 delta_color="normal" if (total_pnl - total_fees) >= 0 else "inverse")
                    
                    # 盈虧分佈圖
                    st.subheader("📊 盈虧分佈")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # 盈虧直方圖
                        fig1 = px.histogram(df, x='pnl', nbins=50,
                                          title='盈虧分佈',
                                          labels={'pnl': '盈虧 (USDT)', 'count': '訂單數'})
                        st.plotly_chart(fig1, use_container_width=True)
                    
                    with col2:
                        # 按帳戶類型的盈虧
                        account_pnl = df.groupby('account_type')['pnl'].sum().reset_index()
                        fig2 = px.bar(account_pnl, x='account_type', y='pnl',
                                     title='各帳戶類型總盈虧',
                                     labels={'account_type': '帳戶類型', 'pnl': '盈虧 (USDT)'})
                        st.plotly_chart(fig2, use_container_width=True)
                    
                    # 下載完整數據
                    st.subheader("📥 下載數據")
                    
                    csv = df.to_csv(index=False, encoding='utf-8-sig')
                    st.download_button(
                        label="📥 下載完整交易記錄 CSV",
                        data=csv,
                        file_name=f"bingx_trades_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )
                    
                    # 查看訂單詳細記錄
                    st.subheader("📋 查看訂單詳細記錄")
                    
                    # 篩選選項
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        filter_account = st.selectbox(
                            "帳戶類型",
                            ["全部"] + list(df['account_type'].unique())
                        )
                    
                    with col2:
                        filter_direction = st.selectbox(
                            "方向",
                            ["全部"] + list(df['direction'].unique())
                        )
                    
                    with col3:
                        filter_pnl = st.selectbox(
                            "盈虧",
                            ["全部", "獲利", "虧損"]
                        )
                    
                    # 應用篩選
                    filtered_df = df.copy()
                    
                    if filter_account != "全部":
                        filtered_df = filtered_df[filtered_df['account_type'] == filter_account]
                    
                    if filter_direction != "全部":
                        filtered_df = filtered_df[filtered_df['direction'] == filter_direction]
                    
                    if filter_pnl == "獲利":
                        filtered_df = filtered_df[filtered_df['pnl'] > 0]
                    elif filter_pnl == "虧損":
                        filtered_df = filtered_df[filtered_df['pnl'] < 0]
                    
                    # 顯示篩選後的記錄
                    st.write(f"**共 {len(filtered_df)} 筆記錄**")
                    
                    # 選擇要顯示的欄位
                    display_columns = ['open_time', 'close_time', 'account_type', 'symbol', 'direction', 
                                     'entry_price', 'exit_price', 'quantity', 'leverage', 'pnl', 'fee']
                    column_names = ['開倉時間', '平倉時間', '帳戶類型', '交易對', '方向', 
                                  '進場價', '出場價', '數量', '槓桿', '盈虧(USDT)', '手續費(USDT)']
                    
                    if 'close_type' in filtered_df.columns:
                        display_columns.append('close_type')
                        column_names.append('平倉類型')
                    
                    # 只選擇存在的欄位
                    available_columns = [col for col in display_columns if col in filtered_df.columns]
                    available_names = [column_names[i] for i, col in enumerate(display_columns) if col in filtered_df.columns]
                    
                    display_df = filtered_df[available_columns].copy()
                    display_df.columns = available_names
                    
                    # 按平倉時間排序（最新的在前）
                    if '平倉時間' in display_df.columns:
                        display_df = display_df.sort_values('平倉時間', ascending=False)
                    
                    st.dataframe(display_df, use_container_width=True, height=400)
        
        except Exception as e:
            st.error(f"❌ 分析失敗：{str(e)}")
            import traceback
            st.code(traceback.format_exc())

