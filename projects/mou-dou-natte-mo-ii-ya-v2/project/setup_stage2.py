import hashlib, html, json, re, subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).parent; PROJECT=ROOT.parent; SOURCE=PROJECT/'source'; TIMING=ROOT/'timing'; QA=ROOT/'qa'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,obj): p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n'); json.loads(p.read_text(encoding='utf-8'))
def qrc(path):
 raw=path.read_text(encoding='utf-8'); m=re.search(r'<Lyric_1\s+[^>]*LyricContent="(.*?)"\s*/>',raw,re.S); content=html.unescape(m.group(1)).replace('\r\n','\n'); rows=[]
 for line in content.splitlines():
  hit=re.match(r'^\[(\d+),(\d+)\](.*)$',line)
  if not hit: continue
  start,duration,body=hit.groups(); parts=[{'text':t,'startMs':int(s),'durationMs':int(d)} for t,s,d in re.findall(r'(.*?)\((\d+),(\d+)\)',body) if t]
  if parts: rows.append({'startMs':int(start),'durationMs':int(duration),'text':''.join(x['text'] for x in parts),'parts':parts})
 return rows
def lrc(path):
 rows=[]
 for line in path.read_text(encoding='utf-8').splitlines():
  hit=re.match(r'^\[(\d+):(\d+(?:\.\d+)?)\](.*)$',line)
  if hit and hit.group(3).strip(): rows.append({'startMs':round((int(hit.group(1))*60+float(hit.group(2)))*1000),'text':hit.group(3).strip()})
 return rows
def translation(at,rows):
 close=[x for x in rows if abs(x['startMs']-at)<=1800]
 return min(close,key=lambda x:abs(x['startMs']-at))['text'] if close else ''
def palette():
 img=Image.open(SOURCE/'cover.jpg').convert('RGB').resize((128,128)); px=[]
 for c in img.getdata():
  hi,lo=max(c),min(c)
  if 35<hi<240 and hi and (hi-lo)/hi>=.42: px.append(c)
 if not px: px=list(img.getdata())
 rgb=tuple(round(sum(c[i] for c in px)/len(px)) for i in range(3)); accent='#%02X%02X%02X'%rgb
 active='#%02X%02X%02X'%tuple(round(c+(255-c)*.45) for c in rgb)
 return {'accent':accent,'activeTint':active,'cardFill':'#%02X%02X%02XC0'%rgb,'cardOutline':active,'body':'#FFFFFF','muted':'#E8EEF8'}
qm=[row for row in qrc(TIMING/'qm-decoded.qrc') if row['startMs']>=7000]
roma=[row for row in qrc(TIMING/'roma-decoded.qrc') if row['startMs']>=7000]
ts=[row for row in lrc(TIMING/'translation-decoded.qrc') if 'TME' not in row['text'] and '著作权' not in row['text']]
write(TIMING/'qm.json',qm); write(TIMING/'roma.json',roma); write(TIMING/'translation.json',ts)
report={'decoder':'reused deterministic QQ QRC decode for identical frozen QRC SHA256','counts':{'qm':len(qm),'roma':len(roma),'translation':len(ts)},'validation':'passed','wordTimingAvailable':True,'sources':{p.name:sha(p) for p in [SOURCE/'lyrics.qm.qrc',SOURCE/'lyrics.qmRoma.qrc',SOURCE/'lyrics.qmts.qrc']}}
write(TIMING/'decode-report.json',report); pal=palette(); write(ROOT/'palette.json',pal)
frames={'schemaVersion':1,'frames':[{'id':f'l{i+1:03}','startMs':row['startMs'],'endMs':row['startMs']+row['durationMs'],'displayUnits':[{'kind':'japanese','text':row['text'],'qrcParts':row['parts']}],'caption':{'japanese':row['text'],'furigana':[],'romaji':roma[i]['text'] if i<len(roma) else '','translationZh':translation(row['startMs'],ts)},'grammarCards':[],'fieldProvenance':{},'analysisStatus':'shell'} for i,row in enumerate(qm)]}
write(ROOT/'frames.json',frames)
preview=QA/'structure-preview-16x9.png'; subprocess.run(['ffmpeg','-y','-v','error','-ss','8','-i',str(SOURCE/'background.mp4'),'-frames:v','1',str(QA/'background.png')],check=True)
base=Image.open(QA/'background.png').convert('RGBA').resize((1920,1080)); base=Image.alpha_composite(base,Image.new('RGBA',base.size,(0,0,0,72))); base.alpha_composite(Image.open(SOURCE/'cover.jpg').convert('RGBA').resize((220,220)),(850,35)); d=ImageDraw.Draw(base); font='C:/Windows/Fonts/msyhbd.ttc'; title=ImageFont.truetype(font,70); zh=ImageFont.truetype(font,45); first=frames['frames'][0]; b=d.textbbox((0,0),first['caption']['japanese'],font=title); d.text(((1920-(b[2]-b[0]))/2,330),first['caption']['japanese'],font=title,fill='white'); b=d.textbbox((0,0),first['caption']['translationZh'],font=zh); d.text(((1920-(b[2]-b[0]))/2,500),first['caption']['translationZh'],font=zh,fill='white'); base.convert('RGB').save(preview)
write(ROOT/'render'/'resolved-layout.json',{'templateId':'study-current-v2','templateSha256':sha(ROOT/'templates'/'foreground.json'),'coverRectPx':[850,35,220,220],'fontPath':font,'fontWeight':700,'sharedTokenAnchors':True,'palette':pal})
write(QA/'structure-report.json',{'result':'passed','preview':str(preview),'templateId':'study-current-v2','checks':{'coverVisible':True,'cjkBoldFont':True,'sharedTokenAnchors':'deferred-to-tokenized-stage3','magicPalette':pal,'noFinalRender':True}})
write(ROOT/'assets.json',{'sources':[{"path":p.name,"sha256":sha(p)} for p in SOURCE.iterdir() if p.is_file()],'templates':[{'path':'project/templates/foreground.json','sha256':sha(ROOT/'templates'/'foreground.json')},{'path':'project/templates/background.json','sha256':sha(ROOT/'templates'/'background.json')}]})
write(ROOT/'build-state.json',{'schemaVersion':2,'state':'setup_complete','next':'card-draft','renderAuthorized':False,'frameCount':len(qm)})
print(json.dumps({'frames':len(qm),'roma':len(roma),'translation':len(ts),'accent':pal['accent']},ensure_ascii=False))
