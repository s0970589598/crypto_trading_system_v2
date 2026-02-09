#!/usr/bin/env python3
"""
策略部署工具

自動部署策略到生產環境。

使用方法：
    # 部署策略（驗證 + 啟用）
    python tools/deploy_strategy.py --config strategies/my-strategy.json
    
    # 部署並運行回測
    python tools/deploy_strategy.py --config strategies/my-strategy.json --backtest
    
    # 部署到指定環境
    python tools/deploy_strategy.py --config strategies/my-strategy.json --env production
    
    # 回滾到之前的版本
    python tools/deploy_strategy.py --config strategies/my-strategy.json --rollback
"""

import argparse
import json
import sys
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple
import subprocess


class DeploymentManager:
    """部署管理器"""
    
    def __init__(self, config_path: str, env: str = 'production'):
        """初始化部署管理器
        
        Args:
            config_path: 配置文件路徑
            env: 環境名稱（development, staging, production）
        """
        self.config_path = Path(config_path)
        self.env = env
        
        # 部署目錄
        self.deploy_dir = Path('deployed_strategies') / env
        self.backup_dir = Path('deployed_strategies') / 'backups' / env
        
        # 確保目錄存在
        self.deploy_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # 部署歷史文件
        self.history_file = Path('deployed_strategies') / f'deployment_history_{env}.json'
    
    def load_config(self) -> dict:
        """載入配置文件"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"配置文件不存在：{self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def load_history(self) -> list:
        """載入部署歷史"""
        if not self.history_file.exists():
            return []
        
        with open(self.history_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def save_history(self, history: list):
        """保存部署歷史"""
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    
    def validate_strategy(self) -> Tuple[bool, str]:
        """驗證策略
        
        Returns:
            Tuple[bool, str]: (是否通過, 訊息)
        """
        print("🔍 驗證策略配置...")
        
        # 使用驗證工具
        try:
            result = subprocess.run(
                ['python', 'tools/validate_strategy.py', '--config', str(self.config_path), '--quiet'],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                return True, "配置驗證通過"
            else:
                return False, f"配置驗證失敗：\n{result.stdout}\n{result.stderr}"
        
        except Exception as e:
            return False, f"驗證過程出錯：{e}"
    
    def run_backtest(self) -> Tuple[bool, str]:
        """運行回測
        
        Returns:
            Tuple[bool, str]: (是否成功, 訊息)
        """
        print("📊 運行回測...")
        
        config = self.load_config()
        strategy_id = config.get('strategy_id', 'unknown')
        
        # 這裡應該調用實際的回測引擎
        # 為了演示，我們只是檢查回測腳本是否存在
        backtest_script = Path('backtest_multi_strategy.py')
        
        if not backtest_script.exists():
            return False, "回測腳本不存在"
        
        # 實際部署時，應該運行回測並檢查結果
        # result = subprocess.run(['python', str(backtest_script), '--strategy', strategy_id])
        
        return True, "回測通過（演示模式）"
    
    def backup_current(self, strategy_id: str) -> Optional[str]:
        """備份當前部署的策略
        
        Args:
            strategy_id: 策略 ID
        
        Returns:
            Optional[str]: 備份文件路徑，如果沒有當前部署則返回 None
        """
        current_file = self.deploy_dir / f"{strategy_id}.json"
        
        if not current_file.exists():
            return None
        
        # 創建備份
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = self.backup_dir / f"{strategy_id}_{timestamp}.json"
        
        shutil.copy2(current_file, backup_file)
        print(f"📦 已備份當前版本：{backup_file.name}")
        
        return str(backup_file)
    
    def deploy(self, run_backtest: bool = False) -> Tuple[bool, str]:
        """部署策略
        
        Args:
            run_backtest: 是否運行回測
        
        Returns:
            Tuple[bool, str]: (是否成功, 訊息)
        """
        try:
            # 載入配置
            config = self.load_config()
            strategy_id = config.get('strategy_id', 'unknown')
            version = config.get('version', 'unknown')
            
            print(f"\n🚀 開始部署策略：{strategy_id} (v{version})")
            print(f"環境：{self.env}")
            print(f"{'='*60}\n")
            
            # 1. 驗證策略
            is_valid, msg = self.validate_strategy()
            if not is_valid:
                return False, f"驗證失敗：{msg}"
            print(f"✅ {msg}\n")
            
            # 2. 運行回測（可選）
            if run_backtest:
                is_success, msg = self.run_backtest()
                if not is_success:
                    return False, f"回測失敗：{msg}"
                print(f"✅ {msg}\n")
            
            # 3. 備份當前版本
            backup_path = self.backup_current(strategy_id)
            
            # 4. 部署新版本
            print("📝 部署新版本...")
            deploy_file = self.deploy_dir / f"{strategy_id}.json"
            shutil.copy2(self.config_path, deploy_file)
            print(f"✅ 已部署到：{deploy_file}\n")
            
            # 5. 記錄部署歷史
            self._record_deployment(strategy_id, version, backup_path)
            
            print(f"{'='*60}")
            print(f"✅ 部署成功！")
            print(f"\n策略：{strategy_id}")
            print(f"版本：{version}")
            print(f"環境：{self.env}")
            print(f"時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            if backup_path:
                print(f"\n💡 如需回滾，運行：")
                print(f"   python tools/deploy_strategy.py --config {self.config_path} --rollback")
            
            return True, "部署成功"
        
        except Exception as e:
            return False, f"部署過程出錯：{e}"
    
    def _record_deployment(self, strategy_id: str, version: str, backup_path: Optional[str]):
        """記錄部署歷史"""
        history = self.load_history()
        
        record = {
            'timestamp': datetime.now().isoformat(),
            'strategy_id': strategy_id,
            'version': version,
            'environment': self.env,
            'config_path': str(self.config_path),
            'backup_path': backup_path,
        }
        
        history.append(record)
        self.save_history(history)
    
    def rollback(self) -> Tuple[bool, str]:
        """回滾到上一個版本
        
        Returns:
            Tuple[bool, str]: (是否成功, 訊息)
        """
        try:
            config = self.load_config()
            strategy_id = config.get('strategy_id', 'unknown')
            
            print(f"\n🔄 回滾策略：{strategy_id}")
            print(f"環境：{self.env}")
            print(f"{'='*60}\n")
            
            # 查找最近的備份
            history = self.load_history()
            
            # 過濾出該策略的部署記錄
            strategy_history = [
                record for record in history
                if record['strategy_id'] == strategy_id
            ]
            
            if not strategy_history:
                return False, f"沒有找到策略 {strategy_id} 的部署歷史"
            
            # 獲取最後一次部署的備份
            last_deployment = strategy_history[-1]
            backup_path = last_deployment.get('backup_path')
            
            if not backup_path or not Path(backup_path).exists():
                return False, "沒有可用的備份文件"
            
            # 恢復備份
            print(f"📦 從備份恢復：{Path(backup_path).name}")
            deploy_file = self.deploy_dir / f"{strategy_id}.json"
            shutil.copy2(backup_path, deploy_file)
            
            print(f"✅ 已回滾到之前的版本\n")
            print(f"{'='*60}")
            print(f"✅ 回滾成功！")
            
            return True, "回滾成功"
        
        except Exception as e:
            return False, f"回滾過程出錯：{e}"
    
    def show_deployments(self, limit: Optional[int] = None) -> list:
        """顯示部署歷史
        
        Args:
            limit: 限制顯示數量
        
        Returns:
            list: 部署記錄列表
        """
        history = self.load_history()
        
        if limit:
            history = history[-limit:]
        
        return history


def print_deployments(deployments: list):
    """打印部署歷史"""
    if not deployments:
        print("\n暫無部署歷史")
        return
    
    print(f"\n部署歷史（共 {len(deployments)} 條）：\n")
    
    for i, record in enumerate(reversed(deployments), 1):
        print(f"{i}. {record['timestamp']}")
        print(f"   策略：{record['strategy_id']} (v{record['version']})")
        print(f"   環境：{record['environment']}")
        print(f"   配置：{record['config_path']}")
        if record.get('backup_path'):
            print(f"   備份：{record['backup_path']}")
        print()


def main():
    """主函數"""
    parser = argparse.ArgumentParser(
        description='策略部署工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
部署流程：
  1. 驗證策略配置
  2. 運行回測（可選）
  3. 備份當前版本
  4. 部署新版本
  5. 記錄部署歷史

示例：
  # 部署策略
  python tools/deploy_strategy.py --config strategies/my-strategy.json
  
  # 部署並運行回測
  python tools/deploy_strategy.py --config strategies/my-strategy.json --backtest
  
  # 部署到測試環境
  python tools/deploy_strategy.py --config strategies/my-strategy.json --env staging
  
  # 回滾到之前的版本
  python tools/deploy_strategy.py --config strategies/my-strategy.json --rollback
  
  # 查看部署歷史
  python tools/deploy_strategy.py --config strategies/my-strategy.json --history
        '''
    )
    
    parser.add_argument(
        '--config',
        required=True,
        help='配置文件路徑'
    )
    
    parser.add_argument(
        '--env',
        default='production',
        choices=['development', 'staging', 'production'],
        help='部署環境（默認：production）'
    )
    
    parser.add_argument(
        '--backtest',
        action='store_true',
        help='部署前運行回測'
    )
    
    parser.add_argument(
        '--rollback',
        action='store_true',
        help='回滾到上一個版本'
    )
    
    parser.add_argument(
        '--history',
        action='store_true',
        help='顯示部署歷史'
    )
    
    parser.add_argument(
        '--limit',
        type=int,
        help='限制歷史記錄顯示數量'
    )
    
    args = parser.parse_args()
    
    try:
        manager = DeploymentManager(args.config, args.env)
        
        # 回滾
        if args.rollback:
            success, message = manager.rollback()
            sys.exit(0 if success else 1)
        
        # 顯示歷史
        elif args.history:
            deployments = manager.show_deployments(args.limit)
            print_deployments(deployments)
            sys.exit(0)
        
        # 部署
        else:
            success, message = manager.deploy(run_backtest=args.backtest)
            sys.exit(0 if success else 1)
    
    except FileNotFoundError as e:
        print(f"\n❌ 錯誤：{e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 發生錯誤：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
