# 日语歌曲跟读视频项目归档

本仓库是私有工作区，**只保留两个已完成项目**：`kimi-no-kioku-reload` 与 `murimuri-shinkaron`。

其余项目只保留在作者本机，由根目录 `.gitignore` 的 `/projects/*` 规则排除（本机现有 34 个，含 love-2000、uchuu-no-fushigi、feel-my-soul、mystic-light-quest-study、eternel、koeru、remember 等）。**不要重新把它们加入 git 或上传**；它们的本地文件没有删除，只是不在仓库里。

核对范围时：

```sh
git check-ignore -v projects/<slug>/project/frames.json   # 非保留项目应命中 /projects/*
git ls-tree origin/main projects/ --name-only             # 远端应只有 README.md 和上面两个项目
```

## 目录结构

每个项目保留三类副本：

- `source/`：用户提供的音频、视频、QRC 和封面来源，冻结原件、字节不改，附 `source-manifest.json`（原始路径、sha256、探测结果）。
- `project/`：`frames.json`（唯一语言与渲染内容源）、`input-manifest.json` / `scene-timeline.json` / `presentation.json` / `palette.json`、模板快照、审核与授权证据、`qa/`。
- `deliverables/`：最终视频、各比例封面、审核文档。

`deliverables/final/` 只放当前成品；被取代的版本若仍在目录里，以 `project/final-manifest.json` 记录的为准。

媒体（音频、视频、封面、成品）走 Git LFS。clone 后必须 `git lfs pull`，再 `git lfs fsck`：LFS 指针文件不等于素材已下载。

## kimi-no-kioku-reload

- 歌曲：キミの記憶 -Reload-（你的记忆）— 高橋あず美／アトラスサウンドチーム／ATLUS GAME MUSIC，出自「ペルソナ3 リロード」LIMITED BOX ORIGINAL SOUNDTRACK。
- 音源：`source/music.mp3`（44.1 kHz，内嵌 720×720 封面），399.53 秒。用户要求音频不压缩，成品按流复制、未重编码。
- 背景：`source/background.mp4` 与 `source/background-0{2..5}-*.mp4`（Makoto / Kotone / Yukari / Mitsuru / Fuuka 主题动态壁纸），自定义时间轴。
- 内容：64 行学习歌词；逐字时间轴 64 个 QRC 完整匹配、0 未匹配行；64 个审核帧全部通过；用户要求关闭封面角标。
- 当前成品：`deliverables/final/kimi-no-kioku-reload--16x9--approved-r3-persistent-countdown-dedup.mp4`（1920×1080 CFR 30 H.264 + MP3 流复制，399.5 秒）。
- 封面：`deliverables/final/kimi-no-kioku-reload--cover-16x9--approved-cover-r1.png`、`kimi-no-kioku-reload--cover-4x3--approved-cover-r1.png`。
- 早期成品 `--approved-r1.mp4` 仍在 final 目录中，但已被 r3 取代。

## murimuri-shinkaron

- 歌曲：ムリムリ進化論 — 七音阿卡莉（NANAOAKARI）。
- 音源：`source/music.flac`（96 kHz / 24-bit / 2ch），194.933 秒；成品 FLAC 流复制、不重编码。
- 背景：`source/background-stage1.mp4`（该曲 OP 影像，源音频静音）；89.899 秒后切换为封面高斯模糊场景。透明频谱浮层始终位于背景与学习内容之上。
- 内容：QRC 三轨解码（100 原词行 / 96 罗马音行 / 63 译文行，日文与罗马音为逐字时间）；96 个歌词帧；用户以「整体采纳」授权整合提案集、以「确认渲染」授权成品。
- 当前成品：`deliverables/final/murimuri-shinkaron--16x9--20260822-r02-stage2-retain-last.mkv`（1920×1080 CFR 30 H.264 + FLAC 96 kHz / 24-bit 流复制）。
- 封面：`deliverables/final/murimuri-shinkaron--cover-{16x9,4x3,3x4,9x16}--20260822-cover-v1.png`。
- 上一版 `--20260822-r01-final-flac.mkv` 已被取代：r02 在间奏保留最后一条完整前景。

## 渲染与授权

视频由仓库内 skill（`.agent/skills/japanese-song-study-video/`）的渲染器生成：Pillow 逐状态画 RGBA 前景帧，FFmpeg 用 concat 时间轴展开、叠加背景与频谱并编码（视频 libx264，音频流复制进 MP4/MKV）。

重渲染前必须按 skill 第 5 阶段用用户原话重绑 `project/render-authorization.json`。输入、内容、模板或渲染器哈希变化会让旧授权失效，这是设计上的防护，不代表审核丢失；已交付的成品不受影响。历史项目使用其本地渲染器副本（`project/render/`），不要用全局模板覆盖。
