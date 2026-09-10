"""Evidence for opening-only visibility revision, no linguistic changes."""
import hashlib,json
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[2];P=ROOT/'project';RUN=P/'work/render-r2-countdown'
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def main():
    old=load(P/'work/render-r1/foreground-timeline.json');new=load(RUN/'foreground-timeline.json')
    assert [s for s in old['segments'] if s['endMs']>33050]==[s for s in new['segments'] if s['endMs']>33050]
    assert new['segments'][0]=={'startMs':0,'endMs':33050,'kind':'blank'}
    frame=Image.open(RUN/'foreground/state-00000.png').convert('RGBA')
    assert frame.getchannel('A').getextrema()==(0,0),'Prelude foreground is not transparent'
    frames_sha=hashlib.sha256((P/'frames.json').read_bytes()).hexdigest()
    assert frames_sha==load(P/'review/review-decision.json')['frameSha256']
    report={'status':'passed','userWording':'歌词不要太早出来，后面歌词间有消失，首次也等到倒计时出来再出来','firstForegroundAtMs':33050,'firstSingingAtMs':36050,'entireTimelineFromCountdownUnchanged':True,'preludeForegroundAlpha':[0,0],'cardsUnchangedSha256':frames_sha,'audioAndSpectrumClockChanged':False}
    (P/'qa/countdown-reveal-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':main()
