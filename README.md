# 🎯 多策略交易系統 (Multi-Strategy Trading System)

一個可擴展的加密貨幣交易平台，支持同時運行多個獨立的交易策略，提供完整的回測、優化、分析和覆盤功能。

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 📊 系統特點

### 🚀 核心功能

- **多策略並行運行**：同時運行多個獨立策略，互不干擾
- **策略隔離**：每個策略擁有獨立的狀態、資金池和執行環境
- **統一回測引擎**：公平對比不同策略的表現
- **參數優化器**：自動尋找最佳策略參數（網格搜索、隨機搜索、貝葉斯優化）
- **虧損分析器**：自動分析虧損原因並生成改進建議
- **性能監控**：實時監控策略表現，自動檢測異常和退化
- **交易覆盤系統**：系統化記錄和分析每筆交易
- **風險管理**：系統級和策略級的雙重風險控制

### 🏗️ 架構優勢

- **配置驅動**：策略通過 JSON 配置文件定義，支持熱重載
- **可擴展性**：快速開發和部署新策略，無需修改核心系統
- **測試友好**：完整的單元測試和屬性測試覆蓋
- **數據優先**：所有決策基於數據，所有操作可追溯

---

## 🚀 快速開始

### 1. 安裝依賴

```bash
# 克隆倉庫
git clone <repository-url>
cd multi-strategy-trading-system

# 安裝依賴
pip install -r requirements.txt
```

### 2. 配置系統

編輯 `system_config.yaml` 配置系統參數：

```yaml
system:
  name: "Multi-Strategy Trading System"
  version: "1.0.0"

data:
  primary_source: "binance"
  backup_sources: ["bingx"]
  cache_ttl: 300

risk:
  global_max_drawdown: 0.20
  daily_loss_limit: 0.10
  global_max_position: 0.80

notifications:
  telegram:
    enabled: true
    bot_token: "${TELEGRAM_BOT_TOKEN}"
    chat_id: "${TELEGRAM_CHAT_ID}"
```

配置環境變數（創建 `.env` 文件）：

```bash
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
BINANCE_API_KEY=your_api_key
BINANCE_API_SECRET=your_api_secret
```

### 3. 創建策略配置

在 `strategies/` 目錄下創建策略配置文件（或使用現有的示例策略）：

```bash
# 查看現有策略
ls strategies/

# 輸出：
# multi-timeframe-aggressive.json
# multi-timeframe-relaxed.json
# breakout-strategy.json
```

### 4. 運行回測

```bash
# 回測單個策略
python cli.py backtest --strategy multi-timeframe-aggressive --start 2024-01-01 --end 2024-12-31

# 回測多個策略
python cli.py backtest --strategies multi-timeframe-aggressive,breakout-strategy --start 2024-01-01 --end 2024-12-31
```

### 5. 啟動實盤交易

```bash
# 啟動單個策略
python cli.py live --strategy multi-timeframe-aggressive

# 啟動多個策略
python cli.py live --strategies multi-timeframe-aggressive,breakout-strategy
```

---

## 📁 項目結構

