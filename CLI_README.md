# 多策略交易系統 - 命令行界面 (CLI)

## 概述

多策略交易系統提供了一個功能完整的命令行界面，支持回測、實盤交易和參數優化三種主要模式。

## 安裝

確保已安裝所有依賴：

```bash
pip install -r requirements.txt
```

## 快速開始

### 查看幫助

```bash
python3 cli.py --help
```

### 查看特定命令的幫助

```bash
python3 cli.py backtest --help
python3 cli.py live --help
python3 cli.py optimize --help
```

## 命令詳解

### 1. 回測命令 (backtest)

回測命令用於使用歷史數據測試策略表現。

#### 基本用法

```bash
# 回測單個策略
python3 cli.py backtest --strategy multi-timeframe-aggressive

# 回測多個策略
python3 cli.py backtest --strategy multi-timeframe-aggressive --strategy breakout-strategy

# 指定日期範圍
python3 cli.py backtest --strategy multi-timeframe-aggressive \
  --start 2024-01-01 \
  --end 2024-12-31

# 自定義初始資金和手續費
python3 cli.py backtest --strategy multi-timeframe-aggressive \
  --capital 5000 \
  --commission 0.001

# 保存結果到文件
python3 cli.py backtest --strategy multi-timeframe-aggressive \
  --output results/backtest_result.json
```

#### 參數說明

- `--strategy`: 策略 ID（必需，可多次指定）
- `--start`: 開始日期，格式 YYYY-MM-DD（可選）
- `--end`: 結束日期，格式 YYYY-MM-DD（可選）
- `--capital`: 初始資金，默認 1000 USDT（可選）
- `--commission`: 手續費率，默認 0.0005（可選）
- `--output`: 輸出文件路徑（可選）

#### 輸出示例

```
================================================================================
回測結果：multi-timeframe-aggressive
================================================================================

時間範圍：2025-10-24 00:00:00 至 2026-01-20 00:00:00
初始資金：1000.00 USDT
最終資金：1133.43 USDT
總損益：133.43 USDT (13.34%)

交易統計：
  總交易數：4
  獲利交易：2
  虧損交易：2
  勝率：50.00%

損益統計：
  平均獲利：110.96 USDT
  平均虧損：-44.24 USDT
  獲利因子：2.51

風險指標：
  最大回撤：88.48 USDT (8.85%)
  夏普比率：1.23
================================================================================
```

### 2. 實盤交易命令 (live)

實盤交易命令用於啟動多策略實盤交易系統。

⚠️ **注意**：實盤交易功能目前為框架實現，需要集成交易所 API 才能執行真實交易。

#### 基本用法

```bash
# 模擬模式（推薦用於測試）
python3 cli.py live --strategies multi-timeframe-aggressive,breakout-strategy --dry-run

# 實盤模式（需要確認）
python3 cli.py live --strategies multi-timeframe-aggressive,breakout-strategy

# 自定義初始資金
python3 cli.py live --strategies multi-timeframe-aggressive \
  --capital 5000 \
  --dry-run
```

#### 參數說明

- `--strategies`: 策略 ID 列表，逗號分隔（必需）
- `--capital`: 初始資金，默認 1000 USDT（可選）
- `--dry-run`: 模擬模式，不執行真實交易（可選）

#### 功能特性

- 多策略並行運行
- 實時風險管理
- 策略隔離（獨立資金池和狀態）
- 自動風險限制檢查
- 實時狀態監控

#### 風險限制

系統內置以下風險限制：

- 全局最大回撤：20%
- 每日虧損限制：10%
- 全局最大倉位：80%
- 每日最大交易次數：10

觸發任何限制時，系統會自動暫停交易。

### 3. 參數優化命令 (optimize)

參數優化命令用於自動尋找最佳策略參數。

#### 基本用法

```bash
# 網格搜索（測試所有參數組合）
python3 cli.py optimize --strategy multi-timeframe-aggressive --method grid

# 隨機搜索（隨機採樣參數空間）
python3 cli.py optimize --strategy multi-timeframe-aggressive \
  --method random \
  --iterations 100

# 貝葉斯優化（智能搜索）
python3 cli.py optimize --strategy multi-timeframe-aggressive \
  --method bayesian \
  --iterations 50

# 自定義優化指標
python3 cli.py optimize --strategy multi-timeframe-aggressive \
  --method grid \
  --metric profit_factor

# 保存優化報告
python3 cli.py optimize --strategy multi-timeframe-aggressive \
  --method grid \
  --output reports/optimization_report.txt
```

#### 參數說明

- `--strategy`: 策略 ID（必需）
- `--method`: 優化方法，可選 grid/random/bayesian，默認 grid（可選）
- `--iterations`: 迭代次數，用於 random 和 bayesian 方法，默認 100（可選）
- `--metric`: 優化指標，可選 sharpe_ratio/profit_factor/win_rate/total_pnl，默認 sharpe_ratio（可選）
- `--output`: 輸出報告路徑（可選）

#### 優化方法對比

| 方法 | 優點 | 缺點 | 適用場景 |
|------|------|------|----------|
| **網格搜索** | 全面覆蓋參數空間 | 計算量大，參數多時很慢 | 參數較少（<5個）時 |
| **隨機搜索** | 快速，適合高維參數 | 可能錯過最優解 | 參數較多，時間有限 |
| **貝葉斯優化** | 智能搜索，效率高 | 實現複雜 | 參數較多，追求最優 |

#### 優化指標說明

