"""Resolve a deliberate CJK font without silently substituting the typeface."""
import os
from pathlib import Path


def font_path():
    explicit = os.environ.get('STUDY_FONT')
    path = Path(explicit) if explicit else Path('C:/Windows/Fonts/msyhbd.ttc')
    if not path.is_file():
        raise RuntimeError('Approved bold CJK font missing. Set STUDY_FONT to an installed font and verify layout; no silent substitution.')
    return path
