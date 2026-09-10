import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
doc = json.loads((ROOT / 'frames.json').read_text(encoding='utf8'))
removed = {'l001', 'l002', 'l003'}
doc['frames'] = [f for f in doc['frames'] if f['id'] not in removed]
(ROOT / 'frames.json').write_text(json.dumps(doc, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
review = ['# もうどうなってもいいや — 合并审核稿', '', '已合并用户批准的高/极高置信度联网审核提案；片头曲目信息与制作人员信息已移除。', '']
for f in doc['frames']:
    c = f['caption']; review += [f"## {f['id']} · {f['startMs']/1000:.3f}s", '', f"日文：{c['japanese']}", f"中文：{c['translationZh']}", '']
    for x in f['grammarCards']:
        review.append(f"- {x['token']}（{x['reading']} / {x['romaji']}）：{x.get('functionZh') or x.get('zhMeaning', '')}；{x['posZh']}（{x.get('status', 'draft')}）")
    review.append('')
text = '\n'.join(review)
(ROOT / 'review' / 'mp3-audio-review.md').write_text(text, encoding='utf8')
(ROOT.parent / 'deliverables' / 'review' / 'mou-dou-natte-mo-ii-ya-review.md').write_text(text, encoding='utf8')
log_path = ROOT / 'review' / 'merge-log.json'
log = json.loads(log_path.read_text(encoding='utf8'))
log['postMergeUserEdits'] = {'removedFrameIds': sorted(removed), 'behavior': 'lyric-free background remains until l004 at 7.471s'}
log_path.write_text(json.dumps(log, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
print(json.dumps({'remainingFrames': len(doc['frames']), 'removed': sorted(removed)}, ensure_ascii=False))
