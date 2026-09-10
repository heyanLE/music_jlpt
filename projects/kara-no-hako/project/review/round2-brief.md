# 空の箱：第二轮独立智能复审

用户要求：有一些修改部分不太行，参考 dare-ni-mo-narenai-watashi-dakara-v3 项目的格式重新启动智能多角色审查。

## 基准与边界

- 正式内容唯一基准：project/frames.json。上一轮提案不是已接受的内容，不预设正确。
- 参照 projects/dare-ni-mo-narenai-watashi-dakara-v3/project/frames.json、deliverables/review/*-confirmed-review.md 和 *-correction-review.md。不要参照含“待联网核对”的旧 assisted-review 草稿。
- 只提交提案；不修改正式 frames、上一轮提案、时间轴、模板或音频。
- 各角色覆盖全部 45 句；允许联网，优先发布者词典、国立国语研究所、东京外大等。网络证据和推断区分，未实际听辨不得写“唱读确认”。

## 教学卡目标

- 词条｜读音｜罗马音｜中文含义／助词功能｜词性或简明结构。
- 名词直接给中文；纯助词给具体语境功能；实词与助词组合可给整个短语含义，不把名词含义抹成抽象功能。
- 词性不能被日文公式完全替代，例如需要保留“动词（可能形）”等身份信息。不要为修改而修改同义标签。
- 重新检查学习单元：固定搭配与完整活用宜保留；过长、包含几个可独立学习结构的块可以提出拆分。不是机械拆成每个字，也不为凑卡数合并。
- 罗马音使用可读词/语法块空格；不要拆坏一个音节、促音，不能只是空格大改而不审词义。
- 顶部仅汉字振假名；熟字训作为整体标注并在词卡结构中说明（仍需分类证据）；纯假名不注音。片假名和外来语不能等同，コタエ、カタチ不加英语词源。
- 第三字段与 token 单行；中文最多两行。为短卡保持简洁，将语法讨论放审核说明，不堆进卡片。
- 以日文完整上下文解释词卡；QQ 中文可能跨行调序，不能把该行中文机械分配给日文词卡。
- QQ 整句中文保持原样。疑似错译单独列 sourceTranslationIssues，非默认词卡采纳范围。

## 输出与分工

每个角色独立写 project/proposals/round2/<role>.json，满足 skill 的 schemaVersion 2、reviewRole、scope.frameIds、baseFrameSha256、changes 合同，并附 frameAssessments（45句逐句实质结论）、sources、uncertainties。

- lexical：词边界、假名、罗马音、熟字训、外来语；结构变化可以用 field=grammarCards 的完整数组替换并同步 caption.furigana/caption.romaji 提案，changesTokenStructure=true；保留元数据。不要仅做空格风格替换。
- grammar：词性、活用、助词功能、合理拆并。可以对 grammarCards 数组给方案；每个变更写目标 token，方便跨角色结构冲突整合。
- translation：中文卡义自然且贴合日文，跨句关系，重复一致。阅读 QQ 全句作参考；源译建议单列，不直接替换 caption.translationZh。

各变更 old 必须精确匹配基准。新增字段 old=null；删字段使用 remove=true。结构提案应包含读音、罗马音、简短含义/功能和结构，便于实际审阅。其他字段可用精确下标路径。

主代理做独立整合，显式处理冲突/拆分映射，再封存新轮次；不会把多数意见视为用户批准。
