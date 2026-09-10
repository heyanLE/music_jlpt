"""Apply confirmed global card rules for うちゅうのふしぎ."""
import json
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
PATH = ROOT / 'uchuu.frames.approved.json'
REVIEW = ROOT / 'output' / 'uchuu-remaining-review.md'
data = json.loads(PATH.read_text(encoding='utf8'))
gloss_cache = {}
NOUN_GLOSSES = {
    '鳥': '鸟', '空': '天空', '猫': '猫', '今日': '今天', 'ぜんぶ': '全部',
    'さがし': '寻找', '朝': '早晨', '夜': '夜晚', 'こと': '事情', 'はんぶん': '一半',
    '世界': '世界', 'すみっこ': '角落', 'うちゅう': '宇宙', 'ふしぎ': '不可思议',
    '話': '话题', '歌': '歌曲', '花': '花朵',
}
def translate(text):
    if text not in gloss_cache:
        try:
            query = urllib.parse.urlencode({'client':'gtx','sl':'ja','tl':'zh-CN','dt':'t','q':text})
            with urllib.request.urlopen('https://translate.googleapis.com/translate_a/single?' + query, timeout=15) as response:
                payload=json.loads(response.read().decode('utf8'))
            gloss_cache[text]=''.join(item[0] for item in payload[0] if item and item[0])
        except Exception:
            gloss_cache[text]='待人工复核'
    return gloss_cache[text]
changed=[]
for frame in data['frames']:
    cards=frame['grammarCards']; result=[]; i=0; did=False
    while i < len(cards):
        pair=cards[i:i+2]
        if len(pair)==2 and pair[0]['token']=='なん' and pair[1]['token']=='で':
            result.append({'token':'なんで','reading':'なんで','romaji':'nande','dictionaryForm':'なんで','posJa':'副詞','posZh':'疑问副词','zhMeaning':'为什么','reviewRequired':False,'render':True,'showJlpt':False})
            i+=2; did=True
        else:
            result.append(cards[i]); i+=1
    if did:
        frame['grammarCards']=result
        frame['caption']['furigana']=[{'base':c['token'],'reading':c['reading'],'romaji':c['romaji']} for c in result]
        frame['caption']['romaji']=' '.join(c['romaji'] for c in result)
        frame['analysisStatus']='global-なんで-normalized'
        changed.append(frame['id'])
    # Nouns are now direct dictionary-form translations; particles keep functions.
    for card in frame['grammarCards']:
        if card.get('posJa') == '\u540d\u8a5e':
            word = card.get('dictionaryForm') or card['token']
            card['zhMeaning'] = NOUN_GLOSSES.get(word) or translate(word)
            card['reviewRequired'] = False
PATH.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

lines=['# うちゅうのふしぎ｜逐句词卡审核','', '已确认规则：`なんで` 合并为「为什么｜疑问副词」。请直接修改其余词卡。','']
for f in data['frames']:
    cap=f['caption']; lines += [f'## {f["id"]} · {f["startMs"]/1000:.3f}s','',f'日文：{cap["japanese"]}',f'暂定中文：{cap["translationZh"]}','', '待核词卡：']
    for c in f['grammarCards']:
        lines += [f'- `{c["token"]}`｜{c["reading"]}｜{c["romaji"]}',f'  - 暂定：{c.get("functionZh") or c["zhMeaning"]}',f'  - 词性：{c["posZh"]}']
    lines.append('')
REVIEW.write_text('\n'.join(lines),encoding='utf8')
print('updated',','.join(changed) or 'none')
