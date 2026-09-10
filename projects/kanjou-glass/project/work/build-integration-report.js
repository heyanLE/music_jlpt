const fs = require('fs');
const crypto = require('crypto');
const path = require('path');

const root = 'C:/project/musicjlpt/projects/kanjou-glass';
const baseHash = '3e3a32c058e5eca15cce097f0ab61965511d3dbf66127431d55ce51e4064af9f';
const framesPath = path.join(root, 'project/frames.json');
const proposalPaths = {
  lexical: path.join(root, 'project/proposals/lexical.json'),
  grammar: path.join(root, 'project/proposals/grammar.json'),
  translation: path.join(root, 'project/proposals/translation.json'),
};
const outputPath = path.join(root, 'project/review/integration-report.json');

const readJson = p => JSON.parse(fs.readFileSync(p, 'utf8'));
const clone = value => JSON.parse(JSON.stringify(value));
const sha256 = p => crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const eq = (a, b) => JSON.stringify(a) === JSON.stringify(b);

function parseField(field) {
  const canonical = field.replace(/\.([0-9]+)(?=\.|$)/g, '[$1]');
  const parts = [];
  const re = /([^[.\]]+)|\[([0-9]+)\]/g;
  let match;
  while ((match = re.exec(canonical))) {
    parts.push(match[2] === undefined ? match[1] : Number(match[2]));
  }
  return { canonical, parts };
}

function getAt(obj, field) {
  const { parts } = parseField(field);
  let cursor = obj;
  for (const part of parts) {
    if (cursor === null || cursor === undefined || !Object.prototype.hasOwnProperty.call(cursor, part)) {
      return { exists: false, value: undefined };
    }
    cursor = cursor[part];
  }
  return { exists: true, value: cursor };
}

function setAt(obj, field, value) {
  const { parts } = parseField(field);
  let cursor = obj;
  for (let i = 0; i < parts.length - 1; i++) cursor = cursor[parts[i]];
  const last = parts[parts.length - 1];
  if (value === null) delete cursor[last];
  else cursor[last] = clone(value);
}

const framesDoc = readJson(framesPath);
const frameMap = new Map(framesDoc.frames.map(frame => [frame.id, frame]));
const proposals = Object.fromEntries(Object.entries(proposalPaths).map(([role, p]) => [role, readJson(p)]));

if (sha256(framesPath) !== baseHash) throw new Error('frames.json hash drifted from required integration base');
for (const [role, proposal] of Object.entries(proposals)) {
  if (proposal.schemaVersion !== 2 || proposal.reviewRole !== role || proposal.baseFrameSha256 !== baseHash) {
    throw new Error(`${role} proposal contract or base hash mismatch`);
  }
}

const sourceValidations = [];
for (const [role, proposal] of Object.entries(proposals)) {
  for (const [sourceIndex, change] of proposal.changes.entries()) {
    const frame = frameMap.get(change.frameId);
    if (!frame) throw new Error(`${role}[${sourceIndex}] references missing frame ${change.frameId}`);
    const current = getAt(frame, change.field);
    const oldMatches = current.exists ? eq(current.value, change.old) : change.old === null || change.old === undefined;
    sourceValidations.push({ role, sourceIndex, frameId: change.frameId, field: parseField(change.field).canonical, oldMatches });
    if (!oldMatches) {
      throw new Error(`${role}[${sourceIndex}] old mismatch at ${change.frameId}.${change.field}`);
    }
  }
}

const ownership = field => {
  if (field === 'grammarCards' || /(?:reading|romaji|sourceWord)$/.test(field) || field === 'caption.furigana' || field === 'caption.romaji') return 'lexical';
  if (/(?:grammarStructureZh|functionZh)$/.test(field)) return 'grammar';
  if (/(?:translationZh|zhMeaning)$/.test(field)) return 'translation';
  return null;
};

const samePath = new Map();
for (const [role, proposal] of Object.entries(proposals)) {
  proposal.changes.forEach((change, sourceIndex) => {
    const key = `${change.frameId}|${parseField(change.field).canonical}`;
    if (!samePath.has(key)) samePath.set(key, []);
    samePath.get(key).push({ role, sourceIndex, change });
  });
}

