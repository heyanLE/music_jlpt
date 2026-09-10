"""Read-only candidate checks plus derived screenshots; does not promote video."""
import hashlib,json,subprocess,sys
from pathlib import Path
import numpy as np
R=Path(__file__).resolve().parents[2];P=R/'project'
run_id=sys.argv[1] if len(sys.argv)>1 else 'approved-v1'
V=P/f'work/{run_id}/16x9/mystic-light-quest-study--16x9--{run_id}.mkv'
Q=P/f'qa/{run_id}';Q.mkdir(exist_ok=True)
def run(args):return subprocess.run(args,check=True,capture_output=True).stdout
def digest(path,copy=False):
    args=['ffmpeg','-v','error','-i',str(path),'-map','0:a:0']
    args+=['-c:a','copy'] if copy else ['-c:a','pcm_s24le']
    return run(args+['-f','hash','-hash','sha256','-']).decode().strip()
pcm=digest(V);source=digest(R/'source/music.flac');wav=digest(R/'source/music.wav')
packet=digest(V,True);source_packet=digest(R/'source/music.flac',True)
assert pcm==source==wav
assert packet==source_packet
probe=json.loads(run(['ffprobe','-v','error','-count_frames','-show_entries','format=duration:stream=codec_type,codec_name,width,height,r_frame_rate,avg_frame_rate,nb_read_frames,sample_rate,bits_per_raw_sample,channels,start_time','-of','json',str(V)]))
vs=next(s for s in probe['streams'] if s['codec_type']=='video'); au=next(s for s in probe['streams'] if s['codec_type']=='audio')
assert (vs['width'],vs['height'],vs['r_frame_rate'])==(1920,1080,'30/1')
assert int(vs['nb_read_frames'])==6210
assert au['codec_name']=='flac' and au['sample_rate']=='48000' and au['bits_per_raw_sample']=='24' and au['channels']==2
assert abs(float(probe['format']['duration'])-207)<.1
timestamps=json.loads(run(['ffprobe','-v','error','-select_streams','v:0','-show_entries','frame=best_effort_timestamp_time','-of','json',str(V)]))['frames']
times=[float(x['best_effort_timestamp_time']) for x in timestamps]
assert all(.0329<=b-a<=.0341 for a,b in zip(times,times[1:]))
samples={'opening':1000,'song-reading-l018':96900,'merged-idiom-l025':126500,'repeat-loanword-l029':141200,'two-line-card-l011':55000,'tail-hold':205950,'tail-clear':206500}
samples.update({'character-first':12050,'character-second':12330,'character-fourth':12750,'character-seventh':13990})
for name,t in samples.items():run(['ffmpeg','-v','error','-y','-ss',str(t/1000),'-i',str(V),'-frames:v','1',str(Q/f'{name}.png')])
def crop(path,t):
    data=run(['ffmpeg','-v','error','-ss',str(t),'-i',str(path),'-frames:v','1','-vf','crop=700:100:0:180,scale=140:20,format=gray','-f','rawvideo','-'])
    return np.frombuffer(data,dtype=np.uint8).astype(float)
alignment=[]
for t in [10,40,80,140,185]:
    a=crop(V,t);b=crop(R/'source/background-trimmed.mp4',t)
    correlation=float(np.corrcoef(a,b)[0,1]);alignment.append({'outputSeconds':t,'backgroundCorrelation':correlation})
    assert correlation>.96,(t,correlation)
report={'schemaVersion':1,'status':'mechanical-passed','candidateSha256':hashlib.sha256(V.read_bytes()).hexdigest(),'audio':{'pcmSha256':pcm,'wavFlacCandidateIdentical':True,'flacPacketHash':packet,'packetCopyIdentical':True},'probe':probe,'cfrAll6210FramesChecked':True,'backgroundAlignmentChecks':alignment,'samples':[{'name':k,'timestampMs':v,'path':(Q/f'{k}.png').relative_to(R).as_posix()} for k,v in samples.items()],'visualStatus':'pending'}
(Q/'extra-qa.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'lossless':True,'cfrFrames':len(times),'backgroundAlignment':alignment,'samples':len(samples)}))
