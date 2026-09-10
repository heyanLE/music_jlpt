"""Apply only the user-authorized smart-audit-v1 proposal bundle."""
from __future__ import annotations

import hashlib, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "work" / "draft-deps"))
from janome.tokenizer import Tokenizer
from pykakasi import kakasi

ROOT = Path(__file__).resolve().parents[2]; PROJECT = ROOT / "project"
TOK, KAKASI = Tokenizer(), kakasi()
SOURCE_WORDS = {"リンク":"link"}
READING_ROMAJI = {"舞って": ("まって", "matte"), "舞う": ("まう", "mau")}

def read(path): return json.loads(path.read_text(encoding="utf-8"))
def write(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    json.loads(path.read_text(encoding="utf-8"))
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def reading(text):
    raw = "".join(t.reading if t.reading != "*" else t.surface for t in TOK.tokenize(text))
    return "".join(chr(ord(c)-0x60) if "ァ" <= c <= "ヶ" else c for c in raw)
def romaji(text): return " ".join(x["hepburn"] for x in KAKASI.convert(text))
def card(token, meaning=None, function=None, pos="短语"):
    rd, rm = READING_ROMAJI.get(token, (reading(token), romaji(token)))
    value={"token":token,"reading":rd,"romaji":rm,"posZh":pos,"status":"user-authorized-proposal","fieldProvenance":"smart-audit-v1; explicitly accepted by user"}
    if function is not None: value["functionZh"] = function
    else: value["zhMeaning"] = meaning
    if token in SOURCE_WORDS: value["sourceWord"] = SOURCE_WORDS[token]
    return value

def set_card(frame, index, fields):
    value = frame["grammarCards"][index]
    if "functionZh" in fields: value.pop("zhMeaning", None)
    if "zhMeaning" in fields: value.pop("functionZh", None)
    value.update(fields)
    value["status"]="user-authorized-proposal"
    value["fieldProvenance"]="smart-audit-v1; explicitly accepted by user"

def main():
    target=PROJECT/"frames.json"; before=sha(target); data=read(target); byid={f["id"]:f for f in data["frames"]}; applied=[]
    set_card(byid["l002"],0,{"zhMeaning":"即使（有人）煞有介事地说着","posZh":"动词已然形＋逆接接续助词"}); applied.append("p-l002-notamaedo")
    byid["l005"]["caption"]["translationZh"]="未经验证的哲学。"; applied.append("p-l005-translation")
    set_card(byid["l008"],3,{"functionZh":"举例、列举；“……之类”","posZh":"并列助词"}); applied.append("p-l008-toka")
    byid["l014"]["caption"]["translationZh"]="完全不知道，也根本不需要。"; applied.append("p-l014-translation")
    byid["l016"]["grammarCards"]=[card("ただ","只是；只管",pos="副词"),card("舞って","跳着舞",pos="动词て形"),card("舞う","起舞；跳舞",pos="动词")]; applied.append("p-l016-split-dance")
    byid["l018"]["caption"]["translationZh"]="把所有灯光都熄掉。"; applied.append("p-l018-translation")
    set_card(byid["l019"],3,{"zhMeaning":"连接；联结","posZh":"サ变名词","sourceWord":"link"}); applied.append("p-l019-link")
    byid["l022"]["caption"]["translationZh"]="在声音之中渐渐消融的"; byid["l023"]["caption"]["translationZh"]="是我的真实感。"; applied.append("p-l022-l023-crossline")
    set_card(byid["l025"],0,{"zhMeaning":"已凋零、散落的","posZh":"动词连用形＋完了助动词"}); applied.append("p-l025-chirinuru")
    changes={"l026":"在五脏六腑中回响不止的","l027":"是脉动的旋律线；","l028":"流星在我的体内奔流，","l029":"不断跃动。","l030":"与呼吸声逐渐重合的","l031":"节奏波浪中，","l032":"我想随其摇摆。","l034":"若纵身跃入，那里便已是","l035":"无重力；漂浮着起舞。","l051":"绝对无人知晓的夜晚。"}
    for frame_id, value in changes.items(): byid[frame_id]["caption"]["translationZh"]=value
    applied.extend(["p-l026-l029-crossline","p-l030-l032-crossline","p-l034-l035-crossline","p-l051-translation"])
    byid["l051"]["grammarCards"]=[card("金輪際","绝对；无论如何",pos="副词"),card("誰","谁",pos="疑问代词"),card("も",function="全面否定：谁也不……",pos="副助词"),card("知らない","不知道的",pos="动词否定形"),card("夜","夜晚",pos="名词")]; applied.append("p-l051-split-daremo")
    set_card(byid["l053"],3,{"zhMeaning":"啊；何其令人感慨","posZh":"感叹词（古语）"}); applied.append("p-l053-ahare")
    touched={"l002","l005","l008","l014","l016","l018","l019","l022","l023","l025","l026","l027","l028","l029","l030","l031","l032","l034","l035","l051","l053"}
    for frame in data["frames"]:
        if frame["id"] in touched:
            frame["caption"]["furigana"]=[{"token":c["token"],"reading":c["reading"]} for c in frame["grammarCards"]]
            frame["status"]="partially-user-authorized; overall-review-pending"
            frame["fieldProvenance"]["smartAudit"]="smart-audit-v1 accepted by user"
    write(target,data); after=sha(target)
    write(PROJECT/"review"/"merge-log.json",{"schemaVersion":1,"source":"project/proposals/smart-audit-v1.json","userWording":"全部采纳","acceptedProposalIds":applied,"beforeFramesSha256":before,"afterFramesSha256":after,"structuralChanges":["p-l016-split-dance","p-l051-split-daremo"],"renderAuthorized":False})
    write(PROJECT/"review"/"review-decision.json",{"content":"changes-requested","scope":"all","renderAuthorized":False,"frameSha256":after,"note":"User authorized every smart-audit-v1 proposal; overall lyric-card review remains open."})

if __name__=="__main__": main()
