# 日语歌曲学习视频流水线优化分析

以 `projects/eternel`（sajou no hana「エテルネル」）的完整执行过程为样本，复盘阶段 1（输入冻结）到阶段 5（QA / promote）中哪些劳动是重复的、哪些流程可以简化，并给出配合「工作区级词库 RAG」的目标流水线。

## 口径与证据来源

- 阶段划分与契约来自 `.agent/skills/japanese-song-study-video/SKILL.md`（stage 表在第 18–22 行）与其 `references/01-inputs.md` … `08-validation.md`。
- 执行事实来自 eternel 项目内文件：`projects/eternel/project/build-state.json`（36 条 notes 记录全过程）、`projects/eternel/project/render/`、`projects/eternel/project/work/inputs-v1/`、`projects/eternel/project/qa/`。
- 重复劳动用全仓统计佐证：扫描 `projects/*/project/render/*.py` 与 `projects/*/project/work/**/*.py` 的文件名分布。
- 词库为本次实测：扫描 `projects/*/project/frames.json` 得 **24 个项目、5102 张卡、1773 个唯一 `token`**。`lexicon/lexicon.json`（schemaVersion 2，2026-09-11 生成）已存在并落盘，其 `stats` 为 `projectsScanned: 24`、`entries: 1773`、`humanConfirmedEntries: 657`、`particleEntries: 104`、`unambiguousEntries: 1376`、`multiMeaningEntries: 397`、`largestAmbiguity: 12`、`overridesApplied: 0`、`feedbackApplied: 0`；生成器与匹配器 `.agent/skills/japanese-song-study-video/scripts/build_lexicon.py`、`lexicon_match.py` 已存在（与本文档同时段由并行任务写入）。
- 扫描时 `projects/kanjou-glass/project/work/python-site/**` 因沙箱权限被跳过；该目录只是本机 python-site，不含项目数据，不影响上述统计。

## 1. 可固化为脚本的重复劳动

### 1.1 eternel 实际新写的脚本（27 个）

`projects/eternel/project/render/`（8 个 .py）：

| 脚本 | 当时用途 | 是否通用 |
| --- | --- | --- |
| `build_card_draft.py` | 从手写 CONTENT 表生成 `frames.json` 词卡 + 假名 + 审核 Markdown | 半通用（CONTENT 是项目专有，逻辑通用） |
| `render_setup_preview.py` | 用 skill 的 `ForegroundRenderer` 出真实三层静帧 | **通用** |
| `render_draft_previews.py` | 出 longest-lyric / longest-meaning / maximum-cards / mixed / pure-english / kanji-ruby 六类抽样 | **通用** |
| `build_card_gallery.py` | 逐行静帧 + HTML 逐行审阅页 | **通用** |
| `apply_review_merge.py` | 按 accepted-changes 应用变更 + 写 `merge-log.json` / `review-decision.json` | **通用** |
| `refresh_after_merge.py` | 重出审核稿、重建 `particle-functions.json`、更新 `draft-manifest.json` | **通用** |
| `replace_cover.py` | 换封面 + 归档旧封面 + 更新 `source/source-manifest.json` | **通用** |
| `write_render_plan.py` | 汇总 17 项哈希写 `project/render/render-plan.json` | **通用** |

`projects/eternel/project/work/inputs-v1/`（19 个 .py）：`analyze_alignment.py`、`analyze_onset.py`、`card_stats.py`、`check_audio_preservation.py`、`check_loop_seam.py`、`check_loop_seam_states.py`、`check_timeline_invariants.py`、`compose_integration.py`、`finalize_preflight.py`、`finalize_qa.py`、`inspect_timing.py`、`list_frame_shells.py`、`measure_background_picture.py`、`preflight_render.py`、`survey_projects.py`、`test_merge_pipeline.py`、`verify_candidate_audio.py`、`verify_merge.py`、`verify_review_export.py`。

这些脚本的输入全部是"项目已有的 JSON + 固定模板"，没有一行是 eternel 专有知识——即"每个项目重写一遍"。

### 1.2 跨项目重复的直接证据

