#!/usr/bin/env python3
"""
策略版本管理工具

支持策略版本號管理和變更歷史記錄。

使用方法：
    # 查看策略版本
    python tools/version_strategy.py --config strategies/my-strategy.json --show
    
    # 升級版本（補丁版本）
    python tools/version_strategy.py --config strategies/my-strategy.json --bump patch
    
    # 升級版本（次版本）
    python tools/version_strategy.py --config strategies/my-strategy.json --bump minor
    
    # 升級版本（主版本）
    python tools/version_strategy.py --config strategies/my-strategy.json --bump major
    
    # 記錄變更
    python tools/version_strategy.py --config strategies/my-strategy.json --bump patch --message "修復止損計算錯誤"
    
    # 查看變更歷史
    python tools/version_strategy.py --config strategies/my-strategy.json --history
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple


class VersionManager:
    """版本管理器"""
    
    def __init__(self, config_path: str):
        """初始化版本管理器
        
        Args:
            config_path: 配置文件路徑
        """
        self.config_path = Path(config_path)
        self.history_path = self.config_path.parent / '.version_history' / f"{self.config_path.stem}.json"
        
        # 確保歷史目錄存在
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
    
    def load_config(self) -> dict:
        """載入配置文件"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"配置文件不存在：{self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def save_config(self, config: dict):
        """保存配置文件"""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    
    def load_history(self) -> list:
        """載入變更歷史"""
        if not self.history_path.exists():
            return []
        
        with open(self.history_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def save_history(self, history: list):
        """保存變更歷史"""
        with open(self.history_path, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    
    def parse_version(self, version: str) -> Tuple[int, int, int]:
        """解析版本號
        
        Args:
            version: 版本字符串（如 "1.2.3"）
        
        Returns:
            Tuple[int, int, int]: (主版本, 次版本, 補丁版本)
        
        Raises:
            ValueError: 版本格式錯誤
        """
        parts = version.split('.')
        if len(parts) != 3:
            raise ValueError(f"版本格式錯誤：{version}。必須是 X.Y.Z 格式")
        
        try:
            major = int(parts[0])
            minor = int(parts[1])
            patch = int(parts[2])
            return major, minor, patch
        except ValueError:
            raise ValueError(f"版本格式錯誤：{version}。版本號必須是整數")
    
    def format_version(self, major: int, minor: int, patch: int) -> str:
        """格式化版本號
        
        Args:
            major: 主版本
            minor: 次版本
            patch: 補丁版本
        
        Returns:
            str: 版本字符串
        """
        return f"{major}.{minor}.{patch}"
    
    def bump_version(self, bump_type: str, message: Optional[str] = None) -> Tuple[str, str]:
        """升級版本
        
        Args:
            bump_type: 升級類型（'major', 'minor', 'patch'）
            message: 變更訊息
        
        Returns:
            Tuple[str, str]: (舊版本, 新版本)
        """
        # 載入配置
        config = self.load_config()
        old_version = config.get('version', '0.0.0')
        
        # 解析版本
        major, minor, patch = self.parse_version(old_version)
        
        # 升級版本
        if bump_type == 'major':
            major += 1
            minor = 0
            patch = 0
        elif bump_type == 'minor':
            minor += 1
            patch = 0
        elif bump_type == 'patch':
            patch += 1
        else:
            raise ValueError(f"無效的升級類型：{bump_type}。有效值：major, minor, patch")
        
        new_version = self.format_version(major, minor, patch)
        
        # 更新配置
        config['version'] = new_version
        self.save_config(config)
        
        # 記錄變更歷史
        self._record_change(old_version, new_version, bump_type, message)
        
        return old_version, new_version
    
    def _record_change(
        self,
        old_version: str,
        new_version: str,
        bump_type: str,
        message: Optional[str]
    ):
        """記錄變更歷史"""
        history = self.load_history()
        
        change_record = {
            'timestamp': datetime.now().isoformat(),
            'old_version': old_version,
            'new_version': new_version,
            'bump_type': bump_type,
            'message': message or f"升級{bump_type}版本",
        }
        
        history.append(change_record)
        self.save_history(history)
    
    def show_version(self) -> str:
        """顯示當前版本"""
        config = self.load_config()
        return config.get('version', '未知')
    
    def show_history(self, limit: Optional[int] = None) -> list:
        """顯示變更歷史
        
        Args:
            limit: 限制顯示數量（最新的 N 條）
        
        Returns:
            list: 變更記錄列表
        """
        history = self.load_history()
        
        if limit:
            history = history[-limit:]
        
        return history
    
    def show_info(self) -> dict:
        """顯示策略信息"""
        config = self.load_config()
        history = self.load_history()
        
        return {
            'strategy_id': config.get('strategy_id', '未知'),
            'strategy_name': config.get('strategy_name', '未知'),
            'current_version': config.get('version', '未知'),
            'total_changes': len(history),
            'last_change': history[-1] if history else None,
        }


def print_version_info(info: dict):
    """打印版本信息"""
    print(f"\n策略信息：")
    print(f"  ID：{info['strategy_id']}")
    print(f"  名稱：{info['strategy_name']}")
    print(f"  當前版本：{info['current_version']}")
    print(f"  變更次數：{info['total_changes']}")
    
    if info['last_change']:
        last = info['last_change']
        print(f"\n最後變更：")
        print(f"  時間：{last['timestamp']}")
        print(f"  版本：{last['old_version']} → {last['new_version']}")
        print(f"  類型：{last['bump_type']}")
        print(f"  訊息：{last['message']}")


def print_history(history: list):
    """打印變更歷史"""
    if not history:
        print("\n暫無變更歷史")
        return
    
    print(f"\n變更歷史（共 {len(history)} 條）：\n")
    
    for i, record in enumerate(reversed(history), 1):
        print(f"{i}. {record['timestamp']}")
        print(f"   版本：{record['old_version']} → {record['new_version']}")
        print(f"   類型：{record['bump_type']}")
        print(f"   訊息：{record['message']}")
        print()


def main():
    """主函數"""
    parser = argparse.ArgumentParser(
        description='策略版本管理工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
版本號格式：
  使用語義化版本（Semantic Versioning）：MAJOR.MINOR.PATCH
  
  - MAJOR（主版本）：不兼容的 API 變更
  - MINOR（次版本）：向後兼容的功能新增
  - PATCH（補丁版本）：向後兼容的問題修正

示例：
  # 查看策略版本
  python tools/version_strategy.py --config strategies/my-strategy.json --show
  
  # 升級補丁版本（1.0.0 → 1.0.1）
  python tools/version_strategy.py --config strategies/my-strategy.json --bump patch --message "修復止損計算錯誤"
  
  # 升級次版本（1.0.1 → 1.1.0）
  python tools/version_strategy.py --config strategies/my-strategy.json --bump minor --message "新增追蹤止損功能"
  
  # 升級主版本（1.1.0 → 2.0.0）
  python tools/version_strategy.py --config strategies/my-strategy.json --bump major --message "重構信號生成邏輯"
  
  # 查看變更歷史
  python tools/version_strategy.py --config strategies/my-strategy.json --history
  
  # 查看最近 5 條變更
  python tools/version_strategy.py --config strategies/my-strategy.json --history --limit 5
        '''
    )
    
    parser.add_argument(
        '--config',
        required=True,
        help='配置文件路徑'
    )
    
    parser.add_argument(
        '--show',
        action='store_true',
        help='顯示當前版本信息'
    )
    
    parser.add_argument(
        '--bump',
        choices=['major', 'minor', 'patch'],
        help='升級版本類型'
    )
    
    parser.add_argument(
        '--message',
        help='變更訊息'
    )
    
    parser.add_argument(
        '--history',
        action='store_true',
        help='顯示變更歷史'
    )
    
    parser.add_argument(
        '--limit',
        type=int,
        help='限制歷史記錄顯示數量'
    )
    
    args = parser.parse_args()
    
    try:
        manager = VersionManager(args.config)
        
        # 升級版本
        if args.bump:
            old_version, new_version = manager.bump_version(args.bump, args.message)
            print(f"\n✅ 版本已升級：{old_version} → {new_version}")
            
            if args.message:
                print(f"變更訊息：{args.message}")
            
            # 顯示更新後的信息
            info = manager.show_info()
            print_version_info(info)
        
        # 顯示版本信息
        elif args.show:
            info = manager.show_info()
            print_version_info(info)
        
        # 顯示變更歷史
        elif args.history:
            history = manager.show_history(args.limit)
            print_history(history)
        
        else:
            # 默認顯示版本信息
            info = manager.show_info()
            print_version_info(info)
        
        sys.exit(0)
        
    except FileNotFoundError as e:
        print(f"\n❌ 錯誤：{e}")
        sys.exit(1)
    except ValueError as e:
        print(f"\n❌ 錯誤：{e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 發生錯誤：{e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
