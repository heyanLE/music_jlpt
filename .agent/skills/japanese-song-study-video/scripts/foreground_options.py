"""Explicit learning-aid options; absent legacy fields never opt in silently."""
from __future__ import annotations

PRELUDE_MODES = ("first-line", "hidden", "countdown-reveal")
COUNTDOWN_PLACEMENTS = ("template", "neighbor-left")


def resolve_options(foreground: dict) -> dict:
    neighbors = foreground.get("neighbors", {"enabled": False})
    countdown = foreground.get("countdown", {"enabled": False, "durationMs": 3000})
    if not isinstance(neighbors, dict) or type(neighbors.get("enabled")) is not bool:
        raise ValueError("foreground.neighbors.enabled must be a boolean")
    if not isinstance(countdown, dict) or type(countdown.get("enabled")) is not bool:
        raise ValueError("foreground.countdown.enabled must be a boolean")
    duration = countdown.get("durationMs", 3000)
    if type(duration) is not int or duration != 3000:
        raise ValueError("foreground.countdown.durationMs must be 3000 (3/2/1, one second each)")
    placement = countdown.get("placement", "template")
    if placement not in COUNTDOWN_PLACEMENTS:
        raise ValueError(f"foreground.countdown.placement must be one of {COUNTDOWN_PLACEMENTS}")
    prelude = foreground.get("preludeMode", "hidden")
    if prelude not in PRELUDE_MODES:
        raise ValueError(f"foreground.preludeMode must be one of {PRELUDE_MODES}")
    return {"neighbors": {"enabled": neighbors["enabled"]},
            "countdown": {"enabled": countdown["enabled"], "durationMs": duration, "placement": placement},
            "preludeMode": prelude}


def configure_options(existing: dict | None, neighbors=None, countdown=None, prelude=None,
                      countdown_placement=None) -> dict:
    options = resolve_options(existing) if existing is not None else {
        "neighbors": {"enabled": True}, "countdown": {"enabled": True, "durationMs": 3000, "placement": "template"},
        "preludeMode": "first-line"}
    if neighbors is not None: options["neighbors"]["enabled"] = neighbors == "on"
    if countdown is not None: options["countdown"]["enabled"] = countdown == "on"
    if countdown_placement is not None: options["countdown"]["placement"] = countdown_placement
    if prelude is not None: options["preludeMode"] = prelude
    return options


def countdown_plan(lines: list[dict], enabled: bool, duration_ms: int) -> dict:
    """All input times have already been transformed to the output clock."""
    onset = None
    for line in lines:
        if not line.get("text", "").strip(): continue
        voiced = [part["startMs"] for part in line["parts"] if part["text"].strip()]
        onset = min(voiced) if voiced else line["startMs"]
        break
    samples = []
    if enabled and onset is not None:
        for value in (3, 2, 1):
            start, end = max(0, onset - value * 1000), min(duration_ms, onset - (value - 1) * 1000)
            if end > start: samples.append({"startMs": start, "endMs": end, "value": value})
    return {"enabled": enabled, "clock": "output", "onsetMs": onset,
            "segments": samples, "clippedAtOutputStart": bool(enabled and onset is not None and onset < 3000)}
