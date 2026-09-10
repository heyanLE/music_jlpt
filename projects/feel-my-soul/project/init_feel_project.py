"""Initialize feel my soul review data from QQ Music QRC assets."""
import json, re
from pathlib import Path
from pykakasi import kakasi
from sudachipy import dictionary, tokenizer

ROOT=Path(__file__).parent; OUT=ROOT/'output'; PARTICLES=json.loads((ROOT/'particle-functions.json').read_text(encoding='utf8'))['particles']
qrc=json.loads((OUT/'feel-qm.parsed.json').read_text(encoding='utf8'))['content']
qmt=(OUT/'feel-qmts.xml').read_text(encoding='utf8')
POS={'名詞':'名词','代名詞':'人称代词','動詞':'动词','形容詞':'形容词','形状詞':'形容动词','副詞':'副词','連体詞':'连体词','接続詞':'连词','助詞':'助词','助動詞':'助动词'}
def roma(t): return ''.join(x['hepburn'] for x in kakasi().convert(t)).lower()
def cards(text):
 r=[]
 for m in dictionary.Dictionary().create().tokenize(text,tokenizer.Tokenizer.SplitMode.C):
  s=m.surface(); p=m.part_of_speech()[0]
  if p in {'空白','補助記号'}: continue
  reading=m.reading_form() or s; c={'token':s,'reading':reading,'romaji':('wa' if s=='は' and p=='助詞' else roma(reading)),'dictionaryForm':m.dictionary_form(),'posJa':p,'posZh':POS.get(p,'待核'),'zhMeaning':'待人工复核','reviewRequired':True,'render':True,'showJlpt':False}
  if p=='助詞': c['functionZh']=PARTICLES.get(s,['语法功能待核'])[0]
  if r and ((p=='助動詞' and r[-1]['posJa']=='動詞') or (s in {'て','で'} and r[-1]['posJa']=='動詞')):
   r[-1]['token']+=s; r[-1]['reading']+=reading; r[-1]['romaji']+=c['romaji']; r[-1]['posZh']='动词（活用）'
  else:r.append(c)
 return r
ts=[]
for mm,ss,v in re.findall(r'^\[(\d{2}):(\d{2}\.\d{2})\](.*)$',qmt,re.M):
 if v and not v.startswith('//') and not v.startswith('TME'): ts.append((int(mm)*60000+round(float(ss)*1000),v.strip()))
frames=[]
for ln in qrc:
 text=''.join(x['content'] for x in ln['content'])
 if ln['start']<5000 or text.startswith(('原唱：','词：','曲：','编曲：')):continue
 cs=cards(text); start=ln['start']; end=start+ln['duration']; zh='；'.join(v for t,v in ts if start-50<=t<end-50) or '待人工复核'
 frames.append({'id':f'l{len(frames)+1:03d}','kind':'lyric','startMs':start,'endMs':end,'caption':{'japanese':text,'romaji':' '.join(c['romaji'] for c in cs),'translationZh':zh,'furigana':[{'base':c['token'],'reading':c['reading'],'romaji':c['romaji']} for c in cs]},'grammarCards':cs,'analysisStatus':'auto-draft-needs-human-review','reviewRequired':True})
project={'schemaVersion':'1.0','project':{'id':'feel-my-soul-terasawa','title':'feel my soul','artist':'寺澤百花','audio':str(ROOT/'feel-my-soul-source.m4a'),'backgroundVideo':r'C:\Users\eke_l\Desktop\【Hi-Res】feel_my_soul_无字版_败犬女主太多了【NCED3】.26084770155.mp4','cover':str(ROOT/'feel-my-soul-cover.jpg'),'durationMs':232832,'canvas':{'width':1920,'height':1080}},'wordTimingSource':{'format':'QQ Music QRC','parsedTimeline':str(OUT/'feel-qm.parsed.json'),'romajiSource':str(OUT/'feel-qmRoma.parsed.json'),'translationSource':str(OUT/'feel-qmts.xml')},'reviewStatus':'auto-draft-needs-human-review','frames':frames}
(ROOT/'feel-my-soul.frames.approved.json').write_text(json.dumps(project,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
lines=['# feel my soul｜逐句词卡审核','', '已接入 QQ Music 日文、罗马音和中文翻译轨。请直接修改暂定中文、词卡含义或词性；确认后回复“核对完了”。','']
for f in frames:
 cap=f['caption'];lines += [f'## {f["id"]} · {f["startMs"]/1000:.3f}s','',f'日文：{cap["japanese"]}',f'暂定中文：{cap["translationZh"]}','', '待核词卡：']
 for c in f['grammarCards']:lines += [f'- `{c["token"]}`｜{c["reading"]}｜{c["romaji"]}',f'  - 暂定：{c.get("functionZh") or c["zhMeaning"]}',f'  - 词性：{c["posZh"]}']
 lines.append('')
(OUT/'feel-my-soul-review.md').write_text('\n'.join(lines),encoding='utf8')
print(f'frames={len(frames)}')
