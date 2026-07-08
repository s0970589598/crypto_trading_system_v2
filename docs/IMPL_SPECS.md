# IMPL_SPECS — Wave 1/2 實作規格

配合 `docs/BACKLOG.md`。每個 SPEC 末尾附可直接貼 Agent tool 的委派工單（`model: "sonnet"`）。
通用鐵則：一張工單一件事；範圍外發現只回報不動手；回報必附 `git diff --stat` 原文。
測試環境：需 Python ≤3.13（pandas_ta 限制）。建議 `uv venv --python 3.13 && uv pip install -r requirements.txt`，跑 `pytest --no-cov` 提速。
基線（2026-07-09 實測）：`pytest --no-cov` → **243 passed, 1 failed（test_monthly_report_time_range，即 SPEC-1 要修的）, 9 skipped**。
⚠️ 基線注意：tests/property/test_review_system.py 的三個 time-range property 測試（daily/weekly/monthly）共用同一段 buggy 過濾碼，hypothesis 隨機化下修前 fail 數可能是 1~3（隨 seed 浮動）。**驗收一律以「修後 0 fail」判定，勿錨定修前 pass 數字**。
執行順序依賴：SPEC-4 前置 SPEC-1；SPEC-3 與 SPEC-5 動同一檔（web_dashboard.py），先跑 SPEC-5 再跑 SPEC-3，不可並行。

---

## SPEC-1：報告期界重複計入 bug

**插入點**：`src/analysis/review_system.py:273`
**現況**：
```python
if not (start_date <= trade.entry_time <= end_date):
```
**改為**：
```python
if not (start_date <= trade.entry_time < end_date):
```
**理由**：三個報告生成器的 `end_date` 全是「下一期起點」（daily `+timedelta(days=1)` :383-384、weekly `+timedelta(days=7)` :397、monthly 次月 1 日 :409-413），閉區間使期界整點交易被兩期重複計入。hypothesis 測試 `tests/property/test_review_system.py::test_monthly_report_time_range` 已抓到（falsifying example：2024-02-01 00:00 進了 1 月報告）。
**雷區**：
- 第二個呼叫者 `export_data`（review_system.py:555）語意會從閉區間變半開——屬一致化，可接受，但工單要在回報中明述此行為變更。
- 修完先單跑該 property 測試，再跑全套確認無其他測試依賴閉區間行為。

**委派工單**：
```
目標：修 src/analysis/review_system.py:273 的期界 off-by-one（閉區間→半開區間）。
動機：daily/weekly/monthly 報告的 end_date 均為下一期起點，現行 `<= end_date` 使期界整點
  交易重複計入兩期；hypothesis 測試 test_monthly_report_time_range 已實抓到此 bug。
規格：`start_date <= trade.entry_time <= end_date` → `start_date <= trade.entry_time < end_date`；
  並在該行上方加一行註解說明半開區間慣例 [start, end)。
檔案白名單：src/analysis/review_system.py（僅此一檔；docstring 若提到日期範圍可同步改）。
禁止：動 generate_*_report 的 end_date 計算；動 export_data；其他重構。
驗收條件（可機械驗證）：
  1. `pytest tests/property/test_review_system.py --no-cov -q` 全綠
  2. `pytest --no-cov -q` 全套 0 fail（勿錨定 pass 數字——修前 fail 數隨 hypothesis seed 浮動 1~3）
回報格式：status / changed_files / 兩條驗收的實際輸出末 3 行 / git diff --stat 原文 /
  明述 export_data 語意連帶變為半開區間。
```

---

## SPEC-2：補 LICENSE 檔

**插入點**：repo 根目錄新檔 `LICENSE`
**內容**：標準 MIT 全文。版權行：`Copyright (c) 2026 s0970589598`
　⚠️ 待驗：署名要用 GitHub ID 還是真名——執行時先問 user，問不到就用 GitHub ID `s0970589598`（可日後改）。
**雷區**：無。純新增檔案。

