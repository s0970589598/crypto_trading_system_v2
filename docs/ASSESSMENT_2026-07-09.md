# 專案全面體檢報告 — crypto_trading_system_v2

**體檢日期**：2026-07-09
**體檢環境**：Linux 端經 sshfs 讀取 Mac mini（`ylwu@YLdeMac-mini-2.local:/Users/ylwu/code`）上的 **fresh clone**（git reflog 唯一一條：`clone: 2026-07-09 03:00`）。
**⚠️ 最重要的前提**：本工作副本今天才 clone，**零 runtime 足跡是必然**（無 .env、無 logs/、無 data/market_data/、無 venv）。所有「實際使用狀態」結論僅能依 git 內容物與 GitHub 遠端狀態推斷，真正的執行環境在你平常開發的那台機器上。證據缺口與自查指令見 §7。

---

## 1. 專案是什麼（實證版）

- Python 加密貨幣**訊號/回測/覆盤**系統，**無下單執行代碼**（repo 掃描確認：無交易所鑑權金鑰變數、無下單 API 呼叫；`cli_commands/live.py` 只做行情與訊號）。
- 44,934 行 Python（`git ls-files '*.py' | xargs wc -l`，2026-07-09）。
- 33 個 commit，三波爆發：2026-02-09~11（8）、06-13~14（13）、07-08（12）。commit 訊息風格與單次改動量顯示大量 AI 輔助開發。
- GitHub 公開 repo：**0 star / 0 fork / 0 issue**（`gh api`，2026-07-09）→ 無任何外部用戶足跡。
- 外部依賴全免費：Binance/BingX 公開行情 API（無金鑰）、Telegram Bot API、開源套件。**月燒錢 ≈ $0**（不含開發時間與 Claude token）。

### 曾真實運作的鐵證
- `data/review_history/quality_scores.json.backup`：真實交易的 auto 評分紀錄，`scored_at: 2026-02-05`，含中文錯誤標註（「獲利太少即出場」等）→ **覆盤評分功能 2 月上旬曾真用**。**但此檔是截斷的壞 JSON**（char 6687 處中斷），且是 git 內唯一一份覆盤資料。
- 根目錄 3 個 `leverage_comparison*.csv` → 槓桿回測曾真跑。
- `重新下載市場數據_修正時區.py` 等修復腳本存在 → 曾有真實資料品質事故（時區錯誤）並修復。

---

## 2. 商業評估

### 2.1 價值主張拆解
| 組成 | 可防禦性 | 依據 |
|---|---|---|
| 回測引擎（滑點/強平/intrabar/分批止盈/MFE） | ❌ 紅海 | freqtrade（~52k星）/vectorbt/jesse 免費且更成熟（替代品掃描 §5） |
| 參數優化＋walk-forward | ❌ 紅海 | 同上，freqtrade Hyperopt、jesse Optuna |
| K線型態識別、支撐阻力 | ❌ 紅海 | TA-Lib CDL* 61 種、pandas-ta 60+ 種，已標準化 |
| Telegram 警報 | ❌ 紅海 | 免費 bot 與開源方案氾濫 |
| 交易覆盤＋自動評分＋Kelly 量化風險 | 🟡 半紅海 | TradesViz（$20-30/月）含 BingX 同步＋Kelly；但「自動評分規則客製」少有人做 |
| **四合一整合＋BingX 深度＋自有評分規則閉環** | ✅ 唯一空白帶 | 2026-07 掃描：無單一 SaaS 或開源框架完整覆蓋（來源見 §5） |

**誠實結論**：可防禦資產不在任何單一模組，在「整合層＋你自己的覆盤資料閉環」。而這個資產的價值目前**只對你一個人成立**——因為閉環裡的資料是你的交易。

### 2.2 買家與商業路線（**這題需要你的判斷**）
三條路線，取捨取決於你每週可投入時數（只有你能答）：

