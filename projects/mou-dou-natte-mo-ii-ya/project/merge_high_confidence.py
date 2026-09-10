import hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
doc = json.loads((ROOT / 'frames.json').read_text(encoding='utf8'))
frames = {f['id']: f for f in doc['frames']}
translations = {
 'l004':'周而复始的幻想','l006':'随本能而行动','l007':'随心跳高涨的冲动','l009':'已经怎样都无所谓了','l010':'我只是想知道那些理所当然的事','l011':'向星星许下真正的心意','l012':'苦于应付时编出的借口','l013':'不需要，没有意义','l014':'你怎么想？','l015':'好像失去了容身之处','l017':'反复说着同样的话','l018':'在鸟笼中起舞','l020':'描绘着、哭喊着，只为不让它消失','l021':'如魔法般过于方便的东西','l022':'如果是主角，就该有起承转合','l024':'那就让我随心所欲吧','l026':'头朝下直直坠落','l027':'在无重力的午夜踏上逃亡','l029':'把一切全都带走','l030':'尽情讴歌人生，不留遗憾','l033':'月色竟如此美丽','l034':'这个夜晚的一切都是 Wonder','l035':'歌唱爱','l037':'被暧昧的笑容撼动','l038':'朝你的眼眸深处','l039':'对焦，Focus','l040':'谁都未曾触及的真实之园','l041':'被雨淋湿的身体，躁动不安','l043':'更加、更加、更加、更加地盲目','l044':'仿佛发狂般猛地暴露出来','l046':'如魔法般过于方便的东西','l047':'就连那种东西，我也想紧紧抓住','l048':'一旦放弃，就已是 Bad Ending','l049':'仅剩的一点勇气','l051':'如火花般燃烧过的证明','l054':'会变得特别吧','l055':'太过正经反而会被轻轻带过','l056':'在寂静的暮色中逃亡','l057':'拉近到能感到温暖的距离','l059':'这世界宛如 Stranger，呼唤爱','l074':'（不译；保留 Ooh）'
}
for repeat, original in {'l025':'l009','l036':'l009','l050':'l009','l075':'l009','l060':'l026','l061':'l027','l063':'l029','l064':'l030','l067':'l033','l069':'l035','l070':'l004','l072':'l006','l073':'l007'}.items(): translations[repeat] = translations[original]
changes=[]
for fid, text in translations.items():
    f=frames[fid]; old=f['caption']['translationZh']; f['caption']['translationZh']=text
    f['fieldProvenance']['caption.translationZh']='user-approved-web-review'; changes.append({'frameId':fid,'field':'caption.translationZh','old':old,'new':text})

def replace_cards(fid, replacements):
    cards=frames[fid]['grammarCards']
    for start, count, card in sorted(replacements, reverse=True): cards[start:start+count]=[card]
    frames[fid]['fieldProvenance']['grammarCards']='user-approved-web-review'

draft=lambda token,reading,romaji,pos,meaning=None,function=None: {'token':token,'reading':reading,'romaji':romaji,'posZh':pos,'status':'user-approved','fieldProvenance':'user-approved-web-review', **({'zhMeaning':meaning} if meaning else {}), **({'functionZh':function} if function else {})}
replace_cards('l006',[(2,2,draft('ままに','ままに','mamani','连语',function='按照、任凭'))])
replace_cards('l009',[(2,3,draft('なっても','なっても','nattemo','接续表达',function='即使变成怎样也…')),(4,1,draft('や','や','ya','终助词',function='口语收束、感叹'))])
replace_cards('l019',[(2,2,draft('穿って','うがって','ugatte','动词',meaning='钻研；此处带猜疑地深究之意'))])
replace_cards('l060',[(0,2,draft('真っ逆さま','まっさかさま','massakasama','名词性副词',meaning='头朝下、倒栽'))])
replace_cards('l061',[(0,2,draft('無重力','むじゅうりょく','mujūryoku','名词',meaning='失重、无重力')),(2,2,draft('逃避行','とうひこう','tōhikō','名词',meaning='逃亡之旅'))])
replace_cards('l063',[(0,2,draft('一切合切','いっさいがっさい','issaigassai','名词',meaning='全部、一概'))])
replace_cards('l064',[(1,2,draft('ことなく','ことなく','kotanaku','语法表达',function='没有…地、毫不…地'))])
replace_cards('l065',[(3,1,draft('想い','おもい','omoi','名词',meaning='思念、心意')),(4,2,draft('馳せて','はせて','hasete','动词',meaning='驰骋；寄托（思绪）'))])
replace_cards('l067',[(2,1,draft('綺麗','きれい','kirei','形容动词',meaning='美丽、漂亮')),(4,1,draft('なんて','なんて','nante','终助词式表达',function='表示惊叹、意外'))])
for fid in ['l001','l002','l003']:
    frames[fid]['classification']='opening-credit-display-only'; frames[fid]['grammarCards']=[]; changes.append({'frameId':fid,'field':'classification','new':'opening-credit-display-only'})
frames['l075']['outroAfterEndMs']=3057; changes.append({'frameId':'l075','field':'outroAfterEndMs','new':3057})

for f in doc['frames']: f['analysisStatus']='user-approved-high-confidence-merge'
(ROOT/'frames.json').write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
review=['# もうどうなってもいいや — 合并审核稿','', '已合并用户批准的高/极高置信度联网审核提案；中低置信度提案仍未合并。','']
for f in doc['frames']:
 c=f['caption']; review += [f"## {f['id']} · {f['startMs']/1000:.3f}s",'',f"日文：{c['japanese']}",f"中文：{c['translationZh']}",'']
 for x in f['grammarCards']: review.append(f"- {x['token']}（{x['reading']} / {x['romaji']}）：{x.get('functionZh') or x.get('zhMeaning','')}；{x['posZh']}（{x.get('status','draft')}）")
 review.append('')
text='\n'.join(review)
(ROOT/'review'/'mp3-audio-review.md').write_text(text,encoding='utf8')
(ROOT.parent/'deliverables'/'review'/'mou-dou-natte-mo-ii-ya-review.md').write_text(text,encoding='utf8')
log={'markdownImport':{'changes':0,'sha256Before':'c1f069a06706e196eb1dd1df8715fed583654928f2437beada2dbe2dfb472282'},'merge':'user approved all high-confidence proposals','translationChanges':len(translations),'structuralChanges':['l006','l009','l019','l060','l061','l063','l064','l065','l067'],'excluded':'medium and low confidence proposals','frameSha256':hashlib.sha256((ROOT/'frames.json').read_bytes()).hexdigest()}
(ROOT/'review'/'merge-log.json').write_text(json.dumps(log,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps(log,ensure_ascii=False))
