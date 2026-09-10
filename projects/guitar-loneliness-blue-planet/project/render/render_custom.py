"""Authorized custom timeline: trimmed video + dialogue/master audio + Gaussian tail."""
from __future__ import annotations
import argparse
from concurrent.futures import ProcessPoolExecutor,ThreadPoolExecutor
import json,math,os,subprocess,sys
from pathlib import Path
from foreground_renderer import ForegroundRenderer
from verify_render_gate import verify_render_gate,load,sha

ROOT=Path(__file__).resolve().parents[2];P=ROOT/'project';HERE=Path(__file__).resolve().parent
RUN_ID='render-r2-countdown'
RUN=P/'work'/RUN_ID;CANDIDATE=RUN/f'guitar-loneliness-blue-planet--16x9--{RUN_ID}.mkv'
DURATION=249837
def write(p,d):
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def run(cmd):subprocess.run(cmd,check=True)
def init_worker():
    global renderer
    renderer=ForegroundRenderer(ROOT,1920,1080)
def paint(item):
    key,path=item;kind,fid,active,count=key
    if not Path(path).exists(): renderer.render(fid,active,Path(path),cover_only=kind=='cover',countdown_value=count)
    return path
def foreground():
    run([sys.executable,'-B','-X','utf8',str(HERE/'build_foreground_timeline.py'),str(ROOT),str(RUN/'foreground-timeline.json'),'--duration-ms',str(DURATION)])
    timeline=load(RUN/'foreground-timeline.json')
    assert timeline['summary']['full']==48 and timeline['summary']['unmatched']==0
    states={};concat=[]
    for s in timeline['segments']:
        key=(s['kind'],s.get('frameId'),s.get('activePartIndex') if s['kind']=='active' else None,s.get('countdownValue'))
        if key not in states:states[key]=RUN/'foreground'/f'state-{len(states):05}.png'
        # Millisecond timebase prevents PNG's default 25 fps rounding from accumulating.
        concat += [f"file '{states[key].as_posix()}'",'option framerate 1000',f"duration {(s['endMs']-s['startMs'])/1000:.6f}"]
    concat += [f"file '{states[key].as_posix()}'",'option framerate 1000']
    (RUN/'foreground').mkdir(exist_ok=True)
    with ProcessPoolExecutor(max_workers=4,initializer=init_worker) as pool:
        for index,_ in enumerate(pool.map(paint,[(key,str(path)) for key,path in states.items()]),1):
            if index%100==0: print(f'foreground {index}/{len(states)}',flush=True)
    (RUN/'foreground.concat.txt').write_text('\n'.join(concat)+'\n',encoding='utf-8')
    print(f'foreground complete: {len(states)} states',flush=True)
    return timeline
def spectrum():
    path=RUN/'spectrum.mov'
    if not path.exists():
        run([sys.executable,'-B','-X','utf8',str(HERE/'render_foobar_spectrum.py'),str(P/'work/audio/program-lossless.flac'),str(P/'palette.json'),str(path),'--duration-ms',str(DURATION),'--offset-ms','0'])
    return path
def dependencies():
    paths=[HERE/name for name in ('render_custom.py','foreground_renderer.py','foreground_options.py','build_foreground_timeline.py','render_foobar_spectrum.py','verify_render_gate.py')]
    paths += [P/'timing/qm.json',P/'templates/background.json',P/'render/render-plan.json',P/'work/audio/program-lossless.flac',ROOT/'source/background.mp4',ROOT/'source/cover.jpg',ROOT/'source/music.flac']
    return {p.relative_to(ROOT).as_posix():sha(p) for p in paths}
def prepare():
    plan=load(P/'render/render-plan.json')
    plan.update(status='ready-for-authorized-render',runId=RUN_ID,entryPoint='project/render/render_custom.py',candidate=CANDIDATE.relative_to(ROOT).as_posix(),canvases=load(P/'input-manifest.json')['outputs'],implementation='Project custom renderer trims source video at 16 s, composes output-clock program audio without delay, foreground at music+20.877 s, persistent transparent spectrum from the same output-clock program; shared token anchors. Project countdown.showFirstLine extension reveals the first complete study frame only when the opening countdown starts.',warning='Preserve master silence. Combined audio already includes 20.877 s original intro; never add the lyric offset again to this program.')
    plan['foreground']['prelude']='hidden-until-countdown'
    plan['foreground']['firstVisibleAtOutputMs']=33050
    plan['revision']={'userWording':'歌词不要太早出来，后面歌词间有消失，首次也等到倒计时出来再出来','scope':'Only opening foreground visibility changes; preserve post-onset timeline, cards, backgrounds, audio and spectrum.'}
    write(P/'render/render-plan.json',plan)
