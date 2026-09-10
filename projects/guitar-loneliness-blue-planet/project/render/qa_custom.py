"""Technical evidence and additional actual-output samples; no automatic visual pass."""
import argparse,io,json,subprocess,hashlib
from pathlib import Path
from PIL import Image,ImageDraw
from prepare_audio import pcm_hash
ROOT=Path(__file__).resolve().parents[2];P=ROOT/'project';RUN=P/'work/render-r1'
VIDEO=RUN/'guitar-loneliness-blue-planet--16x9--render-r1.mkv';QA=P/'qa/render-r1'
BIN=Path('C:/Users/eke_l/miniconda3/envs/manim_render312/Library/bin')
def call(exe,args):return subprocess.run([str(BIN/exe),*args],capture_output=True,check=True)
def frame(path,t):
    raw=call('ffmpeg.exe',['-v','error','-ss',str(t),'-i',str(path),'-frames:v','1','-f','image2pipe','-c:v','png','-']).stdout
    return Image.open(io.BytesIO(raw)).convert('RGBA')
def main():
    global RUN,VIDEO,QA
    parser=argparse.ArgumentParser();parser.add_argument('--run-id',default='render-r1');args=parser.parse_args()
    RUN=P/'work'/args.run_id;VIDEO=RUN/f'guitar-loneliness-blue-planet--16x9--{args.run_id}.mkv';QA=P/'qa'/args.run_id
    QA.mkdir(parents=True,exist_ok=True)
    probe=json.loads(call('ffprobe.exe',['-v','error','-show_streams','-show_format','-of','json',str(VIDEO)]).stdout)
    video=next(s for s in probe['streams'] if s['codec_type']=='video');audio=next(s for s in probe['streams'] if s['codec_type']=='audio')
    assert (video['width'],video['height'],video['r_frame_rate'],video['pix_fmt'])==(1920,1080,'30/1','yuv420p')
    assert audio['codec_name']=='flac' and audio['sample_rate']=='48000' and audio['bits_per_raw_sample']=='24'
    packet_data=json.loads(call('ffprobe.exe',['-v','error','-show_packets','-show_entries','packet=stream_index,pts_time,dts_time,duration_time','-of','json',str(VIDEO)]).stdout)['packets']
    packets=[p for p in packet_data if p['stream_index']==audio['index']]
    starts=[float(p['pts_time']) for p in packets]
    assert starts[0]==0 and all(a<b for a,b in zip(starts,starts[1:]))
    gaps=[starts[i+1]-(starts[i]+float(packets[i].get('duration_time',0))) for i in range(len(packets)-1)]
    assert max(abs(g) for g in gaps)<.002
    vp=[p for p in packet_data if p['stream_index']==video['index']]
    ordered_pts=sorted(float(p['pts_time']) for p in vp)
    assert ordered_pts[0]==0 and all(abs((b-a)-1/30)<.0011 for a,b in zip(ordered_pts,ordered_pts[1:]))
    original=pcm_hash(ROOT/'source/music.flac');suffix=pcm_hash(VIDEO,1002096*8)
    combined=pcm_hash(P/'work/audio/program-lossless.flac');actual=pcm_hash(VIDEO)
    assert suffix==original and combined==actual,'Final output audio PCM differs'
    motion=[]
    for t in [1,12,35,100,126.5,170,220,240]:
        a=frame(RUN/'spectrum.mov',t);b=frame(RUN/'spectrum.mov',t+.3)
        changed=hashlib.sha256(a.tobytes()).digest()!=hashlib.sha256(b.tobytes()).digest()
        assert a.getpixel((0,0))[3]==0,'Spectrum black background'
        assert changed,f'Spectrum frozen at {t}'
        motion.append({'time':t,'laterTime':t+.3,'changed':changed,'cornerAlpha':0})
        a.save(QA/f'spectrum-{t}.png')
    samples={'intro-voice':1,'audio-before-cut':20.75,'audio-after-cut':21.05,'before-first-reveal':32.95,'first-reveal':33.10,'before-gaussian':126.15,'fade-midpoint':126.73,'after-gaussian':127.35,'middle-spectrum':170,'late-spectrum':220}
    screen_records=[]
    for name,t in samples.items():
        output=QA/f'{name}.png';frame(VIDEO,t).convert('RGB').save(output)
        screen_records.append({'name':name,'timestampMs':round(t*1000),'path':output.relative_to(ROOT).as_posix()})
    allshots=sorted(QA.glob('*.png'))
    images=[f for f in allshots if not f.name.startswith('spectrum-')]
    sheet=Image.new('RGB',(1200,math_ceil(len(images)/3)*250),(20,20,20));draw=ImageDraw.Draw(sheet)
    for i,f in enumerate(images):
        im=Image.open(f).convert('RGB');im.thumbnail((400,225));x=(i%3)*400;y=(i//3)*250
        sheet.paste(im,(x,y));draw.text((x+4,y+226),f.stem,fill='white')
    sheet.save(QA/'contact-sheet.jpg',quality=90)
    report={'status':'passed-technical-pending-visual','candidateSha256':hashlib.sha256(VIDEO.read_bytes()).hexdigest(),'video':{'width':1920,'height':1080,'fps':30,'packetCount':len(vp),'firstPts':ordered_pts[0]},'audio':{'codec':'flac','sampleRate':48000,'bits':24,'firstPts':starts[0],'maxPacketGapSeconds':max(abs(g) for g in gaps),'masterPcmBitExact':suffix==original,'combinedPcmBitExact':combined==actual,'masterHash':original},'spectrumMotion':motion,'durationSeconds':float(probe['format']['duration']),'screenshots':screen_records,'visualPassMustBeManual':True}
    (QA/'custom-technical-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))
def math_ceil(x):return int(-(-x//1))
if __name__=='__main__':main()
