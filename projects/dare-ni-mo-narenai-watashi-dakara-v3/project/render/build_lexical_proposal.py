import hashlib,json
from pathlib import Path

ROOT=Path(r"C:\project\musicjlpt\projects\dare-ni-mo-narenai-watashi-dakara-v3")
frames_path=ROOT/'project'/'frames.json'
frames=json.loads(frames_path.read_text(encoding='utf-8'))['frames']
sha=hashlib.sha256(frames_path.read_bytes()).hexdigest()

# token, reading, Hepburn romaji, short POS.  Boundaries intentionally follow
# learnable lexical/fixed-expression units while concatenating back to the lyric.
D={
'l006':[('誰か','だれか','dareka','疑问代词'),('に','に','ni','助词'),('染まれない','そまれない','somarenai','动词（否定形）'),('誰にも','だれにも','darenimo','疑问代词＋助词'),('なれない','なれない','narenai','动词（否定形）')],
'l007':[('夢','ゆめ','yume','名词'),('だ','だ','da','助动词'),('と','と','to','助词'),('思って','おもって','omotte','动词（て形）'),('笑ってみせた','わらってみせた','waratte miseta','固定表达')],
'l008':[('忘れた','わすれた','wasureta','动词（た形）'),('弱さ','よわさ','yowasa','名词'),('悴んでいく','かじかんでいく','kajikande iku','动词（ていく形）')],
'l009':[('寂しい','さびしい','sabishii','形容词'),('なんて','なんて','nante','助词'),('言えるわけもない','いえるわけもない','ieru wake mo nai','固定表达')],
'l010':[('さりげない','さりげない','sarigenai','形容词'),('会話','かいわ','kaiwa','名词'),('すら','すら','sura','助词'),('傷つく','きずつく','kizutsuku','动词'),('心','こころ','kokoro','名词'),('は','は','wa','助词')],
'l011':[('誰一人','だれひとり','dare hitori','副词性表达'),('誰一人','だれひとり','dare hitori','副词性表达'),('幸せにしない','しあわせにしない','shiawase ni shinai','固定表达')],
'l012':[('ねぇ','ねぇ','nee','感叹词'),('それでも','それでも','soredemo','连词'),('まだ','まだ','mada','副词'),('期待','きたい','kitai','名词'),('膨らむんだ','ふくらむんだ','fukuramunda','固定表达')],
'l013':[('すれ違った','すれちがった','surechigatta','动词（た形）'),('嘘','うそ','uso','名词'),('なんて','なんて','nante','助词'),('全部','ぜんぶ','zenbu','名词'),('捨てて','すてて','sutete','动词（て形）')],
'l014':[('大逸れて','おおそれて','oosorete','动词（て形）')],
'l015':[('ないよって','ないよって','nai yo tte','固定表达'),('ただ','ただ','tada','副词'),('聞きたくて','ききたくて','kikitakute','动词（たい形）')],
'l016':[('夢ばかりで','ゆめばかりで','yume bakari de','固定表达'),('幼くたって','おさなくたって','osanakutatte','固定表达')],
'l017':[('今日も','きょうも','kyou mo','名词＋助词'),('変われない','かわれない','kawarenai','动词（否定形）')],
'l018':[('ままだって','ままだって','mama datte','固定表达'),('いいんだ','いいんだ','iinda','固定表达')],
'l019':[('君','きみ','kimi','名词'),('と','と','to','助词'),('歌っていたい','うたっていたい','utatte itai','动词（ていたい形）')],
'l020':[('何度だって','なんどだって','nando datte','副词性表达')],
'l021':[('感情','かんじょう','kanjou','名词'),('ばっか','ばっか','bakka','助词'),('揺れ動いて','ゆれうごいて','yureugoite','动词（て形）')],
'l022':[('嫌われてきた','きらわれてきた','kirawarete kita','动词（てきた形）'),('けど','けど','kedo','接续助词')],
'l023':[('このままで','このままで','kono mama de','固定表达'),('歩いて行くんだ','あるいていくんだ','aruite ikunda','固定表达')],
'l024':[('誰にも','だれにも','darenimo','疑问代词＋助词'),('なれない','なれない','narenai','动词（否定形）'),('私','わたし','watashi','名词'),('胸張って','むねはって','mune hatte','固定表达'),('さ','さ','sa','终助词')],
'l025':[('さよなら','さよなら','sayonara','感叹词'),('さよなら','さよなら','sayonara','感叹词'),('要らない','いらない','iranai','形容词'),('全部','ぜんぶ','zenbu','名词')],
'l026':[('全部','ぜんぶ','zenbu','名词'),('を','を','o','助词'),('消したら','けしたら','keshitara','动词（たら形）'),('自由に','じゆうに','jiyuu ni','形容动词'),('なれる','なれる','nareru','动词')],
'l027':[('煩い','うるさい','urusai','形容词'),('脳内','のうない','nounai','名词'),('誰か','だれか','dareka','疑问代词'),('の','の','no','助词'),('言葉','ことば','kotoba','名词')],
'l028':[('捨てたら','すてたら','sutetara','动词（たら形）'),('自分','じぶん','jibun','名词'),('を','を','o','助词'),('生きれる','いきれる','ikireru','动词（可能形）'),('のかな','のかな','no kana','终助词表达')],
'l029':[('立ち止まる','たちどまる','tachidomaru','动词'),('事','こと','koto','名词'),('ばかり','ばかり','bakari','助词'),('覚えてしまった','おぼえてしまった','oboete shimatta','固定表达')],
'l030':[('あれでもない','あれでもない','are demo nai','固定表达'),('これでもない','これでもない','kore demo nai','固定表达')],
'l031':[('歪んでしまった','ゆがんでしまった','yugande shimatta','固定表达')],
'l032':[('後悔ばかりで','こうかいばかりで','koukai bakari de','固定表达'),('夜','よる','yoru','名词'),('が','が','ga','助词'),('終わらない','おわらない','owaranai','动词（否定形）'),('や','や','ya','终助词')],
'l033':[('朝焼けには','あさやけには','asayake ni wa','名词＋助词'),('誰か','だれか','dareka','疑问代词'),('いて','いて','ite','动词（て形）'),('心躍る','こころおどる','kokoro odoru','固定表达')],
'l034':[('代償','だいしょう','daishou','名词'),('なんて','なんて','nante','助词')],
'l035':[('困難だって','こんなんだって','konnan datte','固定表达'),('超えていくって','こえていくって','koete ikutte','固定表达')],
'l036':[('決めたのに','きめたのに','kimeta noni','固定表达'),('壊したくなって','こわしたくなって','kowashitaku natte','固定表达')],
'l037':[('想像の中じゃ','そうぞうのなかじゃ','souzou no naka ja','固定表达'),('足りない','たりない','tarinai','动词（否定形）'),('くらいに','くらいに','kurai ni','助词表达')],
'l038':[('君','きみ','kimi','名词'),('と','と','to','助词'),('叶えてみたい','かなえてみたい','kanaete mitai','动词（てみたい形）')],
'l039':[('感傷','かんしょう','kanshou','名词'),('ばっか','ばっか','bakka','助词')],
'l040':[('なんで','なんで','nande','副词'),('心','こころ','kokoro','名词'),('に','に','ni','助词'),('壁','かべ','kabe','名词'),('を','を','o','助词')],
'l041':[('つくってしまうんだろう','つくってしまうんだろう','tsukutte shimaun darou','固定表达')],
'l042':[('誰か','だれか','dareka','疑问代词'),('の','の','no','助词'),('希望に','きぼうに','kibou ni','名词＋助词'),('なれるなら','なれるなら','nareru nara','动词（条件形）')],
'l043':[('誰にも','だれにも','darenimo','疑问代词＋助词'),('言えない','いえない','ienai','动词（否定形）'),('痛み','いたみ','itami','名词'),('引き連れて','ひきつれて','hikitsurete','动词（て形）'),('さ','さ','sa','终助词')],
'l044':[('ただ','ただ','tada','副词'),('独りでも','ひとりでも','hitori demo','副词性表达')],
'l045':[('紛れもない','まぎれもない','magire mo nai','固定表达'),('自分','じぶん','jibun','名词'),('を','を','o','助词'),('信じて','しんじて','shinjite','动词（て形）')],
'l046':[('傷つき','きずつき','kizutsuki','动词'),('堕ちる','おちる','ochiru','动词'),('たび','たび','tabi','名词'),('歌えばいい','うたえばいい','utaeba ii','固定表达')],
}

