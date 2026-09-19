# 词库 RAG + 定向联网审核流程 · 对抗式代码评审

评审对象：`.agent/skills/japanese-song-study-video/scripts/` 下的
`build_lexicon.py`、`lexicon_match.py`、`draft_cards_from_lexicon.py`、
`apply_lexicon_feedback.py`、`seal_lexicon_review.py`、`verify_render_gate.py`（双审计模式），
数据 `lexicon/*.json`，文档 `lexicon/README.md`、`references/12-lexicon-rag.md`。
评审日期内代码未做任何修改；所有实验均在 `projects/eternel/project/work/review2/` 内完成。

---

## 1. 结论摘要（按严重度）

### 致命（2 条）

| # | 一句话结论 | 复现命令 |
|---|---|---|
| **F-1** | **定向联网审核门禁形同虚设**：lexicon 模式下 `verify_render_gate` 只比对「审计里写的哈希 == 磁盘上文件的哈希」，从不检查审核有没有产出任何内容；`changes` 为空、甚至手写一份审计、甚至一个 0 张词卡的项目，都能通过渲染门禁。 | `python review2/probe_gate.py`（B1/C1/E1/G1/K1 全 PASS）<br>`python review2/probe_final.py`（0 卡项目 PASS） |
| **F-2** | **假名键由 `dominantReading` 合成，同音异形词互相顶替并静默自动复用**：1205 条汉字 surface 的可匹配词条中有 1202 条（99.8%）的 `kana` 键 = 主导读音（`build_lexicon.py:313` 的回退），而 `Lexicon.best_match` 的假名回退对同音词条用 `max()` 只返回一个，全库共 69 组同音冲突（涉及 143 个 surface）；后果是 `あした`（明天）被解析成 `未来`（未来）并以 0.81 置信度**自动复用、不进审核**。 | `python review2/probe_kana3.py`<br>`python review2/probe_kana2.py`<br>`python review2/probe_homophone2.py` |

### 高（3 条）

| # | 一句话结论 | 复现命令 |
|---|---|---|
| **H-1** | 「净否决后停止自动复用」不成立：`corrections` 被同时计入 `accepts`，一次 correction 就会走进 `accepts and "reliability" in ...` 分支**摘掉 0.3 封顶**，即使 rejects 仍多于 accepts；被否决词条随即以 0.72 重新自动复用，而文档承诺「封顶直到重新审核」。 | `python review2/probe_feedback2.py`（A→B→D） |
| **H-2** | 被否决词条几乎没有恢复通道：`score_entry` 只累加 rejects，`apply_lexicon_feedback.py` 从不消减 rejects；rejects=2 时即使 accepts 累计到 5，score 仍只有 0.65（< 0.70），永远无法自动复用；`frames.json` 里的人工确认也不会清除封顶。文档「被否决 → 可靠性下降」「重新审核后可恢复」与实际不符。 | `python review2/probe_score.py`<br>`python review2/probe_feedback2.py`（G→H） |
| **H-3** | 阈值双轨：`lexicon_match` 自身默认 `needsReview` 阈值是 0.75，而 `draft_cards_from_lexicon.py` 默认传 0.70；当前词库有 **56 条**词条落在 0.70–0.75 之间（词库认为该审、起草器直接复用），其中多数是高频活用形（`みたい`、`なって`、`しない`、`知らない`…）；另有 **103 条**「≥2 个项目的未确认草稿」被 `score_entry` 给到恰好 0.74，全部落在这个盲区，从不进审核。 | `python review2/probe_match.py`（P2.8）<br>`python review2/probe_population.py` |

### 中（5 条）

| # | 一句话结论 | 复现命令 |
|---|---|---|
| **M-1** | 单字功能词例外会再把假名词切碎：`うたって` → `う`（释义「兔子（生肖）」）+`た`+`って`；`うえ`/`じょう`/`さびしい` 同样被单字吃掉。词库里的脏单字条目（`う`、`か`…，共 25 个单字匹配键）与真正的助词同权参与最长匹配，而 `merge_fragments` 只在相邻片段含 `unmatched` 时才合并，纯单字命中不会被合并（`かがやき` 会变成 4 张单字卡）；例外本身是文档写明的设计，问题在于例外没有排除「释义不是功能」的脏条目。 | `python review2/probe_kana3.py`<br>`python review2/probe_kana_index.py`（D 段） |
| **M-2** | 审计里的 `lexicon.sha256` 是自证的：`onlineReview.lexiconSha256` 在 seal 阶段被校验后就不写进审计，门禁端两处都没有复核，于是把审计与队列的 lexicon 哈希同时改成任意值即可通过（H2 PASS）。词库版本实际没有被渲染授权链绑定。 | `python review2/probe_gate.py`（H2） |
| **M-3** | `roles == ["online"]` 可被等价伪造：`seal_lexicon_review.py:101` 无条件写死 `["online"]`，门禁只做集合相等（D2 `["online","online"]` 也 PASS），而多角色模式至少强制 3 份提案 + 1 份整合；lexicon 模式的「审核义务」在门禁层只是一个可手写的 JSON。 | `python review2/probe_gate.py`（D2/G1） |
| **M-4** | 「用户原话」被放宽：门禁检查 `userWording or authorization`，只写一个泛化的 `authorization` 字符串即可通过，`review-decision.json` 里没有任何用户原话仍能渲染。 | `python review2/probe_gate.py`（F1） |
| **M-5** | 起草器非幂等：第二次运行时 `rag-review-queue.json` 的 `framesBeforeSha256` 记录的是「上一轮草稿之后」的 frames，而不是真正的源 frames；且 `frames.json` 被就地覆盖，旧字段（如英文行的 `cardReviewStatus`/`reviewNote`）残留。 | `python review2/probe_draft.py`（determinism 段：frames SAME / queue DIFFERENT） |