```
multi-strategy-trading-system/
│
├── src/                          # 源代碼
│   ├── models/                   # 數據模型
│   │   ├── config.py            # 策略配置模型
│   │   ├── trading.py           # 交易相關模型
│   │   ├── backtest.py          # 回測結果模型
│   │   ├── risk.py              # 風險管理模型
│   │   └── state.py             # 策略狀態模型
│   │
│   ├── managers/                 # 管理層
│   │   ├── strategy_manager.py  # 策略管理器
│   │   ├── risk_manager.py      # 風險管理器
│   │   └── data_manager.py      # 數據管理器
│   │
│   ├── execution/                # 執行層
│   │   ├── strategy.py          # 策略基類
│   │   ├── backtest_engine.py   # 回測引擎
│   │   └── multi_strategy_executor.py  # 多策略執行器
│   │
│   ├── strategies/               # 策略實現
│   │   ├── multi_timeframe_strategy.py  # 多週期策略
│   │   └── breakout_strategy.py         # 突破策略
│   │
│   ├── analysis/                 # 分析層
│   │   ├── optimizer.py         # 參數優化器
│   │   ├── loss_analyzer.py     # 虧損分析器
│   │   ├── performance_monitor.py  # 性能監控器
│   │   └── review_system.py     # 覆盤系統
│   │
│   └── config_manager.py         # 配置管理器
│
├── strategies/                   # 策略配置文件
│   ├── multi-timeframe-aggressive.json
│   ├── multi-timeframe-relaxed.json
│   └── breakout-strategy.json
│
├── tools/                        # 開發工具
│   ├── create_strategy.py       # 創建新策略
│   ├── validate_strategy.py     # 驗證策略
│   ├── version_strategy.py      # 版本管理
│   └── deploy_strategy.py       # 部署策略
│
├── tests/                        # 測試
│   ├── unit/                    # 單元測試
│   ├── property/                # 屬性測試
│   └── integration/             # 集成測試
│
├── data/                         # 數據目錄
│   ├── market_data/             # 市場數據
│   ├── trade_history/           # 交易歷史
│   ├── backtest_results/        # 回測結果
│   └── review_history/          # 覆盤記錄
│
├── cli.py                        # 命令行界面
├── system_config.yaml            # 系統配置
├── requirements.txt              # 依賴列表
└── README.md                     # 本文件
```

---

## 💡 使用示例

### 示例 1：回測單個策略

```bash
python cli.py backtest \
  --strategy multi-timeframe-aggressive \
  --start 2024-01-01 \
  --end 2024-12-31 \
  --initial-capital 1000
```

輸出：
```
=== 回測結果 ===
策略: multi-timeframe-aggressive
時間範圍: 2024-01-01 to 2024-12-31
初始資金: 1000.00 USDT
最終資金: 1404.20 USDT
總收益率: +40.42%
最大回撤: -6.68%
交易次數: 33
勝率: 54.55%
獲利因子: 1.86
夏普比率: 2.34
```

### 示例 2：優化策略參數

```bash
python cli.py optimize \
  --strategy multi-timeframe-aggressive \
  --method bayesian \
  --iterations 100 \
  --start 2024-01-01 \
  --end 2024-12-31
```

### 示例 3：多策略組合回測

```bash
python cli.py backtest \
  --strategies multi-timeframe-aggressive,breakout-strategy \
  --allocation 0.6,0.4 \
  --start 2024-01-01 \
  --end 2024-12-31
```

### 示例 4：創建新策略

```bash
# 使用工具創建新策略
python tools/create_strategy.py \
  --name my-new-strategy \
  --template multi-timeframe \
  --symbol BTCUSDT

# 驗證策略配置
python tools/validate_strategy.py --strategy my-new-strategy

# 部署策略
python tools/deploy_strategy.py --strategy my-new-strategy
```

---

## 📖 核心概念

### 策略配置

每個策略通過 JSON 配置文件定義：

```json
{
  "strategy_id": "multi-timeframe-v1",
  "strategy_name": "多週期共振策略",
  "version": "1.0.0",
  "enabled": true,
  "symbol": "ETHUSDT",
  "timeframes": ["1d", "4h", "1h", "15m"],
  
  "parameters": {
    "stop_loss_atr": 1.5,
    "take_profit_atr": 3.0,
    "rsi_range": [30, 70],
    "ema_distance": 0.03
  },
  
  "risk_management": {
    "position_size": 0.20,
    "leverage": 5,
    "max_trades_per_day": 3,
    "max_consecutive_losses": 3,
    "daily_loss_limit": 0.10
  }
}
```

### 策略接口

所有策略必須實現標準接口：

```python
from src.execution.strategy import Strategy

class MyStrategy(Strategy):
    def generate_signal(self, market_data):
        """生成交易信號"""
        pass
    
    def calculate_position_size(self, capital, price):
        """計算倉位大小"""
        pass
    
    def calculate_stop_loss(self, entry_price, direction, atr):
        """計算止損價格"""
        pass
    
    def calculate_take_profit(self, entry_price, direction, atr):
        """計算目標價格"""
        pass
    
    def should_exit(self, position, market_data):
        """判斷是否應該出場"""
        pass
```

### 風險管理

系統提供兩層風險控制：

