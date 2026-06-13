# backtest_multi_timeframe.py vs CLI backtest 詳細對比

**日期**: 2026-02-11

---

## 核心邏輯對比

### 1. 數據載入

#### backtest_multi_timeframe.py
```python
def load_market_data(symbol: str) -> dict:
    timeframes = ['1d', '4h', '1h', '15m']  # 硬編碼
    data = {}
    
    for tf in timeframes:
        filename = f"market_data_{symbol}_{tf}.csv"
        if Path(filename).exists():
            df = pd.read_csv(filename)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            data[tf] = df
```

**特點**:
- 硬編碼時間週期 `['1d', '4h', '1h', '15m']`
- 簡單的錯誤處理
- 只轉換時間戳

#### CLI backtest.py
```python
def load_market_data(symbol: str, timeframes: List[str]) -> Dict[str, pd.DataFrame]:
    market_data = {}
    
    for timeframe in timeframes:  # 從配置讀取
        filename = f"market_data_{symbol}_{timeframe}.csv"
        
        if not Path(filename).exists():
            logger.warning(f"數據文件不存在：{filename}")
            continue
        
        try:
            df = pd.read_csv(filename)
            
            # 檢查必需的列
            required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
            if not all(col in df.columns for col in required_columns):
                logger.error(f"數據文件 {filename} 缺少必需的列")
                continue
            
            # 轉換時間戳（支持多種格式）
            if df['timestamp'].dtype == 'object':
                df['timestamp'] = pd.to_datetime(df['timestamp'])
            elif df['timestamp'].dtype in ['int64', 'float64']:
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # 排序
            df = df.sort_values('timestamp').reset_index(drop=True)
            
            market_data[timeframe] = df
```

**特點**:
- 從策略配置讀取時間週期（靈活）
- 檢查必需的列
- 支持多種時間戳格式
- 數據排序
- 完整的錯誤處理和日誌

**差異**: CLI 更健壯，支持不同配置

---

### 2. 策略載入

#### backtest_multi_timeframe.py
```python
config_file = "strategies/multi-timeframe-aggressive.json"  # 硬編碼
with open(config_file, 'r') as f:
    config_dict = json.load(f)

config = StrategyConfig.from_dict(config_dict)
strategy = MultiTimeframeStrategy(config)  # 硬編碼策略類
```

**特點**:
- 硬編碼配置檔案路徑
- 硬編碼策略類 `MultiTimeframeStrategy`
- 只能回測這一個策略

#### CLI backtest.py
```python
def load_strategy(strategy_id: str):
    config_file = Path(f"strategies/{strategy_id}.json")  # 動態路徑
    
    if not config_file.exists():
        raise FileNotFoundError(f"策略配置文件不存在：{config_file}")
    
    config = StrategyConfig.from_json(str(config_file))
    
    # 根據策略 ID 推斷策略類
    if 'multi-timeframe' in strategy_id.lower():
        strategy_class = MultiTimeframeStrategy
    elif 'breakout' in strategy_id.lower():
        strategy_class = BreakoutStrategy
    else:
        strategy_class = MultiTimeframeStrategy  # 默認
    
    strategy = strategy_class(config)
    return strategy
```

**特點**:
- 動態載入任何策略配置
- 自動推斷策略類型
- 支持多種策略（MultiTimeframe, Breakout 等）
- 完整的錯誤處理

**差異**: CLI 支持任意策略，不限於 multi-timeframe-aggressive

---

### 3. 回測引擎

#### backtest_multi_timeframe.py
```python
initial_capital = 1000.0  # 硬編碼
commission = 0.0005       # 硬編碼

engine = BacktestEngine(initial_capital, commission)
result = engine.run_single_strategy(strategy, market_data)
```

**特點**:
- 硬編碼初始資金 1000 USDT
- 硬編碼手續費 0.05%
- 只支持單策略回測

#### CLI backtest.py
```python
engine = BacktestEngine(
    initial_capital=args.capital,    # 命令行參數
    commission=args.commission        # 命令行參數
)

if len(strategies) == 1:
    result = engine.run_single_strategy(strategy, market_data, start_date, end_date)
else:
    # 支持多策略回測
    results = engine.run_multi_strategy(strategies, market_data, capital_allocation, start_date, end_date)
```

**特點**:
- 可配置初始資金（默認 1000）
- 可配置手續費（默認 0.0005）
- 支持單策略和多策略回測
- 支持日期範圍過濾

**差異**: CLI 更靈活，支持多策略和日期過濾

---

### 4. 結果輸出

#### backtest_multi_timeframe.py
```python
print(f"策略 ID：{result.strategy_id}")
print(f"開始日期：{result.start_date}")
print(f"結束日期：{result.end_date}")
# ... 詳細的格式化輸出，包含 emoji

# 顯示最近 10 筆交易
for trade in result.trades[-10:]:
    direction_emoji = "📈" if trade.direction == 'long' else "📉"
    pnl_emoji = "✅" if trade.pnl > 0 else "❌"
    print(f"{direction_emoji} {trade.entry_time.strftime('%Y-%m-%d %H:%M')} | ...")

# 保存結果
output_file = f"backtest_result_{config.strategy_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
result.save(output_file)
```