20 个项目带自写 `project/render/*.py`，数量 1–23 个（kara-no-hako 23、ray-chou-kaguya-hime-study 22、guitar-loneliness-blue-planet 17、zattou-bokura-no-machi-v2 15、dare-ni-mo-narenai-watashi-dakara-v3 14、tsuyogaru-girl 13、kimi-no-kioku-reload 13、naze-nazo-answer 12、uchuu-no-fushigi-v2 9、eternel 8、…）。

同名/近义脚本的重复次数（同一职能被反复实现）：

| 职能 | 出现的脚本名（次数） |
| --- | --- |
| 生成词卡草稿 | `build_card_draft.py`(14)、`create_card_draft.py`(1) |
| 出真实预览图 | `render_setup_preview.py`(2)、`make_draft_preview.py`(3)、`structure_preview.py`(1)、`build_preview_gallery.py`(1)、`build_card_gallery.py`(1)、`render_correction_previews.py`(1) |
| 平台封面 | `render_cover.py`(1)、`render_platform_covers.py`(3) |
| 渲染入口 | `render_final.py`(10)、`render_video.py`(2)、`render_custom.py`(1)、`render_next_line_video.py`(1)、`render_horizontal_rail_video.py`(1) |
| 合并审核结果 | `merge_assisted_review.py`(4)、`merge_assisted_proposals.py`(3)、`merge_approved_review.py`(2)、`integrate_proposals.py`(2)、`merge_approved_proposals.py`(1)、`merge_accepted_proposals.py`(1)、`accept_review.py`(1) |
| 导出/同步审核稿 | `export_confirmed_review.py`(2)、`export_current_review.py`(2)、`export_review_draft.py`(1)、`export_assisted_review.py`(1)、`export_draft_review.py`(1) |
| 标记 QA 通过 | `mark_qa_passed.py`(3) + `mark_qa_r3_passed.py` / `mark_qa_r4_passed.py`、`finish_qa.py`、`finalize_render_qa.py`、`finalize_qa.py`、`finalize_delivery_state.py` |
| 记录内容/显示批准 | `record_content_approval.py`(2)、`record_review_approval.py`(2)、`record_display_approval.py`(1) |
| 复制的 skill 脚本 | 项目内私存 `verify_render_gate.py`(3)、`build_foreground_timeline.py`(3)、`render_foobar_spectrum.py`(3)、`foreground_options.py`(2)、`runtime_font.py`(1) |

还有一批"一次性纠错脚本"，说明逐行人工修补也缺少工具化入口：`correct_l003_fuujikomete.py`、`correct_l006_mienakunatta.py`、`correct_l008_teiru.py`、`correct_hibikukana.py`、`correct_makotoka.py`、`correct_make_noun.py`、`shorten_l050_card.py`、`merge_narrow_card_fix_zu_ni.py`、`merge_narrow_card_fixes.py`、`dedupe_sentence_cards.py`、`fill_remaining_meanings.py` 等。

### 1.3 应上收到 skill 级（建议新增于 `.agent/skills/japanese-song-study-video/scripts/`）

