# ledgerwash 紅隊測試報告

- **日期**: 2026-10-01
- **目標**: ledgerwash v0.3.0 / spec 3（原始碼 commit `230b804`，本地 `uv run` 執行）
- **方法**: 每個案例建立一個全新的 ec-ledger git repo（.gitattributes `* -text`、兩段式 commit 讓指紋錨點成立），跑真實 CLI `ledgerwash scan <repo> --at HEAD`。**exit 0 = 消費者閘門通過 = 繞過成立**（SPEC §8 的消費者契約就是記錄 exit code）。
- **範圍界定**: S4 兩輪已實測「內部一致的精密偽造可通過」並記錄為 authenticity 邊界（docs/s4/REPORT-2.md，spec 4+ 範圍）。本輪**不打**那條邊界——專打「規則存在、但其輸入缺席或可操縱時靜默真空化」的機械可查缺口，這是工具自己的設計語彙（liveness / residual）內應該要抓的。
- **重現**: `rt2/harness.py`、`rt2/cases.py`、`rt2/results.json`、`rt2/work/<case>/`（每案的完整 repo 都留著）。

## 總結

20 案：3 個控制組全部正確 block（`NO_OPERATION_HISTORY`、`FP_HASH_MISMATCH`、`POST_HOC_DRIFT` 在欄位齊備時都是硬的）；**17 個攻擊繞過成立**，1 個攻擊被規則正確攔下（A4B，見誠實記錄）。繞過全部集中在四個根因，且彼此可堆疊——**A12「空殼帳本」單獨即為零 findings 的完全繞過**。

嚴重度口徑：**靜默**＝exit 0 且零 findings（連 residual 都沒有）；**可見**＝exit 0 帶 warn finding 或 residual（§5 明定 residual 與 observation 不影響 verdict）。

---

## 頭條：A12 空殼帳本（vacuous ledger）— 完全靜默

兩個 DONE 任務＋兩張**只含 `task_id` 和 `recorded_at` 的收據**：

```json
{"task_id": "T-100", "recorded_at": "2026-09-28T10:00:00Z"}
```

→ `verdict: pass`、**exit 0、零 findings、零 residual**。

每一條 high 規則的輸入欄位都是選配的：沒有 `source_fingerprints` 就沒有指紋驗證（fingerprints.py: `entries is None: continue`，連 residual 都不記）；沒有 `before/after_record_sha256` 就沒有 CHAIN_BREAK（timeline.py 要求兩側皆為非空字串）；沒有 `after_record` 就沒有 POST_HOC_DRIFT（drift.py: `not isinstance(after, dict): continue`）；收據存在本身滿足 NO_OPERATION_HISTORY。這是 checkwash「vacuous assertion padding」（THREATMODEL row 20/25/46）的帳本版：**證據結構在、證據內容為零，判定為乾淨**。

修補方向：收據形狀完整度檢查——一張收據若缺少全部證據欄位（指紋、鏈、after_record 至少其一），至少是 residual，收斂一點可定為新規則（`VACUOUS_RECEIPT`）。

## 根因一：缺席即靜默（optional-field liveness）

| 案例 | 拿掉的欄位 | 規則 | 結果 |
|---|---|---|---|
| A6-STRIP-FPS | `source_fingerprints` | FP_* | 靜默（連 residual 都沒有） |
| A9-STRIP-CHAIN | 第二張收據的 `before_record_sha256`（值其實與前張衝突） | CHAIN_BREAK | 靜默 |
| A11-NO-AFTER-RECORD | 錨點收據的 `after_record`（然後任意改寫任務記錄） | POST_HOC_DRIFT | 靜默 |
| A12-VACUOUS-LEDGER | 以上全部 | 全部 | 靜默 |

A9 值得強調：**把欄位拿掉比留下錯誤值更安全**——留下衝突的 sha 會被擋（控制組性質），拿掉欄位則完全靜默。攻擊者不需要讓鏈一致，只需要讓鏈不可判。

## 根因二：era 閘門錨在攻擊者宣稱的時間上

`NO_OPERATION_HISTORY` 的 era 判定 = 任務 `time` ≥ 帳本最早收據 `recorded_at`（nohistory.py）。兩個繞過＋一個毀滅性操作：

- **A2-BACKDATE-TIME**：零收據 DONE 任務的 `time` 回填到最早收據之前 →「pre-system」靜默。`time` 是攻擊者手寫的欄位，沒有任何交叉驗證。
- **A3-MALFORM-TIME**：`time` 寫成無法解析的字串 → 只有 `TIMESTAMP_MALFORMED(warn)`，era 規則靜默，exit 0。
- **A1-DELETE-RECEIPTS**：把**全部**收據刪掉 → `system_start is None` → 規則整體失效（nohistory.py 第一個 return），只剩一條「no operation receipts found」residual——而 residual 不影響 verdict。**銷毀整個證據庫的 exit code 與誠實帳本相同**。README 說「no-ledger is not a clean-ledger」，但在 §8 的 exit-code 消費契約下它就是 clean。

