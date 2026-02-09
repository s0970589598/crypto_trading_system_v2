"""
系統配置管理器
負責載入、驗證和管理系統配置
"""

import os
import yaml
from dataclasses import dataclass, field
from typing import Dict, List, Any, Tuple, Optional
from pathlib import Path
import logging
from string import Template


logger = logging.getLogger(__name__)


@dataclass
class SystemInfo:
    """系統信息配置"""
    name: str = "Multi-Strategy Trading System"
    version: str = "1.0.0"
    environment: str = "development"


@dataclass
class DataConfig:
    """數據配置"""
    primary_source: str = "binance"
    backup_sources: List[str] = field(default_factory=lambda: ["bingx"])
    cache_ttl: int = 300
    data_dir: str = "data"
    market_data_dir: str = "data/market_data"
    trade_history_dir: str = "data/trade_history"
    backtest_results_dir: str = "data/backtest_results"


@dataclass
class RiskConfig:
    """風險配置"""
    global_max_drawdown: float = 0.20
    daily_loss_limit: float = 0.10
    global_max_position: float = 0.80
    default_max_position_per_strategy: float = 0.30
    default_max_trades_per_day: int = 5
    default_max_consecutive_losses: int = 3
    check_interval: int = 60
    halt_on_global_drawdown: bool = True
    halt_on_daily_loss: bool = True


@dataclass
class TelegramConfig:
    """Telegram 通知配置"""
    enabled: bool = False
    bot_token: str = ""
    chat_id: str = ""


@dataclass
class EmailConfig:
    """Email 通知配置"""
    enabled: bool = False
    smtp_server: str = ""
    smtp_port: int = 587
    sender_email: str = ""
    sender_password: str = ""
    recipient_emails: List[str] = field(default_factory=list)


@dataclass
class WebhookConfig:
    """Webhook 通知配置"""
    enabled: bool = False
    url: str = ""


@dataclass
class NotificationsConfig:
    """通知配置"""
    telegram: TelegramConfig = field(default_factory=TelegramConfig)
    email: EmailConfig = field(default_factory=EmailConfig)
    webhook: WebhookConfig = field(default_factory=WebhookConfig)


@dataclass
class BacktestConfig:
    """回測配置"""
    commission: float = 0.0005
    slippage: float = 0.0001
    initial_capital: float = 1000.0
    risk_free_rate: float = 0.02


