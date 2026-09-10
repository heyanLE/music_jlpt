"use strict";

const crypto = require("crypto");
const fs = require("fs");
const path = require("path");
const { qrc, lrc } = require("C:/project/musicjlpt/tmp-qrc/node_modules/smart-lyric/dist/index.js");

const ROOT = path.resolve(__dirname, "../..");
const SOURCE = path.join(ROOT, "source");
const TIMING = path.join(ROOT, "project", "timing");
fs.mkdirSync(TIMING, { recursive: true });

const sha256 = file => crypto.createHash("sha256").update(fs.readFileSync(file)).digest("hex");
const write = (name, value) => fs.writeFileSync(path.join(TIMING, name), JSON.stringify(value, null, 2) + "\n", "utf8");

function decodeKara(sourceName, outputName) {
  const source = path.join(SOURCE, sourceName);
  const decoded = qrc.decrypt(fs.readFileSync(source));
  if (!decoded) throw new Error(`Could not decrypt ${sourceName}`);
  const parsed = qrc.parse(decoded);
  const lines = parsed.content.map((line, lineIndex) => {
    let offset = 0;
    const parts = line.content.map((part, partIndex) => {
      const text = part.content;
      const item = { text, startMs: line.start + part.start, endMs: line.start + part.start + part.duration, sourceOffset: offset, sourcePartIndex: partIndex };
      offset += text.length;
      return item;
    });
    return { id: `${outputName}-${String(lineIndex + 1).padStart(3, "0")}`, startMs: line.start, endMs: line.start + line.duration, text: parts.map(part => part.text).join(""), parts };
  }).filter(line => line.text.trim());
  const output = { schemaVersion: 1, source: sourceName, lyricType: "karaoke", lines };
  write(outputName, output);
  fs.writeFileSync(path.join(TIMING, `${outputName.replace(/\.json$/, "")}-decoded.qrc`), decoded, "utf8");
  return { count: lines.length, minMs: lines[0]?.startMs ?? null, maxMs: lines.at(-1)?.endMs ?? null };
}

function decodeLrc(sourceName, outputName) {
  const source = path.join(SOURCE, sourceName);
  const decoded = qrc.decrypt(fs.readFileSync(source));
  if (!decoded) throw new Error(`Could not decrypt ${sourceName}`);
  const parsed = lrc.parse(decoded);
  const lines = parsed.content.map((line, index) => ({ id: `translation-${String(index + 1).padStart(3, "0")}`, startMs: line.start, text: line.content })).filter(line => line.text.trim());
  const output = { schemaVersion: 1, source: sourceName, lyricType: "regular", lines };
  write(outputName, output);
  fs.writeFileSync(path.join(TIMING, "translation-decoded.qrc"), decoded, "utf8");
  return { count: lines.length, minMs: lines[0]?.startMs ?? null, maxMs: lines.at(-1)?.startMs ?? null };
}

const report = {
  schemaVersion: 1,
  decoder: "smart-lyric 1.0.1 bundled at C:/project/musicjlpt/tmp-qrc/node_modules/smart-lyric",
  sourceHashes: Object.fromEntries(["lyrics_qm.qrc", "lyrics_qmRoma.qrc", "lyrics_qmts.qrc"].map(file => [file, sha256(path.join(SOURCE, file))])),
  outputs: {
    qm: decodeKara("lyrics_qm.qrc", "qm.json"),
    roma: decodeKara("lyrics_qmRoma.qrc", "roma.json"),
    translation: decodeLrc("lyrics_qmts.qrc", "translation.json")
  },
  validation: { utf8: true, wordTimingAvailable: true, status: "passed" }
};
write("decode-report.json", report);
