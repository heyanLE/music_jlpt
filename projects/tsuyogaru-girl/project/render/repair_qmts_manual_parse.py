from pathlib import Path
import json,re

ROOT=Path(r"C:\project\musicjlpt\projects\tsuyogaru-girl");P=ROOT/'project';RAW=P/'timing'/'translation-decoded.qrc';FRAMES=P/'frames.json'
def wr(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n');json.loads(p.read_text(encoding='utf-8'))
rows=[]
for index,line in enumerate(RAW.read_text(encoding='utf-8').splitlines(),1):
 match=re.match(r'^\[(\d+):(\d+(?:\.\d+)?)\](.*)$',line)
 if not match: continue
 minute,second,text=match.groups();ms=round((int(minute)*60+float(second))*1000)
 if text.strip() and not text.startswith(('TME享有','//')): rows.append({'id':f'translation-{len(rows)+1:03}','startMs':ms,'text':text})
wr(P/'timing'/'translation.json',{'schemaVersion':1,'source':'lyrics.qmts.qrc','lyricType':'regular','parser':'manual-lrc-timestamp-regex','lines':rows})
data=json.loads(FRAMES.read_text(encoding='utf-8'))
for frame in data['frames']:
 nearest=min(rows,key=lambda row:abs(row['startMs']-frame['startMs']))
 frame['caption']['translationZh']=nearest['text'] if abs(nearest['startMs']-frame['startMs'])<=650 else 'QMTS 未提供'
 frame.setdefault('fieldProvenance',{})['translationZh']='qmts-manual-lrc-timestamp-parse-20260817'
FRAMES.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
json.loads(FRAMES.read_text(encoding='utf-8'))
out=ROOT/'deliverables'/'review'/'tsuyogaru-girl-qmts-decoded.md'; lines=['# QMTS 中文翻译解码（手工时间标签解析）','',f'共 {len(rows)} 条歌词翻译。','']
for row in rows:
 m,r=divmod(row['startMs'],60000);lines.append(f'[{m:02}:{r//1000:02}.{r%1000:03}] {row["text"]}')
out.write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
review=ROOT/'deliverables'/'review'/'tsuyogaru-girl-review.md'; lines=['# つよがるガール — 词卡人工审阅','', '整句中文已从 QMTS 原始时间标签重新解析。','']
for f in data['frames']:
 c=f['caption'];lines += [f"## {f['id']}  {c['japanese']}",'',f"- 整句中文：{c['translationZh']}",f"- 罗马音：{c['romaji']}",'- 词卡：']
 for x in f['grammarCards']:lines.append(f"  - {x['token']}｜{x['reading']}｜{x['romaji']}｜{x.get('functionZh') or x.get('zhMeaning','')}｜{x['posZh']}")
 lines.append('')
review.write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
wr(P/'review'/'qmts-reparse-log.json',{'parser':'manual-lrc-timestamp-regex','previousLineCount':45,'correctedLineCount':len(rows),'reason':'smart-lyric lrc parser omitted early timestamped QMTS rows'})
