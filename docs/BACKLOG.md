# BACKLOG — 按價值排序的交付清單

產出自 2026-07-09 全面體檢（依據見 `docs/ASSESSMENT_2026-07-09.md`，實作細節見 `docs/IMPL_SPECS.md`）。

## ⛔ 給執行 session 的護欄（weaker-model 必讀）

1. **本 session 不動手實作**——實作交給之後的普通 session 派 sonnet 照 IMPL_SPECS 的工單做。
2. **不做清單**（ASSESSMENT §4.2，動工前先對照）：不遷移 freqtrade/vectorbt、不做自動下單、不換 DB、不整併 scalping v8~v11、不加交易所、不擴儀表板頁、不追覆蓋率數字。**新需求先對照這份清單**。
3. 此 repo 是**公開的**：任何含真實交易資料的檔案不得新增進 git；secrets 永遠走環境變數。
4. `.gitignore` 排除所有 `*.json`（白名單例外見 .gitignore）——新增 JSON 資料檔預設**不會**被 git 追蹤，別誤以為已備份。
5. 你看到的工作目錄可能是 sshfs 掛載的 fresh clone（mtime 不可信、無 runtime 資料）——判斷「系統有沒有在用」前先讀 ASSESSMENT §7。
6. 測試要用 Python ≤3.13（pandas_ta 限制）；跑 `pytest --no-cov` 比預設快很多。

---

## Wave 0 — 只有 user 本人能做（其他一切的前置）

| # | 項目 | 動機 | 驗收 | 估工 |
|---|---|---|---|---|
| 0.1 | 在開發機跑 ASSESSMENT §7 的 6 條自查指令，把輸出貼給下一個 session | 功能閉環的 ❓ 全掛在這；沒有它，⚫/🔴 判定與 Wave 2 優先序都是猜的 | 里程碑（需人確認）：6 條指令輸出已提供 | 10 分鐘 |
| 0.2 | 清 Mac mini 磁碟（99% 滿，剩 4.5G） | 磁碟滿→資料損毀→覆盤資料是不可重建的 | 里程碑（需人確認）：`df -h` 顯示可用 >20G | 0.5-2h |
| 0.3 | 決定路線 A/B/C（自用/開源作品集/產品化）＋ 每週可投入時數 | Wave 2 之後的所有優先序取決於此 | 里程碑（需人確認）：路線已告知某個 session 並寫進 memory | 想清楚即可 |
| 0.4 | 決定：公開 repo 裡的個人交易資料（quality_scores.json.backup、leverage CSV、部分 docs/reports）去留 | 這是隱私決定，不該是意外（ASSESSMENT §6-3） | 里程碑（需人確認）：決定已下（保留/清除+改私有/清除歷史） | 想清楚即可 |
| 0.5 | 確認 kill criteria / 最小成功定義（ASSESSMENT §2.5）要不要採納 | 沒有活線死線，系統會永遠處於「再蓋一點」狀態 | 里程碑（需人確認） | 想清楚即可 |

## Wave 1 — 機械修繕（sonnet 可做，全部可機械驗收；規格見 IMPL_SPECS）

| # | 項目 | 動機 | 驗收（機械） | 估工 |
|---|---|---|---|---|
| 1.1 | 修月報/週報/日報期界重複計入 bug（SPEC-1） | 實跑測試抓到的真 bug；覆盤數字失真直接傷核心價值 | `pytest tests/property/test_review_system.py --no-cov` 全綠；全套測試 0 fail（三個 time-range property 測試共用此 buggy 過濾碼，修前 fail 數隨 seed 浮動，勿錨定修前數字） | S |
| 1.2 | 補 LICENSE 檔（SPEC-2） | 公開 repo 宣稱 MIT 但無檔＝法律矛盾 | `gh api repos/s0970589598/crypto_trading_system_v2 --jq .license.spdx_id` 回 `MIT`（push 後生效；本地驗收：LICENSE 存在且含 MIT 全文） | S |
| 1.3 | 對外敘事修正：pyproject 描述、CLI_README「實盤交易」章節、bingxHistory 殘留文案、README v1/v2 說明（SPEC-3） | 敘事失真（ASSESSMENT §9-10）；CLI_README 標題級宣稱「實盤交易」但 live.py:163 是 TODO stub | `git grep -c "實盤交易" pyproject.toml` = 0；`git grep -n "bingxHistory" -- 'web_dashboard*.py'` 0 hit（或該檔已歸檔）；CLI_README.md live 章節含「無自動下單」聲明 | S |
| 1.4 | GitHub Actions CI：push 時跑 pytest（SPEC-4） | 243 個綠測試沒 CI 等於白養 | `.github/workflows/test.yml` 存在；（push 後）Actions 頁首跑綠 | S |
| 1.5 | 死檔歸檔：trading_alert_system.py.backup、system_config.yaml.bak、web_dashboard.py(v1)＋啟動Web界面.sh、清除全部評分.py → `_Archive/`（SPEC-5） | 降低未來 session 誤讀 v1 為現役的機率 | 根目錄 `ls` 無上述檔案；`_Archive/Code_20260709/` 含之；全套測試無新 fail | S |

