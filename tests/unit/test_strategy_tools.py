"""
策略開發工具單元測試

測試策略腳手架生成、驗證和版本管理功能。
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
import sys
import os

# 添加 tools 目錄到路徑
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'tools'))

from create_strategy import (
    kebab_to_pascal,
    validate_strategy_id,
    create_strategy,
)
from validate_strategy import (
    ConfigValidator,
    CodeValidator,
    ValidationResult,
)
from version_strategy import VersionManager


class TestCreateStrategy:
    """測試策略腳手架生成器"""
    
    def test_kebab_to_pascal(self):
        """測試 kebab-case 轉 PascalCase"""
        assert kebab_to_pascal('my-strategy') == 'MyStrategy'
        assert kebab_to_pascal('trend-follow') == 'TrendFollow'
        assert kebab_to_pascal('simple') == 'Simple'
        assert kebab_to_pascal('multi-timeframe-v2') == 'MultiTimeframeV2'
    
    def test_validate_strategy_id_valid(self):
        """測試有效的策略 ID"""
        assert validate_strategy_id('my-strategy') == True
        assert validate_strategy_id('trend-follow') == True
        assert validate_strategy_id('simple') == True
        assert validate_strategy_id('strategy-v1') == True
        assert validate_strategy_id('test123') == True
    
    def test_validate_strategy_id_invalid(self):
        """測試無效的策略 ID"""
        assert validate_strategy_id('') == False
        assert validate_strategy_id('My-Strategy') == False  # 大寫
        assert validate_strategy_id('my_strategy') == False  # 下劃線
        assert validate_strategy_id('my strategy') == False  # 空格
        assert validate_strategy_id('-my-strategy') == False  # 開頭連字符
        assert validate_strategy_id('my-strategy-') == False  # 結尾連字符
    
    def test_create_strategy_success(self):
        """測試成功創建策略腳手架"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / 'strategies'
            config_dir = Path(tmpdir) / 'configs'
            
            success, message = create_strategy(
                strategy_id='test-strategy',
                strategy_name='測試策略',
                symbol='BTCUSDT',
                timeframes=['1h', '4h'],
                output_dir=str(output_dir),
                config_dir=str(config_dir),
            )
            
            assert success == True
            assert '成功' in message
            
            # 檢查文件是否創建
            code_file = output_dir / 'test_strategy_strategy.py'
            config_file = config_dir / 'test-strategy.json'
            
            assert code_file.exists()
            assert config_file.exists()
            
            # 檢查代碼文件內容
            code_content = code_file.read_text(encoding='utf-8')
            assert 'TestStrategyStrategy' in code_content
            assert 'test-strategy' in code_content
            
            # 檢查配置文件內容
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            assert config['strategy_id'] == 'test-strategy'
            assert config['strategy_name'] == '測試策略'
            assert config['symbol'] == 'BTCUSDT'
            assert config['timeframes'] == ['1h', '4h']
    
    def test_create_strategy_invalid_id(self):
        """測試無效的策略 ID"""
        with tempfile.TemporaryDirectory() as tmpdir:
            success, message = create_strategy(
                strategy_id='Invalid-ID',  # 大寫
                strategy_name='測試',
                symbol='BTCUSDT',
                timeframes=['1h'],
                output_dir=tmpdir,
                config_dir=tmpdir,
            )
            
            assert success == False
            assert '無效' in message
    
    def test_create_strategy_file_exists(self):
        """測試文件已存在的情況"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / 'strategies'
            config_dir = Path(tmpdir) / 'configs'
            
            # 第一次創建
            create_strategy(
                strategy_id='test-strategy',
                strategy_name='測試',
                symbol='BTCUSDT',
                timeframes=['1h'],
                output_dir=str(output_dir),
                config_dir=str(config_dir),
            )
            
            # 第二次創建（應該失敗）
            success, message = create_strategy(
                strategy_id='test-strategy',
                strategy_name='測試',
                symbol='BTCUSDT',
                timeframes=['1h'],
                output_dir=str(output_dir),
                config_dir=str(config_dir),
            )
            
            assert success == False
            assert '已存在' in message


class TestConfigValidator:
    """測試配置文件驗證器"""
    
    def test_validate_valid_config(self):
        """測試有效的配置文件"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            config = {
                'strategy_id': 'test-strategy',
                'strategy_name': '測試策略',
                'version': '1.0.0',
                'symbol': 'BTCUSDT',
                'timeframes': ['1h', '4h'],
                'risk_management': {
                    'position_size': 0.2,
                    'leverage': 5,
                    'max_trades_per_day': 3,
                    'max_consecutive_losses': 3,
                    'daily_loss_limit': 0.1,
                    'stop_loss_atr': 2.0,
                    'take_profit_atr': 4.0,
                }
            }
            json.dump(config, f)
            config_path = f.name
        
        try:
            validator = ConfigValidator()
            result = validator.validate_config_file(config_path)
            
            assert result.is_valid() == True
            assert len(result.errors) == 0
        finally:
            os.unlink(config_path)
    
    def test_validate_missing_required_field(self):
        """測試缺少必需字段"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            config = {
                'strategy_id': 'test-strategy',
                # 缺少 strategy_name
                'version': '1.0.0',
                'symbol': 'BTCUSDT',
                'timeframes': ['1h'],
            }
            json.dump(config, f)
            config_path = f.name
        
        try:
            validator = ConfigValidator()
            result = validator.validate_config_file(config_path)
            
            assert result.is_valid() == False
            assert any('strategy_name' in error for error in result.errors)
        finally:
            os.unlink(config_path)
    
    def test_validate_invalid_timeframe(self):
        """測試無效的時間週期"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            config = {
                'strategy_id': 'test-strategy',
                'strategy_name': '測試',
                'version': '1.0.0',
                'symbol': 'BTCUSDT',
                'timeframes': ['1h', 'invalid'],  # 無效週期
                'risk_management': {
                    'position_size': 0.2,
                    'leverage': 5,
                    'max_trades_per_day': 3,
                    'max_consecutive_losses': 3,
                    'daily_loss_limit': 0.1,
                    'stop_loss_atr': 2.0,
                    'take_profit_atr': 4.0,
                }
            }
            json.dump(config, f)
            config_path = f.name
        
        try:
            validator = ConfigValidator()
            result = validator.validate_config_file(config_path)
            
            assert result.is_valid() == False
            assert any('invalid' in error for error in result.errors)
        finally:
            os.unlink(config_path)
    
    def test_validate_invalid_risk_values(self):
        """測試無效的風險管理參數"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            config = {
                'strategy_id': 'test-strategy',
                'strategy_name': '測試',
                'version': '1.0.0',
                'symbol': 'BTCUSDT',
                'timeframes': ['1h'],
                'risk_management': {
                    'position_size': 1.5,  # 超出範圍
                    'leverage': 0,  # 無效值
                    'max_trades_per_day': 3,
                    'max_consecutive_losses': 3,
                    'daily_loss_limit': 0.1,
                    'stop_loss_atr': -1.0,  # 負數
                    'take_profit_atr': 4.0,
                }
            }
            json.dump(config, f)
            config_path = f.name
        
        try:
            validator = ConfigValidator()
            result = validator.validate_config_file(config_path)
            
            assert result.is_valid() == False
            assert len(result.errors) >= 3  # 至少 3 個錯誤
        finally:
            os.unlink(config_path)


class TestVersionManager:
    """測試版本管理器"""
    
    def test_parse_version(self):
        """測試版本號解析"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            config = {
                'strategy_id': 'test',
                'strategy_name': '測試',
                'version': '1.2.3',
            }
            json.dump(config, f)
            config_path = f.name
        
        try:
            manager = VersionManager(config_path)
            major, minor, patch = manager.parse_version('1.2.3')
            
            assert major == 1
            assert minor == 2
            assert patch == 3
        finally:
            os.unlink(config_path)
    
    def test_parse_version_invalid(self):
        """測試無效的版本號"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            config = {'strategy_id': 'test', 'version': '1.0.0'}
            json.dump(config, f)
            config_path = f.name
        
        try:
            manager = VersionManager(config_path)
            
            with pytest.raises(ValueError):
                manager.parse_version('1.2')  # 缺少補丁版本
            
            with pytest.raises(ValueError):
                manager.parse_version('1.2.x')  # 非數字
        finally:
            os.unlink(config_path)
    
    def test_bump_patch_version(self):
        """測試升級補丁版本"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / 'test.json'
            config = {
                'strategy_id': 'test',
                'strategy_name': '測試',
                'version': '1.0.0',
            }
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f)
            
            manager = VersionManager(str(config_path))
            old_version, new_version = manager.bump_version('patch', '修復錯誤')
            
            assert old_version == '1.0.0'
            assert new_version == '1.0.1'
            
            # 檢查配置文件已更新
            with open(config_path, 'r', encoding='utf-8') as f:
                updated_config = json.load(f)
            assert updated_config['version'] == '1.0.1'
    
    def test_bump_minor_version(self):
        """測試升級次版本"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / 'test.json'
            config = {
                'strategy_id': 'test',
                'strategy_name': '測試',
                'version': '1.2.3',
            }
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f)
            
            manager = VersionManager(str(config_path))
            old_version, new_version = manager.bump_version('minor', '新增功能')
            
            assert old_version == '1.2.3'
            assert new_version == '1.3.0'  # 補丁版本重置為 0
    
    def test_bump_major_version(self):
        """測試升級主版本"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / 'test.json'
            config = {
                'strategy_id': 'test',
                'strategy_name': '測試',
                'version': '1.2.3',
            }
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f)
            
            manager = VersionManager(str(config_path))
            old_version, new_version = manager.bump_version('major', '重大變更')
            
            assert old_version == '1.2.3'
            assert new_version == '2.0.0'  # 次版本和補丁版本重置為 0
    
    def test_version_history(self):
        """測試版本歷史記錄"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / 'test.json'
            config = {
                'strategy_id': 'test',
                'strategy_name': '測試',
                'version': '1.0.0',
            }
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f)
            
            manager = VersionManager(str(config_path))
            
            # 升級幾次
            manager.bump_version('patch', '修復 1')
            manager.bump_version('patch', '修復 2')
            manager.bump_version('minor', '新功能')
            
            # 檢查歷史
            history = manager.show_history()
            assert len(history) == 3
            
            assert history[0]['old_version'] == '1.0.0'
            assert history[0]['new_version'] == '1.0.1'
            assert history[0]['message'] == '修復 1'
            
            assert history[1]['old_version'] == '1.0.1'
            assert history[1]['new_version'] == '1.0.2'
            
            assert history[2]['old_version'] == '1.0.2'
            assert history[2]['new_version'] == '1.1.0'


class TestCodeValidator:
    """測試代碼驗證器"""
    
    def test_validate_valid_strategy_code(self):
        """測試有效的策略代碼"""
        code = '''
from src.execution.strategy import Strategy
from src.models.config import StrategyConfig
from src.models.market_data import MarketData
from src.models.trading import Signal, Position

class TestStrategy(Strategy):
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
    
    def generate_signal(self, market_data: MarketData) -> Signal:
        pass
    
    def calculate_position_size(self, capital: float, price: float) -> float:
        pass
    
    def calculate_stop_loss(self, entry_price: float, direction: str, atr: float) -> float:
        pass
    
    def calculate_take_profit(self, entry_price: float, direction: str, atr: float) -> float:
        pass
    
    def should_exit(self, position: Position, market_data: MarketData) -> tuple[bool, str]:
        pass
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(code)
            code_path = f.name
        
        try:
            validator = CodeValidator()
            result = validator.validate_code_file(code_path)
            
            # 應該沒有錯誤（只有警告，因為方法是空的）
            assert len(result.errors) == 0
            assert len(result.warnings) > 0  # 有 TODO 或空方法警告
        finally:
            os.unlink(code_path)
    
    def test_validate_missing_method(self):
        """測試缺少必需方法"""
        code = '''
from src.execution.strategy import Strategy

class TestStrategy(Strategy):
    def __init__(self, config):
        super().__init__(config)
    
    def generate_signal(self, market_data):
        pass
    
    # 缺少其他必需方法
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(code)
            code_path = f.name
        
        try:
            validator = CodeValidator()
            result = validator.validate_code_file(code_path)
            
            assert result.is_valid() == False
            assert len(result.errors) >= 4  # 缺少 4 個方法
        finally:
            os.unlink(code_path)
    
    def test_validate_no_strategy_class(self):
        """測試沒有策略類"""
        code = '''
# 普通的 Python 代碼，沒有策略類
def some_function():
    pass
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(code)
            code_path = f.name
        
        try:
            validator = CodeValidator()
            result = validator.validate_code_file(code_path)
            
            assert result.is_valid() == False
            assert any('未找到' in error for error in result.errors)
        finally:
            os.unlink(code_path)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