# Explicit ruby: literal kanji runs only.  Existing kana remains unannotated.
R={
'l006':[('誰','だれ'),('染','そ'),('誰','だれ')], 'l007':[('夢','ゆめ'),('思','おも'),('笑','わら')], 'l008':[('忘','わす'),('弱','よわ'),('悴','かじか')], 'l009':[('寂','さび'),('言','い')], 'l010':[('会話','かいわ'),('傷','きず'),('心','こころ')], 'l011':[('誰一人','だれひとり'),('誰一人','だれひとり'),('幸','しあわ')], 'l012':[('期待','きたい'),('膨','ふく')], 'l013':[('違','ちが'),('嘘','うそ'),('全部','ぜんぶ'),('捨','す')], 'l014':[('大逸','おおそ')], 'l015':[('聞','き')], 'l016':[('夢','ゆめ'),('幼','おさな')], 'l017':[('今日','きょう'),('変','か')], 'l019':[('君','きみ'),('歌','うた')], 'l020':[('何度','なんど')], 'l021':[('感情','かんじょう'),('揺','ゆ'),('動','うご')], 'l022':[('嫌','きら')], 'l023':[('歩','ある'),('行','い')], 'l024':[('誰','だれ'),('私','わたし'),('胸','むね'),('張','は')], 'l025':[('要','い'),('全部','ぜんぶ')], 'l026':[('全部','ぜんぶ'),('消','け'),('自由','じゆう')], 'l027':[('煩','うるさ'),('脳内','のうない'),('誰','だれ'),('言葉','ことば')], 'l028':[('捨','す'),('自分','じぶん'),('生','い')], 'l029':[('立','た'),('止','ど'),('事','こと'),('覚','おぼ')], 'l031':[('歪','ゆが')], 'l032':[('後悔','こうかい'),('夜','よる'),('終','お')], 'l033':[('朝焼','あさや'),('誰','だれ'),('心躍','こころおど')], 'l034':[('代償','だいしょう')], 'l035':[('困難','こんなん'),('超','こ')], 'l036':[('決','き'),('壊','こわ')], 'l037':[('想像','そうぞう'),('中','なか'),('足','た')], 'l038':[('君','きみ'),('叶','かな')], 'l039':[('感傷','かんしょう')], 'l040':[('心','こころ'),('壁','かべ')], 'l042':[('誰','だれ'),('希望','きぼう')], 'l043':[('誰','だれ'),('言','い'),('痛','いた'),('引','ひ')], 'l044':[('独','ひとり')], 'l045':[('紛','まぎ'),('自分','じぶん'),('信','しん')], 'l046':[('傷','きず'),('堕','お'),('歌','うた')]
}