### 低（6 条）

| # | 一句话结论 | 复现命令 |
|---|---|---|
| **L-1** | `project-order.json` 与整个 `lexicon/` 目录**未被 git 跟踪**（`git ls-files lexicon/` 为空，`git status` 显示 `?? lexicon/`），clone 后顺序语义只能退回 mtime 推导；代码逻辑本身已测无问题，风险在交付环节。 | `git -C C:\project\musicjlpt ls-files lexicon/` |
| **L-2** | `contentSha256` 依赖文件 mtime（`lastSeenAt` 直接来自 `frames.json` 的 `stat().st_mtime`，`build_lexicon.py:247`）：同一内容、只改 mtime 就会得到不同哈希，与「同一输入重建两次一致」的直觉不符（同一次会话内重建确实一致）。 | `python review2/probe_final.py`（mtime churn 段） |
| **L-3** | 拉丁片段的判定把 ASCII 全部吞掉且静默丢内容：`don't` 被切成 `don`+`t`（ASCII 撇号成了分隔符），孤立 ASCII 撇号/连字符永远不进审核队列（`'`、`a-b` 无任何 span）。 | `python review2/probe_match.py`（P2.2） |
| **L-4** | `～`(U+301C)、`…`、`・` 不在 `SEPARATOR_RE` 里，会被并进相邻的 unmatched 审核片段；`ヽ`(U+30FD)/`ヾ`(U+30FE) 不在 `KANA_RE` 的假名范围内，含它们的读音会被判成 `reading-not-kana` 而被隔离。 | `python review2/probe_match.py`（P2.3） |
| **L-5** | `build_lexicon.py --out` 指向工作区之外时抛未处理的 `ValueError`；`apply_lexicon_feedback.py` 会为词库里根本不存在的 surface 写入 `overrides/feedback` 条目，并把它计入 `overridesApplied`；`_candidate` 会退回一个未被索引的单字内容词条（`の声`→`の` 命中后 `声` 退化成 unmatched）。 | `python review2/probe_final.py`（首段为 out 越界）<br>`python review2/probe_feedback.py`（第 6 段） |
| **L-6** | 文档数字与当前派生结果不一致：README 的 eternel 留一法表（1 张自动复用 / 38 张低置信）在沙箱复算为 **7 / 32**（审核单元 27 与文档一致）；`quality_issues` 的隔离段只出现在 `lexicon/README.md`，`references/12-lexicon-rag.md` 没有对应条目。 | `python review2/probe_eternel.py` |

---

## 2. 逐条实测记录

所有命令均可直接复制执行（`review2/` = `projects/eternel/project/work/review2/`）。
全部原始输出已合并保存在 `review2/ALL-OUTPUT.txt`。

### 怀疑点 1：门禁是否被削弱

**实验 1.1 — 空审核能否过门禁（`review2/probe_gate.py` B1）**

沙箱 `review2/sandbox/projects/sandbox` 里，队列含 1 个待审单元，定向联网审核刻意
`changes: []`、`checkedUnits: 0`、`status: completed`，其余哈希全部重新绑定为一致
（审计⇄队列/审核、decision⇄审计/merge、authorization⇄全部）。

```
== B: content-empty online review (0 changes) against a NON-empty queue ==
            queue totals.reviewUnits=1, review changes=0, checkedUnits=0
[**DEFECT**] B1 zero-change review over a 1-unit queue
            expect=block  -> PASS (gate accepted)
```

**实验 1.2 — 审核内容与队列毫不相干（C1）**：把 `changes` 改成引用一个不存在的
`frameId/unit`，仍 PASS。门禁不解析审核条目、不做任何集合差校验。

**实验 1.3 — 手写审计，完全不跑 seal（G1）**：只写
`{"mode":"lexicon-rag-targeted-online","status":"completed","roles":["online"], 三个 file+sha256}`
（没有 `sealedAt`、没有 `coverage`、`changes: 0`），PASS。

**实验 1.4 — 端到端 0 卡项目（`review2/probe_final.py`）**：一个只有英文行、
`grammarCards: []` 的项目，队列 0 单元、审核 0 变更，走完 seal → merge-log → decision →
authorization 后：

