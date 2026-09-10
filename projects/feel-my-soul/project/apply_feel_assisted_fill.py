"""Apply reviewed semantic chunks for feel my soul and rebuild its review document."""
import copy,json
from pathlib import Path
ROOT=Path(__file__).parent; PATH=ROOT/'feel-my-soul.frames.approved.json'; REVIEW=ROOT/'output'/'feel-my-soul-review.md'
d=json.loads(PATH.read_text(encoding='utf8')); fs={f['id']:f for f in d['frames']}
def C(t,r,ro,m,p):
 c={'token':t,'reading':r,'romaji':ro,'zhMeaning':m,'posZh':p,'render':True,'showJlpt':False,'reviewRequired':False}
 if '助词' in p:c['functionZh']=m
 return c
def setf(fid,items,zh=None):
 f=fs[fid]; f['grammarCards']=[C(*x) for x in items]
 if zh:f['caption']['translationZh']=zh

setf('l001',[('泣き疲れてた','ナキツカレテタ','nakitsukareteta','哭得精疲力尽了','动词短语'),('んだ','ンダ','nda','说明、强调语气','终助词')],'我已经哭得精疲力尽了。')
setf('l002',[('問いかける','トイカケル','toikakeru','询问、追问','动词'),('場所','バショ','basho','地方','名词'),('も','モ','mo','也（强调连……也没有）','提示助词'),('なく','ナク','naku','没有、无','形容词活用')],'连一个能追问的地方也没有。')
setf('l003',[('迷いながら','マヨイナガラ','mayoinagara','一边迷惘着','动词＋接续助词'),('つまずいても','ツマズイテモ','tsumazuitimo','即使跌倒','动词＋接续助词')],'即使一边迷惘、一边跌倒。')
setf('l004',[('立ち止まれない','タチドマレナイ','tachidomarenai','无法停下脚步','动词否定可能形')],'也无法就这样半途而废。')
setf('l005',[('Yeah','Yeah','yeah','是啊','感叹词'),('just','just','just','只管、就','副词'),('believe it','believe it','believe it','相信它、坚信吧','动词短语')],'是啊，只管相信吧。')
setf('l006',[('君','キミ','kimi','你','人称代词'),('が','ガ','ga','主语标记','格助词'),('くれた','クレタ','kureta','为我给出的','授受动词过去形'),('笑顔','エガオ','egao','笑容','名词'),('落とした','オトシタ','otoshita','落下的、流下的','动词过去形'),('涙','ナミダ','namida','眼泪','名词'),('は','ハ','wa','主题提示','提示助词')],'你为我展露的笑容、流下的泪水。')
setf('l007',[('僕','ボク','boku','我','人称代词'),('の','ノ','no','所属修饰','格助词'),('胸','ムネ','mune','胸口、内心','名词'),('の','ノ','no','所属修饰','格助词'),('深い','フカイ','fukai','深深的','形容词'),('傷','キズ','kizu','伤痕','名词'),('に','ニ','ni','动作触及的对象','格助词'),('触れて消えた','フレテキエタ','furetekieta','触及后消散了','动词短语')],'触及我内心深处的伤痕后消散了。')
setf('l008',[('I','I','I','我','人称代词'),('feel my soul','feel my soul','feel my soul','感受我的灵魂','动词短语'),('take me','take me','take me','带着我','动词短语'),('your way','your way','your way','你的道路、方向','名词短语')],'我感受着灵魂，带我走向你的方向。')
setf('l009',[('そう','ソウ','sou','是啊、没错','副词'),('たったひとつ','タッタヒトツ','tatta hitotsu','唯一的一个','副词＋名词'),('を','ヲ','wo','动作对象','格助词')],'是啊，每个人都一定一直在寻找那唯一的一个（答案）。')
setf('l010',[('きっと','キット','kitto','一定','副词'),('誰もが','ダレモガ','daremoga','每个人都','疑问代词＋提示助词＋格助词'),('ずっと','ズット','zutto','一直','副词'),('探している','サガシテイル','sagashiteiru','一直寻找着','动词进行形'),('の','ノ','no','说明、抒情语气','终助词')],'是啊，每个人都一定一直在寻找那唯一的一个（答案）。')
setf('l011',[('それ','ソレ','sore','那件事','指示代词'),('は','ハ','wa','主题提示','提示助词'),('偶然ではなくて','グウゼンデハナクテ','guuzen de wa nakute','并非偶然，而且……','名词＋断定助动词否定て形')],'那并非偶然。')
setf('l012',[('偽りの愛','イツワリノアイ','itsuwari no ai','虚伪的爱','名词短语'),('なんか','ナンカ','nanka','举例、轻视强调（之类）','副助词'),('じゃなくて','ジャナクテ','janakute','不是……而是、并且','断定助动词否定て形')],'也并非什么虚伪的爱。')
setf('l013',[('You’re right','You’re right','you’re right','你是对的','句子'),('all right','all right','all right','没关系、一切都会好的','感叹语')],'你是对的，一切都会好的。')
setf('l014',[('You’re right','You’re right','you’re right','你是对的','句子'),('all right','all right','all right','没关系、一切都会好的','感叹语'),('scared little boy','scared little boy','scared little boy','害怕的小男孩','名词短语')],'你是对的，没关系，害怕的小男孩。')
setf('l015',[('何度も','ナンドモ','nandomo','无数次、反复地','副词性短语'),('繰り返す','クリカエス','kurikaesu','反复、重来','动词'),('どうか','ドウカ','douka','请、务必','副词'),('行かないで','イカナイデ','ikanai de','请不要离开','动词否定て形')],'无论重复多少次，请不要离开。')
setf('l016',[('ささやくような','ササヤクヨウナ','sasayaku you na','像低语一般的','动词＋比况助动词'),('君','キミ','kimi','你','人称代词'),('の','ノ','no','所属修饰','格助词'),('声','コエ','koe','声音','名词'),('は','ハ','wa','主题提示','提示助词'),('愛しくて','イトシクテ','itoshikute','如此令人怜爱、眷恋着','形容词て形')],'你那像低语般的声音，令我无比眷恋。')
setf('l018',[('もう','モウ','mou','再也、不再','副词'),('振り向かない','フリムカナイ','furimukanai','不回头','动词否定形')],'我再也不会回头。')
setf('l019',[('きっと','キット','kitto','一定','副词'),('この手で','コノテデ','kono te de','用这双手、亲自','名词＋格助词'),('いま','イマ','ima','现在','名词性副词'),('確かめたい','タシカメタイ','tashikametai','想确认、想弄清','动词愿望形'),('よ','ヨ','yo','告知、强调','终助词')],'现在我一定想亲手确认。')
setf('l020',[('いつも','イツモ','itsumo','总是','副词'),('単純なほど','タンジュンナホド','tanjun na hodo','单纯得近乎……的程度','形容动词＋程度助词'),('苦しんで','クルシンデ','kurushinde','痛苦着、挣扎着','动词て形')],'我总是痛苦挣扎，因为想知道活下去的意义。')
setf('l021',[('生きてゆく','イキテユク','ikite yuku','活下去、继续生活','动词短语'),('意味','イミ','imi','意义','名词'),('を','ヲ','wo','动作对象','格助词'),('知りたい','シリタイ','shiritai','想知道','动词愿望形'),('から','カラ','kara','因为、由于','接续助词')],'我总是痛苦挣扎，因为想知道活下去的意义。')
setf('l024',[('そっと','ソット','sotto','轻轻地','副词'),('つぶやいた','ツブヤイタ','tsubuyaita','轻声说出','动词过去形'),('君','キミ','kimi','你','人称代词'),('の','ノ','no','所属修饰','格助词'),('言葉','コトバ','kotoba','话语','名词'),('you say it','you say it','you say it','你说出来','英语动词短语')],'你轻声说出的那些话。')
setf('l025',[('動き出せ','ウゴキダセ','ugokidase','行动起来吧','动词命令形')],'行动起来吧；虽然看不见，前路却正向你敞开。')
setf('l026',[('見えないけど','ミエナイケド','mienai kedo','虽然看不见，但是','动词否定形＋接续助词'),('道','ミチ','michi','道路、前路','名词'),('は','ハ','wa','主题提示','提示助词'),('開かれてる','ヒラカレテル','hirakareteru','正向你敞开','动词被动进行口语形')],'行动起来吧；虽然看不见，前路却正向你敞开。')
setf('l028',[('そう','ソウ','sou','那样、如此','副词'),('もがきながらも','モガキナガラモ','mogakinagara mo','即使挣扎着也……','动词＋接续助词＋提示助词')],'即使如此挣扎着也……')
setf('l029',[('きっと','キット','kitto','一定','副词'),('このまま','コノママ','kono mama','就这样、保持现状','副词性名词')],'也一定能就这样一直走下去。')
setf('l030',[('ずっと','ズット','zutto','一直、始终','副词'),('歩いてゆける','アルイテユケル','aruite yukeru','能够一路走下去','动词短语')],'也一定能就这样一直走下去。')
setf('l031',[('それ','ソレ','sore','那件事','指示代词'),('は','ハ','wa','主题提示','提示助词'),('偶然でもなくって','グウゼンデモナクッテ','guuzen demo nakutte','也并非偶然，而且……','名词＋断定助动词否定口语て形')],'那既不是偶然，也不是什么平凡的梦想。')
setf('l032',[('ありふれた','アリフレタ','arifureta','平凡常见的','连体词性表达'),('夢','ユメ','yume','梦想','名词'),('なんか','ナンカ','nanka','举例、轻视强调（之类）','副助词'),('じゃなくって','ジャナクッテ','janakutte','也不是……而是、并且','断定助动词否定口语て形')],'那既不是偶然，也不是什么平凡的梦想。')
setf('l033',[('You’re right all right','You’re right all right','you’re right all right','你是对的，一切都会好的','英语副歌'),('You’re right all right','You’re right all right','you’re right all right','你是对的，一切都会好的','英语副歌')],'你是对的，一切都会好的；你是对的，一切都会好的。')
setf('l035',[('喜び','ヨロコビ','yorokobi','喜悦','名词'),('の','ノ','no','所属修饰','格助词'),('意味','イミ','imi','意义','名词'),('を','ヲ','wo','动作对象','格助词'),('知りたい','シリタイ','shiritai','想知道','动词愿望形'),('から','カラ','kara','因为、由于','接续助词')],'因为我想知道喜悦的意义。')
for target,source in [('l017','l008'),('l027','l008'),('l022','l013'),('l036','l013'),('l023','l014'),('l037','l014'),('l034','l020')]:
 fs[target]['grammarCards']=copy.deepcopy(fs[source]['grammarCards']);fs[target]['caption']['translationZh']=fs[source]['caption']['translationZh']
