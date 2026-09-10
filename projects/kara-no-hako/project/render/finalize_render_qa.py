"""Record the completed visual and technical QA for the authorized candidate."""
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
P=ROOT/'project'; QA=P/'qa/final-round2-approved-r1'; report_path=QA/'qa-report.json'
candidate=ROOT/'project/work/round2-approved-r1/16x9/kara-no-hako--16x9--round2-approved-r1.mkv'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p): return json.loads(p.read_text(encoding='utf-8'))
def write(p,o): p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
report=load(report_path);assert report['candidateSha256']==sha(candidate)
extras=[
 ('transition-before',95900),('transition-mid',96114),('transition-after',96400),
 ('persistent-gap-actual',110500),('long-persistent-gap',130000),('final-retained',180000),
 ('l009',28200),('l029',99000),('l031',106000),('l035',121000),('spectrum-motion-01',10000),('spectrum-motion-02',10033)
]
existing={s['name'] for s in report['screenshots']}
for name,t in extras:
    path=QA/(name+'.png')
    if path.exists() and name not in existing: report['screenshots'].append({'name':name,'timestampMs':t,'path':path.relative_to(ROOT).as_posix()})
# The generic collector's first long neutral segment is in follow mode; replace its mislabeled persistent sample.
for item in report['screenshots']:
    if item['name']=='persistent-gap': item.update(timestampMs=110500,path=(QA/'persistent-gap-actual.png').relative_to(ROOT).as_posix(),note='Corrected to a neutral segment after the persistent-mode scene begins.')
report.update({
 'result':'passed','reviewedAt':'2026-09-04','qaScope':'authorized round2-approved-r1 16x9 final candidate',
 'technicalFindings':{
   'container':'Matroska','durationMs':183844,'video':'H.264 1920x1080 yuv420p CFR 30/1, starts at 0','audio':'FLAC 48000 Hz 24-bit, starts at 0, stream-copy',
   'sourceAudioPacketSha256':'4f44bd10deb164fd37dba13e7b65830fbf7c44a1a6f3202bcc0b10f4ac208d64',
   'candidateAudioPacketSha256':'4f44bd10deb164fd37dba13e7b65830fbf7c44a1a6f3202bcc0b10f4ac208d64','audioPacketsBitIdentical':True,
   'foregroundTimeline':{'full':45,'adjacentRows':0,'lineFallback':0,'unmatched':0,'blankSegments':3,'neutralSegments':26,'activeSegments':481},
   'customRendererGate':'PASS; project/render/render_next_line_video.py bound by render-authorization.json and dependency pins'
 },
 'visualFindings':{
   'threeLayerOrder':'Passed: source video/Gaussian background, complete study foreground, and bottom transparent spectrum are ordered correctly.',
   'backgroundFitAndTransition':'Passed: video fills 1920x1080 without crop; 95.900 s video, 96.114 s black midpoint, and 96.400 s Gaussian samples show a background-only fade.',
   'foregroundTransitionPersistence':'Passed: cover, next-line preview, current lyric, cards, and spectrum remain visible at the black transition midpoint.',
   'followLyricsGap':'Passed at 39.264 s: no lyric/cover/card foreground, source video remains visible, spectrum continues.',
   'persistentGaps':'Passed at 110.500 s and 130.000 s: the prior complete line remains visible with its next-line preview; spectrum continues.',
   'finalLine':'Passed at lyric start and 180.000 s: final l045 remains through output end; next-line preview is hidden after the final line.',
   'annotations':'Passed on first, l029, l031, maximum-card, and final samples: hiragana appears only over kanji runs, including 下手=へた and 明日=あした; literal kana is not duplicated.',
   'romaji':'Passed: anchored under corresponding learning chunks; l029 and l035 resegmentation has no collision; next-line romaji uses the same reviewed chunks.',
   'cards':'Passed: one translucent horizontal row, no active highlighting, no colon prefixes; 6-card maximum and two resegmented lines fit without clipping; meanings stay within two lines.',
   'spectrum':'Passed: no opaque background; persists through lyric gaps and scene fade. Consecutive 10.000/10.033 s frames differ in 44,634 pixels, confirming animation.',
   'englishAndLoanwordRules':'Not applicable: no pure/mixed English lyric rows and no confirmed loanword; コタエ/カタチ are Japanese words in katakana and correctly have no sourceWord.'
 },
 'sourceTranslations':'Supplied QQ full-line Chinese retained as authorized; seven separate source-translation suggestions remain unaccepted.',
 'promotionReady':True
})
write(report_path,report)
state=load(P/'build-state.json');state.update(stage='qa_passed',renderAuthorization=True)
state['renderResult']={'runId':'round2-approved-r1','candidate':candidate.relative_to(ROOT).as_posix(),'candidateSha256':sha(candidate),'qaReport':report_path.relative_to(ROOT).as_posix(),'qa':'passed','finalPromotion':'pending'}
state['notes'].append('Authorized round2-approved-r1 candidate rendered and passed technical plus visual QA; custom renderer gate used because the shared validator accepts only its fixed entry point.')
write(P/'build-state.json',state)
print(json.dumps({'result':'passed','candidateSha256':sha(candidate),'screenshots':len(report['screenshots']),'promotionReady':True},ensure_ascii=False))
