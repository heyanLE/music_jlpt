import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRAMES = ROOT / "frames.json"
OUT = ROOT / "proposals" / "lexical.json"

# Each sequence covers the displayed Japanese exactly.  The purpose of this
# proposal is lexical grouping and readings only; grammar/translation agents
# own meanings, particle functions, and detailed grammar labels.
UNITS = {
    "l001": [("お別れ", "おわかれ", "owakare"), ("した", "した", "shita"), ("のは", "のは", "no wa"), ("もっと", "もっと", "motto")],
    "l002": [("前", "まえ", "mae"), ("の", "の", "no"), ("事", "こと", "koto"), ("だった", "だった", "datta"), ("ような", "ような", "you na")],
    "l003": [("悲しい", "かなしい", "kanashii"), ("光", "ひかり", "hikari"), ("は", "は", "ha"), ("封じ込めて", "ふうじこめて", "fuujikomete")],
    "l004": [("踵", "かかと", "kakato"), ("すり減らした", "すりへらした", "suriherashita"), ("んだ", "んだ", "n da")],
    "l005": [("君", "きみ", "kimi"), ("と", "と", "to"), ("いた", "いた", "ita"), ("時", "とき", "toki"), ("は", "は", "ha"), ("見えた", "みえた", "mieta")],
    "l006": [("今", "いま", "ima"), ("は", "は", "ha"), ("見えなくなった", "みえなくなった", "mienakunatta")],
    "l007": [("透明な", "とうめいな", "toumei na"), ("彗星", "すいせい", "suisei"), ("を", "を", "wo"), ("ぼんやりと", "ぼんやりと", "bonyari to")],
    "l008": [("でも", "でも", "demo"), ("それだけ", "それだけ", "soredake"), ("探している", "さがしている", "sagashite iru")],
    "l009": [("しょっちゅう", "しょっちゅう", "shotchuu"), ("唄", "うた", "uta"), ("を", "を", "wo"), ("歌った", "うたった", "utatta"), ("よ", "よ", "yo")],
    "l010": [("その", "その", "sono"), ("時だけの", "ときだけの", "toki dake no"), ("メロディー", "メロディー", "merodii"), ("を", "を", "wo")],
    "l011": [("寂しく", "さびしく", "sabishiku"), ("なんか", "なんか", "nanka"), ("なかった", "なかった", "nakatta"), ("よ", "よ", "yo")],
    "l012": [("ちゃんと", "ちゃんと", "chanto"), ("寂しくなれた", "さびしくなれた", "sabishiku nareta"), ("から", "から", "kara")],
    "l013": [("いつまで", "いつまで", "itsu made"), ("どこまで", "どこまで", "doko made"), ("なんて", "なんて", "nante")],
    "l014": [("正常か", "せいじょうか", "seijou ka"), ("異常か", "いじょうか", "ijou ka"), ("なんて", "なんて", "nante")],
    "l015": [("考える", "かんがえる", "kangaeru"), ("暇もない", "ひまもない", "hima mo nai"), ("程", "ほど", "hodo")],
    "l016": [("歩くのは", "あるくのは", "aruku no wa"), ("大変だ", "たいへんだ", "taihen da")],
    "l017": [("楽しい方が", "たのしいほうが", "tanoshii hou ga"), ("ずっと", "ずっと", "zutto"), ("いいよ", "いいよ", "ii yo")],
    "l018": [("ごまかして", "ごまかして", "gomakashite"), ("笑っていくよ", "わらっていくよ", "waratte iku yo")],
    "l019": [("大丈夫だ", "だいじょうぶだ", "daijoubu da"), ("あの", "あの", "ano"), ("痛みは", "いたみは", "itami wa")],
    "l020": [("忘れたって", "わすれたって", "wasuretatte"), ("消えやしない", "きえやしない", "kieyashinai")],
    "l021": [("理想で", "りそうで", "risou de"), ("作った", "つくった", "tsukutta"), ("道を", "みちを", "michi wo")],
    "l022": [("現実が", "げんじつが", "genjitsu ga"), ("塗り替えていくよ", "ぬりかえていくよ", "nurikaete iku yo")],
    "l023": [("思い出は", "おもいでは", "omoide wa"), ("その", "その", "sono"), ("軌跡の上で", "きせきのうえで", "kiseki no ue de")],
    "l024": [("輝きになって", "かがやきになって", "kagayaki ni natte"), ("残っている", "のこっている", "nokotte iru")],
    "l025": [("お別れ", "おわかれ", "owakare"), ("した", "した", "shita"), ("のは", "のは", "no wa"), ("何で", "なんで", "nande")],
    "l026": [("何のため", "なんのため", "nan no tame"), ("だったんだろうな", "だったんだろうな", "datta n darou na")],
    "l027": [("悲しい", "かなしい", "kanashii"), ("光が", "ひかりが", "hikari ga"), ("僕の", "ぼくの", "boku no"), ("影を", "かげを", "kage wo")],
    "l028": [("前に", "まえに", "mae ni"), ("長く", "ながく", "nagaku"), ("伸ばしている", "のばしている", "nobashite iru")],
    "l029": [("時々", "ときどき", "tokidoki"), ("熱が", "ねつが", "netsu ga"), ("出るよ", "でるよ", "deru yo")],
    "l030": [("時間がある時", "じかんがあるとき", "jikan ga aru toki"), ("眠るよ", "ねむるよ", "nemuru yo")],
    "l031": [("夢だと", "ゆめだと", "yume da to"), ("解る", "わかる", "wakaru"), ("その中で", "そのなかで", "sono naka de")],
    "l032": [("君と", "きみと", "kimi to"), ("会ってから", "あってから", "atte kara"), ("また", "また", "mata"), ("行こう", "いこう", "ikou")],
    "l033": [("晴天とは", "せいてんとは", "seiten to wa"), ("ほど遠い", "ほどとおい", "hodotooi")],
    "l034": [("終わらない", "おわらない", "owaranai"), ("暗闇にも", "くらやみにも", "kurayami ni mo")],
    "l035": [("星を", "ほしを", "hoshi wo"), ("思い浮かべたなら", "おもいうかべたなら", "omoiukabetanara")],
    "l036": [("すぐ", "すぐ", "sugu"), ("銀河の中だ", "ぎんがのなかだ", "ginga no naka da")],
    "l037": [("あまり", "あまり", "amari"), ("泣かなくなっても", "なかなくなっても", "nakanakunatte mo")],
    "l038": [("靴を", "くつを", "kutsu wo"), ("新しくしても", "あたらしくしても", "atarashiku shite mo")],
    "l039": [("大丈夫だ", "だいじょうぶだ", "daijoubu da"), ("あの", "あの", "ano"), ("痛みは", "いたみは", "itami wa")],
    "l040": [("忘れたって", "わすれたって", "wasuretatte"), ("消えやしない", "きえやしない", "kieyashinai")],
    "l041": [("伝えたかった", "つたえたかった", "tsutaetakatta"), ("事が", "ことが", "koto ga")],
    "l042": [("きっと", "きっと", "kitto"), ("あったんだろうな", "あったんだろうな", "atta n darou na")],
    "l043": [("恐らく", "おそらく", "osoraku"), ("ありきたり", "ありきたり", "arikitari"), ("なんだろうけど", "なんだろうけど", "nan darou kedo")],
    "l044": [("こんなにも", "こんなにも", "konna ni mo")],
    "l045": [("お別れ", "おわかれ", "owakare"), ("した", "した", "shita"), ("事は", "ことは", "koto wa")],
    "l046": [("出会った事と", "であったことと", "deatta koto to"), ("繋がっている", "つながっている", "tsunagatte iru")],
    "l047": [("あの", "あの", "ano"), ("透明な", "とうめいな", "toumei na"), ("彗星は", "すいせいは", "suisei wa")],
    "l048": [("透明だから", "とうめいだから", "toumei da kara"), ("無くならない", "なくならない", "nakunaranai")],
    "l049": [("◯×△", "まるばつさんかく", "marubatsusankaku"), ("どれか", "どれか", "doreka"), ("なんて", "なんて", "nante")],
    "l050": [("皆と", "みなと", "mina to"), ("比べて", "くらべて", "kurabete"), ("どうか", "どうか", "douka"), ("なんて", "なんて", "nante")],
    "l051": [("確かめる", "たしかめる", "tashikameru"), ("間も無い", "まもない", "ma mo nai"), ("程", "ほど", "hodo")],
    "l052": [("生きるのは", "いきるのは", "ikiru no wa"), ("最高だ", "さいこうだ", "saikou da")],
    "l053": [("あまり", "あまり", "amari"), ("泣かなくなっても", "なかなくなっても", "nakanakunatte mo")],
    "l054": [("ごまかして", "ごまかして", "gomakashite"), ("笑っていくよ", "わらっていくよ", "waratte iku yo")],
    "l055": [("大丈夫だ", "だいじょうぶだ", "daijoubu da"), ("あの", "あの", "ano"), ("痛みは", "いたみは", "itami wa")],
    "l056": [("忘れたって", "わすれたって", "wasuretatte"), ("消えやしない", "きえやしない", "kieyashinai")],
    "l057": [("大丈夫だ", "だいじょうぶだ", "daijoubu da"), ("この", "この", "kono"), ("光の始まりには", "ひかりのはじまりには", "hikari no hajimari ni wa")],
    "l058": [("君がいる", "きみがいる", "kimi ga iru")],
}


