# 词库 RAG（lexicon）

工作区级词卡复用库。目的：新项目不再从零逐行手写词卡，而是**先查词库**（最长匹配），只把词库没有或不敢担保的部分交给**一次定向联网审核**。

## 文件

| 文件 | 角色 | 谁写 |
|---|---|---|
| `lexicon.json` | **派生**产物：全部词条 + 变体 + 可靠性 + 来源 | `build_lexicon.py`（可随时重建） |
| `project-order.json` | 冲突判定用的**新旧顺序**（追加式） | `build_lexicon.py` 自动维护 |
| `feedback.json` | 用户审核结果计数（accepts / rejects / corrections） | `apply_lexicon_feedback.py` |
| `overrides.json` | 审核确认的**新增语境变体**、**主导值钉值**与失效词条的可靠性封顶 | `apply_lexicon_feedback.py`（钉值由人工写） |

`lexicon.json` 是派生物：手改会在下次重建时丢失。要改词库，改 `feedback.json` / `overrides.json`，或直接改某个项目的 `frames.json` 后重建。

## 词条结构（schemaVersion 2）

```jsonc
{
  "surface": "結んで",            // 匹配键（NFC 归一化）
  "kana": "むすんで",             // 假名键：surface 是假名则取自身，否则取读音
  "kind": "content",             // content | particle
  "dominantMeaning": "系紧；相连",  // 主导值：人工确认 > 频次 > 新近
  "dominantGrammar": "动词て形",
  "dominantReading": "むすんで",
  "dominantRomaji": "musunde",
  "meanings": [                   // 全部已见变体（不是冲突，是多义/近义改述）
    { "value": "系紧；相连", "count": 2, "humanConfirmed": 2, "projects": 1,
      "lastSeenAt": "…", "recencyRank": 23 }
  ],
  "grammars": [ … ], "readings": [ … ], "romajis": [ … ],
  "ambiguity": { "meaningVariants": 1, "grammarVariants": 1, "readingVariants": 1 },
  "reliability": { "score": 0.9, "sources": 2, "humanConfirmedSources": 2,
                   "distinctProjects": 1, "accepts": 1, "rejects": 0, "lastSeenAt": "…" },
  "qualityIssues": [],            // 非空 = 隔离，不参与匹配
  "matchable": true,
  "provenance": [ { "project": "eternel", "frameId": "l007",
                    "status": "human-confirmed", "recencyRank": 23, "recordedAt": "…" } ],
  "provenanceTruncated": 0
}
```

### 两类「不一样」必须区分

- **变体（variants）**：同一个词在不同句子里确实有不同用法（助词 `で` 的 12 种功能；`永遠` 读 `えいえん`/`とわ`）。全部保留，对外只给 `dominant*` 与歧义计数。
- **冲突（conflicts）**：同一字段被不同来源写成不同值。按**最新来源优先**（`project-order.json` 的顺序），同一秒内**人工确认优先**。

顺序不取文件系统 mtime（clone 后会全部变成检出时间），而是持久化在 `project-order.json`：新项目自动追加到末尾（视为最新）。需要重算时用 `--refresh-order`。

### 可靠性（reliability）

初始种子只要求「第一次跑得动」，真正校准它的是你的审核结果：

```
人工确认过          → 0.90
≥2 个项目出现过      → 0.72
仅 1 个草稿来源      → 0.60
+ 多项目加成（未确认时，最多 +0.06）
- 缺释义 -0.20 / 缺语法 -0.10
- 歧义：功能词（助词/助动词）每个额外变体 -0.05（上限 -0.25）
        内容词每个额外变体 -0.02（上限 -0.06，近义改述不该被重罚）
- 语法标签变体每个 -0.05（上限 -0.10）
审核反馈：被采纳 → max(score, 0.85 + 0.02×accepts)（上限 0.98）
          被否决 → -0.15×rejects（上限 -0.40，净否决则封顶 0.30）
```

### 主导值钉值（pin）

主导值的排序是 `(是否钉值, 是否有草稿票, 是否人工确认, 票数, 新近度)`，所以**票数只在前两项相同时才起作用**。修正记录（`corrections`）永远只是一张额外的变体，翻不过累积票数；这是有意的（`溢れる` 读 `こぼれる` 只是某一行的義訓，不该改写所有项目）。

当主导值本身就是错的、而它只是被脏草稿堆出来的票数领先时，用**标量形式**手工钉值：

```jsonc
"ない": {
  "meaning": "不……（否定）",
  "grammar": "否定助动词；「聞いてない」＝「聞いていない」的口语省略"
}
```

钉值排在最前，因此票数只有 3 也能压过 6 票的旧值；`lexicon.json` 会在该变体上标 `"pinned": true`，使「主导值与票数领先者不一致」这件事在派生文件里可解释。

两点必须知道的后果：

- 钉值会改写**之后每个项目**的预填，且没有任何机制会自动撤销它——要撤销就删掉该键再重建。
- `grammar` 的钉值会被 `is_function_entry` 读到：把助词/助动词的读法钉上去，词条就会被重新归类为功能词，歧义惩罚从内容词档升到功能词档（`ない` 的可靠性 0.74 → 0.55）。方向是对的——歧义中的助动词本就不该被自动复用。

## 匹配契约（`lexicon_match.py`）