| 建议脚本名 | 输入 | 输出 | 为什么通用 |
| --- | --- | --- | --- |
| `render_real_previews.py` | `PROJECT_ROOT [--samples auto\|list]` | `project/qa/preview-*.png`、`project/qa/structure-report.json` | 合并 eternel 的 `render_setup_preview.py` + `render_draft_previews.py`；对应至少 6 个项目的近义脚本；skill 现有 `preview_learning_aids.py` 只造合成假数据（文件首行自述"isolated synthetic layout QA images"），不能替代真实内容预览 |
| `check_timeline_invariants.py` | `PROJECT_ROOT` | `project/qa/timeline-invariants.json` | eternel 版纯客观断言（连续性、覆盖、3/2/1、prelude、gap、tail），无项目知识；当前 skill 无此脚本 |
| `verify_audio_copy.py` | `PROJECT_ROOT CANDIDATE` | `project/qa/audio-preservation*.json` | eternel 用两份脚本（`check_audio_preservation.py` 预检 30 s、`verify_candidate_audio.py` 全片比对）；「音频不压缩」是可复用硬指标 |
| `finalize_qa.py` | `PROJECT_ROOT CANDIDATE --findings FILE` | `qa-report.json`（`result: passed`） | 替代 `mark_qa_passed.py`(3)+`mark_qa_r3/r4_passed.py`+`finish_qa.py`+`finalize_render_qa.py`；固定"人工结论必须落盘"这一步 |
| `build_review_gallery.py` | `PROJECT_ROOT` | `deliverables/review/<slug>-gallery.html` + 逐行 PNG | eternel `build_card_gallery.py`、guitar `build_preview_gallery.py`；用户逐行审阅是固定需求 |
| `replace_cover.py` | `PROJECT_ROOT --cover FILE --reason TEXT` | 新 `source/cover.jpg` + 归档旧封面 + `source-manifest.json` | eternel `replace_cover.py`；换封面是常态（见 §4） |
| `write_render_plan.py` | `PROJECT_ROOT --run-id ID --authorization-text TEXT` | `project/render/render-plan.json` | eternel `write_render_plan.py`、kara-no-hako `prepare_authorized_render.py` |
| `preflight_render.py` | `PROJECT_ROOT` | `project/qa/render-preflight.json` | eternel `preflight_render.py`：画出全部唯一前景状态 + 2 s 滤镜图试编码，能在授权前发现版式溢出与滤镜错误 |
| `apply_review_merge.py` | `PROJECT_ROOT --accepted FILE --user-wording TEXT` | `frames.json` + `merge-log.json` + `review-decision.json` | eternel 版带 old 值校验与幂等拒绝；替代 7 种 `merge_*`/`integrate_*` 变体 |
| `refresh_after_merge.py` | `PROJECT_ROOT` | 审核 Markdown、`particle-functions.json`、`draft-manifest.json` | eternel 版含"人工改过 Markdown 就拒绝覆盖"的保护 |
| `diff_background_alignment.py` | `MUSIC BACKGROUND REPORT` | 多窗口相关性报告 | eternel 的 `analyze_alignment.py` 直接抄自 `projects/mebuku-toki-alignment/analyze_audio_alignment.py`，已是事实上的共享工具 |
| `check_loop_seam.py` | `PROJECT_ROOT` | `project/qa/loop-seam-report.json` | eternel 两份脚本；`video-loop-follow` 是命名 preset，接缝必然出现 |
| `rehearse_merge.py` | `PROJECT_ROOT` | `project/qa/merge-pipeline-rehearsal.json` | eternel `test_merge_pipeline.py`：沙箱副本演练 + 21 项断言 + 证明真实文件未变，把"用户说采纳后可能失败"提前到授权前 |

配套的架构约束建议：项目内**禁止**再私存 `verify_render_gate.py` / `build_foreground_timeline.py` / `render_foobar_spectrum.py` / `foreground_options.py` 的拷贝（现存 3/3/3/2 份），一律 `sys.path` 引用 skill，避免同一逻辑多版本漂移。

词库侧的现状（已核对，非建议）：`build_lexicon.py` 负责聚合（`workspace_root`、`--out`、`--projects-glob`、`--refresh-order`、`--exclude`），`lexicon_match.py` 负责最长匹配（`--lexicon`、`--text` / `--lines-file`、`--confidence-threshold`、`--min-kana-length`、`--json`）；`lexicon.json` 的 `matchingContract` 写明"longest surface first, then longest kana form"。**缺口**：`lexicon_match.py` 目前只吃文本/行文件，还没有"把命中结果写回 `frames.json` 词卡"的那一步，也未见 adopted/reject 反馈回写词库的实现（`stats.feedbackApplied` 为 0）。

## 2. 可简化或可删除的流程

### 2.1 三角色评审 → 词库匹配 + 单角色定向联网

eternel 阶段 4 的实际产出：lexical 13 条 + grammar 6 条 + translation 3 条 = **22 条提案**，整合为 **30 项操作**（`projects/eternel/project/review/accepted-changes.json`）。逐项看内容：

- 21 项是 `caption.romaji` 重建（QQ 把促音 っ 记成 `'t`），属**机械清理**；
- 5 项是语法标签措辞（「动词＋ゆく（复合）」→「动词连用形＋补助动词ゆく」等），属**术语统一**；
- 2 项助词功能（`二人で`）、1 项重复词卡口径（`結んで`）、1 项卡片合并（`l012` 的 `怯えて` + `いた`）。

