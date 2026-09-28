# RECON：ledgerwash v0.1 對 EC 帳本對帳結報

- 日期：2026-09-28。工具身份：ledgerwash 0.1.0（spec 1）。PREREG：[PREREG.md](PREREG.md)（commit `123fcc6`，掃描前釘死，預測未動）。
- 目標：`dev/estate-consolidation` @ `b8761e95`（round 0 同一 SHA；全程唯讀，epoch 讀取不 checkout）。
- 證據：[run3.json](run3.json)＋[run4.json](run4.json)——同一指令雙跑，**byte-identical**。
- verdict 口徑：本輪以 `--fail-on critical` 跑（pass）；**default（`--fail-on high`）→ block**，唯一 high 即 T-292 時序倒掛。

## 誠實紀錄：工具在 PREREG 之後、正式對帳之前修了三個缺陷

首次掃描（目標 `estate` clone，run1/run2）暴露三個工具缺陷，修復後才得到正式對帳 run3/run4。預測本身一字未改：

1. **排序鍵崩潰**：EC 真有缺 `recorded_at` 的收據，`(parse_ts(...), name)` 對 None 與 datetime 比較拋 TypeError（fixture 蓋不到）；修為 `ts_or_min`。
2. **crash 以 exit 1 收場**違反 SPEC §6——CLI 兜住所有未預期例外轉 exit 2，新增凍結閘 A6。
3. **目錄存在性**：`evidence/hosts/` 這類帶尾斜線的目錄引用被誤判懸空（round 0 的 worktree `exists()` 對目錄為真）；`path_exists` 剝尾斜線，補 fixture 對照。

## 預測對帳（PREREG 13 條）

| # | 預測 | 實際 | 判定 | 歸因 |
|---|---|---|---|---|
| P1 | `DANGLING_REF`=61 且路徑**集合相等** | 61；與 round 0 的 61 唯一死路徑 0 缺 0 多 | **held** | — |
| P2 | `STATUS_STATE_MISMATCH`=0 | 0 | **held** | CJK 正規化殲滅 round 0 的 60 筆雜訊 |
| P3 | `TIMELINE_INVERSION`=1 且 T-292 在內 | 1；收據 `c8d5a3b2…` task_id=**T-292**，`07:12:17Z < 09:55:00Z` 與 round 0 逐字一致 | **held** | 註：locator 未含 task_id（v1.1 候選） |
| P4 | `FP_HASH_MISMATCH`=0 | 0 | **held** | 9 筆 pre-image pin 由 `expected-head-blob` 契約錨吸收，era-valid 通過 |
| P5 | `FP_SOURCE_MISSING`=0 | 0 | **held** | 23 筆搬遷收據 birth-era-valid |
| P6 | pin 聯集覆蓋 20/20，合計 ∈[20,40] | 25（20/20 覆蓋＋5 新增） | **held** | 5 新增＝黏在中文後的裸 SHA（`…squash至main39ed4df9…`），round 0 的 `\b` 邊界抓不到、hex 邊界抓得到 |
| P7 | `POST_HOC_DRIFT`=0 | 0 | **held** | EC 的 type-strict 操作鏈防線有效 |
| P8 | `CHAIN_BREAK`=0 | 0 | **held** | — |
| P9 | `CONTRACT_UNDOCUMENTED` ≥9 | 4 | **not-held（良性）** | 機制比預測好：9 筆 pre-image pin 的 `(hash_format, origin)` 在契約表內（`expected-head-blob`），直接 era-valid、無需警示。4 筆＝3 張 2026-09-10 schema-1 收據**整個缺 `origin` 欄位**（4 個 fingerprint entry），bytes 於 birth 側吻合——「證據有效但契約未宣告」，第十類的機械形態 |
| P10 | `TIMESTAMP_MALFORMED`=0（低信心，探查項） | 112 | **not-held（新類）** | 112 筆**全部是任務 `time` 欄**：`2026-07-27T15:2xZ` 型 x-遮蔽（105 個相異值）與 `A → B` 區間——EC 舊時代的 redaction 慣例。round 0 的 C9 只看收據、scan.py 對壞時間戳静默跳過，此類是 round 0 結構上的盲區。分類：**慣例性遮蔽，非弱化**；v1.1 應給 x-遮蔽獨立規則（info `TIMESTAMP_REDACTED`） |
| P11 | 總數 ∈[80,140] | 203 | **not-held（P10 算術後果）** | 203 = **91**（round-0 對位）＋112（redaction 類）。排除 P10 類後**恰為 91，與 round 0 人判 91 相等** |
| P12 | 雙跑 byte-identical | True | **held** | — |
| P13 | PIN 用語紀律（無 failed/dead/broken） | 0 違規 | **held** | — |

**計分：10 held / 3 not-held；三個 not-held 全數歸因（良性機制升級×1、新類×1、算術後果×1），無一歸因於規則語意錯誤。**

## 頭條

**v0.1 的機械輸出＝91 筆，與 round 0 的人判 91 筆真實實例精確對位**：61 懸空（集合相等）＋25 pin（20/20 覆蓋＋5 新增）＋1 時序（T-292）＋4 契約缺口。同一 corpus 上，round 0 的 naive 掃描是 205 raw、約 98% 誤報——十二條規則把人工判定蒸餾成了規則集，外加浮出 112 筆 round 0 結構上不可能看見的時間戳品質類。

## 對帳過程的新發現

