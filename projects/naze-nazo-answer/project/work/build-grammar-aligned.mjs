import fs from 'node:fs';
import crypto from 'node:crypto';
import path from 'node:path';

const root = 'C:/project/musicjlpt/projects/naze-nazo-answer';
const lexicalPath = path.join(root, 'project/proposals/lexical.json');
const lexicalText = fs.readFileSync(lexicalPath, 'utf8');
const lexical = JSON.parse(lexicalText);
const lexicalSha256 = crypto.createHash('sha256').update(lexicalText).digest('hex');

const defaults = {
  'なぜ': '疑问副词', 'なぞ': '名词', '謎': '名词', '点': '名词', '線': '名词',
  'あら': '感叹词', 'はなまる': '名词', '解決': '名词', '推理': '名词',
  'うら返し': '名词', '二転三転': '副词性名词', '逆転': '名词', '言葉': '名词',
  '仕草': '名词', '罠': '名词', 'だめ': '形容动词', 'よく': '副词',
  'みて': '动词て形', '考えて': '动词て形', 'それから': '接续词',
  '踏み出す': '复合动词', '1歩': '数量表达', '困っている': '持续体', '人': '名词',
  '見たら': '动词たら形', 'すぐに': '副词', '助けたい': '希望形', 'だって': '接续词',
  '何とか': '副词', '何とかしたくて': '希望形て形', '駈け出している': '复合动词持续体',
  '解く': '动词', '名探偵': '名词', 'うそ': '名词', 'まごこと': '名词',
  '見極めて': '复合动词て形', '笑顔': '名词', '答え': '名词', '見つける': '动词',
  'みんな': '名词', 'いると': '动词＋条件', '勇気': '名词', '100倍': '数量表达',
  'ちから合わせて': '复合动词て形', '乗り超える': '复合动词', '友': '名词',
  'キセキ': '名词', 'かたまり': '名词', '行く': '动词', 'つなげたら': '动词たら形',
  'かも': '终助词', '矢印': '名词', 'もう': '副词', '指す': '动词',
  '痛快': '形容动词词干', '愉快': '形容动词词干', '爽快': '形容动词词干',
  'だけど': '接续词', 'でも': '接续词', '解き明かせない': '可能形否定', 'それ': '代词',
  '心': '名词', '迷宮': '名词', '秘密': '名词', '鍵': '名词', 'こじ開けない': '复合动词否定',
  '寄り添う': '动词', 'だけで': '限定表达', 'ごめん': '感叹词', '傷付いてる': '持续体口语',
  '居ると': '动词＋条件', 'コトバ': '名词', 'じゃなくって': '否定连接', 'ずっと': '副词',
  'そばで': '地点表达', '誰より': '比较表达', '味方でいたい': '状态表达', '追えば': '动词ば形',
  '追うほど': '程度表达', '逃げていく': '补助动词表达', 'ムジュン': '名词', 'だらけ': '接尾表达',
  'ミステリー': '名词', 'いれば': '动词ば形', '元気': '形容动词词干', 'ミス': '名词',
  'では': '助词短语', '終わらない': '动词否定形', '伏線回収': '名词＋する',
  '正しさって': '名词＋引用助词', '人によって': '复合格助词', '変わるけど': '动词＋接续助词',
  'やさしさなら': '名词＋条件', 'びくかな': '动词＋终助词', 'ポカポカ': '副词',
  'ときゅんきゅん': '拟声词短语', '届けたい': '希望形', 'あと': '名词',
  '見えてくる': '补助动词表达', 'キボウ': '名词', 'シャラララ': '唱词',
  '友だち': '名词', '光る': '动词', 'ジュエル': '名词', '1人': '数量表达',
  'みんなで': '名词＋で', '輝いてる': '持续体口语', '1000倍': '数量表达',
  '手に手をとって': '固定表达', '万事解決するまで': '固定表达', 'プリキュア': '专有名词'
};

