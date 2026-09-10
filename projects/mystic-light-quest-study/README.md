# Mystic Light Quest

当前阶段：日文正文逐字高亮版 character-v2 已重新渲染并通过成品QA；旧版 approved-v1 保留。

跨设备整理：局部渲染器已改用项目内固定依赖，字体可通过 STUDY_FONT 指定。旧入口/授权已归档至 project/render/pre-portability-snapshot；现有视频和内容未改，未来渲染需核验本机环境并重新绑定当次授权。接续步骤见仓库根 TRANSFER.md。

新规则：仅日文歌词正文使用QRC逐字高亮（353个独立单字时间片）；假名、罗马音仍按词，英文保持原QRC高亮，词卡不高亮。审核内容与时码不改。证据：`project/qa/character-highlight/qa-report.json`。旧版配置和渲染器已归档到 `project/work/approved-v1/config-snapshot/`。

最新视频：`deliverables/final/mystic-light-quest-study--16x9--character-v2.mkv`。
旧版视频：`deliverables/final/mystic-light-quest-study--16x9--approved-v1.mkv`。
规格：1920×1080，CFR 30 fps，207秒；FLAC 48kHz/24-bit/双声道无损音轨。成品PCM与原WAV完全一致，FLAC数据包也与源FLAC一致。
最新成品QA：`project/qa/character-v2/qa-report.json`、`extra-qa.json`；最终文件哈希及规格：`project/final-manifest.json`。19张成品截图已检查，连续こ/こ逐字切换正常；6210帧CFR与无损音轨逐项核验通过。

- 音频：原 WAV 已保留；无损 FLAC 为 48 kHz / 24-bit / 双声道，时长 207 秒。转换前后 PCM SHA256 完全一致。
- 背景：原 MV 已保留；六段相关性分析确认前置偏移 3064 ms。派生视频裁去片头，时长 207 秒，素材音轨已移除。
- 预设：video-loop-follow，全程视频，无频谱。音乐与歌词从各自零点开始；有歌词时显示学习前景及黑色半透明蒙层。
- 歌词：QQ Music QM、Roma、QMTS 均已归档并解码。剔除 4 行标题及制作信息，保留 42 句，中文保持 QMTS 原文。
- 封面：WAV 无内嵌图片，使用 MV 80 秒处角色画面裁成正方形，提取主题色；平台封面输出 16:9 和 4:3，使用既有金色 Hi-Res 标志。

当前审核版：`deliverables/review/mystic-light-quest-study-approved-review.md`。
历史提案：`deliverables/review/mystic-light-quest-study-consolidated-review.md`（保留原提案前后对照）。
完整草稿：`deliverables/review/mystic-light-quest-study-review.md`。
已合入31组字段修改，当前42句、136张已确认词卡；整句QMTS不改。采纳记录及前后哈希位于 `project/review/merge-log.json` 和 `review-decision.json`。
封存审核：`project/review/assisted-review-audit.json`；可执行整合提案：`project/review/recommended-proposals.json`。
初始检查：`project/qa/setup-acceptance.json`。
音频裁剪证据：`project/alignment/video-intro-trim.json`。

历史准备记录：42张草稿透明前景位于 `project/qa/spaced-draft-frames/`；l008/l029的注音及罗马音间距已修复。所有帧重叠检查通过，英文高亮、最大词卡句和实际背景合成静态抽查通过。证据：`project/qa/spacing-check.json`。内容、QRC时码、词卡和封面未改。
使用项目局部渲染器 `project/render/render_video.py` 及哈希绑定的 `foreground_layout.py`；不要回退到有重叠问题的共享渲染器。后续渲染授权需明确绑定此局部入口。
审核版的42张静态前景位于 `project/qa/approved-frames/`，检查报告 `project/qa/approved-layout-check.json` 已通过。l018唱读、l025整词卡及注音锚点、重复词卡一致性均已核验。卡义支持固定字号的均衡两行换行，避免括号独占末行。
本次渲染已显式授权并完成。实际背景时间轴已修正为 `source/background-trimmed.mp4`，不再误用未裁片头的原视频。后续任何内容、模板或渲染配置变更均需重新绑定渲染授权并验收。