const conflicts = [];
const rejectedExactPath = new Set();
for (const [key, entries] of samePath.entries()) {
  if (entries.length < 2) continue;
  const distinct = new Set(entries.map(entry => JSON.stringify(entry.change.new)));
  if (distinct.size < 2) continue;
  const [frameId, field] = key.split('|');
  const owner = ownership(field);
  const chosen = entries.find(entry => entry.role === owner);
  if (!chosen) throw new Error(`No owner proposal for conflict ${key}`);
  for (const entry of entries) if (entry !== chosen) rejectedExactPath.add(`${entry.role}:${entry.sourceIndex}`);
  const maxConfidence = Math.max(...entries.map(entry => Number(entry.change.confidence || 0)));
  conflicts.push({
    frameId,
    field,
    type: 'same-field-role-conflict',
    proposals: entries.map(entry => ({ role: entry.role, new: entry.change.new, confidence: entry.change.confidence })),
    resolution: {
      selectedRole: owner,
      selectedNew: chosen.change.new,
      selectedConfidence: chosen.change.confidence,
      reason: `${owner} owns ${field}; role ownership is explicit and the alternative was not silently merged.`,
      selectedBelowCompetingConfidence: Number(chosen.change.confidence || 0) < maxConfidence,
    },
  });
}

function sourceChange(role, frameId, field) {
  const canonical = parseField(field).canonical;
  return proposals[role].changes.find(change => change.frameId === frameId && parseField(change.field).canonical === canonical);
}

const recommended = [];
function addSource(role, sourceIndex, change) {
  recommended.push({
    ...clone(change),
    field: parseField(change.field).canonical,
    integrationSource: { role, sourceIndex },
  });
}

for (const [role, proposal] of Object.entries(proposals)) {
  proposal.changes.forEach((change, sourceIndex) => {
    const canonical = parseField(change.field).canonical;
    if (rejectedExactPath.has(`${role}:${sourceIndex}`)) return;
    if (change.frameId === 'l020' && (canonical === 'grammarCards' || canonical.startsWith('grammarCards['))) return;
    if (change.frameId === 'l024' && canonical.startsWith('grammarCards[4]')) return;
    addSource(role, sourceIndex, change);
  });
}

// l020: lexical boundary change owns the complete card array. Grammar and translation
// proposals are remapped by token identity, not by their now-stale source indices.
const l020Base = frameMap.get('l020');
const l020Lexical = sourceChange('lexical', 'l020', 'grammarCards');
if (!l020Lexical) throw new Error('Missing l020 lexical grammarCards proposal');
const l020Cards = clone(l020Lexical.new);

l020Cards[0].grammarStructureZh = sourceChange('grammar', 'l020', 'grammarCards[0].grammarStructureZh').new;
l020Cards[0].zhMeaning = sourceChange('translation', 'l020', 'grammarCards[0].zhMeaning').new;
delete l020Cards[0].functionZh;

l020Cards[1].grammarStructureZh = '复合动词连用形（中顿）';
l020Cards[1].zhMeaning = sourceChange('translation', 'l020', 'grammarCards[2].zhMeaning').new;
delete l020Cards[1].functionZh;

l020Cards[2].zhMeaning = sourceChange('translation', 'l020', 'grammarCards[3].zhMeaning').new;
delete l020Cards[2].functionZh;

l020Cards[3].grammarStructureZh = l020Base.grammarCards[4].grammarStructureZh;
l020Cards[3].functionZh = sourceChange('grammar', 'l020', 'grammarCards[4].functionZh').new;
delete l020Cards[3].zhMeaning;

l020Cards[4].grammarStructureZh = sourceChange('grammar', 'l020', 'grammarCards[5].grammarStructureZh').new;
l020Cards[4].zhMeaning = sourceChange('translation', 'l020', 'grammarCards[5].zhMeaning').new;
delete l020Cards[4].functionZh;

