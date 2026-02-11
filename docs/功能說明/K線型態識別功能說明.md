# K線型態識別功能說明

## 📋 功能概述

本系統新增了專業的 **K線型態識別模組**，可以自動偵測以下技術分析型態：

### 1. 避雷針（長上影線）⚡
- **特徵**：上影線至少是實體的2倍，實體不超過整根K線的30%
- **意義**：通常出現在頂部，表示上漲動能衰竭，可能反轉向下
- **強度計算**：影線越長、實體越小，強度越高

### 2. 倒錘子（長下影線）🔨
- **特徵**：下影線至少是實體的2倍，實體不超過整根K線的30%
- **意義**：通常出現在底部，表示下跌動能衰竭，可能反轉向上
- **強度計算**：影線越長、實體越小，強度越高

### 3. 假突破（SFP - Swing Failure Pattern）🚫⬆️
- **特徵**：
  - 價格突破關鍵阻力位
  - 突破幅度小（< 0.2%）
  - 快速回撤（至少50%）
  - 收盤回到阻力位內側
- **意義**：誘多陷阱，可能轉跌
- **強度計算**：回撤幅度越大，強度越高

### 4. 假跌破（SFP）🚫⬇️
- **特徵**：
  - 價格跌破關鍵支撐位
  - 跌破幅度小（< 0.2%）
  - 快速反彈（至少50%）
  - 收盤回到支撐位內側
- **意義**：誘空陷阱，可能轉漲
- **強度計算**：反彈幅度越大，強度越高

### 5. 頭肩頂 👤⬇️
- **特徵**：
  - 左肩 - 頭部 - 右肩
  - 頭部明顯高於兩肩
  - 兩肩高度相近（容差2%）
- **意義**：經典反轉型態，看跌信號
- **強度計算**：兩肩越對稱，強度越高

### 6. 頭肩底 👤⬆️
- **特徵**：
  - 左肩 - 頭部 - 右肩（倒置）
  - 頭部明顯低於兩肩
  - 兩肩高度相近（容差2%）
- **意義**：經典反轉型態，看漲信號
- **強度計算**：兩肩越對稱，強度越高

### 7. 雙頂 ⛰️⛰️⬇️
- **特徵**：兩個高點價格相近（差異 < 2%）
- **意義**：看跌信號
- **強度計算**：兩個高點越接近，強度越高

### 8. 雙底 🏔️🏔️⬆️
- **特徵**：兩個低點價格相近（差異 < 2%）
- **意義**：看漲信號
- **強度計算**：兩個低點越接近，強度越高

---

## 🎯 支撐/阻力有效性分析

### 計算邏輯

1. **觸碰次數**：價格接近該水平的次數（越多越有效）
2. **時間因素**：最近觸碰的時間（越近越有效）
3. **強度評分**：0-100分，綜合考慮觸碰次數和時間因素

### 有效性判斷標準

- **100分**：觸碰10次以上，非常強的支撐/阻力
- **80-99分**：觸碰6-9次，強支撐/阻力
- **60-79分**：觸碰4-5次，中等支撐/阻力
- **40-59分**：觸碰2-3次，弱支撐/阻力
- **< 40分**：觸碰1次，無效

---

## 🖥️ 使用方式

### 方式1：Web界面（推薦）

1. 啟動Web界面：
```bash
./啟動Web界面v2.sh
```

2. 進入「實時市場分析」頁面

3. 輸入交易對（如 BTCUSDT）

4. 點擊「開始分析」

5. 在各時區的詳細分析中，會自動顯示：
   - 🚨 K線型態警報（如果有）
   - 🎯 支撐阻力有效性分析

### 方式2：命令行測試

```bash
python3 測試型態識別.py
```

這會測試：
- 型態識別功能
- 型態警報功能
- 支撐阻力有效性分析

### 方式3：Python API

```python
from src.analysis.market_analyzer import MarketAnalyzer

# 創建分析器
analyzer = MarketAnalyzer()

# 偵測型態
result = analyzer.detect_patterns('BTCUSDT', '1h')

# 獲取結果
patterns = result['patterns']  # 型態列表
supports = result['supports']  # 支撐位列表
resistances = result['resistances']  # 阻力位列表

# 顯示型態
for pattern in patterns:
    print(f"{pattern.emoji} {pattern.description}")
    print(f"強度：{pattern.strength:.0f}/100")

# 獲取型態警報（最近10根K線）
alerts = analyzer.get_pattern_alerts('BTCUSDT', '1h', lookback_bars=10)
for alert in alerts:
    print(alert)

# 分析支撐阻力有效性
sr_analysis = analyzer.analyze_support_resistance_strength('BTCUSDT', '1h')
print(f"最近支撐：${sr_analysis['nearest_support']['level']:.2f}")
print(f"強度：{sr_analysis['nearest_support']['strength']:.0f}/100")
```

