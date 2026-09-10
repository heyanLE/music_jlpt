from pathlib import Path
from PIL import Image

ROOT=Path(__file__).parent
source=Path(r'C:\Users\eke_l\AppData\Local\Temp\codex-clipboard-78583958-9add-452d-b1c9-ab8163492dcc.png')
im=Image.open(source).convert('RGB')
# Right-upper square: use full image width and crop upward from the right side.
side=min(im.width, im.height)
box=(im.width-side, 0, im.width, side)
im.crop(box).resize((1080,1080),Image.Resampling.LANCZOS).save(ROOT/'uchuu-cover.jpg',quality=95)
print(ROOT/'uchuu-cover.jpg')
