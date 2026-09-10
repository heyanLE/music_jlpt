const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const projectRoot = path.resolve(__dirname, '..', '..');
const framesPath = path.join(projectRoot, 'project', 'frames.json');
const outputPath = path.join(projectRoot, 'project', 'proposals', 'lexical.json');
const expectedHash = '3e3a32c058e5eca15cce097f0ab61965511d3dbf66127431d55ce51e4064af9f';
const raw = fs.readFileSync(framesPath);
const actualHash = crypto.createHash('sha256').update(raw).digest('hex');
if (actualHash !== expectedHash) {
  throw new Error(`frames.json hash changed: expected ${expectedHash}, got ${actualHash}`);
}

const doc = JSON.parse(raw.toString('utf8'));
const byId = new Map(doc.frames.map((frame) => [frame.id, frame]));
const changes = [];

const qrcEvidence = [
  'project/timing/qm.json：冻结日文歌词、字符位置和逐词时间。',
  'project/timing/roma.json：冻结 QQ 音乐唱读轨；本提案以唱读轨而非词典默认音纠正歌曲实际读音。'
];
const rubyEvidence = [
  'japanese-song-study-video 固定前景契约：振假名只覆盖连续汉字段，不重复显示歌词中已有的平假名；纯假名词不显示振假名。',
  'project/timing/qm.json 与 project/timing/roma.json：逐字核对汉字位置和对应唱读。'
];

function add(frameId, field, oldValue, newValue, confidence, evidence, changesTokenStructure = false) {
  if (JSON.stringify(oldValue) === JSON.stringify(newValue)) return;
  changes.push({
    frameId,
    field,
    old: oldValue,
    new: newValue,
    confidence,
    evidence,
    changesTokenStructure
  });
}

function cardField(frameId, index, key, newValue, confidence, evidence) {
  const frame = byId.get(frameId);
  add(frameId, `grammarCards[${index}].${key}`, frame.grammarCards[index][key], newValue, confidence, evidence, false);
}

function captionField(frameId, key, newValue, confidence, evidence) {
  const frame = byId.get(frameId);
  add(frameId, `caption.${key}`, frame.caption[key], newValue, confidence, evidence, false);
}

function ruby(cardIndex, base, reading, tokenStart, baseStart) {
  return {
    cardIndex,
    base,
    surfaceOffset: baseStart - tokenStart,
    reading,
    tokenStart,
    baseStart
  };
}

function furigana(frameId, entries, confidence = 0.99) {
  captionField(frameId, 'furigana', entries, confidence, rubyEvidence);
}

// QRC singing overrides dictionary-default readings.
const minamoEvidence = [
  ...qrcEvidence,
  'roma.json 对本句逐拍记录为「mi na mo」；因此「水面」按歌曲实际唱读标为「みなも / minamo」，不是词典默认的「すいめん」。',
  '小学馆《デジタル大辞泉》收录「みなも【水面】」：https://kotobank.jp/word/%E6%B0%B4%E9%9D%A2-639224'
];
cardField('l001', 0, 'reading', 'みなも', 1.0, minamoEvidence);
cardField('l001', 0, 'romaji', 'minamo', 1.0, minamoEvidence);
captionField('l001', 'romaji', 'minamo no hamon kara kao sorashita no wa', 1.0, minamoEvidence);
furigana('l001', [
  ruby(0, '水面', 'みなも', 0, 0),
  ruby(2, '波紋', 'はもん', 3, 3),
  ruby(4, '顔', 'かお', 8, 8),
  ruby(5, '逸', 'そ', 9, 9)
], 1.0);

const watashiEvidence = [
  ...qrcEvidence,
  'roma.json 对本句逐拍记录为「wa ta shi」；草稿的「わたくし / watakushi」与冻结唱读轨不符。',
  '小学馆《デジタル大辞泉》列出「私」常用读音「わたし」：https://kotobank.jp/word/%E7%A7%81-664668'
];
cardField('l002', 0, 'reading', 'わたし', 1.0, watashiEvidence);
cardField('l002', 0, 'romaji', 'watashi', 1.0, watashiEvidence);
captionField('l002', 'romaji', 'watashi no kokoro yuraida no kakushitakute', 1.0, watashiEvidence);
furigana('l002', [
  ruby(0, '私', 'わたし', 0, 0),
  ruby(2, '心', 'こころ', 2, 2),
  ruby(3, '揺', 'ゆ', 4, 4),
  ruby(5, '隠', 'かく', 9, 9)
], 1.0);

// Kanji-only furigana: do not repeat literal kana already present in the lyric.
furigana('l003', [
  ruby(2, '並', 'なら', 4, 4),
  ruby(5, '心臓', 'しんぞう', 11, 11)
]);

furigana('l007', [
  ruby(0, '袖', 'そで', 0, 0),
  ruby(1, '触', 'ふ', 1, 1),
  ruby(2, '満', 'み', 5, 5),
  ruby(3, '引', 'ひ', 7, 7),
  ruby(4, '目', 'め', 11, 11),
  ruby(6, '合', 'あ', 13, 13)
]);

furigana('l009', [
  ruby(0, '一口', 'ひとくち', 0, 0),
  ruby(1, '味', 'あじ', 2, 2),
  ruby(3, '名前', 'なまえ', 9, 9),
  ruby(5, '呼', 'よ', 12, 12)
]);

furigana('l010', [
  ruby(0, '喉', 'のど', 0, 0),
  ruby(1, '通', 'とお', 1, 1)
]);