function particleFunction(frameId, token, index) {
  const perFrame = {
    l003: { 'と': '并列连接两个名词', 'を': '标记结ぶ的动作对象' },
    l005: { 'と': '并列连接推理与謎', 'は': '提示謎为主题' },
    l006: { 'や': '不完全列举言葉、仕草等', 'さえ': '强调极端例，连…也' },
    l010: { 'を': '标记解く的动作对象', 'の': '将前面的动作名词化', 'が': '标记名词化短语为主语' },
    l011: { 'か': '连接うそ与まごこと，表示选择', 'の': '连接笑顔与答え' },
    l012: { 'と': '表示与大家一起的对象' },
    l013: { 'は': '提示友为主题', 'の': '连接キセキ与かたまり' },
    l015: { 'と': '并列连接点与線', 'を': '标记つなげる的动作对象' },
    l016: { 'は': '提示矢印为主题', 'を': '标记指す的动作对象' },
    l018: { 'ね': '缓和语气并唤起共鸣', 'は': '提示それ为主题', 'の': '连接心与迷宮' },
    l019: { 'の': '连接秘密与鍵' },
    l022: { 'を': '标记解く的动作对象', 'の': '将前面的动作名词化', 'が': '标记名词化短语为主语' },
    l024: { 'と': '表示与大家一起的对象' },
    l025: { 'は': '提示ミス为主题', 'と': '表示与朋友一起' },
    l030: { 'は': '提示友だち为主题' },
    l031: { 'を': '标记解く的动作对象', 'の': '将前面的动作名词化', 'が': '标记名词化短语为主语' },
    l032: { 'か': '连接候选内容，表示选择', 'の': '连接笑顔与答え' },
    l033: { 'と': '表示与大家一起的对象' },
    l034: { 'は': '提示友为主题', 'の': '连接キセキ与かたまり' },
    l036: { 'と': '表示与大家一起的对象' },
    l037: { 'と': '表示与朋友一起' }
  };
  if (perFrame[frameId]?.[token]) return perFrame[frameId][token];
  if (token === 'かな') return '表示自问或推测语气';
  if (token === 'かも') return '表示不确定的推测';
  if (token === 'ね') return '缓和语气并唤起共鸣';
  if (token === 'だけで') return '表示仅凭这一条件或方式';
  if (token === 'では') return '表示以某状态为界或条件';
  if (token === 'よ') return '句末加强提醒、劝说语气';
  if (token === 'か') return '表示选择或疑问';
  if (token === 'の') return '连接名词或将前项名词化';
  if (token === 'が') return '标记主语';
  if (token === 'は') return '提示主题';
  if (token === 'を') return '标记动作对象';
  if (token === 'と') return '表示并列或共同对象';
  return null;
}

const cardChanges = lexical.changes.filter(x => x.field === 'grammarCards').map(change => {
  const newCards = change.new.map((source, index) => {
    const card = {...source};
    delete card.zhMeaning;
    delete card.functionZh;
    card.grammarStructureZh = defaults[card.token] || card.posZh || '名词';
    const functionZh = particleFunction(change.frameId, card.token, index);
    if (functionZh) card.functionZh = functionZh;
    return card;
  });
  return {
    frameId: change.frameId,
    field: 'grammarCards',
    old: change.new,
    new: newCards,
    confidence: 0.97,
    evidence: ['Grammar alignment against final lexical card boundaries', 'Particles retain functionZh only; non-particles receive concise grammarStructureZh'],
    changesTokenStructure: false
  };
});

const output = {
  schemaVersion: 2,
  reviewRole: 'grammar-aligned',
  scope: {frameIds: cardChanges.map(x => x.frameId), coverage: 'all-final-lexical-card-bundles'},
  baseFrameSha256: lexical.baseFrameSha256,
  alignsTo: {proposal: 'project/proposals/lexical.json', sha256: lexicalSha256},
  changes: cardChanges,
  reviewNotes: ['l011 和 l032 保留 QQ QRC 的原始文字，不对歌词显示文本做校正。', '助词卡只提供 functionZh；卡面第三行由 grammarStructureZh 或 posZh 使用简洁词性。']
};

fs.writeFileSync(path.join(root, 'project/proposals/grammar-aligned.json'), JSON.stringify(output, null, 2) + '\n', 'utf8');
