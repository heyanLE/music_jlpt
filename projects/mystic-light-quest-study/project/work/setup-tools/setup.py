import os, sys, json, subprocess, hashlib, shutil
from pathlib import Path
import numpy as np

WORK = Path(__file__).parent
ROOT = Path(r'C:\project\musicjlpt\projects\mystic-light-quest-study')
SKILL = Path(r'C:\Users\eke_l\.codex\skills\japanese-song-study-video')
os.environ['PATH'] = r'C:\project\GPT-SoVITS-beta\GPT-SoVITS-beta0706;C:\MediaToolkit;' + os.environ['PATH']
os.environ['PYTHONUTF8'] = '1'
MUSIC = Path(r'C:\Users\eke_l\Downloads\b60134fe3ffab194bbc3c0d8d806c1a6.wav')
VIDEO = Path(r'C:\Users\eke_l\Desktop\《明日方舟》EP_-_Mystic_Light_Quest.1634296480.mp4')
LYRICS = Path(r'C:\Users\eke_l\AppData\Roaming\Tencent\QQMusic\QQMusicCache\QQMusicLyricNew')
STEM = '塞壬唱片-MSR_KOTONOHOUSE (ことのは)_RANASOL_Machico (マチコ) - Mystic Light Quest (秘光寻旅) - 207 - Mystic Light Quest'
def run(args):
    return subprocess.run([str(x) for x in args], check=True)
def script(name,*args):
    run([sys.executable, SKILL/'scripts'/name,*args])
def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def audio(path):
    r=subprocess.run(['ffmpeg','-v','error','-i',str(path),'-vn','-ac','1','-ar','8000','-f','f32le','-'],capture_output=True,check=True)
    return np.frombuffer(r.stdout,dtype=np.float32).astype(np.float64)
def match():
    music,video=audio(MUSIC),audio(VIDEO)
    results=[]
    for seconds in (0,10,40,80,140,185):
        start=seconds*8000; q=music[start:start+8*8000]; q=q-q.mean()
        lo=max(0,start-8000); hi=min(len(video),start+20*8000+len(q)); v=video[lo:hi]
        n=1<<(len(v)+len(q)-2).bit_length()
        corr=np.fft.irfft(np.fft.rfft(v,n)*np.fft.rfft(q[::-1],n),n)[len(q)-1:len(v)]
        energy=np.r_[0,np.cumsum(v*v)]; sums=np.r_[0,np.cumsum(v)]
        variance=energy[len(q):]-energy[:-len(q)]-(sums[len(q):]-sums[:-len(q)])**2/len(q)
        scores=corr/np.sqrt(np.maximum(variance,1e-20)*np.sum(q*q))
        best=int(np.argmax(np.abs(scores)))
        results.append({'musicStartMs':seconds*1000,'videoStartMs':(lo+best)/8,'trimMs':(lo+best-start)/8,'correlation':float(scores[best])})
    trims=[r['trimMs'] for r in results]
    report={'algorithm':'six-window-normalized-waveform-correlation-8000Hz','matches':results,'trimStartMs':float(np.median(trims)),'maxSpreadMs':max(trims)-min(trims)}
    write(WORK/'alignment.json',report); print(json.dumps(report,ensure_ascii=False),flush=True)
    if min(abs(r['correlation']) for r in results)<.7 or report['maxSpreadMs']>30: raise RuntimeError('Audio match needs investigation')
