# 🔄 檔案恢復指南

## 快速恢復

### 恢復單個文檔
```bash
# 從文檔歸檔恢復
cp _Archive/Doc_20260211/文件名.md .

# 範例：恢復 BingX 手續費說明
cp _Archive/Doc_20260211/BingX手續費完整說明.md .
```

### 恢復單個程式
```bash
# 從程式碼歸檔恢復
cp _Archive/Code_20260211/腳本名.py .

# 範例：恢復回測腳本
cp _Archive/Code_20260211/backtest_multi_timeframe.py .
```

### 恢復 Shell 腳本
```bash
# 從腳本歸檔恢復
cp _Archive/Script_20260211/腳本名.sh .
chmod +x 腳本名.sh

# 範例：恢復數據整理腳本
cp _Archive/Script_20260211/執行數據腳本整理.sh .
chmod +x 執行數據腳本整理.sh
```

---

## 批次恢復

### 恢復所有文檔
```bash
cp _Archive/Doc_20260211/*.md .
```

### 恢復所有程式碼
```bash
cp _Archive/Code_20260211/*.py .
```

### 恢復所有 Shell 腳本
```bash
cp _Archive/Script_20260211/*.sh .
chmod +x *.sh
```

---

## 完全回滾

如果需要完全回滾清理操作：

```bash
# 恢復所有檔案
cp _Archive/Doc_20260211/* .
cp _Archive/Code_20260211/* .
cp _Archive/Script_20260211/* .

# 修復 Shell 腳本權限
chmod +x *.sh

# 刪除歸檔目錄（可選）
rm -rf _Archive/
```

---

## 選擇性恢復

### 只恢復回測腳本
```bash
cp _Archive/Code_20260211/backtest_*.py .
cp _Archive/Code_20260211/improved_backtest.py .
cp _Archive/Code_20260211/final_optimized_backtest.py .
```

### 只恢復 BingX 相關文檔
```bash
cp _Archive/Doc_20260211/BingX*.md .
```

### 只恢復評分系統文檔
```bash
cp _Archive/Doc_20260211/評分*.md .
cp _Archive/Doc_20260211/自動評分*.md .
```

---

## 驗證恢復

恢復後驗證功能：

```bash
# 驗證 Python 腳本
python3 -m py_compile 腳本名.py

# 驗證 Shell 腳本
bash -n 腳本名.sh

# 測試執行
python3 腳本名.py --help
```

---

## 常見問題

### Q: 恢復後檔案權限不對？
```bash
# 修復 Python 腳本權限
chmod 644 *.py

# 修復 Shell 腳本權限
chmod +x *.sh
```

### Q: 恢復後 Git 狀態混亂？
```bash
# 查看變更
git status

# 如果需要，重置到清理前
git log  # 找到清理前的 commit
git reset --hard <commit-hash>
```

### Q: 只想查看歸檔內容，不恢復？
```bash
# 列出文檔歸檔
ls -lh _Archive/Doc_20260211/

# 查看文檔內容
cat _Archive/Doc_20260211/文件名.md

# 使用 less 瀏覽
less _Archive/Doc_20260211/文件名.md
```

---

## 歸檔目錄結構

```
_Archive/
├── Doc_20260211/          # 文檔歸檔（48 個）
│   ├── README.md          # 歸檔說明
│   ├── 功能完成總結_*.md
│   ├── BingX*.md
│   ├── K線圖*.md
│   └── ...
├── Code_20260211/         # 程式碼歸檔（15 個）
│   ├── README.md          # 歸檔說明
│   ├── backtest_*.py
│   ├── 測試*.py
│   └── ...
├── Script_20260211/       # 腳本歸檔（2 個）
│   ├── README.md          # 歸檔說明
│   └── *.sh
└── RECOVERY_GUIDE.md      # 本指南
```

---

## 聯絡支援

如有任何問題：
1. 查看歸檔說明：`cat _Archive/*/README.md`
2. 查看清理方案：`cat 專案清理方案_20260211.md`
3. 查看 Git 歷史：`git log --oneline`

---

**最後更新**：2026-02-11  
**維護者**：Kiro AI Assistant
