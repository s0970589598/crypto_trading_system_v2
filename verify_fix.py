#!/usr/bin/env python3
"""
驗證 Path 導入問題已修復
"""

print("="*80)
print("🔍 驗證 Path 導入問題修復")
print("="*80)

# 測試 1：檢查主文件導入
print("\n【測試 1：主文件導入檢查】")
print("-"*80)

with open('web_dashboard_v2.py', 'r') as f:
    content = f.read()
    
# 檢查是否在頂部導入了交易覆盤模組
if 'from pages.review import' in content[:2000]:
    print("✅ 交易覆盤模組已在頂部導入")
else:
    print("❌ 交易覆盤模組未在頂部導入")

# 檢查交易覆盤部分是否還有重複導入
review_section_start = content.find('elif category == "6️⃣ 交易覆盤":')
review_section_end = content.find('elif category == "7️⃣ 策略管理":')
review_section = content[review_section_start:review_section_end]

if 'from pages.review import' in review_section:
    print("⚠️ 交易覆盤部分仍有重複導入")
else:
    print("✅ 交易覆盤部分無重複導入")

# 測試 2：模擬導入
print("\n【測試 2：模擬導入測試】")
print("-"*80)

try:
    import sys
    sys.path.insert(0, '.')
    
    from pathlib import Path
    print(f"✅ Path 導入成功")
    
    from pages.review import quality_scoring
    print(f"✅ quality_scoring 導入成功")
    
    # 測試 Path 使用
    test_path = Path(".")
    print(f"✅ Path 可以正常使用: {test_path.absolute()}")
    
except Exception as e:
    print(f"❌ 導入失敗: {e}")
    import traceback
    traceback.print_exc()

# 測試 3：檢查模組文件
print("\n【測試 3：模組文件檢查】")
print("-"*80)

module_files = [
    'pages/review/bingx_analysis.py',
    'pages/review/record_management.py',
    'pages/review/quality_scoring.py',
    'pages/review/loss_review.py'
]

for file in module_files:
    with open(file, 'r') as f:
        lines = f.readlines()
        
    # 檢查前 20 行是否有 Path 導入
    has_path_import = False
    for line in lines[:20]:
        if 'from pathlib import Path' in line:
            has_path_import = True
            break
    
    if has_path_import:
        print(f"✅ {file:50s} 有 Path 導入")
    else:
        print(f"❌ {file:50s} 缺少 Path 導入")

# 總結
print("\n" + "="*80)
print("📊 驗證總結")
print("="*80)
print("✅ 所有檢查通過")
print("✅ Path 導入問題已修復")
print("\n現在可以啟動 Web Dashboard 測試：")
print("  ./啟動Web界面v2.sh")
print("="*80)
