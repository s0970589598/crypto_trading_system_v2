#!/usr/bin/env python3
"""
清除全部評分記錄

使用方法：
    python 清除全部評分.py
"""

import json
import shutil
from pathlib import Path
from datetime import datetime

def clear_all_scores():
    """清除所有評分記錄並備份"""
    quality_file = Path("data/review_history/quality_scores.json")
    
    if not quality_file.exists():
        print("❌ 評分文件不存在")
        return
    
    # 顯示當前評分數量
    with open(quality_file, 'r', encoding='utf-8') as f:
        scores = json.load(f)
    
    if isinstance(scores, list):
        count = len(scores)
    elif isinstance(scores, dict):
        count = len(scores)
    else:
        count = 0
    
    print(f"📊 當前有 {count} 筆評分記錄")
    
    # 確認
    confirm = input("⚠️  確定要清除所有評分嗎？(yes/no): ")
    
    if confirm.lower() not in ['yes', 'y']:
        print("❌ 已取消")
        return
    
    # 備份
    backup_file = quality_file.parent / f"quality_scores_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    shutil.copy(quality_file, backup_file)
    print(f"💾 已備份至：{backup_file}")
    
    # 清空
    with open(quality_file, 'w', encoding='utf-8') as f:
        json.dump([], f, indent=2)
    
    print("✅ 已清除所有評分記錄！")
    print(f"📁 備份文件：{backup_file}")

if __name__ == "__main__":
    clear_all_scores()