```
   GATE RESULT: PASS   cards in frames.json = 0
   audit coverage: {'frames': 1, 'cardsDrafted': 0, 'reviewUnits': 0}
```

**实验 1.5 — 角色伪造（D1–D4）**

```
[OK      ] D1 review declares lexicon-online, audit declares exactly [online]   -> PASS（本就允许）
[**DEFECT**] D2 audit declares [online, online]                                -> PASS（去重后集合相等）
[OK      ] D3 audit declares [online, integration]                             -> BLOCKED
[OK      ] D4 audit declares []                                                -> BLOCKED
```

结论：`roles` 是由 `seal_lexicon_review.py:101` 无条件写死的字符串，不是证据；
`reviewRole` 只接受 `online` / `lexicon-online` 两值并在封存时归一化，因此
「伪造 `lexicon-online`」本身不构成额外风险（D1 通过是设计），真正的风险是
**整个审计文件可以手写**（G1、M-3）。

**实验 1.6 — 审核描述符可指向任意文件（E1）**：把 `onlineReview.file` 指向
`project/input-manifest.json`（起草器自己会写的文件），只要该 JSON 含
`reviewRole/status/changes` 三个键即 PASS。

**实验 1.7 — 两种模式是否都强制「用户原话 + merge-log 绑定当前 frames」**

```
[**DEFECT**] F1 decision has no userWording, only a generic authorization string   -> PASS
[**DEFECT**] F2 audit has no baseFrameSha256                                       -> PASS
[OK      ] I1 frames edited after the merge log was written                        -> BLOCKED
            ValueError: Merge log is stale for the current frames.json
[OK      ] I2 same edited frames, but the merge log rewritten to match             -> PASS（设计如此）
```

* merge-log 绑定**确实生效**（I1 BLOCKED），两种模式共用 `verify_review_gate` 的这段检查；
  但 merge-log 的**内容**（`appliedOperations` 可以为空）无人检查（K1 PASS）。
* 「用户原话」在 lexicon 模式下**未被强制**（F1）：`decision.get("userWording") or
  decision.get("authorization")` 后者是自由文本。
* 审计记录的 `baseFrameSha256`（`seal_lexicon_review.py:100`）门禁端从不比对（F2），
  它是纯 provenance。真正的保护来自 merge-log，而不是审计。

**实验 1.8 — 模式字符串与多角色模式（J1/J2）**

```
[OK] J1 只把 mode 改成 mandatory-multi-agent            -> BLOCKED（roles 不匹配）
[OK] J2 词库起草的项目改报多角色但没有任何提案            -> BLOCKED（提案缺失）
```

结论：`verify_multi_agent_audit` 的**结构**要求比 `verify_lexicon_audit` 严格
（3 份带 role 的提案 + 1 份 integration，且都校验 sha256 与 `reviewRole` 前缀）。
lexicon 模式确实把「3 份提案 + 1 份整合」降级成「1 份 JSON」，而门禁没有为这次降级
补上任何内容校验 —— 这是本次评审最严重的缺陷。

---

### 怀疑点 2：匹配正确性

**实验 2.1 — 最长优先（`probe_match.py` P2.1）**：`明けゆく` 正确压过 `明け`。

```
[0:4] MATCH '明けゆく' -> 明けゆく by=surface conf=0.9 review=False
[4:5] UNMATCHED '空'
```

**实验 2.2 — 拉丁片段 / 分隔符（P2.2、P2.3）**

```
英文整行: 7 个 LATIN span、0 个 reviewUnit（符合 skill 契约）
"don't 好き": [0:3] LATIN 'don' / [4:5] LATIN 't' / [6:8] UNMATCHED '好き'
"'":        无任何 span（既非 separator 也非 latin，contentSpans=0）
"a-b":      两个 LATIN span，无 span 覆盖 '-' 自身
"あ〜あ…あ・あ": 2 个 unmatched 单元，'〜…・' 被并进文本一起送审
```

**实验 2.3 — 假名回退（P2.4）与键的来源（`probe_kana2.py`）**

```
matchable entries: 1737
kanji surfaces: 1205; kana key == fold(dominantReading): 1202
kanji surfaces whose kana key is neither surface nor dominant reading: 3
    surface='寂しい'  kana='さびしい'  dominantReading='さみしい'
    surface='未来'    kana='あした'    dominantReading='みらい'
    surface='上'      kana='じょう'    dominantReading='うえ'
69 ambiguous kana keys covering 143 surfaces
    'うたう' -> うたう | 歌う | 謳う
    'きせき' -> キセキ | 奇跡 | 軌跡
    'ひとり' -> 1人 | 一人 | 独り
```

`build_lexicon.py:313` 在 `entry["kana"]` 为空时用 `serialise_variants(reading)[0]`
补齐，于是「假名键」在 1202/1205 的情况下其实等于**主导读音**；`Lexicon.best_match`
的假名回退对同音词条用 `max()` 只取一个。实测后果（`probe_kana3.py`）：

