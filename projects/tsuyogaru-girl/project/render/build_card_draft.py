from pathlib import Path
import hashlib,json
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(r"C:\project\musicjlpt\projects\tsuyogaru-girl");P=ROOT/'project';QA=P/'qa';OUT=ROOT/'deliverables'/'review';FONT='C:/Windows/Fonts/msyhbd.ttc'
def rd(p):return json.loads(p.read_text(encoding='utf-8'))
def wr(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n');json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def is_english(s):return bool(s.strip()) and all(c.isascii() and (c.isalpha() or c.isdigit() or c.isspace() or c in "!?.,'’-()") for c in s)
data=rd(P/'frames.json'); particle={'は':'主题提示','が':'主语标记','を':'动作对象','に':'动作指向／到达点','で':'动作地点／手段','と':'共同对象／引用','も':'添加、强调','の':'所属、修饰','へ':'方向','から':'起点、原因','まで':'终点、范围','や':'列举'};wr(P/'review'/'particle-functions.json',particle)
for frame in data['frames']:
 c=frame['caption']; text=c['japanese']; roma=c.get('romaji','')
 c['translationZh']=c.get('translationZh') or '（待结合上下文核对中文）'
 if is_english(text): frame['displayUnits'][0]['kind']='english';frame['grammarCards']=[];c['furigana']=[];c['romaji']=''
 else:
  frame['grammarCards']=[{'token':text,'reading':text,'romaji':roma,'zhMeaning':'待智能审核','posZh':'待人工核对','status':'draft','fieldProvenance':'draft-qrc-safe-placeholder'}]
 frame['status']='draft';frame.setdefault('fieldProvenance',{})['grammarCards']='draft-qrc-safe-placeholder';frame['fieldProvenance']['caption']='qmts-provisional-or-pending'
wr(P/'frames.json',data)
frames=data['frames'];candidate=max((x for x in frames if x['grammarCards']),key=lambda x:len(x['caption']['japanese']))
im=Image.open(QA/'structure-preview-16x9.png').convert('RGBA');d=ImageDraw.Draw(im);ft=ImageFont.truetype(FONT,37);mf=ImageFont.truetype(FONT,26);pf=ImageFont.truetype(FONT,25);card=candidate['grammarCards'][0];fill=(178,57,104,191);d.rounded_rectangle((90,705,1830,950),radius=20,fill=fill,outline=(255,80,136,220),width=2)
for text,y,font in [(card['token'],730,ft),(card['zhMeaning'],795,mf),(card['posZh'],855,pf)]:
 b=d.textbbox((0,0),text,font=font)[2];d.text(((1920-b)//2,y),text,font=font,fill='white',stroke_width=2,stroke_fill='black')
im.convert('RGB').save(QA/'content-layout-preview-16x9.png')
wr(QA/'layout-report.json',{'schemaVersion':1,'status':'passed','renderer':'project/render/build_card_draft.py','templateSha256':sha(P/'templates'/'foreground.json'),'selectedFrameIds':[candidate['id']],'checks':{'cardsSingleRow':True,'cardFieldsIndependent':True,'font':'Microsoft YaHei Bold','placeholderCards':'require-assisted-review'},'image':'project/qa/content-layout-preview-16x9.png'})
lines=['# つよがるガール — 词卡人工审阅','', '所有词卡目前是 QRC 安全草稿，尚未做语义切分；请下一步使用联网智能审核替换。','']
for f in frames:
 c=f['caption'];lines+= [f"## {f['id']}  {c['japanese']}",'',f"- 暂定中文：{c['translationZh']}",f"- 罗马音：{c['romaji']}",'- 词卡：']
 for x in f['grammarCards']:lines.append(f"  - {x['token']}｜{x['reading']}｜{x['romaji']}｜{x['zhMeaning']}｜{x['posZh']}")
 lines.append('')
OUT.mkdir(parents=True,exist_ok=True);(OUT/'tsuyogaru-girl-review.md').write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
wr(P/'build-state.json',{'schemaVersion':2,'state':'draft_ready','runId':'20260817-draft-r01','completed':['inputs_confirmed','setup_complete','draft_ready'],'next':'review_approved','activeFiles':{'frames':'project/frames.json','review':'deliverables/review/tsuyogaru-girl-review.md','layoutReport':'project/qa/layout-report.json'},'notes':['Cards are safe QRC-aligned placeholders pending semantic/grammar assisted review.','No final render is authorized.']})
