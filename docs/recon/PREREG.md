# PREREG：ledgerwash v0.1 對 EC 帳本對帳（v0.1 驗收證據）

- 日期：2026-09-28（預測於掃描前釘死並先行 commit）
- 目標：`estate-consolidation` @ `b8761e95`（round 0 釘死的同一 SHA；本地 clone 已含該物件）。
- 方法：`ledgerwash scan <ec-clone> --at b8761e95`。epoch 讀取只跑唯讀 git 指令（rev-parse／cat-file／ls-tree／log），不 checkout、不建 worktree、對 EC 零寫入。
- 工具身份：ledgerwash 0.1.0（spec 1），agent-rd commit `8742b0d`，29 測試綠、qualify 綠。
- round 0 ground truth（人判，`../round0/FINDINGS.md`）：205 raw → 91 real——懸空引用 61（唯一路徑）、收據語意契約 9（pre-image pin）、釘死驗證本地性 20、時序不可能 1（T-292）；C3 的 60 筆全為 CJK 註解雜訊；C4／C8 零發現。

## 預測（跑後逐項 held / not-held，寫入 RECON.md）

| # | 預測 | 依據 |
|---|---|---|
| P1 | `DANGLING_REF` 恰為 **61**，且其路徑集合與 round 0 的 61 個唯一死路徑**集合相等** | 逐 path 去重＋同 reference 文法 |
| P2 | `STATUS_STATE_MISMATCH` = **0**（round 0 C3 的 60 筆 CJK 雜訊全滅） | CJK 正規化 |
| P3 | `TIMELINE_INVERSION` = **1**，且 T-292 的收據在其中 | round 0 C9 |
| P4 | `FP_HASH_MISMATCH` = **0**：round 0 的 9 筆「born-broken」是 pre-image pin，v0.1 依 origin 錨定（`expected-head-blob`→expected_head）或以 `CONTRACT_UNDOCUMENTED` 出場，**不得**以偽造宣稱（hash mismatch）出場 | 契約表＋時代感知 |
| P5 | `FP_SOURCE_MISSING` = **0**：round 0 的 23 筆 source 缺檔皆 birth-era-valid | 出生驗證 |
| P6 | `PIN_UNROUTABLE`＋`PIN_LOCAL_MISSING` 的 SHA 聯集**涵蓋 round 0 C6 全部 20 個 missing SHA**（20/20）；兩規則合計 findings ∈ [20, 40] | 同一 SHA 同時出現在 prose 與 expected_head 時分別記 |
| P7 | `POST_HOC_DRIFT` = **0**（C8：176/177 type-strict 相等；T-289 是無 after_record 的舊 schema 收據，非 drift） | round 0 C8 |
| P8 | `CHAIN_BREAK` = **0** | round 0 未見鏈斷 |
| P9 | `CONTRACT_UNDOCUMENTED` **≥ 9**（9 筆 pre-image pin 至少以此出場；其他未文件化組合會使數字更大） | 契約表只收編兩種組合 |
| P10 | `TIMESTAMP_MALFORMED` = **0**（低信心，探查項：round 0 對壞時間戳是静默跳過，無基準值） | parse 行為差異 |
| P11 | 總 findings ∈ **[80, 140]** | P1+P6+P9 合計 |
| P12 | 確定性：同一指令重跑兩次，envelope（除 `run.target`）**byte-identical** | SPEC §7 |
| P13 | PIN 類 findings 的 message 一律不含「failed / dead / broken」等斷言（人工抽查全部 PIN 訊息） | SPEC §4 用語紀律 |

判定門檻：P1–P10 全 held 且 P12–P13 held → v0.1 對帳 PASS（S3 驗收證據成立）。任何 not-held → 逐項歸因（工具缺陷、契約表缺口、或 round 0 人判需修正），不得事後改預測。
