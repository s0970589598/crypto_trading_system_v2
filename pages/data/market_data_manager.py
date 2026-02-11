"""
市場數據管理頁面

提供 Web 界面來管理和下載市場數據
"""

import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import sys
import os

# 添加項目根目錄到路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

try:
    from src.analysis.market_analyzer import MarketAnalyzer
    MARKET_ANALYZER_AVAILABLE = True
except Exception as e:
    MARKET_ANALYZER_AVAILABLE = False
    IMPORT_ERROR = str(e)


def render():
    """渲染市場數據管理頁面"""
    
    st.title("📥 市場數據管理")
    
    if not MARKET_ANALYZER_AVAILABLE:
        st.error(f"❌ 無法載入 MarketAnalyzer：{IMPORT_ERROR}")
        return
    
    # 創建標籤頁
    tab1, tab2, tab3 = st.tabs(["📊 數據狀態", "⬇️ 下載數據", "🔄 更新數據"])
    
    # ==================== 標籤頁 1：數據狀態 ====================
    with tab1:
        st.subheader("📊 當前數據狀態")
        
        # 掃描現有數據文件
        data_files = list(Path('.').glob('market_data_*.csv'))
        
        if not data_files:
            st.warning("⚠️ 未找到任何市場數據文件")
            st.info("請使用「下載數據」標籤頁下載數據")
        else:
            st.success(f"✅ 找到 {len(data_files)} 個數據文件")
            
            # 分析數據文件
            data_info = []
            for file in data_files:
                try:
                    df = pd.read_csv(file)
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    
                    # 解析文件名
                    filename = file.name
                    parts = filename.replace('market_data_', '').replace('.csv', '').split('_')
                    symbol = parts[0] if len(parts) > 0 else 'Unknown'
                    interval = parts[1] if len(parts) > 1 else 'Unknown'
                    
                    # 計算數據信息
                    first_time = df['timestamp'].min()
                    last_time = df['timestamp'].max()
                    now = datetime.now()
                    hours_old = (now - last_time).total_seconds() / 3600
                    
                    # 判斷時區
                    if hours_old < 2:
                        timezone_status = "✅ UTC+8"
                    elif 6 < hours_old < 10:
                        timezone_status = "⚠️ UTC (需更新)"
                    else:
                        timezone_status = f"❓ 未知 ({hours_old:.1f}h)"
                    
                    data_info.append({
                        '交易對': symbol,
                        '時區': interval,
                        '數據量': len(df),
                        '開始時間': first_time.strftime('%Y-%m-%d %H:%M'),
                        '結束時間': last_time.strftime('%Y-%m-%d %H:%M'),
                        '更新狀態': timezone_status,
                        '文件大小': f"{file.stat().st_size / 1024 / 1024:.2f} MB"
                    })
                except Exception as e:
                    data_info.append({
                        '交易對': 'Error',
                        '時區': 'Error',
                        '數據量': 0,
                        '開始時間': '-',
                        '結束時間': '-',
                        '更新狀態': f"❌ {str(e)[:20]}",
                        '文件大小': '-'
                    })
            
            # 顯示數據表格
            df_info = pd.DataFrame(data_info)
            st.dataframe(df_info, use_container_width=True)
            
            # 統計信息
            col1, col2, col3 = st.columns(3)
            with col1:
                symbols = df_info['交易對'].unique()
                st.metric("交易對數量", len(symbols))
            with col2:
                total_size = sum([f.stat().st_size for f in data_files]) / 1024 / 1024
                st.metric("總數據大小", f"{total_size:.2f} MB")
            with col3:
                needs_update = len([x for x in data_info if '需更新' in x['更新狀態']])
                st.metric("需要更新", needs_update)
    
    # ==================== 標籤頁 2：下載數據 ====================
    with tab2:
        st.subheader("⬇️ 下載市場數據")
        
        st.info("""
        💡 **說明**：
        - 所有數據使用本地時間（UTC+8）
        - 默認下載最近 90 天的數據
        - 如果文件已存在，將會備份舊文件
        """)
        
        # 選擇交易對
        col1, col2 = st.columns(2)
        with col1:
            symbols_input = st.text_input(
                "交易對（多個用逗號分隔）",
                value="BTCUSDT,ETHUSDT",
                help="例如：BTCUSDT,ETHUSDT,BNBUSDT"
            )
        
        with col2:
            intervals_input = st.multiselect(
                "時間週期",
                options=['1m', '3m', '5m', '15m', '1h', '4h', '1d'],
                default=['15m', '1h', '4h', '1d'],
                help="選擇要下載的時間週期"
            )
        
        # 高級選項
        with st.expander("⚙️ 高級選項"):
            days = st.slider("下載天數", min_value=7, max_value=365, value=90)
            backup_old = st.checkbox("備份舊文件", value=True)
        
        # 下載按鈕
        if st.button("🚀 開始下載", type="primary", use_container_width=True):
            # 解析輸入
            symbols = [s.strip().upper() for s in symbols_input.split(',') if s.strip()]
            intervals = intervals_input
            
            if not symbols:
                st.error("❌ 請輸入至少一個交易對")
                return
            
            if not intervals:
                st.error("❌ 請選擇至少一個時間週期")
                return
            
            # 創建進度條
            total_tasks = len(symbols) * len(intervals)
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # 備份目錄
            if backup_old:
                backup_dir = Path('market_data_backup_utc')
                backup_dir.mkdir(exist_ok=True)
            
            # 創建分析器
            analyzer = MarketAnalyzer()
            
            # 下載數據
            current_task = 0
            success_count = 0
            failed_tasks = []
            
            for symbol in symbols:
                for interval in intervals:
                    current_task += 1
                    progress = current_task / total_tasks
                    progress_bar.progress(progress)
                    status_text.text(f"正在下載 {symbol} {interval}... ({current_task}/{total_tasks})")
                    
                    try:
                        # 備份舊文件
                        if backup_old:
                            old_file = Path(f'market_data_{symbol}_{interval}.csv')
                            if old_file.exists():
                                backup_file = backup_dir / old_file.name
                                if not backup_file.exists():
                                    old_file.rename(backup_file)
                        
                        # 下載數據
                        df = analyzer.load_market_data(symbol, interval)
                        
                        if df is not None and len(df) > 0:
                            success_count += 1
                        else:
                            failed_tasks.append(f"{symbol} {interval}")
                    
                    except Exception as e:
                        failed_tasks.append(f"{symbol} {interval}: {str(e)}")
            
            # 完成
            progress_bar.progress(1.0)
            status_text.empty()
            
            if success_count == total_tasks:
                st.success(f"✅ 成功下載所有 {total_tasks} 個數據文件！")
            else:
                st.warning(f"⚠️ 完成 {success_count}/{total_tasks} 個下載")
                if failed_tasks:
                    with st.expander("查看失敗任務"):
                        for task in failed_tasks:
                            st.text(f"❌ {task}")
    
    # ==================== 標籤頁 3：更新數據 ====================
    with tab3:
        st.subheader("🔄 更新現有數據")
        
        st.info("""
        💡 **說明**：
        - 檢查現有數據文件並更新到最新
        - 只更新已存在的文件
        - 自動補齊缺失的時間段
        """)
        
        # 掃描現有文件
        data_files = list(Path('.').glob('market_data_*.csv'))
        
        if not data_files:
            st.warning("⚠️ 未找到任何數據文件，請先使用「下載數據」功能")
        else:
            st.write(f"找到 {len(data_files)} 個數據文件")
            
            # 快速更新按鈕（強制更新所有文件）
            col1, col2 = st.columns([1, 3])
            with col1:
                quick_update = st.button(
                    "⚡ 快速更新全部",
                    type="primary",
                    help="一鍵強制更新所有數據文件到最新（推薦）"
                )
            with col2:
                st.caption("💡 推薦使用此按鈕快速更新所有數據")
            
            if quick_update:
                st.info("🔄 正在強制更新所有數據文件...")
                
                # 創建進度條
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # 創建分析器
                analyzer = MarketAnalyzer()
                
                # 強制更新模式
                original_expiry = analyzer.cache_expiry_hours
                analyzer.cache_expiry_hours = 0  # 強制更新
                
                # 更新數據
                success_count = 0
                failed_tasks = []
                
                # 解析文件名
                files_to_update = []
                for file in data_files:
                    parts = file.name.replace('market_data_', '').replace('.csv', '').split('_')
                    if len(parts) >= 2:
                        symbol = parts[0]
                        interval = parts[1]
                        files_to_update.append((symbol, interval, file))
                
                for i, (symbol, interval, file) in enumerate(files_to_update):
                    progress = (i + 1) / len(files_to_update)
                    progress_bar.progress(progress)
                    status_text.text(f"正在更新 {symbol} {interval}... ({i+1}/{len(files_to_update)})")
                    
                    try:
                        # 重新載入數據（會自動更新）
                        df = analyzer.load_market_data(symbol, interval)
                        
                        if df is not None and len(df) > 0:
                            success_count += 1
                        else:
                            failed_tasks.append(f"{symbol} {interval}")
                    
                    except Exception as e:
                        failed_tasks.append(f"{symbol} {interval}: {str(e)}")
                
                # 恢復原設置
                analyzer.cache_expiry_hours = original_expiry
                
                # 完成
                progress_bar.progress(1.0)
                status_text.empty()
                
                if success_count == len(files_to_update):
                    st.success(f"✅ 成功更新所有 {len(files_to_update)} 個文件！")
                else:
                    st.warning(f"⚠️ 完成 {success_count}/{len(files_to_update)} 個更新")
                    if failed_tasks:
                        with st.expander("查看失敗任務"):
                            for task in failed_tasks:
                                st.text(f"❌ {task}")
            
            st.markdown("---")
            st.subheader("📋 選擇性更新")
            
            # 更新選項
            update_all = st.checkbox("更新所有文件", value=True)
            
            if not update_all:
                # 選擇要更新的文件
                file_names = [f.name for f in data_files]
                selected_files = st.multiselect(
                    "選擇要更新的文件",
                    options=file_names,
                    default=file_names
                )
            else:
                selected_files = [f.name for f in data_files]
            
            # 更新按鈕
            if st.button("🔄 開始更新", type="primary", use_container_width=True):
                if not selected_files:
                    st.error("❌ 請選擇至少一個文件")
                    return
                
                # 創建進度條
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # 創建分析器
                analyzer = MarketAnalyzer()
                
                # 更新數據
                success_count = 0
                failed_tasks = []
                
                for i, filename in enumerate(selected_files):
                    progress = (i + 1) / len(selected_files)
                    progress_bar.progress(progress)
                    status_text.text(f"正在更新 {filename}... ({i+1}/{len(selected_files)})")
                    
                    try:
                        # 解析文件名
                        parts = filename.replace('market_data_', '').replace('.csv', '').split('_')
                        symbol = parts[0] if len(parts) > 0 else None
                        interval = parts[1] if len(parts) > 1 else None
                        
                        if symbol and interval:
                            # 重新載入數據（會自動更新）
                            df = analyzer.load_market_data(symbol, interval)
                            
                            if df is not None and len(df) > 0:
                                success_count += 1
                            else:
                                failed_tasks.append(filename)
                        else:
                            failed_tasks.append(f"{filename}: 無法解析文件名")
                    
                    except Exception as e:
                        failed_tasks.append(f"{filename}: {str(e)}")
                
                # 完成
                progress_bar.progress(1.0)
                status_text.empty()
                
                if success_count == len(selected_files):
                    st.success(f"✅ 成功更新所有 {len(selected_files)} 個文件！")
                else:
                    st.warning(f"⚠️ 完成 {success_count}/{len(selected_files)} 個更新")
                    if failed_tasks:
                        with st.expander("查看失敗任務"):
                            for task in failed_tasks:
                                st.text(f"❌ {task}")
        
        # 時區修復工具
        st.markdown("---")
        st.subheader("🔧 時區修復工具")
        
        st.warning("""
        ⚠️ **注意**：如果您的數據文件是在 2026-02-09 之前下載的，
        可能使用的是 UTC 時間而非本地時間（UTC+8）。
        
        使用此工具可以重新下載所有數據以修復時區問題。
        """)
        
        if st.button("🔧 重新下載所有數據（修復時區）", type="secondary"):
            st.info("正在準備重新下載...")
            
            # 備份所有舊文件
            backup_dir = Path('market_data_backup_utc')
            backup_dir.mkdir(exist_ok=True)
            
            data_files = list(Path('.').glob('market_data_*.csv'))
            
            if data_files:
                st.write(f"📦 備份 {len(data_files)} 個文件到 {backup_dir}")
                for file in data_files:
                    backup_file = backup_dir / file.name
                    if not backup_file.exists():
                        file.rename(backup_file)
                
                st.success("✅ 備份完成！")
                st.info("💡 請使用「下載數據」標籤頁重新下載數據")
            else:
                st.info("沒有找到需要備份的文件")


if __name__ == "__main__":
    render()