| 路線 | 每週時數 | 誠實評估 |
|---|---|---|
| A. 純自用工具 | 0-2h 維護 | **目前實質路線**。ROI＝你自己交易績效的改善。若 `initial_capital` 1000 USDT 量級是真實本金，45k 行系統的開發時間成本已遠超本金——見 §6「我沒想到的維度」 |
| B. 開源作品集 | 2-4h | 需要：LICENSE 補檔、英文 README、刪個人交易痕跡、CI。回報是履歷/影響力，不是錢 |
| C. 產品化銷售 | 10h+ | 逆風：0 用戶、中文 only、TradesViz $20/月已在賣八成功能。不建議在沒有既有受眾（交易社群/粉絲）的前提下走這條 |

### 2.3 Why-now
- 順風：BingX 中文圈用戶增長、TradesViz 等對 BingX 支援僅 CSV 級、AI 讓個人維護 45k 行系統成為可能。
- 逆風：AI 也讓**買家**能 DIY 出七八成外殼（替代品掃描 §④）——「工具」本身的稀缺性在下降，稀缺的是驗證過的策略與紀律資料。

### 2.4 變現路徑（僅路線 C 適用；每環附轉換假設＋證據等級）
陌生人 → 第一塊錢的鏈：
1. **觸達**：中文交易社群（Telegram 群/Threads/YouTube）發覆盤方法論內容 → 假設 CTR 1-3%【證據等級：無，純假設】
2. **信任**：公開自己的覆盤數據與評分規則 → 假設 10% 追蹤【無證據；且需要你願意公開交易紀錄——這題需要你的判斷】
3. **轉換**：freemium（開源工具＋付費「評分規則庫/代跑報告」）→ 假設 1-2% 付費【無證據】
4. **定價帶**：對標 TradesViz $19.99-29.99/月、Edgewonk $197/年 → 個人開發者可行帶約 **NT$300-600/月或 NT$3000/年買斷**【對標有據，轉換無據】

**最弱環＝第 1 環（觸達）**：你目前沒有任何受眾資產（0 star 亦為旁證）。
**「第一塊錢」最短路徑**：不是賣訂閱——是把覆盤方法論寫成一篇付費文章/小冊（低建置成本，直接測觸達與付費意願）。若那篇文章賣不出 10 份，訂閱制必死，可提前止損。

### 2.5 Kill criteria 與最小成功定義（建議，需你確認）
| 判準 | 訊號來源 |
|---|---|
| **活線（最小成功）**：連續 4 週、每週 ≥1 筆真實交易進覆盤評分，且每月報告產出 ≥1 個被你採納的行為改變 | `data/review_history/quality_scores.json` 的 `scored_at` 時間戳分佈（開發機上查） |
| 死線 1：若至 2026-09-30，覆盤資料最後寫入仍停在 2026 年 2 月 | 同上檔案 mtime/內容 |
| 死線 2（路線 C 專用）：付費意願測試（§2.4 最短路徑）2 個月內 <10 份 | 銷售平台後台數字 |
| 死線 3：連續兩個月「維護系統的時數 > 使用系統覆盤的時數」 | 無自動訊號——需你自己誠實記錄（此條為半裝飾，訊號成本高，可棄用） |

---

## 3. 行銷 / GTM（本節全部為**假設生成**，每條需 user 驗證後才可當真）

**目標客群一句話**【需驗證】：用 BingX/幣安做合約短線、月交易 20+ 筆、吃過「情緒化交易」虧、看得懂中文的散戶。

### 角色 × 痛點 × 滿足度
| 角色 | 痛點 | 本系統滿足度 |
|---|---|---|
| 合約短線散戶 | 不知道自己為什麼虧 | 🟢 覆盤評分＋虧損分析是核心強項 |
| 同上 | 想要自動下單、掛機賺錢 | 🔴 **滿足不了**——無下單執行，也不該做（見 §6 不做清單） |
| 策略開發者 | 要快速回測想法 | 🟡 可用但 freqtrade/vectorbt 更強，此處無優勢 |
| 交易新手 | 想要「保證獲利的策略」 | 🔴 **滿足不了**——沒有工具能，且這群人是客訴主力，應主動排除 |
| 多交易所用戶 | OKX/Bybit/門羅… | 🔴 **滿足不了**——只有 Binance/BingX |
| 紀律型交易者 | Kelly 倉位、傾斜檢測 | 🟢 quantitative_risk 模組覆蓋，且是差異化點 |