```
   'あした'  -> surface='未来'  by=kana  conf=0.81  review=False  meaning='未来'  romaji='mirai'
   'きせき'  -> surface='奇跡'  by=kana  conf=0.81  review=False
   'キセキ'  -> surface='キセキ' by=surface conf=0.6 review=True     （同一读音，另一条被顶掉）
```

「假名回退」在文档里被描述成「`きみ` → `君`，置信度打 0.9 折」的安全兜底；实测它是
**在读音相同、词不同的情况下以 0.81 静默自动复用**，且 `needsReview=False`。

**实验 2.4 — 单字功能词例外（P2.7、`probe_kana_index.py` D 段）**

```
25 single-character match keys: うかがさぜただてでとなにねのはばへもやよれわをん程
'かがやき' -> 全部切成 4 张单字卡（在测试词库里）
实时词库: 'うたって' -> う + た + って，其中 う 的释义是「兔子（生肖）」
          'うえ' -> う（兔子），'さびしい' -> さ
```

例外本身是文档写明的（「单字功能词可复用」），但词库里存在**释义是泥巴的单字功能
条目**，它们与真正的助词同权，于是长假名词被反复切碎。`merge_fragments` 只在 run 里
存在 `unmatched` 时合并，纯单字命中不会被合并，所以这类碎片会直接成为词卡。

**实验 2.5 — 阈值算术（P2.8）**

```
human confirmed, 2 projects: score=0.9  confidence=0.9  needsReview(0.70)=False -> auto
2-draft-project content word: score=0.72 confidence=0.72 needsReview(0.70)=False -> auto
（同一词条用 lexicon_match 默认 0.75 会 needsReview=True）
```

`probe_population.py` 给出当前词库的实际规模：

```
matchable=1737  humanConfirmed=657 (37.8%)  unconfirmed=1080
  unconfirmed, >=2 projects (seed 0.74 -> silently reused at the 0.70 default): 103 (5.9%)
entries whose score sits in the 0.70-0.75 gap: 56
    'くだらない' score=0.72 humanConfirmedSources=0 distinctProjects=2
    '知らない'   score=0.74 humanConfirmedSources=1 distinctProjects=5 sources=8
    'みたい'     score=0.74 humanConfirmedSources=1 distinctProjects=4 sources=12
```

即：**56 条**词条处在「词库自己认为该审、起草器直接复用」的双轨盲区，规模不大但
全是高频助词/活用形（`みたい`、`なって`、`しない`、`知らない`…），影响面广。

---

### 怀疑点 3：写回正确性（`review2/probe_draft.py`）

4 行歌词、9 条合成词条，真实运行 `draft_cards_from_lexicon.py`：

```
l001 'そう思う そう'      -> 3 张卡（そう / 思う / そう），furigana 1 条 [2:3] 思
l002 '生きる 生きて'       -> 1 张卡（生きる @4），[0:3] 因 withinUnknownPhrase 被丢弃
l003 '煌めきの 手のひら'    -> 煌めき / の / 手のひら，ruby [0:1] 煌、[5:6] 手
l004 '永遠の 夜を 重ねた'   -> 永遠 / の / 重ねた，ruby [0:2] 永遠、[7:8] 重
```

* **token 是否都在该行**：全部在行内，且渲染器式左到右游标搜索得到的锚点与匹配器
  的真实 span **完全一致**（`probe_ruby.py` / `probe_ruby2.py` 的 CONSISTENT 判定，
  含重复 token 行 `'煌めきの 煌めき'`、`'笑顔 笑顔'`）。
* **读音 / 罗马音与词条是否一致**：`check_reading_romaji` 零不符。
* **furigana 锚点**：用 `render_video.py:237` 的同一条规则（`text[start:end] != base`
  → RuntimeError）逐条复核，**0 条会抛错**；`ruby_for` 只输出「假名剥离后的汉字核」，
  锚点在 `line.find(core, cursor)` 上，实测未发现错位。
* **同 token 重复成卡**：会出现（l003/l004 各 2 张同名卡），这是「该行确实出现两次」
  的合理结果，渲染器分别锚到 [0:1]/[5:6]，\*\*不算误报\*\*。
* **确定性与幂等性**：

```
frames.json  a11e6ed… -> a11e6ed…  SAME      （卡片内容确定）
queue.json   98d49a5f… -> e1d97b50… DIFFERENT （generatedAt 变化 + framesBeforeSha256 记录的是上一轮草稿后的 frames）
```

总结：**未发现**渲染器会抛错的写回缺陷（怀疑点 3 的「锚点错位/读音不符/token 不在行」
三个具体假设均已被证伪）；确认的写回问题是幂等性（M-5）与两次 `card_from_span` 调用
（代码卫生，不影响输出）。

---

### 怀疑点 4：反馈语义

