"""Record source probes, approved layout variant and reproducible setup state."""
import colorsys
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
PROJECT=ROOT/'project'
def load(p): return json.loads(p.read_text(encoding='utf-8'))
def write(p,o):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
source=load(ROOT/'source/source-manifest.json')
assets={'schemaVersion':1,'sources':source['assets'],'templateSnapshots':[], 'derived':[]}
for p in sorted((PROJECT/'templates').glob('*.json')):
    assets['templateSnapshots'].append({'asset':p.relative_to(ROOT).as_posix(),'sha256':sha(p)})
badge=PROJECT/'assets/hi-res-audio-logo.png'
assets['derived'].append({'role':'platform-cover-hires-badge','asset':badge.relative_to(ROOT).as_posix(),'sha256':sha(badge),'origin':'../dare-ni-mo-narenai-watashi-dakara-v3/project/assets/hi-res-audio-logo.png'})
write(PROJECT/'assets.json',assets)
palette=load(PROJECT/'palette.json')
color=tuple(int(palette['accent'][i:i+2],16)/255 for i in (1,3,5))
h,s,v=colorsys.rgb_to_hsv(*color)
cover_color=colorsys.hsv_to_rgb(h,max(s,0.8),0.43)
palette['accent']='#'+''.join(f'{round(c*255):02X}' for c in cover_color)
palette['derivation']={'source':'project/palette.json','policy':'same hue, darker accent for light-paper cover text; video palette unchanged'}
write(PROJECT/'render/cover-palette.json',palette)
state=load(PROJECT/'build-state.json')
state['stage']='draft_ready'
state['renderAuthorization']=False
state['notes'] += ['45 lyric rows normalized; five verified credit rows before 571 ms excluded.', '151 authored draft cards; per-token kana and romaji; all 45 draft layers pass mechanical layout checks.', 'User approved next-line top preview format; snapshot and project-local renderer preserve current-line sizes.', '48 kHz / 24-bit FLAC source copied bit-for-bit; final policy MKV + FLAC stream copy; no final render authorization yet.', 'Onset -4600 ms rejected: multisegment spectral alignment is approximately +64 ms at 64 ms resolution; keep default zero offset.', 'Mandatory lexical, grammar and translation role review running; frames remain frozen during proposal generation.']
write(PROJECT/'build-state.json',state)
write(PROJECT/'alignment/alignment-decision.json',{'schemaVersion':1,'appliedOffsetMs':0,'reason':'Reject mismatched RMS onset peaks; early/middle spectral windows agree within about two CFR30 frames. Keep full FLAC and do not introduce a multisecond shift.','evidence':['project/alignment/onset-report.json','project/alignment/program-match.json'],'fineAlignmentStatus':'not sample-accurately measured','lateVideoNote':'TV edit near the ending is not the full-length second verse; later matched window cannot define a global offset.'})
write(PROJECT/'render/render-plan.json',{'schemaVersion':1,'state':'awaiting-content-review-and-separate-render-authorization','foregroundVariant':'study-current-v3-next-line-a','foregroundRenderer':'project/render/next_line_foreground.py','backgroundPreset':'video-then-gaussian-hybrid','transitionAtMs':96114,'transitionDurationMs':500,'transitionScope':'background-only','spectrum':'transparent Foobar persistent across whole audio','audio':{'codec':'flac','sampleRate':48000,'bitsPerSample':24,'operation':'stream-copy','container':'mkv','durationMs':183844,'offsetMs':0},'outputs':[{'name':'16x9','width':1920,'height':1080,'fps':30}],'note':'Final entry point must include the project-local preview renderer and bind its hash; never invoke a base renderer that ignores the next-line variant.'})
readme='''# 空の箱（井芹仁菜、河原木桃香）

- 前景：已确认的 A 版——左上封面、右上下一句假名／歌词／分词罗马音；当前句与词卡保持原模板字号。
- 背景：视频播放一次，96.114 秒处以 500 毫秒仅背景淡出淡入切换到封面高斯，持续至 183.844 秒。
- 前景显隐：视频段跟随歌词；高斯段保留上句；预读跟随前景，没有下一句时隐藏预读。
- 频谱：底部透明 Foobar 跳动柱，全程独立于前景显隐。
- 音频：原 FLAC 48 kHz / 24-bit 保留；最终 MKV 内 stream-copy，不转 AAC、不裁母带静音。
- 封面：16:9、4:3，沿用金色 Hi-Res 角标。浅色纸面文字用封面同色系深金色，视频保持亮黄色。
- 内容：45 句、151 张初稿词卡；中文原样来源 QQ 翻译轨，多角色仅提建议。

## 审核文件

- `deliverables/review/kara-no-hako-review.md`：完整初稿。
- `project/proposals/`：三个角色的独立建议；不是已采纳内容。
- `project/review/`：基准哈希、整合审核和后续用户决定。

## 重要

新预读格式已得到用户批准，但本曲词卡和最终渲染尚未得到确认。不得把其他项目的审批复制过来。
本项目的 `project/templates/foreground.json` 含预读扩展；不要重跑初始化覆盖该快照。
最终渲染应使用新的预读前景实现并验证渲染授权，不能直接调用忽略该扩展的旧前景。
'''
(ROOT/'README.md').write_text(readme,encoding='utf-8')
print(json.dumps({'assets':str(PROJECT/'assets.json'),'coverAccent':palette['accent'],'stage':'draft_ready'}))