### 前 3 個獲客通路假設【全部需驗證】
1. 中文加密 Telegram/Discord 群的覆盤內容分享——成本：時間；風險：廣告味重被踢。
2. Threads/X 上連載「我的交易評分系統抓到我哪些壞習慣」——成本：低；最符合信任鏈。
3. YouTube/部落格長文 SEO（「BingX 交易紀錄 分析」這類長尾）——成本：中；見效慢。

**核心訊息主張**【需驗證】：「不是給你策略，是讓你看見自己交易裡的壞習慣——自動評分每一筆真實交易。」

---

## 4. 架構評估

### 4.1 該修的（依嚴重度；實作規格見 IMPL_SPECS.md）
1. **月報邊界 bug（實測抓到）**：`src/analysis/review_system.py:273` 用 `<= end_date`（閉區間），而 daily/weekly/monthly 報告的 end_date 全是「下一期起點」→ 期界整點的交易被**重複計入兩期**。本次實跑 hypothesis 測試 `test_monthly_report_time_range` 直接抓到（2026-07-09）。一字修復＋回歸測試。
2. **覆盤資料無備份且唯一 git 快照已損毀**：`quality_scores.json` 被 `.gitignore` 的 `*.json` 規則排除；git 內僅存的 `.backup` 是截斷壞檔。這是**全系統唯一不可重建的資料**。
3. **LICENSE 缺檔**：公開 repo、README 掛 MIT badge、GitHub API 回 `license: null`。法律上「All rights reserved」與宣稱矛盾。
4. **無 CI**：`.github/workflows` 不存在。測試套件其實健康（本次實跑 85+ pass），沒 CI 等於白養。
5. **對外敘事失真**：`pyproject.toml` 描述寫「支持…實盤交易」但無下單代碼；`web_dashboard.py:404` 還在講已被取代的 `bingxHistory` 目錄慣例；README 只文件化 v2 但 v1 儀表板與啟動腳本並存。
6. **無測試覆蓋的核心模組**：`market_analyzer.py`（1077 行，所有即時功能的資料來源）、`pattern_detector.py`（742 行）、`config_manager.py`（577 行）零直接測試。

### 4.2 不要做的優化（負 ROI 清單）
- **不要遷移到 freqtrade/vectorbt**：紅海模組已經寫完且能跑，遷移只在走路線 C 且引擎維護成本失控時才考慮。
- **不要做自動下單**：合規、資安、爆倉風險全面升級，且與「覆盤紀律」的核心價值主張相斥。
- **不要把 JSON 儲存換 DB**：個人量級（百筆級交易）JSON 完全夠用，換 DB 純架構潔癖。
- **不要現在整併 scalping v8~v11 六個版本檔**：它們是刻意保留的凍結版本（07-08 commit 明示「複製…進 src/strategies」），adapter 只接 v11；整併有回歸風險、無收益。文件化即可。
- **不要做多交易所擴充**：每加一所是長期維護債，先確認現有兩所的閉環有在轉。
- **不要再擴 web 儀表板頁數**：v2 已 1377 行＋10 大分類，資料層（trade_history 等）反而是空的——先讓資料進來，再談界面。
- **不要追測試覆蓋率數字**：補 §4.1-6 三個模組的關鍵路徑測試即可，別為 htmlcov 百分比寫測試。

---

## 5. 替代品掃描（sonnet agent 2026-07-09 網路調研；完整來源 URL 見文末附錄）