也就是说：**没有一条需要三个独立角色才能得出**。其中大部分是"上一次项目已经确认过的结论"，正应由词库直接给出。可简化为：

1. 阶段 3 用词库最长匹配自动填充词卡；
2. 只把「未命中」与「低置信」清单交给**一个**审核角色，允许其联网核对（eternel 的三角色提案里真正联网取证的就是读音/熟字訓/助词功能，单角色足以覆盖）；
3. 删除 `integration` 审计这一层——它的作用是消解三份提案的冲突，单角色模型下不再需要。

**必须同步改代码门禁**：`.agent/skills/japanese-song-study-video/scripts/seal_assisted_review.py:12` 与 `verify_render_gate.py:11` 都硬编码 `REQUIRED_ROLES = {"lexical", "grammar", "translation"}`，且 `verify_render_gate.py:55` 要求审计里 roles 恰好等于该集合。改成单角色模型时，这两处与 `references/04-assisted-review.md` 必须一起改，否则渲染闸门会直接拒绝。

### 2.2 逐行"学习块"注释可由词库复用

eternel 共 101 张卡（合并前 102），其中 `君`、`を`、`の`、`に`、`世界`、`闇`、`夢`、`今`、`だけ`、`は`、`必ず`、`見つける` 这类是日语学习材料的高频词条；词库现有 1773 条，其中 **657 条已有人工确认来源**，这些重复词条本可直接复用。现状却是每个项目在 `project/render/build_card_draft.py` 里手写整张 CONTENT 表（eternel 该文件 28 KB）。

可简化为：

- 词库命中 → 直接复用 `token`/`reading`/`romaji`/`meaning or functionZh`/`grammarStructureZh`/`furigana`，只校验与当前歌词的**上下文一致性**（例如 eternel 的 `結んで` 在两行里口径不同，正是需要这种校验）；
- 未命中 → 生成新卡并进入审核，采纳后写回词库并更新 `reliability`；
- 项目内只保留"项目特有覆写"，不再重复写全表。

### 2.3 可合并或删除的具体步骤

| 现状 | 建议 | 依据 |
| --- | --- | --- |
| 三套预览：`render_setup_preview.py`（setup）+ `render_draft_previews.py`（draft 六类）+ `build_card_gallery.py`（逐行） | 合并为 `render_real_previews.py` 一次产出 | 三者都是"真实渲染器 + 时间轴 + 背景帧 + 频谱"的合成 |
| QA 收尾 6 种脚本（`mark_qa_passed.py` 等） | 一个 `finalize_qa.py` | 全仓 60 份 `qa-report.json`，其中 46 份 `result: passed`，流程完全一致 |
| `merge_*` / `integrate_*` / `accept_review` 共 7 类 | `apply_review_merge.py` | eternel 版已验证可幂等拒绝重复执行（`merge-pipeline-rehearsal.json` 21/21） |
| 手工维护 `project/particle-functions.json` | 由最终词卡自动重建 | eternel `refresh_after_merge.py` 已实现，并把 `status` 从 `draft` 改为 `confirmed` |
| 项目内复制 skill 脚本 | 强制引用 skill | 现存 `verify_render_gate.py`(3)、`build_foreground_timeline.py`(3)、`render_foobar_spectrum.py`(3) 等副本 |
| `project/work/inputs-v1/` 的 19 个一次性脚本 | 上收 skill，项目内只留证据 JSON | 其中 8 个是通用检查（见 §1.3），其余是读取/打印 |
| 逐行纠错脚本（`correct_*.py`、`shorten_l050_card.py` 等） | 改为"accepted-changes 操作 + 预览重出" | 10 个此类脚本说明缺少统一的行级修改入口 |

### 2.4 封面 r01→r04 的返工说明了什么