furigana('l011', [
  ruby(0, '初', 'はじ', 0, 0),
  ruby(1, '知', 'し', 3, 3),
  ruby(2, '感情', 'かんじょう', 5, 5)
]);

furigana('l013', [
  ruby(0, '溶', 'と', 0, 0),
  ruby(0, '込', 'こ', 0, 2),
  ruby(1, '光', 'ひか', 6, 6)
]);

furigana('l014', [
  ruby(2, '透', 'す', 4, 4)
]);

furigana('l015', [
  ruby(0, '向', 'む', 0, 0),
  ruby(0, '側', 'がわ', 0, 3),
  ruby(1, '覗', 'のぞ', 4, 4)
]);

furigana('l017', [
  ruby(0, '世界', 'せかい', 0, 0),
  ruby(2, '変', 'か', 3, 3),
  ruby(4, '綺麗', 'きれい', 8, 8),
  ruby(7, '思', 'おも', 12, 12)
]);

furigana('l019', [
  ruby(0, '隣', 'とな', 0, 0),
  ruby(0, '合', 'あ', 0, 2),
  ruby(1, '影', 'かげ', 5, 5),
  ruby(3, '影', 'かげ', 7, 7),
  ruby(5, '期待', 'きたい', 12, 12)
]);

// 待ちあぐね is the continuative surface of the single dictionary verb 待ちあぐねる.
{
  const frame = byId.get('l020');
  const oldCards = frame.grammarCards;
  const merged = structuredClone(oldCards[1]);
  merged.token = '待ちあぐね';
  merged.reading = 'まちあぐね';
  merged.romaji = 'machiagune';
  merged.grammarStructureZh = '动词（活用）';
  merged.dictionaryForm = '待ちあぐねる';
  merged.status = 'assisted-proposal';
  merged.reviewRequired = true;
  merged.fieldProvenance = {
    ...merged.fieldProvenance,
    segmentation: 'lexical role proposal: dictionary verb 待ちあぐねる',
    reading: 'project/timing/roma.json + lexical review',
    romaji: 'lexical review'
  };
  const newCards = [oldCards[0], merged, ...oldCards.slice(3)];
  const evidence = [
    ...qrcEvidence,
    '小学馆《デジタル大辞泉》将「待ちあぐねる」收为一个动词词条；歌词「待ちあぐね」是其连用形：https://kotobank.jp/word/%E5%BE%85%E3%81%A1%E5%80%A6%E3%81%AD%E3%82%8B-634561',
    '将「待ち」与「あぐね」分成两个学习词卡会切断词典词形，并使罗马音产生不自然的词内空格。'
  ];
  add('l020', 'grammarCards', oldCards, newCards, 0.99, evidence, true);
  captionField('l020', 'romaji', 'uchikeshite machiagune te o totta', 0.99, evidence);
  furigana('l020', [
    ruby(0, '打', 'う', 0, 0),
    ruby(0, '消', 'け', 0, 2),
    ruby(1, '待', 'ま', 6, 6),
    ruby(2, '手', 'て', 12, 12),
    ruby(4, '取', 'と', 14, 14)
  ]);
}

furigana('l021', [
  ruby(0, '苦', 'にが', 0, 2),
  ruby(2, '甘', 'あま', 7, 7)
]);

furigana('l022', [
  ruby(3, '想', 'おも', 6, 6),
  ruby(5, '胸', 'むね', 9, 9),
  ruby(7, '満', 'み', 11, 11)
]);

furigana('l024', [
  ruby(0, '熱', 'ねつ', 0, 0),
  ruby(2, '持', 'も', 2, 2),
  ruby(5, '惑', 'まど', 9, 9)
]);

furigana('l026', [
  ruby(0, '飛', 'と', 0, 0),
  ruby(0, '越', 'こ', 0, 2)
]);

furigana('l028', [
  ruby(0, '思', 'おも', 0, 0),
  ruby(2, '遠', 'とお', 5, 5)
]);

furigana('l029', [
  ruby(2, '涙', 'なみだ', 4, 4),
  ruby(3, '理由', 'りゆう', 6, 6),
  ruby(5, '独', 'ひと', 10, 10),
  ruby(5, '占', 'じ', 10, 12)
]);

// Repeated lyric bundles must carry identical readings and ruby policy.
furigana('l030', [
  ruby(0, '喉', 'のど', 0, 0),
  ruby(1, '通', 'とお', 1, 1)
]);

furigana('l031', [
  ruby(0, '初', 'はじ', 0, 0),
  ruby(1, '知', 'し', 3, 3),
  ruby(2, '感情', 'かんじょう', 5, 5)
]);

furigana('l033', [
  ruby(0, '溶', 'と', 0, 0),
  ruby(0, '込', 'こ', 0, 2),
  ruby(1, '光', 'ひか', 6, 6)
]);

const proposal = {
  schemaVersion: 2,
  reviewRole: 'lexical',
  scope: {
    frameIds: doc.frames.map((frame) => frame.id)
  },
  baseFrameSha256: expectedHash,
  changes
};

if (proposal.scope.frameIds.length !== 33 || proposal.scope.frameIds[0] !== 'l001' || proposal.scope.frameIds[32] !== 'l033') {
  throw new Error('Expected complete l001-l033 scope.');
}

fs.mkdirSync(path.dirname(outputPath), { recursive: true });
fs.writeFileSync(outputPath, `${JSON.stringify(proposal, null, 2)}\n`, { encoding: 'utf8' });
console.log(JSON.stringify({ outputPath, changeCount: changes.length, scopeCount: proposal.scope.frameIds.length }, null, 2));
