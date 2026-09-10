from pathlib import Path
import json

root=Path(r"C:\project\musicjlpt\projects\tsuyogaru-girl")
rows=json.loads((root/'project'/'timing'/'translation.json').read_text(encoding='utf-8'))['lines']
def stamp(ms):
    minutes, remainder=divmod(ms,60000)
    return f'{minutes:02}:{remainder//1000:02}.{remainder%1000:03}'
lines=['# QMTS 解码结果：つよがるガール','',f'共 {len(rows)} 条整句中文；首条从 {stamp(rows[0]["startMs"])} 开始。','']
for row in rows:
    lines.append(f'[{stamp(row["startMs"])}] {row["text"]}')
(root/'deliverables'/'review'/'tsuyogaru-girl-qmts-decoded.md').write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