eternel 的封面/配色共产生 **4 轮**导出报告（`project/qa/cover-report-setup-r01-hires.json`、`-r02-artwork.json`、`-r03-palette.json`、`-r04-subtitle.json`），`project/work/cover-archive/` 里留下 6 张被替换的封面 PNG。原因不是执行错误，而是**阶段 1 没有冻结封面的"内容定义"**：`project/render/cover-content.json`（`title`/`artist`/`subtitle`/`badges`）与"调色板是否跟随封面画作"这两个决策，是在阶段 2 之后、甚至渲染之后才由用户陆续给出的。

这是全仓的普遍现象，而非 eternel 独有：mayocchauwa 有 7 份 cover report、`deliverables/final` 里累积 28 张封面 PNG；dare-ni-mo-narenai-watashi-dakara-v3 有 5 份 report / 10 张封面 PNG；全仓 `deliverables/final` 现有 66 个成品视频与 106 张封面 PNG。

## 3. 目标流水线

标记：**[自动]** 无需人工；**[用户]** 必须显式决策；**[建议新脚本]** 目前不存在。

### 阶段 0：词库（每个新采纳批次后跑一次）

| 步骤 | 命令 | 产物 | 可验证证据 |
| --- | --- | --- | --- |
| 聚合词库（已存在） | `python .agent/skills/japanese-song-study-video/scripts/build_lexicon.py . --out lexicon/lexicon.json` | `lexicon/lexicon.json`、`lexicon/project-order.json` | 已核对：`stats.projectsScanned: 24`、`entries: 1773`、`humanConfirmedEntries: 657`、`largestAmbiguity: 12` |
| 留一覆盖测试（已存在的参数） | 同上加 `--exclude <slug>` | 去掉该项目后的词库 | 用于诚实评估"新项目能命中多少"，`stats.projectsSkipped` 记录被排除项 |
| 反馈回写（**未实现**） | — | — | `stats.feedbackApplied: 0`，尚无 accept/reject 回写路径 |

词条字段（已核对）：`surface`、`kana`、`kind`、`dominantMeaning`/`dominantGrammar`/`dominantReading`/`dominantRomaji`、`meaningField`/`grammarField`、`dictionaryForm`、`sourceWord`、`showJlpt`、变体列表 `meanings`/`grammars`/`readings`/`romajis`（各带 `count`、`humanConfirmed`、`projects`、`lastSeenAt`、`recencyRank`）、`sources`、`humanConfirmed`、`projectCount`、`accepts`、`rejects`、`ambiguity`、`recencyRank`、`lastSeenAt`、`reliability{score, sources, humanConfirmedSources, ...}`、`provenance`。冲突规则为"newest source wins per field; a human-confirmed source breaks same-second ties"，变体规则为"all attested meanings/grammars/readings are kept"。

### 阶段 1：输入与图层 **[自动，除封面文案]**

| 步骤 | 命令 | 产物 | 可验证证据 |
| --- | --- | --- | --- |
| 冻结输入 | `python .agent/skills/.../freeze_inputs.py PROJECT_ROOT --slug SLUG --music ... --background ... --qm ... --qm-roma ... --qmts ...` | `source/source-manifest.json`、`project/input-manifest.json` | 每个 asset 的 sha256/bytes/probe |
| 图层配置 | `python .agent/skills/.../configure_layers.py PROJECT_ROOT --preset video-loop-follow --spectrum on --learning-assist on --prelude-mode first-line --offset-mode manual --offset-ms N --offset-reason "..."` | `scene-timeline.json`、`presentation.json`、`templates/*` | `validate_project.py --stage setup` |
| 对齐取证 | `python .agent/skills/.../detect_audio_offset.py MUSIC BACKGROUND REPORT` 或 **[建议新脚本]** `diff_background_alignment.py` | 相关性报告 | 多窗口一致性与中位偏移（eternel：16 个强窗口、14 个落在 80 ms 内、+0.004 s） |
| **封面文案与调色板策略 [用户]** | 一次性确认 `title`/`artist`/`subtitle`/`badges` 与"palette 是否跟随封面" | `project/render/cover-content.json` | 该文件写定后即冻结；避免 §4 的多轮重出 |

### 阶段 2：解码与准备 **[自动]**