**特點**:
- 友好的格式化輸出（emoji、對齊）
- 顯示最近 10 筆交易明細
- 自動生成帶時間戳的檔名

#### CLI backtest.py
```python
def print_backtest_result(result, strategy_id: str):
    print("\n" + "=" * 80)
    print(f"回測結果：{strategy_id}")
    print("=" * 80)
    
    print(f"\n時間範圍：{result.start_date} 至 {result.end_date}")
    print(f"初始資金：{result.initial_capital:.2f} USDT")
    # ... 標準格式輸出，無 emoji

# 保存結果（可選）
if args.output:
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False, default=str)
```

**特點**:
- 標準格式輸出（無 emoji）
- 不顯示交易明細
- 可選的輸出檔案（需要 --output 參數）

**差異**: backtest_multi_timeframe.py 輸出更友好，CLI 更簡潔

---

## 功能對比表

| 功能 | backtest_multi_timeframe.py | CLI backtest | 差異 |
|------|---------------------------|--------------|------|
| **策略選擇** | 硬編碼 multi-timeframe-aggressive | 任意策略 | CLI 更靈活 |
| **策略類型** | 只支持 MultiTimeframeStrategy | 支持多種策略類 | CLI 更通用 |
| **時間週期** | 硬編碼 ['1d','4h','1h','15m'] | 從配置讀取 | CLI 更靈活 |
| **初始資金** | 硬編碼 1000 | 可配置（默認 1000） | CLI 可配置 |
| **手續費** | 硬編碼 0.0005 | 可配置（默認 0.0005） | CLI 可配置 |
| **日期範圍** | 全部數據 | 可指定 start/end | CLI 支持過濾 |
| **多策略** | ❌ 不支持 | ✅ 支持 | CLI 獨有 |
| **數據驗證** | 基本 | 完整（檢查列、格式） | CLI 更健壯 |
| **錯誤處理** | 簡單 | 完整（logger） | CLI 更完善 |
| **輸出格式** | 友好（emoji、對齊） | 標準（簡潔） | 各有優勢 |
| **交易明細** | ✅ 顯示最近 10 筆 | ❌ 不顯示 | backtest 獨有 |
| **結果保存** | ✅ 自動保存 | 可選（--output） | backtest 更方便 |

---

## 結論

### 功能等價性：**80%**

#### CLI 優勢
1. ✅ 支持任意策略（不限於 multi-timeframe-aggressive）
2. ✅ 支持多策略回測
3. ✅ 可配置參數（資金、手續費）
4. ✅ 支持日期範圍過濾
5. ✅ 更健壯的數據驗證和錯誤處理

#### backtest_multi_timeframe.py 優勢
1. ✅ 更友好的輸出格式（emoji、對齊）
2. ✅ 顯示交易明細（最近 10 筆）
3. ✅ 自動保存結果（無需參數）
4. ✅ 快速執行（無需輸入參數）

### 使用場景

#### 適合使用 backtest_multi_timeframe.py
- 快速測試 multi-timeframe-aggressive 策略
- 需要查看交易明細
- 喜歡友好的輸出格式

#### 適合使用 CLI backtest
- 測試不同策略
- 需要配置參數
- 需要日期範圍過濾
- 多策略對比
- 生產環境使用

---

## 建議

### 方案 A: 刪除 backtest_multi_timeframe.py
**理由**: CLI 功能更完整，可以完全替代

**替代方案**:
```bash
# 原來
python3 backtest_multi_timeframe.py

# 改用 CLI（完全等價）
python3 -m cli_commands.backtest --strategy multi-timeframe-aggressive

# 如果需要交易明細，可以查看保存的 JSON 檔案
```

### 方案 B: 保留作為快速工具
**理由**: 
- 輸出更友好（emoji、交易明細）
- 無需輸入參數，執行更快
- 適合快速測試

**建議**: 如果保留，應該：
1. 添加命令行參數支持（可選）
2. 文檔中說明與 CLI 的區別
3. 標記為「快速測試工具」

---

## 最終建議

✅ **建議刪除 backtest_multi_timeframe.py**

**原因**:
1. CLI 功能覆蓋 80%，且更靈活
2. 交易明細可以從保存的 JSON 檔案查看
3. 友好輸出可以通過改進 CLI 實現
4. 減少代碼維護負擔

**如果需要友好輸出**，可以改進 CLI：
```python
# 在 cli_commands/backtest.py 中添加
if args.verbose:
    # 顯示交易明細
    for trade in result.trades[-10:]:
        print(f"📈 {trade.entry_time} | ...")
```