**全局風險限制**：
- 最大回撤限制（默認 20%）
- 單日虧損限制（默認 10%）
- 全局倉位限制（默認 80%）

**策略級風險限制**：
- 單策略倉位限制
- 每日最大交易次數
- 連續虧損限制
- 單日虧損限制

---

## 🔧 開發指南

### 創建新策略

1. **使用腳手架工具**：
```bash
python tools/create_strategy.py --name my-strategy --template multi-timeframe
```

2. **實現策略邏輯**：
編輯生成的 `src/strategies/my_strategy.py`

3. **配置策略參數**：
編輯生成的 `strategies/my-strategy.json`

4. **驗證策略**：
```bash
python tools/validate_strategy.py --strategy my-strategy
```

5. **回測策略**：
```bash
python cli.py backtest --strategy my-strategy --start 2024-01-01 --end 2024-12-31
```

6. **優化參數**：
```bash
python cli.py optimize --strategy my-strategy --method bayesian
```

7. **部署策略**：
```bash
python tools/deploy_strategy.py --strategy my-strategy
```

詳細開發指南請參考：[docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md)

---

## 🧪 測試

系統採用雙重測試方法：

### 運行所有測試

```bash
# 運行所有測試
pytest

# 運行單元測試
pytest tests/unit/

# 運行屬性測試
pytest tests/property/

# 運行集成測試
pytest tests/integration/

# 生成測試覆蓋率報告
pytest --cov=src --cov-report=html
```

### 測試覆蓋率

- 核心邏輯：90%+ 覆蓋率
- 工具函數：80%+ 覆蓋率
- 整體：85%+ 覆蓋率

詳細測試指南請參考：[docs/TESTING_GUIDE.md](docs/TESTING_GUIDE.md)

---

## 📊 性能指標

### 回測性能

- 1 年分鐘級數據回測：< 1 分鐘
- 多策略並行回測：支持
- 內存使用：< 2GB

### 實時性能

- 信號生成延遲：< 100ms
- 多策略並發執行：支持
- API 調用優化：緩存機制

---

## 🛠️ 命令行工具

### 回測命令

```bash
# 基本回測
python cli.py backtest --strategy <strategy-id> --start <date> --end <date>

# 多策略回測
python cli.py backtest --strategies <id1>,<id2> --allocation <ratio1>,<ratio2>

# 指定初始資金
python cli.py backtest --strategy <strategy-id> --initial-capital 10000

# 保存結果
python cli.py backtest --strategy <strategy-id> --output results.json
```

### 實盤交易命令

```bash
# 啟動單個策略
python cli.py live --strategy <strategy-id>

# 啟動多個策略
python cli.py live --strategies <id1>,<id2>

# 模擬模式（不實際交易）
python cli.py live --strategy <strategy-id> --dry-run
```

### 優化命令

```bash
# 網格搜索
python cli.py optimize --strategy <strategy-id> --method grid

# 隨機搜索
python cli.py optimize --strategy <strategy-id> --method random --iterations 100

# 貝葉斯優化
python cli.py optimize --strategy <strategy-id> --method bayesian --iterations 50
```

---

## 📚 文檔

- [快速開始指南](docs/QUICKSTART.md)
- [開發者指南](docs/DEVELOPER_GUIDE.md)
- [API 文檔](docs/API.md)
- [策略開發指南](docs/STRATEGY_DEVELOPMENT.md)
- [測試指南](docs/TESTING_GUIDE.md)
- [架構設計](docs/ARCHITECTURE.md)

---

## 🤝 貢獻

歡迎貢獻！請閱讀 [CONTRIBUTING.md](CONTRIBUTING.md) 了解如何參與項目。

---

## 📄 許可證

本項目採用 MIT 許可證 - 詳見 [LICENSE](LICENSE) 文件

---

## 🙏 致謝

感謝所有貢獻者和支持者！

---

## 📞 聯繫方式

- 問題反饋：[GitHub Issues](https://github.com/your-repo/issues)
- 討論：[GitHub Discussions](https://github.com/your-repo/discussions)

---

**從單策略到多策略，從手動到自動化，讓交易更智能！** 🚀
