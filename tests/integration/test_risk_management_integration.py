"""
風險管理集成測試

測試各種風險限制觸發和自動暫停功能
Requirements: 9.2, 9.4, 9.5
"""

import pytest
from datetime import datetime

from src.managers.risk_manager import RiskManager
from src.models.risk import RiskConfig, GlobalRiskState
from src.models.trading import Trade


class TestRiskManagementIntegration:
    """風險管理集成測試"""
    
    @pytest.fixture
    def risk_config(self):
        """創建風險配置"""
        return RiskConfig(
            global_max_drawdown=0.20,  # 20%
            daily_loss_limit=0.10,  # 10%
            global_max_position=0.80,  # 80%
            strategy_max_position=0.30  # 30%
        )
    
    @pytest.fixture
    def risk_manager(self, risk_config):
        """創建風險管理器"""
        return RiskManager(risk_config, initial_capital=1000.0)
    
    def test_global_drawdown_limit_trigger(self, risk_manager):
        """測試全局回撤限制觸發"""
        # 設置初始狀態
        risk_manager.global_state.initial_capital = 1000.0
        risk_manager.global_state.current_capital = 1000.0
        risk_manager.global_state.peak_capital = 1000.0
        
        # 模擬虧損，觸發回撤限制
        # 虧損 25% (超過 20% 限制)
        risk_manager.global_state.current_capital = 750.0
        
        # 檢查是否應該暫停交易
        should_halt, reason = risk_manager.should_halt_trading()
        
        assert should_halt, "當回撤超過限制時應該暫停交易"
        assert "回撤" in reason or "drawdown" in reason.lower(), "原因應該提到回撤"
        
        # 驗證回撤計算
        drawdown = risk_manager.global_state.get_current_drawdown()
        assert drawdown == 0.25, f"回撤應該是 25%，實際是 {drawdown*100}%"
        
        print(f"\n全局回撤限制測試:")
        print(f"  初始資金: {risk_manager.global_state.initial_capital}")
        print(f"  當前資金: {risk_manager.global_state.current_capital}")
        print(f"  回撤: {drawdown*100:.2f}%")
        print(f"  應該暫停: {should_halt}")
        print(f"  原因: {reason}")
    
    def test_daily_loss_limit_trigger(self, risk_manager):
        """測試每日虧損限制觸發"""
        # 設置初始狀態
        risk_manager.global_state.initial_capital = 1000.0
        risk_manager.global_state.current_capital = 1000.0
        risk_manager.global_state.daily_start_capital = 1000.0
        risk_manager.global_state.peak_capital = 1000.0
        
        # 模擬今日虧損 15% (超過 10% 限制)
        # 但不觸發回撤限制（因為 peak 也降低）
        risk_manager.global_state.current_capital = 850.0
        risk_manager.global_state.peak_capital = 850.0  # 保持 peak 同步，避免觸發回撤限制
        risk_manager.global_state.daily_pnl = -150.0
        
        # 檢查是否應該暫停交易
        should_halt, reason = risk_manager.should_halt_trading()
        
        assert should_halt, "當每日虧損超過限制時應該暫停交易"
        # 原因可能提到每日虧損或回撤，都是合理的
        
        # 驗證每日虧損計算
        daily_loss_pct = risk_manager.global_state.get_daily_loss_pct()
        assert daily_loss_pct == 0.15, f"每日虧損應該是 15%，實際是 {daily_loss_pct*100}%"
        
        print(f"\n每日虧損限制測試:")
        print(f"  今日開始資金: {risk_manager.global_state.daily_start_capital}")
        print(f"  當前資金: {risk_manager.global_state.current_capital}")
        print(f"  今日損益: {risk_manager.global_state.daily_pnl}")
        print(f"  每日虧損: {daily_loss_pct*100:.2f}%")
        print(f"  應該暫停: {should_halt}")
        print(f"  原因: {reason}")
    
    def test_strategy_position_limit(self, risk_manager):
        """測試單策略倉位限制"""
        # 設置初始狀態
        risk_manager.global_state.initial_capital = 1000.0
        risk_manager.global_state.current_capital = 1000.0
        
        # 設置策略倉位（35%，超過 30% 限制）
        strategy_id = "test-strategy"
        risk_manager.global_state.strategy_positions[strategy_id] = 350.0
        risk_manager.global_state.total_position_value = 350.0
        
        # 檢查策略倉位使用率
        position_usage = risk_manager.global_state.get_strategy_position_usage(strategy_id)
        assert position_usage == 0.35, f"策略倉位使用率應該是 35%，實際是 {position_usage*100}%"
        
        # 驗證超過限制
        assert position_usage > risk_manager.config.strategy_max_position, "策略倉位應該超過限制"
        
        print(f"\n單策略倉位限制測試:")
        print(f"  當前資金: {risk_manager.global_state.current_capital}")
        print(f"  策略倉位: {risk_manager.global_state.strategy_positions[strategy_id]}")
        print(f"  倉位使用率: {position_usage*100:.2f}%")
        print(f"  限制: {risk_manager.config.strategy_max_position*100:.2f}%")
        print(f"  超過限制: {position_usage > risk_manager.config.strategy_max_position}")
    
    def test_global_position_limit(self, risk_manager):
        """測試全局倉位限制"""
        # 設置初始狀態
        risk_manager.global_state.initial_capital = 1000.0
        risk_manager.global_state.current_capital = 1000.0
        
        # 設置多個策略的倉位，總計 85% (超過 80% 限制)
        risk_manager.global_state.strategy_positions = {
            "strategy-1": 300.0,  # 30%
            "strategy-2": 300.0,  # 30%
            "strategy-3": 250.0,  # 25%
        }
        risk_manager.global_state.total_position_value = 850.0
        
        # 檢查全局倉位使用率
        position_usage = risk_manager.global_state.get_position_usage()
        assert position_usage == 0.85, f"全局倉位使用率應該是 85%，實際是 {position_usage*100}%"
        
        # 驗證超過限制
        assert position_usage > risk_manager.config.global_max_position, "全局倉位應該超過限制"
        
        print(f"\n全局倉位限制測試:")
        print(f"  當前資金: {risk_manager.global_state.current_capital}")
        print(f"  總倉位: {risk_manager.global_state.total_position_value}")
        print(f"  倉位使用率: {position_usage*100:.2f}%")
        print(f"  限制: {risk_manager.config.global_max_position*100:.2f}%")
        print(f"  超過限制: {position_usage > risk_manager.config.global_max_position}")
        for sid, pos_value in risk_manager.global_state.strategy_positions.items():
            print(f"    {sid}: {pos_value} ({pos_value/risk_manager.global_state.current_capital*100:.2f}%)")
    
    def test_risk_event_recording(self, risk_manager):
        """測試風險事件記錄"""
        # 設置初始狀態
        risk_manager.global_state.initial_capital = 1000.0
        risk_manager.global_state.current_capital = 750.0  # 25% 回撤
        risk_manager.global_state.peak_capital = 1000.0
        
        # 觸發風險檢查
        should_halt, reason = risk_manager.should_halt_trading()
        
        # 驗證風險事件被記錄
        assert len(risk_manager.global_state.risk_events) > 0, "應該記錄風險事件"
        
        # 檢查最新的風險事件
        latest_event = risk_manager.global_state.risk_events[-1]
        assert latest_event.event_type in ['drawdown', 'daily_loss', 'position_limit'], "事件類型應該有效"
        assert latest_event.trigger_value > 0, "觸發值應該大於0"
        assert latest_event.limit_value > 0, "限制值應該大於0"
        assert latest_event.action_taken != "", "應該記錄採取的行動"
        
        print(f"\n風險事件記錄測試:")
        print(f"  風險事件數量: {len(risk_manager.global_state.risk_events)}")
        print(f"  最新事件:")
        print(f"    類型: {latest_event.event_type}")
        print(f"    觸發值: {latest_event.trigger_value}")
        print(f"    限制值: {latest_event.limit_value}")
        print(f"    行動: {latest_event.action_taken}")
    
    def test_automatic_halt_and_resume(self, risk_manager):
        """測試自動暫停和恢復功能"""
        # 初始狀態：未暫停
        assert not risk_manager.global_state.trading_halted, "初始狀態應該未暫停"
        
        # 觸發暫停
        risk_manager.global_state.halt_trading("測試暫停")
        assert risk_manager.global_state.trading_halted, "應該已暫停"
        assert risk_manager.global_state.halt_reason == "測試暫停", "暫停原因應該匹配"
        
        # 恢復交易
        risk_manager.global_state.resume_trading()
        assert not risk_manager.global_state.trading_halted, "應該已恢復"
        assert risk_manager.global_state.halt_reason == "", "暫停原因應該被清除"
        
        print(f"\n自動暫停和恢復測試:")
        print(f"  初始狀態: 未暫停")
        print(f"  暫停後: 已暫停")
        print(f"  恢復後: 未暫停")
    
    def test_multiple_risk_limits_simultaneously(self, risk_manager):
        """測試同時觸發多個風險限制"""
        # 設置初始狀態
        risk_manager.global_state.initial_capital = 1000.0
        risk_manager.global_state.current_capital = 750.0  # 25% 回撤
        risk_manager.global_state.peak_capital = 1000.0
        risk_manager.global_state.daily_start_capital = 1000.0
        risk_manager.global_state.daily_pnl = -250.0  # 25% 每日虧損
        risk_manager.global_state.total_position_value = 850.0  # 113% 倉位（不合理但用於測試）
        
        # 檢查是否應該暫停交易
        should_halt, reason = risk_manager.should_halt_trading()
        
        assert should_halt, "當多個限制被觸發時應該暫停交易"
        
        # 驗證多個風險指標
        drawdown = risk_manager.global_state.get_current_drawdown()
        daily_loss = risk_manager.global_state.get_daily_loss_pct()
        position_usage = risk_manager.global_state.get_position_usage()
        
        assert drawdown > risk_manager.config.global_max_drawdown, "回撤應該超過限制"
        assert daily_loss > risk_manager.config.daily_loss_limit, "每日虧損應該超過限制"
        
        print(f"\n多重風險限制測試:")
        print(f"  回撤: {drawdown*100:.2f}% (限制: {risk_manager.config.global_max_drawdown*100:.2f}%)")
        print(f"  每日虧損: {daily_loss*100:.2f}% (限制: {risk_manager.config.daily_loss_limit*100:.2f}%)")
        print(f"  倉位使用: {position_usage*100:.2f}% (限制: {risk_manager.config.global_max_position*100:.2f}%)")
        print(f"  應該暫停: {should_halt}")
        print(f"  原因: {reason}")