for f in fs.values():
 f['caption']['furigana']=[{'base':c['token'],'reading':c['reading'],'romaji':c['romaji']} for c in f['grammarCards']];f['caption']['romaji']=' '.join(c['romaji'] for c in f['grammarCards']);f['analysisStatus']='assisted-linguistic-fill-needs-review';f['reviewRequired']=True
d['reviewStatus']='assisted-linguistic-fill-needs-human-review';d['assistedReviewSources']=['QQ Music qmts','QRC/QMRoma','dictionary-backed subagent review']
PATH.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
lines=['# feel my soul｜智能补全后词卡审核','', '已按语义重新分词、补齐英文副歌、同步重复句与跨行译文。请直接修改仍想调整的内容；确认后回复“核对完了”。','']
for f in d['frames']:
 cap=f['caption'];lines += [f'## {f["id"]} · {f["startMs"]/1000:.3f}s','',f'日文：{cap["japanese"]}',f'暂定中文：{cap["translationZh"]}','', '词卡：']
 for c in f['grammarCards']:lines += [f'- `{c["token"]}`｜{c["reading"]}｜{c["romaji"]}',f'  - 暂定：{c.get("functionZh") or c["zhMeaning"]}',f'  - 词性：{c["posZh"]}']
 lines.append('')
REVIEW.write_text('\n'.join(lines),encoding='utf8');print(REVIEW)
