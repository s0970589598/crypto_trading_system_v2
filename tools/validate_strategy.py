#!/usr/bin/env python3
"""
策略驗證工具

檢查策略邏輯完整性和配置文件格式。

使用方法：
    # 驗證配置文件
    python tools/validate_strategy.py --config strategies/my-strategy.json
    
    # 驗證策略代碼
    python tools/validate_strategy.py --code src/strategies/my_strategy.py
    
    # 同時驗證配置和代碼
    python tools/validate_strategy.py --config strategies/my-strategy.json --code src/strategies/my_strategy.py
    
    # 驗證整個目錄
    python tools/validate_strategy.py --config-dir strategies/
"""

import argparse
import ast
import json
import sys
from pathlib import Path
from typing import List, Tuple, Optional
import importlib.util


class ValidationResult:
    """驗證結果"""
    
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []
    
    def add_error(self, message: str):
        """添加錯誤"""
        self.errors.append(f"❌ 錯誤：{message}")
    
    def add_warning(self, message: str):
        """添加警告"""
        self.warnings.append(f"⚠️  警告：{message}")
    
    def add_info(self, message: str):
        """添加信息"""
        self.info.append(f"ℹ️  信息：{message}")
    
    def is_valid(self) -> bool:
        """是否通過驗證（無錯誤）"""
        return len(self.errors) == 0
    
    def print_results(self, verbose: bool = True):
        """打印結果"""
        if self.errors:
            print("\n錯誤：")
            for error in self.errors:
                print(f"  {error}")
        
        if self.warnings:
            print("\n警告：")
            for warning in self.warnings:
                print(f"  {warning}")
        
        if verbose and self.info:
            print("\n信息：")
            for info in self.info:
                print(f"  {info}")
        
        if self.is_valid():
            print("\n✅ 驗證通過！")
        else:
            print(f"\n❌ 驗證失敗：發現 {len(self.errors)} 個錯誤")


