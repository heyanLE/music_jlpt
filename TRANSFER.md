# 跨设备接续

目标仓库：`https://github.com/heyanLE/music_jlpt`。用户确认私有，允许上传素材；不要改变公开性。

## 下载和检查

先在新设备安装 Git 与 Git LFS，再 clone，不要只下载 ZIP：

```sh
git lfs install
git clone https://github.com/heyanLE/music_jlpt.git
cd music_jlpt
git lfs pull
git lfs fsck
```

Git LFS 指针不等于素材下载成功。用本机 Python 3.10+ 创建虚拟环境，安装 `.agent/skills/japanese-song-study-video/requirements.txt`；将 FFmpeg/ffprobe 加入 PATH。Node/npm 只用于需要重新解密的 QRC；已有解码文件不用重复导入。不要重新初始化历史项目。

```sh
python -B .agent/skills/japanese-song-study-video/scripts/check_runtime.py
python -B .agent/skills/japanese-song-study-video/scripts/inspect_project.py projects/mystic-light-quest-study --renderer projects/mystic-light-quest-study/project/render/render_video.py
```

当前模板字体为微软雅黑粗体 `msyhbd.ttc`、index 0。不随仓库分发微软字体。Windows 通常已有；其他系统需自行提供有权使用的字体并通过环境变量 `STUDY_FONT` 指向它。替代字体需要检查文字宽度、注音位置和长词卡，不能声称像素一致。运行时版本/字体哈希保存在本机检查报告，不要从旧机器复制可执行程序路径。

## 当前工作项目

`projects/mystic-light-quest-study`：42 句、136 张审核卡；日文逐字高亮，假名/罗马音按词、英文保持 QRC 单元高亮；无频谱，全程裁剪后 MV。旧项目没有邻句/倒计时/前奏内容，不启用新项目默认值。

已完成视频：`deliverables/final/mystic-light-quest-study--16x9--character-v2.mkv`，1920×1080 / 30 fps / 207 秒，FLAC 48 kHz / 24-bit 双声道。文件 SHA256：`77567226ff7430c88984acfc2b42a0182ea01a5a2a0978c6fc0f79f749fec019`。旧版成品也保留。

本次迁移只把局部渲染器的跨目录依赖固定到 `project/render/runtime/`，支持显式字体路径；没有修改歌词、审核内容、时间、颜色和成品。迁移前入口及授权在 `project/render/pre-portability-snapshot/`。现成视频仍有效；代码依赖变化使未来渲染授权失效，这是预期的防护，不是审核丢失。重新渲染必须先完成布局/时间轴检查并按当次请求重绑授权，不能改哈希来掩盖差异。

## 同步边界

同步：各项目 source、配置/时间轴/模板、直接编辑的审核稿、提案/采纳证据、项目脚本、QA 报告和代表截图、成品视频及封面。所有媒体使用 Git LFS。

不上传：本机安装依赖、node_modules、python-site、虚拟环境、生成的逐帧/候选缓存、根目录 scratch/output/旧 skill 安装备份；未删除这些本地文件。project/work 中独有的脚本和文本证据保留，不可据此认为里面所有旧绝对路径脚本都已跨平台改造。

其他历史项目原样归档，未逐个迁移其硬编码路径。打开目标项目后先检查 active manifest、源素材和实际 renderer；只修复该项目需要的路径，不用全局新模板覆盖旧项目。已忽略的渲染候选可从 final 或源素材重建；封存审核依赖若缺文件则停止，不能伪造确认。

字节保持：`.gitattributes` 禁止自动换行转换，避免 JSON 审核哈希失效。不要在迁移时格式化全部文件。基本敏感信息检查不能替代人工保密审核。

## Skill 入口

仓库唯一维护版：`.agent/skills/japanese-song-study-video/SKILL.md`。根 `AGENTS.md` 让新上下文读取它，不依赖旧用户目录。Codex 官方自动扫描目录是 `.agents/skills`（复数），本仓库按用户要求保留 `.agent`，用 AGENTS.md 显式入口；不要维护两份分叉版本。