- **D2｜clone 完整性本身就是審計變數**：`estate` clone（非 shallow）對 79 張收據找不到出生 commit（例：`0073faa1…` 的 birth `f44fdcbd…` 只存在於 dev clone）；dev/estate-consolidation 全數可達。同一釘死 SHA、不同本地 clone、審計能力不同——round 0 教訓 3（釘死驗證本地性）的升級版：**birth map 依賴 clone 完整性**。v0.1 對此以 79 筆 residual 如實回報、不静默；run1/run2（estate 目標）據此作廢。
- **D3｜pin 引用的邊界語意**：hex 邊界正則優於 word boundary（P6 的 5 筆新增）。
- **D4｜redaction 慣例**：見 P10；`2026-09-05T19:12:50Z → 2026-09-07T07:00:19Z` 區間寫法同屬此類。

## v1.1 候選（待人類裁量，未動工）

1. TIMELINE/CHAIN 類 finding 的 locator 帶 task_id（T-292 直接可讀）。
2. x-遮蔽時間戳 → 獨立 `TIMESTAMP_REDACTED`（info），與真 malformed 分流。
3. 契約表**不**收編「缺 origin 欄位」形態——「契約未宣告」本身就是 finding，保留。

## 重現

```powershell
cd backlog/evidence-audit/ledgerwash
uv run python -m pytest          # 30 passed
uv run ledgerwash qualify        # 12 rules fire exactly as planted
uv run ledgerwash scan C:\Users\nelson\dev\estate-consolidation --at b8761e95 --fail-on critical
```

判決句範例（SPEC §8）：`block @ ledgerwash 0.1.0, spec 1, epoch b8761e95…, adapter ec-ledger, exit 1（default fail-on high；1 high = T-292 TIMELINE_INVERSION）`。

---

# Addendum（2026-09-28 review pass，人類指示「你來 review 繼續」）

## Review 發現與修復（spec 2，v0.2.0，commit `7b4cbda`）

把 S3 交付當外部代碼重審，修了五項、新增一條規則：

1. **空帳本静默 pass（誠實度缺陷）**：對任意無帳本 git repo 掃描會得到 0 findings＋pass，看起來像「帳本乾淨」。修：空 tasks／receipts 目錄各記一筆 residual（SPEC §3 明文：no-ledger ≠ clean-ledger），凍結閘 A9 釘死。
2. **anchor 未過濾 commit 型別**：`expected_head` 若為 blob/tree SHA，`blob_at` 必敗、會偽報 `FP_SOURCE_MISSING`。修：anchor 解析改 commit-only 批次（`Epoch.commits`），非 commit anchor 走 residual。
3. **redaction 分流**：新增第十三條凍結規則 `TIMESTAMP_REDACTED`（info）——x-遮蔽與 `A → B` 區間是 EC 舊慣例、非弱化；真 malformed 維持 warn。rule count 12→13。
4. **TIMELINE locator 帶 task_id**：對帳時 T-292 要靠人工對收據；現在 locator/message 直接是 `T-292:c8d5a3b2…`。
5. **整潔**：drift.py／test_gates.py 多餘 import、測試 helper 位置。

Review 過程中 redaction 偵測正則收緊了兩次（誠實紀錄）：先放寬到 `THH:M`（分鐘部分被遮的 `15:2xZ`）、再放寬到日期層級（時間整段被遮的 `T02:xxZ`）——兩次都是 EC 真實資料教出來的。

## 調查收案（RECON 本文遺留的兩個未竟項）

- **P6 的 5 筆新增裸 SHA 全數驗證**：`squash至main3e8c8d9e…`、`Lab master758cc100…`、`工程f8e92ade…`、`承接a4acb97e…`＋原先的 T-158——全部黏在中文詞後，word-boundary 正則抓不到、hex 邊界抓得到，歸因成立（5/5）。
- **self_signing 104 vs round 0 的 100**：4 筆收據的任務 `owner` 是**空字串**（`2804f670…`、`4ba3b5ed…`、`69f5e230…`、`ac79dc54…`）——round 0 的 truthy 檢查跳過、v1 的 isinstance 檢查計入 differ。觀察值非 verdict；行為差異歸因明確，兩種語意皆可辯護，v1 維持 isinstance。

## spec 2 重跑（run5→run6，證據 `run5.json`／`run6.json`）

| 口徑 | spec 1（run3/run4） | spec 2（run6） |
|---|---|---|
| 總 findings | 203（warn 202＋high 1） | 203（info 107＋warn 95＋high 1） |
| 時間戳類 | TIMESTAMP_MALFORMED 112（全 warn） | **TIMESTAMP_REDACTED 107（info）＋TIMESTAMP_MALFORMED 5（warn，全部是中文註解黏時間戳的自由文本）** |
| round-0 對位 | 91 | 91（不變） |
| TIMELINE locator | 收據檔名 | `T-292:c8d5a3b2…` |
| residuals | 0 | 0 |

非 redaction、非 prose-timestamp 的 findings 仍為 **91，與 round 0 人判精確對位**。verdict 口徑不變：default（fail-on high）→ **block**（唯一 high＝T-292）。

判決句：`block @ ledgerwash 0.2.0, spec 2, epoch b8761e95…, adapter ec-ledger, exit 1（1 high = T-292 TIMELINE_INVERSION；203 findings = 91 對位＋107 redacted＋5 prose-timestamp）`。
