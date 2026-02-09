"""
Record Management Module
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
    """渲染record management頁面"""
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