**实验 4.1 — 净否决（`probe_feedback2.py` A→H）**

```
A. initial              : accepts=0 rejects=0 score=0.85 cap=-
B. after 1 reject       : accepts=0 rejects=1 score=0.3  cap=0.3   pinnedBy=overrides.json
C. after an empty batch : accepts=0 rejects=1 score=0.3  cap=0.3   （空批次不动封顶）
D. after a CORRECTION   : accepts=1 rejects=1 score=0.72 cap=-      <-- 封顶被摘掉
   match now: confidence=0.6 needsReview=True                      （这一条侥幸仍需审）
（同一会话里 meanings 只有 2 个变体时 score=0.72；变体增多后会继续下降）
G. after 2 rejects      : accepts=2 rejects=3 score=0.3  cap=0.3
H. 更新的项目里人工确认  : accepts=2 rejects=3 score=0.3  cap=0.3   <-- 仍被压住，不会恢复
```

* 「净否决后停止自动复用」：**对 `reliability` 封顶这一层成立**（B/G/H 的 0.3 会让
  `needsReview=True`）。
* 但封顶**会被 correction 摘掉**：`apply_lexicon_feedback.py:102-106` 的条件是
  `rejects > accepts`，correction 同时把 `accepts += 1`（第 82 行），于是只要一次
  correction，`rejects(1) > accepts(1)` 为假，走入 `elif bucket["accepts"] and "reliability" in ...`
  分支把 0.3 删掉，随后 `score_entry` 从 rejects 无法判定的新数值重算 —— 未审的否决记录
  被静默作废（H-1）。
* 「被否决词条后续再被人工确认能否恢复」：`frames.json` 里的人工确认**不会**清除封顶，
  reject 计数也永不清零（H-2），`probe_score.py` 给出完整阈值表：

```
accepts rejects  score  verdict
      5       2   0.65  queued for review     <- 5 次采纳也回不到 0.70
      5       3   0.55  queued for review
```

* `corrections` 只新增变体、不覆盖主导值：**确认成立**（`probe_feedback.py` 第 5 段）：
  `meanings=['动作共同参与者','动作场所','提示动作的共同参与者']`，无覆盖、无丢失。

**实验 4.2 — 不存在词条的 correction（`probe_feedback.py` 第 6 段）**：为词库里没有的
`存在しない語` 写入 overrides/feedback，`lexicon` 不包含它，但 `stats.overridesApplied`
从 1 变 2（虚报），且该条永远无法被应用。

---

### 怀疑点 5：确定性与可移植性

**实验 5.1 — 同输入两次重建（`probe_draft.py` determinism / `probe_final.py` mtime 段）**

```
build 1: d3d670e0c72138af60c289a9755c435f258d5a8834d9ffe2ec5a9dc79b20f17e  (0.2s)
build 2: d3d670e0c72138af60c289a9755c435f258d5a8834d9ffe2ec5a9dc79b20f17e  SAME
after touching every frames.json mtime: 3616a4f40e35eb872c05a688a9d71ec46d9925f87c0098e2b7f9ceec9906a9f8
*** DIFFERENT: contentSha256 depends on filesystem mtimes ***
```

同一次会话、同一批输入：**一致**。但 `lastSeenAt` 取自 `frames.json` 的 mtime
（`build_lexicon.py:247`），clone/checkout 会重写 mtime，于是 `contentSha256` 在克隆后
必然变化（L-2）。这解释了为什么 `resolve_project_order` 要把顺序持久化 —— 但那个文件
没有被 git 跟踪。

**实验 5.2 — `project-order.json` 在 clone 后是否仍保持顺序语义**

```
== 7. project-order.json semantics across a 'clone' ==
  order now: ['aaa-old', 'bbb-mid', 'ccc-new', 'ddd-later']
  order with project-order.json DELETED (fresh clone): ['aaa-old','bbb-mid','ccc-new','ddd-later']
  SAME (mtime-independent)
== 8. --exclude also rewrites the persisted order file ==
  order unchanged by --exclude: True
```

代码逻辑：**已测，未发现问题**（删掉顺序文件后重建，在本沙箱里复现出同样顺序；`--exclude`
不会破坏已持久化的顺序）。真正的问题在交付层：

```
> git -C C:\project\musicjlpt ls-files lexicon/
(空)
> git -C C:\project\musicjlpt status --porcelain lexicon/
?? lexicon/
```

整个 `lexicon/` 目录（含 `project-order.json`）**未被跟踪**（`.gitignore` 里没有任何
针对 `lexicon/` 的忽略规则，即这一层保护尚未落地），clone 后目录不存在
（L-1），此时顺序只能退回 mtime 推导，而 mtime 在 clone 后全部相同 —— 「不取 mtime」
的设计目标在交付链路上落空。

---

### 怀疑点 6：隔离误杀

`quality_issues` 共隔离 **36/1773** 条（`probe_quarantine.py`），逐条判定见第 3 节。

---

