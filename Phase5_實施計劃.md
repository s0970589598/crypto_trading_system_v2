# Phase 5 實施計劃

**日期**: 2026-02-11  
**目標**: 提供 CLI 接口整合量化風險分析

---

## 📊 實施範圍

### 新建檔案

1. **cli_commands/analyze_risk.py** - 量化風險分析 CLI 命令
2. **tests/cli/test_analyze_risk.py** - CLI 命令測試（可選）

### 更新檔案

1. **CLI_README.md** - 添加新命令文檔

---

## 🎯 CLI 命令設計

### 命令名稱

```bash
python -m cli_commands.analyze_risk [選項]
```

### 主要功能

1. **基本分析** - 顯示所有量化風險指標
2. **Kelly Criterion** - 計算最優倉位
3. **傾斜行為** - 檢測情緒化交易
4. **破產風險** - 計算破產概率
5. **手續費壓力** - 分析手續費影響
6. **恢復係數** - 評估恢復能力
7. **情緒控制** - 分析情緒控制
8. **能力評分** - 評估交易能力
9. **連損分析** - 分析最長連損
10. **短線交易** - 分析短線交易效果
11. **冷靜期** - 提供冷靜期建議

### 命令行參數

```bash
# 必需參數
--data PATH          交易數據文件路徑（CSV 格式）

# 可選參數
--analysis TYPE      分析類型（all, kelly, tilt, ror, fee, recovery, 
                     emotional, skill, streak, short, cooling）
                     默認：all
--short-minutes N    短線交易時間閾值（分鐘），默認：5.0
--output PATH        輸出結果到文件（JSON 格式）
--format FORMAT      輸出格式（text, json），默認：text
--verbose           顯示詳細信息
```

### 使用示例

```bash
# 1. 顯示所有分析
python -m cli_commands.analyze_risk --data trades.csv

# 2. 只顯示 Kelly Criterion
python -m cli_commands.analyze_risk --data trades.csv --analysis kelly

# 3. 分析短線交易（10分鐘）
python -m cli_commands.analyze_risk --data trades.csv --analysis short --short-minutes 10

# 4. 輸出到 JSON 文件
python -m cli_commands.analyze_risk --data trades.csv --output result.json --format json

# 5. 詳細模式
python -m cli_commands.analyze_risk --data trades.csv --verbose
```

---

## 📋 實施步驟

### Step 1: 創建 CLI 命令檔案（10分鐘）

**檔案**: `cli_commands/analyze_risk.py`

**內容**:
1. 導入必要模組
2. 定義命令行參數解析
3. 實現數據載入函數
4. 實現各種分析函數
5. 實現結果格式化輸出
6. 實現主函數

### Step 2: 實現核心功能（10分鐘）

**功能列表**:
1. `load_trades_data()` - 載入交易數據
2. `analyze_all()` - 執行所有分析
3. `analyze_kelly()` - Kelly Criterion 分析
4. `analyze_tilt()` - 傾斜行為分析
5. `analyze_ror()` - 破產風險分析
6. `analyze_fee()` - 手續費壓力分析
7. `analyze_recovery()` - 恢復係數分析
8. `analyze_emotional()` - 情緒控制分析
9. `analyze_skill()` - 能力評分分析
10. `analyze_streak()` - 連損分析
11. `analyze_short()` - 短線交易分析
12. `analyze_cooling()` - 冷靜期分析

### Step 3: 實現輸出格式化（5分鐘）

**格式**:
1. **文本格式** - 友好的終端輸出
2. **JSON 格式** - 機器可讀的結構化輸出

### Step 4: 測試（5分鐘）

**測試內容**:
1. 命令行參數解析
2. 數據載入
3. 各種分析功能
4. 輸出格式

### Step 5: 更新文檔（5分鐘）

**更新檔案**: `CLI_README.md`

**添加內容**:
- 命令說明
- 參數說明
- 使用示例
- 輸出格式說明

**總時間**: 約 35 分鐘

