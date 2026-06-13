#!/usr/bin/env python3
"""
交易系統 Web Dashboard
使用 Streamlit 創建簡單的 Web 界面
"""

import streamlit as st
import pandas as pd
import json
import glob
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px

# 設置頁面配置
st.set_page_config(
    page_title="交易系統 Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 標題
st.title("🚀 多策略交易系統 Dashboard")

# 側邊欄
st.sidebar.title("📋 功能選單")
page = st.sidebar.radio(
    "選擇功能",
    ["📊 回測結果", "📈 槓桿對比", "⚙️ 策略配置", "💰 交易分析", "🎯 快速操作"]
)

# ==================== 頁面 1：回測結果 ====================
if page == "📊 回測結果":
    st.header("📊 回測結果總覽")
    
    # 查找所有回測結果
    result_files = glob.glob('backtest_result_*.json')
    
    if not result_files:
        st.warning("⚠️ 沒有找到回測結果文件")
        st.info("請先運行回測：`python3 -m cli_commands.backtest --strategy multi-timeframe-aggressive`")
    else:
        # 選擇回測結果
        selected_file = st.selectbox(
            "選擇回測結果",
            result_files,
            format_func=lambda x: x.replace('backtest_result_', '').replace('.json', '')
        )
        
        # 讀取結果
        with open(selected_file, 'r') as f:
            result = json.load(f)
        
        # 顯示基本信息
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "總收益",
                f"+{result['total_pnl_pct']:.2f}%",
                delta=f"{result['total_pnl']:.2f} USDT"
            )
        
        with col2:
            st.metric(
                "勝率",
                f"{result['win_rate']:.2f}%",
                delta=f"{result['winning_trades']}/{result['total_trades']}"
            )
        
        with col3:
            st.metric(
                "最大回撤",
                f"-{result['max_drawdown_pct']:.2f}%",
                delta=f"-{result['max_drawdown']:.2f} USDT",
                delta_color="inverse"
            )
        
        with col4:
            st.metric(
                "獲利因子",
                f"{result['profit_factor']:.2f}",
                delta="優秀" if result['profit_factor'] > 1.5 else "一般"
            )
        
        # 詳細指標
        st.subheader("📈 詳細指標")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**資金情況**")
            st.write(f"- 初始資金：{result['initial_capital']:.2f} USDT")
            st.write(f"- 最終資金：{result['final_capital']:.2f} USDT")
            st.write(f"- 淨損益：{result['total_pnl']:.2f} USDT")
            
            st.write("**交易統計**")
            st.write(f"- 總交易數：{result['total_trades']}")
            st.write(f"- 獲利交易：{result['winning_trades']}")
            st.write(f"- 虧損交易：{result['losing_trades']}")
        
        with col2:
            st.write("**損益分析**")
            st.write(f"- 平均獲利：{result['avg_win']:.2f} USDT")
            st.write(f"- 平均虧損：{result['avg_loss']:.2f} USDT")
            st.write(f"- 獲利因子：{result['profit_factor']:.2f}")
            
            st.write("**風險指標**")
            st.write(f"- 最大回撤：{result['max_drawdown_pct']:.2f}%")
            st.write(f"- 夏普比率：{result['sharpe_ratio']:.2f}")
        
        # 權益曲線
        if 'equity_curve' in result and result['equity_curve']:
            st.subheader("📉 權益曲線")
            
            try:
                # 處理不同格式的 equity_curve
                equity_curve = result['equity_curve']
                
                if isinstance(equity_curve, list):
                    if len(equity_curve) > 0 and isinstance(equity_curve[0], dict):
                        # 如果是字典列表
                        equity_df = pd.DataFrame(equity_curve)
                        equity_values = equity_df['equity'].values if 'equity' in equity_df.columns else equity_df.iloc[:, 0].values
                    else:
                        # 如果是數值列表
                        equity_values = equity_curve
                elif isinstance(equity_curve, dict):
                    # 如果是字典
                    equity_values = list(equity_curve.values())
                else:
                    equity_values = [equity_curve]
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=list(range(len(equity_values))),
                    y=equity_values,
                    mode='lines',
                    name='權益',
                    line=dict(color='#00D9FF', width=2)
                ))
                
                fig.update_layout(
                    title="權益變化",
                    xaxis_title="交易次數",
                    yaxis_title="權益 (USDT)",
                    hovermode='x unified',
                    height=400
                )
                
                st.plotly_chart(fig, width='stretch')
            except Exception as e:
                st.warning(f"⚠️ 無法顯示權益曲線：{str(e)}")
        
        # 交易明細
        if 'trades' in result and result['trades']:
            st.subheader("📋 交易明細")
            
            trades_df = pd.DataFrame(result['trades'])
            
            # 只顯示重要欄位
            display_cols = ['entry_time', 'direction', 'entry_price', 'exit_price', 'pnl', 'pnl_pct', 'exit_reason']
            if all(col in trades_df.columns for col in display_cols):
                display_df = trades_df[display_cols].copy()
                display_df['pnl'] = display_df['pnl'].round(2)
                display_df['pnl_pct'] = display_df['pnl_pct'].round(2)
                
                # 添加顏色
                def color_pnl(val):
                    color = 'green' if val > 0 else 'red'
                    return f'color: {color}'
                
                styled_df = display_df.style.map(color_pnl, subset=['pnl', 'pnl_pct'])
                
                st.dataframe(styled_df, width='stretch', height=400)

