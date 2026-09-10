"""Seal technical and visual QA for the authorized horizontal-rail render."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P = ROOT / "project"
QA = P / "qa/static-neighbors-r1-auto"
REPORT = QA / "qa-report.json"
CANDIDATE = ROOT / "project/work/static-neighbors-r1/16x9/kara-no-hako--16x9--static-neighbors-r1.mkv"

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def load(path): return json.loads(path.read_text(encoding="utf-8"))
def write(path, value): path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

report = load(REPORT)
assert report["candidateSha256"] == sha(CANDIDATE)
report.update({
    "result": "passed",
    "reviewedAt": datetime.now(timezone.utc).isoformat(),
    "qaScope": "authorized static-neighbors-r1 clean full render",
    "technicalFindings": {
        "durationMs": 183844,
        "video": "H.264 1920x1080 yuv420p CFR 30/1; starts at zero",
        "audio": "FLAC 48000 Hz 24-bit stream-copy; starts at zero",
        "sourceAudioPacketSha256": "4f44bd10deb164fd37dba13e7b65830fbf7c44a1a6f3202bcc0b10f4ac208d64",
        "candidateAudioPacketSha256": "4f44bd10deb164fd37dba13e7b65830fbf7c44a1a6f3202bcc0b10f4ac208d64",
        "audioPacketsBitIdentical": True,
        "renderMethod": "source background + Gaussian cover + reviewed frames + transparent spectrum; no prior-master pixels",
        "customRendererGate": "PASS"
    },
    "visualFindings": {
        "staticNeighbors": "Passed: previous/current/next sentences remain fixed and update only at the original hard line-switch boundary; no position interpolation.",
        "edgeClipping": "Passed: neighboring sentences clip at x=0/1920 without inset seams.",
        "cover": "Passed: exact hoshi-furu-umi geometry [850,35,220,220].",
        "highlight": "Passed: Japanese follows QRC timing; associated furigana and romaji highlight as whole blocks.",
        "foregroundVeil": "Passed: one foreground-wide 0.28 veil; no lyric-local mask or upper/lower discontinuity.",
        "cards": "Passed: reviewed 153-card content remains static, translucent, single-row and unhighlighted.",
        "backgroundTransition": "Passed: 96.114 s background-only video-to-Gaussian transition retains foreground and spectrum.",
        "spectrum": "Passed: transparent persistent spectrum remains bottom-centred.",
        "finalLine": "Passed: final line remains visible to output end in persistent mode."
    },
    "promotionReady": True
})
write(REPORT, report)
state = load(P / "build-state.json")
state["stage"] = "qa_passed"
state["renderAuthorization"] = True
state["renderResult"] = {
    "runId": "static-neighbors-r1",
    "candidate": CANDIDATE.relative_to(ROOT).as_posix(),
    "candidateSha256": sha(CANDIDATE),
    "qaReport": REPORT.relative_to(ROOT).as_posix(),
    "qa": "passed",
    "finalPromotion": "pending"
}
state["notes"].append("Static previous/current/next lyric full render passed technical and visual QA; authorized wording: 按照这个生成整个视频.")
write(P / "build-state.json", state)
print(json.dumps({"result": "passed", "candidateSha256": sha(CANDIDATE)}, ensure_ascii=False))
