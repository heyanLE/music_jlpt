"""Resolve the accepted render plan immediately before authorization."""
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
P=ROOT/'project'; RUN='round2-approved-r1'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p): return json.loads(p.read_text(encoding='utf-8'))
renderer=P/'render/render_next_line_video.py'
plan={
 'schemaVersion':2,'state':'ready-for-explicitly-authorized-render','runId':RUN,'authorizationText':'按当前审核版渲染',
 'foregroundVariant':'study-current-v3-next-line-a','entryPoint':'project/render/render_next_line_video.py','rendererSha256':sha(renderer),
 'backgroundPreset':'video-then-gaussian-hybrid','transition':{'atMs':96114,'durationMs':500,'scope':'background-only'},
 'layers':['background','foreground','floatingOverlay'],'spectrum':{'enabled':True,'persistent':True,'transparent':True,'clock':'output'},
 'audio':{'asset':'source/music.flac','codec':'flac','sampleRate':48000,'bitsPerSample':24,'operation':'stream-copy','container':'matroska','durationMs':183844,'offsetMs':0},
 'outputs':[{'name':'16x9','width':1920,'height':1080,'fps':30,'candidate':f'project/work/{RUN}/16x9/kara-no-hako--16x9--{RUN}.mkv'}],
 'activeHashes':{
   'frames':sha(P/'frames.json'),'reviewDecision':sha(P/'review/review-decision.json'),'mergeLog':sha(P/'review/merge-log.json'),
   'palette':sha(P/'palette.json'),'presentation':sha(P/'presentation.json'),'sceneTimeline':sha(P/'scene-timeline.json'),
   'foregroundTemplate':sha(P/'templates/foreground.json'),'overlayTemplate':sha(P/'templates/overlay.json')
 },
 'content':{'frames':45,'cards':153,'sourceTranslationIssuesApproved':False},
 'qaRequired':['probe','first-last-lyric','max-cards','resegmented-cards','repeat','gap','scene-transition','spectrum-transparency-persistence','audio-stream-copy']
}
(P/'render/render-plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
state=load(P/'build-state.json');state['renderPlan']='project/render/render-plan.json';state['notes'].append('Explicit render wording received; plan round2-approved-r1 resolved. Authorization and render gate still run separately.')
(P/'build-state.json').write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps({'runId':RUN,'frameSha256':plan['activeHashes']['frames'],'candidate':plan['outputs'][0]['candidate']},ensure_ascii=False))