class ConfigValidator:
    """配置文件驗證器"""
    
    REQUIRED_FIELDS = [
        'strategy_id',
        'strategy_name',
        'version',
        'symbol',
        'timeframes',
        'risk_management',
    ]
    
    REQUIRED_RISK_FIELDS = [
        'position_size',
        'leverage',
        'max_trades_per_day',
        'max_consecutive_losses',
        'daily_loss_limit',
        'stop_loss_atr',
        'take_profit_atr',
    ]
    
    VALID_TIMEFRAMES = [
        '1m', '3m', '5m', '15m', '30m',
        '1h', '2h', '4h', '6h', '8h', '12h',
        '1d', '3d', '1w', '1M'
    ]
    
    def validate_config_file(self, config_path: str) -> ValidationResult:
        """驗證配置文件
        
        Args:
            config_path: 配置文件路徑
        
        Returns:
            ValidationResult: 驗證結果
        """
        result = ValidationResult()
        
        # 檢查文件存在
        path = Path(config_path)
        if not path.exists():
            result.add_error(f"配置文件不存在：{config_path}")
            return result
        
        result.add_info(f"驗證配置文件：{config_path}")
        
        # 讀取 JSON
        try:
            with open(path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except json.JSONDecodeError as e:
            result.add_error(f"JSON 格式錯誤：{e}")
            return result
        except Exception as e:
            result.add_error(f"讀取文件失敗：{e}")
            return result
        
        # 驗證必需字段
        self._validate_required_fields(config, result)
        
        # 驗證字段值
        if result.is_valid():
            self._validate_field_values(config, result)
        
        # 驗證風險管理配置
        if 'risk_management' in config:
            self._validate_risk_management(config['risk_management'], result)
        
        return result
    
    def _validate_required_fields(self, config: dict, result: ValidationResult):
        """驗證必需字段"""
        for field in self.REQUIRED_FIELDS:
            if field not in config:
                result.add_error(f"缺少必需字段：{field}")
            elif not config[field]:
                result.add_error(f"字段不能為空：{field}")
    
    def _validate_field_values(self, config: dict, result: ValidationResult):
        """驗證字段值"""
        # 驗證 strategy_id 格式
        strategy_id = config.get('strategy_id', '')
        if strategy_id:
            import re
            if not re.match(r'^[a-z0-9]+(-[a-z0-9]+)*$', strategy_id):
                result.add_error(
                    f"strategy_id 格式錯誤：{strategy_id}。"
                    f"必須使用 kebab-case 格式（如 my-strategy）"
                )
        
        # 驗證 version 格式
        version = config.get('version', '')
        if version:
            import re
            if not re.match(r'^\d+\.\d+\.\d+$', version):
                result.add_warning(
                    f"version 格式建議使用語義化版本（如 1.0.0）：{version}"
                )
        
        # 驗證 symbol
        symbol = config.get('symbol', '')
        if symbol and not symbol.isupper():
            result.add_warning(f"symbol 建議使用大寫：{symbol}")
        
        # 驗證 timeframes
        timeframes = config.get('timeframes', [])
        if not isinstance(timeframes, list):
            result.add_error("timeframes 必須是列表")
        elif not timeframes:
            result.add_error("timeframes 不能為空")
        else:
            for tf in timeframes:
                if tf not in self.VALID_TIMEFRAMES:
                    result.add_error(
                        f"無效的時間週期：{tf}。"
                        f"有效值：{', '.join(self.VALID_TIMEFRAMES)}"
                    )
        
        # 驗證 parameters
        if 'parameters' in config:
            if not isinstance(config['parameters'], dict):
                result.add_error("parameters 必須是字典")
        
        # 驗證 entry_conditions
        if 'entry_conditions' in config:
            if not isinstance(config['entry_conditions'], list):
                result.add_error("entry_conditions 必須是列表")
            elif not config['entry_conditions']:
                result.add_warning("entry_conditions 為空，策略可能無法生成信號")
    
    def _validate_risk_management(self, risk_mgmt: dict, result: ValidationResult):
        """驗證風險管理配置"""
        # 檢查必需字段
        for field in self.REQUIRED_RISK_FIELDS:
            if field not in risk_mgmt:
                result.add_error(f"risk_management 缺少必需字段：{field}")
        
        # 驗證數值範圍
        if 'position_size' in risk_mgmt:
            ps = risk_mgmt['position_size']
            if not isinstance(ps, (int, float)) or not 0 < ps <= 1:
                result.add_error(
                    f"position_size 必須在 (0, 1] 範圍內：{ps}"
                )
        
        if 'leverage' in risk_mgmt:
            lev = risk_mgmt['leverage']
            if not isinstance(lev, int) or lev < 1:
                result.add_error(f"leverage 必須 >= 1：{lev}")
            elif lev > 20:
                result.add_warning(f"leverage 過高可能增加風險：{lev}")
        
        if 'max_trades_per_day' in risk_mgmt:
            mtpd = risk_mgmt['max_trades_per_day']
            if not isinstance(mtpd, int) or mtpd < 1:
                result.add_error(f"max_trades_per_day 必須 >= 1：{mtpd}")
        
        if 'max_consecutive_losses' in risk_mgmt:
            mcl = risk_mgmt['max_consecutive_losses']
            if not isinstance(mcl, int) or mcl < 1:
                result.add_error(f"max_consecutive_losses 必須 >= 1：{mcl}")
        
        if 'daily_loss_limit' in risk_mgmt:
            dll = risk_mgmt['daily_loss_limit']
            if not isinstance(dll, (int, float)) or not 0 < dll <= 1:
                result.add_error(
                    f"daily_loss_limit 必須在 (0, 1] 範圍內：{dll}"
                )
        
        if 'stop_loss_atr' in risk_mgmt:
            sl = risk_mgmt['stop_loss_atr']
            if not isinstance(sl, (int, float)) or sl <= 0:
                result.add_error(f"stop_loss_atr 必須 > 0：{sl}")
        
        if 'take_profit_atr' in risk_mgmt:
            tp = risk_mgmt['take_profit_atr']
            if not isinstance(tp, (int, float)) or tp <= 0:
                result.add_error(f"take_profit_atr 必須 > 0：{tp}")


class CodeValidator:
    """策略代碼驗證器"""
    
    REQUIRED_METHODS = [
        'generate_signal',
        'calculate_position_size',
        'calculate_stop_loss',
        'calculate_take_profit',
        'should_exit',
    ]
    
    def validate_code_file(self, code_path: str) -> ValidationResult:
        """驗證策略代碼文件
        
        Args:
            code_path: 代碼文件路徑
        
        Returns:
            ValidationResult: 驗證結果
        """
        result = ValidationResult()
        
        # 檢查文件存在
        path = Path(code_path)
        if not path.exists():
            result.add_error(f"代碼文件不存在：{code_path}")
            return result
        
        result.add_info(f"驗證代碼文件：{code_path}")
        
        # 讀取代碼
        try:
            with open(path, 'r', encoding='utf-8') as f:
                code = f.read()
        except Exception as e:
            result.add_error(f"讀取文件失敗：{e}")
            return result
        
        # 解析 AST
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            result.add_error(f"語法錯誤：{e}")
            return result
        
        # 查找策略類
        strategy_classes = self._find_strategy_classes(tree)
        
        if not strategy_classes:
            result.add_error("未找到繼承自 Strategy 的策略類")
            return result
        
        if len(strategy_classes) > 1:
            result.add_warning(
                f"找到多個策略類：{', '.join(strategy_classes.keys())}。"
                f"建議每個文件只包含一個策略類。"
            )
        
        # 驗證每個策略類
        for class_name, class_node in strategy_classes.items():
            result.add_info(f"驗證策略類：{class_name}")
            self._validate_strategy_class(class_node, result)
        
        # 檢查 TODO 標記
        todo_count = code.count('TODO')
        if todo_count > 0:
            result.add_warning(
                f"發現 {todo_count} 個 TODO 標記，請確保完成所有實現"
            )
        
        return result
    
    def _find_strategy_classes(self, tree: ast.AST) -> dict:
        """查找繼承自 Strategy 的類
        
        Returns:
            dict: {類名: 類節點}
        """
        strategy_classes = {}
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # 檢查是否繼承自 Strategy
                for base in node.bases:
                    if isinstance(base, ast.Name) and base.id == 'Strategy':
                        strategy_classes[node.name] = node
                        break
        
        return strategy_classes
    
    def _validate_strategy_class(self, class_node: ast.ClassDef, result: ValidationResult):
        """驗證策略類"""
        # 獲取所有方法
        methods = {}
        for node in class_node.body:
            if isinstance(node, ast.FunctionDef):
                methods[node.name] = node
        
        # 檢查必需方法
        for method_name in self.REQUIRED_METHODS:
            if method_name not in methods:
                result.add_error(f"缺少必需方法：{method_name}")
            else:
                # 檢查方法是否只有 pass 語句
                method_node = methods[method_name]
                if self._is_empty_method(method_node):
                    result.add_warning(
                        f"方法 {method_name} 只包含 pass 語句，需要實現"
                    )
        
        # 檢查 __init__ 方法
        if '__init__' in methods:
            init_node = methods['__init__']
            # 檢查是否調用了 super().__init__
            has_super_call = False
            for node in ast.walk(init_node):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Attribute):
                        if (isinstance(node.func.value, ast.Call) and
                            isinstance(node.func.value.func, ast.Name) and
                            node.func.value.func.id == 'super'):
                            has_super_call = True
                            break
            
            if not has_super_call:
                result.add_warning(
                    "__init__ 方法應該調用 super().__init__(config)"
                )
    
    def _is_empty_method(self, method_node: ast.FunctionDef) -> bool:
        """檢查方法是否為空（只有 pass 或 docstring）"""
        body = method_node.body
        
        # 過濾掉 docstring
        non_doc_body = []
        for i, node in enumerate(body):
            if i == 0 and isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
                continue  # 跳過 docstring
            non_doc_body.append(node)
        
        # 檢查是否只有 pass
        if len(non_doc_body) == 1 and isinstance(non_doc_body[0], ast.Pass):
            return True
        
        return False