## 3. 被隔离词条逐条判定（误杀清单）

统计：`entries=1773`、`matchable=1737`、`quarantined=36`；
原因分布 `kana-key-not-kana 33 / reading-not-kana 30 / reading-shorter-than-kanji-count 15 / no-japanese-characters 2`
（与 `lexicon/README.md` 的记载一致）。

**判定：全部 36 条均被正确隔离，误杀 0 条。** 互斥分桶与逐条判定见
`review2/ALL-OUTPUT.txt` 的 `probe_quarantine2` 段（36 行全表），摘要如下：

| 桶 | 条数 | 触发原因 | 实例 | 判定 |
|---|---|---|---|---|
| A 非日文 surface | 2 | `no-japanese-characters` | `300mm`、`◯×△` | **隔离正确**。surface 无假名/汉字，作为词卡是数字/符号，不应参与匹配。 |
| B `reading` 不是假名 | 30 | `reading-not-kana` | `いつになっても枯れることのない` (reading `i`)、`何にも変わらない世界で` (`na`)、`永遠の中で` (`e`)、`くだらないけど` (`ku`) | **隔离正确**。这些整行「词卡」的 reading 存的是罗马字首音，作为读音/罗马音不可用。 |
| C `kana` 键非法、reading 合法 | 4 | `kana-key-not-kana` | `頼りなくてもいい` (reading `たよりなくてもいい`, kana `ta`)、`滑り落ちたら` (`すべりおちたら`/`su`)、`嘘みたいな` (`うそみたいな`/`u`)、`想像通り` (`そうぞうどおり`/`so`) | **隔离正确**。kana 键是首字母；这 4 条只有 kana 检查能救下来（reading 是合法假名）。 |

补充判定（逐条复核 36 行后）：

* **误杀 0 条**。没有任何一条是「短词 + 正确读音」却被隔离的。
* **但存在侥幸**：B 桶 30 条靠 `reading-not-kana` 拦截，C 桶 4 条靠 `kana-key-not-kana`
  拦截 —— 两类检查互为兜底。如果只保留 `kana-key-not-kana`，C 桶的 4 条会带着
  「整句假名读音」进入匹配表；如果只保留 `reading-not-kana`，`想像通り` 这类
  （surface 全汉字、reading 合法）会漏进匹配表。建议把「kana 键必须与 surface 或
  主导读音存在 attested 关系」写成显式规则，而不是依赖两个格式检查互相补位。

---

## 4. 已测未发现问题清单

1. **最长优先匹配**：`明けゆく` 压过 `明け`；`じょうず`（整词）压过更短的假名键。
2. **假名回退的基本功能**：`きみ`（测试词库中只有 `君`）确实命中 `君`。
3. **单字内容词不参与匹配**：`夜`（content）在 `夜が明ける` 中不匹配；`の`（particle）可以。
4. **分隔符集合内的字符**：`\u3000`、`、`、`。` 等正确切分（`夜\u3000夜、夜` → 3 个 match）。
5. **写回的渲染契约**：token 均在行内；渲染器式左到右游标搜索的锚点与匹配 span 一致
   （含重复 token 行）；`furigana` 全部通过 `render_video.py:237` 的锚点断言；
   卡片的 `reading`/`romaji` 与所引词条完全一致；无跨行/错行引用。
6. **同一 token 重复出现**：生成多张卡不是误报，锚点分别落在各自出现位置。
7. **`draft_cards_from_lexicon.py` 的卡片内容确定性**：同输入重建两次 `frames.json` 一致
   （只有 `generatedAt` 变化）。
8. **`build_lexicon.py` 的同会话重建确定性**：`contentSha256` 两次完全相同。
9. **`project-order.json` 的追加式语义**：删除后重建得到相同顺序；`--exclude` 不破坏它。
10. **`--apply` 的双保险**：不传 `--apply` 时 `wrote: []`，确实不落盘（dry-run 只读）。
11. **`corrections` 追加而不覆盖**：主导值以外的所有变体全部保留。
12. **两种审计模式的 merge-log / frames 绑定**：编辑 frames 而不改 merge-log 会被拦
    （`Merge log is stale for the current frames.json`），lexicon 模式同样生效。
13. **`verify_multi_agent_audit` 的结构强度**：缺提案、缺 integration、角色不匹配均被拦。
14. **`seal_lexicon_review.py` 的版本绑定**：审核里声明了错误的 `lexiconSha256` /
    `queueSha256` 会被拒（`Online review was produced against a different lexicon revision`）；
    队列对当前 lexicon 陈旧也会被拒。
15. **`--lexicon` 的默认路径解析**：`workspace = root.parents[1]`，无论 cwd 在何处，
    默认 `lexicon/lexicon.json` 都解析到工作区根（已在 cwd=工作区根 / cwd=项目根 下各测一次，均成功）。
16. **隔离判定本身**：36 条全部为真实脏数据，误杀 0（见第 3 节）。

---

## 5. 修复建议（按优先级，只给方案）