def bind():
    authorization=load(P/'render-authorization.json');assert authorization['renderAuthorized']
    authorization['customDependencyHashes']=dependencies();write(P/'render-authorization.json',authorization)
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--prepare',action='store_true');parser.add_argument('--bind',action='store_true');args=parser.parse_args()
    if args.prepare:prepare();return
    if args.bind:bind();return
    verify_render_gate(ROOT,Path(__file__))
    auth=load(P/'render-authorization.json');assert auth.get('customDependencyHashes')==dependencies(),'Custom renderer dependencies changed'
    assert load(P/'presentation.json')['floatingOverlay']['enabled']
    binding={'authorizationSha256':sha(P/'render-authorization.json')}
    if (RUN/'run-binding.json').exists():assert load(RUN/'run-binding.json')==binding,'Use new run ID for changed inputs'
    write(RUN/'run-binding.json',binding)
    with ThreadPoolExecutor(max_workers=2) as pool:
        fg=pool.submit(foreground);sp=pool.submit(spectrum)
        timeline=fg.result();spectrum_path=sp.result()
    scenes=load(P/'scene-timeline.json')['segments']
    first,second=scenes;assert len(scenes)==2 and first['sourceStartMs']==16000 and second['startMs']==126740
    # First segment has exactly the selected source range, not the untrimmed original.
    video_duration=first['endMs']/1000;tail_duration=DURATION/1000-video_duration
    fade_out=first['transitionOut']['durationMs']/1000;fade_in=second['transitionIn']['durationMs']/1000
    filters=[
        f'[0:v]fps=30,scale=-2:1080,crop=min(iw\\,1920):1080,pad=1920:1080:(ow-iw)/2:(oh-ih):black,setsar=1,trim=duration={video_duration:.6f},setpts=PTS-STARTPTS,fade=t=out:st={video_duration-fade_out:.6f}:d={fade_out:.6f}[v0]',
        f'[1:v]fps=30,scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1,gblur=sigma=30,eq=brightness=-0.25,trim=duration={tail_duration:.6f},setpts=PTS-STARTPTS,fade=t=in:st=0:d={fade_in:.6f}[v1]',
        '[v0][v1]concat=n=2:v=1:a=0[background]',
        '[2:v]fps=30,format=rgba,setpts=PTS-STARTPTS[foreground]',
        '[background][foreground]overlay=0:0:format=auto[learning]',
        '[3:v]fps=30,format=rgba,setpts=PTS-STARTPTS[spectrum]',
        '[learning][spectrum]overlay=36:894:format=auto,fps=30,format=yuv420p[video]'
    ]
    cmd=['ffmpeg','-y','-v','error','-threads','4','-filter_complex_threads','4','-ss','16','-i',str(ROOT/first['asset']),'-loop','1','-framerate','30','-i',str(ROOT/second['asset']),'-f','concat','-safe','0','-i',str(RUN/'foreground.concat.txt'),'-i',str(spectrum_path),'-i',str(P/'work/audio/program-lossless.flac'),'-filter_complex',';'.join(filters),'-map','[video]','-map','4:a:0','-t',str(DURATION/1000),'-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-r','30','-fps_mode','cfr','-threads','8','-c:a','copy','-progress',str(RUN/'encode-progress.txt'),str(CANDIDATE)]
    write(RUN/'ffmpeg-command.json',cmd);print('encoding composite',flush=True);run(cmd)
    write(RUN/'render-report.json',{'schemaVersion':2,'candidate':str(CANDIDATE),'candidateSha256':sha(CANDIDATE),'durationMs':DURATION,'offsetMs':20877,'scenes':scenes,'foregroundTimeline':timeline['summary'],'layers':['background','foreground','floatingOverlay'],'spectrum':'persistent transparent Foobar bars; output-clock program offset=0','audioCodecPolicy':'copy FLAC lossless program, master PCM preserved','activeHashes':{'frames':sha(P/'frames.json'),'authorization':sha(P/'render-authorization.json')},'rendererDependencies':dependencies(),'validationRoute':'common gate + explicit custom timeline/media/visual QA; generic render validator does not support custom preset'})
    print(json.dumps({'candidate':str(CANDIDATE)},ensure_ascii=False),flush=True)
if __name__=='__main__':main()