- `sharpe_ratio`: 夏普比率（風險調整後收益）
- `profit_factor`: 獲利因子（總獲利/總虧損）
- `win_rate`: 勝率（獲利交易比例）
- `total_pnl`: 總損益（絕對收益）

#### 輸出示例

```
================================================================================
參數優化報告
================================================================================
優化方法：grid_search
優化指標：sharpe_ratio
測試組合數：64
優化時間：123.45 秒

最佳參數：
--------------------------------------------------------------------------------
  parameters.stop_loss_atr: 1.5000
  parameters.take_profit_atr: 3.0000
  risk_management.position_size: 0.2000
  risk_management.leverage: 5

訓練集性能：
--------------------------------------------------------------------------------
  總交易數：15
  勝率：60.00%
  總損益：234.56 USDT
  獲利因子：2.34
  夏普比率：1.56

驗證集性能：
--------------------------------------------------------------------------------
  總交易數：8
  勝率：62.50%
  總損益：145.23 USDT
  獲利因子：2.12
  夏普比率：1.45

參數敏感度分析：
--------------------------------------------------------------------------------
  parameters.stop_loss_atr:
    範圍：1.0000 - 2.5000
    評分範圍：0.8900 - 1.5600
    敏感度：0.6700
================================================================================
```

## 數據要求

### 市場數據格式

系統需要 CSV 格式的市場數據，文件命名規則：

```
market_data_{SYMBOL}_{TIMEFRAME}.csv
```

例如：
- `market_data_ETHUSDT_1h.csv`
- `market_data_ETHUSDT_4h.csv`
- `market_data_ETHUSDT_1d.csv`

### CSV 文件格式

必需的列：

```csv
timestamp,open,high,low,close,volume
2024-01-01 00:00:00,2000.0,2050.0,1990.0,2030.0,1000000
2024-01-01 01:00:00,2030.0,2060.0,2020.0,2055.0,1200000
...
```

### 獲取市場數據

使用提供的腳本獲取數據：

```bash
python3 fetch_market_data.py
```

## 策略配置

策略配置文件位於 `strategies/` 目錄，使用 JSON 格式。

### 配置文件示例

```json
{
  "strategy_id": "multi-timeframe-aggressive",
  "strategy_name": "多週期共振策略（激進模式）",
  "version": "1.0.0",
  "enabled": true,
  "symbol": "ETHUSDT",
  "timeframes": ["1d", "4h", "1h", "15m"],
  
  "parameters": {
    "stop_loss_atr": 1.5,
    "take_profit_atr": 3.0,
    "rsi_range": [30, 70],
    "ema_distance": 0.03,
    "volume_threshold": 1.0
  },
  
  "risk_management": {
    "position_size": 0.20,
    "leverage": 5,
    "max_trades_per_day": 3,
    "max_consecutive_losses": 3,
    "daily_loss_limit": 0.10,
    "stop_loss_atr": 1.5,
    "take_profit_atr": 3.0
  }
}
```

### 可用策略

系統內置以下策略：

1. **多週期共振策略** (`multi-timeframe-aggressive`)
   - 基於多個時間週期的趨勢一致性
   - 適合趨勢市場

2. **突破策略** (`breakout-strategy`)
   - 基於價格突破關鍵阻力/支撐位
   - 適合波動市場

## 常見問題

### Q: 如何添加新策略？

1. 在 `src/strategies/` 目錄創建策略類
2. 繼承 `Strategy` 基類並實現所有必需方法
3. 在 `strategies/` 目錄創建 JSON 配置文件
4. 在 CLI 命令模組中註冊策略類

### Q: 回測結果不準確怎麼辦？

檢查以下幾點：
- 市場數據是否完整
- 手續費設置是否合理
- 策略參數是否合理
- 是否有數據洩漏（使用未來數據）

### Q: 如何解讀優化結果？

重點關注：
1. **訓練集 vs 驗證集性能**：差距不應太大，否則可能過擬合
2. **參數敏感度**：敏感度高的參數需要謹慎調整
3. **交易次數**：太少可能不具統計意義
4. **多個指標**：不要只看單一指標

### Q: 實盤交易如何集成交易所 API？

目前實盤交易是框架實現，需要：
1. 集成交易所 API（Binance/BingX）
2. 實現市場數據獲取
3. 實現訂單執行
4. 實現持倉管理

建議先使用模擬模式（`--dry-run`）測試。

## 進階用法

### 批量回測

創建腳本批量測試多個策略：

```bash
#!/bin/bash
for strategy in multi-timeframe-aggressive breakout-strategy; do
  python3 cli.py backtest --strategy $strategy \
    --output results/${strategy}_result.json
done
```

### 參數掃描

測試不同參數組合：

```bash
for capital in 1000 5000 10000; do
  python3 cli.py backtest --strategy multi-timeframe-aggressive \
    --capital $capital \
    --output results/capital_${capital}.json
done
```

### 自動化優化流程

```bash
# 1. 優化參數
python3 cli.py optimize --strategy multi-timeframe-aggressive \
  --method bayesian \
  --output optimization_report.txt

# 2. 手動更新配置文件（根據優化結果）

# 3. 驗證優化後的性能
python3 cli.py backtest --strategy multi-timeframe-aggressive \
  --output optimized_result.json
```

## 相關文檔

- [系統架構](項目結構.md)
- [策略開發指南](STRATEGY_TOOLS_SUMMARY.md)
- [風險管理](槓桿與風險管理.md)
- [快速開始](快速開始.md)

## 支持

如有問題或建議，請查看：
- [項目文檔](文件導覽.md)
- [常見問題](README.md)
- [開發指南](.kiro/specs/multi-strategy-system/design.md)
