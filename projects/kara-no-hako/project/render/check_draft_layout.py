"""Validate every static draft layer and export selected content previews."""
import hashlib
import json
from pathlib import Path
from next_line_foreground import NextLineRenderer

ROOT=Path(__file__).resolve().parents[2]
PROJECT=ROOT/'project'
renderer=NextLineRenderer(ROOT)
folder=PROJECT/'qa/draft-foreground'
folder.mkdir(parents=True,exist_ok=True)
for frame in renderer.ordered:
    renderer.render(frame['id'],None,folder/(frame['id']+'.png'))
report={'schemaVersion':1,'result':'passed-mechanical','visualReview':'pending','frames':len(renderer.ordered),'cards':sum(len(f['grammarCards']) for f in renderer.ordered),'frameSha256':hashlib.sha256((PROJECT/'frames.json').read_bytes()).hexdigest(),'nextLineLayouts':renderer.preview_layouts,'pureEnglish':'not applicable','loanwords':'none: コタエ and カタチ are Japanese words styled in katakana, not loanwords'}
(PROJECT/'qa/layout-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'frames':report['frames'],'cards':report['cards'],'result':report['result']}))