- **①商用**：最接近的單品是 **TradesViz**（$19.99-29.99/月）——Binance+BingX 自動同步、回測、Kelly 統計、型態分析都有。交易日誌類另有 Edgewonk $197/年、Tradervue $29.95/月。圖表分析類 TrendSpider $89+/月。**無任何單一 SaaS 同時原生涵蓋 Kelly＋型態＋支撐阻力＋覆盤評分四項**。
- **②開源**：freqtrade（~52k star，活躍）、vectorbt（~8k）、jesse（~8k）、nautilus_trader（~24.5k）覆蓋回測/優化/警報；**無一內建覆盤評分**。型態識別已被 TA-Lib/pandas-ta 標準化。
- **③官方免費**：Binance 內建回測（僅 USDT-M、無 walk-forward）＋價格警報（50 個上限、90 天）≈ 本系統 15-20%。
- **④AI DIY**：ChatGPT/Claude 可在數天內逼近 7-8 成「工程外殼」；最難替代的是回測正確性（look-ahead/滑點）與長期累積的覆盤資料。
- **紅海**：回測、優化、型態、警報、儀表板。**空白帶**：四合一整合＋BingX 深度＋自有評分規則閉環。

---

## 6. 我沒想到的維度（審視後補充）

1. **開發投入 vs 交易本金的不對稱**：`system_config.yaml` 預設 `initial_capital: 1000` USDT。若真實本金是千元美金量級，45k 行系統＋數月開發的機會成本遠超過交易本身可能的獲利——這系統的真實產出可能是「學習與樂趣」，承認這點反而能做出正確的投資決策（比如：別再為它寫新功能，只用它）。
2. **AI 生成碼的維護懸崖**：三波 commit 各對應一波 AI session；docs/reports/ 有 75 個進度報告 md。當下一次 AI session 的模型/你的記憶都換了，這 45k 行裡「哪些是活的」只剩 git log 可考。本次補的 CLAUDE.md 就是為此。
3. **公開 repo 裡的個人交易資料**：`quality_scores.json.backup`、`leverage_comparison*.csv`、docs/reports/ 部分內容含真實交易績效與行為分析（「搶帽子」「缺乏耐心」）。這是公開的。你可能不在意，但這是個決定，不該是個意外——**這題需要你的判斷**。
4. **審計環境 ≠ 開發環境的結構性風險**：這次 audit 發現「工作副本是今天的 fresh clone」花了實查才確認。若未來 session 在此路徑工作並以為看到全貌，會做出錯誤判斷（已寫入 CLAUDE.md 護欄）。

---

## 7. 證據缺口（在開發機上各跑一行即可補齊）

| 缺口 | 自查指令（在你平常開發的機器、專案根目錄跑） |
|---|---|
| 警報系統是否排程在跑 | `crontab -l; launchctl list \| grep -iE 'trade\|alert'; ps aux \| grep -E 'trading_alert\|streamlit' \| grep -v grep` |
| 覆盤資料最後寫入時間（活線判準） | `ls -la data/review_history/ && python3 -c "import json;d=json.load(open('data/review_history/quality_scores.json'));print(len(d))"` |
| 市場資料 cache 規模與最後更新 | `du -sh data/market_data/ 2>/dev/null; ls -lat data/market_data/ 2>/dev/null \| head -5` |
| .env 是否存在（警報系統能否啟動） | `ls -la .env` |
| 開發機是哪台、venv 是否還健在 | `ls -d venv .venv 2>/dev/null && ./{venv,.venv}/bin/python --version` |
| logs/system.log 最後活動 | `tail -3 logs/system.log 2>/dev/null; ls -la logs/ 2>/dev/null` |

---

## 8. 功能級 Review

閉環定義：產出→被使用→產生結果。狀態依據為 git 內容物與遠端狀態（2026-07-09）；標 ❓ 處受 §7 缺口影響。

