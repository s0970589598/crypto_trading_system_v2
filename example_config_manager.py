"""
系統配置管理器使用示例
演示如何載入、使用和動態更新系統配置
"""

import logging
from src.config_manager import get_config_manager, get_system_config

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def config_change_handler(old_config, new_config):
    """配置變更處理器
    
    Args:
        old_config: 舊配置
        new_config: 新配置
    """
    logger.info("配置已變更！")
    
    # 檢查風險配置變更
    if old_config.risk.global_max_drawdown != new_config.risk.global_max_drawdown:
        logger.info(f"全局最大回撤限制已變更：{old_config.risk.global_max_drawdown} -> {new_config.risk.global_max_drawdown}")
    
    if old_config.risk.daily_loss_limit != new_config.risk.daily_loss_limit:
        logger.info(f"每日虧損限制已變更：{old_config.risk.daily_loss_limit} -> {new_config.risk.daily_loss_limit}")


def main():
    """主函數"""
    
    # 1. 獲取配置管理器並載入配置
    logger.info("=== 1. 載入系統配置 ===")
    config_manager = get_config_manager("system_config.yaml")
    config = config_manager.get_config()
    
    # 顯示當前配置
    logger.info(f"系統名稱：{config.system.name}")
    logger.info(f"系統版本：{config.system.version}")
    logger.info(f"環境：{config.system.environment}")
    logger.info(f"主數據源：{config.data.primary_source}")
    logger.info(f"備用數據源：{config.data.backup_sources}")
    logger.info(f"全局最大回撤：{config.risk.global_max_drawdown * 100}%")
    logger.info(f"每日虧損限制：{config.risk.daily_loss_limit * 100}%")
    logger.info(f"全局最大倉位：{config.risk.global_max_position * 100}%")
    logger.info(f"回測初始資金：{config.backtest.initial_capital} USDT")
    logger.info(f"手續費率：{config.backtest.commission * 100}%")
    
    # 2. 註冊配置變更監聽器
    logger.info("\n=== 2. 註冊配置變更監聽器 ===")
    config_manager.watch_config_changes(config_change_handler)
    logger.info("配置變更監聽器已註冊")
    
    # 3. 動態更新風險配置（無需重啟系統）
    logger.info("\n=== 3. 動態更新風險配置 ===")
    try:
        config_manager.update_risk_config(
            global_max_drawdown=0.15,  # 從 20% 降低到 15%
            daily_loss_limit=0.08,     # 從 10% 降低到 8%
        )
        logger.info("風險配置更新成功")
        
        # 獲取更新後的配置
        updated_config = config_manager.get_config()
        logger.info(f"新的全局最大回撤：{updated_config.risk.global_max_drawdown * 100}%")
        logger.info(f"新的每日虧損限制：{updated_config.risk.daily_loss_limit * 100}%")
        
    except ValueError as e:
        logger.error(f"配置更新失敗：{e}")
    
    # 4. 嘗試更新無效配置（應該失敗）
    logger.info("\n=== 4. 嘗試更新無效配置 ===")
    try:
        config_manager.update_risk_config(
            global_max_drawdown=1.5,  # 無效值（> 1）
        )
        logger.error("不應該執行到這裡！")
    except ValueError as e:
        logger.info(f"配置驗證成功阻止了無效配置：{e}")
    
    # 5. 重新載入配置文件
    logger.info("\n=== 5. 重新載入配置文件 ===")
    reloaded_config = config_manager.reload_config()
    logger.info(f"配置已重新載入")
    logger.info(f"全局最大回撤：{reloaded_config.risk.global_max_drawdown * 100}%")
    
    # 6. 使用全局配置獲取器
    logger.info("\n=== 6. 使用全局配置獲取器 ===")
    global_config = get_system_config()
    logger.info(f"通過全局獲取器獲取配置：{global_config.system.name}")
    
    # 7. 顯示通知配置
    logger.info("\n=== 7. 通知配置 ===")
    logger.info(f"Telegram 通知：{'啟用' if config.notifications.telegram.enabled else '停用'}")
    logger.info(f"Email 通知：{'啟用' if config.notifications.email.enabled else '停用'}")
    logger.info(f"Webhook 通知：{'啟用' if config.notifications.webhook.enabled else '停用'}")
    
    # 8. 顯示策略配置
    logger.info("\n=== 8. 策略配置 ===")
    logger.info(f"策略配置目錄：{config.strategies.config_dir}")
    logger.info(f"自動載入：{'是' if config.strategies.auto_load else '否'}")
    logger.info(f"熱重載：{'是' if config.strategies.hot_reload else '否'}")
    logger.info(f"重載間隔：{config.strategies.reload_interval} 秒")
    
    # 9. 顯示優化配置
    logger.info("\n=== 9. 優化配置 ===")
    logger.info(f"默認優化方法：{config.optimization.default_method}")
    logger.info(f"訓練/測試集分割：{config.optimization.train_test_split * 100}% / {(1 - config.optimization.train_test_split) * 100}%")
    logger.info(f"最大迭代次數：{config.optimization.max_iterations}")
    logger.info(f"並行任務數：{config.optimization.n_jobs}")
    
    logger.info("\n=== 配置管理器示例完成 ===")


if __name__ == "__main__":
    main()