| 步骤 | 命令 | 产物 | 证据 |
| --- | --- | --- | --- |
| 解码歌词 | `normalize_lyrics.py PROJECT_ROOT [--exclude-prefix ...]` | `project/timing/*.json`、`frames.json` 骨架、`decode-report.json` | 行数、可用时序（eternel：28 行 → 排除 3 行署名 → 25 行） |
| setup | `prepare_setup.py PROJECT_ROOT` | `palette.json`、`resolved-layout*.json` | `PASS setup` |
| 真实预览 **[建议新脚本]** | `render_real_previews.py PROJECT_ROOT` | `qa/structure-preview-16x9.png`、`structure-report.json` | 目视 + 报告 |

### 阶段 3：词库匹配与定向审核 **[自动 + 一次用户决策]**

| 步骤 | 命令 | 产物 | 证据 |
| --- | --- | --- | --- |
| 词库最长匹配（匹配器已存在，写回**待实现**） | `python .agent/skills/japanese-song-study-video/scripts/lexicon_match.py --lexicon lexicon/lexicon.json --lines-file <行文本> --confidence-threshold <N> --json` | 命中/未命中/低置信清单 | 命中率、`ambiguity`、`reliability.score`；把命中写回 `frames.json` 的那一步尚无脚本 |
| 定向联网审核（仅未命中/低置信） | 单角色 agent，产出 proposals JSON | `project/review/proposals/review.json` | 每条含 URL 与所支撑的断言 |
| 逐行审阅页 **[建议新脚本]** | `build_review_gallery.py PROJECT_ROOT` | `deliverables/review/<slug>-词卡逐行预览.html` + PNG | 用户逐行查看（eternel 实测有效） |
| **内容采纳 [用户]** | 用户回「采纳」或按行给修改 | `project/review/accepted-changes.json` | 逐字段 old → new，可机械校验 |
| 应用合并 **[建议新脚本]** | `apply_review_merge.py PROJECT_ROOT --user-wording "..."` | `frames.json`、`merge-log.json`、`review-decision.json` | 幂等拒绝重复执行 |
| 刷新派生物 **[建议新脚本]** | `refresh_after_merge.py PROJECT_ROOT` | 审核 Markdown、`particle-functions.json`、`draft-manifest.json` | 哈希一致；人工改过则拒绝覆盖 |
| 封存 | `seal_assisted_review.py`（角色集合需按 §2.1 改造） | `assisted-review-audit.json` | 提案与整合报告 sha256 |

### 阶段 5：渲染、QA、交付 **[自动，除渲染授权]**

| 步骤 | 命令 | 产物 | 证据 |
| --- | --- | --- | --- |
| 渲染计划 **[建议新脚本]** | `write_render_plan.py PROJECT_ROOT --run-id ID` | `project/render/render-plan.json` | 17 项哈希（eternel 实测） |
| **渲染授权 [用户]** | 用户明确说「确认渲染」 | — | — |
| 绑定授权 | `authorize_render.py PROJECT_ROOT --authorization-text "用户原话" --renderer .../render_video.py` | `project/render-authorization.json` | 声明 17 项哈希 |
| 预检 **[建议新脚本]** | `preflight_render.py PROJECT_ROOT` | `qa/render-preflight.json` | eternel：292 个状态零失败、约 36 s、滤镜图 2 s 试编码通过 |
| 渲染 | `render_video.py PROJECT_ROOT --run-id ID --canvas 16x9` | `project/work/ID/16x9/<slug>--16x9--ID.mkv` + `render-report.json` | `audioCodecPolicy: stream-copy`、`layers` |
| 抽样 QA | `collect_qa.py PROJECT_ROOT CANDIDATE QA_DIR` | 15+ 张截图 + `qa-report.json`（pending） | 截图清单与时间戳 |
| 视觉结论落盘 **[建议新脚本]** | `finalize_qa.py PROJECT_ROOT CANDIDATE --findings FILE` | `qa-report.json`（passed） | 结论条数（eternel 11 条） |
| 音频取证 **[建议新脚本]** | `verify_audio_copy.py PROJECT_ROOT CANDIDATE` | `qa/audio-preservation-candidate.json` | 全片解码 PCM 与源 FLAC 逐字节相同（eternel：36,657,628 B，sha256 `11f8fa61…`） |
| 结构校验 | `validate_project.py PROJECT_ROOT --stage render --renderer .../render_video.py` | 终端 `PASS render` | — |
| 交付 | `promote_final.py PROJECT_ROOT CANDIDATE QA_REPORT` | `deliverables/final/<name>.mkv`、`project/final-manifest.json` | 候选哈希一致才复制 |

