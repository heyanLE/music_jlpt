# 13 - 视频简介（交付件）

简介是**交付物的一部分**，每次出片都要同步产出，且必须由项目自身数据生成、不许手抄：
数据一旦分叉，简介就会和成品不一致（例如把 16-bit 母带写成 24-bit）。

```bash
python SKILL_ROOT/scripts/write_video_description.py PROJECT_ROOT
# 只打印不落盘：--print-only；指定路径：--out FILE
```

产物：`deliverables/final/<slug>--description.txt`，同时打印所用字段便于核对。

## 模板（系列固定）

**中间不留空行**：整段是连续的行，平台会自行分段。

```
《{title}》- {artist} ({artistReading})（《{workName}》{songRole} {version}）
📌 ：{credits}
🎧 ：{audio}，{losslessTip}
📖 ： {features}。
 {tip}
{closing}
```

默认文案（可用项目覆盖）：

| 字段 | 默认值 |
|---|---|
| `credits` | `歌词：QQ音乐 \| 文法：ds大肥鱼和我 \| 校对：大家` |
| `losslessTip` | `PC 建议开启无损音质食用~` |
| `baseFeatures` | `歌词 KTV 跟随`、`假名`、`罗马音`、`中文翻译`、`文法提示` |
| `tip` | `（建议直接跟唱熟悉发音，再过一遍文法解析，学唱背词更轻松~）` |
| `closing` | `觉得有用欢迎点赞收藏，想继续看可以关注支持一下！` |
| `version` | `完整版` |

## 每期需要填的项目字段

写在 `project/render/description.json`（缺项走默认）：

| 字段 | 说明 | 例 |
|---|---|---|
| `workName` | 作品中文名，不带书名号 | `赛马娘 芦毛灰姑娘`、`超辉夜姬` |
| `songRole` | 该曲在作品中的定位 | `OP`、`ED`、`插曲` |
| `version` | 通常 `完整版` | `完整版` |
| `artistReading` | 艺人名的片假名读法；**没有就不写**（自动省略括号） | `アレキサンドロス` |
| `extraFeatures` | 基础特色之外的追加项，会以「，以及…」接在后面 | `["外来语词源"]` |

歌名 `title` 与艺人 `artist` 取自 `project/render/cover-content.json`（与封面同源，避免两处写法不一致）。

## 自动推导的字段（不要手写）

- `audio`：从**冻结母带**探测真实格式，形如 `48kHz/24-bit Flac`；有损编码会写明「（有损编码）」，
  不会替母带宣称无损或 Hi-Res——封面角标同理，只有确实 ≥24-bit/48kHz 才允许标 Hi-Res。
- `features`：基础特色来自系列默认，追加项来自该期实际启用的层（如舶来语词源）。

## 交付顺序

1. QA 通过、`validate --stage render` 通过、`promote_final.py` 完成；
2. `write_video_description.py` 生成简介（本步不可省）；
3. 简介与成品、封面一起交付给用户。