def validate_strategy(
    config_path: Optional[str] = None,
    code_path: Optional[str] = None,
    config_dir: Optional[str] = None,
    verbose: bool = True
) -> bool:
    """驗證策略
    
    Args:
        config_path: 配置文件路徑
        code_path: 代碼文件路徑
        config_dir: 配置文件目錄（驗證所有配置）
        verbose: 是否顯示詳細信息
    
    Returns:
        bool: 是否通過驗證
    """
    all_valid = True
    
    # 驗證配置目錄
    if config_dir:
        config_validator = ConfigValidator()
        config_files = list(Path(config_dir).glob("*.json"))
        
        if not config_files:
            print(f"⚠️  目錄 {config_dir} 中沒有找到配置文件")
            return False
        
        print(f"\n驗證 {len(config_files)} 個配置文件...\n")
        
        for config_file in config_files:
            print(f"{'='*60}")
            result = config_validator.validate_config_file(str(config_file))
            result.print_results(verbose)
            if not result.is_valid():
                all_valid = False
        
        return all_valid
    
    # 驗證單個配置文件
    if config_path:
        print(f"\n{'='*60}")
        config_validator = ConfigValidator()
        result = config_validator.validate_config_file(config_path)
        result.print_results(verbose)
        if not result.is_valid():
            all_valid = False
    
    # 驗證代碼文件
    if code_path:
        print(f"\n{'='*60}")
        code_validator = CodeValidator()
        result = code_validator.validate_code_file(code_path)
        result.print_results(verbose)
        if not result.is_valid():
            all_valid = False
    
    return all_valid


def main():
    """主函數"""
    parser = argparse.ArgumentParser(
        description='策略驗證工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例：
  # 驗證配置文件
  python tools/validate_strategy.py --config strategies/my-strategy.json
  
  # 驗證策略代碼
  python tools/validate_strategy.py --code src/strategies/my_strategy.py
  
  # 同時驗證配置和代碼
  python tools/validate_strategy.py --config strategies/my-strategy.json --code src/strategies/my_strategy.py
  
  # 驗證整個配置目錄
  python tools/validate_strategy.py --config-dir strategies/
        '''
    )
    
    parser.add_argument(
        '--config',
        help='配置文件路徑'
    )
    
    parser.add_argument(
        '--code',
        help='代碼文件路徑'
    )
    
    parser.add_argument(
        '--config-dir',
        help='配置文件目錄（驗證所有配置）'
    )
    
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='只顯示錯誤和警告'
    )
    
    args = parser.parse_args()
    
    # 檢查參數
    if not any([args.config, args.code, args.config_dir]):
        parser.print_help()
        print("\n❌ 錯誤：必須指定 --config、--code 或 --config-dir 中的至少一個")
        sys.exit(1)
    
    # 執行驗證
    verbose = not args.quiet
    is_valid = validate_strategy(
        config_path=args.config,
        code_path=args.code,
        config_dir=args.config_dir,
        verbose=verbose
    )
    
    sys.exit(0 if is_valid else 1)


if __name__ == '__main__':
    main()