**P0（阻断性，先修这两条再新建项目）**

1. **让门禁真正检查审核内容**（对应 F-1 / M-3 / M-4 / M-2）：
   * `verify_lexicon_audit` 增加「队列 → 审核」的覆盖校验：`queue.units` 的
     `(frameId, unit.text)` 集合必须被 `onlineReview.changes` 的 `(frameId, unit)`
     集合**完全覆盖**，且 `changes` 非空（当 `queue.totals.reviewUnits > 0`）；
     `changes` 为空但队列非空 → 直接 `ValueError`。
   * 校验审计的必需字段与类型：`sealedAt`（ISO8601）、`lexicon.path`、
     `lexicon.sha256`、`ragQueue.totals.reviewUnits`、
     `onlineReview.changes == len(review["changes"])`，并复核
     `review.get("lexiconSha256") == audit["lexicon"]["sha256"]`
     （把 seal 阶段已有的这层校验保留到门禁端），同时把 lexicon 的 sha256 纳入
     `authorization_hash_paths`，让渲染授权直接绑定词库版本。
   * 要求审核文件位于固定路径（如 `project/review/online-review.json`）或至少限定在
     `project/review/` 下，禁止指向 `input-manifest.json` 这类派生文件。
   * 增加「审核实质性」下限：每个 change 必须含 `evidence`（非空数组）与
     `new`（非空字符串），并统计 `resolvedUnits >= reviewUnits`。
   * 把 `decision.userWording` 改为**必需**（`authorization` 只作附加信息），
     并在审计里保存 `userWordingSha256` 以便交叉核对。
   * 若继续允许 `roles` 字段，改成以文件内容为准：审计必须记录
     `onlineReview.reviewRole` 且在门禁端复核，而不是只信 `roles`。
2. **修掉假名键的读音合成**（对应 F-2 / M-1）：
   * `build_lexicon.py` 不要在 `kana` 为空时用 `serialise_variants(reading)[0]` 回填；
     区分两个字段：`kanaKey`（只来自 attested kana surface）与 `readingKey`（读音索引），
     并分别标注 `matchableBy`。
   * `Lexicon.best_match` 的假名/读音回退：命中多个同音词条时**不要 `max()` 取一个**，
     而是返回「读音命中、surface 不唯一」的结果（`needsReview=True`，附候选列表）；
     或直接要求 `entry["kana"]` 与 `entry["surface"]` 存在 attested 关系才允许回退。
   * `quality_issues` 增加 `kana-disagrees-with-dominant-reading`
     （例如 `未来/kana=あした/reading=みらい`），并把「读音回退」的置信度上限压到
     自动复用阈值以下（建议 ≤0.65）。
   * 单字功能词例外加两个约束：(a) 单字条目的 `dominantMeaning` 必须像助词/助动词
     （可用 `kind == "particle"` 或 `FUNCTION_MARKERS` 白名单过滤掉「兔子」这类脏条目）；
     (b) 单字命中若被 ≥2 个单字命中相邻包裹（假名串），整串降级为审核单元，不自动成卡。

**P1（反馈闭环，影响长期可靠性）**

3. **修正否决语义**（对应 H-1 / H-2）：
   * `apply_lexicon_feedback.py` 里 `corrected` **不要**自增 `accepts`；单独记
     `corrections` 计数。
   * 封顶判定与「是否回收封顶」解耦：只要该 surface 的累计 `rejects > accepts`，
     就保持 `overrides.entries[surface].reliability = 0.3`；**只有显式 `accepted`
     决策**才允许移除封顶，且移除时按 `accepts - rejects` 重算。
   * 给「被人工确认（`status == "human-confirmed"`）的新 frames」一条恢复通道：
     `build_lexicon.py` 读到新的 `humanConfirmed` 来源时，清除该 surface 的
     `rejects` 或至少把封顶抬到 0.75 以上（文档承诺的「重新审核后可恢复」）。
   * 让 rejects 可衰减：例如 `score_entry` 用 `max(0, rejects - accepts)` 计罚，
     或引入时间衰减，避免「5 次采纳仍 0.65」。
4. **消除阈值双轨**（对应 H-3）：让 `draft_cards_from_lexicon.py` 默认沿用
   `lexicon_match` 的 0.75，或在 `Lexicon` 里暴露 `reviewThreshold` 并让起草器显式
   下调时必须写进审计（`audit.confidenceThreshold`）以便复核。
5. **幂等化**（对应 M-5）：起草器写入前先把目标字段清空（`grammarCards`/`furigana`
   由本工具独占），并把 `framesBeforeSha256` 改为「源 frames」（若已有 `cardDraft`
   记录则沿用其记录的源哈希），或明确拒绝在 `frames.json` 已带 `cardDraft` 时重复起草。

**P2（正确性细节 / 交付）**

6. 把 `lexicon/` 纳入版本控制（至少 `feedback.json`、`overrides.json`、
   `project-order.json`；`lexicon.json` 是派生物可继续忽略），否则 clone 后顺序语义丢失（L-1）。
