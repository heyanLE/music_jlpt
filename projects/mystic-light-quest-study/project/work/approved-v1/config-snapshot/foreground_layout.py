"""Shared character anchors for lyric, ruby, source words and token romaji."""
import unicodedata

def plan(frame, draw, font, ruby_font, roman_font, source_font, gap):
    text = frame['caption']['japanese']
    cards = frame.get('grammarCards', [])
    spans, cursor = [], 0
    for card in cards:
        start = text.find(card['token'], cursor)
        if start < 0: raise ValueError(f"Missing token: {frame['id']} {card['token']}")
        cursor = start + len(card['token'])
        spans.append((start, cursor))
    rubies = []
    for ruby in frame['caption'].get('furigana', []):
        start = ruby.get('start')
        if start is None: start = spans[ruby['cardIndex']][0] + ruby.get('surfaceOffset', 0)
        end = ruby.get('end', start + len(ruby['base']))
        assert text[start:end] == ruby['base']
        rubies.append({**ruby, 'start':start, 'end':end})
    segments, cursor = [], 0
    for ci, (start, end) in enumerate(spans):
        if start > cursor: segments.append((cursor, start, None))
        segments.append((start, end, ci)); cursor = end
    if cursor < len(text): segments.append((cursor, len(text), None))
    xs, widths = [0.0]*len(text), [float(draw.textlength(c,font=font)) for c in text]
    blocks, total = [], 0.0
    for start, end, ci in segments:
        local, x = [], 0.0
        for i in range(start,end): local.append(x); x += widths[i]
        # Ruby remains left-aligned with its kanji; reserve room before the next ruby.
        previous_end = 0.0
        own = [r for r in rubies if start <= r['start'] < end]
        for r in own:
            k = r['start'] - start
            shift = max(0.0, previous_end-local[k])
            if shift:
                local[k:] = [v+shift for v in local[k:]]; x += shift
            previous_end = local[k]+draw.textlength(r['reading'],font=ruby_font)+gap
        extent = max(x, previous_end-gap if own else x)
        roman_w = source_w = 0.0
        if ci is not None:
            card=cards[ci]
            roman_w=draw.textlength(card.get('romaji',''),font=roman_font)
            source_w=draw.textlength(card.get('sourceWord',''),font=source_font)
        block_w=max(extent,roman_w,source_w)
        inset=(block_w-extent)/2
        for i in range(start,end): xs[i]=total+inset+local[i-start]
        blocks.append({'start':start,'end':end,'cardIndex':ci,'x':total,'width':block_w,
                       'romajiX':total+(block_w-roman_w)/2,'romajiWidth':roman_w,
                       'sourceX':total+(block_w-source_w)/2,'sourceWidth':source_w})
        total += block_w+gap
    return {'xs':xs,'widths':widths,'width':max(0,total-gap),'blocks':blocks,'spans':spans,'rubies':rubies}

def qrc_spans(text, parts):
    """Map source QRC parts without accumulating offsets from omitted spaces."""
    cursor, result = 0, []
    for part in parts:
        positions=[]
        for ch in part['text']:
            if ch.isspace():
                if cursor<len(text) and text[cursor].isspace(): cursor+=1
                continue
            while cursor<len(text) and text[cursor].isspace(): cursor+=1
            if cursor>=len(text) or unicodedata.normalize('NFKC',ch)!=unicodedata.normalize('NFKC',text[cursor]):
                raise ValueError(f'QRC character mismatch at {cursor}: {part!r}')
            positions.append(cursor); cursor+=1
        result.append((min(positions),max(positions)+1) if positions else (cursor,cursor))
    if text[cursor:].strip(): raise ValueError('Unmatched trailing lyric text')
    return result