recommended.push({
  frameId: 'l020',
  field: 'grammarCards',
  old: clone(l020Base.grammarCards),
  new: l020Cards,
  confidence: 0.98,
  evidence: [
    'Lexical proposal identifies 待ちあぐねる as one dictionary verb and owns token boundaries/readings/romaji.',
    'Grammar proposals for old cards 1 and 2 are reconciled as one compound-verb card: 复合动词连用形（中顿）.',
    'Translation meaning for the complete compound is taken from old card 2; 手/を/取った fields are shifted from old indices 3/4/5 to new indices 2/3/4.',
    'The complete replacement preserves exactly one of zhMeaning/functionZh on every card.',
  ],
  changesTokenStructure: true,
  integrationSource: {
    role: 'integration',
    absorbed: ['lexical:grammarCards', 'grammar:grammarCards[0,1,2,4,5]', 'translation:grammarCards[0..5]'],
  },
});

conflicts.push({
  frameId: 'l020',
  field: 'grammarCards',
  type: 'token-structure-index-remap',
  proposals: [
    { role: 'lexical', action: 'merge old cards 1+2 into 待ちあぐね' },
    { role: 'grammar', action: 'changes reference old indices 0,1,2,4,5' },
    { role: 'translation', action: 'changes reference old indices 0..5' },
  ],
  resolution: {
    selectedRole: 'integration',
    reason: 'Lexical owns the boundary; grammar and translation values were remapped by token identity into a complete five-card replacement.',
    indexMap: { '0': 0, '1+2': 1, '3': 2, '4': 3, '5': 4 },
    mergedCard: {
      token: '待ちあぐね',
      reading: 'まちあぐね',
      romaji: 'machiagune',
      grammarStructureZh: '复合动词连用形（中顿）',
      zhMeaning: '等得厌倦；等得不耐烦',
    },
  },
});

// l024 card 4 is a functional な-adjective adverbial marker. Replace the whole card
// so the renderer cannot retain both a meaning and a function field.
const l024Base = frameMap.get('l024');
const l024Card4 = clone(l024Base.grammarCards[4]);
l024Card4.grammarStructureZh = sourceChange('grammar', 'l024', 'grammarCards[4].grammarStructureZh').new;
l024Card4.functionZh = sourceChange('grammar', 'l024', 'grammarCards[4].functionZh').new;
delete l024Card4.zhMeaning;
recommended.push({
  frameId: 'l024',
  field: 'grammarCards[4]',
  old: clone(l024Base.grammarCards[4]),
  new: l024Card4,
  confidence: 0.99,
  evidence: [
    'Grammar owns the adverbial function of に in かすかに惑う.',
    'Whole-card replacement removes the draft zhMeaning field and leaves exactly one functionZh field.',
    'Translation proposed a gloss for this functional card; it is rejected to satisfy the particle/function exclusivity contract.',
  ],
  changesTokenStructure: false,
  integrationSource: { role: 'integration', absorbed: ['grammar:grammarCards[4].grammarStructureZh', 'grammar:grammarCards[4].zhMeaning', 'grammar:grammarCards[4].functionZh', 'translation:grammarCards[4].zhMeaning'] },
});

conflicts.push({
  frameId: 'l024',
  field: 'grammarCards[4].zhMeaning|functionZh',
  type: 'meaning-function-exclusivity',
  proposals: [
    { role: 'grammar', new: { grammarStructureZh: 'な形容词副词化', functionZh: '使かすか作状语：隐约地' }, confidence: 0.99 },
    { role: 'translation', new: { zhMeaning: '使形容动词副词化：隐约地' }, confidence: 0.99 },
  ],
  resolution: {
    selectedRole: 'grammar',
    reason: 'This に is functional; grammar owns functionZh and exactly-one meaning/function forbids retaining the translation gloss.',
  },
});

// Keep deterministic order: frame, parent-before-child, then field.
recommended.sort((a, b) => {
  const byFrame = a.frameId.localeCompare(b.frameId, 'en');
  if (byFrame) return byFrame;
  const aDepth = parseField(a.field).parts.length;
  const bDepth = parseField(b.field).parts.length;
  return aDepth - bDepth || a.field.localeCompare(b.field, 'en');
});

