"""Merge the explicitly accepted multi-role proposals with token-aware rebasing."""
from __future__ import annotations
import hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; P=ROOT/'project'; F=P/'frames.json'
def load(p): return json.loads(p.read_text(encoding='utf-8'))
def dump(p,x): p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 data=load(F); frames={x['id']:x for x in data['frames']}; lex=load(P/'proposals/lexical.json')['changes']; grammar=load(P/'proposals/grammar.json')['changes']; trans=load(P/'proposals/translation.json')['changes']; base={}
 # Stage 1: lexical structure and caption pronunciation.
 for c in lex:
  f=frames[c['frameId']]
  if f.get('status')=='user-supplied': continue
  if c['field']=='grammarCards': base[c['frameId']]=c['old']; f['grammarCards']=c['new']
  elif c['field']=='caption.romaji': f['caption']['romaji']=c['new']
  elif c['field']=='caption.furigana': f['caption']['furigana']=c['new']
 # Rebase indexed fields from the draft token to final phrase token.
 rebased=0; unresolved=[]
 def apply(change):
  nonlocal rebased
  f=frames[change['frameId']]; field=change['field']
  if field=='caption.translationZh': f['caption']['translationZh']=change['new']; return
  m=re.fullmatch(r'grammarCards\.(\d+)\.(.+)',field)
  if not m: return
  i,sub=int(m.group(1)),m.group(2); old=(base.get(change['frameId'],f['grammarCards']))
  if i>=len(old): unresolved.append(field); return
  token=old[i]['token']; candidates=[x for x in f['grammarCards'] if x.get('token')==token] or [x for x in f['grammarCards'] if token in x.get('token','')]
  if len(candidates)!=1: unresolved.append(f"{change['frameId']}:{token}:{field}"); return
  card=candidates[0]
  if sub in ('zhMeaning','functionZh'):
   card.pop('zhMeaning',None); card.pop('functionZh',None)
  card[sub]=change['new']; card['status']='assisted-accepted'; rebased+=1
 for c in grammar+trans:
  if frames[c['frameId']].get('status')!='user-supplied': apply(c)
 # Fix known repeated groups from integration audit.
 for target,source in [('l040','l020'),('l053','l037'),('l056','l020')]:
  if target in frames and source in frames:
   if target=='l053': frames[target]['caption']['translationZh']=frames[source]['caption']['translationZh']
   if target in ('l040','l056'): frames[target]['grammarCards']=frames[source]['grammarCards']
 for f in frames.values():
  if f.get('status')!='user-supplied': f['status']='assisted-accepted'
 dump(F,data)
 log={'schemaVersion':1,'userWording':'整体采纳','framesBeforeSha256':'2cc913ecd2e826499c1825faf348627dd818dd65848ec5e44ef5210dd1aa4b42','framesAfterSha256':sha(F),'mergedProposalFiles':['project/proposals/lexical.json','project/proposals/grammar.json','project/proposals/translation.json'],'rebasedFields':rebased,'unresolved':unresolved}
 dump(P/'review/merge-log.json',log); audit=P/'review/assisted-review-audit.json'; decision={'schemaVersion':2,'content':'approved','scope':'all','renderAuthorized':False,'userWording':'整体采纳','frameSha256':log['framesAfterSha256'],'assistedReviewAuditSha256':sha(audit),'mergeLogSha256':sha(P/'review/merge-log.json')}; dump(P/'review/review-decision.json',decision)
 print(json.dumps({'rebased':rebased,'unresolved':len(unresolved),'sha':log['framesAfterSha256']},ensure_ascii=False))
if __name__=='__main__': main()
