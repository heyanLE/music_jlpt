"""Portable-entrypoint safety regressions; no media rendering or external writes."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import verify_render_gate as gate
from runtime_font import font_path


class PortabilityTests(unittest.TestCase):
    def test_local_dependency_tamper_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); render=root/'project/render';render.mkdir(parents=True)
            renderer=render/'custom.py';renderer.write_text('# entry')
            helper=render/'helper.py';helper.write_text('# original')
            manifest=render/'renderer-dependencies.json'
            manifest.write_text(json.dumps({'files':['project/render/helper.py']}))
            review={k:root/(k+'.json') for k in ('auditPath','mergePath','decisionPath')}
            paths=gate.authorization_hash_paths(root,renderer,review)
            for path in paths.values():
                if not path.exists():
                    path.parent.mkdir(parents=True,exist_ok=True);path.write_text('{}')
            auth={'renderAuthorized':True,**{k:gate.sha(p) for k,p in paths.items()}}
            (root/'project/render-authorization.json').write_text(json.dumps(auth))
            with patch.object(gate,'verify_review_gate',return_value=review):
                gate.verify_render_gate(root,renderer)
                helper.write_text('# changed')
                with self.assertRaisesRegex(ValueError,'stale'):
                    gate.verify_render_gate(root,renderer)
                helper.write_text('# original')
                manifest.unlink()
                with self.assertRaisesRegex(ValueError,'missing'):
                    gate.verify_render_gate(root,renderer)

    def test_dependency_escape_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'projectroot';render=root/'project/render';render.mkdir(parents=True)
            outside=Path(tmp)/'outside.py';outside.write_text('')
            (render/'renderer-dependencies.json').write_text(json.dumps({'files':['../outside.py']}))
            review={k:root/k for k in ('auditPath','mergePath','decisionPath')}
            with self.assertRaisesRegex(ValueError,'inside project root'):
                gate.authorization_hash_paths(root,render/'custom.py',review)

    def test_explicit_missing_font_does_not_fallback(self):
        with patch.dict(os.environ,{'STUDY_FONT':'/missing-test-font-193857.ttf'}):
            with self.assertRaises(RuntimeError): font_path()


if __name__=='__main__':unittest.main()
