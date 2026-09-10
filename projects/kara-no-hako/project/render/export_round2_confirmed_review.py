"""Export the accepted card set in the project's human-readable reference format."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
P=ROOT/'project'
data=json.loads((P/'frames.json').read_text(encoding='utf-8'))
lines=['# 空の箱｜第二轮已确认词卡','','以下内容已合并到正式 frames.json。QQ整句中文仍保持原翻译轨；单独列出的7组源译建议未采纳。','','词卡格式：词条｜读音｜罗马音｜中文含义／助词功能｜词性与必要结构。','']
for frame in data['frames']:
    c=frame['caption'];lines += [f"## {frame['id']}  {c['japanese']}",'',f"- 整句中文（QQ）：{c['translationZh']}",'- 词卡：']
    for card in frame['grammarCards']:
        lines.append('  - '+'｜'.join([card['token'],card['reading'],card['romaji'],card.get('functionZh',card.get('zhMeaning','')),card['grammarStructureZh']]))
    lines.append('')
output=ROOT/'deliverables/review/kara-no-hako-round2-confirmed-review.md'
output.write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
print(json.dumps({'output':str(output),'frames':len(data['frames']),'cards':sum(len(f['grammarCards']) for f in data['frames'])},ensure_ascii=False))
