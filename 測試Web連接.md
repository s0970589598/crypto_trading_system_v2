# 🌐 Web 界面連接測試

## ✅ 服務已啟動！

Web Dashboard 已經成功啟動並運行在：

### 📱 訪問地址

**方法 1：本地訪問（推薦）**
```
http://localhost:8501
```

**方法 2：IP 訪問**
```
http://192.168.1.179:8501
```

**方法 3：外網訪問（如果需要）**
```
http://114.36.14.233:8501
```

---

## 🔧 如果無法連接

### 檢查 1：服務是否運行？

```bash
# 查看進程
ps aux | grep streamlit

# 應該看到類似：
# python3 -m streamlit run web_dashboard.py
```

### 檢查 2：端口是否開放？

```bash
# 檢查端口
lsof -i :8501

# 應該看到 streamlit 在監聽
```

### 檢查 3：防火牆設置

```bash
# macOS 檢查防火牆
sudo pfctl -s all | grep 8501
```

### 檢查 4：瀏覽器問題

1. 清除瀏覽器緩存
2. 嘗試無痕模式
3. 嘗試其他瀏覽器（Chrome、Firefox、Safari）

---

## 🚀 重新啟動服務

### 方法 1：使用腳本

```bash
# 停止舊服務
pkill -f streamlit

# 重新啟動
bash 啟動Web界面.sh
```

### 方法 2：手動啟動

```bash
# 停止舊服務
pkill -f streamlit

# 手動啟動
python3 -m streamlit run web_dashboard.py
```

### 方法 3：指定端口

```bash
# 如果 8501 被佔用，使用其他端口
python3 -m streamlit run web_dashboard.py --server.port 8502

# 然後訪問
# http://localhost:8502
```

---

## 📊 當前狀態

根據最新檢查：

✅ **Streamlit 已安裝**：版本 1.50.0
✅ **服務已啟動**：進程 ID 4
✅ **監聽端口**：8501
✅ **本地地址**：http://localhost:8501
✅ **網絡地址**：http://192.168.1.179:8501

---

## 💡 使用提示

### 1. 打開瀏覽器

在瀏覽器地址欄輸入：
```
http://localhost:8501
```

### 2. 等待加載

首次啟動可能需要 5-10 秒加載。

### 3. 查看界面

你應該看到：
```
┌─────────────────────────────────┐
│ 🚀 多策略交易系統 Dashboard      │
├─────────────────────────────────┤
│ 側邊欄：                         │
│ ├─ 📊 回測結果                  │
│ ├─ 📈 槓桿對比                  │
│ ├─ ⚙️ 策略配置                  │
│ ├─ 💰 交易分析                  │
│ └─ 🎯 快速操作                  │
└─────────────────────────────────┘
```

### 4. 開始使用

點擊側邊欄的功能開始使用！

---

## 🐛 常見錯誤

### 錯誤 1：「無法連上這個網站」

**原因**：服務未啟動或端口錯誤

**解決**：
```bash
# 重新啟動
pkill -f streamlit
python3 -m streamlit run web_dashboard.py
```

### 錯誤 2：「連接被拒絕」

**原因**：防火牆阻擋

**解決**：
```bash
# 臨時關閉防火牆測試（macOS）
sudo pfctl -d

# 測試後記得重新開啟
sudo pfctl -e
```

### 錯誤 3：「頁面載入緩慢」

**原因**：首次載入需要時間

**解決**：
- 等待 10-20 秒
- 刷新頁面（F5）

### 錯誤 4：「ModuleNotFoundError」

**原因**：缺少依賴

**解決**：
```bash
pip3 install streamlit plotly openpyxl pandas numpy
```

---

## 📞 需要幫助？

### 查看日誌

```bash
# 查看 streamlit 輸出
# 在運行 streamlit 的終端查看錯誤信息
```

### 測試連接

```bash
# 測試端口是否開放
curl http://localhost:8501

# 應該返回 HTML 內容
```

### 重置一切

```bash
# 停止所有 streamlit 進程
pkill -f streamlit

# 清除緩存
rm -rf ~/.streamlit/cache

# 重新安裝
pip3 install --upgrade streamlit

# 重新啟動
python3 -m streamlit run web_dashboard.py
```

---

## ✅ 確認清單

在瀏覽器訪問 `http://localhost:8501` 之前，確認：

- [ ] Streamlit 已安裝（`python3 -c "import streamlit"`）
- [ ] 服務已啟動（`ps aux | grep streamlit`）
- [ ] 端口已監聽（`lsof -i :8501`）
- [ ] 防火牆已關閉或允許 8501 端口
- [ ] 瀏覽器已打開

---

## 🎯 快速測試

複製以下命令，一次性執行：

```bash
# 停止舊服務
pkill -f streamlit

# 等待 2 秒
sleep 2

# 啟動新服務
python3 -m streamlit run web_dashboard.py &

# 等待 5 秒
sleep 5

# 打開瀏覽器
open http://localhost:8501
```

---

**現在試試訪問：http://localhost:8501** 🚀
