from pathlib import Path
import json

root=Path(r"C:\project\musicjlpt\projects\tsuyogaru-girl")
timing=root/'project'/'timing';out=root/'deliverables'/'review'
def stamp(ms):
 m,r=divmod(ms,60000);return f'{m:02}:{r//1000:02}.{r%1000:03}'
def export_karaoke(source,name,title):
 data=json.loads((timing/source).read_text(encoding='utf-8'))['lines']
 lines=[f'# {title}','',f'共 {len(data)} 行；每行保留逐词时码。','']
 for row in data:
  parts=' '.join(f'<{stamp(p["startMs"])}–{stamp(p["endMs"])} {p["text"]}>' for p in row['parts'])
  lines.extend([f'## [{stamp(row["startMs"])}–{stamp(row["endMs"])}] {row["text"]}','',parts,''])
 (out/name).write_text('\n'.join(lines),encoding='utf-8',newline='\n')
def export_translation():
 data=json.loads((timing/'translation.json').read_text(encoding='utf-8'))['lines'];lines=['# QMTS 中文翻译解码','',f'共 {len(data)} 行。','']
 lines += [f'[{stamp(x["startMs"])}] {x["text"]}' for x in data]
 (out/'tsuyogaru-girl-qmts-decoded.md').write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
out.mkdir(parents=True,exist_ok=True)
export_karaoke('qm.json','tsuyogaru-girl-qm-decoded.md','QM 原歌词解码')
export_karaoke('roma.json','tsuyogaru-girl-qmRoma-decoded.md','QMRoma 罗马音解码')
export_translation()
