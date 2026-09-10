import fs from 'node:fs';
import path from 'node:path';
import lyric from './tmp-qrc/node_modules/smart-lyric/dist/index.js';
const {qrc}=lyric;
const [source, stem]=process.argv.slice(2);
if(!source||!stem) throw new Error('usage: node decode_qrc_file.mjs <source> <stem>');
const raw=qrc.decrypt(fs.readFileSync(source));
const out='C:/project/musicjlpt/output';
fs.writeFileSync(path.join(out,`${stem}.xml`),raw,'utf8');
let parsed=null, parseError=null;
try { parsed=qrc.parse(raw); fs.writeFileSync(path.join(out,`${stem}.parsed.json`),JSON.stringify(parsed,null,2),'utf8'); }
catch (error) { parseError=String(error.message); }
console.log(JSON.stringify({stem,rawChars:raw.length,preview:raw.slice(0,600),parsedType:typeof parsed,parseError},null,2));
