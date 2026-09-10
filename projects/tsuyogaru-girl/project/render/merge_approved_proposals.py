from __future__ import annotations
import hashlib,json
import copy
from pathlib import Path

ROOT=Path(r"C:\project\musicjlpt\projects\tsuyogaru-girl");P=ROOT/'project';FRAMES=P/'frames.json';OUT=ROOT/'deliverables'/'review'/'tsuyogaru-girl-review.md';MERGE='assisted-review-20260817-user-approved-all'
FILES=[P/'proposals'/'early-l001-l023.json',P/'proposals'/'middle-l024-l046.json',P/'proposals'/'late-l047-l070.json']
def rd(p):return json.loads(p.read_text(encoding='utf-8'))
def wr(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n');json.loads(p.read_text(encoding='utf-8'))
data=rd(FRAMES); byid={f['id']:f for f in data['frames']}; changed=[]
for path in FILES:
 for frame_id,proposal in rd(path)['frames'].items():
  frame=byid[frame_id]; frame['grammarCards']=proposal.get('cards',[]); frame['caption']['furigana']=proposal.get('furigana',[]); frame['caption']['romaji']=proposal.get('romaji','')
  for card in frame['grammarCards']:
   card['status']='assisted-merged-awaiting-human-confirmation';card['fieldProvenance']=MERGE
  frame['status']='assisted-merged-awaiting-human-confirmation';prov=frame.setdefault('fieldProvenance',{});prov['grammarCards']=MERGE;prov['furigana']=MERGE;prov['romaji']=MERGE
  # QMTS-only policy: never invent a Chinese line. Existing initial fallback is explicitly marked unavailable.
  if not frame['caption'].get('translationZh') or frame['caption']['translationZh']=='（待结合上下文核对中文）': frame['caption']['translationZh']='QMTS 未提供'
  changed.append(frame_id)
# These repeated frames were explicitly grouped in the approved middle-range
# proposal; copy only the approved token bundle, never a translated line.
for target,source in {'l029':'l025','l042':'l041','l044':'l041','l045':'l041'}.items():
 frame=byid[target]; source_frame=byid[source]
 frame['grammarCards']=copy.deepcopy(source_frame['grammarCards'])
 frame['caption']['furigana']=copy.deepcopy(source_frame['caption']['furigana'])
 frame['caption']['romaji']=source_frame['caption']['romaji']
 for card in frame['grammarCards']:
  card['status']='assisted-merged-awaiting-human-confirmation';card['fieldProvenance']=MERGE
 frame['status']='assisted-merged-awaiting-human-confirmation';frame.setdefault('fieldProvenance',{})['grammarCards']=MERGE;frame['fieldProvenance']['furigana']=MERGE;frame['fieldProvenance']['romaji']=MERGE
 if not frame['caption'].get('translationZh') or frame['caption']['translationZh']=='（待结合上下文核对中文）': frame['caption']['translationZh']='QMTS 未提供'
 changed.append(target)
wr(FRAMES,data); frame_sha=hashlib.sha256(FRAMES.read_bytes()).hexdigest()
wr(P/'review'/'merge-log.json',{'schemaVersion':1,'mergeId':MERGE,'userAuthorization':'采纳全部提案','proposalFiles':[str(x.relative_to(ROOT)) for x in FILES],'changedFrameIds':changed,'translationPolicy':'QMTS-only; no machine line translations','frameSha256':frame_sha,'reviewDecision':'not-created; merge authorization is not content approval/render authorization'})
lines=['# つよがるガール — 词卡人工审阅','', '已合并联网提案。整句中文仅采用 QMTS；标记“QMTS 未提供”的句子不含模型补译。','']
for f in data['frames']:
 c=f['caption'];lines += [f"## {f['id']}  {c['japanese']}",'',f"- 整句中文：{c['translationZh']}",f"- 罗马音：{c['romaji']}",'- 词卡：']
 for x in f['grammarCards']:
  lines.append(f"  - {x['token']}｜{x['reading']}｜{x['romaji']}｜{x.get('functionZh') or x.get('zhMeaning','')}｜{x['posZh']}")
 lines.append('')
OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
state=rd(P/'build-state.json');state['state']='draft_ready';state['next']='review_approved';state.setdefault('activeFiles',{})['mergeLog']='project/review/merge-log.json';state['activeFiles']['review']='deliverables/review/tsuyogaru-girl-review.md';state['notes']=['All user-approved assisted proposals have been merged; final human content confirmation remains required.','QMTS-only line translation policy is enforced.','No final render is authorized.'];wr(P/'build-state.json',state)
