from __future__ import annotations
import json
from pathlib import Path
P=Path(__file__).resolve().parents[2]/'project'; F=P/'frames.json'
M={'あの':'那个；那时的','ある':'有；存在','い':'在；存在','いい':'好；可以','いつ':'何时','いる':'在；存在','こんなにも':'如此；这么','し':'做；进行','すぐ':'立刻；马上','ずっと':'一直','その':'那个','それだけ':'仅此；只是那样','た':'过去；完成','だ':'是','ちゃんと':'好好地；确实地','て':'连接后续动作','でも':'但是；即使','どうか':'请；务必','どこ':'哪里','な':'构成连体修饰','ない':'不；没有','なら':'如果是；既然','なれ':'变得；能够成为','ほど遠い':'相差甚远','ぼんやり':'模糊地；发呆地','上':'上面；之上','中':'之中','僕':'我（男性自称）','光':'光；光芒','出る':'出来；出现','君':'你','夢':'梦','大丈夫':'没关系；没问题','大変':'辛苦；严重','寂しく':'寂寞地','彗星':'彗星','影':'影子','思い出':'回忆','思い浮かべ':'想起；浮现于脑海','悲しい':'悲伤的','探し':'寻找','新しく':'新地；重新','方':'方法；一方','星':'星星','時':'时候','時々':'有时','時間':'时间','晴天':'晴天','暇':'空闲','暗闇':'黑暗','最高':'最好；最高','楽しい':'快乐的','正常':'正常','歩く':'走；步行','比べ':'比较','無い':'没有；不存在','熱':'热度；热情','生きる':'活着；生活','異常':'异常','痛み':'疼痛','皆':'大家','眠る':'睡；沉睡','確かめる':'确认；弄清','終わら':'结束','考える':'思考','見え':'能看见；显得','解る':'明白；理解','軌跡':'轨迹','透明':'透明','銀河':'银河','間':'之间；期间','靴':'鞋'}
x=json.loads(F.read_text(encoding='utf-8')); missing=[]
for f in x['frames']:
 for c in f.get('grammarCards',[]):
  if c.get('zhMeaning')=='待联网核对':
   if c['token'] not in M: missing.append(c['token'])
   else: c['zhMeaning']=M[c['token']]; c['status']='assisted-accepted'; c.setdefault('fieldProvenance',{})['meaningOrFunction']='targeted lexical completion after user approval'
if missing: raise RuntimeError(sorted(set(missing)))
F.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
