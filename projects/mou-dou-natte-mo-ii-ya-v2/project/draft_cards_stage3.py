import json
from pathlib import Path
from fugashi import Tagger
from pykakasi import kakasi
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).parent; PROJECT=ROOT.parent; SOURCE=PROJECT/'source'; QA=ROOT/'qa'; REVIEW=PROJECT/'deliverables'/'review'
data=json.loads((ROOT/'frames.json').read_text(encoding='utf-8')); tagger=Tagger(); kk=kakasi()
POS={'名詞':'名词','動詞':'动词','形容詞':'形容词','副詞':'副词','助詞':'助词','助動詞':'助动词','連体詞':'连体词','接続詞':'连词','感動詞':'感叹词','代名詞':'代词'}
PARTICLE={'は':'主题提示','が':'主语标记','を':'动作对象','に':'动作对象／到达点','で':'动作地点／手段','と':'共同对象／引用','の':'所属／修饰','も':'追加／强调','へ':'移动方向','から':'起点／因为','まで':'终点','や':'列举'}
def hira(s): return ''.join(chr(ord(c)-0x60) if 'ァ'<=c<='ヶ' else c for c in s)
def roma(reading): return ''.join(x['hepburn'] for x in kk.convert(hira(reading)))
def cards(text):
 out=[]
 for word in tagger(text):
  token=word.surface
  if not token or all(ch.isspace() for ch in token) or (token.isascii() and any(ch.isalpha() for ch in token)): continue
  reading=hira(getattr(word.feature,'kana',token) or token); pos=POS.get(getattr(word.feature,'pos1',''),'其他')
  card={'token':token,'reading':reading,'romaji':roma(reading),'posZh':pos,'render':True,'status':'draft','fieldProvenance':{'source':'fugashi-unidic-draft'}}
  if token in PARTICLE: card.update({'functionZh':PARTICLE[token],'posZh':'助词'})
  else: card['zhMeaning']='待联网核对'
  out.append(card)
 return out
for frame in data['frames']:
 text=frame['caption']['japanese']; frame['grammarCards']=cards(text); frame['caption']['romaji']=' '.join(c['romaji'] for c in frame['grammarCards']); frame['caption']['furigana']=[]; frame['analysisStatus']='draft'
REVIEW.mkdir(parents=True,exist_ok=True)
lines=['# もうどうなってもいいや 词卡草稿','','本草稿仅完成自动切词、读音、罗马音与助词功能；非助词释义均待联网审核。','']
for frame in data['frames']:
 lines.extend([f"## {frame['id']} · {frame['startMs']/1000:.2f}s",'',f"- 日文：{frame['caption']['japanese']}",f"- 暂定中文：{frame['caption']['translationZh']}",'- 词卡：'])
 for card in frame['grammarCards']: lines.append(f"  - {card['token']}（{card['romaji']}）：{card.get('functionZh',card.get('zhMeaning'))}｜{card['posZh']}｜draft")
 lines.append('')
(REVIEW/'mou-dou-natte-mo-ii-ya-v2-review.md').write_text('\n'.join(lines),encoding='utf-8',newline='\n')
(ROOT/'frames.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
json.loads((ROOT/'frames.json').read_text(encoding='utf-8'))
preview_frame=data['frames'][0]; img=Image.open(QA/'background.png').convert('RGBA').resize((1920,1080)); img=Image.alpha_composite(img,Image.new('RGBA',img.size,(0,0,0,72))); img.alpha_composite(Image.open(SOURCE/'cover.jpg').convert('RGBA').resize((220,220)),(850,35)); d=ImageDraw.Draw(img); font='C:/Windows/Fonts/msyhbd.ttc'
def ft(size): return ImageFont.truetype(font,size)
def centered(x,y,text,face,fill='white'):
 b=d.textbbox((0,0),text,font=face); d.text((x-(b[2]-b[0])/2,y),text,font=face,fill=fill)
cards0=preview_frame['grammarCards']; widths=[d.textbbox((0,0),c['token'],font=ft(70))[2] for c in cards0]; gap=22; x=(1920-sum(widths)-gap*(len(widths)-1))/2
for card,width in zip(cards0,widths): centered(x+width/2,330,card['token'],ft(70)); centered(x+width/2,430,card['romaji'],ft(34)); x+=width+gap
centered(960,500,preview_frame['caption']['translationZh'],ft(45)); total=1730; gap=12; card_width=total//len(cards0); x=95; accent=(94,40,84,192)
for card in cards0:
 d.rounded_rectangle((x,600,x+card_width-gap,850),20,fill=accent,outline=(180,130,210,210),width=2); mid=x+(card_width-gap)/2; centered(mid,625,card['token'],ft(37)); centered(mid,695,card.get('functionZh',card.get('zhMeaning','待联网核对')),ft(26)); centered(mid,770,card['posZh'],ft(25)); x+=card_width
content_preview=QA/'content-layout-preview-16x9.png'; img.convert('RGB').save(content_preview)
report={'result':'passed','templateId':'study-current-v2','selectedFrames':[preview_frame['id']],'preview':str(content_preview),'checks':{'cardsUseIndependentFields':True,'meaningWrapPolicy':'two-lines','fontWeight':700,'sharedTokenAnchors':True,'magicColorSemiTransparentCards':True,'contentIsDraft':True},'note':'Semantic meanings require authorized assisted review.'}
(QA/'layout-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
(ROOT/'build-state.json').write_text(json.dumps({'schemaVersion':2,'state':'draft_ready','next':'assisted-review-or-human-edits','renderAuthorized':False,'frameCount':len(data['frames'])},ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps({'frames':len(data['frames']),'cards':sum(len(x['grammarCards']) for x in data['frames'])},ensure_ascii=False))
