"""
Loss Review Module
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
    """渲染loss review頁面"""
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