| 功能 | 商業價值 | 不足 | 閉環狀態 |
|---|---|---|---|
| 交易覆盤＋自動評分（review_system, pages/review） | ★★★ 核心差異化 | 月報邊界 bug；資料無備份 | ⚫ **曾運作已斷供**（鐵證停在 2026-02-05；之後 ❓ 需 §7 查） |
| 量化風險分析（quantitative_risk：Kelly/傾斜/破產風險） | ★★★ 差異化 | 只在有覆盤資料時有意義——上游斷則此功能空轉 | 🟡 靠人（需手動餵 trades.json 或覆盤資料） |
| 回測引擎（backtest_engine：滑點/強平/intrabar/分批TP/MFE/時間停損） | ★★ 但紅海 | 無 CI 保護；07-08 大改後只有單機測試驗證 | 🟢 運作中（07-08 commit 活躍演進＋測試通過） |
| 參數優化＋walk-forward（optimizer, strategy_selector） | ★★ 紅海 | 產出 `optimize_*.json` 的消費端（儀表板頁）在乾淨環境是空的 | ❓ 疑 🟡（產出→被使用鏈未證實） |
| K線型態識別＋支撐阻力（pattern_detector, market_analyzer） | ★ 紅海 | 兩模組共 1819 行**零直接測試** | ❓ 疑 🔴 建好未驗證使用足跡 |
| Telegram 即時警報（trading_alert_system） | ★ 紅海 | 需 .env；本 clone 無 .env、無 logs | ❓ 疑 ⚫（§7 第 1、4、6 條可判定） |
| Web 儀表板 v2（10 大分類） | ★★ 整合入口 | 依賴的 `data/trade_history/`、`data/backtest_results/`、`backtest_result_*.json` 在 clone 中全不存在→多數頁籤空白 | 🟡 靠人（要先手動跑出資料才有東西看） |
| Web 儀表板 v1 | — | 已被 v2 取代但檔案與啟動腳本並存 | 🔴 疑棄置未清 |
| CLI（backtest/optimize/live/analyze_risk） | ★ | live 模式無下單（名實不符的「live」） | ❓ 未證實使用足跡 |
| 策略庫（15 檔，含 scalping v8~v11 六版本） | ★★ | 六版本並存僅 v11 經 adapter 接入；v8~v10 是凍結標本 | 🟢（v11 經 07-08 commits 活躍接線）；v8~v10 ⚫ 凍結 |
| 資料修復工具（時區修正、缺K補齊） | ★ 運維 | 中文檔名腳本，被 docs 引用、屬現役 | ⚫ 事故驅動（曾用過，事故解決後閒置——合理） |
| 中文教學文件（新手入門/手冊/快速開始） | ★（路線 B/C 才有價值） | 與現狀有漂移（bingxHistory 殘留等） | 🟡 |

**閉環總判**：整條「回測引擎→策略驗證」的**工程閉環**是活的（07-08 還在演進）；但「交易→覆盤→評分→行為改變」的**價值閉環**鐵證停在 2 月初。系統目前更像「越蓋越好的廠房」而非「在出貨的工廠」——除非 §7 自查推翻此判斷。

---

## 9. 快速健檢清單

