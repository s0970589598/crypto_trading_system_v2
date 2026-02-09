"""
策略管理器 - 負責策略的生命週期管理
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime

from src.models.config import StrategyConfig
from src.models.state import StrategyState
from src.execution.strategy import Strategy


# 配置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StrategyManager:
    """策略管理器
    
    負責：
    1. 從配置文件載入策略
    2. 驗證策略配置
    3. 創建策略實例
    4. 管理策略生命週期（啟用/停用）
    5. 追蹤策略狀態
    6. 支持熱重載
    """
    
    def __init__(self, strategies_dir: str = "strategies/"):
        """初始化策略管理器
        
        Args:
            strategies_dir: 策略配置文件目錄
        """
        self.strategies_dir = Path(strategies_dir)
        self.strategies: Dict[str, Strategy] = {}
        self.strategy_states: Dict[str, StrategyState] = {}
        self.strategy_configs: Dict[str, StrategyConfig] = {}
        
        # 確保策略目錄存在
        self.strategies_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"策略管理器已初始化，策略目錄：{self.strategies_dir}")
    
    def load_strategies(self) -> List[str]:
        """從配置文件載入所有策略
        
        掃描策略目錄中的所有 JSON 文件，嘗試載入每個策略。
        如果某個策略載入失敗，記錄錯誤但繼續載入其他策略。
        
        Returns:
            List[str]: 成功載入的策略 ID 列表
        """
        loaded_ids = []
        
        # 查找所有 JSON 配置文件
        config_files = list(self.strategies_dir.glob("*.json"))
        
        if not config_files:
            logger.warning(f"策略目錄 {self.strategies_dir} 中沒有找到配置文件")
            return loaded_ids
        
        logger.info(f"找到 {len(config_files)} 個策略配置文件")
        
        for config_file in config_files:
            try:
                # 載入配置
                config = StrategyConfig.from_json(str(config_file))
                
                # 驗證配置
                is_valid, error_msg = self.validate_config(config.to_dict())
                if not is_valid:
                    logger.error(f"配置文件 {config_file.name} 驗證失敗：{error_msg}")
                    continue
                
                # 檢查 ID 唯一性
                if config.strategy_id in self.strategies:
                    logger.error(f"策略 ID 重複：{config.strategy_id}（文件：{config_file.name}）")
                    continue
                
                # 創建策略實例
                strategy = self.create_strategy(config)
                
                # 保存策略和配置
                self.strategies[config.strategy_id] = strategy
                self.strategy_configs[config.strategy_id] = config
                
                # 初始化策略狀態
                self.strategy_states[config.strategy_id] = StrategyState(
                    strategy_id=config.strategy_id,
                    enabled=config.enabled,
                )
                
                loaded_ids.append(config.strategy_id)
                logger.info(f"✅ 成功載入策略：{config.strategy_id}（{config.strategy_name}）")
                
            except FileNotFoundError as e:
                logger.error(f"配置文件不存在：{config_file} - {e}")
            except json.JSONDecodeError as e:
                logger.error(f"配置文件 {config_file.name} JSON 格式錯誤：{e}")
            except ValueError as e:
                logger.error(f"配置文件 {config_file.name} 格式錯誤：{e}")
            except Exception as e:
                logger.error(f"載入配置文件 {config_file.name} 時發生錯誤：{e}")
        
        logger.info(f"策略載入完成：成功 {len(loaded_ids)}/{len(config_files)}")
        return loaded_ids
    
    def validate_config(self, config: dict) -> Tuple[bool, str]:
        """驗證策略配置
        
        檢查配置字典是否包含所有必需字段，且值在有效範圍內。
        
        Args:
            config: 策略配置字典
        
        Returns:
            Tuple[bool, str]: (是否有效, 錯誤訊息)
        """
        # 檢查必需字段
        required_fields = [
            'strategy_id',
            'strategy_name',
            'version',
            'symbol',
            'timeframes',
            'risk_management',
        ]
        
        for field in required_fields:
            if field not in config:
                return False, f"缺少必需字段：{field}"
        
        # 驗證 strategy_id
        if not config['strategy_id']:
            return False, "strategy_id 不能為空"
        
        # 驗證 strategy_name
        if not config['strategy_name']:
            return False, "strategy_name 不能為空"
        
        # 驗證 version
        if not config['version']:
            return False, "version 不能為空"
        
        # 驗證 symbol
        if not config['symbol']:
            return False, "symbol 不能為空"
        
        # 驗證 timeframes
        if not config['timeframes'] or not isinstance(config['timeframes'], list):
            return False, "timeframes 必須是非空列表"
        
        valid_timeframes = ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d', '3d', '1w', '1M']
        for tf in config['timeframes']:
            if tf not in valid_timeframes:
                return False, f"無效的時間週期：{tf}，有效值：{valid_timeframes}"
        
        # 驗證 risk_management
        risk_mgmt = config['risk_management']
        if not isinstance(risk_mgmt, dict):
            return False, "risk_management 必須是字典"
        
        required_risk_fields = [
            'position_size',
            'leverage',
            'max_trades_per_day',
            'max_consecutive_losses',
            'daily_loss_limit',
            'stop_loss_atr',
            'take_profit_atr',
        ]
        
        for field in required_risk_fields:
            if field not in risk_mgmt:
                return False, f"risk_management 缺少必需字段：{field}"
        
        # 驗證風險管理參數範圍
        if not 0 < risk_mgmt['position_size'] <= 1:
            return False, f"position_size 必須在 (0, 1] 範圍內，當前值：{risk_mgmt['position_size']}"
        
        if risk_mgmt['leverage'] < 1:
            return False, f"leverage 必須 >= 1，當前值：{risk_mgmt['leverage']}"
        
        if risk_mgmt['max_trades_per_day'] < 1:
            return False, f"max_trades_per_day 必須 >= 1，當前值：{risk_mgmt['max_trades_per_day']}"
        
        if risk_mgmt['stop_loss_atr'] <= 0:
            return False, f"stop_loss_atr 必須 > 0，當前值：{risk_mgmt['stop_loss_atr']}"
        
        if risk_mgmt['take_profit_atr'] <= 0:
            return False, f"take_profit_atr 必須 > 0，當前值：{risk_mgmt['take_profit_atr']}"
        
        return True, ""
    
    def create_strategy(self, config: StrategyConfig) -> Strategy:
        """根據配置創建策略實例
        
        根據配置中的策略ID或參數動態載入對應的策略類。
        
        Args:
            config: 策略配置對象
        
        Returns:
            Strategy: 策略實例
        
        Raises:
            NotImplementedError: 如果策略類型不支持
        """
        # 根據策略ID或配置推斷策略類型
        strategy_id = config.strategy_id.lower()
        
        # 嘗試從策略ID推斷策略類型
        if 'multi-timeframe' in strategy_id or 'multi_timeframe' in strategy_id:
            from src.strategies.multi_timeframe_strategy import MultiTimeframeStrategy
            return MultiTimeframeStrategy(config)
        elif 'breakout' in strategy_id:
            from src.strategies.breakout_strategy import BreakoutStrategy
            return BreakoutStrategy(config)
        elif 'mean-reversion' in strategy_id or 'mean_reversion' in strategy_id:
            from src.strategies.mean_reversion_strategy import MeanReversionStrategy
            return MeanReversionStrategy(config)
        
        # 如果配置中有 strategy_type 參數，使用它
        strategy_type = config.parameters.get('strategy_type', '')
        if strategy_type:
            if strategy_type == 'MultiTimeframeStrategy':
                from src.strategies.multi_timeframe_strategy import MultiTimeframeStrategy
                return MultiTimeframeStrategy(config)
            elif strategy_type == 'BreakoutStrategy':
                from src.strategies.breakout_strategy import BreakoutStrategy
                return BreakoutStrategy(config)
            elif strategy_type == 'MeanReversionStrategy':
                from src.strategies.mean_reversion_strategy import MeanReversionStrategy
                return MeanReversionStrategy(config)
        
        # 如果無法推斷，拋出錯誤
        raise NotImplementedError(
            f"無法為策略 {config.strategy_id} 推斷策略類型。"
            f"請在配置中添加 'strategy_type' 參數，或確保策略ID包含策略類型關鍵字。"
            f"支持的策略類型：MultiTimeframeStrategy, BreakoutStrategy, MeanReversionStrategy"
        )
    
    def enable_strategy(self, strategy_id: str) -> bool:
        """啟用策略
        
        Args:
            strategy_id: 策略 ID
        
        Returns:
            bool: 是否成功
        """
        if strategy_id not in self.strategy_states:
            logger.error(f"策略不存在：{strategy_id}")
            return False
        
        self.strategy_states[strategy_id].enabled = True
        
        # 同步更新配置
        if strategy_id in self.strategy_configs:
            self.strategy_configs[strategy_id].enabled = True
        
        logger.info(f"策略已啟用：{strategy_id}")
        return True
    
    def disable_strategy(self, strategy_id: str) -> bool:
        """停用策略
        
        Args:
            strategy_id: 策略 ID
        
        Returns:
            bool: 是否成功
        """
        if strategy_id not in self.strategy_states:
            logger.error(f"策略不存在：{strategy_id}")
            return False
        
        self.strategy_states[strategy_id].enabled = False
        
        # 同步更新配置
        if strategy_id in self.strategy_configs:
            self.strategy_configs[strategy_id].enabled = False
        
        logger.info(f"策略已停用：{strategy_id}")
        return True
    
    def get_strategy_state(self, strategy_id: str) -> Optional[StrategyState]:
        """獲取策略狀態
        
        Args:
            strategy_id: 策略 ID
        
        Returns:
            StrategyState: 策略狀態對象，如果策略不存在則返回 None
        """
        return self.strategy_states.get(strategy_id)
    
    def get_strategy(self, strategy_id: str) -> Optional[Strategy]:
        """獲取策略實例
        
        Args:
            strategy_id: 策略 ID
        
        Returns:
            Strategy: 策略實例，如果策略不存在則返回 None
        """
        return self.strategies.get(strategy_id)
    
    def get_all_strategy_ids(self) -> List[str]:
        """獲取所有策略 ID
        
        Returns:
            List[str]: 策略 ID 列表
        """
        return list(self.strategies.keys())
    
    def get_enabled_strategy_ids(self) -> List[str]:
        """獲取所有啟用的策略 ID
        
        Returns:
            List[str]: 啟用的策略 ID 列表
        """
        return [
            strategy_id
            for strategy_id, state in self.strategy_states.items()
            if state.enabled
        ]
    
    def reload_strategy(self, strategy_id: str) -> bool:
        """熱重載策略配置
        
        重新從配置文件載入策略，更新策略實例和狀態。
        注意：這會重置策略的運行狀態。
        
        Args:
            strategy_id: 策略 ID
        
        Returns:
            bool: 是否成功
        """
        if strategy_id not in self.strategies:
            logger.error(f"策略不存在：{strategy_id}")
            return False
        
        try:
            # 查找配置文件
            config_files = list(self.strategies_dir.glob("*.json"))
            target_file = None
            
            for config_file in config_files:
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if data.get('strategy_id') == strategy_id:
                            target_file = config_file
                            break
                except:
                    continue
            
            if not target_file:
                logger.error(f"找不到策略 {strategy_id} 的配置文件")
                return False
            
            # 重新載入配置
            config = StrategyConfig.from_json(str(target_file))
            
            # 驗證配置
            is_valid, error_msg = self.validate_config(config.to_dict())
            if not is_valid:
                logger.error(f"配置驗證失敗：{error_msg}")
                return False
            
            # 重新創建策略實例
            strategy = self.create_strategy(config)
            
            # 更新策略和配置
            self.strategies[strategy_id] = strategy
            self.strategy_configs[strategy_id] = config
            
            # 保留現有狀態，但更新 enabled 狀態
            if strategy_id in self.strategy_states:
                self.strategy_states[strategy_id].enabled = config.enabled
            else:
                self.strategy_states[strategy_id] = StrategyState(
                    strategy_id=strategy_id,
                    enabled=config.enabled,
                )
            
            logger.info(f"✅ 策略已重載：{strategy_id}")
            return True
            
        except Exception as e:
            logger.error(f"重載策略 {strategy_id} 時發生錯誤：{e}")
            return False
    
    def reset_daily_stats(self) -> None:
        """重置所有策略的每日統計
        
        應該在每天開始時調用。
        """
        for state in self.strategy_states.values():
            state.reset_daily_stats()
        
        logger.info("所有策略的每日統計已重置")
    
    def get_summary(self) -> Dict[str, any]:
        """獲取策略管理器摘要
        
        Returns:
            Dict: 摘要信息
        """
        total_strategies = len(self.strategies)
        enabled_strategies = len(self.get_enabled_strategy_ids())
        
        return {
            'total_strategies': total_strategies,
            'enabled_strategies': enabled_strategies,
            'disabled_strategies': total_strategies - enabled_strategies,
            'strategies': {
                strategy_id: {
                    'name': self.strategy_configs[strategy_id].strategy_name if strategy_id in self.strategy_configs else 'Unknown',
                    'enabled': state.enabled,
                    'trades_today': state.trades_today,
                    'pnl_today': state.pnl_today,
                    'total_trades': state.total_trades,
                    'total_pnl': state.total_pnl,
                }
                for strategy_id, state in self.strategy_states.items()
            }
        }
