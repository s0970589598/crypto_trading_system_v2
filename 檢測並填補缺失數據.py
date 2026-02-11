"""
檢測並填補市場數據中的缺失K線

使用 MarketAnalyzer 的 fill_missing_data() 方法
"""

import sys
from pathlib import Path
import glob

sys.path.insert(0, '.')

from src.analysis.market_analyzer import MarketAnalyzer


def check_all_market_data(auto_fetch: bool = False):
    """檢查所有市場數據文件"""
    
    csv_files = glob.glob('market_data_*.csv')
    
    if not csv_files:
        print("未找到市場數據文件")
        return
    
    print(f"找到 {len(csv_files)} 個市場數據文件\n")
    
    analyzer = MarketAnalyzer()
    results = []
    
    for filename in sorted(csv_files):
        # 從文件名解析交易對和時間週期
        # 格式：market_data_SYMBOL_INTERVAL.csv
        parts = filename.replace('market_data_', '').replace('.csv', '').split('_')
        
        if len(parts) >= 2:
            symbol = parts[0]
            interval = parts[1]
            
            if auto_fetch:
                # 自動填補缺失數據
                result = analyzer.fill_missing_data(symbol, interval)
                results.append((filename, result))
            else:
                # 只檢測，不填補
                gaps = analyzer.detect_missing_gaps(symbol, interval)
                
                print(f"\n{'='*60}")
                print(f"文件：{filename}")
                print(f"交易對：{symbol} | 時間週期：{interval}")
                print(f"{'='*60}")
                
                if not gaps:
                    print(f"✅ 沒有缺失的K線數據")
                    results.append((filename, {'success': True, 'total_missing': 0}))
                else:
                    total_missing = sum(gap['missing_count'] for gap in gaps)
                    print(f"⚠️ 發現 {len(gaps)} 個缺失時間段，共 {total_missing} 個缺失K線")
                    
                    # 顯示前5個缺失時間段
                    print(f"\n缺失的時間段（前5個）：")
                    for i, gap in enumerate(gaps[:5], 1):
                        print(f"   {i}. {gap['start_time']} 至 {gap['end_time']} ({gap['missing_count']} 個)")
                    
                    if len(gaps) > 5:
                        print(f"   ... 還有 {len(gaps) - 5} 個時間段")
                    
                    results.append((filename, {'success': False, 'total_missing': total_missing}))
        else:
            print(f"⚠️ 無法解析文件名：{filename}")
    
    # 總結
    print(f"\n{'='*60}")
    print(f"檢查完成總結")
    print(f"{'='*60}")
    
    success_count = sum(1 for _, result in results if result.get('success', False))
    total_files = len(results)
    
    print(f"✅ 完整：{success_count}/{total_files}")
    print(f"⚠️ 有缺失：{total_files - success_count}/{total_files}")
    
    if auto_fetch:
        total_filled = sum(result.get('filled', 0) for _, result in results)
        print(f"📥 共填補：{total_filled} 個K線")
    
    if success_count < total_files:
        print(f"\n有缺失的文件：")
        for filename, result in results:
            if not result.get('success', False):
                missing = result.get('total_missing', 0)
                print(f"   - {filename} (缺失 {missing} 個)")


def clean_backup_files():
    """清理備份文件"""
    print("\n🗑️  清理模式：刪除所有備份文件")
    
    backup_files = glob.glob('market_data_*.csv.backup') + glob.glob('market_data_*.csv.before_fill')
    
    if not backup_files:
        print("✅ 沒有找到備份文件")
        return
    
    print(f"\n找到 {len(backup_files)} 個備份文件：")
    for f in backup_files:
        print(f"   - {f}")
    
    confirm = input("\n確定要刪除這些文件嗎？(y/N): ")
    if confirm.lower() == 'y':
        for f in backup_files:
            Path(f).unlink()
            print(f"   ✅ 已刪除：{f}")
        print(f"\n✅ 共刪除 {len(backup_files)} 個備份文件")
    else:
        print("❌ 已取消")


if __name__ == "__main__":
    print("=" * 60)
    print("市場數據缺失檢測與填補工具 v2.0")
    print("使用 MarketAnalyzer 模組")
    print("=" * 60)
    
    # 檢查命令行參數
    auto_fetch = '--fetch' in sys.argv or '-f' in sys.argv
    clean_backups = '--clean' in sys.argv or '-c' in sys.argv
    
    # 如果只是清理備份
    if clean_backups and not auto_fetch:
        clean_backup_files()
        sys.exit(0)
    
    if auto_fetch:
        print("\n⚠️ 自動獲取模式：將從 Binance API 獲取缺失數據")
        print("   這可能需要幾分鐘時間...")
    else:
        print("\n📊 檢測模式：只檢測缺失，不自動獲取")
        print("   如需自動獲取，請使用：python3 檢測並填補缺失數據.py --fetch")
        print("   如需清理備份，請使用：python3 檢測並填補缺失數據.py --clean")
    
    input("\n按 Enter 繼續...")
    
    check_all_market_data(auto_fetch)
    
    print("\n" + "=" * 60)
    print("完成！")
    print("=" * 60)