1. **安全**：✅ 掃過無重大問題——git 全史無 hardcoded secrets（`git log -p -G` 掃描，2026-07-09）；token 全走環境變數。次要：Streamlit 儀表板無認證且 headless 模式預設監聽所有介面（`啟動Web界面v2.sh:15` 未指定 `--server.address`）——LAN 內個人用可接受，勿暴露公網。
2. **成本結構**：✅ 外部服務月燒 $0（全免費 API＋開源件）；真實成本＝你的時間＋AI token＋Mac mini 電費。無收入，unit economics 不適用。
3. **測試/CI**：⚠️ 測試本體健康（本次實跑 Python 3.13 venv 全套：**243 pass / 1 fail / 9 skip**，唯一 fail 是真 bug 見 §4.1-1）但**無 CI**，等於每次改動都在裸奔；`market_analyzer`/`pattern_detector`/`config_manager` 共 2396 行零直接測試。產品 runtime 不呼叫 LLM，無 agent 層回歸議題。
4. **備份/DR**：🔴 **紅燈**——唯一不可重建資料（覆盤評分）被 gitignore 且 git 內僅存快照是壞檔；開發資料只在單一機器；**存放 code 的 Mac mini 磁碟 99% 滿（229G 剩 4.5G，df 實測 2026-07-09）**——磁碟滿是資料損毀的經典前奏。
5. **資料品質**：⚠️ 曾有真實時區事故（修復腳本為證）；git 內快照檔截斷損毀；活資料品質無法在本環境驗（§7 缺口 2、3）。
6. **擴充瓶頸**：✅ 個人用量下無真瓶頸。若硬要 10x：第一個爆的是 JSON 全量讀寫（review_system 每次 load 全檔）與回測引擎單核逐根迴圈——都不值得先修。
7. **依賴健康度**：⚠️ 一處脆弱——`pandas_ta` 綁 Python ≤3.13（requirements.txt 自註「3.14 無 llvmlite wheel」），6 支策略 import 它；升 Python 前必查。其餘（pandas/streamlit/python-telegram-bot）健康。平台依賴：跑在自己機器上，無平台方風險；Binance/BingX 公開端點無鑑權，額度限制與端點變動是低機率斷供源。
8. **單點依賴**：🔴 bus factor＝1（只有你＋AI session 懂它）；不可重建資料綁單一開發機；GitHub 帳號是 code 唯一異地副本。
9. **授權/法務**：⚠️ 公開 repo **無 LICENSE 檔**但 README 宣稱 MIT——矛盾需修（補檔即可）；依賴全為寬鬆授權無傳染問題；用的是交易所公開行情端點，ToS 風險低；**公開 repo 內含個人真實交易紀錄與行為分析**（§6-3，需你決定去留）。
10. **對外敘事 vs 資料流向**：⚠️ 兩處失真——`pyproject.toml:8`「支持…實盤交易」（無下單代碼）；README MIT badge（無 LICENSE 檔）。資料流真相：行情從公開 API 進、警報經 Telegram 伺服器出（交易訊號會過境 Telegram，非純本機）、runtime 零 LLM 呼叫。無「宣稱本機、實則上雲」類的高嚴重度不一致。

---

## 附錄：替代品掃描來源（sonnet agent 調研，2026-07-09）

商用：tradingview.com/pricing、coinglass.com/pricing、3commas.io/pricing、cryptohopper.com/pricing、tradervue.com/site/pricing、edgewonk.com/pricing、tradesviz.com/pricing（含 /brokers/BingX、/blog/charts-statistics-reference）、tradersync.com/pricing、trendspider.com/pricing、journalplus.co/metrics/kelly-criterion、tradezella.com/blog、usetct.io/trade-grading
開源：github.com/freqtrade/freqtrade（freqtrade.io/en/stable/hyperopt）、github.com/mementum/backtrader（停維護 2023-）、github.com/polakowo/vectorbt（vectorbt.pro）、hummingbot.org/dashboard/backtest、docs.jesse.trade/docs/notifications、github.com/Drakkar-Software/OctoBot、github.com/nautechsystems/nautilus_trader、github.com/xgboosted/pandas-ta-classic、github.com/streamlit/example-app-crypto-dashboard
官方/免費：binance.com/en/support/faq（回測與警報條目）、bingx.com/en/support/articles/13254678297881、bybit.com/en/help-center（TradingView 對接）、cryptocurrencyalerting.com/bot/telegram、github.com/hschickdevs/Telegram-Crypto-Alerts
AI DIY：tradezella.com/blog/chatgpt-claude-backtesting、dev.to/ji_ai（Claude Code 14-session 實錄）、medium.com/@aiintrading（900 小時心得）、arxiv.org/pdf/2309.17322（LLM look-ahead bias）、quantpass.org/before-ai-quantitative-trading、github.com/Willmin-wm/kalshi-claude-trading-bot、chudi.dev/blog/claude-code-production-trading-bot

註：3Commas/Cryptohopper 定價各來源不一；TradingView 免費層 Strategy Tester 可用性未能確證。
