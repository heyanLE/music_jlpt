import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';

const [runtime, source, output] = process.argv.slice(2);
if (!runtime || !source || !output) throw new Error('usage: node decode_qrc_file.mjs RUNTIME SOURCE OUTPUT');
const requireFromRuntime = createRequire(path.join(path.resolve(runtime), 'package.json'));
const lyric = requireFromRuntime('smart-lyric');
const decoded = lyric.qrc.decrypt(fs.readFileSync(source));
fs.mkdirSync(path.dirname(output), { recursive: true });
fs.writeFileSync(output, decoded, 'utf8');
console.log(JSON.stringify({ source, output, chars: decoded.length }));
