"""Consolidate independent round-two proposals, requiring explicit conflict decisions."""
import copy
import hashlib
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
P=ROOT/'project'
ROLES=('lexical','grammar','translation')
def load(p): return json.loads(p.read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,o):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def get(obj,path):
    path=re.sub(r'\[(\d+)\]',r'.\1',path)
    for k in path.split('.'):
        if isinstance(obj,list): obj=obj[int(k)]
        else: obj=obj.get(k)
    return obj
def put(obj,path,value,remove=False):
    path=re.sub(r'\[(\d+)\]',r'.\1',path)
    keys=path.split('.')
    for k in keys[:-1]: obj=obj[int(k)] if isinstance(obj,list) else obj[k]
    key=int(keys[-1]) if isinstance(obj,list) else keys[-1]
    if remove:
        if key in obj: del obj[key]
    else: obj[key]=copy.deepcopy(value)
def signature(c): return {k:c.get(k) for k in ('token','reading','romaji','zhMeaning','functionZh','grammarStructureZh','sourceWord') if c.get(k) is not None}
def main():
    base=load(P/'frames.json'); digest=sha(P/'frames.json'); lookup={f['id']:f for f in base['frames']}
    config=load(P/'review/round2-decisions.json'); docs={r:load(P/f'proposals/round2/{r}.json') for r in ROLES}
    entries=[]
    for role,doc in docs.items():
        assert doc['baseFrameSha256']==digest,role
        assert set(doc['scope']['frameIds'])==set(lookup),role
        for index,c in enumerate(doc['changes']):
            assert get(lookup[c['frameId']],c['field'])==c.get('old'),(role,index,c['field'])
            entries.append({'id':f'{role}:{index}','role':role,**c,'originalField':c['field'],'field':re.sub(r'\[(\d+)\]',r'.\1',c['field'])})
    proposed=copy.deepcopy(base); target={f['id']:f for f in proposed['frames']}
    applied=[]; excluded=[]; conflicts=[]
    drops=config.get('exclude',{})
    for e in entries:
        if e['id'] in drops: excluded.append({**e,'resolution':drops[e['id']]})
    entries=[e for e in entries if e['id'] not in drops]
    # Structural proposals change indices, so apply complete bundles first.
    for fid in lookup:
        bundles=[e for e in entries if e['frameId']==fid and e['field']=='grammarCards']
        if not bundles: continue
        unique={json.dumps(e['new'],sort_keys=True,ensure_ascii=False) for e in bundles}
        choice=config.get('bundleChoices',{}).get(fid)
        if len(unique)>1 and choice is None:
            conflicts.append({'frameId':fid,'field':'grammarCards','candidates':[e['id'] for e in bundles]}); continue
        selected=next((e for e in bundles if e['id']==choice['proposalId']),bundles[0]) if choice else bundles[0]
        target[fid]['grammarCards']=copy.deepcopy(selected['new']); applied.append(selected)
        for e in bundles:
            if e is not selected: excluded.append({**e,'resolution':choice['reason'] if choice else 'Identical replacement bundle coalesced.'})
    # Field proposals are rebased by the original token occurrence, never by a stale index.
    field_groups={}
    for e in entries:
        if e['field']=='grammarCards': continue
        fid,path=e['frameId'],e['field']; mapped=path
        if path.startswith('grammarCards.'):
            bits=path.split('.'); index=int(bits[1]); token=lookup[fid]['grammarCards'][index]['token']
            occurrence=sum(c['token']==token for c in lookup[fid]['grammarCards'][:index])
            matches=[i for i,c in enumerate(target[fid]['grammarCards']) if c['token']==token]
            if occurrence>=len(matches):
                conflicts.append({'frameId':fid,'proposalId':e['id'],'field':path,'issue':'Token was split/merged; explicit exclusion or replacement required','token':token}); continue
            bits[1]=str(matches[occurrence]); mapped='.'.join(bits)
        field_groups.setdefault((fid,mapped),[]).append({**e,'mappedField':mapped})
    for (fid,path),items in field_groups.items():
        choice=config.get('fieldChoices',{}).get(fid+'.'+path)
        unique={json.dumps(e.get('new'),sort_keys=True,ensure_ascii=False)+str(e.get('remove',False)) for e in items}
        current=get(target[fid],path)
        bundled=current!=get(lookup[fid],items[0]['field'])
        if (len(unique)>1 or (bundled and any(e.get('new')!=current for e in items))) and choice is None:
            conflicts.append({'frameId':fid,'field':path,'currentBundleValue':current,'candidates':[{'id':e['id'],'new':e.get('new')} for e in items]});continue
        if choice and choice.get('keepBundle'):
            excluded.extend({**e,'resolution':choice['reason']} for e in items);continue
        selected=next((e for e in items if choice and e['id']==choice.get('proposalId')),items[0])
        value=choice['value'] if choice and 'value' in choice else selected.get('new')
        put(target[fid],path,value,selected.get('remove',False)); applied.append({**selected,'integrationReason':choice.get('reason') if choice else 'Unopposed field or identical role agreement.'})
        for e in items:
            if e is not selected: excluded.append({**e,'resolution':choice['reason'] if choice else 'Identical proposal coalesced.'})
    for override in config.get('overrides',[]):
        assert override.get('reason'),override
        put(target[override['frameId']],override['field'],override.get('new'),override.get('remove',False))
    write(P/'review/round2-conflict-check.json',{'conflicts':conflicts,'appliedProposals':len(applied),'excluded':excluded})
    if conflicts:
        print(json.dumps({'status':'conflict-resolution-required','conflicts':conflicts},ensure_ascii=False,indent=2));return
    repeats={}
    for fid,f in target.items():
        assert f['caption']['japanese']==lookup[fid]['caption']['japanese']
        assert f['caption']['translationZh']==lookup[fid]['caption']['translationZh']
        # Caption romaji is derived from the final chosen token romaji, not stale proposal ordering.
        f['caption']['romaji']=' '.join(c['romaji'] for c in f['grammarCards'])
        for c in f['grammarCards']: assert bool(c.get('zhMeaning'))!=bool(c.get('functionZh')),(fid,c['token'])
        text=f['caption']['japanese']; bundle=[signature(c) for c in f['grammarCards']]
        if text in repeats: assert bundle==repeats[text],('repeated line mismatch',fid)
        repeats[text]=bundle
    changes=[]
    for fid,f in target.items():
        for path in ('grammarCards','caption.furigana','caption.romaji'):
            old,new=get(lookup[fid],path),get(f,path)
            if old!=new: changes.append({'frameId':fid,'field':path,'old':old,'new':new,'changesTokenStructure':path=='grammarCards' and [c['token'] for c in old]!=[c['token'] for c in new],'evidence':['Independent round2 role proposals and explicit integration decisions; see sourceProposalFiles/integrationDecisions.']})
    report={'schemaVersion':2,'reviewRole':'integration','status':'completed','reviewRound':'round2','baseFrameSha256':digest,'sourceProposalFiles':[f'project/proposals/round2/{r}.json' for r in ROLES],'conflicts':[],'integrationDecisions':config,'appliedProposals':applied,'excludedProposals':excluded,'recommendedChanges':changes,'checks':{'allOldValuesMatched':True,'allRolesCover45Frames':True,'qqTranslationsPreserved':True,'repeatsConsistent':True,'liveFramesUnchanged':True},'sourceTranslationPolicy':'Advisory only, never included in batch card acceptance.','counts':{'frames':len(target),'cardsBefore':sum(len(f['grammarCards']) for f in base['frames']),'cardsProposed':sum(len(f['grammarCards']) for f in proposed['frames']),'changedFrames':len(set(c['frameId'] for c in changes)),'structureChangedFrames':[c['frameId'] for c in changes if c['changesTokenStructure']]},'uncertainties':{r:d.get('uncertainties',[]) for r,d in docs.items()}}
    write(P/'review/round2-integrated-proposed-frames.json',proposed)
    write(P/'review/round2-integration-report.json',report)
    assert sha(P/'frames.json')==digest
    print(json.dumps(report['counts'],ensure_ascii=False))

if __name__=='__main__':main()