**两处人工决策**：内容采纳（阶段 3）与渲染授权（阶段 5）。其余全部可自动化。封面导出可与阶段 3/5 并行，但文案必须在阶段 1 冻结。

## 4. 返工成本

eternel 本次的实际返工（数字均可在项目内核对）：

| 轮次 | 触发 | 重跑了什么 |
| --- | --- | --- |
| r01 | 初次（内嵌封面 + 橄榄黄调色板） | 25 张逐行静帧、6 张 draft 预览、1 次渲染预检（292 状态）、时间轴不变量、16:9 + 4:3 封面 |
| r02 | 用户换封面画作（500×500 新图） | 封面重出 + **再次**重跑上述全部预览/预检/时间轴检查 |
| r03 | 用户改调色板（跟随新封面，橙色系） | 封面重出 + **第三次**重跑全部预览/预检 |
| r04 | 用户改副标题（「恋死 ED」） | 仅封面重出；但改动了 `project/input-manifest.json`，使 `inputManifestSha256` 变化，渲染闸门随即以 `Render authorization hash missing or stale: inputManifestSha256` 拒绝新渲染（成品视频未受影响） |

另有流程性重跑：3 次修复 `python -c` 引号/路径错误、渲染预检 2 次、合并流程沙箱演练 1 次（21 项断言全过）。**视频本身只渲染了 1 次**——返工全部集中在封面/配色与"证据重出"上。

避免返工的建议：

1. **把封面的内容定义前移到阶段 1**：`title`/`artist`/`subtitle`/`badges`/画作与"palette 是否跟随封面"一次确认；之后任何文案改动都视为新决策并记入 build-state。
2. **封面文案只存 `project/render/cover-content.json`，不要写进 `project/input-manifest.json`**：eternel 把 `coverExport.subtitle` 写进 manifest，导致纯导出参数的变化作废了渲染授权哈希（本次的教训）。
3. **区分"影响视频的输入"与"仅影响导出的输入"**：调色板影响视频卡片配色，属于前者；封面文案属于后者。前者变更必须重跑预览与预检，后者只重跑封面导出。
4. **交付目录只放当前版本**：eternel 结束后把 r01–r03 封面移入 `project/work/cover-archive/`；反例是 mayocchauwa 的 `deliverables/final` 累积了 28 张封面 PNG。
5. **授权后不要动任何被绑定的文件**：`authorize_render.py` 绑定 17 项哈希；渲染完成后再改 `input-manifest.json`、`palette.json`、`frames.json` 都会使授权失效（这是设计上的保护，但要事先规划好编辑顺序）。

## 5. 未验证与风险

- 词库已完成聚合（1773 条、657 条人工确认），但**匹配结果写回 `frames.json` 的环节尚未实现**，也没有 `accepts`/`rejects` 的反馈回写路径（`stats.feedbackApplied: 0`）；`lexicon_match.py` 的 `--text` / `--lines-file` 接口与"逐行最长匹配 + 上下文一致性校验"之间的衔接需要补设计。
- 三角色评审 → 单角色定向审核的改造，会与 `seal_assisted_review.py`、`verify_render_gate.py` 的 `REQUIRED_ROLES` 硬编码及 `references/04-assisted-review.md` 冲突，必须同步修改。
- 词库最长匹配的上下文风险未量化：eternel 的 `結んで`（l007 vs l020）与 `明けゆく`（l010 谓语用法 vs l021 连体用法）说明**同一词条在不同上下文可能需要不同释义**，命中后仍需一致性校验步骤；词库的 `variantRule` 只是"保留全部变体 + 主选规则"，并不解决句中语境选择。
- 本文件未修改任何代码、配置或项目数据；所有统计为只读扫描结果。写作期间有并行任务在同一工作区写入 `lexicon/` 与两个词库脚本，本文档按核对时的状态描述（`lexicon.json` 生成时间 2026-09-11T15:39Z），后续可能继续变化。

