from pathlib import Path
from render_thumbnail import make_cover, make_cover_4x3
ROOT=Path(__file__).parent
params=(ROOT/'love2000-cover.jpg','LOVE 2000','遠野ひかる','败犬女主太多了 ED')
make_cover(*params,ROOT/'output'/'love2000-thumbnail-v2.png')
make_cover_4x3(*params,ROOT/'output'/'love2000-thumbnail-4x3-v2.png')
