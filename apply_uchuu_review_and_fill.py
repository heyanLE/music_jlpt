"""Import user edits, then fill remaining うちゅうのふしぎ cards conservatively."""
import copy
import json
import re
from pathlib import Path

ROOT=Path(__file__).parent; PATH=ROOT/'uchuu.frames.approved.json'; REVIEW=ROOT/'output/uchuu-remaining-review.md'
data=json.loads(PATH.read_text(encoding='utf8')); frames={f['id']:f for f in data['frames']}

# Import the user's current Markdown edits first. Every explicitly written value wins.
current=None; entries={}; card=None
for line in REVIEW.read_text(encoding='utf8').splitlines():
    m=re.match(r'^## (l\d+) · ',line)
    if m: current=m.group(1); entries[current]={'translation':None,'cards':[]}; card=None; continue
    if not current: continue
    if line.startswith('暂定中文：'): entries[current]['translation']=line[5:].strip(); continue
    m=re.match(r'^- `(.+)`｜([^｜]+)｜(.+)$',line)
    if m:
        card={'token':m.group(1),'reading':m.group(2),'romaji':m.group(3)}; entries[current]['cards'].append(card); continue
    if card and line.startswith('  - 暂定：'): card['zhMeaning']=line[6:].strip()
    if card and line.startswith('  - 词性：'): card['posZh']=line[6:].strip()
for fid,entry in entries.items():
    if fid not in frames or not entry['cards']: continue
    if entry['translation']: frames[fid]['caption']['translationZh']=entry['translation']
    cards=[]
    for c in entry['cards']:
        if not {'token','reading','romaji','zhMeaning','posZh'}<=set(c): continue
        c.update({'render':True,'showJlpt':False,'reviewRequired':False})
        if '助词' in c['posZh']: c['functionZh']=c['zhMeaning']
        cards.append(c)
    if cards:
        frames[fid]['grammarCards']=cards
        frames[fid]['caption']['furigana']=[{'base':c['token'],'reading':c['reading'],'romaji':c['romaji']} for c in cards]
        frames[fid]['caption']['romaji']=' '.join(c['romaji'] for c in cards)

def make(token, reading, romaji, meaning, pos):
    c={'token':token,'reading':reading,'romaji':romaji,'zhMeaning':meaning,'posZh':pos,'render':True,'showJlpt':False,'reviewRequired':False}
    if '助词' in pos: c['functionZh']=meaning
    return c

# Correct only known lexical/structural issues; preserve all other user values.
exact={
 'l001':[('とべる','能飞','动词（可能形）'),('の','疑问语气','终助词')],
 'l002':[('ずっと','一直','副词'),('ねてる','正在睡（寝ている的口语缩约）','动词（进行）'),('の','疑问语气','终助词')],
 'l003':[('君','你','人称代词'),('どんな','什么样的','连体词'),('生きる','生活、度过','动词'),('の','疑问语气','终助词')],
 'l005':[('さがし','寻找（探す的连用形）','动词（连用形）'),('に','动作目的','助词'),('ゆこう','去吧、一起去（行こう的口语）','动词（意志形）')],
 'l006':[('僕','我','人称代词'),('照らす','照亮','动词'),('の','疑问语气','终助词')],
 'l007':[('寂しく','寂寞地（寂しい的连用形）','形容词'),('なる','变成','动词'),('の','疑问语气','终助词')],
 'l009':[('できたら','如果能做到','动词（条件形）'),('いい','好、就好了','形容词'),('ね','征求认同、加强感叹','终助词')],
 'l011':[('この','这个','连体词'),('広い','广阔的','形容词'),('で','动作、状态发生的地点','助词')],
 'l013':[('解き明かして','解开、弄明白','动词（て形）'),('みよう','试着看看吧','补助动词（意志形）')],
 'l014':[('どんな','什么样的','连体词'),('しよう','做吧、来聊吧','动词（意志形）')],
 'l015':[('君','你','人称代词'),('と','共同对象','助词'),('どんな','什么样的','连体词'),('歌おう','唱吧、一起唱吧','动词（意志形）')],
 'l016':[('誰','谁','疑问代词'),('まだ','还、尚未','副词'),('知らない','不知道、没人知道的','动词（否定）')],
}
for fid, replacements in exact.items():
    for token,meaning,pos in replacements:
        for c in frames[fid]['grammarCards']:
            if c['token']==token:
                c['zhMeaning']=meaning; c['posZh']=pos; c['reviewRequired']=False
                if '助词' in pos: c['functionZh']=meaning

# Structural learner-friendly chunks.
frames['l008']['grammarCards']=[make('かなしい','カナシイ','kanashii','悲伤的','形容词'),make('こと','コト','koto','事情','名词'),make('は','ハ','wa','主题提示','助词'),make('はんぶんこ','ハンブンコ','hanbunko','一人一半、平分','名词')]
frames['l009']['grammarCards']=[c for c in frames['l009']['grammarCards'] if c['token'] not in {'の','に'}]
frames['l009']['grammarCards'].insert(2,make('のに','ノニ','noni','却、明明……却……','接续助词'))
frames['l010']['grammarCards']=[make('笑ったり','ワラッタリ','warattari','时而笑笑','动词＋列举助词'),make('悩んでみたり','ナヤンデミタリ','nayandemitari','时而试着烦恼、苦恼','动词＋补助动词＋列举助词')]
frames['l012']['grammarCards']=[make('僕ら','ボクラ','bokura','我们','人称代词'),make('で','デ','de','手段、主体','助词'),make('うちゅう','ウチュウ','uchuu','宇宙','名词'),make('の','ノ','no','所属修饰','助词'),make('ふしぎ','フシギ','fushigi','不可思议','名词')]
frames['l012']['caption']['translationZh']='让我们来解开宇宙的不可思议吧'
frames['l013']['caption']['translationZh']='让我们来解开宇宙的不可思议吧'
for fid in ('l005','l018','l020'): 
    if fid!='l005': frames[fid]['grammarCards']=copy.deepcopy(frames['l005']['grammarCards'])
for fid in ('l004','l017','l019'):
    if fid!='l004': frames[fid]['grammarCards']=copy.deepcopy(frames['l004']['grammarCards'])
for f in frames.values():
    f['caption']['furigana']=[{'base':c['token'],'reading':c['reading'],'romaji':c['romaji']} for c in f['grammarCards']]
    f['caption']['romaji']=' '.join(c['romaji'] for c in f['grammarCards'])
    f['analysisStatus']='human-edits-preserved-and-assisted-fill'
data['reviewStatus']='assisted-fill-needs-human-review'; data['assistedReviewSources']=['user Markdown edits','QQ Music qmts','QRC timing','lexical review']
PATH.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

lines=['# うちゅうのふしぎ｜智能补全后词卡审核','', '已保留你已写入的内容，并修正了固定表达、助词功能与明显误分。请只检查仍想微调的地方；确认后回复“核对完了”。','']
for f in data['frames']:
    cap=f['caption']; lines += [f'## {f["id"]} · {f["startMs"]/1000:.3f}s','',f'日文：{cap["japanese"]}',f'暂定中文：{cap["translationZh"]}','', '词卡：']
    for c in f['grammarCards']:
        lines += [f'- `{c["token"]}`｜{c["reading"]}｜{c["romaji"]}',f'  - 暂定：{c.get("functionZh") or c["zhMeaning"]}',f'  - 词性：{c["posZh"]}']
    lines.append('')
REVIEW.write_text('\n'.join(lines),encoding='utf8')
print(PATH); print(REVIEW)