@dataclass
class LoggingConfig:
    """日誌配置"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file: str = "logs/system.log"
    max_bytes: int = 10485760
    backup_count: int = 5


@dataclass
class StrategiesConfig:
    """策略配置"""
    config_dir: str = "strategies"
    auto_load: bool = True
    hot_reload: bool = True
    reload_interval: int = 300


@dataclass
class PerformanceConfig:
    """性能監控配置"""
    monitor_interval: int = 60
    degradation_threshold: float = 0.20
    anomaly_detection: bool = True


@dataclass
class OptimizationConfig:
    """優化配置"""
    default_method: str = "grid"
    train_test_split: float = 0.7
    max_iterations: int = 1000
    n_jobs: int = -1


@dataclass
class SystemConfig:
    """系統配置"""
    system: SystemInfo = field(default_factory=SystemInfo)
    data: DataConfig = field(default_factory=DataConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    notifications: NotificationsConfig = field(default_factory=NotificationsConfig)
    backtest: BacktestConfig = field(default_factory=BacktestConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    strategies: StrategiesConfig = field(default_factory=StrategiesConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    optimization: OptimizationConfig = field(default_factory=OptimizationConfig)
    
    def validate(self) -> Tuple[bool, str]:
        """驗證配置有效性
        
        Returns:
            Tuple[bool, str]: (是否有效, 錯誤訊息)
        """
        # 驗證風險配置
        if not 0 < self.risk.global_max_drawdown <= 1:
            return False, f"global_max_drawdown 必須在 (0, 1] 範圍內，當前值：{self.risk.global_max_drawdown}"
        
        if not 0 < self.risk.daily_loss_limit <= 1:
            return False, f"daily_loss_limit 必須在 (0, 1] 範圍內，當前值：{self.risk.daily_loss_limit}"
        
        if not 0 < self.risk.global_max_position <= 1:
            return False, f"global_max_position 必須在 (0, 1] 範圍內，當前值：{self.risk.global_max_position}"
        
        if not 0 < self.risk.default_max_position_per_strategy <= 1:
            return False, f"default_max_position_per_strategy 必須在 (0, 1] 範圍內，當前值：{self.risk.default_max_position_per_strategy}"
        
        # 驗證回測配置
        if self.backtest.commission < 0:
            return False, f"commission 必須 >= 0，當前值：{self.backtest.commission}"
        
        if self.backtest.slippage < 0:
            return False, f"slippage 必須 >= 0，當前值：{self.backtest.slippage}"
        
        if self.backtest.initial_capital <= 0:
            return False, f"initial_capital 必須 > 0，當前值：{self.backtest.initial_capital}"
        
        # 驗證優化配置
        if not 0 < self.optimization.train_test_split < 1:
            return False, f"train_test_split 必須在 (0, 1) 範圍內，當前值：{self.optimization.train_test_split}"
        
        if self.optimization.default_method not in ['grid', 'random', 'bayesian']:
            return False, f"default_method 必須是 'grid', 'random' 或 'bayesian'，當前值：{self.optimization.default_method}"
        
        # 驗證日誌配置
        valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.logging.level not in valid_log_levels:
            return False, f"logging.level 必須是 {valid_log_levels} 之一，當前值：{self.logging.level}"
        
        return True, ""


class ConfigManager:
    """配置管理器
    
    負責載入、驗證和管理系統配置
    支持配置優先級：環境變數 > 配置文件 > 默認值
    """
    
    def __init__(self, config_path: str = "system_config.yaml"):
        """初始化配置管理器
        
        Args:
            config_path: 配置文件路徑
        """
        self.config_path = config_path
        self.config: Optional[SystemConfig] = None
        self._watchers: List[callable] = []
    
    def load_config(self) -> SystemConfig:
        """載入配置
        
        優先級：環境變數 > 配置文件 > 默認值
        
        Returns:
            SystemConfig: 系統配置對象
            
        Raises:
            FileNotFoundError: 配置文件不存在
            yaml.YAMLError: YAML 格式錯誤
            ValueError: 配置驗證失敗
        """
        # 先使用默認值創建配置
        config = SystemConfig()
        
        # 如果配置文件存在，從文件載入
        if Path(self.config_path).exists():
            with open(self.config_path, 'r', encoding='utf-8') as f:
                yaml_data = yaml.safe_load(f)
            
            if yaml_data:
                # 替換環境變數
                yaml_data = self._substitute_env_vars(yaml_data)
                
                # 解析配置
                config = self._parse_config(yaml_data)
        else:
            logger.warning(f"配置文件不存在：{self.config_path}，使用默認配置")
        
        # 從環境變數覆蓋配置
        config = self._override_from_env(config)
        
        # 驗證配置
        valid, error_msg = config.validate()
        if not valid:
            raise ValueError(f"配置驗證失敗：{error_msg}")
        
        self.config = config
        logger.info(f"配置載入成功：{self.config_path}")
        
        return config
    
    def _substitute_env_vars(self, data: Any) -> Any:
        """替換配置中的環境變數
        
        支持 ${VAR_NAME} 格式的環境變數引用
        
        Args:
            data: 配置數據
            
        Returns:
            Any: 替換後的配置數據
        """
        if isinstance(data, dict):
            return {k: self._substitute_env_vars(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._substitute_env_vars(item) for item in data]
        elif isinstance(data, str):
            # 使用 Template 替換環境變數
            try:
                template = Template(data)
                return template.safe_substitute(os.environ)
            except Exception as e:
                logger.warning(f"環境變數替換失敗：{data}, 錯誤：{e}")
                return data
        else:
            return data
    
    def _parse_config(self, yaml_data: Dict[str, Any]) -> SystemConfig:
        """解析 YAML 配置數據
        
        Args:
            yaml_data: YAML 配置數據
            
        Returns:
            SystemConfig: 系統配置對象
        """
        # 解析系統信息
        system_data = yaml_data.get('system', {})
        system = SystemInfo(
            name=system_data.get('name', "Multi-Strategy Trading System"),
            version=system_data.get('version', "1.0.0"),
            environment=system_data.get('environment', "development"),
        )
        
        # 解析數據配置
        data_config_data = yaml_data.get('data', {})
        data_config = DataConfig(
            primary_source=data_config_data.get('primary_source', "binance"),
            backup_sources=data_config_data.get('backup_sources', ["bingx"]),
            cache_ttl=data_config_data.get('cache_ttl', 300),
            data_dir=data_config_data.get('data_dir', "data"),
            market_data_dir=data_config_data.get('market_data_dir', "data/market_data"),
            trade_history_dir=data_config_data.get('trade_history_dir', "data/trade_history"),
            backtest_results_dir=data_config_data.get('backtest_results_dir', "data/backtest_results"),
        )
        
        # 解析風險配置
        risk_data = yaml_data.get('risk', {})
        risk = RiskConfig(
            global_max_drawdown=risk_data.get('global_max_drawdown', 0.20),
            daily_loss_limit=risk_data.get('daily_loss_limit', 0.10),
            global_max_position=risk_data.get('global_max_position', 0.80),
            default_max_position_per_strategy=risk_data.get('default_max_position_per_strategy', 0.30),
            default_max_trades_per_day=risk_data.get('default_max_trades_per_day', 5),
            default_max_consecutive_losses=risk_data.get('default_max_consecutive_losses', 3),
            check_interval=risk_data.get('check_interval', 60),
            halt_on_global_drawdown=risk_data.get('halt_on_global_drawdown', True),
            halt_on_daily_loss=risk_data.get('halt_on_daily_loss', True),
        )
        
        # 解析通知配置
        notif_data = yaml_data.get('notifications', {})
        
        telegram_data = notif_data.get('telegram', {})
        telegram = TelegramConfig(
            enabled=telegram_data.get('enabled', False),
            bot_token=telegram_data.get('bot_token', ""),
            chat_id=telegram_data.get('chat_id', ""),
        )
        
        email_data = notif_data.get('email', {})
        email = EmailConfig(
            enabled=email_data.get('enabled', False),
            smtp_server=email_data.get('smtp_server', ""),
            smtp_port=email_data.get('smtp_port', 587),
            sender_email=email_data.get('sender_email', ""),
            sender_password=email_data.get('sender_password', ""),
            recipient_emails=email_data.get('recipient_emails', []),
        )
        
        webhook_data = notif_data.get('webhook', {})
        webhook = WebhookConfig(
            enabled=webhook_data.get('enabled', False),
            url=webhook_data.get('url', ""),
        )
        
        notifications = NotificationsConfig(
            telegram=telegram,
            email=email,
            webhook=webhook,
        )
        
        # 解析回測配置
        backtest_data = yaml_data.get('backtest', {})
        backtest = BacktestConfig(
            commission=backtest_data.get('commission', 0.0005),
            slippage=backtest_data.get('slippage', 0.0001),
            initial_capital=backtest_data.get('initial_capital', 1000.0),
            risk_free_rate=backtest_data.get('risk_free_rate', 0.02),
        )
        
        # 解析日誌配置
        logging_data = yaml_data.get('logging', {})
        logging_config = LoggingConfig(
            level=logging_data.get('level', "INFO"),
            format=logging_data.get('format', "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
            file=logging_data.get('file', "logs/system.log"),
            max_bytes=logging_data.get('max_bytes', 10485760),
            backup_count=logging_data.get('backup_count', 5),
        )
        
        # 解析策略配置
        strategies_data = yaml_data.get('strategies', {})
        strategies = StrategiesConfig(
            config_dir=strategies_data.get('config_dir', "strategies"),
            auto_load=strategies_data.get('auto_load', True),
            hot_reload=strategies_data.get('hot_reload', True),
            reload_interval=strategies_data.get('reload_interval', 300),
        )
        
        # 解析性能配置
        performance_data = yaml_data.get('performance', {})
        performance = PerformanceConfig(
            monitor_interval=performance_data.get('monitor_interval', 60),
            degradation_threshold=performance_data.get('degradation_threshold', 0.20),
            anomaly_detection=performance_data.get('anomaly_detection', True),
        )
        
        # 解析優化配置
        optimization_data = yaml_data.get('optimization', {})
        optimization = OptimizationConfig(
            default_method=optimization_data.get('default_method', "grid"),
            train_test_split=optimization_data.get('train_test_split', 0.7),
            max_iterations=optimization_data.get('max_iterations', 1000),
            n_jobs=optimization_data.get('n_jobs', -1),
        )
        
        return SystemConfig(
            system=system,
            data=data_config,
            risk=risk,
            notifications=notifications,
            backtest=backtest,
            logging=logging_config,
            strategies=strategies,
            performance=performance,
            optimization=optimization,
        )
    
    def _override_from_env(self, config: SystemConfig) -> SystemConfig:
        """從環境變數覆蓋配置
        
        支持的環境變數：
        - SYSTEM_ENVIRONMENT: 系統環境
        - DATA_PRIMARY_SOURCE: 主數據源
        - RISK_GLOBAL_MAX_DRAWDOWN: 全局最大回撤
        - RISK_DAILY_LOSS_LIMIT: 每日虧損限制
        - BACKTEST_INITIAL_CAPITAL: 回測初始資金
        
        Args:
            config: 系統配置對象
            
        Returns:
            SystemConfig: 覆蓋後的配置對象
        """
        # 系統配置
        if 'SYSTEM_ENVIRONMENT' in os.environ:
            config.system.environment = os.environ['SYSTEM_ENVIRONMENT']
        
        # 數據配置
        if 'DATA_PRIMARY_SOURCE' in os.environ:
            config.data.primary_source = os.environ['DATA_PRIMARY_SOURCE']
        
        if 'DATA_CACHE_TTL' in os.environ:
            try:
                config.data.cache_ttl = int(os.environ['DATA_CACHE_TTL'])
            except ValueError:
                logger.warning(f"無效的 DATA_CACHE_TTL 值：{os.environ['DATA_CACHE_TTL']}")
        
        # 風險配置
        if 'RISK_GLOBAL_MAX_DRAWDOWN' in os.environ:
            try:
                config.risk.global_max_drawdown = float(os.environ['RISK_GLOBAL_MAX_DRAWDOWN'])
            except ValueError:
                logger.warning(f"無效的 RISK_GLOBAL_MAX_DRAWDOWN 值：{os.environ['RISK_GLOBAL_MAX_DRAWDOWN']}")
        
        if 'RISK_DAILY_LOSS_LIMIT' in os.environ:
            try:
                config.risk.daily_loss_limit = float(os.environ['RISK_DAILY_LOSS_LIMIT'])
            except ValueError:
                logger.warning(f"無效的 RISK_DAILY_LOSS_LIMIT 值：{os.environ['RISK_DAILY_LOSS_LIMIT']}")
        
        if 'RISK_GLOBAL_MAX_POSITION' in os.environ:
            try:
                config.risk.global_max_position = float(os.environ['RISK_GLOBAL_MAX_POSITION'])
            except ValueError:
                logger.warning(f"無效的 RISK_GLOBAL_MAX_POSITION 值：{os.environ['RISK_GLOBAL_MAX_POSITION']}")
        
        # 回測配置
        if 'BACKTEST_INITIAL_CAPITAL' in os.environ:
            try:
                config.backtest.initial_capital = float(os.environ['BACKTEST_INITIAL_CAPITAL'])
            except ValueError:
                logger.warning(f"無效的 BACKTEST_INITIAL_CAPITAL 值：{os.environ['BACKTEST_INITIAL_CAPITAL']}")
        
        if 'BACKTEST_COMMISSION' in os.environ:
            try:
                config.backtest.commission = float(os.environ['BACKTEST_COMMISSION'])
            except ValueError:
                logger.warning(f"無效的 BACKTEST_COMMISSION 值：{os.environ['BACKTEST_COMMISSION']}")
        
        # 日誌配置
        if 'LOG_LEVEL' in os.environ:
            config.logging.level = os.environ['LOG_LEVEL']
        
        return config
    
    def get_config(self) -> SystemConfig:
        """獲取當前配置
        
        Returns:
            SystemConfig: 系統配置對象
            
        Raises:
            RuntimeError: 配置未載入
        """
        if self.config is None:
            raise RuntimeError("配置未載入，請先調用 load_config()")
        
        return self.config
    
    def reload_config(self) -> SystemConfig:
        """重新載入配置
        
        Returns:
            SystemConfig: 系統配置對象
        """
        logger.info("重新載入配置...")
        old_config = self.config
        new_config = self.load_config()
        
        # 通知所有監聽器
        for watcher in self._watchers:
            try:
                watcher(old_config, new_config)
            except Exception as e:
                logger.error(f"配置變更通知失敗：{e}")
        
        return new_config
    
    def watch_config_changes(self, callback: callable) -> None:
        """監聽配置變更
        
        Args:
            callback: 回調函數，接收 (old_config, new_config) 參數
        """
        self._watchers.append(callback)
    
    def update_risk_config(self, **kwargs) -> None:
        """動態更新風險配置
        
        Args:
            **kwargs: 風險配置參數
        """
        if self.config is None:
            raise RuntimeError("配置未載入，請先調用 load_config()")
        
        old_config = self.config
        
        # 更新風險配置
        for key, value in kwargs.items():
            if hasattr(self.config.risk, key):
                setattr(self.config.risk, key, value)
                logger.info(f"風險配置已更新：{key} = {value}")
            else:
                logger.warning(f"未知的風險配置參數：{key}")
        
        # 驗證配置
        valid, error_msg = self.config.validate()
        if not valid:
            # 恢復舊配置
            self.config = old_config
            raise ValueError(f"配置驗證失敗：{error_msg}")
        
        # 通知監聽器
        for watcher in self._watchers:
            try:
                watcher(old_config, self.config)
            except Exception as e:
                logger.error(f"配置變更通知失敗：{e}")


# 全局配置管理器實例
_config_manager: Optional[ConfigManager] = None


def get_config_manager(config_path: str = "system_config.yaml") -> ConfigManager:
    """獲取全局配置管理器實例
    
    Args:
        config_path: 配置文件路徑
        
    Returns:
        ConfigManager: 配置管理器實例
    """
    global _config_manager
    
    if _config_manager is None:
        _config_manager = ConfigManager(config_path)
        _config_manager.load_config()
    
    return _config_manager


def get_system_config() -> SystemConfig:
    """獲取系統配置
    
    Returns:
        SystemConfig: 系統配置對象
    """
    return get_config_manager().get_config()