# ==================== 頁面 2：槓桿對比 ====================
elif page == "📈 槓桿對比":
    st.header("📈 槓桿對比分析")
    
    # 添加執行按鈕
    st.info("💡 槓桿對比將測試 1x, 2x, 3x, 5x, 10x, 20x 槓桿（約需 2-3 分鐘）")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🚀 執行槓桿對比回測", use_container_width=True, type="primary"):
            with st.spinner("正在執行槓桿對比回測，請稍候..."):
                import subprocess
                result = subprocess.run(
                    ['python3', 'backtest_leverage_comparison.py'],
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 分鐘超時
                )
                
                if result.returncode == 0:
                    st.success("✅ 槓桿對比完成！結果已保存。")
                    st.balloons()
                    # 顯示執行摘要
                    with st.expander("查看執行日誌"):
                        st.code(result.stdout[-2000:])  # 顯示最後 2000 字符
                    st.rerun()  # 重新載入頁面以顯示新結果
                else:
                    st.error("❌ 執行失敗")
                    st.code(result.stderr)
    
    with col2:
        st.markdown("""
        **測試內容**:
        - 激進模式（1.5 ATR 止損）
        - 輕鬆模式（2.0 ATR 止損）
        - 每個模式測試 6 個槓桿
        - 共 12 次回測
        """)
    
    st.divider()
    
    # 查找槓桿對比文件
    leverage_files = glob.glob('leverage_comparison_*.csv')
    
    if not leverage_files:
        st.warning("⚠️ 沒有找到槓桿對比結果")
        st.info("👆 點擊上方按鈕執行槓桿對比回測")
    else:
        # 選擇文件
        selected_file = st.selectbox(
            "選擇對比結果",
            leverage_files,
            format_func=lambda x: x.replace('leverage_comparison_', '').replace('.csv', '')
        )
        
        # 讀取數據
        df = pd.read_csv(selected_file)
        
        # 計算風險調整收益
        df['risk_adjusted'] = df['total_return'] / df['max_drawdown']
        
        # 顯示表格
        st.subheader("📊 對比表格")
        
        display_df = df[['leverage', 'total_return', 'max_drawdown', 'win_rate', 'risk_adjusted']].copy()
        display_df.columns = ['槓桿', '收益率(%)', '最大回撤(%)', '勝率(%)', '風險調整收益']
        
        # 格式化
        display_df['收益率(%)'] = display_df['收益率(%)'].round(2)
        display_df['最大回撤(%)'] = display_df['最大回撤(%)'].round(2)
        display_df['勝率(%)'] = display_df['勝率(%)'].round(2)
        display_df['風險調整收益'] = display_df['風險調整收益'].round(2)
        
        st.dataframe(display_df, width='stretch')
        
        # 圖表
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📈 收益率 vs 槓桿")
            fig1 = px.bar(df, x='leverage', y='total_return', 
                         title='不同槓桿的收益率',
                         labels={'leverage': '槓桿', 'total_return': '收益率(%)'},
                         color='total_return',
                         color_continuous_scale='RdYlGn')
            st.plotly_chart(fig1, width='stretch')
        
        with col2:
            st.subheader("📉 回撤 vs 槓桿")
            fig2 = px.bar(df, x='leverage', y='max_drawdown',
                         title='不同槓桿的最大回撤',
                         labels={'leverage': '槓桿', 'max_drawdown': '最大回撤(%)'},
                         color='max_drawdown',
                         color_continuous_scale='RdYlGn_r')
            st.plotly_chart(fig2, width='stretch')
        
        # 風險調整收益
        st.subheader("⭐ 風險調整收益")
        fig3 = px.line(df, x='leverage', y='risk_adjusted',
                      title='風險調整收益（越高越好）',
                      labels={'leverage': '槓桿', 'risk_adjusted': '風險調整收益'},
                      markers=True)
        st.plotly_chart(fig3, width='stretch')
        
        # 推薦
        best_idx = df['risk_adjusted'].idxmax()
        best_leverage = int(df.loc[best_idx, 'leverage'])
        best_return = df.loc[best_idx, 'total_return']
        best_drawdown = df.loc[best_idx, 'max_drawdown']
        
        st.success(f"""
        💡 **推薦配置**：{best_leverage}x 槓桿
        - 收益率：+{best_return:.2f}%
        - 最大回撤：-{best_drawdown:.2f}%
        - 風險調整收益：{df.loc[best_idx, 'risk_adjusted']:.2f}
        """)

