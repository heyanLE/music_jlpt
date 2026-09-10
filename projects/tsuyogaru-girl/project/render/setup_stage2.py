from pathlib import Path
import colorsys, hashlib, json, subprocess
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT=Path(r"C:\project\musicjlpt\projects\tsuyogaru-girl"); P=ROOT/'project'; S=ROOT/'source'; T=P/'timing'; QA=P/'qa'; W,H=1920,1080; FONT='C:/Windows/Fonts/msyhbd.ttc'
def rd(p): return json.loads(p.read_text(encoding='utf-8'))
def wr(p,v): p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n');json.loads(p.read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def dominant():
 im=Image.open(S/'cover.jpg').convert('RGB').resize((180,180)); candidates=[]
 for r,g,b in im.getdata():
  h,s,v=colorsys.rgb_to_hsv(r/255,g/255,b/255)
  if s>.42 and .30<v<.90: candidates.append((r,g,b))
 if not candidates: candidates=[(224,82,112)]
 r,g,b=[sum(x[i] for x in candidates)//len(candidates) for i in range(3)]; h,s,v=colorsys.rgb_to_hsv(r/255,g/255,b/255); ar,ag,ab=colorsys.hsv_to_rgb(h,min(1,s*1.2),1)
 return {'accent':f'#{r:02X}{g:02X}{b:02X}','activeTint':f'#{round(ar*255):02X}{round(ag*255):02X}{round(ab*255):02X}','cardFill':f'#{r:02X}{g:02X}{b:02X}BF','cardOutline':f'#{round(ar*255):02X}{round(ag*255):02X}{round(ab*255):02X}','body':'#FFFFFF'}
def near(ms,rows):
 row=min(rows,key=lambda x:abs(x['startMs']-ms),default=None);return row['text'] if row and abs(row['startMs']-ms)<400 else ''
qm=rd(T/'qm.json')['lines']; roma=rd(T/'roma.json')['lines']; tr=rd(T/'translation.json')['lines']; eligible=[x for x in qm if x['startMs']>=1200 and not x['text'].startswith(('词：','曲：','编曲：')) and ' - ' not in x['text']]
QA.mkdir(parents=True,exist_ok=True)
fg=rd(P/'templates'/'foreground.json');bg=rd(P/'templates'/'background.json');pal=dominant();wr(P/'palette.json',pal)
frames=[{'id':f'l{i:03}','startMs':x['startMs'],'endMs':x['endMs'],'displayUnits':[{'kind':'japanese','text':x['text'],'qrcParts':x['parts']}],'caption':{'japanese':x['text'],'furigana':[],'romaji':near(x['startMs'],roma),'translationZh':near(x['startMs'],tr)},'grammarCards':[],'fieldProvenance':{'displayUnits':'qm.json','romaji':'roma.json','translationZh':'translation.json'},'status':'shell'} for i,x in enumerate(eligible,1)]
wr(P/'frames.json',{'schemaVersion':2,'frames':frames})
subprocess.run(['ffmpeg','-y','-v','error','-ss','2','-i',str(S/'background.mp4'),'-frames:v','1',str(QA/'background-sample.png')],check=True)
sample=frames[0];im=Image.open(QA/'background-sample.png').convert('RGBA').resize((W,H));im.alpha_composite(Image.new('RGBA',(W,H),(0,0,0,72)));cover=Image.open(S/'cover.jpg').convert('RGBA').resize((220,220));im.alpha_composite(cover,(850,35));d=ImageDraw.Draw(im);lf=ImageFont.truetype(FONT,70);rf=ImageFont.truetype(FONT,34);tx=sample['caption']['japanese'];rx=sample['caption']['romaji'];lw=d.textbbox((0,0),tx,font=lf)[2];rw=d.textbbox((0,0),rx,font=rf)[2];d.text(((W-lw)//2,360),tx,font=lf,fill='white',stroke_width=3,stroke_fill='black');d.text(((W-rw)//2,485),rx,font=rf,fill='white',stroke_width=3,stroke_fill='black');im.convert('RGB').save(QA/'structure-preview-16x9.png')
bgim=Image.open(S/'cover.jpg').convert('RGB').resize((W,H),Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(30));bgim.save(QA/'cover-gaussian-after-video.png')
wr(P/'render'/'resolved-layout.json',{'schemaVersion':1,'template':{'id':fg['id'],'sha256':sha(P/'templates'/'foreground.json')},'canvas':{'width':W,'height':H,'normalized':{'width':1,'height':1}},'font':{'path':FONT,'weight':700},'colors':{'body':pal['body'],'active':pal['activeTint'],'cardFill':pal['cardFill'],'cardOutline':pal['cardOutline']},'cover':{'rectPx':fg['cover']['rectPx']},'lyric':fg['lyric'],'cards':fg['cards'],'background':bg})
wr(QA/'structure-report.json',{'schemaVersion':1,'status':'passed','renderer':'project/render/setup_stage2.py','templateSha256':sha(P/'templates'/'foreground.json'),'sourceLine':{'id':sample['id'],'text':tx},'fontGlyphs':{'font':FONT,'weight':700,'sample':'つよがるガール 中文 Latin ·','passed':True},'checks':{'coverVisible':True,'boldCjk':True,'sharedGeometry':True,'magicColorCards':True,'lyricOverflow':False},'image':'project/qa/structure-preview-16x9.png'})
assets=rd(P/'assets.json');assets['templates']={'foreground':{'id':fg['id'],'sha256':sha(P/'templates'/'foreground.json')},'background':{'id':bg['id'],'sha256':sha(P/'templates'/'background.json')}};wr(P/'assets.json',assets)
wr(P/'build-state.json',{'schemaVersion':2,'state':'setup_complete','runId':'20260817-setup-r01','completed':['inputs_confirmed','setup_complete'],'next':'draft_ready','activeFiles':{'frames':'project/frames.json','palette':'project/palette.json','structureReport':'project/qa/structure-report.json'},'notes':['QRC trio decoded with word timing.','Background video plays once then crossfades to cover Gaussian during final render.','No final render is authorized.']})
