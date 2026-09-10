"""Render both phone-first cover ratios for うちゅうのふしぎ."""
from pathlib import Path
from render_thumbnail import make_cover, make_cover_4x3

ROOT=Path(__file__).parent
params=(ROOT/'uchuu-cover.jpg','うちゅうのふしぎ','夢限大みゅーたいぷ','BanG Dream! YUME∞MITA ED')
make_cover(*params,ROOT/'output'/'uchuu-thumbnail.png')
make_cover_4x3(*params,ROOT/'output'/'uchuu-thumbnail-4x3.png')
print(ROOT/'output'/'uchuu-thumbnail.png')
print(ROOT/'output'/'uchuu-thumbnail-4x3.png')
