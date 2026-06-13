#!/usr/bin/env python3
"""
清理模組化過程中產生的臨時文件
"""

import os
from pathlib import Path

print("="*80)
print("🧹 清理模組化臨時文件")
print("="*80)

# 定義文件分類
files = {
    "一次性輔助腳本（可刪除）": [
        "split_review_module.py",           # 拆分模組的腳本（已完成）
        "update_main_dashboard.py",         # 更新主文件的腳本（已完成）
    ],
    
    "測試腳本（建議保留）": [
        "test_modularization.py",           # 完整的模組化測試
        "verify_fix.py",                    # Path 問題驗證
        "測試新功能.py",                     # 量化風險分析測試
        "測試新功能_完整版.py",              # 完整功能測試
    ],
    
    "文檔（建議保留）": [
        "web_dashboard_模組化方案.md",      # 模組化方案
        "模組化實施計劃.md",                # 實施計劃
        "模組化完成總結.md",                # 完成總結
        "模組化使用說明.md",                # 使用說明
        "Path導入問題修復說明.md",          # 問題修復說明
        "量化風險分析完整功能總結.md",      # 功能總結
        "新功能使用說明_2026-02-09.md",    # 新功能說明
    ],
    
    "備份文件（建議保留）": [
        "web_dashboard_v2.py.backup_before_modularization",  # 原始備份
        "pages/review/quality_scoring.py.bak",               # sed 備份
    ]
}

# 顯示文件分類
for category, file_list in files.items():
    print(f"\n【{category}】")
    print("-"*80)
    for file in file_list:
        if os.path.exists(file):
            size = os.path.getsize(file)
            print(f"  ✓ {file:50s} ({size:,} bytes)")
        else:
            print(f"  ✗ {file:50s} (不存在)")

# 詢問是否刪除
print("\n" + "="*80)
print("建議操作：")
print("="*80)
print("\n1. 刪除一次性輔助腳本（已完成任務）")
print("   - split_review_module.py")
print("   - update_main_dashboard.py")
print("\n2. 保留測試腳本（未來可能需要）")
print("   - test_modularization.py")
print("   - verify_fix.py")
print("   - 測試新功能*.py")
print("\n3. 保留所有文檔（記錄過程）")
print("   - *.md 文件")
print("\n4. 保留備份文件（安全起見）")
print("   - *.backup_*")
print("   - *.bak")

print("\n" + "="*80)
response = input("是否執行刪除一次性輔助腳本？(y/n): ")

if response.lower() == 'y':
    deleted_files = []
    for file in files["一次性輔助腳本（可刪除）"]:
        if os.path.exists(file):
            os.remove(file)
            deleted_files.append(file)
            print(f"✅ 已刪除: {file}")
    
    if deleted_files:
        print(f"\n✅ 共刪除 {len(deleted_files)} 個文件")
    else:
        print("\n⚠️ 沒有文件需要刪除")
else:
    print("\n❌ 取消刪除操作")

print("\n" + "="*80)
print("清理完成")
print("="*80)
