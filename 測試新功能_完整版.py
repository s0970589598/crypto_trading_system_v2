#!/usr/bin/env python3
"""
測試所有量化風險分析新功能
包括：冷靜期、Kelly Criterion、情緒失控係數、能力維度評分
"""

from quantitative_risk_analysis import QuantitativeRiskOfficer

print("="*80)
print("🧪 測試量化風險分析完整功能")
print("="*80)

try:
    # 創建風險官實例
    risk_officer = QuantitativeRiskOfficer()
    
    print("\n【測試 1：冷靜期檢測】")
    print("-"*80)
    cooling = risk_officer.check_cooling_period()
    print(f"✅ 冷靜期檢測：{'需要休息' if cooling['should_cool'] else '狀態正常'}")
    if cooling['should_cool']:
        print(f"   嚴重程度：{cooling['severity']}")
        print(f"   建議休息：{cooling['duration_minutes']} 分鐘")
    
    print("\n【測試 2：Kelly Criterion 分析】")
    print("-"*80)
    kelly = risk_officer.calculate_ror_kelly()
    print(f"✅ Kelly 最優倉位：{kelly['kelly_optimal_size']:.2%}")
    print(f"   建議倉位：{kelly['recommended_size']:.2%}")
    print(f"   期望值：{kelly['expectancy']:.2f} USDT/筆")
    
    print("\n【測試 3：情緒失控係數分析】")
    print("-"*80)
    emotional = risk_officer.analyze_emotional_control()
    print(f"✅ 情緒控制評分：{emotional['emotional_control_score']:.1f}/100")
    print(f"   嚴重程度：{emotional['severity']}")
    print(f"   虧損後頻率增加：{emotional['frequency_increase_after_loss']:+.1f}%")
    print(f"   虧損後槓桿增加：{emotional['leverage_increase_after_loss']:+.1f}%")
    print(f"   情緒失控案例：{emotional['cases_count']} 次")
    
    print("\n【測試 4：能力維度評分】")
    print("-"*80)
    skills = risk_officer.calculate_skill_dimensions()
    print(f"✅ 綜合能力評分：{skills['overall_score']:.1f}/10")
    print(f"\n   各維度評分：")
    print(f"   - 方向研判力：{skills['direction_judgment']:.1f}/10")
    print(f"   - 風險控管力：{skills['risk_management']:.1f}/10")
    print(f"   - 心理韌性：{skills['psychological_resilience']:.1f}/10")
    print(f"   - 執行紀律：{skills['execution_discipline']:.1f}/10")
    print(f"   - 成本意識：{skills['cost_awareness']:.1f}/10")
    
    print("\n" + "="*80)
    print("✅ 所有測試完成！功能正常運作")
    print("="*80)
    print("\n現在可以啟動 Web 界面查看完整功能：")
    print("  ./啟動Web界面v2.sh")
    print("\n或直接運行：")
    print("  streamlit run web_dashboard_v2.py")
    print("\n或查看完整報告：")
    print("  python3 quantitative_risk_analysis.py")
    print()

except Exception as e:
    print(f"\n❌ 測試失敗：{e}")
    import traceback
    traceback.print_exc()