---

## 📊 測試結果示例

### ETHUSDT 1h 發現假跌破

```
🚨 發現 1 個型態信號：
  🚫⬇️ 假跌破
     價格：$1995.83
     強度：100/100
     說明：假跌破：跌破0.09%後反彈416.5%，可能轉漲
```

### BTCUSDT 1h 發現避雷針

```
🚨 發現 1 個警報：
  ⚡ 避雷針：上影線是實體的174.9倍，可能反轉向下 (強度: 100)
```

### 支撐阻力有效性分析

```
🟢 最近支撐位：
  價格：$68787.34
  觸碰：19 次
  強度：100/100
  距離：0.77%

🔴 最近阻力位：
  價格：$69999.99
  觸碰：17 次
  強度：100/100
  距離：0.98%
```

---

## ⚙️ 參數調整

如果需要調整偵測靈敏度，可以修改 `src/analysis/pattern_detector.py`：

```python
class PatternDetector:
    def __init__(self):
        # 避雷針參數
        self.lightning_rod_ratio = 2.0  # 上影線至少是實體的2倍
        self.lightning_rod_body_ratio = 0.3  # 實體不超過整根K線的30%
        
        # 假突破參數
        self.fakeout_threshold = 0.002  # 突破幅度閾值 0.2%
        self.fakeout_retracement = 0.5  # 回撤至少50%
        self.fakeout_lookback = 20  # 回看K線數量
        
        # 頭肩頂參數
        self.hs_tolerance = 0.02  # 肩膀高度容差 2%
        self.hs_min_bars = 15  # 最小K線數量
        
        # 支撐阻力參數
        self.sr_proximity = 0.005  # 價格接近度 0.5%
        self.sr_lookback = 100  # 回看K線數量
        self.sr_min_touches = 2  # 最少觸碰次數
```

---

## 🎓 交易建議

### 避雷針/倒錘子
- **出現位置**：關注是否在關鍵阻力/支撐位
- **成交量**：配合放量效果更好
- **確認**：等待下一根K線確認方向

### 假突破/假跌破
- **最佳進場**：假突破後立即反向開倉
- **止損**：突破點位外側
- **止盈**：下一個支撐/阻力位

### 頭肩頂/底
- **進場時機**：右肩形成後，跌破/突破頸線
- **止損**：右肩高點/低點外側
- **止盈**：頭部到頸線的距離

### 支撐阻力
- **強度 > 80**：非常可靠，可作為主要交易依據
- **強度 60-80**：較可靠，建議配合其他指標
- **強度 < 60**：參考價值有限

---

## ⚠️ 注意事項

1. **型態識別不是100%準確**：需要配合其他技術指標和基本面分析
2. **強度評分僅供參考**：市場隨時可能改變
3. **建議多時區確認**：單一時區的信號可能是噪音
4. **風險管理最重要**：永遠設置止損，控制倉位

---

## 🔧 技術細節

### 模組結構

```
src/analysis/
├── market_analyzer.py      # 市場分析器（整合型態識別）
└── pattern_detector.py     # 型態偵測器（核心邏輯）
```

### 新增方法

**MarketAnalyzer 類**：
- `detect_patterns()` - 偵測K線型態
- `get_pattern_alerts()` - 獲取型態警報
- `analyze_support_resistance_strength()` - 分析支撐阻力有效性

**PatternDetector 類**：
- `detect_all_patterns()` - 偵測所有型態
- `detect_lightning_rod()` - 偵測避雷針/倒錘子
- `detect_fakeout()` - 偵測假突破/假跌破
- `detect_head_shoulders()` - 偵測頭肩頂/底
- `detect_double_pattern()` - 偵測雙頂/雙底
- `calculate_support_resistance()` - 計算支撐阻力有效性

---

## 📚 延伸閱讀

- [技術分析入門](https://www.investopedia.com/terms/t/technicalanalysis.asp)
- [K線型態大全](https://www.investopedia.com/trading/candlestick-charting-what-is-it/)
- [支撐阻力理論](https://www.investopedia.com/trading/support-and-resistance-basics/)

---

**版本**：v1.0  
**更新日期**：2026-02-10  
**作者**：Kiro AI Assistant