# ==================== 頁面 3：策略配置 ====================
elif page == "⚙️ 策略配置":
    st.header("⚙️ 策略配置管理")
    
    # 查找所有策略
    strategy_files = glob.glob('strategies/*.json')
    
    if not strategy_files:
        st.warning("⚠️ 沒有找到策略配置文件")
    else:
        # 選擇策略
        selected_strategy = st.selectbox(
            "選擇策略",
            strategy_files,
            format_func=lambda x: x.replace('strategies/', '').replace('.json', '')
        )
        
        # 讀取配置
        with open(selected_strategy, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 顯示基本信息
        st.subheader("📋 基本信息")
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**策略名稱**：{config.get('name', 'Unknown')}")
            st.write(f"**策略 ID**：{config.get('id', 'unknown')}")
            st.write(f"**策略類型**：{config.get('class', 'Unknown')}")
        
        with col2:
            status = "✅ 啟用" if config.get('enabled', False) else "❌ 禁用"
            st.write(f"**狀態**：{status}")
            st.write(f"**版本**：{config.get('version', '1.0.0')}")
        
        # 參數配置
        if 'parameters' in config:
            st.subheader("🎛️ 策略參數")
            params = config['parameters']
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.write("**技術指標**")
                st.write(f"- EMA 短期：{params.get('ema_short', 'N/A')}")
                st.write(f"- EMA 長期：{params.get('ema_long', 'N/A')}")
                st.write(f"- RSI 週期：{params.get('rsi_period', 'N/A')}")
                st.write(f"- ATR 週期：{params.get('atr_period', 'N/A')}")
            
            with col2:
                st.write("**進出場**")
                st.write(f"- 止損：{params.get('stop_loss_atr', 'N/A')} ATR")
                st.write(f"- 目標：{params.get('take_profit_atr', 'N/A')} ATR")
                st.write(f"- RSI 超賣：{params.get('rsi_oversold', 'N/A')}")
                st.write(f"- RSI 超買：{params.get('rsi_overbought', 'N/A')}")
            
            with col3:
                st.write("**週期**")
                timeframes = params.get('timeframes', [])
                for tf in timeframes:
                    st.write(f"- {tf}")
        
        # 風險管理
        if 'risk_management' in config:
            st.subheader("⚠️ 風險管理")
            risk = config['risk_management']
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                pos_size = risk.get('position_size', 0) * 100
                st.metric("倉位大小", f"{pos_size:.0f}%")
            
            with col2:
                st.metric("槓桿倍數", f"{risk.get('leverage', 'N/A')}x")
            
            with col3:
                max_dd = risk.get('max_drawdown', 0) * 100
                st.metric("最大回撤限制", f"{max_dd:.0f}%")
            
            with col4:
                st.metric("連損限制", f"{risk.get('max_consecutive_losses', 'N/A')} 次")
        
        # 顯示完整配置
        with st.expander("📄 查看完整配置（JSON）"):
            st.json(config)

# ==================== 頁面 4：交易分析 ====================
elif page == "💰 交易分析":
    st.header("💰 你的交易分析")
    
    # 導入分析器
    import sys
    sys.path.insert(0, '.')
    
    try:
        from 完整交易分析 import BingXTradeAnalyzer
        
        # 創建分析器
        analyzer = BingXTradeAnalyzer()
        analyzer.load_data()
        
        # 分析訂單和資金流水
        order_analysis = analyzer.analyze_orders()
        trans_analysis = analyzer.analyze_transactions()
        
        if order_analysis is None and trans_analysis is None:
            st.warning("⚠️ 沒有找到交易記錄")
            st.info("請確保 bingxHistory 目錄中有 Order_History 和 Transaction_History 文件")
        else:
            st.success(f"✅ 成功載入交易數據")
            
            # ========== 訂單分析 ==========
            if order_analysis:
                st.subheader("📋 訂單分析")
                
                summary = order_analysis['summary']
                
                # 基本統計
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("總訂單數", summary['total_orders'])
                
                with col2:
                    st.metric("勝率", f"{summary['win_rate']:.2f}%",
                             delta="優秀" if summary['win_rate'] >= 50 else "需改進",
                             delta_color="normal" if summary['win_rate'] >= 50 else "inverse")
                
                with col3:
                    st.metric("總盈虧", f"{summary['total_pnl']:.2f} USDT",
                             delta_color="normal" if summary['total_pnl'] >= 0 else "inverse")
                
                with col4:
                    st.metric("總手續費", f"{summary['total_fees']:.2f} USDT",
                             delta_color="inverse")
                
                # 詳細指標
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**損益分析**")
                    st.write(f"- 獲利訂單：{summary['winning_orders']} 筆")
                    st.write(f"- 虧損訂單：{summary['losing_orders']} 筆")
                    st.write(f"- 平均獲利：{summary['avg_win']:.2f} USDT")
                    st.write(f"- 平均虧損：{summary['avg_loss']:.2f} USDT")
                    st.write(f"- 最大獲利：{summary['max_win']:.2f} USDT")
                    st.write(f"- 最大虧損：{summary['max_loss']:.2f} USDT")
                
                with col2:
                    st.write("**交易習慣**")
                    st.write(f"- 平均持倉時間：{summary['avg_holding_time']:.1f} 分鐘")
                    st.write(f"- 平均槓桿：{summary['avg_leverage']:.1f}x")
                    st.write(f"- 總資金費：{summary['total_funding']:.2f} USDT")
                    
                    # 計算盈虧比
                    if summary['avg_loss'] != 0:
                        profit_loss_ratio = abs(summary['avg_win'] / summary['avg_loss'])
                        st.write(f"- 盈虧比：{profit_loss_ratio:.2f}")
                    
                    # 計算獲利因子
                    df = order_analysis['raw_data']
                    total_profit = df[df['Realized PNL'] > 0]['Realized PNL'].sum()
                    total_loss = abs(df[df['Realized PNL'] < 0]['Realized PNL'].sum())
                    if total_loss > 0:
                        profit_factor = total_profit / total_loss
                        st.write(f"- 獲利因子：{profit_factor:.2f}")
                
                # 按交易對分析
                st.subheader("💱 按交易對分析")
                by_symbol = order_analysis['by_symbol']
                st.dataframe(by_symbol, width="stretch")
                
                # 按方向分析
                st.subheader("🔄 按方向分析")
                by_direction = order_analysis['by_direction']
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.dataframe(by_direction, width="stretch")
                
                with col2:
                    # 方向分佈圖
                    direction_counts = df['direction'].value_counts()
                    fig = px.pie(values=direction_counts.values, 
                               names=direction_counts.index,
                               title='做多 vs 做空分佈')
                    st.plotly_chart(fig, width="stretch")
                
                # 按平倉類型分析
                st.subheader("🎯 按平倉類型分析")
                by_close_type = order_analysis['by_close_type']
                st.dataframe(by_close_type, width="stretch")
                
                # 按帳戶類型分析
                st.subheader("💼 按帳戶類型分析")
                by_account = order_analysis['by_account']
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.dataframe(by_account, width="stretch")
                
                with col2:
                    # 帳戶類型分佈圖
                    account_counts = df['account_type'].value_counts()
                    fig = px.pie(values=account_counts.values, 
                               names=account_counts.index,
                               title='帳戶類型分佈')
                    st.plotly_chart(fig, width="stretch")
                
                # 時間分析
                st.subheader("📅 時間分析")
                df['Date'] = df['openTime(UTC+8)'].dt.date
                daily_trades = df.groupby('Date').size()
                
                fig = px.line(x=daily_trades.index, y=daily_trades.values,
                            title='每日交易數量',
                            labels={'x': '日期', 'y': '交易數量'},
                            markers=True)
                st.plotly_chart(fig, width="stretch")
            
            # ========== 資金流水分析 ==========
            if trans_analysis:
                st.subheader("💰 資金流水分析")
                
                trans_summary = trans_analysis['summary']
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("總記錄數", trans_summary['total_transactions'])
                
                with col2:
                    st.metric("總入金", f"+{trans_summary['total_deposit']:.2f} USDT")
                
                with col3:
                    st.metric("淨流入", f"{trans_summary['net_flow']:.2f} USDT",
                             delta_color="normal" if trans_summary['net_flow'] >= 0 else "inverse")
                
                with col4:
                    st.metric("最終餘額", f"{trans_summary['final_balance']:.2f} USDT")
                
                # 按類型分析
                st.write("**按類型分析**")
                by_type = trans_analysis['by_type']
                st.dataframe(by_type, width="stretch")
                
                # 按帳戶類型分析
                st.write("**按帳戶類型分析**")
                by_account = trans_analysis['by_account']
                st.dataframe(by_account, width="stretch")
            
            # ========== 綜合分析 ==========
            if order_analysis and trans_analysis:
                st.subheader("🎯 綜合分析與建議")
                
                # 計算 ROI
                if trans_summary['total_deposit'] > 0:
                    roi = (summary['total_pnl'] / trans_summary['total_deposit']) * 100
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("入金", f"{trans_summary['total_deposit']:.2f} USDT")
                    
                    with col2:
                        st.metric("盈虧", f"{summary['total_pnl']:.2f} USDT")
                    
                    with col3:
                        st.metric("ROI", f"{roi:.2f}%",
                                 delta_color="normal" if roi >= 0 else "inverse")
                
                # 問題診斷
                st.write("**⚠️ 問題診斷**")
                
                issues = []
                
                if summary['win_rate'] < 45:
                    issues.append(f"❌ 勝率過低（{summary['win_rate']:.1f}%），建議 > 50%")
                
                if summary['total_pnl'] < 0:
                    issues.append(f"❌ 總體虧損（{summary['total_pnl']:.2f} USDT）")
                
                if summary['total_fees'] > abs(summary['total_pnl']) * 0.3:
                    fee_pct = summary['total_fees']/abs(summary['total_pnl'])*100 if summary['total_pnl'] != 0 else 0
                    issues.append(f"❌ 手續費過高（{summary['total_fees']:.2f} USDT），佔盈虧 {fee_pct:.1f}%")
                
                avg_holding_hours = summary['avg_holding_time'] / 60
                if avg_holding_hours < 1:
                    issues.append(f"⚠️ 平均持倉時間過短（{avg_holding_hours:.1f} 小時），可能過度交易")
                
                if summary['avg_leverage'] > 10:
                    issues.append(f"⚠️ 平均槓桿過高（{summary['avg_leverage']:.1f}x），風險較大")
                
                if len(issues) > 0:
                    for issue in issues:
                        st.warning(issue)
                else:
                    st.success("✅ 未發現明顯問題")
                
                # 改進建議
                st.write("**💡 改進建議**")
                
                suggestions = []
                
                if summary['win_rate'] < 50:
                    suggestions.append("1. 提高勝率：使用系統輔助，只在高質量信號時交易")
                
                if summary['total_fees'] > 10:
                    suggestions.append("2. 減少手續費：降低交易頻率，每天 1-2 筆即可")
                
                if summary['total_pnl'] < 0:
                    suggestions.append("3. 扭虧為盈：嚴格執行止損，使用系統風險管理")
                
                if avg_holding_hours < 2:
                    suggestions.append("4. 延長持倉：避免頻繁進出，給趨勢時間發展")
                
                if summary['avg_leverage'] > 10:
                    suggestions.append("5. 降低槓桿：建議使用 3-5x 槓桿，降低風險")
                
                suggestions.append("6. 使用系統：運行 `python3 cli.py live --strategy multi-timeframe-aggressive`")
                
                for suggestion in suggestions:
                    st.info(suggestion)
            
            # 詳細記錄
            with st.expander("📋 查看訂單詳細記錄"):
                if order_analysis:
                    st.dataframe(order_analysis['raw_data'], width="stretch", height=400)
            
            with st.expander("📋 查看資金流水詳細記錄"):
                if trans_analysis:
                    st.dataframe(trans_analysis['raw_data'], width="stretch", height=400)
    
    except ImportError as e:
        st.error(f"❌ 無法導入分析器：{str(e)}")
        st.info("請確保 完整交易分析.py 文件存在")
    except Exception as e:
        st.error(f"❌ 分析失敗：{str(e)}")
        import traceback
        st.code(traceback.format_exc())

# ==================== 頁面 5：快速操作 ====================
elif page == "🎯 快速操作":
    st.header("🎯 快速操作")
    
    st.subheader("📊 回測操作")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🚀 運行激進模式回測", width="stretch"):
            with st.spinner("正在運行回測..."):
                import subprocess
                result = subprocess.run(['python3', '-m', 'cli_commands.backtest', '--strategy', 'multi-timeframe-aggressive'], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    st.success("✅ 回測完成！")
                    st.code(result.stdout[-1000:])  # 顯示最後 1000 字符
                else:
                    st.error("❌ 回測失敗")
                    st.code(result.stderr)
    
    with col2:
        if st.button("🎯 運行輕鬆模式回測", width="stretch"):
            with st.spinner("正在運行回測..."):
                import subprocess
                result = subprocess.run(['python3', 'cli.py', 'backtest', 
                                       '--strategy', 'multi-timeframe-relaxed'], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    st.success("✅ 回測完成！")
                else:
                    st.error("❌ 回測失敗")
    
    st.subheader("📈 分析操作")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📊 查看快速總覽", width="stretch"):
            with st.spinner("正在生成總覽..."):
                import subprocess
                result = subprocess.run(['python3', '快速查看.py'], 
                                      capture_output=True, text=True)
                st.code(result.stdout)
    
    with col2:
        if st.button("💰 分析交易記錄", width="stretch"):
            with st.spinner("正在分析..."):
                import subprocess
                result = subprocess.run(['python3', '分析你的交易記錄.py'], 
                                      capture_output=True, text=True)
                st.code(result.stdout)
    
    st.subheader("📚 文檔鏈接")
    
    docs = {
        "新手入門教學": "新手入門教學.md",
        "完整功能與指令手冊": "完整功能與指令手冊.md",
        "給你的使用建議": "給你的使用建議.md",
        "階段性倉位策略": "PROGRESSIVE_POSITION_STRATEGY.md",
        "槓桿與風險管理": "槓桿與風險管理.md"
    }
    
    for name, file in docs.items():
        if st.button(f"📖 {name}", width="stretch"):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    content = f.read()
                st.markdown(content)
            except:
                st.error(f"無法讀取 {file}")

# 底部信息
st.sidebar.markdown("---")
st.sidebar.info("""
**系統信息**
- 版本：1.0.0
- 策略數：5 個
- 功能數：66 個
""")

st.sidebar.success("""
**快速命令**
```bash
# 運行回測
python3 -m cli_commands.backtest --strategy multi-timeframe-aggressive

# 查看結果
python3 快速查看.py

# 啟動 Web
streamlit run web_dashboard.py
```
""")
