const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const projectRoot = path.resolve(__dirname, '..', '..');
const framesPath = path.join(projectRoot, 'project', 'frames.json');
const outputPath = path.join(projectRoot, 'project', 'proposals', 'lexical.json');
const expectedHash = 'a1e1a1247da27e4509dd9978abb2915128c7bd48bd42cef162ae539e50479499';

const raw = fs.readFileSync(framesPath);
const actualHash = crypto.createHash('sha256').update(raw).digest('hex');
if (actualHash !== expectedHash) {
  throw new Error(`frames.json changed: expected ${expectedHash}, got ${actualHash}`);
}

const doc = JSON.parse(raw.toString('utf8'));
const byId = new Map(doc.frames.map((frame) => [frame.id, frame]));
const changes = [];

const romajiEvidence = [
  'project/timing/qm.json 与 project/timing/roma.json：逐行核对冻结歌词、唱读和字符时值；本提案不改歌词字面或时间。',
  '文化庁《ローマ字のつづり方》（令和7年12月22日内閣告示第4号）及官方问答：助词「は」「へ」「を」分别写作「wa」「e」「o」。https://www.bunka.go.jp/kokugo_nihongo/sisaku/joho/joho/kijun/naikaku/roma/index2.html',
  '学习型罗马音应表示句中实际助词读音；助词的 reading 字段仍保留日文正字法「は／へ／を」。'
];

const rubyEvidence = [
  'project/templates/foreground.json：annotation.kanjiOnly=true，振假名须只覆盖连续汉字段，不重复歌词中已有的平假名。',
  'project/timing/qm.json 与 project/timing/roma.json：逐字对应确认混合表记中的唱读，例如「飛び立つ」= と・び・た・つ。',
  '原草稿把被假名隔开的汉字拼成一个 base（如「飛立」），该 base 不是 token 的连续子串，无法按 surfaceOffset 正确锚定。'
];

function same(a, b) {
  return JSON.stringify(a) === JSON.stringify(b);
}