修補方向：(1) 任務 `time` 早於該任務檔案自身的 git birth commit 日期 → 機械可查的回填（epoch 已有 birth_map 機制，目前只用在收據上）；(2) 「tasks 存在但 receipts 為空」從 residual 升為 finding，或讓 residual 參與 verdict；(3) `time` 無法解析的 DONE 任務不應比可解析者更安靜。

## 根因三：adapter 列舉邊界外的檔案無聲消失

- **A5-RENAME-TASK**：`T-800.json` 改名 `DONE-800.json` → 不符 `T-*.json` glob → 靜默跳過（ec_ledger.py `continue`，**無 residual**）。該任務的 zero-receipt DONE、狀態矛盾全部不可見。
- **A4-SUBDIR-RECEIPT**：收據移入 `evidence/task-operations/sub/` → `list_dir` 非遞迴 → 不可見。全移＝只剩 no-receipts residual；**A4C 部分隱藏**＝把非 DONE 任務的收據藏進子目錄後任意改寫其記錄（drift 失去錨點），零 residual、exit 0。
- **誠實記錄（A4B）**：把 DONE 任務唯一收據藏進子目錄、era 由其他收據建立 → `NO_OPERATION_HISTORY` 正確攔下。規則在此形態是做對的。

修補方向：目錄列舉改為遞迴或對「目錄下有非 .json / 不符 glob 的檔案」記 residual；glob 外的 `*.json` 檔案出現在 tasks 目錄 = residual。

## 根因四：錨點選擇可被最後一張收據操縱（anchor swamp）

POST_HOC_DRIFT 只與 `max(recorded_at, filename)` 的錨點收據比對（drift.py）。攻擊：改寫任務記錄後，補一張 `recorded_at` 較晚、`after_record` 等於改寫後記錄、鏈欄位連續的「確認收據」：

- **A10 / A15-DRIFT-SWAMP**：對著會正常作動的 drift 控制組（CTL-DRIFT block）補一張 swamp 收據 → exit 0、零 findings。真實收據裡誠實的 after_record 還在 repo 裡，只是不再是錨點。

修補方向：與**所有**收據的 after_record 比對（任一張與現行記錄不一致即報），或錨點定義改為「最早之後不可被更晚收據覆寫」的不變量；起碼「存在 after_record 早於錨點且與錨點不同」應觸發。

## 次級：嚴重度設計讓「驗證降級」全部不設閘

預設 `fail_on=high`，而所有「證據變弱」類規則都是 warn——它們在預設閘門下**永不阻擋**：

- A7-UNDOC-ORIGIN：指紋 origin 改成契約表外的拼法 → `CONTRACT_UNDOCUMENTED(warn)`，摘要永不被驗證，exit 0。
- A8-GHOST-ANCHOR：`expected_head` 填一個不存在的 40-hex → `PIN_LOCAL_MISSING(warn)` ＋「unverified」residual，exit 0。
- A14-REF-GRAMMAR：任務引用 `src/proofs/t-100.csv`（不存在）→ 文法根目錄（evidence|docs|governance|tools）之外的引用**完全不查**，靜默。
- A16-DANGLING-WARN-ONLY：即使文法內的懸空引用 `evidence/results/ghost-missing.csv` 也只有 `DANGLING_REF(warn)`，exit 0。
- A13-STATUS-UNICODE：`status="✅已完成（验收通过）"`、`state="TODO"` → `normalized_head` 無 ASCII 前綴 → 規則跳過（records.py），靜默。非 ASCII status 是這個 adapter 的真實語料形態，這個 skip 是為了 CJK 語料存在的——但它的代價是 status 欄位對非 ASCII 拼寫完全失去約束力。

這一組是設計取捨而非缺陷，但組合起來的淨效果是：**把所有可驗證性拿掉（A6+A7+A8）與誠實帳本在閘門上等價**。建議至少「一個任務的全部收據皆無可驗證指紋」要有 high 級的總體檢查。

## 有被正確攔截的項目（控制組）

| 案例 | 判定 |
|---|---|
| CTL-NOHISTORY（era 內零收據 DONE） | `NO_OPERATION_HISTORY(high)` block |
| CTL-HASHMISMATCH（摘要錯） | `FP_HASH_MISMATCH(high)` block |
| CTL-DRIFT（after_record 與現行記錄不符） | `POST_HOC_DRIFT(high)` block |
| A4B（DONE 任務唯一收據藏子目錄） | `NO_OPERATION_HISTORY(high)` block |

## 與 S4 已記錄邊界的關係

S4 REPORT-2 的結論是「內部一致的偽造通過＝authenticity 邊界，需要帳本外的訊號」。本輪發現不同且更便宜：**不需要偽造任何一致的內容**——把欄位拿掉（A6/A9/A11/A12）、把時間回填（A2）、把檔案改名或移目錄（A4/A5）、補一張空收據（A10）即可，全部是「缺席」攻擊，每一項都是工具現有語彙內機械可查的。換言之：在擴充 spec 4 討論外部訊號之前，spec 3 的 liveness 邊界還有便宜一整個數量級的補強空間。
