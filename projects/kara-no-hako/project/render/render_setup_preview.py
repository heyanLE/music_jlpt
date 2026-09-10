"""Compose representative draft stills using the real three-layer assets."""
import json
import subprocess
from pathlib import Path
from PIL import Image
from next_line_foreground import NextLineRenderer

ROOT=Path(__file__).resolve().parents[2]
P=ROOT/'project'
WORK=P/'work/setup-preview'
WORK.mkdir(parents=True,exist_ok=True)
renderer=NextLineRenderer(ROOT)
def extract(source, time, out, filters=''):
    command=['ffmpeg','-hide_banner','-loglevel','error','-y']
    if time is not None: command += ['-ss',str(time)]
    command += ['-i',str(source)]
    if filters: command += ['-vf',filters]
    subprocess.run(command+['-frames:v','1',str(out)],check=True)

samples=[]
for frame_id,time in [('l001',2.0),('l009',28.2),('l029',99.0),('l041',152.5)]:
    frame=renderer.frames[frame_id]
    parts=renderer.matched_parts(frame)
    active=next((i for i,u in enumerate(parts) if u.get('startMs',0) <= time*1000 < u.get('endMs',0)),None)
    foreground=WORK/f'{frame_id}-foreground.png'
    renderer.render(frame_id,active,foreground)
    background=WORK/f'{frame_id}-background.png'
    if time < 96.114:
        extract(ROOT/'source/background.mp4',time,background,'scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black')
    else:
        extract(ROOT/'source/cover.jpg',None,background,'scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,gblur=sigma=30,eq=brightness=-0.25')
    spectrum=WORK/f'{frame_id}-spectrum.png'
    extract(WORK/'foobar-spectrum.mov',time,spectrum,'format=rgba')
    image=Image.open(background).convert('RGBA')
    image.alpha_composite(Image.open(foreground).convert('RGBA'))
    image.alpha_composite(Image.open(spectrum).convert('RGBA'),(36,894))
    output=ROOT/f'deliverables/review/kara-no-hako--next-line-preview--{frame_id}.png'
    image.convert('RGB').save(output)
    if frame_id=='l001': image.convert('RGB').save(P/'qa/structure-preview-16x9.png')
    samples.append({'frameId':frame_id,'timeSeconds':time,'path':output.relative_to(ROOT).as_posix()})
report={'schemaVersion':1,'type':'draft-static-preview','result':'pending-visual-review','variant':'study-current-v3-next-line-a','samples':samples,'layers':['background','foreground-with-preview','floating-spectrum'],'contentStatus':'draft-not-approved'}
(P/'qa/structure-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