7. `contentSha256` 与 mtime 解耦：`lastSeenAt` 改用可复现的时间源（如
   `source-manifest.json` 的记录时间，或 `frames.json` 内的时间戳），不要把 mtime
   写进被哈希的内容（L-2）。
8. 拉丁/标点收敛（L-3、L-4）：把 `\u301C`、`\u2026`、`\u30FB` 加入 `SEPARATOR_RE`；
   把 `\u30FD`/`\u30FE` 纳入假名范围；孤立 ASCII 撇号/连字符至少要在 coverage 里计数，
   避免「既不是分隔符也不进审核」的静默丢失。
9. 小修（L-5）：`build_lexicon.py` 在 `--out` 越界时给出明确 `ValueError`；
   `apply_lexicon_feedback.py` 对词库中不存在的 surface 给出警告或拒绝；
   `Lexicon` 不要让未被索引的条目经由 `hints_for` 路径退化成匹配。
10. 文档同步（L-6）：更新 README 的 eternel 实测表（当前复算 7 张自动复用 / 32 张
    低置信 / 27 个审核单元），把 `qualityIssues` 的隔离说明补进
    `references/12-lexicon-rag.md`，并把「两种模式都不削弱门禁」的表述改为
    「lexicon 模式的门禁强度取决于 `online-review.json` 的实质内容校验（见 P0-1）」。

---

## 6. 收尾声明

* 本目录 `projects/eternel/project/work/review2/` 最终：**89 个文件、9.44 MB**（9 899 138 B）。
  单次实验产物远低于 50 MB 预算（最大单文件 4.60 MB，为门禁/封存实验所需的
  `lexicon.json` 副本，共 2 份：`review2/sandbox/lexicon/lexicon.json`、
  `review2/sandbox7/lexicon/lexicon.json`；`review2/sandbox8/lexicon/lexicon.json`
  在同目录下另有一份，均未复制任何目录）。
* `review2/` 下的沙箱目录共 8 个（`sandbox`、`sandbox2`–`sandbox8`），
  全部由代码逐个 JSON 写出，**没有任何目录复制**（无 `Copy-Item -Recurse` / `cp -r` /
  `shutil.copytree` / `robocopy` / `xcopy` / `git clone`）。
  目录层级：`review2\<sandbox>` 一层，其内部最深为
  `review2\sandbox8\projects\emptytest\project\templates`（脚本本身要求
  `projects/<slug>/project/...` 结构才能运行，不是复制出来的）。
* 除本报告外，未写入 `review2/` 之外的任何路径（本报告为 `docs/lexicon-rag-review.md`
  这一个文件；`review2/` 内还写入了 `ALL-OUTPUT.txt` 作为证据汇编）。原始文件只读，复核用哈希：
  `lexicon/lexicon.json` `334b8ee0be02f745ab97b766082cd5f22e5965b42bb60c0f0bc63545396494f6`（4 823 316 B）、
  `lexicon/project-order.json` `c2a3b7c21bf7cf13fd233333a58790336112651a9d568c1c077607ba7ef7bf29`（806 B）、
  `lexicon/feedback.json` `4cec1c62d19de5f173c5cfb870d6d31007c344a83292089eff0dbb3b0241ac8e`（24 368 B）、
  `lexicon/overrides.json` `b4782e99474f5c7f5218bec135ccf285a10df41ae934590ed63679602ece0cc4`（388 B）；
  `lexicon/`、`projects/*/project/frames.json`、`projects/*/source/`、`.agent/` 均未被修改。
  本次评审锚定的 6 个脚本 SHA256（评审期间未变，评审结束时复算一致）：
  `lexicon_match.py` `1EB102A55552D71C660139ED04B57C4AAFB9B72BC1ADC2218B3D1DFAE6ADB65E`、
  `draft_cards_from_lexicon.py` `8900DB00262C04B18615B5F94DD1877FF75E69275234E13F919C6734A25F085C`、
  `seal_lexicon_review.py` `5199506F2ACAD07CD5A6577CD7F3FD668DC4095C52A21FF22F760F868862C168`、
  `verify_render_gate.py` `A0CCDC72ABE0A1E7294CD9AD214942732FE9A083A80F4BBCEAA10FF66E102BB2`、
  `apply_lexicon_feedback.py` `C8F1695DF643DEC9845C6B10EA77E0B96CB4AE573B433DDFA72191BA988AEE5E`、
  `build_lexicon.py` `61FEF417D5122C114A4669EED95D776AF25F8FDA5C14890390540E0CF9BCB7EF`。
* 主要证据文件：`review2/ALL-OUTPUT.txt`（全部探针原始输出）、
  `review2/probe_gate.py`、`review2/probe_draft.py`、`review2/probe_feedback2.py`、
  `review2/probe_kana3.py`、`review2/probe_final.py`、`review2/probe_quarantine2.py`。
