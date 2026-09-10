"""Authorized full-video entry point for the accepted next-line foreground.

Delegates composition to the fixed renderer, replacing only its foreground class.
The standard review gate is preserved and binds this entry point, while dependency
pins additionally prevent an edited preview class from escaping authorization.
"""
import json
import sys
from pathlib import Path

SKILL = Path('C:/Users/eke_l/.codex/skills/japanese-song-study-video/scripts')
sys.path.insert(0,str(SKILL))
import render_video as base
from next_line_foreground import NextLineRenderer
from verify_render_gate import sha, verify_render_gate

PINS = {
    SKILL/'render_video.py':'dccfbc2f4233aee70aa2381f9745ac88552a58b1c1e0b044a3dd9023201d5b61',
    SKILL/'build_foreground_timeline.py':'6ac68b7ac62ea813d22118a82035aa5c34d128410d0805c51e2a5c0fc298d2f6',
    SKILL/'render_foobar_spectrum.py':'a86096b6055426bde5c5be39eccf74d3a3068acfb4d41a0c55cc97e9cc470fa3',
    Path(__file__).with_name('next_line_foreground.py'):'f614cac796f910f0803a7580826ecc553b2e196f48172b3b958400f4c06560e7',
}

def project_gate(root, _base_renderer):
    for path, expected in PINS.items():
        if sha(path) != expected: raise ValueError(f'Pinned render dependency changed: {path}')
    manifest=base.load(root/'project/input-manifest.json')
    presentation=base.load(root/'project/presentation.json')
    if presentation['foreground'].get('variantId') != 'study-current-v3-next-line-a':
        raise ValueError('This entry point requires the user-approved next-line variant')
    if manifest['alignment']['offsetMs'] != 0:
        raise ValueError('This project plan preserves the complete FLAC at output zero; review offset changes explicitly')
    if not manifest['music']['asset'].endswith('.flac'):
        raise ValueError('Expected the original FLAC source')
    return verify_render_gate(root,Path(__file__).resolve())

if __name__=='__main__':
    base.verify_render_gate=project_gate
    base.ForegroundRenderer=NextLineRenderer
    base.main()