1. **按长度从长到短**取最长命中：`明けゆく` 优先于 `明け`；若某句里存在更长的词卡（例如整块固定表达），就按长词卡拆。
2. 退而求其次按**假名键**匹配（`きみ` → `君`），置信度打 0.9 折。
3. **单字条目**只有功能词（助词/助动词）能参与匹配；单字内容词会把真词切碎（`愛おしい` → `愛`+`お`+`し`+`い`），因此不参与匹配，只作为**提示（hints）**出现在审核单元里。
4. 空白与标点只作分隔；**拉丁文片段**（英文行/英文插入）单独成段，既不匹配也不进审核队列（按 skill 契约，英文无词卡/假名/罗马音）。
5. 匹配结果分三类：
   - `rag-reused`：可靠性足够 → 直接复用成卡
   - `rag-proposed-low-confidence`：词库有但不敢担保 → 预填候选，待审核确认
   - **审核单元（review unit）**：包含未知文本的连续片段 → 聚合成**一个短语级审核单位**，附着已识别的碎片与候选取值，交给一次定向联网审核

### 隔离（quarantine）

历史项目里有脏数据：把整行歌词当词卡、`reading` 只存首音（`i`/`ya`/`ko`）、非日文词条。它们**留在库里作为证据**，但 `matchable: false` 永不参与匹配。当前统计：1,773 条中 36 条被隔离（`kana-key-not-kana` 33、`reading-not-kana` 30、`reading-shorter-than-kanji-count` 15、`no-japanese-characters` 2）。

## 命令

```bash
# 重建词库（工作区根目录执行）
python .agent/skills/japanese-song-study-video/scripts/build_lexicon.py .
python … build_lexicon.py . --exclude eternel          # 留一法：诚实测复用率
python … build_lexicon.py . --refresh-order            # 按 mtime 重算新旧顺序

# 查词 / 分词预览
python … lexicon_match.py --lexicon lexicon/lexicon.json --text "重ねた 手のひら"
python … lexicon_match.py --lexicon lexicon/lexicon.json --lines-file lines.txt --json

# 用词库起草项目词卡（写 frames.json + 审核队列）
python … draft_cards_from_lexicon.py projects/<slug> --confidence-threshold 0.70

# 审核：一次定向联网审核后封存
python … seal_lexicon_review.py projects/<slug> --online-review project/review/online-review.json

# 把审核结果回灌词库（先 dry-run，再 --apply，最后重建）
python … apply_lexicon_feedback.py . --decisions decisions.json
python … apply_lexicon_feedback.py . --decisions decisions.json --apply
```

## 实测（eternel 留一法）

用**排除 eternel** 的词库（1,740 条）去匹配 eternel 的 25 行歌词（`measure_reuse.py` 可复算）：

| 指标 | 数值 |
|---|---|
| 内容片段命中率 | 63.1%（89/141） |
| 可直接复用（高置信） | 7 张 |
| 低置信预填候选 | 32 张 |
| **需人工/联网处理的审核单元** | **27 个（≈1.3 个/行）** |
| 纯英文行 | 4 行，0 审核项 |

对照：eternel 当初是逐行手写 102 张卡、再经三角色评审出 30 项修改。现在同样的内容由词库预填大部分、审核单位降到 27 个短语级单元；且采纳后这些词条可靠性上升到 0.9，下一个项目可直接复用。

> 注意：`rag-reused` 数量偏低是因为该测试用的是**排除 eternel 后**的词库，其中的词条多为其它项目的**未确认草稿**（0.60–0.72）。随着审核结果回灌，可直接复用的比例会上升——这正是可靠性迭代的目的。

## 假名匹配的安全策略

汉字词条的 `kana` 键由读音折叠而来（1,205 条中 1,202 条如此），因此**同音异形词会互相竞争**（全库 69 组、涉及 143 个 surface，例如 `あした` 可能对应 `明日` 或 `未来`）。词库无法判断句中写的到底是哪个，所以：

- 假名回退匹配的置信度上限压到 0.55；同音组内竞争者 ≥2 时进一步压到 0.40；
- 假名匹配**永远 `needsReview`，绝不进入 `rag-reused`**；
- 匹配结果附带 `homophoneAlternatives`（同音候选表面形与释义），审核者一句话即可选定。

即：假名匹配只用于「给候选」，不用于「自动复用」。

## 交付前必须提交的文件

`lexicon/` 需要提交：`lexicon.json`（派生但便于跨机复用）、`project-order.json`（**顺序语义依赖它**，缺失会退回 mtime 推导）、`feedback.json`、`overrides.json`、`README.md`。该目录不在任何 `.gitignore` 规则内；手工推送前请确认这四个文件都在。

## 与审核门禁的关系

`verify_render_gate.py` 支持两种审计模式，二者都**不削弱**你的两项决策权（内容采纳、渲染授权）：

| 模式 | 用于 | 审计要求 |
|---|---|---|
| `mandatory-multi-agent` | 历史项目 | lexical/grammar/translation 三份提案 + integration 报告 |
| `lexicon-rag-targeted-online` | 新的词库流程 | 锁定词库版本 + 审核队列 + 一份 `reviewRole: online` 的定向联网审核 |

两种模式都仍要求：`merge-log.json` 绑定当前 `frames.json`、`review-decision.json` 记录你的**原话**并绑定审计与合并日志。