**委派工單**：
```
目標：在 repo 根目錄新增標準 MIT LICENSE 檔。
動機：公開 repo，README 掛 MIT badge，但 GitHub API 回 license:null——宣稱與法律狀態矛盾。
規格：標準 MIT License 全文（英文），版權行 `Copyright (c) 2026 s0970589598`。
檔案白名單：LICENSE（新增）。
驗收條件：1. LICENSE 存在且首行為 "MIT License"；2. 含 "Permission is hereby granted" 全文段。
回報格式：status / git diff --stat 原文。
```

---

## SPEC-3：對外敘事修正

**修改點**：
1. `pyproject.toml:8`：`description = "可擴展的多策略交易系統，支持回測、優化和實盤交易"` → `"可擴展的多策略交易系統，支持回測、優化與交易覆盤（純訊號分析，無自動下單）"`。
1b. `CLI_README.md`「實盤交易命令」章節（:5/:99/:101 附近）：章節標題與內文補明確聲明「live 模式僅行情監控與訊號，無自動下單（cli_commands/live.py:163 為 TODO stub）」——該檔 :103 已有部分警語，強化為顯眼聲明即可，不重寫章節。
2. `web_dashboard.py:404` 附近的「請確保 bingxHistory 目錄中有…」文案：改為指向現行上傳流程（pages/review/record_management.py 的 file_uploader → `data/review_history/bingx/orders/`）。⚠️ 待驗：若 SPEC-5 已把 web_dashboard.py 歸檔則此點跳過。
3. `README.md`：在「Web 界面 v2」段落附近補一句「v1（web_dashboard.py）已由 v2 取代」（若 SPEC-5 已歸檔 v1，改為刪除對 v1 的殘留引用）。
4. `項目清單.txt:58`、`docs/reports/項目結構.md:47` 的 bingxHistory 條目：加註「（已改為 Web 上傳流程，此目錄慣例已廢）」——docs/reports/ 屬歷史紀錄，僅加註不刪。
**雷區**：README 其餘宣稱（K線型態、量化風險等）經盤點屬實，勿動；別把「修正敘事」擴大成重寫 README。

**委派工單**：
```
目標：修正 5 處對外敘事失真（清單見 docs/IMPL_SPECS.md SPEC-3，含逐點的修改前後文字）。
動機：pyproject 與 CLI_README 宣稱「實盤交易」但 live.py:163 是 TODO stub、repo 無下單代碼；
  bingxHistory 目錄慣例已被 Web 上傳流程取代。
檔案白名單：pyproject.toml、CLI_README.md、web_dashboard.py、README.md、項目清單.txt、docs/reports/項目結構.md。
備註：tests/unit/test_scalping_v11_integration.py:5 的 bingxHistory 是歷史敘述註解，留著即可，不在修正範圍。
禁止：重寫 README 其他段落；動任何 .py 邏輯（web_dashboard.py 只准改字串文案）。
順序注意：若同 wave 的 SPEC-5 已把 web_dashboard.py 移入 _Archive，第 2 點改為在歸檔副本原地不動、跳過。
驗收條件：
  1. `grep -c "實盤交易" pyproject.toml` = 0
  2. `git grep -n "bingxHistory" -- 'web_dashboard*.py'` 0 hit（或該檔已歸檔）
  3. `pytest --no-cov -q` 無新增 fail
回報格式：status / changed_files / 驗收輸出 / git diff --stat 原文。
```

---

## SPEC-4：GitHub Actions CI

