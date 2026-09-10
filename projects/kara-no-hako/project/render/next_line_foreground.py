"""Project-local, code-native foreground variant accepted by the user.

Only the top cover strip changes. Current-line fonts/cards/highlights are delegated
to the shared renderer. No content is generated here: all readings come from frames.
This module renders still layers only; final composition needs separate authorization.
"""
import json
import sys
from pathlib import Path
from PIL import Image, ImageDraw

SKILL = Path('C:/Users/eke_l/.codex/skills/japanese-song-study-video/scripts')
sys.path.insert(0, str(SKILL))
from render_video import ForegroundRenderer


class NextLineRenderer(ForegroundRenderer):
    def __init__(self, root, width=1920, height=1080):
        super().__init__(root, width, height)
        self.ordered = sorted(self.frames.values(), key=lambda f: f['startMs'])
        self.preview_layouts = {}

    def render(self, frame_id, active_index, output, cover_only=False, cover_visible=True):
        super().render(frame_id, active_index, output, cover_only=cover_only, cover_visible=False)
        if frame_id is None and not cover_only: return
        image = Image.open(output).convert('RGBA')
        if cover_visible:
            image.alpha_composite(self.cover.resize((self.px(220,'x'), self.px(220,'y')), Image.Resampling.LANCZOS), (self.px(95,'x'), self.px(35,'y')))
        index = next((i for i,f in enumerate(self.ordered) if f['id']==frame_id), -1)
        if not cover_only and index >= 0 and index+1 < len(self.ordered):
            self.add_preview(image, self.ordered[index+1])
        image.save(output)

    def add_preview(self, image, frame):
        panel = Image.new('RGBA', image.size)
        draw = ImageDraw.Draw(panel)
        draw.rounded_rectangle((self.px(350,'x'),self.px(35,'y'),self.px(1825,'x'),self.px(255,'y')),radius=self.px(20),fill=(0,0,0,72))
        self.outlined(draw,(self.px(380,'x'),self.px(42,'y')),'下一句',self.font(23),'white',2)
        text = frame['caption']['japanese']
        cells, cursor = [], 0
        for card in frame.get('grammarCards',[]):
            start=text.find(card['token'],cursor)
            if start < 0: raise ValueError(f"Preview token mismatch {frame['id']} {card['token']}")
            if text[cursor:start].strip():
                cells.append({'token':text[cursor:start],'romaji':'','start':cursor,'end':start})
            end=start+len(card['token'])
            cells.append({**card,'start':start,'end':end})
            cursor=end
        if text[cursor:].strip(): cells.append({'token':text[cursor:],'romaji':'','start':cursor,'end':len(text)})
        gap=self.px(40)
        available=self.px(1385,'x')
        for size, roman_size in ((54,34),(50,34),(46,32),(42,30)):
            jp, roman = self.font(size), self.font(roman_size)
            widths=[max(draw.textlength(c['token'],font=jp),draw.textlength(c.get('romaji',''),font=roman)) for c in cells]
            total=sum(widths)+gap*(len(cells)-1)
            if total <= available: break
        else: raise ValueError(f"Preview overflow: {frame['id']}")
        x=self.px(395,'x')+(available-total)/2
        found=0
        for cell,width in zip(cells,widths):
            token=cell['token']; tx=x+(width-draw.textlength(token,font=jp))/2
            self.outlined(draw,(tx,self.px(105,'y')),token,jp,'white',3)
            romaji=cell.get('romaji','')
            self.outlined(draw,(x+(width-draw.textlength(romaji,font=roman))/2,self.px(184,'y')),romaji,roman,'white',2)
            for ruby in frame['caption'].get('furigana',[]):
                start,end=ruby['start'],ruby['end']
                if cell['start'] <= start and end <= cell['end']:
                    assert text[start:end]==ruby['base']
                    rx=tx+draw.textlength(text[cell['start']:start],font=jp)
                    self.outlined(draw,(rx,self.px(73,'y')),ruby['reading'],self.font(28),'white',2)
                    found+=1
            if cell.get('sourceWord'):
                source=cell['sourceWord']; font=self.font(23)
                self.outlined(draw,(x+(width-draw.textlength(source,font=font))/2,self.px(73,'y')),source,font,'white',2)
            x+=width+gap
        assert found==len(frame['caption'].get('furigana',[]))
        self.preview_layouts[frame['id']]={'japaneseFontSize':size,'romajiFontSize':roman_size,'widthPx':total,'limitPx':available,'rubyCount':found}
        image.alpha_composite(panel)
