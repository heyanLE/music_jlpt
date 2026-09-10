"""Read-only executable, imaging library and font inventory; no installs or renders."""
import hashlib
import importlib.metadata
import json
import platform
import shutil
import subprocess
import sys
from runtime_font import font_path


def inspect():
    result = {'python': sys.version, 'platform': platform.platform(), 'libraries': {}, 'tools': {}, 'issues': []}
    for name in ('Pillow', 'numpy'):
        try: result['libraries'][name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError: result['issues'].append('Missing library: '+name)
    for name in ('ffmpeg', 'ffprobe', 'node', 'npm'):
        exe = shutil.which(name)
        result['tools'][name] = {'path': exe}
        if not exe:
            if name in ('ffmpeg', 'ffprobe'): result['issues'].append('Missing executable: '+name)
            continue
        if name in ('ffmpeg', 'ffprobe'):
            p = subprocess.run([exe, '-version'], capture_output=True, text=True, timeout=15)
            result['tools'][name]['version'] = p.stdout.splitlines()[0] if p.stdout else p.stderr[:200]
            if p.returncode: result['issues'].append(name+' did not run successfully')
    try:
        font = font_path()
        result['font'] = {'path': str(font), 'sha256': hashlib.sha256(font.read_bytes()).hexdigest(), 'index': 0}
    except RuntimeError as exc: result['issues'].append(str(exc))
    result['note'] = 'Availability only. Check FFmpeg features and font glyph/layout QA before rendering. Node/npm optional for decoded projects.'
    return result


if __name__ == '__main__':
    report = inspect()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    sys.exit(bool(report['issues']))