**插入點**：新檔 `.github/workflows/test.yml`
**草稿**：
```yaml
name: tests
on:
  push: { branches: [main] }
  pull_request:
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.13" }   # pandas_ta 無 3.14 wheel，勿升
      - run: pip install -r requirements.txt
      - run: pytest --no-cov -q --hypothesis-seed=0   # 固定 seed 防 property 測試在 CI flaky
```
**雷區**：
- `pytest.ini` 的 addopts 帶 `--cov`＋hypothesis 統計，CI 用 `--no-cov` 覆蓋即可（實測全套 ~4-9 分鐘，可接受）。
- SPEC-1 未修前 CI 會紅（1 fail）——**先做 SPEC-1 再上 CI**，或首版工作流照上、註明預期紅。
- ⚠️ 待驗：hypothesis property 測試在 CI 環境的耗時與 flakiness——首跑觀察，若超時再加 `--ignore=tests/property` 的快速 job 拆分（不要現在預先優化）。

**委派工單**：
```
目標：新增 .github/workflows/test.yml（內容照 docs/IMPL_SPECS.md SPEC-4 草稿）。
動機：243 個測試無 CI 保護，改動全裸奔。
前置：確認 SPEC-1 已合入（否則 CI 首跑必紅）；未合入就停下回報。
檔案白名單：.github/workflows/test.yml（新增）。
驗收條件：
  1. 檔案存在且 `python-version: "3.13"`（含勿升 3.14 註解）
  2. 本地模擬：`pip install -r requirements.txt && pytest --no-cov -q` 全綠（在 3.13 venv）
回報格式：status / git diff --stat 原文。備註：Actions 實跑綠燈需 push 後才能驗，標為里程碑。
```

---

## SPEC-5：死檔歸檔

**動作**（全部 `git mv` 到 `_Archive/Code_20260709/`，沿用既有 `_Archive/Code_20260211/` 慣例）：
- `trading_alert_system.py.backup`（重構前存檔，無 code 引用）
- `system_config.yaml.bak`（備份殘留）
- `web_dashboard.py` ＋ `啟動Web界面.sh`（v1，已被 v2 取代；README 僅文件化 v2）
- `清除全部評分.py`（git grep 0 引用的孤立腳本）
**雷區**：
- `web_dashboard.py` 被 `恢復核心工具.sh` 或其他腳本引用與否——工單內先 `git grep -l "web_dashboard.py"` 排查，有現役引用就停下回報。
- 中文檔名腳本（快速查看.py 等）**是現役**（被 docs 與 pages/trading/live_market_analysis.py 引用），**不在歸檔清單**。
- 歸檔目錄加一個 `README.md` 說明歸檔原因與日期。

**委派工單**：
```
目標：把 4+1 個棄置檔 git mv 進 _Archive/Code_20260709/（清單與前置排查見 docs/IMPL_SPECS.md SPEC-5）。
動機：v1 儀表板與 .backup/.bak 殘留會誤導未來 session 判斷哪版是現役。
前置排查：git grep -l 逐一確認每個待歸檔檔案無現役引用（引用者若只有 docs/reports/ 或 _Archive/ 屬歷史紀錄，不算現役）；
  有現役引用的檔案跳過並回報。
檔案白名單：上述待歸檔檔案、_Archive/Code_20260709/*（新增 README.md 說明）。
禁止：刪檔（只准 git mv）；動中文檔名工具腳本（現役）。
驗收條件：
  1. 根目錄 `ls trading_alert_system.py.backup system_config.yaml.bak web_dashboard.py 清除全部評分.py` 全部 no such file（跳過者除外）
  2. `pytest --no-cov -q` 無新增 fail
  3. `git status` 顯示為 rename 而非 delete+add 不強求，但 git log --follow 可追
回報格式：status / 每檔「歸檔 or 跳過＋引用者」/ git diff --stat 原文。
```

---

## SPEC-6：覆盤資料備份腳本

