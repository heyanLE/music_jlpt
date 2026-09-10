import hashlib,json,sys
from pathlib import Path
R=Path(__file__).resolve().parents[2]; P=R/'project'
run_id=sys.argv[1] if len(sys.argv)>1 else 'approved-v1'
load=lambda p:json.loads(p.read_text(encoding='utf-8'))
manifest=load(P/'input-manifest.json'); scenes=load(P/'scene-timeline.json'); presentation=load(P/'presentation.json')
assert scenes['segments'][0]['asset']==manifest['backgroundAsset']=='source/background-trimmed.mp4'
plan={'schemaVersion':2,'runId':run_id,'canvases':manifest['outputs'],'offsetMs':0,
      'hashes':{name:hashlib.sha256((P/name).read_bytes()).hexdigest() for name in ['frames.json','input-manifest.json','palette.json','scene-timeline.json','presentation.json','render/render_video.py','render/foreground_layout.py']},
      'timingMatches':load(P/'render/foreground-preflight.json')['summary'],
      'threeLayers':{'background':scenes,'foreground':presentation['foreground'],'floatingOverlay':presentation['floatingOverlay']},
      'audioCodecPolicy':'FLAC stream copy to MKV; 48kHz 24bit stereo; no resampling or lossy encoding',
      'renderer':'project/render/render_video.py','deviation':'Project-local snapshot of fixed renderer fixes shared annotation anchors, token highlight grouping and balanced two-line card meanings. Same snapshotted study-current-v3 geometry and scene policy. FFmpeg 4.1 uses -vsync cfr equivalent instead of newer -fps_mode cfr.',
      'japaneseHighlightPolicy':'Japanese body follows individual QRC characters; ruby and romaji remain token highlighted; English unchanged; cards never highlight',
      'candidate':f'project/work/{run_id}/16x9/mystic-light-quest-study--16x9--{run_id}.mkv',
      'runtime':{'ffmpeg':'C:/Users/eke_l/AppData/Local/Temp/Gihosoft/TubeGet/ffmpeg.exe','ffprobe':'C:/project/GPT-SoVITS-beta/GPT-SoVITS-beta0706/ffprobe.exe'}}
(P/'render/render-plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'candidate':plan['candidate'],'matches':plan['timingMatches']}))
