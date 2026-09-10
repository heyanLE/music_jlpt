"""Render both cover ratios for feel my soul."""
from pathlib import Path
from render_thumbnail import make_cover, make_cover_4x3

ROOT=Path(__file__).parent
params=(ROOT/'feel-my-soul-cover.jpg','feel my soul','寺澤百花','败犬女主太多了 ED')
make_cover(*params,ROOT/'output'/'feel-my-soul-thumbnail.png')
make_cover_4x3(*params,ROOT/'output'/'feel-my-soul-thumbnail-4x3.png')
print(ROOT/'output'/'feel-my-soul-thumbnail.png')
print(ROOT/'output'/'feel-my-soul-thumbnail-4x3.png')