def card(token, reading, romaji):
    item = {
        "token": token,
        "reading": reading,
        "romaji": romaji,
        "grammarStructureZh": "待语法审阅",
        "posZh": "待语法审阅",
        "status": "assisted-proposal",
        "fieldProvenance": {
            "token": "lexical v2 proposal",
            "reading": "lexical v2 proposal",
            "romaji": "lexical v2 proposal",
            "grammarStructureZh": "lexical v2 proposal",
        },
    }
    if token == "メロディー":
        item["sourceWord"] = "melody"
    return item


raw = FRAMES.read_bytes()
data = json.loads(raw)
by_id = {frame["id"]: frame for frame in data["frames"]}
changes = []
# Limit this role artifact to the highest-value corrections: broken
# conjugation/compound boundaries, an actual loanword annotation, and the
# symbol reading that the draft tokenizer cannot infer.
SELECTED = {
    "l001", "l002", "l003", "l004", "l006", "l009", "l010", "l011",
    "l018", "l020", "l021", "l022", "l024", "l025", "l026", "l028",
    "l032", "l037", "l041", "l042", "l043", "l045", "l046", "l048",
    "l049", "l053", "l054", "l056", "l057",
}
for frame_id, units in UNITS.items():
    if frame_id not in SELECTED:
        continue
    frame = by_id[frame_id]
    original = frame["caption"]["japanese"]
    assert "".join(unit[0] for unit in units) == "".join(original.split()), (frame_id, original, units)
    replacement = [card(*unit) for unit in units]
    changes.append({
        "frameId": frame_id,
        "field": "grammarCards",
        "old": frame["grammarCards"],
        "new": replacement,
        "confidence": 0.95,
        "evidence": [
            "JOYSOUND official karaoke lyric listing and ChordWiki kana notation cross-check",
            "Japanese dictionary-form grouping; only kanji ruby, loanword, and revised Hepburn fields proposed",
        ],
        "changesTokenStructure": True,
    })
    old_romaji = frame["caption"]["romaji"]
    new_romaji = " ".join(unit[2] for unit in units)
    if old_romaji != new_romaji:
        changes.append({
            "frameId": frame_id,
            "field": "caption.romaji",
            "old": old_romaji,
            "new": new_romaji,
            "confidence": 0.98,
            "evidence": [
                "ChordWiki kana notation cross-check; revised Hepburn aligned to proposed lexical units",
            ],
            "changesTokenStructure": False,
        })

proposal = {
    "schemaVersion": 2,
    "reviewRole": "lexical",
    "scope": {"frameIds": [frame_id for frame_id in UNITS if frame_id in SELECTED]},
    "baseFrameSha256": hashlib.sha256(raw).hexdigest(),
    "changes": changes,
}
OUT.parent.mkdir(exist_ok=True)
OUT.write_text(json.dumps(proposal, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"wrote {OUT}: {len(SELECTED)} frames, {len(changes)} changes")
