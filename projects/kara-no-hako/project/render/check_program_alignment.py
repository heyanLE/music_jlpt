"""Read-only multisegment comparison; never shifts or trims the FLAC."""
import importlib.util
import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT.parent / 'ray-chou-kaguya-hime-study/project/render/match_music_program.py'
spec = importlib.util.spec_from_file_location('program_features', HELPER)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
music = helper.features(helper.audio(ROOT / 'source/music.flac'))
video = helper.features(helper.audio(ROOT / 'source/background.mp4'))
hop_ms = helper.HOP * 1000 / helper.RATE
matches = []
for sec in (0, 8, 16, 30, 46, 62, 76, 85):
    start = round(sec * 1000 / hop_ms)
    query = music[start:start + round(8000 / hop_ms)]
    scores = np.array([(video[i:i+len(query)] * query).sum(axis=1).mean() for i in range(len(video)-len(query)+1)])
    best = int(np.argmax(scores))
    matches.append({'musicMs': round(start*hop_ms), 'videoMs': round(best*hop_ms), 'offsetMs': round((best-start)*hop_ms), 'cosineScore': round(float(scores[best]), 5)})
report = {'algorithm': 'normalized-log-spectral-multiple-windows', 'hopMs': hop_ms, 'windowMs': 8000, 'matches': matches, 'applied': False}
path = ROOT / 'project/alignment/program-match.json'
path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(report, ensure_ascii=False, indent=2))
