# 空の箱（井芹仁菜、河原木桃香）

- 前景：已确认的 A 版——左上封面、右上下一句假名／歌词／分词罗马音；当前句与词卡保持原模板字号。
- 背景：视频播放一次，96.114 秒处以 500 毫秒仅背景淡出淡入切换到封面高斯，持续至 183.844 秒。
- 前景显隐：视频段跟随歌词；高斯段保留上句；预读跟随前景，没有下一句时隐藏预读。
- 频谱：底部透明 Foobar 跳动柱，全程独立于前景显隐。
- 音频：原 FLAC 48 kHz / 24-bit 保留；最终 MKV 内 stream-copy，不转 AAC、不裁母带静音。
- 封面：16:9、4:3，沿用金色 Hi-Res 角标。浅色纸面文字用封面同色系深金色，视频保持亮黄色。
- 内容：45 句、153 张第二轮已确认词卡；中文原样来源 QQ 翻译轨。

## 审核文件

- **当前已确认第二轮**：`deliverables/review/kara-no-hako-round2-confirmed-review.md`（dare-v3 格式完整 45 句）。
- `deliverables/review/kara-no-hako-round2-source-translations.md`：7 组 QQ 中文疑点，需另行决定，不随词卡默认采纳。
- 第二轮证据：`project/proposals/round2/`、`project/review/round2-integration-report.json`、`project/review/merge-log.json`。153 张词卡已采纳；尚未授权渲染。
- 第一轮输出保留作历史，`project/review/round1-archive/` 保存上一轮审核封存。不要把旧 `integration-report.json` 或旧 `integrate_review.py` 当成本轮合并入口；从当前 `assisted-review-audit.json` 读取有效提案路径。
- `deliverables/review/kara-no-hako-review.md`：完整初稿。
- `project/proposals/`：三个角色的独立建议；不是已采纳内容。
- `project/review/`：基准哈希、整合审核和后续用户决定。

## 重要

新预读格式和第二轮词卡已得到用户确认。授权成片 `deliverables/final/kara-no-hako--16x9--round2-approved-r1.mkv` 已通过 QA 并交付；不得把本项目审批复制给其他项目。
本项目的 `project/templates/foreground.json` 含预读扩展；不要重跑初始化覆盖该快照。
最终渲染入口为 `project/render/render_next_line_video.py`。它复用固定合成流程、调用通用审核授权门禁并锁定依赖哈希；不能直接调用忽略预读扩展的旧前景。当前仅完成语法和未授权拒绝检查，没有执行最终合成。
