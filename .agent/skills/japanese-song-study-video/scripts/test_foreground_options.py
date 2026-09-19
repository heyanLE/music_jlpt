"""Small synthetic regressions; no historical project or full-video rendering."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from foreground_options import configure_options, countdown_plan, resolve_options


class LearningAidTests(unittest.TestCase):
    def test_configuration_compatibility(self):
        self.assertTrue(configure_options(None)["neighbors"]["enabled"])
        self.assertTrue(configure_options(None)["countdown"]["enabled"])
        self.assertEqual(configure_options(None)["preludeMode"], "first-line")
        self.assertEqual(resolve_options({})["preludeMode"], "hidden")
        self.assertFalse(configure_options({})["neighbors"]["enabled"])
        self.assertFalse(configure_options({})["countdown"]["enabled"])
        self.assertEqual(configure_options({}, "on", "off", "first-line"), {
            "neighbors": {"enabled": True},
            "countdown": {"enabled": False, "durationMs": 3000, "placement": "template"},
            "preludeMode": "first-line"})
        self.assertEqual(configure_options(None, None, None, None, "neighbor-left")["countdown"]["placement"], "neighbor-left")
        for neighbors in ("on", "off"):
            for countdown in ("on", "off"):
                options = configure_options({}, neighbors, countdown)
                self.assertEqual(options["neighbors"]["enabled"], neighbors == "on")
                self.assertEqual(options["countdown"]["enabled"], countdown == "on")

    def test_countdown_reveal_prelude(self):
        """Lyrics appear together with the 3/2/1 badge, and not before it."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); project = root / "project"; (project / "timing").mkdir(parents=True)
            def write(name, doc): (project / name).write_text(json.dumps(doc), encoding="utf-8")
            frames = [{"id": "l1", "startMs": 8000, "endMs": 9000, "caption": {"japanese": "歌"}}]
            write("frames.json", {"frames": frames})
            write("timing/qm.json", {"lines": [{"startMs": 8000, "endMs": 9000, "text": "歌",
                                                "parts": [{"text": "歌", "startMs": 8000, "endMs": 9000}]}]})
            write("input-manifest.json", {"alignment": {"offsetMs": 0}})
            write("scene-timeline.json", {"segments": [{"startMs": 0, "endMs": "audio-end", "foregroundMode": "follow-lyrics"}]})
            options = configure_options(None, "on", "on", "countdown-reveal", "neighbor-left")
            write("presentation.json", {"foreground": {**options, "defaultMode": "follow-lyrics"}})
            subprocess.run([sys.executable, str(Path(__file__).with_name("build_foreground_timeline.py")),
                            str(root), str(root / "timeline.json"), "--duration-ms", "10000"], check=True, capture_output=True)
            timeline = json.loads((root / "timeline.json").read_text())
            def state(time): return next(s for s in timeline["segments"] if s["startMs"] <= time < s["endMs"])
            self.assertEqual(state(1000)["kind"], "blank")          # before the countdown: nothing
            self.assertNotIn("countdownValue", state(1000))
            self.assertEqual(state(5500)["countdownValue"], 3)      # countdown starts here
            self.assertEqual(state(5500)["frameId"], "l1")          # ... with the first line
            self.assertEqual(state(5500)["kind"], "neutral")
            self.assertEqual(state(7500)["countdownValue"], 1)
            self.assertEqual(state(9000)["kind"], "neutral")

    def test_authorize_and_verify_share_dependency_hashes(self):
        import authorize_render
        from verify_render_gate import authorization_hash_paths, sha
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); (root / "project").mkdir()
            review = {"auditPath": root / "audit.json", "mergePath": root / "merge.json", "decisionPath": root / "decision.json"}
            renderer = Path(__file__).with_name("render_video.py").resolve()
            paths = authorization_hash_paths(root, renderer, review)
            self.assertIn("rendererDependency:foreground_options.py", paths)
            self.assertIn("rendererDependency:build_foreground_timeline.py", paths)
            for path in paths.values():
                if path.is_relative_to(root):
                    path.parent.mkdir(parents=True, exist_ok=True); path.write_text("{}", encoding="utf-8")
            with patch.object(authorize_render, "verify_review_gate", return_value=review), patch.object(sys, "argv", ["authorize_render", str(root), "--authorization-text", "确认渲染"]):
                authorize_render.main()
            contract = json.loads((root / "project" / "render-authorization.json").read_text(encoding="utf-8"))
            self.assertTrue(all(contract[key] == sha(path) for key, path in paths.items()))

    def test_invalid_options(self):
        for options in ({"neighbors": {"enabled": "false"}}, {"countdown": {"enabled": True, "durationMs": 5000}}, {"preludeMode": "always"}):
            with self.assertRaises(ValueError): resolve_options(options)

    def test_explicit_migration_preserves_unrelated_settings_and_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"; project.mkdir()
            presentation = {"schemaVersion": 2, "foreground": {"defaultMode": "persistent", "veil": {"opacity": .54}, "customReviewedField": "keep"}, "floatingOverlay": {"enabled": True}}
            path = project / "presentation.json"; path.write_text(json.dumps(presentation), encoding="utf-8")
            subprocess.run([sys.executable, str(Path(__file__).with_name("update_learning_aids.py")), tmp, "--learning-assist", "on", "--countdown", "off"], check=True, capture_output=True)
            result = json.loads(path.read_text())
            self.assertTrue(result["foreground"]["neighbors"]["enabled"])
            self.assertFalse(result["foreground"]["countdown"]["enabled"])
            self.assertEqual(result["foreground"]["veil"], {"opacity": .54})
            self.assertEqual(result["foreground"]["customReviewedField"], "keep")
            self.assertEqual(result["floatingOverlay"], {"enabled": True})

    def test_countdown_on_output_clock(self):
        line = {"text": "歌", "startMs": 3000, "parts": [{"text": " ", "startMs": 3000}, {"text": "歌", "startMs": 5500}]}
        plan = countdown_plan([line], True, 10000)
        self.assertEqual(plan["onsetMs"], 5500)
        self.assertEqual([(p["startMs"], p["endMs"], p["value"]) for p in plan["segments"]], [(2500, 3500, 3), (3500, 4500, 2), (4500, 5500, 1)])
        self.assertEqual(countdown_plan([line], False, 10000)["segments"], [])
        line["parts"] = []; line["startMs"] = 1500
        self.assertEqual(countdown_plan([line], True, 10000)["segments"], [{"startMs": 0, "endMs": 500, "value": 2}, {"startMs": 500, "endMs": 1500, "value": 1}])
        line["startMs"] = -100
        self.assertEqual(countdown_plan([line], True, 10000)["segments"], [])

    def test_timeline_prelude_gap_switch_and_offset(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); project = root / "project"; (project / "timing").mkdir(parents=True)
            def write(name, doc): (project / name).write_text(json.dumps(doc), encoding="utf-8")
            frames = [{"id": "l1", "startMs": 5000, "endMs": 6000, "caption": {"japanese": "歌"}}, {"id": "l2", "startMs": 8000, "endMs": 9000, "caption": {"japanese": "声"}}]
            write("frames.json", {"frames": frames})
            write("timing/qm.json", {"lines": [{"startMs": f["startMs"], "endMs": f["endMs"], "text": f["caption"]["japanese"], "parts": [{"text": f["caption"]["japanese"], "startMs": f["startMs"], "endMs": f["endMs"]}]} for f in frames]})
            write("input-manifest.json", {"alignment": {"offsetMs": 1000}})
            write("scene-timeline.json", {"segments": [{"startMs": 0, "endMs": "audio-end", "foregroundMode": "follow-lyrics"}]})
            options = configure_options(None); write("presentation.json", {"foreground": {**options, "defaultMode": "follow-lyrics"}})
            def compile():
                subprocess.run([sys.executable, str(Path(__file__).with_name("build_foreground_timeline.py")), str(root), str(root / "timeline.json"), "--duration-ms", "11000"], check=True, capture_output=True)
                return json.loads((root / "timeline.json").read_text())
            timeline = compile()
            def state(time): return next(s for s in timeline["segments"] if s["startMs"] <= time < s["endMs"])
            self.assertEqual(state(0)["frameId"], "l1")
            self.assertEqual(state(3000)["countdownValue"], 3)
            self.assertEqual(state(5000)["countdownValue"], 1)
            self.assertNotIn("countdownValue", state(6000))
            self.assertEqual(state(6000)["kind"], "active")
            self.assertEqual(state(7600)["kind"], "blank")
            self.assertEqual(state(9000)["frameId"], "l2")
            write("presentation.json", {"foreground": {"defaultMode": "persistent"}})
            write("scene-timeline.json", {"segments": [{"startMs": 0, "endMs": "audio-end", "foregroundMode": "persistent"}]})
            timeline = compile()
            self.assertEqual(state(0)["kind"], "blank")
            self.assertEqual(state(7600)["frameId"], "l1")
            self.assertEqual(state(10900)["frameId"], "l2")


if __name__ == "__main__": unittest.main()