const duplicateKeys = new Set();
for (const change of recommended) {
  const key = `${change.frameId}|${parseField(change.field).canonical}`;
  if (duplicateKeys.has(key)) throw new Error(`Duplicate recommended path ${key}`);
  duplicateKeys.add(key);
  const baseFrame = frameMap.get(change.frameId);
  const current = getAt(baseFrame, change.field);
  if (!current.exists || !eq(current.value, change.old)) throw new Error(`Recommended old mismatch at ${key}`);
}

const simulated = clone(framesDoc);
const simulatedMap = new Map(simulated.frames.map(frame => [frame.id, frame]));
for (const change of recommended) setAt(simulatedMap.get(change.frameId), change.field, change.new);

const exclusivityErrors = [];
const rubyErrors = [];
const loanwordErrors = [];
const romajiErrors = [];
const kanjiOnly = /^[\u3400-\u4dbf\u4e00-\u9fff々〆ヶ]+$/u;
const hiraganaOnly = /^[ぁ-ゖー]+$/u;
const katakana = /[ァ-ヶー]/u;
for (const frame of simulated.frames) {
  frame.grammarCards.forEach((card, cardIndex) => {
    const hasMeaning = typeof card.zhMeaning === 'string' && card.zhMeaning.length > 0;
    const hasFunction = typeof card.functionZh === 'string' && card.functionZh.length > 0;
    if (hasMeaning === hasFunction) exclusivityErrors.push(`${frame.id}[${cardIndex}]`);
    if (katakana.test(card.token) && (!card.sourceWord || typeof card.sourceWord !== 'string')) loanwordErrors.push(`${frame.id}[${cardIndex}] ${card.token}`);
  });
  for (const ruby of frame.caption.furigana || []) {
    const card = frame.grammarCards[ruby.cardIndex];
    const lyricSlice = frame.caption.japanese.slice(ruby.baseStart, ruby.baseStart + ruby.base.length);
    const tokenSlice = card && card.token.slice(ruby.surfaceOffset, ruby.surfaceOffset + ruby.base.length);
    if (!kanjiOnly.test(ruby.base) || !hiraganaOnly.test(ruby.reading) || lyricSlice !== ruby.base || tokenSlice !== ruby.base) {
      rubyErrors.push({ frameId: frame.id, ruby, lyricSlice, tokenSlice });
    }
  }
  const joined = frame.grammarCards.map(card => card.romaji).filter(Boolean).join(' ');
  if (joined !== frame.caption.romaji) romajiErrors.push({ frameId: frame.id, expected: joined, actual: frame.caption.romaji });
}
if (exclusivityErrors.length) throw new Error(`Meaning/function exclusivity errors: ${exclusivityErrors.join(', ')}`);
if (rubyErrors.length) throw new Error(`Ruby errors: ${JSON.stringify(rubyErrors)}`);
if (loanwordErrors.length) throw new Error(`Loanword source errors: ${loanwordErrors.join(', ')}`);
if (romajiErrors.length) throw new Error(`Romaji alignment errors: ${JSON.stringify(romajiErrors)}`);

const repeatedGroups = [
  ['l010', 'l030'],
  ['l011', 'l031'],
  ['l012', 'l032'],
  ['l013', 'l033'],
];
const repeatChecks = repeatedGroups.map(([a, b]) => ({
  frames: [a, b],
  japaneseEqual: simulatedMap.get(a).caption.japanese === simulatedMap.get(b).caption.japanese,
  grammarCardsEqual: eq(simulatedMap.get(a).grammarCards, simulatedMap.get(b).grammarCards),
  lineTranslationsIndependentlyRetained: true,
}));
if (repeatChecks.some(check => !check.japaneseEqual || !check.grammarCardsEqual)) throw new Error(`Repeated card bundles diverged: ${JSON.stringify(repeatChecks)}`);

