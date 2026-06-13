"""
量化風險分析模組測試
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import tempfile
import os

from src.analysis.quantitative_risk import (
    QuantitativeRiskAnalyzer,
    KellyCriterionCalculator,
    TiltDetector,
    EmotionalControlAnalyzer,
    SkillDimensionScorer,
    FeeAnalyzer,
    CoolingPeriodChecker,
)


@pytest.fixture
def sample_trades_df():
    """創建測試用的交易數據"""
    np.random.seed(42)
    n_trades = 50
    
    data = {
        'trade_id': [f'T{i:04d}' for i in range(n_trades)],
        'symbol': ['BTCUSDT'] * n_trades,
        'direction': np.random.choice(['Long', 'Short'], n_trades),
        'leverage': np.random.uniform(5, 20, n_trades),
        'quantity': np.random.uniform(0.01, 0.1, n_trades),
        'entry_price': np.random.uniform(40000, 50000, n_trades),
        'exit_price': np.random.uniform(40000, 50000, n_trades),
        'pnl': np.random.uniform(-50, 100, n_trades),
        'fee': np.random.uniform(1, 5, n_trades),
        'open_time': [datetime.now() - timedelta(hours=n_trades-i) for i in range(n_trades)],
        'close_time': [datetime.now() - timedelta(hours=n_trades-i-0.5) for i in range(n_trades)],
    }
    
    df = pd.DataFrame(data)
    df['holding_minutes'] = (df['close_time'] - df['open_time']).dt.total_seconds() / 60
    df['is_win'] = df['pnl'] > 0
    df['is_loss'] = df['pnl'] < 0
    
    return df


@pytest.fixture
def sample_trades_json(sample_trades_df):
    """創建測試用的 JSON 檔案"""
    # 轉換 DataFrame 為 JSON 可序列化的格式
    data = sample_trades_df.to_dict('records')
    for record in data:
        record['open_time'] = record['open_time'].isoformat()
        record['close_time'] = record['close_time'].isoformat()
    
    # 創建臨時檔案
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(data, f)
        temp_path = f.name
    
    yield temp_path
    
    # 清理
    os.unlink(temp_path)


class TestKellyCriterionCalculator:
    """測試 Kelly Criterion 計算器"""
    
    def test_calculate_with_valid_data(self, sample_trades_df):
        """測試正常數據的 Kelly 計算"""
        calculator = KellyCriterionCalculator()
        result = calculator.calculate(sample_trades_df)
        
        assert 'kelly_ror' in result
        assert 'kelly_optimal_size' in result
        assert 'recommended_size' in result
        assert 'win_rate' in result
        assert 'payoff_ratio' in result
        assert 'expectancy' in result
        
        # 檢查數值範圍
        assert 0 <= result['kelly_ror'] <= 1
        assert 0 <= result['kelly_optimal_size'] <= 1
        assert 0 <= result['recommended_size'] <= 1
        assert 0 <= result['win_rate'] <= 1
    
    def test_calculate_with_empty_data(self):
        """測試空數據"""
        calculator = KellyCriterionCalculator()
        result = calculator.calculate(pd.DataFrame())
        
        assert result['kelly_ror'] == 1.0
        assert 'explanation' in result


class TestTiltDetector:
    """測試傾斜行為檢測器"""
    
    def test_detect_with_valid_data(self, sample_trades_df):
        """測試正常數據的傾斜檢測"""
        detector = TiltDetector()
        result = detector.detect(sample_trades_df)
        
        assert 'has_tilt' in result
        assert 'severity' in result
        assert 'tilt_cases_count' in result
        assert 'tilt_cases_percentage' in result
        
        # 檢查嚴重程度
        assert result['severity'] in ['none', 'low', 'medium', 'high']
    
    def test_detect_with_insufficient_data(self):
        """測試數據不足的情況"""
        detector = TiltDetector()
        df = pd.DataFrame({'is_loss': [True]})
        result = detector.detect(df)
        
        assert result['has_tilt'] == False
        assert 'explanation' in result


class TestEmotionalControlAnalyzer:
    """測試情緒控制分析器"""
    
    def test_analyze_with_valid_data(self, sample_trades_df):
        """測試正常數據的情緒控制分析"""
        analyzer = EmotionalControlAnalyzer()
        result = analyzer.analyze(sample_trades_df)
        
        assert 'emotional_control_score' in result
        assert 'severity' in result
        assert 'frequency_increase_after_loss' in result
        assert 'leverage_increase_after_loss' in result
        
        # 檢查評分範圍
        assert 0 <= result['emotional_control_score'] <= 100
        assert result['severity'] in ['none', 'low', 'medium', 'high', 'critical']
    
    def test_analyze_with_insufficient_data(self):
        """測試數據不足的情況"""
        analyzer = EmotionalControlAnalyzer()
        df = pd.DataFrame({'is_loss': [True, False]})
        result = analyzer.analyze(df)
        
        assert result['emotional_control_score'] == 100.0
        assert result['severity'] == 'none'


class TestSkillDimensionScorer:
    """測試能力維度評分器"""
    
    def test_score_with_valid_data(self, sample_trades_df):
        """測試正常數據的能力評分"""
        scorer = SkillDimensionScorer()
        result = scorer.score(sample_trades_df)
        
        assert 'direction_judgment' in result
        assert 'risk_management' in result
        assert 'psychological_resilience' in result
        assert 'execution_discipline' in result
        assert 'cost_awareness' in result
        assert 'overall_score' in result
        
        # 檢查評分範圍
        for key in ['direction_judgment', 'risk_management', 'psychological_resilience', 
                    'execution_discipline', 'cost_awareness', 'overall_score']:
            assert 0 <= result[key] <= 10
    
    def test_score_with_insufficient_data(self):
        """測試數據不足的情況"""
        scorer = SkillDimensionScorer()
        df = pd.DataFrame({'is_win': [True] * 5})
        result = scorer.score(df)
        
        assert result['overall_score'] == 0.0
        assert 'explanation' in result


class TestFeeAnalyzer:
    """測試手續費分析器"""
    
    def test_analyze_fee_pressure(self, sample_trades_df):
        """測試手續費壓力分析"""
        analyzer = FeeAnalyzer()
        result = analyzer.analyze_fee_pressure(sample_trades_df)
        
        assert 'total_fee' in result
        assert 'total_loss' in result
        assert 'fee_to_loss_ratio' in result
        assert result['total_fee'] > 0
    
    def test_analyze_short_term_trades(self, sample_trades_df):
        """測試短線交易分析"""
        analyzer = FeeAnalyzer()
        result = analyzer.analyze_short_term_trades(sample_trades_df, threshold_minutes=30.0)
        
        assert 'count' in result
        # percentage 只在有短線交易時才會出現
        if result['count'] > 0:
            assert 'percentage' in result
        assert result['count'] >= 0
    
    def test_simulate_without_short_trades(self, sample_trades_df):
        """測試模擬停止短線交易"""
        analyzer = FeeAnalyzer()
        result = analyzer.simulate_without_short_trades(sample_trades_df, threshold_minutes=30.0)
        
        if 'pnl_difference' in result:
            assert 'original_pnl' in result
            assert 'new_pnl' in result
            assert 'fee_saved' in result


class TestCoolingPeriodChecker:
    """測試冷靜期檢測器"""
    
    def test_check_with_valid_data(self, sample_trades_df):
        """測試正常數據的冷靜期檢測"""
        checker = CoolingPeriodChecker()
        result = checker.check(sample_trades_df)
        
        assert 'should_cool' in result
        assert 'duration_minutes' in result
        assert 'reason' in result
        assert 'severity' in result
        
        if result['should_cool']:
            assert result['duration_minutes'] > 0
            assert result['severity'] in ['low', 'medium', 'high', 'critical']
    
    def test_check_with_empty_data(self):
        """測試空數據"""
        checker = CoolingPeriodChecker()
        result = checker.check(pd.DataFrame())
        
        assert result['should_cool'] == False
        assert result['reason'] == '無數據'


class TestQuantitativeRiskAnalyzer:
    """測試量化風險分析器主類"""
    
    def test_initialization_without_data(self):
        """測試無數據初始化"""
        analyzer = QuantitativeRiskAnalyzer()
        assert analyzer.df is None
    
    def test_initialization_with_dataframe(self):
        """測試使用 DataFrame 初始化"""
        # 創建測試數據
        test_data = pd.DataFrame({
            'pnl': [100, -50, 200, -30],
            'close_time': pd.date_range('2024-01-01', periods=4, freq='h'),
            'open_time': pd.date_range('2024-01-01', periods=4, freq='h') - pd.Timedelta(minutes=30)
        })
        
        analyzer = QuantitativeRiskAnalyzer(trades_df=test_data)
        
        assert analyzer.df is not None
        assert len(analyzer.df) == 4
        assert 'is_win' in analyzer.df.columns
        assert 'is_loss' in analyzer.df.columns
        assert analyzer.kelly_calculator is not None
        assert analyzer.tilt_detector is not None
    
    def test_initialization_with_data(self, sample_trades_json):
        """測試帶數據初始化"""
        analyzer = QuantitativeRiskAnalyzer(sample_trades_json)
        assert analyzer.df is not None
        assert len(analyzer.df) > 0
    
    def test_load_data(self, sample_trades_json):
        """測試數據載入"""
        analyzer = QuantitativeRiskAnalyzer()
        analyzer.load_data(sample_trades_json)
        
        assert analyzer.df is not None
        assert 'pnl' in analyzer.df.columns
        assert 'is_win' in analyzer.df.columns
        assert 'is_loss' in analyzer.df.columns
    
    def test_calculate_ror_kelly(self, sample_trades_json):
        """測試 Kelly Criterion 計算"""
        analyzer = QuantitativeRiskAnalyzer(sample_trades_json)
        result = analyzer.calculate_ror_kelly()
        
        assert 'kelly_ror' in result
        assert 'kelly_optimal_size' in result
    
    def test_detect_tilt_behavior(self, sample_trades_json):
        """測試傾斜行為檢測"""
        analyzer = QuantitativeRiskAnalyzer(sample_trades_json)
        result = analyzer.detect_tilt_behavior()
        
        assert 'has_tilt' in result
        assert 'severity' in result
    
    def test_analyze_emotional_control(self, sample_trades_json):
        """測試情緒控制分析"""
        analyzer = QuantitativeRiskAnalyzer(sample_trades_json)
        result = analyzer.analyze_emotional_control()
        
        assert 'emotional_control_score' in result
        assert 'severity' in result
    
    def test_calculate_skill_dimensions(self, sample_trades_json):
        """測試能力維度評分"""
        analyzer = QuantitativeRiskAnalyzer(sample_trades_json)
        result = analyzer.calculate_skill_dimensions()
        
        assert 'overall_score' in result
        assert 'direction_judgment' in result
    
    def test_calculate_fee_pressure(self, sample_trades_json):
        """測試手續費壓力計算"""
        analyzer = QuantitativeRiskAnalyzer(sample_trades_json)
        result = analyzer.calculate_fee_pressure()
        
        assert 'total_fee' in result
        assert 'fee_to_loss_ratio' in result
    
    def test_check_cooling_period(self, sample_trades_json):
        """測試冷靜期檢測"""
        analyzer = QuantitativeRiskAnalyzer(sample_trades_json)
        result = analyzer.check_cooling_period()
        
        assert 'should_cool' in result
        assert 'reason' in result
    
    def test_calculate_max_losing_streak(self, sample_trades_json):
        """測試最長連損計算"""
        analyzer = QuantitativeRiskAnalyzer(sample_trades_json)
        result = analyzer.calculate_max_losing_streak()
        
        assert 'max_streak' in result
        assert 'total_loss_in_streak' in result
    
    def test_calculate_risk_of_ruin(self, sample_trades_json):
        """測試破產風險計算"""
        analyzer = QuantitativeRiskAnalyzer(sample_trades_json)
        result = analyzer.calculate_risk_of_ruin()
        
        assert 'risk_of_ruin' in result
        assert 'win_rate' in result
        assert 'expectancy' in result
    
    def test_calculate_recovery_factor(self, sample_trades_json):
        """測試恢復係數計算"""
        analyzer = QuantitativeRiskAnalyzer(sample_trades_json)
        result = analyzer.calculate_recovery_factor()
        
        assert 'max_drawdown' in result
        assert 'max_drawdown_pct' in result
        assert 'recovery_needed_pct' in result


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