**插入點**：新檔 `tools/backup_review_data.py`
**規格**：把 `data/review_history/`（含 quality_scores.json、bingx/）打包成 `review_backup_YYYYMMDD_HHMMSS.tar.gz` 到目的地目錄；保留最近 N 份（預設 30）；`--dry-run` 只列印動作；目的地由 `--dest` 或環境變數 `REVIEW_BACKUP_DEST` 指定，**無預設值、未指定即報錯**（防止誤寫進公開 repo）。
**草稿骨架**：
```python
#!/usr/bin/env python3
"""備份 data/review_history/（覆盤評分＝全系統唯一不可重建資料）到 repo 外目的地。"""
import argparse, os, sys, tarfile, time
from pathlib import Path

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dest", default=os.environ.get("REVIEW_BACKUP_DEST"))
    p.add_argument("--keep", type=int, default=30)
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()
    if not a.dest:
        sys.exit("未指定備份目的地（--dest 或 REVIEW_BACKUP_DEST）；禁止備份進本 repo（公開）")
    src = Path(__file__).resolve().parent.parent / "data" / "review_history"
    dest = Path(a.dest).expanduser()
    if dest.resolve().is_relative_to(src.parent.parent):
        sys.exit("目的地不得在 repo 內（repo 是公開的）")
    name = f"review_backup_{time.strftime('%Y%m%d_%H%M%S')}.tar.gz"
    if a.dry_run:
        print(f"[dry-run] would create {dest/name} from {src}"); return
    dest.mkdir(parents=True, exist_ok=True)
    with tarfile.open(dest / name, "w:gz") as tf:
        tf.add(src, arcname="review_history")
    backups = sorted(dest.glob("review_backup_*.tar.gz"))
    for old in backups[:-a.keep]:
        old.unlink()
    print(f"OK: {dest/name}（現存 {min(len(backups), a.keep)} 份）")

if __name__ == "__main__":
    main()
```
⚠️ 待驗：`is_relative_to` 的 repo 根判定在 symlink/sshfs 下的行為——工單內以 dry-run 實測兩種目的地（repo 內應拒、repo 外應過）。
**排程**（launchd/cron 掛載）只有 user 能做——BACKLOG 2.1 標里程碑；工單只交付腳本＋一行建議 crontab。

**委派工單**：
```
目標：新增 tools/backup_review_data.py（規格與骨架照 docs/IMPL_SPECS.md SPEC-6，可修 bug 但不可簡化防呆）。
動機：data/review_history/ 是全系統唯一不可重建資料，目前零備份且 git 內快照已損毀；repo 公開，
  備份絕不可落在 repo 內。
檔案白名單：tools/backup_review_data.py（新增）。
驗收條件（在暫存目錄實測）：
  1. 未給 --dest → exit code ≠0 且訊息含「未指定」
  2. --dest 指向 repo 內路徑 → exit code ≠0 且訊息含「不得在 repo 內」
  3. --dest /tmp/xxx --dry-run → 印出 would create 且不產生檔案
  4. 實跑一次 → tar.gz 存在且 `tar -tzf` 列出 review_history/ 內容
回報格式：status / 4 條驗收實際輸出 / git diff --stat 原文。
```

---

## SPEC-7：market_analyzer / pattern_detector 測試

**目標**：不打真 API 的離線測試。
**插入點**：新檔 `tests/unit/test_market_analyzer.py`、`tests/unit/test_pattern_detector.py`；fixture 放 `tests/fixtures/`（目錄已存在）。
**規格**：
- market_analyzer：mock `requests.get`（klines 端點在 `src/analysis/market_analyzer.py:244`），驗證 ①K線解析欄位/型別 ②API 錯誤/空回應的降級行為 ③時區處理（曾有真實時區事故，重點）。
- pattern_detector：手工構造 3-5 個黃金樣本 OHLCV 序列（明確的避雷針/假突破/頭肩頂），驗證偵測有命中；再加 1 個「無型態」序列驗證不誤報。
⚠️ 待驗：兩模組的公開介面簽名（本次未逐函式細讀）——工單第一步是先讀模組列出 public methods 再寫測試，不准照猜的簽名寫。
**雷區**：pattern 判定閾值可能對樣本敏感——黃金樣本要造得誇張明確，別造邊界樣本（那是之後的事）。

