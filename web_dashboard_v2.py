#!/usr/bin/env python3
"""
交易系統 Web Dashboard v2
按照系統完整功能清單的 10 大類別組織
"""

import streamlit as st
import pandas as pd
import json
import glob
import time
from datetime import datetime
from pathlib import Path
import plotly.graph_objects as go
import plotly.express as px
import sys
import numpy as np
sys.path.insert(0, '.')

# 導入市場分析器
from src.analysis.market_analyzer import MarketAnalyzer

# 輔助函數：將對象轉換為 JSON 可序列化格式
def make_json_serializable(obj, _seen=None):
    """將對象轉換為 JSON 可序列化格式，避免循環引用"""
    if _seen is None:
        _seen = set()
    
    # 檢查循環引用
    obj_id = id(obj)
    if obj_id in _seen:
        return "<circular reference>"
    
    # 處理基本類型
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    
    # 處理特殊數值類型
    if isinstance(obj, (pd.Timestamp, datetime)):
        return obj.strftime('%Y-%m-%d %H:%M:%S')
    elif isinstance(obj, (np.integer, np.floating)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif pd.isna(obj):
        return None
    
    # 標記為已訪問
    _seen.add(obj_id)
    
    try:
        if isinstance(obj, dict):
            return {k: make_json_serializable(v, _seen) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [make_json_serializable(item, _seen) for item in obj]
        else:
            # 嘗試轉換為字符串
            return str(obj)
    finally:
        # 清理標記
        _seen.discard(obj_id)

# 設置頁面配置
st.set_page_config(
    page_title="交易系統 Dashboard v2",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 標題
st.title("🚀 多策略交易系統 Dashboard v2")

# 側邊欄 - 按照 10 大功能分類
st.sidebar.title("📋 系統功能")

# 主分類
category = st.sidebar.radio(
    "選擇功能類別",
    [
        "1️⃣ 回測系統",
        "2️⃣ 實盤交易", 
        "3️⃣ 參數優化",
        "4️⃣ 虧損分析",
        "5️⃣ 性能監控",
        "6️⃣ 交易覆盤",
        "7️⃣ 策略管理",
        "8️⃣ 風險管理",
        "9️⃣ 數據管理",
        "🔟 系統配置"
    ]
)

# ==================== 1. 回測系統 ====================
if category == "1️⃣ 回測系統":
    st.header("📊 回測系統")
    
    # 子功能選擇
    sub_function = st.sidebar.selectbox(
        "選擇功能",
        [
            "單策略回測結果",
            "多策略組合回測",
            "槓桿對比測試",
            "倉位對比測試",
            "績效指標分析",
            "交易明細查看"
        ]
    )
    
    if sub_function == "交易明細查看":
        st.subheader("📋 交易明細查看")
        
        # 查找所有回測結果
        result_files = glob.glob('backtest_result_*.json')
        
        if not result_files:
            st.warning("⚠️ 沒有找到回測結果文件")
            st.info("請先運行回測：`python3 backtest_multi_timeframe.py`")
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
            
            # 檢查是否有交易記錄
            if 'trades' not in result or not result['trades']:
                st.warning("⚠️ 此回測結果沒有交易記錄")
            else:
                trades = result['trades']
                
                # 轉換為 DataFrame
                trades_df = pd.DataFrame(trades)
                
                # 顯示統計
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("總交易數", len(trades_df))
                
                with col2:
                    winning_trades = len(trades_df[trades_df['pnl'] > 0])
                    st.metric("獲利交易", winning_trades)
                
                with col3:
                    losing_trades = len(trades_df[trades_df['pnl'] < 0])
                    st.metric("虧損交易", losing_trades)
                
                with col4:
                    total_pnl = trades_df['pnl'].sum()
                    st.metric("總損益", f"{total_pnl:.2f} USDT")
                
                # 篩選選項
                st.subheader("🔍 篩選交易")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    trade_type = st.selectbox(
                        "交易類型",
                        ["全部", "獲利", "虧損"]
                    )
                
                with col2:
                    direction = st.selectbox(
                        "方向",
                        ["全部", "做多", "做空"]
                    )
                
                with col3:
                    sort_by = st.selectbox(
                        "排序",
                        ["時間（新到舊）", "時間（舊到新）", "損益（高到低）", "損益（低到高）"]
                    )
                
                # 應用篩選
                filtered_df = trades_df.copy()
                
                if trade_type == "獲利":
                    filtered_df = filtered_df[filtered_df['pnl'] > 0]
                elif trade_type == "虧損":
                    filtered_df = filtered_df[filtered_df['pnl'] < 0]
                
                if direction == "做多":
                    filtered_df = filtered_df[filtered_df['side'] == 'long']
                elif direction == "做空":
                    filtered_df = filtered_df[filtered_df['side'] == 'short']
                
                # 應用排序
                if sort_by == "時間（新到舊）":
                    filtered_df = filtered_df.sort_values('entry_time', ascending=False)
                elif sort_by == "時間（舊到新）":
                    filtered_df = filtered_df.sort_values('entry_time', ascending=True)
                elif sort_by == "損益（高到低）":
                    filtered_df = filtered_df.sort_values('pnl', ascending=False)
                elif sort_by == "損益（低到高）":
                    filtered_df = filtered_df.sort_values('pnl', ascending=True)
                
                # 顯示交易明細
                st.subheader(f"📊 交易明細（共 {len(filtered_df)} 筆）")
                
                # 格式化顯示
                display_df = filtered_df.copy()
                
                # 選擇要顯示的列
                columns_to_show = ['entry_time', 'exit_time', 'side', 'entry_price', 'exit_price', 'quantity', 'pnl', 'pnl_pct']
                
                if all(col in display_df.columns for col in columns_to_show):
                    display_df = display_df[columns_to_show]
                    
                    # 重命名列
                    display_df.columns = ['進場時間', '出場時間', '方向', '進場價', '出場價', '數量', '損益(USDT)', '損益(%)']
                    
                    # 格式化數值
                    display_df['進場價'] = display_df['進場價'].apply(lambda x: f"{x:.2f}")
                    display_df['出場價'] = display_df['出場價'].apply(lambda x: f"{x:.2f}")
                    display_df['數量'] = display_df['數量'].apply(lambda x: f"{x:.4f}")
                    display_df['損益(USDT)'] = display_df['損益(USDT)'].apply(lambda x: f"{x:.2f}")
                    display_df['損益(%)'] = display_df['損益(%)'].apply(lambda x: f"{x:.2f}%")
                    
                    # 顯示表格
                    st.dataframe(display_df, use_container_width=True, height=400)
                    
                    # 下載按鈕
                    csv = filtered_df.to_csv(index=False)
                    st.download_button(
                        label="📥 下載 CSV",
                        data=csv,
                        file_name=f"trades_{selected_file.replace('.json', '.csv')}",
                        mime="text/csv"
                    )
                else:
                    st.dataframe(filtered_df, use_container_width=True, height=400)
    
    elif sub_function == "單策略回測結果":
        st.subheader("📈 單策略回測結果")
        
        # 查找所有回測結果
        result_files = glob.glob('backtest_result_*.json')
        
        if not result_files:
            st.warning("⚠️ 沒有找到回測結果文件")
            st.info("請先運行回測：`python3 backtest_multi_timeframe.py`")
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
                total_return = result.get('total_pnl_pct', 0)
                st.metric(
                    "總收益",
                    f"+{total_return:.2f}%",
                    delta=f"{result.get('total_pnl', 0):.2f} USDT"
                )
            
            with col2:
                st.metric(
                    "勝率",
                    f"{result['win_rate']:.2f}%",
                    delta=f"{result['winning_trades']}/{result['total_trades']}"
                )
            
            with col3:
                max_dd = result.get('max_drawdown_pct', result.get('max_drawdown', 0))
                st.metric(
                    "最大回撤",
                    f"-{max_dd:.2f}%",
                    delta=f"-{result.get('max_drawdown', 0):.2f} USDT",
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
                st.write(f"- 淨損益：{result.get('total_pnl', 0):.2f} USDT")
                
                st.write("**交易統計**")
                st.write(f"- 總交易數：{result['total_trades']}")
                st.write(f"- 獲利交易：{result['winning_trades']}")
                st.write(f"- 虧損交易：{result['losing_trades']}")
            
            with col2:
                st.write("**損益分析**")
                st.write(f"- 平均獲利：{result.get('avg_win', 0):.2f} USDT")
                st.write(f"- 平均虧損：{result.get('avg_loss', 0):.2f} USDT")
                st.write(f"- 獲利因子：{result['profit_factor']:.2f}")
                
                st.write("**風險指標**")
                st.write(f"- 最大回撤：{max_dd:.2f}%")
                st.write(f"- 夏普比率：{result['sharpe_ratio']:.2f}")
            
            # 權益曲線
            if 'equity_curve' in result and result['equity_curve']:
                st.subheader("📉 權益曲線")
                
                try:
                    equity_curve = result['equity_curve']
                    
                    if isinstance(equity_curve, list):
                        if len(equity_curve) > 0 and isinstance(equity_curve[0], dict):
                            equity_df = pd.DataFrame(equity_curve)
                            equity_values = equity_df['equity'].values if 'equity' in equity_df.columns else equity_df.iloc[:, 0].values
                        else:
                            equity_values = equity_curve
                    elif isinstance(equity_curve, dict):
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
                    
                    st.plotly_chart(fig, use_container_width=True)
                except Exception as e:
                    st.warning(f"⚠️ 無法顯示權益曲線：{str(e)}")
    
    elif sub_function == "槓桿對比測試":
        st.subheader("📈 槓桿對比分析")
        
        leverage_files = glob.glob('leverage_comparison_*.csv')
        
        if not leverage_files:
            st.warning("⚠️ 沒有找到槓桿對比結果")
            st.info("請先運行：`python3 backtest_leverage_comparison.py`")
        else:
            selected_file = st.selectbox(
                "選擇對比結果",
                leverage_files,
                format_func=lambda x: x.replace('leverage_comparison_', '').replace('.csv', '')
            )
            
            df = pd.read_csv(selected_file)
            df['risk_adjusted'] = df['total_return'] / df['max_drawdown']
            
            st.subheader("📊 對比表格")
            
            display_df = df[['leverage', 'total_return', 'max_drawdown', 'win_rate', 'risk_adjusted']].copy()
            display_df.columns = ['槓桿', '收益率(%)', '最大回撤(%)', '勝率(%)', '風險調整收益']
            display_df['收益率(%)'] = display_df['收益率(%)'].round(2)
            display_df['最大回撤(%)'] = display_df['最大回撤(%)'].round(2)
            display_df['勝率(%)'] = display_df['勝率(%)'].round(2)
            display_df['風險調整收益'] = display_df['風險調整收益'].round(2)
            
            st.dataframe(display_df, use_container_width=True)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📈 收益率 vs 槓桿")
                fig1 = px.bar(df, x='leverage', y='total_return', 
                             title='不同槓桿的收益率',
                             labels={'leverage': '槓桿', 'total_return': '收益率(%)'},
                             color='total_return',
                             color_continuous_scale='RdYlGn')
                st.plotly_chart(fig1, use_container_width=True)
            
            with col2:
                st.subheader("📉 回撤 vs 槓桿")
                fig2 = px.bar(df, x='leverage', y='max_drawdown',
                             title='不同槓桿的最大回撤',
                             labels={'leverage': '槓桿', 'max_drawdown': '最大回撤(%)'},
                             color='max_drawdown',
                             color_continuous_scale='RdYlGn_r')
                st.plotly_chart(fig2, use_container_width=True)
            
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

# ==================== 2. 實盤交易 ====================
elif category == "2️⃣ 實盤交易":
    st.header("🔴 實盤交易")
    
    sub_function = st.sidebar.selectbox(
        "選擇功能",
        [
            "實盤狀態監控",
            "當前持倉",
            "實盤交易記錄",
            "Telegram 通知設置"
        ]
    )
    
    if sub_function == "實盤狀態監控":
        st.subheader("📡 實盤狀態監控")
        
        # 檢查是否有實盤日誌
        log_file = Path("logs/trading.log")
        
        if not log_file.exists():
            st.warning("⚠️ 沒有找到實盤日誌文件")
            st.info("💡 實盤交易功能需要通過命令行啟動：")
            st.code("python3 cli.py live --strategy multi-timeframe-aggressive")
        else:
            # 讀取最新的日誌
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    recent_logs = lines[-100:]  # 最近 100 行
                
                # 解析日誌統計
                total_lines = len(recent_logs)
                error_count = sum(1 for line in recent_logs if 'ERROR' in line)
                warning_count = sum(1 for line in recent_logs if 'WARNING' in line)
                trade_signals = sum(1 for line in recent_logs if '交易信號' in line or 'SIGNAL' in line)
                
                # 顯示統計
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("日誌行數", total_lines)
                
                with col2:
                    st.metric("交易信號", trade_signals)
                
                with col3:
                    st.metric("警告", warning_count, delta_color="inverse")
                
                with col4:
                    st.metric("錯誤", error_count, delta_color="inverse")
                
                # 顯示最新日誌
                st.subheader("📝 最新日誌（最近 50 行）")
                
                log_text = ''.join(recent_logs[-50:])
                st.text_area("日誌內容", log_text, height=400)
                
                # 自動刷新選項
                auto_refresh = st.checkbox("自動刷新（每 5 秒）")
                
                if auto_refresh:
                    import time
                    time.sleep(5)
                    st.rerun()
            
            except Exception as e:
                st.error(f"❌ 讀取日誌失敗：{str(e)}")
        
        st.divider()
        
        st.write("**功能說明**：")
        st.write("- 單策略實盤運行")
        st.write("- 多策略並行運行")
        st.write("- 乾跑模式（不實際下單）")
        st.write("- 自動下單")
        st.write("- Telegram 實時通知")
        st.write("- 自動風險控制")
    
    elif sub_function == "當前持倉":
        st.subheader("💼 當前持倉")
        
        # 檢查是否有持倉記錄文件
        position_file = Path("data/trade_history/current_positions.json")
        
        if not position_file.exists():
            st.info("⚠️ 沒有當前持倉記錄")
            st.write("實盤運行時會自動記錄持倉信息")
        else:
            try:
                with open(position_file, 'r') as f:
                    positions = json.load(f)
                
                if not positions:
                    st.info("✅ 當前無持倉")
                else:
                    st.write(f"**持倉數量**：{len(positions)}")
                    
                    # 顯示每個持倉
                    for i, pos in enumerate(positions):
                        with st.expander(f"持倉 {i+1}: {pos.get('symbol', 'N/A')} - {pos.get('side', 'N/A')}"):
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                st.write(f"**交易對**：{pos.get('symbol', 'N/A')}")
                                st.write(f"**方向**：{pos.get('side', 'N/A')}")
                                st.write(f"**數量**：{pos.get('quantity', 0):.4f}")
                            
                            with col2:
                                st.write(f"**進場價**：{pos.get('entry_price', 0):.2f}")
                                st.write(f"**當前價**：{pos.get('current_price', 0):.2f}")
                                st.write(f"**槓桿**：{pos.get('leverage', 1)}x")
                            
                            with col3:
                                pnl = pos.get('unrealized_pnl', 0)
                                pnl_pct = pos.get('unrealized_pnl_pct', 0)
                                st.metric("未實現損益", f"{pnl:.2f} USDT", f"{pnl_pct:.2f}%")
                                st.write(f"**止損價**：{pos.get('stop_loss', 0):.2f}")
                                st.write(f"**目標價**：{pos.get('take_profit', 0):.2f}")
            
            except Exception as e:
                st.error(f"❌ 讀取持倉失敗：{str(e)}")
    
    elif sub_function == "實盤交易記錄":
        st.subheader("📊 實盤交易記錄")
        
        # 檢查是否有交易記錄
        trade_history_files = glob.glob('data/trade_history/trades_*.json')
        
        if not trade_history_files:
            st.info("⚠️ 沒有實盤交易記錄")
        else:
            # 選擇日期
            selected_file = st.selectbox(
                "選擇日期",
                trade_history_files,
                format_func=lambda x: x.replace('data/trade_history/trades_', '').replace('.json', '')
            )
            
            # 讀取交易記錄
            with open(selected_file, 'r') as f:
                trades = json.load(f)
            
            if not trades:
                st.info("該日期沒有交易記錄")
            else:
                # 轉換為 DataFrame
                trades_df = pd.DataFrame(trades)
                
                # 顯示統計
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("總交易數", len(trades_df))
                
                with col2:
                    winning = len(trades_df[trades_df['pnl'] > 0])
                    st.metric("獲利交易", winning)
                
                with col3:
                    losing = len(trades_df[trades_df['pnl'] < 0])
                    st.metric("虧損交易", losing)
                
                with col4:
                    total_pnl = trades_df['pnl'].sum()
                    st.metric("總損益", f"{total_pnl:.2f} USDT")
                
                # 顯示交易列表
                st.dataframe(trades_df, use_container_width=True)
    
    else:  # Telegram 通知設置
        st.subheader("📢 Telegram 通知設置")
        
        try:
            import yaml
            with open('system_config.yaml', 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            telegram_config = config.get('notifications', {}).get('telegram', {})
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**當前設置**")
                enabled = telegram_config.get('enabled', False)
                st.write(f"- 狀態：{'✅ 啟用' if enabled else '❌ 禁用'}")
                st.write(f"- Bot Token：{'已設置' if telegram_config.get('bot_token') else '未設置'}")
                st.write(f"- Chat ID：{'已設置' if telegram_config.get('chat_id') else '未設置'}")
            
            with col2:
                st.write("**通知類型**")
                notify_types = telegram_config.get('notify_on', [])
                st.write(f"- 交易信號：{'✅' if 'signal' in notify_types else '❌'}")
                st.write(f"- 訂單執行：{'✅' if 'order' in notify_types else '❌'}")
                st.write(f"- 風險警報：{'✅' if 'risk' in notify_types else '❌'}")
                st.write(f"- 錯誤：{'✅' if 'error' in notify_types else '❌'}")
            
            st.divider()
            
            st.write("**測試 Telegram 連接**")
            if st.button("發送測試消息"):
                st.info("請在命令行運行：`python3 test_telegram.py`")
        
        except Exception as e:
            st.error(f"❌ 讀取配置失敗：{str(e)}")

# ==================== 3. 參數優化 ====================
elif category == "3️⃣ 參數優化":
    st.header("🔧 參數優化")
    
    sub_function = st.sidebar.selectbox(
        "選擇功能",
        [
            "優化結果查看",
            "參數敏感度分析",
            "優化任務管理"
        ]
    )
    
    if sub_function == "優化結果查看":
        st.subheader("📊 優化結果查看")
        
        # 查找優化結果文件
        optimize_files = glob.glob('data/backtest_results/optimize_*.json')
        
        if not optimize_files:
            st.warning("⚠️ 沒有找到優化結果文件")
            st.info("請先運行優化：`python3 cli.py optimize --strategy multi-timeframe-aggressive --method grid`")
        else:
            # 選擇優化結果
            selected_file = st.selectbox(
                "選擇優化結果",
                optimize_files,
                format_func=lambda x: x.replace('data/backtest_results/optimize_', '').replace('.json', '')
            )
            
            # 讀取結果
            with open(selected_file, 'r') as f:
                result = json.load(f)
            
            # 顯示基本信息
            st.subheader("📋 優化信息")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.write(f"**優化方法**：{result.get('method', 'N/A')}")
                st.write(f"**測試組合數**：{result.get('total_combinations_tested', 0)}")
            
            with col2:
                st.write(f"**優化時間**：{result.get('optimization_time', 0):.2f} 秒")
                st.write(f"**最佳評分**：{result.get('best_score', 0):.4f}")
            
            with col3:
                train_perf = result.get('train_performance', {})
                val_perf = result.get('validation_performance', {})
                st.write(f"**訓練集勝率**：{train_perf.get('win_rate', 0):.2%}")
                st.write(f"**驗證集勝率**：{val_perf.get('win_rate', 0):.2%}")
            
            # 最佳參數
            st.subheader("🎯 最佳參數")
            
            best_params = result.get('best_params', {})
            
            if best_params:
                # 分組顯示參數
                param_groups = {}
                for key, value in best_params.items():
                    if '.' in key:
                        group = key.split('.')[0]
                        param_name = '.'.join(key.split('.')[1:])
                    else:
                        group = '其他'
                        param_name = key
                    
                    if group not in param_groups:
                        param_groups[group] = {}
                    param_groups[group][param_name] = value
                
                # 顯示分組參數
                cols = st.columns(len(param_groups))
                
                for i, (group, params) in enumerate(param_groups.items()):
                    with cols[i]:
                        st.write(f"**{group}**")
                        for param, value in params.items():
                            if isinstance(value, float):
                                st.write(f"- {param}: {value:.4f}")
                            else:
                                st.write(f"- {param}: {value}")
            
            # 性能對比
            st.subheader("📈 性能對比")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**訓練集**")
                st.write(f"- 總交易數：{train_perf.get('total_trades', 0)}")
                st.write(f"- 勝率：{train_perf.get('win_rate', 0):.2%}")
                st.write(f"- 總損益：{train_perf.get('total_pnl', 0):.2f} USDT")
                st.write(f"- 獲利因子：{train_perf.get('profit_factor', 0):.2f}")
                st.write(f"- 夏普比率：{train_perf.get('sharpe_ratio', 0):.2f}")
            
            with col2:
                st.write("**驗證集**")
                st.write(f"- 總交易數：{val_perf.get('total_trades', 0)}")
                st.write(f"- 勝率：{val_perf.get('win_rate', 0):.2%}")
                st.write(f"- 總損益：{val_perf.get('total_pnl', 0):.2f} USDT")
                st.write(f"- 獲利因子：{val_perf.get('profit_factor', 0):.2f}")
                st.write(f"- 夏普比率：{val_perf.get('sharpe_ratio', 0):.2f}")
            
            # 參數敏感度
            if 'parameter_sensitivity' in result:
                st.subheader("📊 參數敏感度")
                
                sensitivity = result['parameter_sensitivity']
                
                for param_name, scores in sensitivity.items():
                    if scores:
                        st.write(f"**{param_name}**")
                        
                        # 轉換為 DataFrame
                        df = pd.DataFrame(scores, columns=['值', '評分'])
                        
                        # 繪製圖表
                        fig = px.scatter(df, x='值', y='評分', 
                                       title=f'{param_name} 敏感度分析',
                                       trendline="lowess")
                        st.plotly_chart(fig, use_container_width=True)
    
    elif sub_function == "優化任務管理":
        st.subheader("🎯 參數優化")
        st.info("💡 參數優化需要通過命令行啟動：")
        st.code("python3 cli.py optimize --strategy multi-timeframe-aggressive --method grid")
        
        st.write("**支持的優化方法**：")
        st.write("- 網格搜索（Grid Search）")
        st.write("- 隨機搜索（Random Search）")
        st.write("- 貝葉斯優化（Bayesian Optimization）")

# ==================== 4. 虧損分析 ====================
elif category == "4️⃣ 虧損分析":
    st.header("📉 虧損分析")
    
    sub_function = st.sidebar.selectbox(
        "選擇功能",
        [
            "虧損原因分類",
            "虧損模式識別",
            "改進建議"
        ]
    )
    
    st.subheader("🔍 虧損分析工具")
    st.info("💡 虧損分析需要通過 Python 腳本運行：")
    st.code("python3 example_loss_analyzer.py")

# ==================== 5. 性能監控 ====================
elif category == "5️⃣ 性能監控":
    st.header("📊 性能監控")
    
    sub_function = st.sidebar.selectbox(
        "選擇功能",
        [
            "實時指標追蹤",
            "異常檢測",
            "策略退化檢測"
        ]
    )
    
    st.subheader("📈 性能監控")
    st.info("💡 性能監控需要通過 Python 腳本運行：")
    st.code("python3 example_performance_monitor.py")

# ==================== 6. 交易覆盤 ====================
elif category == "6️⃣ 交易覆盤":
    st.header("📝 交易覆盤")
    
    sub_function = st.sidebar.selectbox(
        "選擇功能",
        [
            "BingX 交易分析",
            "交易記錄管理",
            "執行質量評分",
            "虧損分析"
        ]
    )
    
    if sub_function == "BingX 交易分析":
        st.subheader("💰 BingX 交易分析")
        
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
    
    elif sub_function == "交易記錄管理":
        st.subheader("📝 交易記錄管理")
        
        st.info("""
        **功能說明**：
        - 上傳 BingX Order_History 文件（Excel 或 CSV）
        - 自動按 Order No 去重
        - 按天保存到 `data/review_history/bingx/orders/`
        - 支持增量更新
        """)
        
        # 步驟 1：選擇交易所
        st.subheader("1️⃣ 選擇交易所")
        exchange = st.radio(
            "交易所",
            ["BingX", "Binance（未來）", "OKX（未來）"],
            index=0,
            help="目前只支持 BingX，其他交易所即將推出"
        )
        
        if exchange != "BingX":
            st.warning("⚠️ 目前只支持 BingX")
            st.stop()
        else:
            # 步驟 2：上傳文件
            st.subheader("2️⃣ 上傳 Order_History")
            
            uploaded_file = st.file_uploader(
                "選擇 Order_History 文件",
                type=['xlsx', 'xls', 'csv'],
                help="從 BingX 匯出的 Order_History 文件"
            )
        
        if uploaded_file is not None:
            try:
                # 檢測文件真實類型
                uploaded_file.seek(0)
                file_header = uploaded_file.read(4)
                uploaded_file.seek(0)
                
                is_excel = file_header[:2] == b'PK'
                file_extension = uploaded_file.name.split('.')[-1].lower()
                
                if is_excel:
                    st.caption(f"📌 檢測到 Excel 格式（副檔名：.{file_extension}）")
                    file_extension = 'xlsx'
                
                # 讀取文件
                all_orders = []
                
                if file_extension == 'csv':
                    # CSV 格式
                    encodings = ['utf-8', 'utf-8-sig', 'big5', 'gb2312', 'gbk', 'gb18030', 'latin1', 'cp1252']
                    df = None
                    
                    for encoding in encodings:
                        try:
                            uploaded_file.seek(0)
                            df = pd.read_csv(uploaded_file, encoding=encoding)
                            st.caption(f"使用編碼：{encoding}")
                            break
                        except:
                            continue
                    
                    if df is None:
                        st.error("❌ 無法讀取 CSV 文件")
                    else:
                        # 推斷帳戶類型
                        if 'Standard' in uploaded_file.name:
                            df['account_type'] = 'Standard_Futures'
                        elif 'Perpetual' in uploaded_file.name or 'USDⓈ' in uploaded_file.name:
                            df['account_type'] = 'USDⓢ_M_Perpetual_Futures'
                        else:
                            df['account_type'] = 'Unknown'
                        
                        all_orders.append(df)
                
                else:
                    # Excel 格式（多個工作表）
                    xl = pd.ExcelFile(uploaded_file)
                    
                    for sheet_name in xl.sheet_names:
                        df = pd.read_excel(uploaded_file, sheet_name=sheet_name)
                        if len(df) > 0:
                            df['account_type'] = sheet_name
                            all_orders.append(df)
                
                if not all_orders:
                    st.warning("⚠️ 文件中沒有數據")
                else:
                    # 統一欄位名稱
                    for df in all_orders:
                        # 統一 Order No 欄位
                        for col in df.columns:
                            if col in ['Order No.', 'order_no', 'OrderNo']:
                                df.rename(columns={col: 'Order No'}, inplace=True)
                                break
                        
                        # 統一時間欄位
                        for col in df.columns:
                            if col in ['Time(UTC+8)', 'closeTime(UTC+8)', 'close_time', 'time']:
                                df.rename(columns={col: 'closeTime(UTC+8)'}, inplace=True)
                                break
                        
                        # 統一其他關鍵欄位
                        rename_map = {
                            # Perpetual 的欄位映射
                            'Pair': 'symbol',
                            'Type': 'side',
                            'Quantity': 'quantity',
                            'Leverage': 'leverage',
                            'Fee': 'fees',
                            # Standard 的欄位映射
                            'category': 'symbol',
                            'direction': 'side',
                            'margin': 'quantity',  # 使用保證金作為數量的替代
                            'closeType': 'close_type'  # 平倉類型
                        }
                        
                        for old_name, new_name in rename_map.items():
                            if old_name in df.columns:
                                # 如果目標欄位已存在且有值，不覆蓋
                                if new_name in df.columns:
                                    # 填充空值
                                    df[new_name].fillna(df[old_name], inplace=True)
                                else:
                                    df.rename(columns={old_name: new_name}, inplace=True)
                        
                        # 處理 side 欄位：提取真正的方向
                        # 'Close Long' -> 'Long', 'Open Short' -> 'Short'
                        if 'side' in df.columns:
                            df['side'] = df['side'].astype(str).str.upper()
                            df['direction'] = df['side'].apply(lambda x: 
                                'Long' if 'LONG' in x else ('Short' if 'SHORT' in x else x)
                            )
                            # 標記動作類型
                            df['action'] = df['side'].apply(lambda x: 
                                'Open' if 'OPEN' in x else ('Close' if 'CLOSE' in x else 'Unknown')
                            )
                    
                    # 合併所有訂單
                    combined_df = pd.concat(all_orders, ignore_index=True)
                    
                    # 處理 Perpetual 帳戶：以 Close 為主（因為只有 Close 有 PNL）
                    final_orders = []
                    
                    # 分離 Standard 和 Perpetual
                    standard_df = combined_df[combined_df['account_type'] == 'Standard_Futures']
                    perpetual_df = combined_df[combined_df['account_type'] != 'Standard_Futures']
                    
                    # Standard 直接加入（已經是完整記錄）
                    for _, row in standard_df.iterrows():
                        final_orders.append(row.to_dict())
                    
                    # Perpetual：智能配對 Open 和 Close
                    # 策略：按 symbol + direction + leverage 配對，如果找不到則按時間順序配對
                    if len(perpetual_df) > 0 and 'action' in perpetual_df.columns:
                        open_records = perpetual_df[perpetual_df['action'] == 'Open'].copy()
                        close_records = perpetual_df[perpetual_df['action'] == 'Close'].copy()
                        
                        st.info(f"🔍 調試信息：Perpetual 總記錄 {len(perpetual_df)} 筆，Open {len(open_records)} 筆，Close {len(close_records)} 筆")
                        
                        # 找到時間欄位
                        time_col_for_sort = None
                        for col in ['closeTime(UTC+8)', 'Time(UTC+8)', 'time', 'close_time']:
                            if col in perpetual_df.columns:
                                time_col_for_sort = col
                                break
                        
                        # 先按時間排序
                        if time_col_for_sort:
                            open_records[time_col_for_sort] = pd.to_datetime(open_records[time_col_for_sort], errors='coerce')
                            close_records[time_col_for_sort] = pd.to_datetime(close_records[time_col_for_sort], errors='coerce')
                            open_records = open_records.sort_values(time_col_for_sort)
                            close_records = close_records.sort_values(time_col_for_sort)
                        
                        processed_closes = set()
                        
                        # 為每個 Close 找到最佳匹配的 Open
                        for close_idx, close_row in close_records.iterrows():
                            symbol = close_row.get('symbol', '')
                            direction = close_row.get('direction', '')
                            leverage = close_row.get('leverage') or close_row.get('Leverage', 0)
                            close_time = close_row.get(time_col_for_sort) if time_col_for_sort else None
                            
                            # 找到所有可能的 Open（相同 symbol + direction，時間在 Close 之前）
                            candidate_opens = []
                            
                            for open_idx, open_row in open_records.iterrows():
                                open_symbol = open_row.get('symbol', '')
                                open_direction = open_row.get('direction', '')
                                open_leverage = open_row.get('leverage') or open_row.get('Leverage', 0)
                                open_time = open_row.get(time_col_for_sort) if time_col_for_sort else None
                                
                                # 基本匹配：相同 symbol + direction
                                if open_symbol == symbol and open_direction == direction:
                                    # 檢查時間順序
                                    if open_time and close_time:
                                        if pd.notna(open_time) and pd.notna(close_time):
                                            if open_time >= close_time:
                                                continue  # Open 不能晚於或等於 Close
                                            
                                            # 時間窗口檢查（7天內）
                                            time_diff = (close_time - open_time).total_seconds() / 86400
                                            if time_diff > 7:
                                                continue
                                    
                                    # 計算匹配分數
                                    score = 0
                                    
                                    # 槓桿匹配（最重要）
                                    try:
                                        if float(open_leverage) == float(leverage):
                                            score += 100  # 槓桿相同，高分
                                    except:
                                        pass
                                    
                                    # 時間越近越好
                                    if open_time and close_time:
                                        if pd.notna(open_time) and pd.notna(close_time):
                                            time_diff_minutes = (close_time - open_time).total_seconds() / 60
                                            score += max(0, 50 - time_diff_minutes / 60)  # 時間越近分數越高
                                    
                                    candidate_opens.append({
                                        'idx': open_idx,
                                        'row': open_row,
                                        'score': score,
                                        'leverage': open_leverage,
                                        'time': open_time
                                    })
                            
                            # 選擇最佳匹配（分數最高的）
                            if candidate_opens:
                                best_match = max(candidate_opens, key=lambda x: x['score'])
                                open_row = best_match['row']
                                
                                # 創建合併記錄（使用 Open 的時間和價格，Close 的 PNL）
                                merged_record = close_row.to_dict()
                                
                                # 補充 Open 時間信息
                                if time_col_for_sort:
                                    merged_record['openTime(UTC+8)'] = open_row.get(time_col_for_sort)
                                
                                # 補充 Open 價格（進場價）
                                # Perpetual: Open 的 DealPrice 是進場價
                                open_price = open_row.get('DealPrice', 0)
                                if not open_price or pd.isna(open_price):
                                    open_price = open_row.get('AvgPrice', 0)
                                if not open_price or pd.isna(open_price):
                                    open_price = 0
                                else:
                                    open_price = float(open_price)
                                
                                merged_record['openPrice'] = open_price
                                
                                # 確保 Close 的 DealPrice 被正確設置為出場價
                                # Perpetual: Close 的 DealPrice 是出場價
                                close_price = close_row.get('DealPrice', 0)
                                if not close_price or pd.isna(close_price):
                                    close_price = 0
                                merged_record['closePrice'] = float(close_price) if close_price else 0
                                
                                # 如果槓桿不同，標記為加倉換倍數
                                try:
                                    open_lev = open_row.get('leverage') or open_row.get('Leverage', 0)
                                    close_lev = close_row.get('leverage') or close_row.get('Leverage', 0)
                                    if open_lev and close_lev and float(open_lev) != float(close_lev):
                                        merged_record['note'] = f"加倉換倍數 ({open_lev}X → {close_lev}X)"
                                except:
                                    pass
                                
                                final_orders.append(merged_record)
                                processed_closes.add(close_idx)
                            else:
                                # 沒有找到匹配的 Open，直接保存 Close
                                # 這種情況下沒有進場價和進場時間
                                close_dict = close_row.to_dict()
                                # 設置 closePrice（出場價）
                                close_price = close_row.get('DealPrice', 0)
                                if close_price and not pd.isna(close_price):
                                    close_dict['closePrice'] = float(close_price)
                                final_orders.append(close_dict)
                                processed_closes.add(close_idx)
                        
                        matched_count = len([o for o in final_orders if o.get('account_type') != 'Standard_Futures' and 'openTime(UTC+8)' in o])
                        unmatched_count = len(close_records) - matched_count
                        st.info(f"🔍 配對結果：已配對 {matched_count} 筆（找到對應 Open），未配對 {unmatched_count} 筆（無對應 Open）")
                    
                    # 轉換回 DataFrame
                    combined_df = pd.DataFrame(final_orders)
                    
                    perpetual_count = len(combined_df) - len(standard_df)
                    st.info(f"🔍 Standard {len(standard_df)} 筆 + Perpetual {perpetual_count} 筆 = 總共 {len(combined_df)} 筆")
                    
                    perpetual_count = len(combined_df) - len(standard_df)
                    st.info(f"🔍 調試信息：Standard {len(standard_df)} 筆 + Perpetual {perpetual_count} 筆 = 總共 {len(combined_df)} 筆")
                    
                    # 步驟 3：預覽數據
                    st.subheader("3️⃣ 預覽數據")
                    
                    # 識別 Order No 欄位（應該已經統一為 'Order No'）
                    order_no_col = 'Order No'
                    
                    if order_no_col not in combined_df.columns:
                        st.error("❌ 找不到 Order No 欄位")
                        st.write("可用欄位：", ", ".join(combined_df.columns.tolist()))
                    else:
                        # 統計信息
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.metric("總訂單數", len(combined_df))
                        
                        with col2:
                            # 時間範圍
                            time_cols = ['closeTime(UTC+8)', 'close_time', 'time']
                            time_col = None
                            for col in time_cols:
                                if col in combined_df.columns:
                                    time_col = col
                                    break
                            
                            if time_col:
                                combined_df[time_col] = pd.to_datetime(combined_df[time_col], errors='coerce')
                                min_date = combined_df[time_col].min()
                                max_date = combined_df[time_col].max()
                                st.write(f"**時間範圍**")
                                st.write(f"{min_date.date()} 至 {max_date.date()}")
                        
                        with col3:
                            # 帳戶類型分佈
                            account_counts = combined_df['account_type'].value_counts()
                            st.write("**帳戶類型**")
                            for acc_type, count in account_counts.items():
                                st.write(f"- {acc_type}: {count}")
                        
                        # 檢查重複
                        st.subheader("4️⃣ 檢查重複")
                        
                        # 載入已存在的 Order No
                        order_index_file = Path("data/review_history/bingx/metadata/order_index.json")
                        existing_orders = set()
                        
                        if order_index_file.exists():
                            try:
                                with open(order_index_file, 'r', encoding='utf-8') as f:
                                    index_data = json.load(f)
                                    existing_orders = set(index_data.get('order_numbers', []))
                            except:
                                pass
                        
                        # 檢查當前文件中的 Order No
                        current_orders = set(combined_df[order_no_col].astype(str).tolist())
                        duplicate_orders = current_orders & existing_orders
                        new_orders = current_orders - existing_orders
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.metric("新訂單", len(new_orders), delta="將被保存")
                        
                        with col2:
                            st.metric("重複訂單", len(duplicate_orders), delta="將被跳過", delta_color="inverse")
                        
                        if len(duplicate_orders) > 0:
                            with st.expander(f"查看 {len(duplicate_orders)} 個重複的 Order No"):
                                st.write(list(duplicate_orders)[:20])
                                if len(duplicate_orders) > 20:
                                    st.write(f"... 還有 {len(duplicate_orders) - 20} 個")
                        
                        # 步驟 5：處理選項
                        st.subheader("5️⃣ 處理選項")
                        
                        duplicate_action = st.radio(
                            "重複訂單處理方式",
                            ["跳過重複（推薦）", "更新重複", "保留所有"],
                            help="跳過：只保存新訂單 | 更新：用新數據覆蓋 | 保留所有：允許重複"
                        )
                        
                        # 步驟 6：轉換並保存
                        st.subheader("6️⃣ 轉換並保存")
                        
                        if st.button("🔄 轉換並保存", type="primary"):
                            try:
                                with st.spinner("正在處理..."):
                                    # 創建目錄
                                    base_dir = Path("data/review_history/bingx")
                                    orders_dir = base_dir / "orders"
                                    metadata_dir = base_dir / "metadata"
                                    
                                    orders_dir.mkdir(parents=True, exist_ok=True)
                                    metadata_dir.mkdir(parents=True, exist_ok=True)
                                    
                                    # 處理每個訂單
                                    saved_count = 0
                                    skipped_count = 0
                                    updated_count = 0
                                    
                                    # 按日期分組
                                    if time_col:
                                        combined_df['date'] = pd.to_datetime(combined_df[time_col], errors='coerce').dt.date
                                        grouped = combined_df.groupby('date')
                                    else:
                                        # 如果沒有時間欄位，全部保存到一個文件
                                        grouped = [(datetime.now().date(), combined_df)]
                                    
                                    new_order_numbers = []
                                    
                                    for date, group in grouped:
                                        if pd.isna(date):
                                            continue
                                        
                                        # 文件路徑
                                        year = date.year
                                        month = f"{date.month:02d}"
                                        day_file = f"{date.strftime('%Y%m%d')}.json"
                                        
                                        file_path = orders_dir / str(year) / month / day_file
                                        file_path.parent.mkdir(parents=True, exist_ok=True)
                                        
                                        # 讀取已存在的數據
                                        existing_data = []
                                        if file_path.exists():
                                            try:
                                                with open(file_path, 'r', encoding='utf-8') as f:
                                                    existing_data = json.load(f)
                                            except:
                                                pass
                                        
                                        # 轉換當天的訂單
                                        day_orders = []
                                        
                                        for _, row in group.iterrows():
                                            order_no = str(row.get(order_no_col, ''))
                                            
                                            # 檢查重複
                                            if order_no in existing_orders:
                                                if "跳過" in duplicate_action:
                                                    skipped_count += 1
                                                    continue
                                                elif "更新" in duplicate_action:
                                                    # 從已存在數據中移除舊的
                                                    existing_data = [o for o in existing_data if o.get('order_no') != order_no]
                                                    updated_count += 1
                                            
                                            # 轉換為標準格式
                                            # 安全獲取欄位值，處理可能的缺失
                                            def safe_get(row, keys, default=''):
                                                """嘗試多個可能的欄位名稱"""
                                                if isinstance(keys, str):
                                                    keys = [keys]
                                                for key in keys:
                                                    if key in row.index and pd.notna(row.get(key)):
                                                        return row.get(key)
                                                return default
                                            
                                            def safe_float(value, default=0):
                                                """安全轉換為浮點數"""
                                                try:
                                                    if pd.isna(value) or value == '':
                                                        return default
                                                    # 處理槓桿格式 '5X' -> 5
                                                    if isinstance(value, str):
                                                        value = value.upper().replace('X', '').strip()
                                                    return float(value)
                                                except:
                                                    return default
                                            
                                            # 獲取手續費（取絕對值，因為有些交易所用負數表示）
                                            fee_value = safe_float(safe_get(row, ['fees', 'Fee'], 0))
                                            fee_value = abs(fee_value)  # 統一為正數
                                            
                                            # 獲取平倉類型並翻譯
                                            close_type_raw = str(safe_get(row, ['close_type', 'closeType'], ''))
                                            close_type_map = {
                                                'manual close': '手動平倉',
                                                'Take profit/ Stop loss': '止盈止損',
                                                'liqudated': '爆倉',
                                                'liquidated': '爆倉',
                                                '1': '系統平倉',
                                                '': '未知'
                                            }
                                            close_type = close_type_map.get(close_type_raw, close_type_raw)
                                            
                                            # 創建合併記錄
                                            order = {
                                                'order_no': order_no,
                                                'trade_id': f"bingx_{order_no}",
                                                'source': 'bingx',
                                                'account_type': str(row.get('account_type', '')),
                                                'symbol': str(safe_get(row, ['symbol', 'Pair'], '')),
                                                'side': str(safe_get(row, ['side', 'Type'], '')),
                                                'direction': str(safe_get(row, ['direction'], '')),
                                                'close_type': close_type,
                                                'open_time': str(safe_get(row, ['openTime(UTC+8)', 'closeTime(UTC+8)'], '')),
                                                'close_time': str(safe_get(row, ['closeTime(UTC+8)', 'Time(UTC+8)'], '')),
                                                'entry_price': safe_float(safe_get(row, ['openPrice', 'AvgPrice'], 0)),
                                                'exit_price': safe_float(safe_get(row, ['closePrice', 'DealPrice'], 0)),
                                                'quantity': safe_float(safe_get(row, ['quantity', 'Quantity'], 0)),
                                                'leverage': safe_float(safe_get(row, ['leverage', 'Leverage'], 1), 1),
                                                'pnl': safe_float(safe_get(row, ['Realized PNL'], 0)),
                                                'fee': fee_value,
                                                'uploaded_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                                'file_source': uploaded_file.name
                                            }
                                            
                                            # 如果是分批平倉的合併記錄，添加備註
                                            if 'note' in row.index and pd.notna(row.get('note')):
                                                order['note'] = str(row.get('note'))
                                            
                                            day_orders.append(order)
                                            new_order_numbers.append(order_no)
                                            saved_count += 1
                                        
                                        # 合併並保存
                                        if day_orders:
                                            all_day_orders = existing_data + day_orders
                                            
                                            with open(file_path, 'w', encoding='utf-8') as f:
                                                json.dump(all_day_orders, f, indent=2, ensure_ascii=False)
                                    
                                    # 更新索引
                                    all_order_numbers = list(existing_orders | set(new_order_numbers))
                                    
                                    index_data = {
                                        'order_numbers': all_order_numbers,
                                        'total_orders': len(all_order_numbers),
                                        'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                    }
                                    
                                    with open(order_index_file, 'w', encoding='utf-8') as f:
                                        json.dump(index_data, f, indent=2, ensure_ascii=False)
                                    
                                    # 顯示結果
                                    st.success("✅ 轉換完成！")
                                    
                                    # 統計各帳戶類型的保存數量
                                    saved_by_account = {}
                                    for order_no in new_order_numbers:
                                        # 從 combined_df 找到對應的記錄
                                        matching_rows = combined_df[combined_df[order_no_col].astype(str) == order_no]
                                        if len(matching_rows) > 0:
                                            acc_type = matching_rows.iloc[0]['account_type']
                                            saved_by_account[acc_type] = saved_by_account.get(acc_type, 0) + 1
                                    
                                    st.info(f"📊 保存明細：" + " | ".join([f"{k}: {v} 筆" for k, v in saved_by_account.items()]))
                                    
                                    col1, col2, col3 = st.columns(3)
                                    
                                    with col1:
                                        st.metric("已保存", saved_count)
                                    
                                    with col2:
                                        st.metric("已跳過", skipped_count)
                                    
                                    with col3:
                                        st.metric("已更新", updated_count)
                                    
                                    st.info(f"📁 保存位置：`data/review_history/bingx/orders/`")
                                    st.info(f"📋 索引已更新：{len(all_order_numbers)} 個 Order No")
                            
                            except Exception as e:
                                st.error(f"❌ 保存失敗：{str(e)}")
                                import traceback
                                st.code(traceback.format_exc())
            
            except Exception as e:
                st.error(f"❌ 讀取文件失敗：{str(e)}")
                import traceback
                st.code(traceback.format_exc())
            
            # 查看已保存的記錄
            st.subheader("📂 已保存的記錄")
            
            orders_dir = Path("data/review_history/bingx/orders")
            
            if not orders_dir.exists():
                st.info("還沒有保存任何記錄")
            else:
                # 列出所有文件
                json_files = list(orders_dir.rglob("*.json"))
                
                if not json_files:
                    st.info("還沒有保存任何記錄")
                else:
                    st.write(f"**總共 {len(json_files)} 個文件**")
                    
                    # 選擇文件查看
                    selected_file = st.selectbox(
                        "選擇文件查看",
                        json_files,
                        format_func=lambda x: x.name
                    )
                    
                    if selected_file:
                        try:
                            with open(selected_file, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                            
                            st.write(f"**記錄數**：{len(data)}")
                            
                            # 轉換為 DataFrame 顯示
                            df = pd.DataFrame(data)
                            st.dataframe(df, use_container_width=True, height=300)
                            
                            # 下載按鈕
                            csv = df.to_csv(index=False, encoding='utf-8-sig')
                            st.download_button(
                                label="📥 下載 CSV",
                                data=csv,
                                file_name=f"{selected_file.stem}.csv",
                                mime="text/csv"
                            )
                        
                        except Exception as e:
                            st.error(f"❌ 讀取失敗：{str(e)}")
    
    elif sub_function == "執行質量評分":
        st.subheader("⭐ 執行質量評分")
        
        # 檢查是否有交易記錄
        orders_dir = Path("data/review_history/bingx/orders")
        
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
                quality_file = Path("data/review_history/quality_scores.json")
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
                            quality_file = Path("data/review_history/quality_scores.json")
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
                                quality_file = Path("data/review_history/quality_scores.json")
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
                
                quality_file = Path("data/review_history/quality_scores.json")
                
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
                                    from pathlib import Path
                                    
                                    # 添加當前目錄到 Python 路徑
                                    current_dir = Path(__file__).parent
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
                                                    quality_file = Path("data/review_history/quality_scores.json")
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
    
    elif sub_function == "虧損分析":
        st.subheader("📉 虧損分析")
        
        # 檢查是否有交易記錄
        orders_dir = Path("data/review_history/bingx/orders")
        
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
                
                # 只分析虧損交易
                losing_df = df[df['pnl'] < 0].copy()
                
                if len(losing_df) == 0:
                    st.success("🎉 恭喜！沒有虧損交易")
                else:
                    st.write(f"**虧損交易數**：{len(losing_df)} 筆（佔總交易 {len(losing_df)/len(df)*100:.1f}%）")
                    
                    # 轉換時間
                    losing_df['close_time'] = pd.to_datetime(losing_df['close_time'], errors='coerce')
                    losing_df['open_time'] = pd.to_datetime(losing_df['open_time'], errors='coerce')
                    
                    # 計算持倉時間（小時）
                    losing_df['duration_hours'] = (losing_df['close_time'] - losing_df['open_time']).dt.total_seconds() / 3600
                    
                    # 虧損原因分類
                    st.subheader("📊 虧損原因分類")
                    
                    def classify_loss_reason(row):
                        """簡化的虧損原因分類"""
                        duration = row['duration_hours']
                        pnl_pct = (row['pnl'] / (row['entry_price'] * row['quantity'])) * 100 if row['entry_price'] > 0 and row['quantity'] > 0 else 0
                        
                        # 根據平倉類型
                        if row['close_type'] == '止盈止損':
                            if duration < 1:
                                return '止損太緊'
                            else:
                                return '趨勢判斷錯誤'
                        elif row['close_type'] == '爆倉':
                            return '風險管理不當'
                        elif row['close_type'] == '手動平倉':
                            if duration < 0.5:
                                return '過早進場'
                            elif duration > 24:
                                return '持倉時間過長'
                            else:
                                return '市場反轉'
                        else:
                            return '其他原因'
                    
                    losing_df['loss_reason'] = losing_df.apply(classify_loss_reason, axis=1)
                    
                    # 統計虧損原因
                    reason_stats = losing_df.groupby('loss_reason').agg({
                        'pnl': ['count', 'sum', 'mean']
                    }).round(2)
                    
                    reason_stats.columns = ['次數', '總虧損', '平均虧損']
                    reason_stats['佔比(%)'] = (reason_stats['次數'] / len(losing_df) * 100).round(1)
                    reason_stats = reason_stats.sort_values('總虧損')
                    
                    # 顯示統計表格
                    st.dataframe(reason_stats, use_container_width=True)
                    
                    # 可視化
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # 虧損原因分佈（次數）
                        fig_count = px.pie(
                            values=reason_stats['次數'],
                            names=reason_stats.index,
                            title='虧損原因分佈（按次數）'
                        )
                        st.plotly_chart(fig_count, use_container_width=True)
                    
                    with col2:
                        # 虧損原因分佈（金額）
                        fig_amount = px.pie(
                            values=abs(reason_stats['總虧損']),
                            names=reason_stats.index,
                            title='虧損原因分佈（按金額）'
                        )
                        st.plotly_chart(fig_amount, use_container_width=True)
                    
                    # 詳細分析
                    st.subheader("🔍 詳細分析")
                    
                    # 選擇虧損原因查看詳情
                    selected_reason = st.selectbox(
                        "選擇虧損原因查看詳情",
                        losing_df['loss_reason'].unique()
                    )
                    
                    reason_df = losing_df[losing_df['loss_reason'] == selected_reason]
                    
                    st.write(f"**{selected_reason}** - {len(reason_df)} 筆交易")
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("總虧損", f"{reason_df['pnl'].sum():.2f} USDT")
                    
                    with col2:
                        st.metric("平均虧損", f"{reason_df['pnl'].mean():.2f} USDT")
                    
                    with col3:
                        st.metric("平均持倉時間", f"{reason_df['duration_hours'].mean():.1f} 小時")
                    
                    # 改進建議
                    st.subheader("💡 改進建議")
                    
                    recommendations = {
                        '止損太緊': [
                            "✅ 放寬止損距離，建議至少 1.5-2 倍 ATR",
                            "✅ 在波動較大的市場環境中，適當增加止損空間",
                            "✅ 使用移動止損而非固定止損"
                        ],
                        '趨勢判斷錯誤': [
                            "✅ 加強趨勢確認，等待更多確認信號",
                            "✅ 使用多週期分析確認趨勢方向",
                            "✅ 避免在震盪市場中追趨勢"
                        ],
                        '過早進場': [
                            "✅ 等待更明確的進場信號",
                            "✅ 使用回調進場而非突破進場",
                            "✅ 確認支撐/阻力位後再進場"
                        ],
                        '市場反轉': [
                            "✅ 注意市場反轉信號（如背離、吞沒形態）",
                            "✅ 在關鍵支撐/阻力位附近提高警惕",
                            "✅ 使用移動止損保護利潤"
                        ],
                        '持倉時間過長': [
                            "✅ 設置時間止損，避免過度持倉",
                            "✅ 定期檢查持倉理由是否仍然成立",
                            "✅ 使用移動止損鎖定利潤"
                        ],
                        '風險管理不當': [
                            "✅ 降低槓桿倍數，建議使用 3-5x",
                            "✅ 嚴格執行止損，不要心存僥倖",
                            "✅ 控制單筆交易風險在總資金的 1-2%"
                        ],
                        '其他原因': [
                            "✅ 詳細記錄交易過程，以便後續分析",
                            "✅ 檢查是否有遺漏的市場信號或條件",
                            "✅ 回顧交易計劃，確保執行一致性"
                        ]
                    }
                    
                    if selected_reason in recommendations:
                        for rec in recommendations[selected_reason]:
                            st.write(rec)
                    
                    # 虧損交易列表
                    with st.expander("📋 查看虧損交易詳情"):
                        display_df = reason_df[['close_time', 'symbol', 'direction', 'entry_price', 
                                                'exit_price', 'pnl', 'duration_hours', 'leverage', 'close_type']].copy()
                        display_df.columns = ['時間', '交易對', '方向', '進場價', '出場價', 
                                             '盈虧', '持倉時間(h)', '槓桿', '平倉類型']
                        display_df = display_df.sort_values('時間', ascending=False)
                        st.dataframe(display_df, use_container_width=True, height=400)
                    
                    # 虧損趨勢分析
                    st.subheader("📈 虧損趨勢分析")
                    
                    # 按日期統計虧損
                    losing_df['date'] = losing_df['close_time'].dt.date
                    daily_loss = losing_df.groupby('date').agg({
                        'pnl': ['sum', 'count']
                    }).reset_index()
                    daily_loss.columns = ['日期', '虧損金額', '虧損次數']
                    
                    fig_trend = px.line(daily_loss, x='日期', y='虧損金額',
                                       title='每日虧損趨勢',
                                       labels={'虧損金額': '虧損 (USDT)'})
                    st.plotly_chart(fig_trend, use_container_width=True)
                    
                    # 虧損改善建議總結
                    st.subheader("🎯 虧損改善行動計劃")
                    
                    # 找出最嚴重的虧損原因（前3名）
                    top_reasons = reason_stats.nsmallest(3, '總虧損')
                    
                    st.write("**優先改善項目**（按虧損金額排序）：")
                    
                    for idx, (reason, row) in enumerate(top_reasons.iterrows(), 1):
                        st.write(f"\n**{idx}. {reason}**")
                        st.write(f"   - 虧損金額：{row['總虧損']:.2f} USDT（{row['佔比(%)']:.1f}%）")
                        st.write(f"   - 發生次數：{int(row['次數'])} 次")
                        
                        if reason in recommendations:
                            st.write("   **行動計劃**：")
                            for rec in recommendations[reason][:2]:  # 只顯示前2條
                                st.write(f"   {rec}")

# ==================== 7. 策略管理 ====================
elif category == "7️⃣ 策略管理":
    st.header("⚙️ 策略管理")
    
    sub_function = st.sidebar.selectbox(
        "選擇功能",
        [
            "策略列表",
            "策略配置查看",
            "策略啟用/禁用",
            "策略版本管理"
        ]
    )
    
    if sub_function == "策略啟用/禁用":
        st.subheader("⚙️ 策略啟用/禁用")
        
        strategy_files = glob.glob('strategies/*.json')
        
        if not strategy_files:
            st.warning("⚠️ 沒有找到策略配置文件")
        else:
            st.write("**所有策略狀態**")
            
            # 讀取所有策略狀態
            strategies_status = []
            
            for strategy_file in strategy_files:
                with open(strategy_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                strategies_status.append({
                    'file': strategy_file,
                    'name': config.get('name', 'Unknown'),
                    'id': config.get('id', 'unknown'),
                    'enabled': config.get('enabled', False),
                    'version': config.get('version', '1.0.0')
                })
            
            # 顯示策略列表
            for i, strategy in enumerate(strategies_status):
                col1, col2, col3, col4 = st.columns([3, 2, 1, 2])
                
                with col1:
                    st.write(f"**{strategy['name']}**")
                    st.caption(f"ID: {strategy['id']}")
                
                with col2:
                    st.write(f"版本: {strategy['version']}")
                
                with col3:
                    if strategy['enabled']:
                        st.success("✅ 啟用")
                    else:
                        st.error("❌ 禁用")
                
                with col4:
                    # 切換按鈕
                    new_status = st.checkbox(
                        "啟用" if not strategy['enabled'] else "禁用",
                        key=f"toggle_{i}",
                        value=strategy['enabled']
                    )
                    
                    # 如果狀態改變，更新配置文件
                    if new_status != strategy['enabled']:
                        try:
                            with open(strategy['file'], 'r', encoding='utf-8') as f:
                                config = json.load(f)
                            
                            config['enabled'] = new_status
                            
                            with open(strategy['file'], 'w', encoding='utf-8') as f:
                                json.dump(config, f, indent=2, ensure_ascii=False)
                            
                            st.success(f"✅ 已{'啟用' if new_status else '禁用'}策略：{strategy['name']}")
                            st.rerun()
                        
                        except Exception as e:
                            st.error(f"❌ 更新失敗：{str(e)}")
                
                st.divider()
    
    elif sub_function == "策略列表" or sub_function == "策略配置查看":
        st.subheader("📋 策略配置")
        
        strategy_files = glob.glob('strategies/*.json')
        
        if not strategy_files:
            st.warning("⚠️ 沒有找到策略配置文件")
        else:
            selected_strategy = st.selectbox(
                "選擇策略",
                strategy_files,
                format_func=lambda x: x.replace('strategies/', '').replace('.json', '')
            )
            
            with open(selected_strategy, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
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
            
            with st.expander("📄 查看完整配置（JSON）"):
                st.json(config)

# ==================== 8. 風險管理 ====================
elif category == "8️⃣ 風險管理":
    st.header("⚠️ 風險管理")
    
    sub_function = st.sidebar.selectbox(
        "選擇功能",
        [
            "全局風險設置",
            "策略級風險設置",
            "風險事件記錄"
        ]
    )
    
    if sub_function == "全局風險設置":
        st.subheader("🛡️ 全局風險設置")
        
        try:
            import yaml
            with open('system_config.yaml', 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            risk_config = config.get('risk', {})
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**全局限制**")
                st.write(f"- 最大回撤：{risk_config.get('global_max_drawdown', 0)*100:.0f}%")
                st.write(f"- 每日虧損限制：{risk_config.get('daily_loss_limit', 0)*100:.0f}%")
                st.write(f"- 最大倉位：{risk_config.get('global_max_position', 0)*100:.0f}%")
            
            with col2:
                st.write("**策略默認值**")
                st.write(f"- 單策略最大倉位：{risk_config.get('default_max_position_per_strategy', 0)*100:.0f}%")
                st.write(f"- 每日最大交易數：{risk_config.get('default_max_trades_per_day', 0)}")
                st.write(f"- 最大連損：{risk_config.get('default_max_consecutive_losses', 0)}")
            
            with st.expander("📄 查看完整風險配置"):
                st.json(risk_config)
        
        except Exception as e:
            st.error(f"❌ 讀取配置失敗：{str(e)}")

# ==================== 9. 數據管理 ====================
elif category == "9️⃣ 數據管理":
    st.header("💾 數據管理")
    
    sub_function = st.sidebar.selectbox(
        "選擇功能",
        [
            "數據源設置",
            "歷史數據下載",
            "數據驗證"
        ]
    )
    
    if sub_function == "數據源設置":
        st.subheader("🌐 數據源設置")
        
        try:
            import yaml
            with open('system_config.yaml', 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            data_config = config.get('data', {})
            
            st.write(f"**主數據源**：{data_config.get('primary_source', 'N/A')}")
            st.write(f"**備用數據源**：{', '.join(data_config.get('backup_sources', []))}")
            st.write(f"**緩存時間**：{data_config.get('cache_ttl', 0)} 秒")
            
            with st.expander("📄 查看完整數據配置"):
                st.json(data_config)
        
        except Exception as e:
            st.error(f"❌ 讀取配置失敗：{str(e)}")
    
    elif sub_function == "歷史數據下載":
        st.subheader("📥 歷史數據下載")
        st.info("💡 數據下載需要通過命令行：")
        st.code("python3 fetch_market_data.py")

# ==================== 10. 系統配置 ====================
elif category == "🔟 系統配置":
    st.header("🔧 系統配置")
    
    sub_function = st.sidebar.selectbox(
        "選擇功能",
        [
            "系統信息",
            "回測配置",
            "通知配置",
            "日誌配置"
        ]
    )
    
    try:
        import yaml
        with open('system_config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        if sub_function == "系統信息":
            st.subheader("ℹ️ 系統信息")
            system_config = config.get('system', {})
            
            st.write(f"**系統名稱**：{system_config.get('name', 'N/A')}")
            st.write(f"**版本**：{system_config.get('version', 'N/A')}")
            st.write(f"**環境**：{system_config.get('environment', 'N/A')}")
        
        elif sub_function == "回測配置":
            st.subheader("📊 回測配置")
            backtest_config = config.get('backtest', {})
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**手續費**：{backtest_config.get('commission', 0)*100:.2f}%")
                st.write(f"**滑點**：{backtest_config.get('slippage', 0)*100:.2f}%")
            
            with col2:
                st.write(f"**初始資金**：{backtest_config.get('initial_capital', 0):.0f} USDT")
                st.write(f"**無風險利率**：{backtest_config.get('risk_free_rate', 0)*100:.0f}%")
            
            with st.expander("📄 查看完整回測配置"):
                st.json(backtest_config)
        
        elif sub_function == "通知配置":
            st.subheader("📢 通知配置")
            notif_config = config.get('notifications', {})
            
            telegram = notif_config.get('telegram', {})
            st.write(f"**Telegram**：{'✅ 啟用' if telegram.get('enabled', False) else '❌ 禁用'}")
            
            email = notif_config.get('email', {})
            st.write(f"**Email**：{'✅ 啟用' if email.get('enabled', False) else '❌ 禁用'}")
            
            webhook = notif_config.get('webhook', {})
            st.write(f"**Webhook**：{'✅ 啟用' if webhook.get('enabled', False) else '❌ 禁用'}")
        
        elif sub_function == "日誌配置":
            st.subheader("📝 日誌配置")
            logging_config = config.get('logging', {})
            
            st.write(f"**日誌級別**：{logging_config.get('level', 'N/A')}")
            st.write(f"**日誌文件**：{logging_config.get('file', 'N/A')}")
            st.write(f"**最大大小**：{logging_config.get('max_bytes', 0) / 1024 / 1024:.0f} MB")
            st.write(f"**備份數量**：{logging_config.get('backup_count', 0)}")
    
    except Exception as e:
        st.error(f"❌ 讀取配置失敗：{str(e)}")

# 底部信息
st.sidebar.markdown("---")
st.sidebar.info("""
**系統信息**
- 版本：2.0.0
- 功能分類：10 大類
- 總功能數：66 個
""")

st.sidebar.success("""
**快速命令**
```bash
# 運行回測
python3 backtest_multi_timeframe.py

# 實盤交易
python3 cli.py live --strategy xxx

# 參數優化
python3 cli.py optimize --strategy xxx
```
""")