function add(frameId, field, oldValue, newValue, confidence, evidence, changesTokenStructure = false) {
  if (same(oldValue, newValue)) return;
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

function setCardRomaji(frameId, cardIndex, expectedToken, newRomaji) {
  const frame = byId.get(frameId);
  if (!frame) throw new Error(`Unknown frame ${frameId}`);
  const card = frame.grammarCards[cardIndex];
  if (!card || card.token !== expectedToken) {
    throw new Error(`${frameId} grammarCards[${cardIndex}] expected ${expectedToken}, got ${card && card.token}`);
  }
  add(frameId, `grammarCards[${cardIndex}].romaji`, card.romaji, newRomaji, 1.0, romajiEvidence, false);
}

function ruby(base, cardIndex, surfaceOffset, reading) {
  return { base, cardIndex, surfaceOffset, reading };
}

const particleCardChanges = [
  ['l002', 2, 'を', 'o'],
  ['l004', 4, 'を', 'o'],
  ['l005', 3, 'を', 'o'],
  ['l006', 5, 'を', 'o'],
  ['l007', 2, 'を', 'o'],
  ['l009', 4, 'を', 'o'],
  ['l012', 3, 'を', 'o'],
  ['l013', 2, 'は', 'wa'],
  ['l014', 3, 'を', 'o'],
  ['l015', 4, 'へ', 'e'],
  ['l016', 2, 'は', 'wa'],
  ['l017', 2, 'を', 'o'],
  ['l018', 0, '祝福をしよう', 'shukufukuoshiyou'],
  ['l018', 3, 'を', 'o'],
  ['l019', 2, 'を', 'o'],
  ['l020', 2, 'を', 'o'],
  ['l021', 2, 'は', 'wa'],
  ['l022', 2, 'は', 'wa'],
  ['l028', 3, 'へ', 'e'],
  ['l030', 3, 'を', 'o'],
  ['l031', 2, 'は', 'wa'],
  ['l032', 3, 'を', 'o'],
  ['l034', 3, 'を', 'o'],
  ['l035', 2, 'は', 'wa'],
  ['l036', 3, 'を', 'o'],
  ['l037', 4, 'へ', 'e'],
  ['l038', 2, 'は', 'wa'],
  ['l039', 2, 'を', 'o'],
  ['l040', 0, '祝福をしよう', 'shukufukuoshiyou'],
  ['l040', 3, 'を', 'o'],
  ['l042', 2, 'を', 'o'],
  ['l044', 4, 'を', 'o']
];

for (const args of particleCardChanges) setCardRomaji(...args);

const cardRomajiOverrides = new Map(
  particleCardChanges.map(([frameId, cardIndex, , newRomaji]) => [`${frameId}:${cardIndex}`, newRomaji])
);

for (const frame of doc.frames) {
  const proposed = frame.grammarCards
    .map((card, cardIndex) => cardRomajiOverrides.get(`${frame.id}:${cardIndex}`) || card.romaji)
    .filter(Boolean)
    .join(' ');
  add(frame.id, 'caption.romaji', frame.caption.romaji, proposed, 1.0, romajiEvidence, false);
}

const rubyCorrections = {
  l011: [
    ruby('飛', 0, 0, 'と'),
    ruby('立', 0, 2, 'た'),
    ruby('空', 1, 0, 'そら'),
    ruby('祈', 3, 0, 'いの'),
    ruby('撃', 4, 0, 'う'),
    ruby('放', 4, 2, 'はな')
  ],
  l017: [
    ruby('守', 0, 0, 'まも'),
    ruby('引', 1, 0, 'ひ'),
    ruby('金', 1, 2, 'がね'),
    ruby('引', 3, 0, 'ひ')
  ],
  l023: [
    ruby('光', 0, 0, 'ひかり'),
    ruby('願', 2, 0, 'ねが'),
    ruby('暗闇', 4, 0, 'くらやみ'),
    ruby('撃', 5, 0, 'う'),
    ruby('抜', 5, 2, 'ぬ')
  ],
  l029: [
    ruby('飛', 0, 0, 'と'),
    ruby('立', 0, 2, 'た'),
    ruby('空', 1, 0, 'そら'),
    ruby('祈', 3, 0, 'いの'),
    ruby('撃', 4, 0, 'う'),
    ruby('放', 4, 2, 'はな')
  ],
  l033: [
    ruby('飛', 0, 0, 'と'),
    ruby('立', 0, 2, 'た'),
    ruby('空', 1, 0, 'そら'),
    ruby('祈', 3, 0, 'いの'),
    ruby('撃', 4, 0, 'う'),
    ruby('放', 4, 2, 'はな')
  ],
  l039: [
    ruby('守', 0, 0, 'まも'),
    ruby('引', 1, 0, 'ひ'),
    ruby('金', 1, 2, 'がね'),
    ruby('引', 3, 0, 'ひ')
  ]
};

for (const [frameId, newRuby] of Object.entries(rubyCorrections)) {
  const frame = byId.get(frameId);
  add(frameId, 'caption.furigana', frame.caption.furigana, newRuby, 1.0, rubyEvidence, false);
}

const proposal = {
  schemaVersion: 2,
  reviewRole: 'lexical',
  scope: { frameIds: doc.frames.map((frame) => frame.id) },
  baseFrameSha256: expectedHash,
  changes
};

const expectedIds = Array.from({ length: 44 }, (_, index) => `l${String(index + 1).padStart(3, '0')}`);
if (!same(proposal.scope.frameIds, expectedIds)) {
  throw new Error(`Scope is not complete l001-l044: ${JSON.stringify(proposal.scope.frameIds)}`);
}

// Simulate only this role's proposals and validate its lexical invariants.
const simulated = structuredClone(doc);
const simulatedById = new Map(simulated.frames.map((frame) => [frame.id, frame]));
for (const change of changes) {
  const frame = simulatedById.get(change.frameId);
  if (change.field === 'caption.romaji') frame.caption.romaji = change.new;
  else if (change.field === 'caption.furigana') frame.caption.furigana = change.new;
  else {
    const match = /^grammarCards\[(\d+)\]\.romaji$/.exec(change.field);
    if (!match) throw new Error(`Unexpected field path ${change.field}`);
    frame.grammarCards[Number(match[1])].romaji = change.new;
  }
}

const kanjiOnly = /^[\u3400-\u4dbf\u4e00-\u9fff々〆ヶ]+$/u;
const hiraganaOnly = /^[ぁ-ゖー]+$/u;
const katakana = /[ァ-ヶー]/u;
for (const frame of simulated.frames) {
  const joinedRomaji = frame.grammarCards.map((card) => card.romaji).filter(Boolean).join(' ');
  if (joinedRomaji !== frame.caption.romaji) {
    throw new Error(`${frame.id}: caption/card romaji mismatch: ${joinedRomaji} != ${frame.caption.romaji}`);
  }
  for (const annotation of frame.caption.furigana || []) {
    const card = frame.grammarCards[annotation.cardIndex];
    const cardSlice = card && card.token.slice(annotation.surfaceOffset, annotation.surfaceOffset + annotation.base.length);
    if (!card || cardSlice !== annotation.base || !kanjiOnly.test(annotation.base) || !hiraganaOnly.test(annotation.reading)) {
      throw new Error(`${frame.id}: invalid kanji-only ruby ${JSON.stringify({ annotation, cardSlice })}`);
    }
  }
  for (const [cardIndex, card] of frame.grammarCards.entries()) {
    if (katakana.test(card.token) && (typeof card.sourceWord !== 'string' || card.sourceWord.trim() === '')) {
      throw new Error(`${frame.id}[${cardIndex}]: katakana card lacks sourceWord`);
    }
  }
  if ((frame.displayUnits || []).some((unit) => unit.kind === 'english')) {
    if ((frame.caption.furigana || []).length || frame.caption.romaji || frame.grammarCards.length) {
      throw new Error(`${frame.id}: English exclusion rule violated`);
    }
  }
}

const groups = new Map();
for (const frame of simulated.frames) {
  const key = frame.caption.japanese;
  if (!groups.has(key)) groups.set(key, []);
  groups.get(key).push(frame);
}
for (const repeated of groups.values()) {
  if (repeated.length < 2) continue;
  const reference = repeated[0];
  for (const frame of repeated.slice(1)) {
    if (!same(reference.grammarCards, frame.grammarCards) || !same(reference.caption.furigana, frame.caption.furigana) || reference.caption.romaji !== frame.caption.romaji) {
      throw new Error(`Repeated-line lexical inconsistency: ${reference.id} vs ${frame.id}`);
    }
  }
}

if (changes.some((change) => change.changesTokenStructure !== false)) {
  throw new Error('This lexical pass does not propose token-structure changes.');
}

fs.mkdirSync(path.dirname(outputPath), { recursive: true });
fs.writeFileSync(outputPath, `${JSON.stringify(proposal, null, 2)}\n`, 'utf8');
console.log(JSON.stringify({ outputPath, scopeCount: proposal.scope.frameIds.length, changeCount: changes.length }, null, 2));
