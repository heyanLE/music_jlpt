"""Losslessly join the video introduction and bit-exact master PCM."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
BIN=Path('C:/Users/eke_l/miniconda3/envs/manim_render312/Library/bin')
OUT=ROOT/'project/work/audio'
OFFSET_MS=20877


def run(args):
    return subprocess.run([str(BIN/'ffmpeg.exe'),'-v','error','-y',*args],check=True,capture_output=True)


def pcm_hash(path,skip=0):
    filters=['-af',f'atrim=start_sample={skip//8},asetpts=PTS-STARTPTS'] if skip else []
    result=subprocess.run([str(BIN/'ffmpeg.exe'),'-v','error','-i',str(path),'-map','0:a:0',*filters,'-c:a','pcm_s32le','-f','hash','-hash','sha256','-'],capture_output=True,check=True,timeout=60)
    return {'sha256':result.stdout.decode().strip().split('=')[-1]}


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    intro=OUT/'original-introduction.flac'; program=OUT/'program-lossless.flac'
    run(['-ss','16','-i',str(ROOT/'source/background.mp4'),'-t',str(OFFSET_MS/1000),'-vn','-ac','2','-ar','48000','-c:a','flac','-sample_fmt','s32','-bits_per_raw_sample','24',str(intro)])
    run(['-i',str(intro),'-i',str(ROOT/'source/music.flac'),'-filter_complex','[0:a][1:a]concat=n=2:v=0:a=1[a]','-map','[a]','-c:a','flac','-compression_level','0','-sample_fmt','s32','-bits_per_raw_sample','24',str(program)])
    original=pcm_hash(ROOT/'source/music.flac')
    suffix=pcm_hash(program,round(OFFSET_MS*48)*2*4)
    report={'schemaVersion':1,'introSourceRangeMs':[16000,16000+OFFSET_MS],'masterStartsAtOutputMs':OFFSET_MS,'masterOperation':'lossless FLAC rewrap of unchanged decoded 48kHz 24-bit samples; no resampling/gain/fade','introOperation':'AAC decode to 48kHz 24-bit FLAC, lossless storage of decoded source','finalMuxPolicy':'stream-copy this combined FLAC into MKV','asset':program.relative_to(ROOT).as_posix(),'originalMasterPcm':original,'programMasterSuffixPcm':suffix,'masterPcmBitExact':original==suffix}
    (ROOT/'project/qa/audio-preservation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))
    if original!=suffix: raise RuntimeError('Program suffix differs from original master PCM')


if __name__=='__main__': main()
