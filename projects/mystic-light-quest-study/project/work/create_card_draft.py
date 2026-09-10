"""Build an explicit, reviewable draft without modifying frozen lyric sources."""
import json, re, hashlib, sys, copy
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
P=ROOT/'project'
# Ruby notation records only the reading of the enclosed contiguous kanji.
# Each row: annotated token | reading | romaji | meaning/function | structure.
DATA={
'l001': '''ここ|ここ|koko|这里|指示代词
から|から|kara|表示起点|格助词
{全:すべ}て|すべて|subete|一切；全部|名词
{始:はじ}まる|はじまる|hajimaru|开始|自动词''',
'l002': '''{私:わたし}|わたし|watashi|我|人称代词
は|は|wa|提示主题|提示助词
ただ|ただ|tada|只是；仅仅|副词
{知:し}りたい|しりたい|shiritai|想知道；想了解|动词＋たい''',
'l003': '''{遠:とお}く|とおく|tooku|远远地|イ形容词连用形
{離:はな}れても|はなれても|hanaretemo|即使相隔；即使远离|动词＋ても''',
'l004': '''{大地:だいち}|だいち|daichi|大地|名词
{照:て}らす|てらす|terasu|照耀|他动词''',
'l005': '''{砂:すな}|すな|suna|沙子|名词
に|に|ni|标示受阻的原因|格助词
{足:あし}を{取:と}られて|あしをとられて|ashi o torarete|脚步受阻；陷住脚|惯用表达·被动て形''',
'l006': '''それでも|それでも|soredemo|即便如此|连词
{歩:ある}き{続:つづ}ける|あるきつづける|arukitsuzukeru|继续行走|复合动词''',
'l007': '''{新:あたら}しい|あたらしい|atarashii|崭新的|イ形容词
{風:かぜ}|かぜ|kaze|风|名词
あの|あの|ano|那个|连体词
{日:ひ}|ひ|hi|日子；那一天|名词
の|の|no|连接所属或修饰关系|格助词
{記憶:きおく}|きおく|kioku|记忆|名词''',
'l008': '''{私:わたし}|わたし|watashi|我|人称代词
の|の|no|表示所属|格助词
{心:こころ}|こころ|kokoro|心；心灵|名词
{癒:いや}す|いやす|iyasu|治愈；抚慰|他动词
オアシス|おあしす|oashisu|绿洲|外来语名词''',
'l009': '''{隠:かく}された|かくされた|kakusareta|被隐藏的|动词被动过去形
{秘密:ひみつ}|ひみつ|himitsu|秘密|名词
なら|なら|nara|提出假设或话题|助动词条件形''',
'l010': '''{私:わたし}|わたし|watashi|我|人称代词
が|が|ga|标示动作主体|格助词
{見:み}つけ{出:だ}す|みつけだす|mitsukedasu|找出；寻获|复合动词
から|から|kara|说明理由并加强承诺|接续助词''',
'l011': '''{誰:だれ}も|だれも|dare mo|与否定呼应：任何人都不|疑问代词＋も
{知:し}らない|しらない|shiranai|不知道|动词否定形
{場所:ばしょ}|ばしょ|basho|地方|名词
へ|へ|e|表示前往的方向|格助词
{太陽:たいよう}|たいよう|taiyou|太阳|名词
を{頼:たよ}りに|をたよりに|o tayori ni|以……为依靠或指引|固定表达''',
'l014': '''もっと|もっと|motto|更加|副词
{強:つよ}く|つよく|tsuyoku|强烈地；有力地|イ形容词连用形
{輝:かがや}いて|かがやいて|kagayaite|闪耀吧；绽放光芒|动词て形''',
'l015': '''{誰:だれ}も{彼:かれ}も|だれもかれも|dare mo kare mo|每个人；所有人|固定表达
{夢:ゆめ}{見:み}ている|ゆめみている|yumemiteiru|怀抱梦想；憧憬着|动词＋ている''',
'l016': '''{流:なが}れ{行:ゆ}く|ながれゆく|nagareyuku|流逝而去|复合动词
{時:とき}|とき|toki|时光|名词
の|の|no|连接修饰关系|格助词
{中:なか}|なか|naka|之中|名词''',
'l017': '''{自由:じゆう}|じゆう|jiyuu|自由|名词
{手:て}に{入:い}れる|てにいれる|te ni ireru|得到；获得|惯用表达
ため|ため|tame|为了；表示目的|形式名词''',
'l018': '''まだ|まだ|mada|还；仍然|副词
{行:い}ける|いける|ikeru|能去；还能前进|动词可能形
ずっとずっと|ずっとずっと|zutto zutto|更远更远；一直|副词重复
{奥深:おくふか}く|おくふかく|okufukaku|向深处；深入地|イ形容词连用形''',
'l019': '''{導:みちび}かれていく|みちびかれていく|michibikareteiku|被引导着前行|被动形＋ていく
{未知:みち}なる|みちなる|michinaru|未知的|名词＋文语连体形
{大地:だいち}|だいち|daichi|大地|名词''',
'l020': '''{燃:も}えるような|もえるような|moeru you na|如同燃烧般的|动词＋ような
{陽:ひ}|ひ|hi|太阳；阳光|名词
を|を|o|标示动作对象|格助词
{浴:あ}びながら|あびながら|abinagara|一边沐浴着|动词＋ながら''',
'l021': '''{追:お}い{求:もと}めている|おいもとめている|oimotometeiru|不断追求着|复合动词＋ている
もの|もの|mono|所追求的事物|形式名词
は|は|wa|提出疑问的主题|提示助词''',
'l022': '''これ{以上:いじょう}|これいじょう|kore ijou|再；比这更多|固定表达
{朽:く}ち{果:は}てないで|くちはてないで|kuchihatenaide|不要彻底腐朽消亡|复合动词＋ないで''',
'l024': '''{今:いま}まで|いままで|ima made|至今；迄今为止|时间表达
{出会:であ}えた|であえた|deaeta|得以遇见的|动词可能过去形
{奇跡:きせき}|きせき|kiseki|奇迹|名词
を|を|o|标示动作对象|格助词
{集:あつ}めて|あつめて|atsumete|收集起来|动词て形''',
'l025': '''{心:こころ}|こころ|kokoro|心；心灵|名词
が|が|ga|标示状态主体|格助词
{躍:おど}れば|おどれば|odoreba|若心情雀跃|动词ば形''',
'l026': '''{探:さが}していた|さがしていた|sagashiteita|一直寻找着的|动词＋ていた
もの|もの|mono|所寻找的事物|形式名词
が|が|ga|标示被找到的主体|格助词
{見:み}つかる|みつかる|mitsukaru|被找到；找到|自动词
よ|よ|yo|告知并加强肯定语气|终助词''',
'l027': '''{季節:きせつ}|きせつ|kisetsu|季节|名词
{巡:めぐ}る|めぐる|meguru|轮转；循环更替|自动词
{度:たび}|たび|tabi|每当；每一次|形式名词
{過去:かこ}|かこ|kako|过去|名词
が|が|ga|标示状态主体|格助词
{蘇:よみがえ}るように|よみがえるように|yomigaeru you ni|如同往事复苏一般|动词＋ように''',
'l038': '''{自由:じゆう}|じゆう|jiyuu|自由|名词
{手:て}に{入:い}れられたら|てにいれられたら|te ni ireraretara|如果能获得|惯用表达·可能条件形''',
'l039': '''もっと|もっと|motto|更加|副词
{強:つよ}くなる|つよくなる|tsuyoku naru|变得强大|イ形容词＋なる
ために|ために|tame ni|为了；表示目的|目的表达''',
'l040': '''{私:わたし}|わたし|watashi|我|人称代词
なら|なら|nara|提出假设或话题|助动词条件形
できる|できる|dekiru|能够做到|动词
はず|はず|hazu|应当；理应|形式名词''',
'l041': '''{遠:とお}い|とおい|tooi|遥远的|イ形容词
{日:ひ}|ひ|hi|日子；往日|名词
の|の|no|连接修饰关系|格助词
{記憶:きおく}|きおく|kioku|记忆|名词
{辿:たど}り|たどり|tadori|追溯；循着|动词连用形''',
'l042': '''{宝物:たからもの}|たからもの|takaramono|宝物|名词
{手:て}に{入:い}れる|てにいれる|te ni ireru|得到；获得|惯用表达
まで|まで|made|表示动作持续的终点|副助词''',
}
REPEATS={'l028':'l007','l029':'l008','l030':'l009','l031':'l010','l032':'l011','l035':'l014','l036':'l015','l037':'l016'}
PURE_ENGLISH={'l012','l013','l023','l033','l034'}
FUNCTIONS={'から','は','に','の','なら','が','へ','を','よ','まで'}
def write(path,obj): path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def main():
    path=P/'frames.json'; doc=json.loads(path.read_text(encoding='utf-8'))
    before=path.read_bytes(); backup=P/'review/frames-before-card-draft.json'
    if not backup.exists(): backup.write_bytes(before)
    functions={}; review=['# Mystic Light Quest 词卡草稿','', '状态：待多角色审核。中文整句保留 QMTS；词卡均为暂定。','']
    for frame in doc['frames']:
        fid=frame['id']; text=frame['caption']['japanese']; rows=[] if fid in PURE_ENGLISH else DATA[REPEATS.get(fid,fid)].splitlines()
        cards=[]; ruby=[]; cursor=0
        for raw in rows:
            annotated,reading,romaji,meaning,pos=raw.split('|')
            token=re.sub(r'\{([^:]+):([^}]+)\}',r'\1',annotated)
            start=text.find(token,cursor)
            assert start>=0,(fid,token,text)
            local=0; prev=0
            for m in re.finditer(r'\{([^:]+):([^}]+)\}',annotated):
                local+=len(annotated[prev:m.start()]); base,rr=m.groups()
                ruby.append({'base':base,'reading':rr,'start':start+local,'end':start+local+len(base),'cardIndex':len(cards),'surfaceOffset':local})
                local+=len(base);prev=m.end()
            card={'token':token,'reading':reading,'romaji':romaji,'grammarStructureZh':pos,'render':True,'showJlpt':False,'status':'draft','fieldProvenance':{'token':'learning-value segmentation draft','reading':'QM kana/romaji source checked draft','meaningOrFunction':'contextual assistant draft; pending review','grammarStructureZh':'assistant draft; pending review'}}
            field='functionZh' if token in FUNCTIONS else 'zhMeaning'
            card[field]=meaning
            if field=='functionZh': functions.setdefault(token,set()).add(meaning)
            if token=='オアシス':card['sourceWord']='oasis'
            cards.append(card);cursor=start+len(token)
        # Verify coverage while keeping the original mixed-language row intact.
        remainder=text
        for c in cards:remainder=remainder.replace(c['token'],'',1)
        assert not re.search(r'[一-鿿ぁ-ゖァ-ヺ]',remainder),(fid,remainder)
        frame['grammarCards']=cards;frame['caption']['furigana']=ruby
        frame['caption']['romaji']=' '.join(c['romaji'] for c in cards)
        frame['caption']['translationStatus']='qmts-source-preserved'
        frame['status']='draft'
        review += [f"## {fid} · {frame['startMs']/1000:.3f}s",'',text,'',f"暂定中文：{frame['caption']['translationZh']}",'','待核词卡：','']
        if not cards: review+=['纯英文：不生成词卡、假名或罗马音。','']
        for c in cards: review += [f"- {c['token']}｜{c['reading']}｜{c['romaji']}｜{c.get('zhMeaning',c.get('functionZh'))}｜{c['grammarStructureZh']}" + (f"｜来源词：{c['sourceWord']}" if c.get('sourceWord') else '')]
        review+=['']
    write(path,doc)
    write(P/'review/particle-function-table.json',{'schemaVersion':1,'status':'draft','functions':{k:sorted(v) for k,v in functions.items()}})
    (ROOT/'deliverables/review/mystic-light-quest-study-review.md').write_text('\n'.join(review),encoding='utf-8')
    print(json.dumps({'frames':len(doc['frames']),'cards':sum(len(f['grammarCards']) for f in doc['frames']),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}))
if __name__=='__main__':main()