## 6. 落地进度（写作后更新）

§1.3 的 5 条脚本已上收为 skill 级通用脚本（`.agent/skills/japanese-song-study-video/scripts/`），全部用 eternel 真实数据实测通过：

| 建议脚本 | 已落地文件 | 实测结果 |
| --- | --- | --- |
| `render_real_previews.py` | `render_real_previews.py` + 共享模块 `preview_render.py` | 9 张 setup + 6 张 draft 预览 |
| `check_timeline_invariants.py` | `check_timeline_invariants.py` | passed，336 段 / 292 状态 / 0 问题 |
| `verify_audio_copy.py` | `verify_audio_copy.py` | 20 s 探针 `bitExact: true`（全片版默认全比） |
| `finalize_qa.py` | `finalize_qa.py` | 标记 passed + 重复调用返回 `already-passed` |
| `build_review_gallery.py` | `build_review_gallery.py` | 25 张静帧 + 30 项提案标注（正确选中 `approved-r01` 时间轴） |

同时已落地的还有：`build_lexicon.py`、`lexicon_match.py`、`draft_cards_from_lexicon.py`、`apply_lexicon_feedback.py`、`seal_lexicon_review.py`，以及 `verify_render_gate.py` 的双模式改造（`mandatory-multi-agent` / `lexicon-rag-targeted-online`）。

§5 的两条"未验证"已解决：匹配结果写回 `frames.json`（`draft_cards_from_lexicon.py`）与 accepts/rejects 反馈回灌（`apply_lexicon_feedback.py` + `build_lexicon.py` 的评分项）均已实现并实测；`REQUIRED_ROLES` 冲突已按 §5 的提示同步处理（`verify_render_gate.py` 拆成 `verify_multi_agent_audit` / `verify_lexicon_audit`，历史项目仍通过）。

仍未做：§1.3 的其余 8 条（`replace_cover`、`write_render_plan`、`preflight_render`、`apply_review_merge`、`refresh_after_merge`、`diff_background_alignment`、`check_loop_seam`、`rehearse_merge`）仍只存在于 `projects/eternel/project/` 内；以及"禁止项目内私存 skill 脚本副本"的清理尚未执行。

### 6.1 第二批上收（8 个脚本）

`replace_cover.py`、`write_render_plan.py`、`preflight_render.py`、`apply_review_merge.py`、`refresh_after_merge.py`、`diff_background_alignment.py`、`check_loop_seam.py`、`rehearse_merge.py` 已全部上收为 skill 脚本并用 eternel 真实数据实测：对齐复现 0.004 s/16 窗口；预检 292 状态 0 失败 + 滤镜图 passed；接缝 2 处均在句中；彩排在沙箱 9/9 通过、真实文件逐字节未变、对已合并项目如实报 `stale-accepted-set`；换封面在沙箱完成 r03 归档与来源记录。`SKILL.md` 增补规则：共享工具必须用 skill 脚本，项目内副本只允许用于确属项目专属的渲染器，且须在 build-state 写明理由。

### 6.2 流程规则落地（§4 建议 1、2）

`references/01-inputs.md` 新增「Freeze what a later edit would otherwise re-open」与「Keep export-only settings out of the manifest」两节：封面文案/画作版本与「调色板是否跟随封面」在阶段 1 一次冻结；封面文案只存 `project/render/cover-content.json`，`input-manifest.json` 只保留媒体、输出与对齐。`references/07-covers.md` 同步该约束并补上 `replace_cover.py`。eternel 的 `input-manifest.json` 已按新规则清理（`coverExport` 移出，徽章与副标题保留在 cover-content.json，成品哈希不变）。

### 6.3 读取成本优化

`collect_qa.py` 新增**联系图（contact-sheet.png）**：16 张抽样合成一张带标签的网格图，先看网格、只在异常处点开单图，把逐张读图成本降到约 1/16；同时修正了邻句抽样（原按「中间帧」取样常落进空白段，改为「显示帧发生变化的首个状态」前后各取一帧），并把语义含混的 `persistent-gap` 更名为 `line-hold`。