---

## 🎨 輸出格式設計

### 文本格式示例

```
================================================================================
量化風險分析報告
================================================================================

數據文件: trades.csv
分析時間: 2026-02-11 10:30:00
交易數量: 150

--------------------------------------------------------------------------------
Kelly Criterion 分析
--------------------------------------------------------------------------------
最優倉位: 15.2%
建議倉位: 7.6%
勝率: 52.3%
盈虧比: 1.45
期望值: 0.089
破產風險: 2.3%

--------------------------------------------------------------------------------
傾斜行為檢測
--------------------------------------------------------------------------------
綜合評分: 3.2 / 10
嚴重程度: 低
倉位因子: 1.2
槓桿因子: 1.1
時機因子: 0.9
頻率因子: 1.0
貢獻因素:
  - 虧損後倉位略有增加

... (其他分析)

================================================================================
```

### JSON 格式示例

```json
{
  "metadata": {
    "data_file": "trades.csv",
    "analysis_time": "2026-02-11T10:30:00",
    "trade_count": 150
  },
  "kelly_criterion": {
    "optimal_size": 0.152,
    "recommended_size": 0.076,
    "win_rate": 0.523,
    "payoff_ratio": 1.45,
    "expectancy": 0.089,
    "risk_of_ruin": 0.023
  },
  "tilt_behavior": {
    "overall_score": 3.2,
    "severity": "low",
    "position_size_factor": 1.2,
    "leverage_factor": 1.1,
    "timing_factor": 0.9,
    "frequency_factor": 1.0,
    "contributing_factors": [
      "虧損後倉位略有增加"
    ]
  }
}
```

---

## ✅ 驗證清單

### 功能驗證

- [ ] 命令行參數解析正確
- [ ] 數據載入正常
- [ ] Kelly Criterion 分析正常
- [ ] 傾斜行為檢測正常
- [ ] 破產風險計算正常
- [ ] 手續費壓力分析正常
- [ ] 恢復係數計算正常
- [ ] 情緒控制分析正常
- [ ] 能力評分計算正常
- [ ] 連損分析正常
- [ ] 短線交易分析正常
- [ ] 冷靜期建議正常

### 輸出驗證

- [ ] 文本格式輸出正確
- [ ] JSON 格式輸出正確
- [ ] 輸出到文件正常
- [ ] 錯誤處理正確

### 文檔驗證

- [ ] CLI_README.md 已更新
- [ ] 命令說明清晰
- [ ] 示例正確可用

---

## 🛡️ 錯誤處理

### 常見錯誤

1. **數據文件不存在**
   ```
   錯誤：數據文件不存在：trades.csv
   請檢查文件路徑是否正確
   ```

2. **數據格式錯誤**
   ```
   錯誤：數據文件格式錯誤
   請確保 CSV 文件包含必需的列
   ```

3. **分析類型無效**
   ```
   錯誤：無效的分析類型：invalid
   可用類型：all, kelly, tilt, ror, fee, recovery, emotional, skill, streak, short, cooling
   ```

4. **輸出文件無法寫入**
   ```
   錯誤：無法寫入輸出文件：result.json
   請檢查文件路徑和權限
   ```

---

## 📊 預期效果

### 功能完整性

✅ **11種分析類型**，全部可通過 CLI 使用

✅ **2種輸出格式**，適應不同使用場景

✅ **靈活的參數**，支持各種分析需求

### 用戶體驗

✅ **簡單易用** - 清晰的命令行參數

✅ **友好輸出** - 易讀的文本格式

✅ **機器可讀** - 結構化的 JSON 格式

✅ **錯誤提示** - 清晰的錯誤信息

---

## 🚀 下一步

完成 Phase 5 後：

1. **Phase 6**: 全面測試（30-45分鐘）
2. **Phase 7**: 文檔與部署（15-30分鐘）

---

**制定人**: Kiro AI Assistant  
**制定日期**: 2026-02-11  
**預計執行時間**: 35 分鐘

