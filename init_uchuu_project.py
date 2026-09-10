"""Initialize the うちゅうのふしぎ review project from decoded QQ Music QRC data."""
import json
import re
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path

from pykakasi import kakasi
from sudachipy import dictionary, tokenizer

ROOT = Path(__file__).parent
OUT = ROOT / 'output'
QM = OUT / 'uchuu-qm.parsed.json'
QMTS = OUT / 'uchuu-qmts.xml'
AUDIO = Path(r'C:\Users\eke_l\Downloads\夢限大みゅーたいぷ - うちゅうのふしぎ.flac')
VIDEO = Path(r'C:\Users\eke_l\Desktop\TV动画_ED影像公开「バンドリ!_ゆめ∞みた(BanG_Dream!_YUME∞MITA)」.39577256487.mp4')
TARGET = ROOT / 'uchuu.frames.approved.json'
REVIEW = OUT / 'uchuu-remaining-review.md'
COVER = ROOT / 'uchuu-cover.jpg'
PARTICLES = json.loads((ROOT / 'particle-functions.json').read_text(encoding='utf8'))['particles']
POS = {'名詞':'名词','動詞':'动词','形容詞':'形容词','形状詞':'形容动词','副詞':'副词','連体詞':'连体词','接続詞':'连词','感動詞':'感叹词','助詞':'助词','助動詞':'助动词'}

def roma(t): return ''.join(x['hepburn'] for x in kakasi().convert(t)).lower()
def cardize(text):
    cards=[]
    for m in dictionary.Dictionary().create().tokenize(text, tokenizer.Tokenizer.SplitMode.C):
        surface=m.surface(); pos=m.part_of_speech()[0]
        if pos in {'空白','補助記号'}: continue
        reading=m.reading_form() or surface
        card={'token':surface,'reading':reading,'romaji':('wa' if surface=='は' and pos=='助詞' else roma(reading)),'dictionaryForm':m.dictionary_form(),'posJa':pos,'posZh':POS.get(pos,'待核'),'zhMeaning':'待人工复核','reviewRequired':True,'render':True,'showJlpt':False}
        if pos=='助詞': card['functionZh']=PARTICLES.get(surface,['语法功能待核'])[0]
        if cards and ((pos=='助動詞' and cards[-1]['posJa']=='動詞') or (surface in {'て','で'} and cards[-1]['posJa']=='動詞')):
            prev=cards[-1]; prev['token']+=surface; prev['reading']+=reading; prev['romaji']+=card['romaji']; prev['posZh']='动词（活用）'
        else: cards.append(card)
    return cards

def qmts():
    values=[]
    for mm, ss, value in re.findall(r'^\[(\d{2}):(\d{2}\.\d{2})\](.*)$', QMTS.read_text(encoding='utf8'), re.M):
        if value and not value.startswith('//') and not value.startswith('TME'):
            values.append((int(mm)*60000+round(float(ss)*1000),value.strip()))
    return values

qrc=json.loads(QM.read_text(encoding='utf8'))['content']; translations=qmts(); frames=[]
for index,line in enumerate(qrc):
    japanese=''.join(x['content'] for x in line['content'])
    # QRC metadata and credits have a title/artist-like line but no lyric parts worth teaching.
    if not japanese or line['start'] < 1100 or japanese.startswith(('词：', '曲：')): continue
    cards=cardize(japanese); start=line['start']; end=start+line['duration']
    zh='；'.join(v for t,v in translations if start-40<=t<end-40) or '待人工复核'
    frames.append({'id':f'l{len(frames)+1:03d}','kind':'lyric','startMs':start,'endMs':end,'caption':{'japanese':japanese,'romaji':' '.join(x['romaji'] for x in cards),'translationZh':zh,'furigana':[{'base':x['token'],'reading':x['reading'],'romaji':x['romaji']} for x in cards]},'grammarCards':cards,'analysisStatus':'auto-draft-needs-human-review','reviewRequired':True})

duration=90149
project={'schemaVersion':'1.0','project':{'id':'uchuu-no-fushigi-mugendai','title':'うちゅうのふしぎ','artist':'夢限大みゅーたいぷ','audio':str(AUDIO),'backgroundVideo':str(VIDEO),'cover':str(COVER),'durationMs':duration,'canvas':{'width':1920,'height':1080}},'wordTimingSource':{'format':'QQ Music QRC','parsedTimeline':str(QM),'romajiSource':str(OUT/'uchuu-qmRoma.parsed.json'),'translationSource':str(QMTS)},'reviewStatus':'auto-draft-needs-human-review','frames':frames}
TARGET.write_text(json.dumps(project,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

subprocess.run(['ffmpeg','-y','-v','error','-ss','00:00:20','-i',str(VIDEO),'-frames:v','1','-q:v','2',str(COVER)],check=True)
lines=['# うちゅうのふしぎ｜逐句词卡审核','', '已接入 QQ Music 的日文、罗马音和中文翻译轨。请直接修改“暂定中文”、词卡含义或词性；确认完毕后回复“核对完了”。','']
for f in frames:
    cap=f['caption']; lines += [f'## {f["id"]} · {f["startMs"]/1000:.3f}s','',f'日文：{cap["japanese"]}',f'暂定中文：{cap["translationZh"]}','', '待核词卡：']
    for c in f['grammarCards']:
        lines += [f'- `{c["token"]}`｜{c["reading"]}｜{c["romaji"]}',f'  - 暂定：{c.get("functionZh") or c["zhMeaning"]}',f'  - 词性：{c["posZh"]}']
    lines.append('')
REVIEW.write_text('\n'.join(lines),encoding='utf8')
print(TARGET); print(REVIEW); print(COVER); print(f'frames={len(frames)}')
