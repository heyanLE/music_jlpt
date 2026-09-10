from setup import *

script('normalize_lyrics.py',ROOT,'--min-lyric-ms','11908')
script('prepare_setup.py',ROOT)
project=ROOT/'project'
templates={p.name:sha(p) for p in (project/'templates').glob('*.json')}
write(project/'assets.json',{'schemaVersion':1,'sourceManifest':'source/source-manifest.json','sourceManifestSha256':sha(ROOT/'source/source-manifest.json'),'active':{'music':{'asset':'source/music.flac','sha256':sha(ROOT/'source/music.flac'),'sampleRateHz':48000,'bitsPerSample':24,'finalContainer':'mkv','finalAudioCodec':'copy'},'cover':{'asset':'source/cover.jpg','sha256':sha(ROOT/'source/cover.jpg'),'origin':'MV frame at 80s, square crop x540 y0 w1080 h1080'},'background':{'asset':'source/background-trimmed.mp4','sha256':sha(ROOT/'source/background-trimmed.mp4'),'trimStartMs':3064,'durationMs':207000},'lyrics':{'minDisplayedLyricMs':11908},'preset':'video-loop-follow','spectrum':'off'},'templateSha256':templates})
script('render_cover.py','--cover',ROOT/'source/cover.jpg','--palette',project/'palette.json','--config',project/'render/cover-content.json','--output-dir',ROOT/'deliverables/final','--run-id','mystic-setup-v1','--report',project/'qa/cover-report-mystic-setup-v1.json')
frames=json.loads((project/'frames.json').read_text(encoding='utf-8'))['frames']
lines=['# Mystic Light Quest 初始歌词审阅','', '整句中文取自 QMTS；此文件为歌词源核对稿，词卡尚未生成。','']
for f in frames:
    lines += [f"## {f['id']} · {f['startMs']/1000:.3f}s",'',f['caption']['japanese'],'',f['caption']['translationZh'],'']
(ROOT/'deliverables/review/lyrics-source-review.md').write_text('\n'.join(lines),encoding='utf-8')
script('build_foreground_timeline.py',ROOT,project/'render/foreground-timeline-shells.json','--duration-ms','207000')
sys.path.insert(0,str(SKILL/'scripts'))
from render_video import ForegroundRenderer
from PIL import Image
renderer=ForegroundRenderer(ROOT,1920,1080)
fg=project/'qa/setup-foreground.png'
renderer.render(frames[0]['id'],None,fg)
bg=project/'qa/setup-background.png'
run(['ffmpeg','-v','error','-ss',str(frames[0]['startMs']/1000+.3),'-i',ROOT/'source/background-trimmed.mp4','-frames:v','1',bg])
image=Image.open(bg).convert('RGBA'); image.alpha_composite(Image.open(fg).convert('RGBA'))
image.convert('RGB').save(project/'qa/structure-preview-16x9.png')
write(project/'qa/structure-report.json',{'schemaVersion':1,'status':'setup-preview','frameId':frames[0]['id'],'preview':'project/qa/structure-preview-16x9.png','notes':['Real cover, source Japanese and QMTS Chinese over trimmed MV; grammar and per-token romaji are intentionally pending card drafting.','This is a setup preview, not a final foreground acceptance.']})
state=json.loads((project/'build-state.json').read_text(encoding='utf-8')); state['stage']='setup_complete';state['notes'] += ['Video intro removed at 3064 ms using six consistent audio matches.','WAV to FLAC 48kHz/24bit conversion passes decoded PCM SHA256 equality.','Excluded four verified song-title and songwriter metadata rows; retained 42 lyric rows, source QMTS Chinese.','Two platform covers exported with existing Hi-Res logo; next stage is card drafting.']
write(project/'build-state.json',state)
script('validate_project.py',ROOT,'--stage','setup')
print(json.dumps({'stage':'setup_complete','lyricFrames':len(frames),'root':str(ROOT)},ensure_ascii=False))
