from __future__ import annotations
import json
from pathlib import Path
R=Path(__file__).resolve().parents[2]; x=json.loads((R/'project/frames.json').read_text(encoding='utf-8'))['frames']; out=['# ray｜当前审核版','','整句中文保留 QMTS 来源；词卡采用已确认的多角色合并结果。','']
for f in x:
 c=f['caption']; out += [f"## {f['id']}  {c['japanese']}",'',f"- 中文：{c.get('translationZh','')}",'- 词卡：']
 for k in f.get('grammarCards',[]): out.append(f"  - {k['token']}｜{k['reading']}｜{k['romaji']}｜{k.get('functionZh',k.get('zhMeaning',''))}｜{k['grammarStructureZh']}")
 out.append('')
p=R/'deliverables/review/ray-chou-kaguya-hime-study-current-review.md'; p.write_text('\n'.join(out),encoding='utf-8',newline='\n'); print(p)