**委派工單**：
```
目標：為 src/analysis/market_analyzer.py 與 src/analysis/pattern_detector.py 各建一個離線單元測試檔
  （範圍與重點照 docs/IMPL_SPECS.md SPEC-7）。
動機：共 1819 行、即時功能的資料源與警報依據，目前零直接測試。
第一步：先讀兩模組，列出實際 public 介面，再寫測試——嚴禁照猜的簽名寫。
檔案白名單：tests/unit/test_market_analyzer.py、tests/unit/test_pattern_detector.py、tests/fixtures/ 下新 fixture。
禁止：改 src/ 任何檔（發現 bug 只回報）；測試中發真實 HTTP 請求。
驗收條件：
  1. 測試全程 mock requests、不發任何真實 HTTP，且 `pytest tests/unit/test_market_analyzer.py tests/unit/test_pattern_detector.py --no-cov -q` 全綠
  2. 每檔 ≥5 個測試、含至少 1 個負樣本（錯誤回應/無型態）
  3. 全套 `pytest --no-cov -q` 無新增 fail
回報格式：status / 新增測試清單（一行一個，說驗了什麼）/ 驗收輸出 / git diff --stat 原文 /
  若讀碼時發現 src bug，列出但不修。
```

---

## SPEC-8：回測引擎 look-ahead 黃金案例測試（BACKLOG 2.5）

**動機**：「回測正確性」是本專案唯一被判定為護城河的能力（ASSESSMENT §5），且引擎在 2026-06-13 才修過同根 look-ahead（commit「Phase A1: 回測引擎加滑點 + 修同根 look-ahead（next-open 成交）」）、07-08 又大改（時間停損/跨交易回饋）——需要一個直接針對「未來函數」的守門測試，而非只靠泛用 property 測試。
**插入點**：新檔 `tests/unit/test_backtest_lookahead.py`
**規格**：手工構造一段價格劇本（例如 bar i 收盤觸發進場訊號、bar i+1 跳空開高），斷言：
1. 成交價 = bar i+1 的 open（含滑點方向正確），**絕不是** bar i 的 close；
2. bar i 當根的 high/low 不影響該筆的止損/止盈觸發（同根不觸發）；
3. 構造「訊號依賴未來資料才會出現」的對照組，確認引擎介面拿不到未來 bar。
⚠️ 待驗：backtest_engine 的實際進場/出場 API 與既有測試寫法（tests/property/test_backtest_engine.py 等）——工單第一步先讀既有測試照其構造模式寫，嚴禁照猜的簽名寫。
**雷區**：滑點與手續費會讓成交價 ≠ 精確 open，斷言用「等於 open±滑點容差」而非硬等值。

**委派工單**：
```
目標：新增 tests/unit/test_backtest_lookahead.py——回測引擎未來函數守門測試（規格照 docs/IMPL_SPECS.md SPEC-8）。
動機：回測正確性是本專案護城河，引擎剛大改過，需要直接針對 look-ahead 的黃金案例防護。
第一步：先讀 src/execution/backtest_engine.py 與 tests/property/test_backtest_engine.py，
  照既有測試的構造模式寫，嚴禁照猜的簽名寫。
檔案白名單：tests/unit/test_backtest_lookahead.py（新增）、tests/fixtures/ 下新 fixture（如需要）。
禁止：改 src/ 任何檔（發現疑似 look-ahead bug 只回報，附重現劇本）。
驗收條件：
  1. `pytest tests/unit/test_backtest_lookahead.py --no-cov -q` 全綠且 ≥3 個測試
  2. 含「訊號 bar 的 close 成交」反例斷言（即若引擎回退到同根成交，此測試必紅）
  3. 全套 `pytest --no-cov -q` 0 fail
回報格式：status / 測試清單（各驗什麼）/ 驗收輸出 / git diff --stat 原文。
```
