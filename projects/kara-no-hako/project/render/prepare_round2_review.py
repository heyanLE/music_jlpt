"""Verify editable review baseline and preserve first-round evidence without changing content."""
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P = ROOT / 'project'
def load(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

frames = load(P/'frames.json')
md = (ROOT/'deliverables/review/kara-no-hako-review.md').read_text(encoding='utf-8')
differences = []
for frame in frames['frames']:
    section = md.split(f"## {frame['id']}　", 1)[1].split('\n## ', 1)[0]
    expected = [f"- {c['token']}（{c['reading']} / {c['romaji']}）——{c.get('functionZh',c.get('zhMeaning'))}；{c['grammarStructureZh']}" for c in frame['grammarCards']]
    actual = [s for s in section.splitlines() if s.startswith('- ')]
    if expected != actual or f"暂定中文：{frame['caption']['translationZh']}" not in section:
        differences.append({'frameId':frame['id'],'expectedCards':expected,'actualCards':actual})
write(P/'review/round2-input-check.json', {'baseFrameSha256':digest(P/'frames.json'),'markdownSha256':digest(ROOT/'deliverables/review/kara-no-hako-review.md'),'fieldLevelDifferences':differences,'result':'no-edits-to-import' if not differences else 'stop-import-required'})
assert not differences, 'Import user Markdown edits before continuing.'
archive = P/'review/round1-archive'
archive.mkdir(exist_ok=True)
archived=[]
for source in [P/'review/assisted-review-audit.json', P/'review/integration-report.json', P/'review/integrated-proposed-frames.json', ROOT/'deliverables/review/kara-no-hako-review-changes.md']:
    dest=archive/source.name
    if dest.exists(): assert digest(source)==digest(dest), str(dest)
    else: shutil.copy2(source,dest)
    archived.append({'source':str(source.relative_to(ROOT)),'archive':str(dest.relative_to(ROOT)),'sha256':digest(dest)})
write(archive/'manifest.json',{'status':'superseded-by-new-review-request-not-accepted','files':archived})
write(P/'review/review-decision.json', {'schemaVersion':2,'content':'changes-requested','scope':'all','renderAuthorized':False,'userWording':'有一些修改部分不太行，参考dare-ni-mo-narenai-watashi-dakara-v3项目的格式重新启动智能多角色审查','frameSha256':digest(P/'frames.json'),'reviewRound':'round2'})
state=load(P/'build-state.json')
state.update(stage='draft_ready',renderAuthorization=False,activeReviewRound='round2')
state['notes'].append('User requested independent second-round lexical/grammar/translation review using dare-v3 confirmed card format; first-round recommendations superseded, not accepted; live frames unchanged.')
write(P/'build-state.json',state)
print(json.dumps({'framesSha256':digest(P/'frames.json'),'import': 'no Markdown field edits','archived':len(archived)},ensure_ascii=False))
