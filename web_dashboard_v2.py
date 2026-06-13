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

# 導入交易覆盤模組
from pages.review import bingx_analysis, record_management, quality_scoring, loss_review

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
            st.info("請先運行回測：`python3 -m cli_commands.backtest --strategy multi-timeframe-aggressive`")
        else:
            # ... 現有的單策略回測結果顯示代碼 ...
            pass  # 保留現有代碼
    
    elif sub_function == "多策略組合回測":
        st.subheader("📊 多策略組合回測")
        
        # 策略選擇
        st.info("💡 選擇要組合回測的策略（至少 2 個）")
        
        # 查找可用策略
        strategy_files = glob.glob('strategies/*.json')
        available_strategies = [
            f.replace('strategies/', '').replace('.json', '')
            for f in strategy_files
        ]
        
        if len(available_strategies) < 2:
            st.warning("⚠️ 可用策略少於 2 個，無法進行多策略回測")
            st.info("請確保 strategies/ 目錄中至少有 2 個策略配置文件")
        else:
            col1, col2 = st.columns([2, 1])
            
            with col1:
                selected_strategies = st.multiselect(
                    "選擇策略",
                    available_strategies,
                    default=available_strategies[:2] if len(available_strategies) >= 2 else []
                )
            
            with col2:
                st.markdown("""
                **可用策略**:
                """)
                for strategy in available_strategies:
                    st.write(f"- {strategy}")
            
            if len(selected_strategies) < 2:
                st.warning("⚠️ 請至少選擇 2 個策略")
            else:
                # 執行按鈕
                if st.button("🚀 執行多策略組合回測", use_container_width=True, type="primary"):
                    with st.spinner(f"正在執行 {len(selected_strategies)} 個策略的組合回測，請稍候..."):
                        import subprocess
                        
                        # 構建命令
                        cmd = ['python3', 'cli.py', 'backtest']
                        for strategy in selected_strategies:
                            cmd.extend(['--strategy', strategy])
                        
                        result = subprocess.run(
                            cmd,
                            capture_output=True,
                            text=True,
                            timeout=300
                        )
                        
                        if result.returncode == 0:
                            st.success(f"✅ 多策略組合回測完成！（{len(selected_strategies)} 個策略）")
                            st.balloons()
                            with st.expander("查看執行日誌"):
                                st.code(result.stdout[-2000:])
                            st.rerun()
                        else:
                            st.error("❌ 執行失敗")
                            st.code(result.stderr)
                
                st.divider()
                
                # 顯示現有結果
                st.subheader("📈 歷史多策略回測結果")
                
                # 查找多策略回測結果（包含多個策略 ID 的檔案）
                all_result_files = glob.glob('backtest_result_*.json')
                
                # 簡單判斷：檔名包含多個策略 ID 或者是 multi_strategy 開頭
                multi_strategy_files = [
                    f for f in all_result_files
                    if 'multi_strategy' in f or f.count('_') > 4
                ]
                
                if not multi_strategy_files:
                    st.info("💡 尚無多策略回測結果，點擊上方按鈕執行回測")
                else:
                    selected_file = st.selectbox(
                        "選擇回測結果",
                        multi_strategy_files,
                        format_func=lambda x: x.replace('backtest_result_', '').replace('.json', '')
                    )
                    
                    # 讀取並顯示結果
                    try:
                        with open(selected_file, 'r') as f:
                            result = json.load(f)
                        
                        # 顯示基本信息
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.metric("策略數量", len(selected_strategies))
                        
                        with col2:
                            total_return = result.get('total_pnl_pct', 0)
                            st.metric("總收益", f"+{total_return:.2f}%")
                        
                        with col3:
                            total_trades = result.get('total_trades', 0)
                            st.metric("總交易數", total_trades)
                        
                        # 顯示詳細信息
                        st.json(result)
                        
                    except Exception as e:
                        st.error(f"❌ 讀取結果失敗：{e}")
    
    elif sub_function == "槓桿對比測試":
        st.subheader("📈 槓桿對比分析")
        
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
        
        # 查看現有結果
        leverage_files = glob.glob('leverage_comparison_*.csv')
        
        if not leverage_files:
            st.warning("⚠️ 沒有找到槓桿對比結果")
            st.info("👆 點擊上方按鈕執行槓桿對比回測")
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
            "實時市場分析",  # 新增
            "實盤狀態監控",
            "當前持倉",
            "實盤交易記錄",
            "Telegram 通知設置"
        ]
    )
    
    if sub_function == "實時市場分析":
        # 使用新的實時市場分析頁面
        try:
            from pages.trading import live_market_analysis
            live_market_analysis.render()
        except Exception as e:
            st.error(f"❌ 載入實時市場分析頁面失敗：{e}")
            import traceback
            with st.expander("查看錯誤詳情"):
                st.code(traceback.format_exc())
    
    elif sub_function == "實盤狀態監控":
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
        bingx_analysis.render()
    elif sub_function == "交易記錄管理":
        record_management.render()
    elif sub_function == "執行質量評分":
        quality_scoring.render()
    elif sub_function == "虧損分析":
        loss_review.render()

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
        # 使用新的市場數據管理頁面
        try:
            from pages.data import market_data_manager
            market_data_manager.render()
        except Exception as e:
            st.error(f"❌ 載入數據管理頁面失敗：{e}")
            st.info("💡 備用方案 - 使用命令行下載：")
            st.code("python3 快速重新下載_關鍵時區.py")

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
python3 -m cli_commands.backtest --strategy multi-timeframe-aggressive

# 實盤交易
python3 cli.py live --strategy xxx

# 參數優化
python3 cli.py optimize --strategy xxx
```
""")
