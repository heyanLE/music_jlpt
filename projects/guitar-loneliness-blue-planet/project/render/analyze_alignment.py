"""Match multiple studio windows to noisy video music; preserve original media."""
import json
import subprocess
from pathlib import Path
import numpy as np
from scipy import signal

ROOT = Path(__file__).resolve().parents[2]
FFMPEG = 'C:/Users/eke_l/miniconda3/envs/manim_render312/Library/bin/ffmpeg.exe'
SR, HOP = 16000, 160


def decode(path):
    result = subprocess.run([FFMPEG, '-v', 'error', '-i', str(path), '-vn', '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'], capture_output=True, check=True)
    return np.frombuffer(result.stdout, dtype='<f4')


def features(samples):
    f, t, z = signal.stft(samples, SR, nperseg=1024, noverlap=1024-HOP, boundary='zeros')
    power = abs(z)**2
    edges = np.geomspace(80, 7000, 49)
    bands = np.array([power[max(1,int(np.searchsorted(f,a))):max(int(np.searchsorted(f,a))+1,int(np.searchsorted(f,b)))].mean(axis=0) for a,b in zip(edges,edges[1:])])
    bands = np.log(bands+1e-10)
    bands -= bands.mean(axis=0,keepdims=True)
    bands -= np.median(bands,axis=1,keepdims=True)
    # Spectral shape correlation tolerates gain/noise changes better than PCM.
    return bands.astype(np.float32)


def match(query, target):
    n = query.shape[1]
    numer = signal.fftconvolve(target, query[:, ::-1], mode='valid', axes=1).sum(axis=0)
    energy = signal.fftconvolve((target**2).sum(axis=0), np.ones(n), mode='valid')
    scores = numer / np.sqrt(np.maximum(energy * (query**2).sum(),1e-12))
    peaks,_ = signal.find_peaks(scores,distance=200)
    best=sorted(peaks,key=lambda i:float(scores[i]),reverse=True)[:4]
    return [{'videoStartSec':round(i*.01,3),'score':round(float(scores[i]),5)} for i in best]


def main():
    music = decode(ROOT/'source/music.flac'); video=decode(ROOT/'source/background.mp4')
    mf,vf=features(music),features(video)
    rows=[]
    for start in (0,3,8,15,25,40,55,70,85,100,115,135,160,185,205):
        candidates=match(mf[:,int(start*100):int((start+8)*100)],vf)
        rows.append({'musicStartSec':start,'windowSec':8,'matches':[{**m,'videoMinusMusicSec':round(m['videoStartSec']-start,3)} for m in candidates]})
    fine=[]
    for start in (8,15,40,55,70):
        expected=start+36.88
        query=music[round(start*SR):round((start+3)*SR)]
        base=round((expected-.15)*SR)
        target=video[base:base+len(query)+round(.3*SR)]
        scores=signal.correlate(target,query,mode='valid',method='fft')
        i=int(np.argmax(scores)); offset=(base+i)/SR-start
        aligned=target[i:i+len(query)]
        fine.append({'musicStartSec':start,'offsetSec':round(offset,6),'pcmCorrelation':round(float(np.sum(aligned*query)/np.sqrt(np.sum(aligned*aligned)*np.sum(query*query))),5)})
    # RMS is diagnostic only, never the sole alignment evidence.
    size=1600
    envelope=lambda a:[round(float(x),2) for x in 20*np.log10(np.sqrt(np.mean(a[:len(a)//size*size].reshape(-1,size)**2,axis=1))+1e-10)]
    result={'algorithm':'48-log-spectral-bands-multisegment-ncc','sampleRate':SR,'hopMs':10,'videoTrimStartMs':16000,'matches':rows,'finePcmMatches':fine,'rmsWindowMs':100,'musicRmsDb':envelope(music[:SR*15]),'videoRmsDb':envelope(video[SR*16:SR*32])}
    path=ROOT/'project/timing/audio-match-report.json'
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'finePcmMatches':fine},ensure_ascii=False,indent=2))


if __name__=='__main__': main()