## Wave 2 — 資料安全與測試地基（sonnet 可做；1 項需 user 配合）

| # | 項目 | 動機 | 驗收 | 估工 |
|---|---|---|---|---|
| 2.1 | 覆盤資料備份腳本＋排程建議（SPEC-6）——**目的地需 user 決定**（⚠️ 不得是本公開 repo） | 唯一不可重建資料目前零備份、git 快照已損毀 | 腳本存在且 dry-run 輸出正確；排程掛載為里程碑（需人確認） | S |
| 2.2 | `market_analyzer.py` 關鍵路徑測試（離線 fixture，不打真 API）（SPEC-7） | 1077 行、所有即時功能的資料源、零測試 | 新測試檔存在、`pytest tests/unit/test_market_analyzer.py --no-cov` 全綠、不需網路 | M |
| 2.3 | `pattern_detector.py` 黃金樣本測試（SPEC-7 附帶） | 742 行零測試；型態誤報直接影響警報可信度 | 同上模式 | M |
| 2.4 | 修復/重建 `quality_scores.json.backup` 壞檔（若開發機活檔健在則以活檔重出快照；否則標記損毀並歸檔） | git 內唯一覆盤快照是截斷 JSON | `python3 -c "import json;json.load(open(...))"` 不拋錯，或壞檔已移 _Archive 並留 README 說明 | S |
| 2.5 | 回測引擎 look-ahead 黃金案例測試（SPEC-8） | 「回測正確性」被本體檢列為唯一護城河，但 07-08 引擎大改後無專門的未來函數防護驗證——體檢本身也沒抽驗這塊（自驗 agent 指出的盲點） | `pytest tests/unit/test_backtest_lookahead.py --no-cov` 全綠；測試含「訊號產生於 bar i、成交不得早於 bar i+1 open」斷言 | M |

## Wave 3 — 條件觸發（先完成 Wave 0.3 再議）

- 路線 B（開源作品集）：英文 README、清個人資料（0.4 的執行）、範例資料集、screenshot。估 M-L。
- 路線 C（產品化）：先做 ASSESSMENT §2.4 的「第一塊錢」付費意願測試——**在寫任何新 code 之前**。
- 路線 A（自用）：Wave 2 完成後即凍結功能開發，只修 bug；把時間花在「用」不是「蓋」。

---

## 啟動提示詞（給下一個 session 直接貼）

### 場景 1：執行 Wave 1 機械修繕
```
讀 docs/BACKLOG.md 的護欄與 Wave 1、docs/IMPL_SPECS.md 的 SPEC-1~5。
逐項把 SPEC 末尾的委派工單用 Agent tool 派給 sonnet（model 顯式填 "sonnet"，一張工單一個 agent）。
依賴順序（不可全並行）：
  批次一（可並行）：SPEC-1(=1.1)、SPEC-2(=1.2)、SPEC-5(=1.5)
  批次二（批次一驗收過後）：SPEC-3(=1.3，依賴 SPEC-5 決定 web_dashboard.py 是否已歸檔，且與 SPEC-5 動同檔不可同時跑)、
                            SPEC-4(=1.4，前置 SPEC-1 已合入)
每個 agent 回報後，你本人獨立複驗至少 1 條驗收條件（實跑指令），再進下一批。
全部完成後：跑全套 `pytest --no-cov`（需 Python ≤3.13 venv），確認 0 fail（勿錨定 pass 數字，
  time-range property 測試在修復前為非決定性），然後只 commit 這些變更（訊息前綴 "Wave1:"），不 push。
遇到 SPEC 標 ⚠️待驗 的點：按 SPEC 內指示現場驗證，驗不過就停下回報，不硬做。
```

### 場景 2：user 環境自查（需要你本人在開發機上跑）
```
我要補 2026-07-09 體檢的證據缺口。請在你平常開發這專案的機器上、專案根目錄，
跑 docs/ASSESSMENT_2026-07-09.md §7 表格裡的 6 條指令，把原始輸出全部貼給我。
我會據此更新功能閉環判定（哪些功能真的在用 vs 建好沒用）、修正 BACKLOG 優先序，
並把結論寫進 memory。不會動任何 code。
```

### 場景 3：複審驗收（Wave 1/2 執行完後）
```
用 /fable-review 或以下工單複審：
讀 docs/ASSESSMENT_2026-07-09.md、docs/BACKLOG.md、docs/IMPL_SPECS.md，
對照最近的 commits（git log --oneline -15）與 git diff。
逐條 Wave 1/2 驗收條件實跑驗證（pass/fail 附輸出）；
抽驗 SPEC 修改點的 file:line 是否照規格；
找「改了 A 弄壞 B」：全套 pytest --no-cov 對照基線 243 pass/9 skip/1 fail(1.1 修後應 244+ pass)。
只回差距清單與總判定（ship / fix-then-ship / rework），不動手修。
```
