#!/usr/bin/env python3
"""
測試冷靜期和 Kelly Criterion 功能
"""

from quantitative_risk_analysis import QuantitativeRiskOfficer

print("="*80)
print("🧪 測試量化風險分析新功能")
print("="*80)

try:
    # 創建風險官實例
    risk_officer = QuantitativeRiskOfficer()
    
    print("\n【測試 1：冷靜期檢測】")
    print("-"*80)
    cooling = risk_officer.check_cooling_period()
    
    print(f"是否需要冷靜期：{'是' if cooling['should_cool'] else '否'}")
    if cooling['should_cool']:
        print(f"嚴重程度：{cooling['severity']}")
        print(f"建議休息時間：{cooling['duration_minutes']} 分鐘")
        print(f"觸發原因：{cooling['reason']}")
        print(f"連續虧損：{cooling['consecutive_losses']} 次")
        if cooling['max_daily_loss_pct'] < 0:
            print(f"最大單日虧損：{abs(cooling['max_daily_loss_pct']):.2f}%")
        print(f"\n💡 {cooling['recommendation']}")
    else:
        print(f"狀態：{cooling['reason']}")
        print(f"連續虧損：{cooling['consecutive_losses']} 次")
    
    print("\n【測試 2：Kelly Criterion 分析】")
    print("-"*80)
    kelly = risk_officer.calculate_ror_kelly()
    
    print(f"Kelly 破產風險：{kelly['kelly_ror']:.2%}")
    print(f"Kelly 最優倉位：{kelly['kelly_optimal_size']:.2%}")
    print(f"建議倉位（Half Kelly）：{kelly['recommended_size']:.2%}")
    print(f"勝率：{kelly['win_rate']:.2%}")
    print(f"賠率：{kelly['payoff_ratio']:.2f}:1")
    print(f"期望值：{kelly['expectancy']:.2f} USDT/筆")
    print(f"\n💡 {kelly['explanation']}")
    
    if kelly['kelly_optimal_size'] <= 0:
        print("\n⚠️ 警告：Kelly 最優倉位 ≤ 0，表示當前策略期望值為負，不建議交易！")
    elif kelly['kelly_optimal_size'] < 0.1:
        print(f"\n💡 建議：Kelly 最優倉位很小（{kelly['kelly_optimal_size']:.2%}），建議降低風險或改善策略")
    else:
        print(f"\n✅ Kelly 最優倉位正常，建議使用 Half Kelly: {kelly['recommended_size']:.2%}")
    
    print("\n" + "="*80)
    print("✅ 測試完成！所有功能正常運作")
    print("="*80)
    print("\n現在可以啟動 Web 界面查看完整功能：")
    print("  ./啟動Web界面v2.sh")
    print("\n或直接運行：")
    print("  streamlit run web_dashboard_v2.py")
    print()

except Exception as e:
    print(f"\n❌ 測試失敗：{e}")
    import traceback
    traceback.print_exc()