def freeze():
    if not ROOT.exists():
        if not (WORK/'cover.jpg').exists():
            run(['ffmpeg','-n','-v','error','-ss','80','-i',VIDEO,'-vf','crop=1080:1080:540:0','-frames:v','1',WORK/'cover.jpg'])
        script('freeze_inputs.py',ROOT,'--slug',ROOT.name,'--music',MUSIC,'--background',VIDEO,'--cover',WORK/'cover.jpg','--qm',LYRICS/(STEM+'_qm.qrc'),'--qm-roma',LYRICS/(STEM+'_qmRoma.qrc'),'--qmts',LYRICS/(STEM+'_qmts.qrc'))
    if not (ROOT/'project/input-manifest.json').exists():
        # Complete the interrupted freeze after the three user-specified QRCs
        # were copied with approved read access; never overwrite frozen media.
        entries=[]
        originals={'music.wav':MUSIC,'background.mp4':VIDEO,'cover-original.jpg':WORK/'cover.jpg','cover.jpg':WORK/'cover.jpg'}
        for role in ('qm','qmRoma','qmts'): originals['lyrics_'+role+'.qrc']=LYRICS/(STEM+'_'+role+'.qrc')
        for name,original in originals.items():
            p=ROOT/'source'/name
            assert p.is_file() and p.stat().st_size>0
            pr=subprocess.run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(p)],capture_output=True,text=True)
            entries.append({'role':name.split('.')[0],'originalAbsolutePath':str(original),'frozenAsset':'source/'+name,'bytes':p.stat().st_size,'sha256':sha(p),'probe':json.loads(pr.stdout) if pr.returncode==0 else {'notMedia':True}})
        write(ROOT/'source/source-manifest.json',{'schemaVersion':1,'assets':entries})
        write(ROOT/'project/input-manifest.json',{'schemaVersion':4,'slug':ROOT.name,'runId':'inputs-v1','stage':'inputs_pending','music':{'asset':'source/music.wav','preserveCodec':True,'clock':'music'},'cover':{'asset':'source/cover.jpg'},'lyrics':{'format':'qq-music','qm':'source/lyrics_qm.qrc','qmRoma':'source/lyrics_qmRoma.qrc','qmts':'source/lyrics_qmts.qrc'},'backgroundAsset':'source/background.mp4','alignment':{'method':'none','offsetMs':0,'appliesTo':['music','lyrics','spectrum']},'outputs':[{'name':'16x9','width':1920,'height':1080,'fps':30}]})
        write(ROOT/'project/build-state.json',{'schemaVersion':2,'stage':'inputs_pending','renderAuthorization':False,'notes':['Completed input freeze after approved read of the three QQ Music files.']})
    if not (ROOT/'source/music.flac').exists():
        run(['ffmpeg','-n','-v','error','-i',ROOT/'source/music.wav','-map','0:a:0','-c:a','flac','-sample_fmt','s32',ROOT/'source/music.flac'])
    for name in ('music.wav','music.flac'):
        result=subprocess.run(['ffmpeg','-v','error','-i',str(ROOT/'source'/name),'-map','0:a:0','-f','hash','-hash','sha256','-c:a','pcm_s24le','-'],capture_output=True,text=True,check=True)
        if name=='music.wav': wav_hash=result.stdout.strip()
        else: flac_hash=result.stdout.strip()
    assert wav_hash==flac_hash
    write(ROOT/'project/qa/lossless-audio.json',{'wavDecodedPcmSha256':wav_hash,'flacDecodedPcmSha256':flac_hash,'identical':True,'sampleRateHz':48000,'bitsPerSample':24,'channels':2})
    trim=json.loads((WORK/'alignment.json').read_text(encoding='utf-8'))
    run([r'C:\MediaToolkit\ffmpeg.exe','-n','-v','error','-ss',str(trim['trimStartMs']/1000),'-i',ROOT/'source/background.mp4','-t','207','-map','0:v:0','-an','-c:v','libx264','-preset','fast','-crf','16','-pix_fmt','yuv420p',ROOT/'source/background-trimmed.mp4'])
    write(ROOT/'project/alignment/video-intro-trim.json',trim)
    manifest_path=ROOT/'project/input-manifest.json'; m=json.loads(manifest_path.read_text(encoding='utf-8'))
    m['music'].update(asset='source/music.flac',origin='lossless-conversion-from-frozen-wav')
    m['backgroundAsset']='source/background-trimmed.mp4'
    m['cover']['origin']='video frame at 80s, crop 1080x1080 x=540 y=0; WAV has no attached picture'
    write(manifest_path,m)
    source_path=ROOT/'source/source-manifest.json'; sm=json.loads(source_path.read_text(encoding='utf-8'))
    for role,asset,parent in [('musicLossless','source/music.flac','source/music.wav'),('backgroundTrimmed','source/background-trimmed.mp4','source/background.mp4')]:
        path=ROOT/asset; sm['assets'].append({'role':role,'frozenAsset':asset,'derivedFrom':parent,'bytes':path.stat().st_size,'sha256':sha(path)})
    write(source_path,sm)
    script('configure_layers.py',ROOT,'--preset','video-loop-follow','--spectrum','off','--offset-mode','none')
    decoder=ROOT/'project/work/qrc-runtime'
    shutil.copytree(Path(r'C:\project\musicjlpt\projects\heavenly-me-study\project\work\qrc-runtime'),decoder)
    script('normalize_lyrics.py',ROOT)

if __name__=='__main__':
    {'match':match,'freeze':freeze}[sys.argv[1]]()