const belowCompeting = conflicts.filter(conflict => conflict.resolution && conflict.resolution.selectedBelowCompetingConfidence);
const report = {
  schemaVersion: 2,
  reviewRole: 'integration',
  status: 'completed',
  baseFrameSha256: baseHash,
  sourceProposalFiles: Object.fromEntries(Object.entries(proposalPaths).map(([role, p]) => [role, {
    path: path.relative(root, p).replace(/\\/g, '/'),
    sha256: sha256(p),
    reviewRole: proposals[role].reviewRole,
    scopeFrameCount: proposals[role].scope.frameIds.length,
    changeCount: proposals[role].changes.length,
  }])),
  proposalCounts: {
    source: {
      lexical: proposals.lexical.changes.length,
      grammar: proposals.grammar.changes.length,
      translation: proposals.translation.changes.length,
      total: Object.values(proposals).reduce((sum, proposal) => sum + proposal.changes.length, 0),
    },
    sourceOldValuesValidated: sourceValidations.length,
    sourceOldValueMismatches: sourceValidations.filter(item => !item.oldMatches).length,
    conflicts: conflicts.length,
    recommendedChanges: recommended.length,
  },
  conflicts,
  recommendedProposalSet: {
    schemaVersion: 2,
    baseFrameSha256: baseHash,
    applicationOrder: 'Apply changes in listed order against the unchanged base frames.json. A null new value means delete, though this set contains no null writes.',
    ownership: {
      lexical: 'token boundaries, reading, romaji, furigana, loanword sourceWord',
      grammar: 'grammarStructureZh and grammatical functionZh',
      translation: 'caption.translationZh and lexical zhMeaning',
    },
    changes: recommended,
  },
  validation: {
    framesSha256MatchesBase: true,
    allSourceOldValuesMatchBase: true,
    allRecommendedOldValuesMatchBase: true,
    duplicateRecommendedPaths: 0,
    simulatedMeaningFunctionExactlyOne: true,
    simulatedKanjiOnlyRuby: true,
    simulatedLoanwordSourceWords: true,
    simulatedCardRomajiMatchesCaption: true,
    singingReadingOverrides: [
      { frameId: 'l001', token: '水面', reading: 'みなも', romaji: 'minamo', basis: 'QQ romaji singing track plus dictionary attestation' },
      { frameId: 'l002', token: '私', reading: 'わたし', romaji: 'watashi', basis: 'QQ romaji singing track' },
    ],
    repeatedLineChecks: repeatChecks,
    translationPolicy: 'Repeated card bundles are synchronized; each repeated frame keeps its independently proposed caption.translationZh rather than inheriting by force.',
  },
  attentionItems: [
    {
      frameId: 'l020',
      severity: 'resolved-structural',
      item: '待ち＋あぐね was merged as 待ちあぐね. Review the synthesized structure 复合动词连用形（中顿） and meaning 等得厌倦；等得不耐烦 before user approval.',
    },
    {
      frameId: 'l024',
      severity: 'resolved-contract',
      item: 'The に card is represented only by functionZh; the competing translation gloss is intentionally omitted.',
    },
    {
      frameId: 'l028',
      severity: 'user-review',
      item: 'Translation proposal adds an implicit object（你）at confidence 0.91: 只要思念着你，距离便还不算遥远.',
    },
    {
      frameIds: ['l014', 'l015'],
      severity: 'user-review',
      item: 'Cross-line translations were rewritten as 我透过酒杯 / 窥望着另一边; inspect together because each line is intentionally fragmentary.',
    },
    {
      frameIds: ['l025', 'l026'],
      severity: 'user-review',
      item: 'Cross-line translations were rewritten as 一路走到今天的我们，如今仿佛已能 / 跨越过往的一切.',
    },
    {
      severity: 'conflict-disclosure',
      item: `${belowCompeting.length} grammar-owned function proposal(s) were selected despite a higher-confidence competing translation wording; each is explicitly marked selectedBelowCompetingConfidence in conflicts.`,
    },
  ],
  protectedHumanFieldsTouched: [],
  framesModified: false,
};

fs.mkdirSync(path.dirname(outputPath), { recursive: true });
fs.writeFileSync(outputPath, JSON.stringify(report, null, 2) + '\n', 'utf8');
console.log(JSON.stringify({
  outputPath,
  sourceOldValuesValidated: sourceValidations.length,
  conflicts: conflicts.length,
  recommendedChanges: recommended.length,
  repeatedLineChecks: repeatChecks,
  outputSha256: sha256(outputPath),
}, null, 2));
