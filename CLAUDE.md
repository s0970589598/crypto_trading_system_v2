# CLAUDE.md — 本專案交接護欄

加密貨幣訊號/回測/覆盤系統（**無自動下單**，勿加）。個人專案、公開 repo、無外部用戶。
新需求動工前，先對照 `docs/ASSESSMENT_2026-07-09.md` §4.2 的「不做清單」與 `docs/BACKLOG.md` 護欄。

## 環境雷區（先讀，省你半小時誤判）

- 你的工作目錄可能是 **sshfs 掛載**（`/home/alan/mnt/code/...` → Mac mini `/Users/ylwu/code`），
  且可能是 **fresh clone**：mtime 全是 clone 時間、無 .env / logs / data/market_data / venv。
  **不要據此下「系統從未運行」結論**——runtime 足跡在 user 的開發機上，自查指令見 ASSESSMENT §7。
- sshfs 上跑 pytest 很慢：先 `cp -r` 到本地 scratchpad 再跑。
- 遇到 `dubious ownership`：`git config --global --add safe.directory <path>`。
- 本機（Linux 端）可能無 pip/venv 模組：裝 uv（`curl -LsSf https://astral.sh/uv/install.sh | sh`）。

## 語言/依賴 gate

- **Python ≤3.13 硬限制**：`pandas_ta` 在 3.14 無 llvmlite wheel（requirements.txt 有註）。勿升。
- 建環境：`uv venv --python 3.13 .venv && uv pip install -r requirements.txt`。
- 跑測試：`pytest --no-cov -q`（pytest.ini 預設帶 --cov＋hypothesis 統計，全套約 4-9 分鐘）。
  基線 2026-07-09：243 pass / 9 skip / 1 fail（月報邊界 bug，BACKLOG 1.1；修後應 244 pass）。

## 資料層語意（易踩坑）

- `.gitignore` 排除**所有 `*.json`**（白名單見該檔）→ 新資料檔預設不進 git，別以為 commit 了就有備份。
- **`data/review_history/quality_scores.json` 是全系統唯一不可重建資料**（真實交易覆盤評分）。
  git 內僅存的 `.backup` 是截斷壞檔（char 6687 中斷），不可當恢復源。
- 資料目錄慣例（src/config_manager.py:35、src/managers/data_manager.py:98）：`data/market_data/`（可重下載）、
  `data/trade_history/`、`data/backtest_results/`；回測結果另有根目錄 `backtest_result_*.json` glob（web_dashboard）。
- 報告期間語意：daily/weekly/monthly 的 end_date 均為「下一期起點」，過濾應為半開區間 [start, end)
  （review_system.py:273；BACKLOG 1.1 修這裡）。
- BingX 交易紀錄：Web 上傳 → `data/review_history/bingx/orders/`。文件裡的 `bingxHistory/` 目錄慣例**已廢**。

## 程式碼慣例與現況

- 現役 Web 入口是 `web_dashboard_v2.py`（port 8502）；`web_dashboard.py`(v1) 已棄置待歸檔（BACKLOG 1.5）。
- `src/strategies/scalping_high_leverage*.py` 六個版本是**刻意凍結的標本**，只有 v11 經
  `scalping_adapter.py` 接入引擎。勿整併、勿「順手清理」。
- 根目錄中文檔名腳本（快速查看.py、重新下載市場數據_修正時區.py 等）是**現役工具**，
  被 docs 與 pages/trading/live_market_analysis.py 引用，勿當死碼刪。
- `_Archive/` 是有意保留的歷史；docs/reports/ 是 AI session 進度報告存檔（75 個 md），只加註不刪改。
- 測試分四層：tests/unit、property（hypothesis）、integration、analysis。改 src/analysis、src/execution 必跑對應層。

## 安全/法務 gate

- **repo 是公開的**：secrets 只走環境變數（現況乾淨，維持）；任何含真實交易資料的檔案不得新增進 git。
- README 掛 MIT badge 但 LICENSE 檔尚缺（BACKLOG 1.2）。
- 外部 API 全是免費公開端點（Binance/BingX 行情、Telegram Bot），無交易所鑑權金鑰、無下單。

## 試過/查過、別重走的路

- git 全史 secrets 掃描：乾淨（2026-07-09）。
- 替代品掃描已做（ASSESSMENT §5＋附錄）：回測/優化/型態/警報是紅海，別建議「再強化引擎」；
  差異化只在覆盤評分閉環。
- GitHub：0 star/0 fork/0 issue（2026-07-09）——別假設有外部用戶或相容性包袱。