def rubies(text, pairs):
    result=[]; pos=0
    for base,reading in pairs:
        i=text.find(base,pos)
        if i<0: raise ValueError((text,base))
        result.append({'base':base,'reading':reading,'start':i,'end':i+len(base)})
        pos=i+len(base)
    return result
def card(t,r,ro,pos):
    return {'token':t,'reading':r,'romaji':ro,'grammarStructureZh':pos,'posZh':pos,'render':True,'showJlpt':False,'status':'assisted-proposal','fieldProvenance':{'token':'lexical v2 proposal','reading':'lexical v2 proposal','romaji':'lexical v2 proposal','grammarStructureZh':'lexical v2 proposal'}}
changes=[]
for f in frames:
    fid=f['id']; text=f['caption']['japanese']; units=D[fid]
    expected=text.replace(' ','').replace('？','').replace('?','')
    if ''.join(x[0] for x in units)!=expected:
        raise ValueError(f'{fid}: '+''.join(x[0] for x in units)+' != '+text)
    newcards=[card(*x) for x in units]
    changes.append({'frameId':fid,'field':'grammarCards','old':f['grammarCards'],'new':newcards,'confidence':0.93,'evidence':['JLPT Dictionary / Weblio lexical segmentation cross-check','learnable fixed-expression grouping; exact lyric-character coverage asserted'],'changesTokenStructure':True})
    newruby=rubies(text,R.get(fid,[]))
    changes.append({'frameId':fid,'field':'caption.furigana','old':f['caption'].get('furigana',[]),'new':newruby,'confidence':0.95,'evidence':['kanji-only ruby; literal kana deliberately unannotated'],'changesTokenStructure':False})
    newroma=' '.join(x[2] for x in units)
    changes.append({'frameId':fid,'field':'caption.romaji','old':f['caption'].get('romaji',''),'new':newroma,'confidence':0.95,'evidence':['revised Hepburn romaji aligned to lexical card units'],'changesTokenStructure':False})
out={'schemaVersion':2,'reviewRole':'lexical','scope':{'frameIds':[f['id'] for f in frames]},'baseFrameSha256':sha,'changes':changes}
dst=ROOT/'project'/'proposals'/'lexical.json'; dst.parent.mkdir(exist_ok=True)
dst.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'output':str(dst),'frames':len(frames),'changes':len(changes),'cards':sum(len(D[f['id']]) for f in frames),'sha':sha},ensure_ascii=False))
